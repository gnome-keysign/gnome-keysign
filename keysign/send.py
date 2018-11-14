#!/usr/bin/env python

import logging
import os
import signal

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gdk
from gpg import errors
from wormhole.errors import ServerConnectionError, LonelyError, WrongPasswordError
if __name__ == "__main__":
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

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
from .offer import Offer
from . import gpgmeh
# We import i18n to have the locale set up for Glade
from .i18n import _
log = logging.getLogger(__name__)

try:
    from .bluetoothoffer import BluetoothOffer
except ImportError:
    log.exception("cannot import BluetoothOffer")
    BluetoothOffer = None


DRAG_ACTION = Gdk.DragAction.COPY


class SendApp:
    """Common functionality needed when building the sending part
    
    This class will automatically start the keyserver
    and avahi components.  It will load a GtkStack from "send.ui"
    and automatically switch to a newly generate KeyPresentWidget.
    To switch the stack back and stop the keyserver, you have to
    call deactivate().
    """
    def __init__(self, builder=None):
        self.offer = None
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
        keys = gpgmeh.get_usable_secret_keys()
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
        fakekey = gpgmeh.Key("","","")
        kpw = KeyPresentWidget(fakekey, "", builder=builder)

        self.rb = builder.get_object('resultbox')
        self.stack.remove(self.rb)
        self.key = None
        self.result_label = builder.get_object("result_label")
        self.notify = None
        self.internet_option = False

        # Add drag and drop to the keys list widget
        builder.connect_signals(self)
        self.label = builder.get_object("keys_listbox")
        self.label.drag_dest_set(Gtk.DestDefaults.ALL, [], DRAG_ACTION)
        self.label.drag_dest_set_target_list(None)
        self.label.drag_dest_add_text_targets()

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        filename = data.get_text()
        filename = filename[7:].strip('\r\n\x00')  # remove file://, \r\n and NULL
        log.info("Received file: %s" % filename)
        try:
            gpgmh.import_signature(filename)
        except errors.GPGMEError as e:
            log.error(e)

    @inlineCallbacks
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
        if self.internet_option:
            #self.kpw.internet_spinner.start()
            # After 10 seconds without a wormhole code we display an info bar
            timer = 10
            self.notify = reactor.callLater(timer, self.slow_connection)
            self.offer = Offer(self.key)
            try:
                info = yield self.offer.allocate_code(worm=True)
            except ServerConnectionError:
                # We are without a working Internet connection so we stop the previously
                # activated Avahi server and we display an infobar
                self._deactivate_timer()
                self.offer.stop_avahi()
                self.offer = None
                self.klw.code_spinner.stop()
                self.no_connection()
                return

            code, discovery_data = info
            self.create_keypresent(code, discovery_data)
            defers = self.offer.start()
            for de in defers:
                # TODO handle errors here?
                de.addCallback(self._received)
        else:
            self.offer = Offer(self.key)
            info = yield self.offer.allocate_code(worm=False)
            code, discovery_data = info
            self.create_keypresent(code, discovery_data)
            defers = self.offer.start()
            for de in defers:
                de.addCallback(self._received)

    def _received(self, start_data):
        success, message = start_data
        if message and type(message) == LonelyError:
            # This only means that we closed wormhole before a transfer
            pass
        elif message and message == "Back":
            # Simply the return of the back button, no errors here
            pass
        elif message and type(message) == ServerConnectionError:
            self._deactivate_timer()
            self.deactivate()
            self.klw.code_spinner.stop()
            self.no_connection()
        else:
            self.show_result(success, message)

    def slow_connection(self):
        self.klw.label_ib.set_label(_("Still trying to get a connection to the Internet. "
                                      "It appears to be slow or unavailable."))
        self.klw.ib.show()
        log.info("Slow Internet connection")

    def no_connection(self):
        self.klw.label_ib.set_label(_("There isn't an Internet connection!"))
        self.klw.ib.show()
        log.info("No Internet connection")

    def create_keypresent(self, discovery_code, discovery_data):
        self._deactivate_timer()
        log.info("Use this for discovering the other key: %r", discovery_data)
        ####
        # Create widget for key
        self.kpw = KeyPresentWidget(self.key, discovery_code, discovery_data)

        ####
        # Show widget for key
        self.stack.add(self.kpw)
        self.stack_saved_visible_child = self.stack.get_visible_child()
        self.stack.set_visible_child(self.kpw)
        log.debug('Setting kpw: %r', self.kpw)
        self.klw.ib.hide()
        self.klw.code_spinner.stop()

    def show_result(self, success, message):
        self._deactivate_offer()

        self.stack.add(self.rb)
        self.stack.remove(self.kpw)
        self.kpw = None

        if success:
            self.result_label.set_label(_("Key successfully sent.\n"
                                          "You should receive soon an email with the signature."))
            self.stack.set_visible_child(self.rb)
        else:
            if type(message) == WrongPasswordError:
                self.result_label.set_label(_("Could not establish a secure connection.\n"
                                              "Either your partner has entered a wrong code or "
                                              "someone tried to intercept your connection"))
            else:
                self.result_label.set_label(_("An unexpected error occurred:\n%s" % message))
            self.stack.set_visible_child(self.rb)

    def deactivate(self):
        self._deactivate_offer()

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

    def _deactivate_offer(self):
        # Stop network services
        if self.offer:
            self.offer.stop()
            self.offer = None
            log.debug("Stopped network services")


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
        hb.connect("clicked", self.on_header_button_clicked)
        self.header_button = hb
        self.internet_toggle = self.builder.get_object("internet_toggle")
        self.internet_toggle.connect("toggled", self.on_toggle_clicked)

        self.send_app = SendApp(builder=self.builder)
        ss = self.send_app.stack
        ss.connect('notify::visible-child', self.on_send_stack_switch)
        ss.connect('map', self.on_send_stack_mapped)
        self.send_stack = ss

        window.show_all()
        self.add_window(window)

    @staticmethod
    def on_delete_window(*args):
        reactor.callFromThread(reactor.stop)

    def on_toggle_clicked(self, toggle):
        log.info("Internet toggled to: %s", toggle.get_active())
        self.send_app.set_internet_option(toggle.get_active())

    def on_send_stack_switch(self, stack, *args):
        log.debug("Switched Send Stack! %r", args)
        current = self.send_app.stack.get_visible_child()
        if current == self.send_app.klw:
            log.debug("Key list page now visible")
            self.on_keylist_mapped(self.send_app.klw)
        elif current == self.send_app.kpw:
            log.debug("Key present page now visible")
            self.on_keypresent_mapped(self.send_app.kpw)
        elif current == self.send_app.rb:
            log.debug("Result page now visible")
            self.on_resultbox_mapped(self.send_app.rb)
        else:
            log.error("An unexpected page is now visible: %r", current)

    def on_resultbox_mapped(self, rb):
        log.debug("Resultbox becomes visible!")
        self.header_button.set_sensitive(True)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("go-previous",
                                         Gtk.IconSize.BUTTON))
        self.internet_toggle.hide()

    def on_keylist_mapped(self, keylistwidget):
        log.debug("Keylist becomes visible!")
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("view-refresh",
            Gtk.IconSize.BUTTON))
        # We don't support refreshing for now.
        self.header_button.set_sensitive(False)
        self.internet_toggle.show()

    def on_send_stack_mapped(self, stack):
        log.debug("send stack becomes visible!")
        # Adjust the top bar buttons
        self.on_send_stack_switch(stack)

    def on_keypresent_mapped(self, kpw):
        log.debug("keypresent becomes visible!")
        self.header_button.set_sensitive(True)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("go-previous",
            Gtk.IconSize.BUTTON))
        self.internet_toggle.hide()

    def on_send_header_button_clicked(self, button, *args):
        # Here we assume that there is only two places where
        # we could have possibly pressed this button, i.e.
        # from the keypresentwidget or the result page
        log.debug("Send Headerbutton %r clicked! %r", button, args)
        current = self.send_app.stack.get_visible_child()
        klw = self.send_app.klw
        kpw = self.send_app.kpw
        # If we are in the keypresentwidget
        if current == kpw:
            self.send_stack.set_visible_child(klw)
            self.send_app.deactivate()
        # Else we are in the result page
        else:
            self.send_stack.remove(current)
            self.send_app.set_saved_child_visible()
            self.send_app.on_key_activated(None, self.send_app.key)

    def on_header_button_clicked(self, button, *args):
        log.debug("Headerbutton %r clicked! %r", button, args)
        return self.on_send_header_button_clicked(button, *args)

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
