#!/usr/bin/env python
# encoding: utf-8
#    Copyright 2016 Andrei Macavei <andrei.macavei89@gmail.com>
#    Copyright 2017 Tobias Mueller <muelli@cryptobitch.de>
#
#    This file is part of GNOME Keysign.
#
#    GNOME Keysign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    GNOME Keysign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with GNOME Keysign.  If not, see <http://www.gnu.org/licenses/>.

from datetime import date, datetime
import signal
import sys
import argparse
import logging
import os

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GLib
from gi.repository import GObject


if  __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')


from .gpgmeh import get_usable_keys
from .scan_barcode import ScalingImage
from .util import format_fingerprint

log = logging.getLogger(__name__)


#FIXME: remove the temporary keyword args after updating Key class
#with length and creation_time fields
def format_key_header(fpr, length='2048', creation_time=None):
    if creation_time == None:
        creation_time = datetime.strptime('01011970', "%d%m%Y").date()
    try:
        creation = date.fromtimestamp(float(creation_time))
    except TypeError as e:
        # This might be the case when the creation_time is already a timedate
        creation = creation_time

    key_header = format_fingerprint(fpr).replace('\n', '  ')
    return key_header

def format_uidslist(uidslist):
    result = ""
    for uid in uidslist:
        uidstr = GLib.markup_escape_text(uid.uid)
        result += ("{}\n".format(uidstr))

    return result



class PreSignWidget(Gtk.VBox):
    """A widget for obtaining a key fingerprint.

    The fingerprint can be obtain by inserting it into
    a text entry, or by scanning a barcode with the
    built-in camera.
    """

    __gsignals__ = {
        str('sign-key-confirmed'): (GObject.SignalFlags.RUN_LAST, None,
                                    (GObject.TYPE_PYOBJECT,)),
    }

    def __init__(self, key, pixbuf=None, builder=None):
        super(PreSignWidget, self).__init__()
        thisdir = os.path.dirname(os.path.abspath(__file__))
        widget_name = 'keyconfirmbox'
        if not builder:
            builder = Gtk.Builder()
            builder.add_objects_from_file(
                os.path.join(thisdir, 'receive.ui'),
                [widget_name, 'confirm-button-image'])
        widget = builder.get_object(widget_name)
        parent = widget.get_parent()
        if parent:
            parent.remove(widget)
        self.add(widget)

        confirm_btn = builder.get_object("confirm_sign_button")
        confirm_btn.connect("clicked", self.on_confirm_button_clicked)

        self.key = key

        keyIdsLabel = builder.get_object("key_ids_label")
        log.info("The Key ID Label can focus: %r, %r",
            keyIdsLabel.props.can_focus,
            keyIdsLabel.get_can_focus())
        # Weird. The glade file defines can_focus = False, but it's set to True...
        keyIdsLabel.set_can_focus(False)
        keyIdsLabel.set_markup(format_key_header(self.key.fingerprint))

        uidsLabel = builder.get_object("uids_label")
        # FIXME: Check why Builder thinks the widget can focus when the glade file says no
        uidsLabel.set_can_focus(False)
        markup = format_uidslist(self.key.uidslist)
        uidsLabel.set_markup(markup)

        imagebox = builder.get_object("imagebox")
        for child in imagebox.get_children():
            imagebox.remove(child)
        imagebox.add(ScalingImage(pixbuf=pixbuf))
        imagebox.show_all()

        # We save the reference here to expose this infobar to the caller.
        # This is a bit ugly, because it makes this implementation detail part of the
        # API. The infobar should probably be part of the caller's responsibility,
        # i.e. not part of this widget.
        self.infobar_success = builder.get_object('infobar_certifications_produced')
        self.infobar_errors = builder.get_object('infobar_certifications_errors')
        self.infobar_save_as_button = builder.get_object('btn_local_import_save_as')
        self.infobar_import_button = builder.get_object('btn_local_import')
        self.infobar_show_error_button = builder.get_object('btn_show_error_details')

        ib_error_show = self.infobar_errors.show
        def show(exception):
            self.infobar_errors.exception = exception
            ib_error_show()
            def show_error(btn):
                dialog = Gtk.MessageDialog(
                    transient_for=self.get_toplevel(),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CLOSE,
                    text="Error certifying key"
                )
                dialog.format_secondary_text(
                    str(exception) + "\n"
                    "We don't know any more, sorry :(")
                dialog.run()
                dialog.destroy()
            self.infobar_show_error_button.connect("clicked", show_error)
        self.infobar_errors.show = show

    def on_confirm_button_clicked(self, buttonObject, *args):
        self.emit('sign-key-confirmed', self.key, *args)



class PreSignApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(PreSignApp, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.psw = None

        self.log = logging.getLogger(__name__)

    def on_activate(self, app):
        window = Gtk.ApplicationWindow()
        window.set_title("Key Pre Sign Widget")
        # window.set_size_request(600, 400)

        if not self.psw:
            self.psw = PreSignWidget()

        self.psw.connect('sign-key-confirmed', self.on_sign_key_confirmed)
        window.add(self.psw)

        window.show_all()
        self.add_window(window)

    def on_sign_key_confirmed(self, keyPreSignWidget, *args):
        self.log.debug ("Sign key confirmed!")

    def run(self, args):
        if not args:
            args = [""]
        key = get_usable_keys (pattern=args[0])[0]
        if len(args) >= 2:
            image_fname = args[1]
            log.debug("Trying to load pixbuf from %r", image_fname)
            pixbuf = Gtk.Image.new_from_file(image_fname).get_pixbuf()
        else:
            pixbuf = None
        self.psw = PreSignWidget(key, pixbuf=pixbuf)
        super(PreSignApp, self).run()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    app = PreSignApp()
    app.run(sys.argv[1:])
