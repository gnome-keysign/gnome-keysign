#!/usr/bin/env python

import logging
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
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

from .keylistwidget import KeyListWidget
from .KeyPresent import KeyPresentWidget
from .avahioffer import AvahiHTTPOffer
from . import gpgmh

log = logging.getLogger(__name__)

class App(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        #self.builder = Gtk.Builder.new_from_file('send.ui')

    def on_activate(self, data=None):
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "send.ui")
        self.builder = Gtk.Builder.new_from_file(ui_file_path)
        window = self.builder.get_object("appwindow")
        assert window
        self.headerbar = self.builder.get_object("headerbar")
        hb = self.builder.get_object("headerbutton")
        hb.connect("clicked", self.on_headerbutton_clicked)
        self.headerbutton = hb

        keys = gpgmh.get_usable_secret_keys()
        klw = KeyListWidget(keys, builder=self.builder)
        klw.connect("key-activated", self.on_key_activated)

        stack = self.builder.get_object("send_stack")
        stack.add(klw)
        self.stack = stack

        # This is a dirty hack :-/
        # The problem is that the .ui file contains a few widgets
        # that we (potentially) want to instantiate separately.
        # Now that may not necessarily be what Gtk people envisioned
        # so it's not supported nicely.
        # The actual problem is that the widgets of our desire are
        # currently attached to a GtkStack. When our custom widget
        # code runs, it detaches itself from its parent, i.e. the stack.
        # We need need to instantiate the widget with key, however.
        fakekey = gpgmh.Key("","","")
        kpw = KeyPresentWidget(fakekey, builder=self.builder)

        window.show_all()
        self.add_window(window)

        self.avahi_offer = None


    def on_key_activated(self, widget, key):
        log.info("Activated key %r", key)
        ####
        # Start network services
        self.avahi_offer = AvahiHTTPOffer(key)
        discovery_data = self.avahi_offer.start()
        log.info("Use this for discovering the other key: %r", discovery_data)
        ####
        # Create and show widget for key
        kpw = KeyPresentWidget(key, qrcodedata=discovery_data)
        self.stack.add(kpw)
        self.stack_saved_visible_child = self.stack.get_visible_child()
        self.stack.set_visible_child(kpw)
        self.kpw = kpw
        ####
        # Saving subtitle
        self.headerbar_subtitle = self.headerbar.get_subtitle()
        self.headerbar.set_subtitle("Sending {}".format(key.fpr))
        ####
        # Making button clickable
        self.headerbutton.set_sensitive(True)


    def on_headerbutton_clicked(self, button):
        log.info("Headerbutton pressed: %r", button)
        # If we ever defer operations here, it seems that
        # the order of steps is somewhat important for the
        # responsiveness of the UI.  It seems that shutting down
        # the HTTPd takes ages to finish and blocks animations.
        # So we want to do that first, because we can argue
        # better that going back takes some time rather than having
        # a half-baked switching animation.
        # For now, it doesn't matter, because we don't defer.
        ####
        # Stop network services
        avahi_offer = self.avahi_offer
        avahi_offer.stop()
        self.avahi_offer = None
        ####
        # Making button non-clickable
        self.headerbutton.set_sensitive(False)
        ####
        # Restoring subtitle
        self.headerbar.set_subtitle(self.headerbar_subtitle)
        ####
        # Re-set stack to inital position
        self.stack.set_visible_child(self.stack_saved_visible_child)
        self.stack.remove(self.kpw)
        self.kpw = None
        self.stack_saved_visible_child = None

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = App()
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        pass
    app.run()
