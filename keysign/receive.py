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
from textwrap import dedent
from urllib.parse import unquote

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from gi.repository import Gdk
gi.require_version('Gst', '1.0')
from gi.repository import Gst
if __name__ == "__main__":
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks
from wormhole.errors import WrongPasswordError, LonelyError

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


from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .discover import Discover
from .errors import NoBluezDbus, UnpoweredAdapter, NoAdapter
from .gpgmeh import openpgpkey_from_data, local_sign_keydata, GPGRuntimeError
from .i18n import _
from .keyfprscan import KeyFprScanWidget
from .keyconfirm import PreSignWidget
from .util import sign_keydata_and_send, fix_infobar, get_local_bt_address

log = logging.getLogger(__name__)


def remove_whitespace(s):
    cleaned = re.sub('[\s+]', '', s)
    return cleaned


class ReceiveApp:
    def __init__(self, builder=None):
        self.psw = None
        self.discovery = None
        self.log = logging.getLogger(__name__)

        widget_name = "receive_stack"
        if not builder:
            ui_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "receive.ui")
            builder = Gtk.Builder()
            builder.add_objects_from_file(ui_file,
                [widget_name, 'confirm-button-image'])

        self.accept_button = builder.get_object("confirm_sign_button")

        old_scanner = builder.get_object("scanner_widget")
        old_scanner_parent = old_scanner.get_parent()

        scanner = KeyFprScanWidget() #builder=builder)
        scanner.connect("changed", self.on_code_changed)
        scanner.connect("barcode", self.on_barcode)

        if old_scanner_parent:
            old_scanner_parent.remove(old_scanner)
            # Hm. If we don't have an old parent, we never get to see
            # the newly created scanner. Weird.
            old_scanner_parent.add(scanner)

        receive_stack = builder.get_object(widget_name)
        # It needs to be show()n so that it can be made visible
        scanner.show()
        # FIXME: Use "stack_scanner_child" or so as identification
        # for the stack's scanner child to make it visible when the
        # app starts
        # receive_stack.set_visible_child(old_scanner_parent)
        self.scanner = scanner
        self.stack = receive_stack

        DRAG_ACTION = Gdk.DragAction.COPY
        self.scanner.drag_dest_set(Gtk.DestDefaults.ALL, [], DRAG_ACTION)
        self.scanner.drag_dest_set_target_list(None)
        self.scanner.drag_dest_add_text_targets()
        self.scanner.drag_dest_add_uri_targets()
        self.scanner.connect("drag-data-received", self.on_drag_data_received)

        self.discovery = AvahiKeysignDiscoveryWithMac()
        ib = builder.get_object('infobar_discovery')
        fix_infobar(ib)
        self.discovery.connect('list-changed', self.on_list_changed, ib)

        self.discover = None
        self.rb = builder.get_object('box50')
        self.result_label = builder.get_object("error_download_label")
        self.cancel_button = builder.get_object("cancel_download_button")
        self.redo_button = builder.get_object("redo_download_button")
        self.redo_button.connect("clicked", self.on_redo_button_clicked)
        self.cancel_button.connect("clicked", self.on_cancel_button_clicked)
        # Clear the "downloading" label
        builder.get_object("label10").set_label("")

        self.bt_usable = False

        # We call this in async because it can take several seconds to complete and we don't want
        # to stall the UI boot. Also we don't care about having this information immediately.
        threads.deferToThread(self.check_bt_availability)

    def on_drag_data_received(self, widget, drag_context, x, y, data, info, time):
        log.info("recv: Drag data rcvd: %s (%s) %s", data, data.get_text(), info)
        drag_data = data.get_text()
        dragged_data = unquote(drag_data)
        if dragged_data.startswith("file://"):
            filename = dragged_data[7:].strip('\r\n\x00')  # remove file://, \r\n and NULL
            keydata = open(filename, 'br').read()

        elif dragged_data.startswith("-----BEGIN PGP PUBLIC KEY BLOCK-----"):
            # We assume a raw (well, armored) key to be passed
            keydata = dragged_data

        else:
            log.warning("We got a drag with neither file:// nor ----: %s", drag_data)
            keydata = dragged_data

        self.on_keydata_downloaded(keydata)

    def on_redo_button_clicked(self, button):
        log.info("redo pressed")
        self.stack.remove(self.rb)
        self.discover.start()

    def on_cancel_button_clicked(self, button):
        log.info("cancel pressed")
        self.stack.remove(self.rb)

    def check_bt_availability(self):
        try:
            if get_local_bt_address():
                self.bt_usable = True
                log.debug("A working Bluetooth seems to be available")
            else:
                self.bt_usable = False
                log.debug("There is no usable Bluetooth")
        except NoBluezDbus as e:
            log.debug("Bluetooth service seems to be unavailable: %s", e)
        except NoAdapter as e:
            log.debug("Bluetooth adapter is not available: %s", e)
        except UnpoweredAdapter as e:
            log.debug("Bluetooth adapter is turned off: %s", e)

    def on_keydata_downloaded(self, keydata, pixbuf=None):
        log.debug("Downloaded keydata of length %d: %s", len(keydata), keydata[:50])
        key = openpgpkey_from_data(keydata)
        psw = PreSignWidget(key, pixbuf)
        psw.connect('sign-key-confirmed',
            self.on_sign_key_confirmed, keydata)
        self.stack.add_titled(psw, "presign", _("Sign Key"))
        psw.set_name("presign")
        psw.show()
        self.psw = psw
        self.stack.set_visible_child(self.psw)

    def on_message_received(self, key_data, success=True, message=None):
        if success:
            self.log.debug("message received")
            try:
                self.on_keydata_downloaded(key_data)
            except ValueError as ve:
                log.error(ve.args[0])
        else:
            self.stack.add(self.rb)
            self.result_label.set_label(dedent(message.__doc__))
            self.stack.set_visible_child(self.rb)

    def on_code_changed(self, scanner, entry):
        self.log.debug("Entry changed %r: %r", scanner, entry)
        text = entry.get_text()
        self._receive(text)

    def on_barcode(self, scanner, barcode, gstmessage, pixbuf):
        self.log.debug("Scanned barcode %r", barcode)
        self._receive(barcode)

    @inlineCallbacks
    def _receive(self, code):
        if self.discover:
            self.discover.stop()
        self.discover = Discover(code, self.discovery)
        msg_tuple = yield self.discover.start()
        key_data, success, message = msg_tuple
        if message == WrongPasswordError or message == LonelyError:
            # If a wrong password has been provided or we closed the connection
            # before a transfer. We do not display that to the user
            log.info("Waiting for another code")
            pass
        else:
            self.on_message_received(key_data, success, message)

    def on_sign_key_confirmed(self, keyPreSignWidget, key, keydata):
        self.log.debug ("Sign key confirmed! %r", key)
        # We need to prevent tmpfiles from going out of
        # scope too early so that they don't get deleted
        try:
            tmpfiles_plaintext = list(sign_keydata_and_send(keydata))
        except GPGRuntimeError as e:
            self.log.exception("Something went wrong with signing the key")
            keyPreSignWidget.infobar_success.hide()
            keyPreSignWidget.infobar_errors.show(e)
        else:
            self.log.debug("sign keydata result: %r", tmpfiles_plaintext)
            # This is unzipping the list of tuples, e.g. [(1,2), (3,4)] becomes [(1,3), (2,4)]
            self.tmpfiles, plaintexts = zip(*tmpfiles_plaintext)

            keyPreSignWidget.infobar_errors.hide()
            keyPreSignWidget.infobar_success.show()

            def import_clicked(button):
                self.log.info("Import clicked")
                local_sign_keydata(keydata)
            keyPreSignWidget.infobar_import_button.connect("clicked", import_clicked)

            def save_as_clicked(button):
                self.log.info("Save as clicked")
                dialog = Gtk.FileChooserDialog(_("Select file for saving"),
                    self.get_toplevel(),
                    Gtk.FileChooserAction.SAVE,
                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
                )
                response = dialog.run()
                if response == Gtk.ResponseType.OK:
                    filename = dialog.get_filename()
                    self.log.info("Saving file to: %r", filename)
                    with open(filename, 'wb') as f:
                        for p in plaintexts:
                            f.write(p)
                        for sigfile in self.tmpfiles:
                            pass
                            # Hrm. Those are the encrypted files, I think.
                            # We probably want to offer the plaintext versions, though
                            #f.write(open(sigfile, 'r').read())
                else:
                    self.log.info("Not saving file: %r", response)
                dialog.destroy()

            keyPreSignWidget.infobar_save_as_button.connect("clicked", save_as_clicked)

            # After the user has signed, we switch back to the scanner,
            # because currently, there is not much to do on the
            # key confirmation page.
            log.debug ("Signed the key: %r", self.tmpfiles)
            # self.stack.set_visible_child_name("scanner")

    def on_list_changed(self, discovery, number, userdata):
        """We show an infobar if we can only receive with Avahi and
        there are zero nearby servers"""
        ib = userdata
        if number == 0 and not self.bt_usable:
            ib.show()
        elif ib.is_visible():
            ib.hide()


class App(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.log = logging.getLogger(__name__)

    def on_activate(self, app):
        ui_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "receive.ui")
        builder = Gtk.Builder.new_from_file(ui_file)

        window = Gtk.ApplicationWindow()
        window.connect("delete-event", self.on_delete_window)
        window.set_title(_("Receive"))
        # window.set_size_request(600, 400)
        #window = self.builder.get_object("appwindow")
        
        self.receive = ReceiveApp(builder)
        receive_stack = self.receive.stack

        window.add(receive_stack)
        window.show_all()
        self.add_window(window)

    @staticmethod
    def on_delete_window(*args):
        reactor.callFromThread(reactor.stop)


def main(args=[]):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        args = []
    Gst.init(None)

    app = App()
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT,
                                  lambda *args: reactor.callFromThread(reactor.stop), None)
    except AttributeError:
        pass
    reactor.registerGApplication(app)
    reactor.run()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
