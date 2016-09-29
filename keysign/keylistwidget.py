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

from .gpgmh import get_usable_keys

log = logging.getLogger(__name__)

class ListBoxRowWithKey(Gtk.ListBoxRow):
    "A simple extension of a Gtk.ListBoxRow to also hold a key object"

    def __init__(self, key):
        super(ListBoxRowWithKey, self).__init__()
        self.key = key

        s = self.format(key)
        label = Gtk.Label(s, use_markup=True, xalign=0)
        self.add(label)


    @classmethod
    def format_uid(cls, uid):
        "Returns a pango string for a gpgmh.UID"
        fmt = "{name}\t<i>{email}</i>\t<small>{expiry}</small>"

        d = {k: GLib.markup_escape_text("{}".format(v))
             for k, v in uid._asdict().items()}
        log.info("Formatting UID %r", d)
        s = fmt.format(**d)
        log.info("Formatted UID: %r", s)
        return s


    @classmethod
    def format(cls, key):
        "Returns a pango string for a gpgmh.Key"
        fmt  = "{created} "
        fmt  = "<b>{fingerprint}</b>\n"
        fmt += "\n".join((cls.format_uid(uid) for uid in key.uidslist))
        fmt += "\n<small>Expires {expiry}</small>"

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
        str('key-activated'): (GObject.SIGNAL_RUN_LAST, None,
                               # (ListBoxRowWithKey.__gtype__,)
                               (object,)),
                               # The activated key
        str('key-selected'): (GObject.SIGNAL_RUN_LAST, None,
                               # (ListBoxRowWithKey.__gtype__,)
                               (object,)),
                               # The selected key
    }

    def __init__(self, keys, builder=None):
        "Sets the widget up with the given keys"
        super(KeyListWidget, self).__init__()

        thisdir = os.path.dirname(os.path.abspath(__file__))
        if not builder:
            builder = Gtk.Builder.new_from_file(
                os.path.join(thisdir, 'send.ui'))
        widget = builder.get_object('box2')
        old_parent = widget.get_parent()
        old_parent.remove(widget)
        self.add(widget)

        self.listbox = builder.get_object("keys_listbox")

        if len(list(keys)) <= 0:
            infobar = builder.get_object("infobar")
            infobar.show()
            l = Gtk.Label("You don't have any OpenPGP keys")
            self.listbox.add(l)
        else:
            for key in keys:
                lbr = ListBoxRowWithKey(key)
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
            self.kpw = KeyListWidget()
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
