#!/usr/bin/env python
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


from .avahioffer import AvahiHTTPOffer
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .keyconfirm import PreSignWidget
from .keyfprscan import KeyFprScanWidget
from .keylistwidget import KeyListWidget
from .KeyPresent import KeyPresentWidget
from .gpgmh import openpgpkey_from_data
from . import gpgmh
from .util import sign_keydata_and_send
from . import gtkexcepthook

log = logging.getLogger(__name__)

def remove_whitespace(s):
    cleaned = re.sub('[\s+]', '', s)
    return cleaned



class KeysignApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(KeysignApp, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        
        self.send_stack = None
        self.receive_stack = None
        self.send_receive_stack = None
        self.header_button_handler_id = None
        self.key_list_widget = None
        self.key_present_widget = None
        self.pre_sign_widget = None

    def on_activate(self, app):
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "app.ui")
        appwindow = 'applicationwindow1'
        builder = Gtk.Builder()
        builder.add_objects_from_file(ui_file_path, [appwindow])
        window = builder.get_object(appwindow)
        #window.set_title("Keysign")
        # window.set_size_request(600, 400)
        #window = self.builder.get_object("appwindow")
        self.headerbar = window.get_titlebar()
        self.header_button = builder.get_object("back_refresh_button")
        self.header_button.connect('clicked', self.on_header_button_clicked)

        sw = builder.get_object('stackswitcher1')
        # FIXME: I want to be able to press Alt+S and Alt+R respectively
        # to switch the stack pages to Send and Receive.
        # It's possible when using the Gtk Inspector and modify the
        # Switcher's children (ToggleButton and Label) to "use-underscore".
        # but it must be possible to do programmatically.
        # sw.get_children()
        self.stack_switcher = sw

        self.send_receive_stack = builder.get_object("send_receive_stack")
        self.send_receive_stack.connect('notify::visible-child',
            self.on_sr_stack_switch)


        # Load Send part
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "send.ui")
        widget_name = 'send_stack'
        builder = Gtk.Builder()
        builder.add_objects_from_file(ui_file_path, [widget_name])
        widget = builder.get_object(widget_name)
        ss = widget
        ss.connect('notify::visible-child', self.on_send_stack_switch)
        ss.connect('map', self.on_send_stack_mapped)

        keys = gpgmh.get_usable_secret_keys()
        klw = KeyListWidget(keys, builder=builder)
        klw.connect("key-activated", self.on_key_activated)
        klw.connect("map", self.on_keylist_mapped)
        klw.props.margin_left = klw.props.margin_right = 15

        ss.add_titled(klw, "keylist", "All Keys")
        self.key_list_widget = klw
        self.send_stack = ss

        # Dirty hack
        fakekey = gpgmh.Key("","","")
        kpw = KeyPresentWidget(fakekey, builder=builder)
        self.avahi_offer = None
        ## End of loading send part


        # Load Receive part
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "receive.ui")
        widget_name = 'receive_stack'
        builder = Gtk.Builder()
        builder.add_objects_from_file(ui_file_path,
            # Weird. The UI file has the confirm-button-image out of hierarchy
            [widget_name, 'confirm-button-image'])
        widget = builder.get_object(widget_name)
        rs = widget

        rs.connect('notify::visible-child',
            self.on_receive_stack_switch)

        scanner = KeyFprScanWidget() #builder=builder)
        scanner.connect("barcode", self.on_barcode)
        scanner.connect("changed", self.on_changed)
        scanner.connect("map", self.on_scanner_mapped)

        old_scanner = builder.get_object("scanner_widget")
        old_scanner_parent = old_scanner.get_parent()

        if old_scanner_parent:
            old_scanner_parent.remove(old_scanner)
            # Hrm. We probably always have to have a parent
            # otherwise we won't add the scanner here...
            old_scanner_parent.add(scanner)


        self.receive_stack = rs

        # It needs to be show()n so that it can be made visible
        scanner.show()
        # The stack now contains a box which we don't modify.
        # We could potentially ask the stack to show scanner.parent...
        # rs.set_visible_child(old_scanner_parent)


        self.send_receive_stack.add_titled(self.send_stack,
            "send_stack", "Send")
        self.send_receive_stack.add_titled(rs,
            "receive_stack", "Receive")
        window.show_all()
        self.add_window(window)

        self.discovery = AvahiKeysignDiscoveryWithMac()

    def run(self, args=[]):
        super(KeysignApp, self).run()

    def on_key_activated(self, widget, key):
        log.info("Activated key %r", key)
        ####
        # Start network services
        self.avahi_offer = AvahiHTTPOffer(key)
        discovery_data = self.avahi_offer.start()
        log.info("Use this for discovering the other key: %r", discovery_data)
        ####
        # Create and show widget for key
        stack = self.send_stack
        kpw = KeyPresentWidget(key, qrcodedata=discovery_data)
        kpw.connect('map', self.on_keypresent_mapped)
        stack.add_titled(kpw, "keypresent", "Publishing")
        stack_saved_visible_child = stack.get_visible_child()
        self.key_present_widget = kpw
        stack.set_visible_child(kpw)
        ####
        # Saving subtitle
        self.headerbar_subtitle = self.headerbar.get_subtitle()
        self.headerbar.set_subtitle("Sending {}".format(key.fpr))
        ####
        # Making button clickable
        self.header_button.set_sensitive(True)

    def on_barcode(self, scanner, barcode, gstmessage, pixbuf):
        log.debug("Scanned barcode %r", barcode)
        keydata = self.discovery.find_key(barcode)
        if keydata:
            self.on_keydata_downloaded(keydata, pixbuf)

    def on_changed(self, widget, entry):
        log.debug("Entry changed %r: %r", widget, entry)
        text = entry.get_text()
        keydata = self.discovery.find_key(text)
        if keydata:
            self.on_keydata_downloaded(keydata)

    # FIXME: I don't think we use this function anymore.
    # It's very complex for what it wants to achieve and
    # may serve as an example of how to not do things.
    # But we may as well get rid of it once we've checked
    # that it's not used anymore.
    def update_header_button(self, *args):
        if not (self.send_stack and self.receive_stack
                and self.send_receive_stack):
            # In the very beginning the app seems to be
            # not completely initialised as if on_activate has
            # not run yet, i.e. the stacks are still None
            return

        # We have 2 children in the top level stack: send and receive.
        # In the send stack, we currently have two children.
        # In the receive stack, we have at least three.
        visible_child = self.send_receive_stack.get_visible_child()
        if not visible_child:
            return

        hb = self.header_button
        old_id = self.header_button_handler_id

        if visible_child == self.send_stack:
            child = self.send_stack.get_visible_child()
            if not child:
                return

            if child == self.key_list_widget:
                hb.set_sensitive(True)
                hb.set_image(Gtk.Image.new_from_icon_name("gtk-refresh",
                    Gtk.IconSize.BUTTON))
                # FIXME: We don't support refreshing for now,
                # because we would need to construct a new KeyListWidget
                # and replace the existing one. That makes it more
                # complicated.
                hb.set_sensitive(False)
                handler = None

            elif child == self.key_present_widget:
                hb.set_sensitive(True)
                hb.set_image(Gtk.Image.new_from_icon_name("gtk-go-back",
                    Gtk.IconSize.BUTTON))
                def switch_back(*args):
                    log.debug("Current children: %r",
                        [(w, w.get_name()) for w in self.send_stack.get_children()])
                    log.debug("Key list widget: %r", self.key_list_widget)
                    self.send_stack.set_visible_child(self.key_list_widget)

                #handler = (lambda *args:
                handler = switch_back
            else:
                raise RuntimeError("Expected either %r "
                    "or %r "
                    "but got %r" %
                    (self.key_list_widget, self.key_present_widget, child))

        elif visible_child == self.receive_stack:
            child = self.receive_stack.get_visible_child()
            if child == self.scanner:
                hb.set_sensitive(False)
                handler = None
            elif child == "keyconfirm":
                hb.set_sensitive(True)
                hb.set_image(Gtk.Image.new_from_icon_name("gtk-go-back",
                    Gtk.IconSize.BUTTON))
                handler = (lambda *args:
                    self.receive_stack.set_visible_child(self.scanner))
            else:
                raise RuntimeError("Expected either 'scanner' "
                    "or 'keyconfirm' "
                    "but got %r" % child)

        else:
            raise RuntimeError("We expected either send or receive stack "
                "but got %r" % visible_child)

        if old_id:
            hb.disconnect(old_id)

        if handler:
            log.debug("Connecting %r to %r", handler, hb)
            signal_id = hb.connect('clicked', handler)
            self.header_button_handler_id = signal_id

    def on_sr_stack_switch(self, stack, *args):
        log.debug("Switched Stack! %r", args)
        #self.update_header_button()

    def on_send_stack_switch(self, stack, *args):
        log.debug("Switched Send Stack! %r", args)
        #self.update_header_button()

    def on_receive_stack_switch(self, stack, *args):
        log.debug("Switched Receive Stack! %r", args)
        #self.update_header_button()


    def on_send_header_button_clicked(self, button, *args):
        # Here we assume that there is only one place where
        # we could have possibly pressed this button, i.e.
        # from the keypresentwidget.
        log.debug("Send Headerbutton %r clicked! %r", button, args)
        self.send_stack.set_visible_child(self.key_list_widget)
        # Now more send specific actions are performed.
        # It would probably be helpful to have those in
        # a more central place for the "send" app to re-use
        self.avahi_offer.stop()
        self.avahi_offer = None

    def on_receive_header_button_clicked(self, button, *args):
        # Here we assume that there is only one place where
        # we could have possibly pressed this button, i.e.
        # from the presignwidget.
        log.debug("Receive Headerbutton %r clicked! %r", button, args)
        self.receive_stack.set_visible_child_name("scanner")

    def on_header_button_clicked(self, button, *args):
        log.debug("Headerbutton %r clicked! %r", button, args)
        # We have 2 children in the top level stack: send and receive.
        # In the send stack, we currently have two children.
        # In the receive stack, we have at least three.
        visible_child = self.send_receive_stack.get_visible_child()
        if not visible_child:
            return
        if visible_child == self.send_stack:
            return self.on_send_header_button_clicked(button, *args)
        elif visible_child == self.receive_stack:
            return self.on_receive_header_button_clicked(button, *args)
        else:
            raise RuntimeError("We expected either send or receive stack "
                "but got %r" % visible_child)


    def on_keydata_downloaded(self, keydata, pixbuf=None):
        key = openpgpkey_from_data(keydata)
        psw = PreSignWidget(key, pixbuf)
        psw.connect('sign-key-confirmed',
            self.on_sign_key_confirmed,
            keydata)
        psw.connect('map', self.on_presign_mapped)
        psw.set_name("presign")
        stack = self.receive_stack
        stack.add_titled(psw, "presign", "Sign Key")
        psw.show()
        stack.set_visible_child(psw)
        # self.psw = psw

    def on_keylist_mapped(self, keylistwidget):
        log.debug("Keylist becomes visible!")
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("gtk-refresh",
            Gtk.IconSize.BUTTON))
        # We don't support refreshing for now.
        self.header_button.set_sensitive(False)


    def on_send_stack_mapped(self, stack):
        log.debug("send stack becomes visible!")

    def on_keypresent_mapped(self, kpw):
        log.debug("keypresent becomes visible!")
        self.header_button.set_sensitive(True)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("gtk-go-back",
            Gtk.IconSize.BUTTON))

    def on_scanner_mapped(self, scanner):
        log.debug("scanner becomes visible!")
        self.header_button.set_sensitive(False)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("gtk-go-back",
            Gtk.IconSize.BUTTON))

    def on_presign_mapped(self, psw):
        log.debug("presign becomes visible!")
        self.header_button.set_sensitive(True)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("gtk-go-back",
            Gtk.IconSize.BUTTON))

    def on_sign_key_confirmed(self, keyPreSignWidget, key, keydata):
        log.debug ("Sign key confirmed! %r", key)
        # We need to prevent tmpfiles from going out of
        # scope too early so that they don't get deleted
        self.tmpfiles = list(
            sign_keydata_and_send(keydata))
        
        # After the user has signed, we switch back to the scanner,
        # because currently, there is not much to do on the
        # key confirmation page.
        log.debug ("Signed the key: %r", self.tmpfiles)
        self.receive_stack.set_visible_child_name("scanner")
        # Do we also want to add an infobar message or so..?





def main(args):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        args = []
    Gst.init()

    app = KeysignApp()
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        pass
    app.run(args)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
