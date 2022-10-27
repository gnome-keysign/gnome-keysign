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

from .__init__ import __version__
from .gpgmeh import get_usable_keys
from .QRCode import QRImage
from .util import format_fingerprint


log = logging.getLogger(__name__)



class KeyPresentWidget(Gtk.Widget):
    """A widget for presenting a gpgmeh.Key

    It shows details of the given key and customizable data in a
    qrcode encoded in a QRImage.

    The widget takes a full key object, rather than a fingerprint,
    because it makes assumptions about the key object anyway. So
    it can as well take it directly and enable higher level controllers
    to deal with the situation that a given fingerprint, which really is
    a search string for gpg, yields multiple results.
    """

    def __new__(cls, *args, **kwargs):
        thisdir = os.path.dirname(os.path.abspath(__file__))
        builder = kwargs.pop("builder", None)
        if not builder:
            builder = Gtk.Builder()
            builder.add_objects_from_file(
                os.path.join(thisdir, 'send.ui'),
                ['box3']
                )
        log.debug("Our builder is: %r", builder)
        # The widget will very likely have a parent.
        # Gtk doesn't like so much adding a Widget to a container
        # when the widget already has been added somewhere.
        # So we get the parent widget and remove the child.
        w = builder.get_object('box3')
        parent = w.get_parent()
        if parent:
            parent.remove(w)
        w._builder = builder
        w.__class__ = cls
        return w

    def __init__(self, key, discovery_code, qrcodedata=None, builder=None):
        """
        A new KeyPresentWidget shows the string you provide as qrcodedata
        in a qrcode. If it evaluates to False, the key's fingerprint will
        be shown. That is, "OPENPGP4FPR: + fingerprint.

        :param key: a QR code will be generated using this key's fingerprint if qrcodedata is None
        :param discovery_code: the code that is displayed to the user in the send tab.
        When a user wants to receive a key he can type this code manually instead of scanning the QR code.
        :param qrcodedata: this string will be used in the QR code.
        If None, the key's fingerprint will be used.
        :param builder: not used
        """

        self.key_id_label = self._builder.get_object("keyidLabel")
        self.uids_label = self._builder.get_object("uidsLabel")
        self.fingerprint_label = self._builder.get_object("keyFingerprintLabel")
        self.qrcode_frame = self._builder.get_object("qrcode_frame")

        self.key_id_label.set_markup(
            format_fingerprint(key.fingerprint).replace('\n', '  '))
        self.uids_label.set_markup("\n".join(
                                        [GLib.markup_escape_text(uid.uid)
                                        for uid
                                        in key.uidslist]))
        self.fingerprint_label.set_markup(format_fingerprint(key.fingerprint))
        self.key_fingerprint = key.fingerprint

        self.fingerprint_label.set_markup(discovery_code)

        if not qrcodedata:
            qrcodedata = "OPENPGP4FPR:" + self.key_fingerprint
        qr = self.qrcode_frame.get_child()
        if qr:
            self.qrcode_frame.remove(self.qrcode_frame.get_child())
        self.qrcode_frame.add(QRImage(qrcodedata))
        self.qrcode_frame.show_all()


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

        key = next(iter(get_usable_keys(pattern=fpr)))
        self.key_present_page = KeyPresentWidget(key, format_fingerprint(key.fingerprint))

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
                        help="increases log verbosity for each occurrence.")
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
