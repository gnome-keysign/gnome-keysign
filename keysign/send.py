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
from .avahiwormholeoffer import AvahiWormholeOffer
from . import gpgmh

log = logging.getLogger(__name__)


class SendApp:
    """Common functionality needed when building the sending part
    
    This class will automatically start the keyserver
    and avahi components.  It will load a GtkStack from "send.ui"
    and automatically switch to a newly generate KeyPresentWidget.
    To switch the stack back and stop the keyserver, you have to
    call deactivate().
    """
    def __init__(self, builder=None):
        self.avahi_worm_offer = None
        self.stack = None
        self.stack_saved_visible_child = None
        self.klw = None
        self.kpw = None

        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "send.ui")
        if not builder:
            builder = Gtk.Builder()
            builder.add_objects_from_file(ui_file_path, ["send_stack"])
        keys = gpgmh.get_usable_secret_keys()
        klw = KeyListWidget(keys, builder=builder)
        klw.connect("key-activated", self.on_key_activated)
        self.klw = klw

        stack = builder.get_object("send_stack")
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
        kpw = KeyPresentWidget(fakekey, builder=builder)

        self.rb = builder.get_object('resultbox')
        self.stack.remove(self.rb)
        self.key = None
        self.result_label = builder.get_object("result_label")
        self.cancel_button = builder.get_object("cancel_download_button")
        self.ok_button = builder.get_object("ok_download_button")
        self.redo_button = builder.get_object("redo_download_button")
        self.redo_button.connect("clicked", self.on_redo_button_clicked)
        self.ok_button.connect("clicked", self.on_ok_button_clicked)
        self.cancel_button.connect("clicked", self.on_cancel_button_clicked)

    def on_key_activated(self, widget, key):
        self.key = key
        log.info("Activated key %r", key)
        ####
        # Create and show widget for key
        kpw = KeyPresentWidget(key)
        self.stack.add(kpw)
        self.stack_saved_visible_child = self.stack.get_visible_child()
        self.stack.set_visible_child(kpw)
        log.debug('Setting kpw: %r', kpw)
        self.kpw = kpw
        ####
        # Start network services
        self.avahi_worm_offer = AvahiWormholeOffer(key, self.on_message_callback, self.on_code_generated)
        self.avahi_worm_offer.start()

    def on_code_generated(self, worm_code, discovery_data):
        self.kpw.set_wormhole_code(worm_code)
        log.info("Use this for discovering the other key: %r", discovery_data)
        self.kpw.set_qrcode(discovery_data)

    def on_message_callback(self, success, message=None):
        # TODO use a better filter
        if message == 'wormhole.close() was called before the peer connection could be\n    established':
            pass
        else:
            self.show_result(success, message)
            # Deactivate wormhole and avahi?

    def show_result(self, success, message):
        self._deactivate_avahi_worm_offer()

        self.stack.add(self.rb)
        self.stack.remove(self.kpw)
        self.kpw = None

        if success:
            self.result_label.set_label("Key successfully sent.\nYou should receive soon an email with the signature.")
            self.cancel_button.set_visible(False)
            self.ok_button.set_visible(True)
            self.redo_button.set_visible(True)
            self.stack.set_visible_child(self.rb)
        else:
            self.result_label.set_label(str(message))
            self.cancel_button.set_visible(True)
            self.ok_button.set_visible(False)
            self.redo_button.set_visible(True)
            self.stack.set_visible_child(self.rb)

    def on_redo_button_clicked(self, button):
        log.info("redo pressed")
        self._set_saved_child_visible()
        self.on_key_activated(None, self.key)

    def on_ok_button_clicked(self, button):
        log.info("ok pressed")
        self._set_saved_child_visible()

    def on_cancel_button_clicked(self, button):
        log.info("cancel pressed")
        self._set_saved_child_visible()

    def deactivate(self):
        self._deactivate_avahi_worm_offer()

        ####
        # Re-set stack to initial position
        self._set_saved_child_visible()
        self.stack.remove(self.kpw)
        self.kpw = None

    def _set_saved_child_visible(self):
        self.stack.set_visible_child(self.stack_saved_visible_child)
        self.stack_saved_visible_child = None

    def _deactivate_avahi_worm_offer(self):
        # Stop network services
        if self.avahi_worm_offer:
            self.avahi_worm_offer.stop()
            self.avahi_worm_offer = None


class App(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.send_app = None
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

        self.send_app = SendApp(builder=self.builder)
        self.send_app.klw.connect("key-activated", self.on_key_activated)

        window.show_all()
        self.add_window(window)


    

    def on_key_activated(self, widget, key):
        ####
        # Saving subtitle
        self.headerbar_subtitle = self.headerbar.get_subtitle()
        self.headerbar.set_subtitle("Sending {}".format(key.fpr))
        ####
        # Making button clickable
        self.headerbutton.set_sensitive(True)


    def on_headerbutton_clicked(self, button):
        log.info("Headerbutton pressed: %r", button)
        self.send_app.deactivate()

        # If we ever defer operations here, it seems that
        # the order of steps is somewhat important for the
        # responsiveness of the UI.  It seems that shutting down
        # the HTTPd takes ages to finish and blocks animations.
        # So we want to do that first, because we can argue
        # better that going back takes some time rather than having
        # a half-baked switching animation.
        # For now, it doesn't matter, because we don't defer.

        ####
        # Making button non-clickable
        self.headerbutton.set_sensitive(False)
        ####
        # Restoring subtitle
        self.headerbar.set_subtitle(self.headerbar_subtitle)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = App()
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        pass
    app.run()
