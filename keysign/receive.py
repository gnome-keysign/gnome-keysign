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


from .avahidiscovery import AvahiKeysignDiscovery
from .keyfprscan import KeyFprScanWidget
from .keyconfirm import PreSignWidget
from .gpgmh import openpgpkey_from_data
from .util import sign_keydata_and_send

log = logging.getLogger(__name__)

def remove_whitespace(s):
    cleaned = re.sub('[\s+]', '', s)
    return cleaned


class ReceiveApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(ReceiveApp, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.scanner = None
        self.psw = None
        self.discovery = None
        
        self.log = logging.getLogger(__name__)

    def on_activate(self, app):
        ui_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "receive.ui")
        builder = Gtk.Builder.new_from_file(ui_file)

        window = Gtk.ApplicationWindow()
        window.set_title("Receive")
        # window.set_size_request(600, 400)
        #window = self.builder.get_object("appwindow")
        
        scanner = KeyFprScanWidget()
        scanner.connect("changed", self.on_scanner_changed)
        scanner.connect("barcode", self.on_barcode)

        receive_stack = builder.get_object("receive_stack")
        # FIXME: We should probaly ask the ScannerWidget what it identifies itself as
        receive_stack.remove(receive_stack.get_child_by_name("scanner"))
        receive_stack.add_titled(scanner, "scanner", "Scan Barcode")
        # It needs to be show()n so that it can be made visible
        scanner.show()
        receive_stack.set_visible_child(scanner);

        window.add(receive_stack)
        window.show_all()
        self.add_window(window)

        self.discovery = AvahiKeysignDiscovery()

    def on_keydata_downloaded(self, keydata, pixbuf=None):
        key = openpgpkey_from_data(keydata)
        self.psw = PreSignWidget(key, pixbuf)
        self.psw.connect('sign-key-confirmed', self.on_sign_key_confirmed, keydata)
        self.stack.add_titled(self.psw, "presign", "Sign Key")
        self.psw.show()
        self.stack.set_visible_child(self.psw)

    def on_scanner_changed(self, scanner, entry):
        text = entry.get_text()
        keydata = self.discovery.find_key(text)
        if keydata:
            self.on_keydata_downloaded(keydata)

    def on_barcode(self, scanner, barcode, gstmessage, pixbuf):
        self.log.debug("Scanned barcode %r", barcode)
        keydata = self.discovery.find_key(barcode)
        if keydata:
            self.on_keydata_downloaded(keydata, pixbuf)

    def on_sign_key_confirmed(self, keyPreSignWidget, key, keydata):
        self.log.debug ("Sign key confirmed! %r", key)
        # We need to prevent tmpfiles from going out of
        # scope too early so that they don't get deleted
        self.tmpfiles = list(
            sign_keydata_and_send(keydata))

    def run(self, args):
        if not args:
            args = [""]
        super(ReceiveApp, self).run()


def main(args):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        args = []
    Gst.init()

    app = ReceiveApp()
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        pass
    app.run(args)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
