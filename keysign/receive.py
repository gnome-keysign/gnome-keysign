#!/usr/bin/env python
#    Copyright 2016 Tobias Mueller <muelli@cryptobitch.de>
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

import logging
import re
import os
import signal
import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
gi.require_version('Gst', '1.0')
from gi.repository import Gst
if __name__ == "__main__":
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
from twisted.internet import reactor

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


from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .keyfprscan import KeyFprScanWidget
from .keyconfirm import PreSignWidget
from .gpgmh import openpgpkey_from_data
from .i18n import _
from .util import sign_keydata_and_send, fix_infobar
from .avahiwormholediscover import AvahiWormholeDiscover

log = logging.getLogger(__name__)

def remove_whitespace(s):
    cleaned = re.sub('[\s+]', '', s)
    return cleaned


class ReceiveApp:
    def __init__(self, builder=None):
        self.psw = None
        self.discovery = None
        self.log = logging.getLogger(__name__)

        widget_name = "receive_stack"
        if not builder:
            ui_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "receive.ui")
            builder = Gtk.Builder()
            builder.add_objects_from_file(ui_file,
                [widget_name, 'confirm-button-image'])

        self.accept_button = builder.get_object("confirm_sign_button")

        old_scanner = builder.get_object("scanner_widget")
        old_scanner_parent = old_scanner.get_parent()

        scanner = KeyFprScanWidget() #builder=builder)
        scanner.connect("changed", self.on_code_changed)
        scanner.connect("barcode", self.on_barcode)

        if old_scanner_parent:
            old_scanner_parent.remove(old_scanner)
            # Hm. If we don't have an old parent, we never get to see
            # the newly created scanner. Weird.
            old_scanner_parent.add(scanner)

        receive_stack = builder.get_object(widget_name)
        # It needs to be show()n so that it can be made visible
        scanner.show()
        # FIXME: Use "stack_scanner_child" or so as identification
        # for the stack's scanner child to make it visible when the
        # app starts
        # receive_stack.set_visible_child(old_scanner_parent)
        self.scanner = scanner
        self.stack = receive_stack

        self.discovery = AvahiKeysignDiscoveryWithMac()
        ib = builder.get_object('infobar_discovery')
        fix_infobar(ib)
        self.discovery.connect('list-changed', self.on_list_changed, ib)

        self.aw_discovery = None
        self.rb = builder.get_object('box50')
        self.result_label = builder.get_object("error_download_label")
        self.cancel_button = builder.get_object("cancel_download_button")
        self.redo_button = builder.get_object("redo_download_button")
        self.redo_button.connect("clicked", self.on_redo_button_clicked)
        self.cancel_button.connect("clicked", self.on_cancel_button_clicked)
        # Clear the "downloading" label
        builder.get_object("label10").set_label("")

    def on_redo_button_clicked(self, button):
        """ Right know the redo button is quite useless because the sender after
        the first error it will never reuse the same wormhole code, even if the
        user press the redo button. So trying a redo here with the same code will
        never be success"""
        log.info("redo pressed")
        self.stack.remove(self.rb)
        self.aw_discovery.start()

    def on_cancel_button_clicked(self, button):
        log.info("cancel pressed")
        self.stack.remove(self.rb)

    def on_keydata_downloaded(self, keydata, pixbuf=None):
        key = openpgpkey_from_data(keydata)
        psw = PreSignWidget(key, pixbuf)
        psw.connect('sign-key-confirmed',
            self.on_sign_key_confirmed, keydata)
        self.stack.add_titled(psw, "presign", _("Sign Key"))
        psw.set_name("presign")
        psw.show()
        self.psw = psw
        self.stack.set_visible_child(self.psw)

    def on_message_received(self, key_data, success=True, message=None):
        if success:
            self.log.debug("message received")
            self.on_keydata_downloaded(key_data)
        else:
            self.stack.add(self.rb)
            self.result_label.set_label(str(message))
            self.stack.set_visible_child(self.rb)

    def on_code_changed(self, scanner, entry):
        self.log.debug("Entry changed %r: %r", scanner, entry)
        text = entry.get_text()
        if self.aw_discovery:
            self.aw_discovery.stop()
        self.aw_discovery = AvahiWormholeDiscover(text, self.discovery, self.on_message_received)
        self.aw_discovery.start()

    def on_barcode(self, scanner, barcode, gstmessage, pixbuf):
        self.log.debug("Scanned barcode %r", barcode)
        if self.aw_discovery:
            self.aw_discovery.stop()
        self.aw_discovery = AvahiWormholeDiscover(barcode, self.discovery, self.on_message_received)
        self.aw_discovery.start()

    def on_sign_key_confirmed(self, keyPreSignWidget, key, keydata):
        self.log.debug ("Sign key confirmed! %r", key)
        # We need to prevent tmpfiles from going out of
        # scope too early so that they don't get deleted
        self.tmpfiles = list(
            sign_keydata_and_send(keydata))

        # After the user has signed, we switch back to the scanner,
        # because currently, there is not much to do on the
        # key confirmation page.
        log.debug ("Signed the key: %r", self.tmpfiles)
        self.stack.set_visible_child_name("scanner")
        # Do we also want to add an infobar message or so..?

    def on_list_changed(self, discovery, number, userdata):
        ib = userdata
        if number == 0:
            ib.show()
        elif ib.is_visible():
            ib.hide()



class App(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.log = logging.getLogger(__name__)

    def on_activate(self, app):
        ui_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "receive.ui")
        builder = Gtk.Builder.new_from_file(ui_file)

        window = Gtk.ApplicationWindow()
        window.connect("delete-event", self.on_delete_window)
        window.set_title(_("Receive"))
        # window.set_size_request(600, 400)
        #window = self.builder.get_object("appwindow")
        
        self.receive = ReceiveApp(builder)
        receive_stack = self.receive.stack

        window.add(receive_stack)
        window.show_all()
        self.add_window(window)

        reactor.run()

    @staticmethod
    def on_delete_window(*args):
        reactor.callFromThread(reactor.stop)
        Gtk.main_quit(*args)


def main(args=[]):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        args = []
    Gst.init(None)

    app = App()
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT,
                                  lambda *args: (app.quit(), reactor.callFromThread(reactor.stop)), None)
    except AttributeError:
        pass
    app.run(args)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
