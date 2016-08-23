#!/usr/bin/env python
# encoding: utf-8
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
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

import signal
import sys
import argparse
import logging
import os

from gi.repository import Gtk, GLib
from gi.repository import GObject

if  __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')

from .__init__ import __version__
from .gpgmh import get_public_key_data
from .gpgmh import get_usable_keys
from .QRCode import QRImage
from .util import mac_verify, mac_generate
from .util import format_fingerprint



log = logging.getLogger(__name__)


class KeyPresentPage(Gtk.HBox):
    def __init__(self, fpr, qrcodedata = None):
        super(KeyPresentPage, self).__init__()

        # create left side Key labels
        leftTopLabel = Gtk.Label()
        leftTopLabel.set_markup('<span size="15000">' + 'Key Fingerprint' + '</span>')

        self.fingerprintLabel = Gtk.Label()
        self.fingerprintLabel.set_selectable(True)

        # left vertical box
        leftVBox = Gtk.VBox(spacing=10)
        leftVBox.pack_start(leftTopLabel, False, False, 0)
        leftVBox.pack_start(self.fingerprintLabel, False, False, 0)

        self.pixbuf = None # Hold QR code in pixbuf
        self.fpr = fpr # The fpr of the key selected to sign with

        # display QR code on the right side
        qrcodeLabel = Gtk.Label()
        qrcodeLabel.set_markup('<span size="15000">' + 'Fingerprint QR code' + '</span>')

        if not qrcodedata:
            qrcodedata = self.generate_qrcode_data()
        self.qrcode = QRImage(qrcodedata)
        self.qrcode.props.margin = 10


        # right vertical box
        self.rightVBox = Gtk.VBox(spacing=10)
        self.rightVBox.pack_start(qrcodeLabel, False, False, 0)
        self.rightVBox.pack_start(self.qrcode, True, True, 0)

        self.pack_start(leftVBox, True, True, 0)
        self.pack_start(self.rightVBox, True, True, 0)

        self.setup_fingerprint_widget(self.fpr)


    def setup_fingerprint_widget(self, fingerprint):
        '''The purpose of this function is to populate the label holding
        the fingerprint with a formatted version.
        '''
        fpr = format_fingerprint(fingerprint)
        self.fingerprintLabel.set_markup('<span size="20000">' + fpr + '</span>')


    def generate_qrcode_data(self):
        assert self.fpr
        fingerprint = self.fpr
        data = 'OPENPGP4FPR:' + fingerprint
        # FIXME: okay, this is really bad.
        # We should really try to get the keydata from another
        # channel. There is key-selected signal. Maybe we can use that.
        keydata = get_public_key_data(fingerprint)
        mac = mac_generate(fingerprint, keydata)
        # FIXME: We probably want to urlencode the thing...
        data += '#MAC=%s' % mac
        # we call upper to made the barcode more efficient
        data = data.upper()
        log.info("Shoving %r to the QRCode", data)
        return data




class KeyPresentWidget(Gtk.Widget):

    def __new__(cls, *args, **kwargs):
        thisdir = os.path.dirname(os.path.abspath(__file__))
        builder = Gtk.Builder.new_from_file(os.path.join(thisdir, 'send.ui'))
        stack = builder.get_object('stack2')
        stack.set_visible_child_name("page1")
        # Hrm. That doesn't seem to work, but I don't know why.
        #stack = builder.get_object('box3')
        stack._builder = builder
        stack.__class__ = cls
        return stack
    
    def __init__(self, fingerprint, qrcodedata=None):
        key = get_usable_keys(pattern=fingerprint)[0]
        self.key_id_label = self._builder.get_object("keyidLabel")
        self.uids_label = self._builder.get_object("uidsLabel")
        self.fingerprint_label = self._builder.get_object("keyFingerprintLabel")
        self.qrcode_frame = self._builder.get_object("qrcode_frame")

        self.key_id_label.set_markup(key.fingerprint[-8:])
        self.uids_label.set_markup("\n".join(
                                        [GLib.markup_escape_text("{}".format(uid))
                                        for uid
                                        in key.uidslist]))
        self.fingerprint_label.set_markup(format_fingerprint(key.fingerprint))
        if not qrcodedata:
            qrcodedata = key.fingerprint
        self.qrcode_frame.add(QRImage(qrcodedata))







class KeyPresent(Gtk.Application):
    """A demo application showing how to display sufficient details
    about a key such that it can be sent securely.
    
    Note that the main purpose is to enable secure transfer, not
    reviewing key details.  As such, the implementation might change
    a lot, depending on the method of secure transfer.
    """
    def __init__(self, *args, **kwargs):
        #super(Keys, self).__init__(*args, **kwargs)
        Gtk.Application.__init__(
            self, application_id="org.gnome.keysign.keypresent")
        self.connect("activate", self.on_activate)
        self.connect("startup", self.on_startup)

        self.log = logging.getLogger(__name__)

        self.key_present_page = None


    def on_quit(self, app, param=None):
        self.quit()


    def on_startup(self, app):
        self.log.info("Startup")
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title ("Keysign - Key")
        self.window.add(self.key_present_page)


    def on_activate(self, app):
        self.log.info("Activate!")
        #self.window = Gtk.ApplicationWindow(application=app)

        self.window.show_all()
        # In case the user runs the application a second time,
        # we raise the existing window.
        self.window.present()


    def run(self, args):
        log.debug("running: %s", args)
        fpr = args

        self.key_present_page = KeyPresentPage(fpr=fpr)

        super(KeyPresent, self).run()


def parse_command_line(argv):
    """Parse command line argument. See -h option

    :param argv: arguments on the command line must include caller file name.
    """
    formatter_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description='Auxiliary helper program '+
                                                 'to present a key',
                                     formatter_class=formatter_class)
    parser.add_argument("--version", action="version",
                        version="%(prog)s {}".format(__version__))
    parser.add_argument("-v", "--verbose", dest="verbose_count",
                        action="count", default=0,
                        help="increases log verbosity for each occurence.")
    #parser.add_argument("-g", "--gpg",
    #                    action="store_true", default=False,
    #                    help="Use local GnuPG Keyring instead of file.")
    #parser.add_argument('-o', metavar="output",
    #                    type=argparse.FileType('w'), default=sys.stdout,
    #                    help="redirect output to a file")
    #parser.add_argument('file', help='File to read keydata from ' +
    #                                 '(or KeyID if --gpg is given)')
    parser.add_argument('fpr', help='The fingerprint of the key to transfer')
    ## nargs='+', # argparse.REMAINDER,
    #parser.add_argument('input', metavar="input",
    ## nargs='+', # argparse.REMAINDER,
    #help="input if any...")
    arguments = parser.parse_args(argv[1:])
    # Sets log level to WARN going more verbose for each new -v.
    log.setLevel(max(3 - arguments.verbose_count, 0) * 10)
    return arguments


def main(args=sys.argv):
    """This is an example program of how to use the PresentKey widget"""
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                        format='%(name)s (%(levelname)s): %(message)s')
    try:
        arguments = parse_command_line(args)
        
        #if arguments.gpg:
        #    keydata = export_keydata(next(get_usable_keys(keyid)))
        #else:
        #    keydata = open(arguments.file, 'r').read()
        fpr = arguments.fpr

        app = KeyPresent()
        try:
            GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
        except AttributeError:
            pass
    
        exit_status = app.run(fpr)
    
        return exit_status

        
    finally:
        logging.shutdown()

if __name__ == "__main__":
    sys.exit(main())
