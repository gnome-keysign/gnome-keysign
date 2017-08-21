#!/usr/bin/env python

import logging
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib  # for markup_escape_text
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

from .keylistwidget import KeyListWidget
from .KeyPresent import KeyPresentWidget
from .avahioffer import AvahiHTTPOffer
from . import gpgmh
# We import i18n to have the locale set up for Glade
from .i18n import _
try:
    from .bluetoothoffer import BluetoothOffer
except ImportError:
    BluetoothOffer = None

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
        self.a_offer = None
        self.bt_offer = None
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

        self.key = None

    def on_key_activated(self, widget, key):
        self.key = key
        log.info("Activated key %r", key)
        ####
        # Start network services
        discovery_list = []
        self.a_offer = AvahiHTTPOffer(self.key)
        a_data = self.a_offer.start()
        discovery_list.append(a_data)
        bt_data = None
        if BluetoothOffer:
            self.bt_offer = BluetoothOffer(self.key)
            bt_data = self.bt_offer.allocate_code()
            if bt_data:
                discovery_list.append(bt_data)
        discovery_data = ";".join(discovery_list)
        if bt_data:
            self.bt_offer.start().addCallback(self._restart_bluetooth)
        else:
            log.info("Bluetooth as been skipped")
        log.info("Use this for discovering the other key: %r", discovery_data)
        ####
        # Create and show widget for key
        kpw = KeyPresentWidget(key, qrcodedata=discovery_data)
        self.stack.add(kpw)
        self.stack_saved_visible_child = self.stack.get_visible_child()
        self.stack.set_visible_child(kpw)
        log.debug('Setting kpw: %r', kpw)
        self.kpw = kpw

    def deactivate(self):
        self._deactivate_offer()

        ####
        # Re-set stack to inital position
        self.stack.set_visible_child(self.stack_saved_visible_child)
        self.stack.remove(self.kpw)
        self.kpw = None
        self.stack_saved_visible_child = None

    def _deactivate_offer(self):
        # Stop network services
        if self.a_offer:
            self.a_offer.stop()
            # We need to deallocate the avahi object or the used port will never be released
            self.a_offer = None
        if self.bt_offer:
            self.bt_offer.stop()
            self.bt_offer = None
        log.debug("Stopped network services")

    def _restart_bluetooth(self, _):
        log.info("Bluetooth as been restarted")
        self.bt_offer.start().addCallback(self._restart_bluetooth)


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
        window.connect("delete-event", self.on_delete_window)
        self.headerbar = self.builder.get_object("headerbar")
        hb = self.builder.get_object("headerbutton")
        hb.connect("clicked", self.on_headerbutton_clicked)
        self.headerbutton = hb

        self.send_app = SendApp(builder=self.builder)
        self.send_app.klw.connect("key-activated", self.on_key_activated)

        window.show_all()
        self.add_window(window)

    @staticmethod
    def on_delete_window(*args):
        reactor.callFromThread(reactor.stop)

    

    def on_key_activated(self, widget, key):
        ####
        # Saving subtitle
        self.headerbar_subtitle = self.headerbar.get_subtitle()
        self.headerbar.set_subtitle(_("Sending {}").format(key.fpr))
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
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT,
                                  lambda *args: reactor.callFromThread(reactor.stop), None)
    except AttributeError:
        pass
    reactor.registerGApplication(app)
    reactor.run()
