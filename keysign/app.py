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
from gi.repository import Gdk
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


from .avahioffer import AvahiHTTPOffer
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .keyconfirm import PreSignWidget
from .keyfprscan import KeyFprScanWidget
from .keylistwidget import KeyListWidget
from .KeyPresent import KeyPresentWidget
from .gpgmh import openpgpkey_from_data
from . import gpgmh
from .receive import ReceiveApp
from .send import SendApp
from .util import sign_keydata_and_send
from . import gtkexcepthook


log = logging.getLogger(__name__)

def remove_whitespace(s):
    cleaned = re.sub('[\s+]', '', s)
    return cleaned



class PswMappingReceiveApp(ReceiveApp):
    """A simple extension to the existing Receive class
    to connect to the PreSignWidget's mapped signal (or
    an emulation thereof.  This is a bit of a hack, but by
    having pushed common receive functionality in the ReceiveApp
    class, we do not necessarily control anymore when the 
    PreSignWidget is created let alone connect to the map signal
    in time.
    """
    def __init__(self, mapped_func, builder=None):
        # ReceiveApp, in Python 2, is an old style object
        ReceiveApp.__init__(self, builder=builder)
        self.func = mapped_func
        
    def on_keydata_downloaded(self, *args, **kwargs):
        ReceiveApp.on_keydata_downloaded(self, *args, **kwargs)
        psw = self.psw
        psw.connect('map', self.func)
        if psw.get_mapped():
            self.func(psw)
    


class KeysignApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(KeysignApp, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)

        self.send_stack = None
        self.receive_stack = None
        self.send_receive_stack = None
        self.header_button_handler_id = None
        self.pre_sign_widget = None

    def on_activate(self, app):
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "app.ui")
        appwindow = 'applicationwindow1'
        builder = Gtk.Builder()
        builder.add_objects_from_file(ui_file_path, [appwindow])
        window = builder.get_object(appwindow)
        window.set_wmclass ("GNOME Keysign", "GNOME Keysign")
        window.set_title("GNOME Keysign")
        window.connect("delete-event", self.on_delete_window)
        self.headerbar = window.get_titlebar()
        self.header_button = builder.get_object("back_refresh_button")
        self.header_button.connect('clicked', self.on_header_button_clicked)
        self.internet_toggle = builder.get_object("internet_toggle")
        self.internet_toggle.connect("toggled", self.on_toggle_clicked)

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


        ## Load Send part
        self.send = SendApp()
        ss = self.send.stack
        p = ss.get_parent()
        if p:
            p.remove(ss)
        ss.connect('notify::visible-child', self.on_send_stack_switch)
        ss.connect('map', self.on_send_stack_mapped)
        klw = self.send.klw
        klw.connect("key-activated", self.on_key_activated)
        klw.connect("map", self.on_keylist_mapped)
        klw.props.margin_left = klw.props.margin_right = 15
        self.send.rb.connect('map', self.on_resultbox_mapped)
        self.send_stack = ss
        ## End of loading send part


        # Load Receive part
        self.receive = PswMappingReceiveApp(self.on_presign_mapped)
        rs = self.receive.stack

        rs.connect('notify::visible-child',
            self.on_receive_stack_switch)


        scanner = self.receive.scanner
        scanner.connect("map", self.on_scanner_mapped)
        self.receive_stack = rs


        self.send_receive_stack.add_titled(self.send_stack,
            "send_stack", "Send")
        self.send_receive_stack.add_titled(rs,
            "receive_stack", "Receive")

        # These properties must be set after the stacks has been added to the window
        # because they require a window element that "receive.ui" file doesn't provide.
        accel_group = Gtk.AccelGroup()
        window.add_accel_group(accel_group)
        self.receive.accept_button.add_accelerator("clicked", accel_group, ord('o'), Gdk.ModifierType.MOD1_MASK,
                                                   Gtk.AccelFlags.VISIBLE)
        self.receive.accept_button.set_can_default(True)

        window.show_all()
        self.add_window(window)
        reactor.run()

    def run(self, args=[]):
        super(KeysignApp, self).run()

    def on_key_activated(self, widget, key):
        log.info("Activated key %r", key)
        # Ouf, we rely on the the SendApp to have reacted to
        # the signal first, so that it sets up the keypresentwidget
        # and so that we can access it here.  If it did, however,
        # We might not be able to catch the mapped signal quickly
        # enough. So we ask the widget wether it is already mapped.
        kpw = self.send.kpw
        kpw.connect('map', self.on_keypresent_mapped)
        log.debug("KPW to wait for map: %r (%r)", kpw, kpw.get_mapped())
        if kpw.get_mapped():
            # The widget is already visible. Let's quickly call our handler
            self.on_keypresent_mapped(kpw)

        ####
        # Saving subtitle
        self.headerbar_subtitle = self.headerbar.get_subtitle()
        self.headerbar.set_subtitle("Sending {}".format(key.fpr))

    @staticmethod
    def on_delete_window(*args):
        reactor.callFromThread(reactor.stop)
        Gtk.main_quit(*args)

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
        # Here we assume that there is only two places where
        # we could have possibly pressed this button, i.e.
        # from the keypresentwidget or the result page
        log.debug("Send Headerbutton %r clicked! %r", button, args)
        current = self.send.stack.get_visible_child()
        klw = self.send.klw
        kpw = self.send.kpw
        # If we are in the keypresentwidget
        if current == kpw:
            self.send_stack.set_visible_child(klw)
            self.send.deactivate()
        # Else we are in the result page
        else:
            self.send_stack.remove(current)
            self.send.set_saved_child_visible()
            self.send.on_key_activated(None, self.send.key)

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

    def on_toggle_clicked(self, toggle):
        log.info("Internet toggled to: %s", toggle.get_active())
        self.send.set_internet_option(toggle.get_active())

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

    def on_keypresent_mapped(self, kpw):
        log.debug("keypresent becomes visible!")
        self.header_button.set_sensitive(True)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("go-previous",
            Gtk.IconSize.BUTTON))
        self.internet_toggle.hide()

    def on_scanner_mapped(self, scanner):
        log.debug("scanner becomes visible!")
        self.header_button.set_sensitive(False)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("go-previous",
            Gtk.IconSize.BUTTON))
        self.internet_toggle.hide()

    def on_presign_mapped(self, psw):
        log.debug("presign becomes visible!")
        self.header_button.set_sensitive(True)
        self.header_button.set_image(
            Gtk.Image.new_from_icon_name("go-previous",
            Gtk.IconSize.BUTTON))
        self.internet_toggle.hide()


def main(args=[]):
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(name)s (%(levelname)s): %(message)s')
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        args = []
    Gst.init(None)

    app = KeysignApp()

    def stop(signum, stackframe):
        app.quit()
        reactor.callFromThread(reactor.stop)

    signal.signal(signal.SIGINT, stop)
    app.run(args)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
