#!/usr/bin/env python
import logging
import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject  # for __gsignals__
from gi.repository import GLib  # for markup_escape_text

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
from .i18n import _
from .util import fix_infobar

log = logging.getLogger(__name__)

class ListBoxRowWithKey(Gtk.ListBoxRow):
    "A simple extension of a Gtk.ListBoxRow to also hold a key object"

    def __init__(self, key):
        super(ListBoxRowWithKey, self).__init__()
        self.key = key

        s = self.format(key)
        label = Gtk.Label(label=s, use_markup=True, xalign=0)
        self.add(label)

    @staticmethod
    def glib_markup_escape_text_to_text(s):
        """A helper function to return the text type
        markup_escape_text returns a "str" which is
        a binary type in python2.
        This function tries to decode the returned
        str object.  It will fail in Python3.
        """
        m = GLib.markup_escape_text(s)
        try:
            ret = m.decode('utf-8')
        except AttributeError:
            # We are in Python3 land. All is fine.
            ret = m
        return ret
        

    @classmethod
    def format_uid(cls, uid):
        "Returns a pango string for a gpgmeh.UID"
        fmt = "{name}\t<i>{email}</i>\t<small>{expiry}</small>"

        items = ('name', 'email', 'expiry')
        format_dict = {k: ""+(uid._asdict()[k] or "")
                          for k in items}
        log.info("format dicT: %r", format_dict)
        d = {k: (log.debug("handling kv: %r %r", k, v),
                  cls.glib_markup_escape_text_to_text(
                    "{}".format(v)))[1]
             for k, v in format_dict.items()}
        log.info("Formatting UID %r", d)
        s = fmt.format(**d)
        log.info("Formatted UID: %r", s)
        return s


    @classmethod
    def format(cls, key):
        "Returns a pango string for a gpgmeh.Key"
        fmt  = "{created} "
        fmt  = "<b>{fingerprint}</b>\n"
        fmt += "\n".join((cls.format_uid(uid) for uid in key.uidslist))
        fmt += "\n<small>" + _("Expires: ") + " {expiry}</small>"

        d = {k: GLib.markup_escape_text("{}".format(v))
             for k,v in key._asdict().items()}
        log.info("Formatting key %r", d)
        s = fmt.format(**d)
        log.info("Formatted key: %r", s)
        return s


class KeyListWidget(Gtk.HBox):
    """A Gtk Widget representing a list of OpenPGP Keys
    
    It shows the keys you provide in a ListBox and emits a
    `key-activated` or `key-selected` signal when the user
    "activated" or "selected" a key. "Activating" is Gtk speak for
    double-clicking (or pressing space, enter, ...) on an entry.
    It is also possible that the widget emits that signal on a single
    click if so configured.  "Selected" means that the user switched
    to an entry, e.g. by clicking it or pressing up or down.

    If you don't provide any keys, the widget will not behave nicely
    and potentially display a user facing warning. Or not.
    """
    __gsignals__ = {
        str('key-activated'): (GObject.SignalFlags.RUN_LAST, None,
                               # (ListBoxRowWithKey.__gtype__,)
                               (object,)),
                               # The activated key
        str('key-selected'): (GObject.SignalFlags.RUN_LAST, None,
                               # (ListBoxRowWithKey.__gtype__,)
                               (object,)),
                               # The selected key
    }

    def __init__(self, keys, builder=None):
        "Sets the widget up with the given keys"
        super(KeyListWidget, self).__init__()
        self.log = logging.getLogger(__name__)
        self.log.debug("KLW with keys: %r", keys)

        thisdir = os.path.dirname(os.path.abspath(__file__))
        widget_name = 'keylistbox'
        if not builder:
            builder = Gtk.Builder()
            builder.add_objects_from_file(
                os.path.join(thisdir, 'send.ui'),
                [widget_name])
        widget = builder.get_object(widget_name)
        old_parent = widget.get_parent()
        if old_parent:
            old_parent.remove(widget)
        self.add(widget)

        self.listbox = builder.get_object("keys_listbox")
        self.code_spinner = builder.get_object("code_spinner")
        self.ib_internet = builder.get_object('infobar_internet')
        fix_infobar(self.ib_internet)
        self.label_ib_internet = builder.get_object('label_internet')

        self.ib_import_okay = builder.get_object('infobar_import_okay')
        self.ib_import_error = builder.get_object('infobar_import_error')
        self.ib_import_error_no_new_sigs = builder.get_object('infobar_import_error_no_new_signatures')
        assert self.ib_import_okay
        assert self.ib_import_error
        assert self.ib_import_error_no_new_sigs
        fix_infobar(self.ib_import_okay)
        fix_infobar(self.ib_import_error)
        self.label_ib_import_okay = builder.get_object('label_import_okay')
        self.image_ib_import_okay = builder.get_object('image_import_okay')
        self.label_ib_import_error = builder.get_object('label_import_error')
        self.image_ib_import_error = builder.get_object('image_import_error')
        self.button_ib_import_error = builder.get_object('import_error_details_button')
        self.button_ib_import_okay = builder.get_object('return_signature')

        if len(list(keys)) <= 0:
            infobar = builder.get_object("infobar")
            infobar.show()
            l = Gtk.Label("You don't have any OpenPGP keys")
            self.listbox.add(l)
        else:
            for key in keys:
                self.log.debug("Adding key: %r", key)
                lbr = ListBoxRowWithKey(key)
                lbr.props.margin_bottom = 5
                self.listbox.add(lbr)
            self.listbox.connect('row-activated', self.on_row_activated)
            self.listbox.connect('row-selected', self.on_row_selected)


    def on_row_activated(self, keylistwidget, row):
        if row:
            self.emit('key-activated', row.key)

    def on_row_selected(self, keylistwidget, row):
        if row:
            self.emit('key-selected', row.key)


class App(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.kpw = None

    def on_activate(self, app):
        window = Gtk.ApplicationWindow()
        window.set_title("Key List")

        if not self.kpw:
            self.kpw = KeyListWidget(get_usable_keys())
        self.kpw.connect('key-activated', self.on_key_activated)
        self.kpw.connect('key-selected', self.on_key_selected)
        window.add(self.kpw)

        window.show_all()
        self.add_window(window)

    def on_key_activated(self, keylistwidget, row):
        self.get_windows()[0].get_window().beep()
        print ("Row activated! %r" % (row,))

    def on_key_selected(self, keylistwidget, row):
        print ("Row selected! %r" % (row,))

    def run(self, args):
        if not args:
            args = [""]
        keys = list(get_usable_keys(pattern=args[0]))
        self.kpw = KeyListWidget(keys)
        super(App, self).run()

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    app = App()
    app.run(sys.argv[1:])
