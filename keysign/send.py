#!/usr/bin/env python

import logging
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib  # for markup_escape_text
from wormhole.errors import ServerConnectionError, LonelyError, WrongPasswordError
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
from .avahiwormholeoffer import AvahiWormholeOffer
from . import gpgmh
from .util import is_code_complete
# We import i18n to have the locale set up for Glade
from .i18n import _

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
        kpw = KeyPresentWidget(fakekey, "", builder=builder)

        self.rb = builder.get_object('resultbox')
        self.stack.remove(self.rb)
        self.key = None
        self.result_label = builder.get_object("result_label")
        self.notify = None
        self.internet_option = False

    def on_key_activated(self, widget, key):
        # Deactivate any old connection attempt
        self._deactivate_timer()
        self.deactivate()
        self.klw.ib.hide()
        self.key = key
        log.info("Activated key %r", key)
        ####
        # Start network services
        self.klw.code_spinner.start()
        self.avahi_worm_offer = AvahiWormholeOffer(key, self.on_message_callback, self.on_code_generated)
        if self.internet_option:
            #self.kpw.internet_spinner.start()
            # After 10 seconds without a wormhole code we display an info bar
            timer = 10
            self.notify = reactor.callLater(timer, self.slow_connection)
            self.avahi_worm_offer.start()
        else:
            self.avahi_worm_offer.start_avahi()

    def slow_connection(self):
        self.klw.label_ib.set_label("Very slow Internet connection!")
        self.klw.ib.show()
        log.info("Slow Internet connection")

    def no_connection(self):
        self.klw.label_ib.set_label("No Internet connection!")
        self.klw.ib.show()
        log.info("No Internet connection")

    def on_code_generated(self, code, discovery_data):
        self._deactivate_timer()
        log.info("Use this for discovering the other key: %r", discovery_data)
        ####
        # Create widget for key
        self.kpw = KeyPresentWidget(self.key, code, discovery_data)

        ####
        # Show widget for key
        self.stack.add(self.kpw)
        self.stack_saved_visible_child = self.stack.get_visible_child()
        self.stack.set_visible_child(self.kpw)
        log.debug('Setting kpw: %r', self.kpw)
        self.klw.ib.hide()
        self.klw.code_spinner.stop()

    def on_message_callback(self, success, message=None):
        if message and message.type == LonelyError:
            # This only means that we closed wormhole before a transfer
            pass
        elif message and message.type == ServerConnectionError:
            self._deactivate_timer()
            self.deactivate()
            self.klw.code_spinner.stop()
            self.no_connection()
        else:
            self.show_result(success, message)

    def show_result(self, success, message):
        self._deactivate_avahi_worm_offer()

        self.stack.add(self.rb)
        self.stack.remove(self.kpw)
        self.kpw = None

        if success:
            self.result_label.set_label("Key successfully sent.\n"
                                        "You should receive soon an email with the signature.")
            self.stack.set_visible_child(self.rb)
        else:
            if message.type == WrongPasswordError:
                self.result_label.set_label("The security of the connection seems low.\n"
                                            "Either your partner has entered a wrong code or"
                                            "someone tried to intercept your connection")
            else:
                self.result_label.set_label("An unexpected error occurred:\n%s" % message)
            self.stack.set_visible_child(self.rb)

    def deactivate(self):
        self._deactivate_avahi_worm_offer()

        ####
        # Re-set stack to initial position
        self.set_saved_child_visible()
        if self.kpw:
            self.stack.remove(self.kpw)
            self.kpw = None

    def set_saved_child_visible(self):
        if self.stack_saved_visible_child:
            self.stack.set_visible_child(self.stack_saved_visible_child)
            self.stack_saved_visible_child = None

    def set_internet_option(self, value):
        self._deactivate_timer()
        self.deactivate()
        self.klw.ib.hide()
        self.klw.code_spinner.stop()
        self.internet_option = value

    def _deactivate_timer(self):
        if self.notify and not self.notify.called:
            self.notify.cancel()
            self.notify = None

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
        window.connect("delete-event", self.on_delete_window)
        self.headerbar = self.builder.get_object("headerbar")
        hb = self.builder.get_object("headerbutton")
        hb.connect("clicked", self.on_headerbutton_clicked)
        self.headerbutton = hb
        self.internet_toggle = self.builder.get_object("internet_toggle")
        self.internet_toggle.connect("toggled", self.on_toggle_clicked)

        self.send_app = SendApp(builder=self.builder)
        self.send_app.klw.connect("key-activated", self.on_key_activated)

        window.show_all()
        self.add_window(window)

    @staticmethod
    def on_delete_window(*args):
        reactor.callFromThread(reactor.stop)

    def on_toggle_clicked(self, toggle):
        log.info("Internet toggled to: %s", toggle.get_active())
        self.send_app.set_internet_option(toggle.get_active())

    def on_key_activated(self, widget, key):
        kpw = self.send_app.kpw
        kpw.connect('map', self.on_keypresent_mapped)
        log.debug("KPW to wait for map: %r (%r)", kpw, kpw.get_mapped())
        if kpw.get_mapped():
            # The widget is already visible. Let's quickly call our handler
            self.on_keypresent_mapped(kpw)

        ####
        # Saving subtitle
        self.headerbar_subtitle = self.headerbar.get_subtitle()
        self.headerbar.set_subtitle("Sending {}".format(key.fpr))

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
        # Restoring subtitle
        self.headerbar.set_subtitle(self.headerbar_subtitle)

        current = self.send_app.stack.get_visible_child()
        klw = self.send_app.klw
        kpw = self.send_app.kpw
        # If we are in the keypresentwidget
        if current == kpw:
            self.send_app.stack.set_visible_child(klw)
            self.send_app.deactivate()
        # Else we are in the result page
        else:
            self.send_app.stack.remove(current)
            self.send_app.set_saved_child_visible()
            self.send_app.on_key_activated(None, self.send_app.key)

        self.headerbutton.set_sensitive(False)
        self.internet_toggle.show()

    def on_keypresent_mapped(self, kpw):
        log.debug("keypresent becomes visible!")
        self.headerbutton.set_sensitive(True)
        self.headerbutton.set_image(
            Gtk.Image.new_from_icon_name("go-previous",
                                         Gtk.IconSize.BUTTON))
        self.internet_toggle.hide()

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
