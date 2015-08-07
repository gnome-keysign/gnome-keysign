#!/usr/bin/env python
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
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

from itertools import islice
import logging
import sys
import StringIO

from gi.repository import GObject, Gtk, GLib, GdkPixbuf
from monkeysign.gpg import Keyring
from qrencode import encode_scaled

from datetime import datetime

from compat import gtkbutton
from QRCode import QRImage
from scan_barcode import BarcodeReaderGTK


log = logging.getLogger()


def parse_sig_list(text):
    '''Parses GnuPG's signature list (i.e. list-sigs)
    
    The format is described in the GnuPG man page'''
    sigslist = []
    for block in text.split("\n"):
        if block.startswith("sig"):
            record = block.split(":")
            log.debug("sig record (%d) %s", len(record), record)
            keyid, timestamp, uid = record[4], record[5], record[9]
            sigslist.append((keyid, timestamp, uid))

    return sigslist

# This is a cache for a keyring object, so that we do not need
# to create a new object every single time we parse signatures
_keyring = None
def signatures_for_keyid(keyid, keyring=None):
    '''Returns the list of signatures for a given key id
    
    This will call out to GnuPG list-sigs, using Monkeysign,
    and parse the resulting string into a list of signatures.
    
    A default Keyring will be used unless you pass an instance
    as keyring argument.
    '''
    # Retrieving a cached instance of a keyring,
    # unless we were being passed a keyring
    global _keyring
    if keyring is not None:
        kr = keyring
    else:
        if _keyring is None:
            _keyring = Keyring()
        kr = _keyring

    # FIXME: this would be better if it was done in monkeysign
    kr.context.call_command(['list-sigs', keyid])
    siglist = parse_sig_list(kr.context.stdout)

    return siglist



class KeyPresentPage(Gtk.HBox):
    def __init__(self, fpr=None):
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

        self.qrcode = QRImage()
        self.qrcode.props.margin = 10

        # right vertical box
        self.rightVBox = Gtk.VBox(spacing=10)
        self.rightVBox.pack_start(qrcodeLabel, False, False, 0)
        self.rightVBox.pack_start(self.qrcode, True, True, 0)

        self.pack_start(leftVBox, True, True, 0)
        self.pack_start(self.rightVBox, True, True, 0)
        
        if self.fpr:
            self.setup_fingerprint_widget(self.fpr)


    def display_fingerprint_qr_page(self, openPgpKey=None):
        assert openPgpKey or self.fpr

        rawfpr = openPgpKey.fpr if openPgpKey else self.fpr
        self.fpr = rawfpr
        self.setup_fingerprint_widget(self.fpr)

        # draw qr code for this fingerprint
        self.draw_qrcode()


    def setup_fingerprint_widget(self, fingerprint):
        '''The purpose of this function is to populate the label holding
        the fingerprint with a formatted version.
        '''
        fpr = ""
        for i in xrange(0, len(fingerprint), 4):

            fpr += fingerprint[i:i+4]
            if i != 0 and (i+4) % 20 == 0:
                fpr += "\n"
            else:
                fpr += " "

        fpr = fpr.rstrip()
        self.fingerprintLabel.set_markup('<span size="20000">' + fpr + '</span>')


    def draw_qrcode(self):
        assert self.fpr
        data = 'OPENPGP4FPR:' + self.fpr
        self.qrcode.data = data



class KeyDetailsPage(Gtk.VBox):

    def __init__(self):
        super(KeyDetailsPage, self).__init__()
        self.set_spacing(10)
        self.log = logging.getLogger()

        # FIXME: this should be moved to KeySignSection
        self.keyring = Keyring()

        uidsLabel = Gtk.Label()
        uidsLabel.set_text("UIDs")

        # this will later be populated with uids when user selects a key
        self.uidsBox = Gtk.VBox(spacing=5)

        self.expireLabel = Gtk.Label()
        self.expireLabel.set_text("Expires 0000-00-00")

        self.signatures_label = signaturesLabel = Gtk.Label()
        signaturesLabel.set_text("Signatures")

        # this will also be populated later
        self.signaturesBox = Gtk.VBox(spacing=5)

        self.pack_start(uidsLabel, False, False, 0)
        self.pack_start(self.uidsBox, True, True, 0)
        self.pack_start(self.expireLabel, False, False, 0)
        self.pack_start(signaturesLabel, False, False, 0)
        self.pack_start(self.signaturesBox, True, True, 0)


    def display_uids_signatures_page(self, openPgpKey):

        # destroy previous uids
        for uid in self.uidsBox.get_children():
            self.uidsBox.remove(uid)
        for sig in self.signaturesBox.get_children():
            self.signaturesBox.remove(sig)

        # display a list of uids
        labels = []
        for uid in openPgpKey.uidslist:
            label = Gtk.Label(str(uid.uid))
            label.set_line_wrap(True)
            labels.append(label)

        for label in labels:
            self.uidsBox.pack_start(label, False, False, 0)
            label.show()

        try:
            exp_date = datetime.fromtimestamp(float(openPgpKey.expiry))
            expiry = "Expires {:%Y-%m-%d %H:%M:%S}".format(exp_date)
        except ValueError, e:
            expiry = "No expiration date"

        self.expireLabel.set_markup(expiry)
        
        
        ### Set up signatures
        keyid = str(openPgpKey.keyid())
        sigslist = signatures_for_keyid(keyid)

        SHOW_SIGNATURES = False
        if not SHOW_SIGNATURES:
            self.signatures_label.hide()
        else:
            self.signatures_label.show()
            sorted_sigslist = sorted(sigslist,
                                     key=lambda signature:signature[1],
                                     reverse=True)
            for (keyid,timestamp,uid) in islice(sorted_sigslist, 10):
                sigLabel = Gtk.Label()
                date = datetime.fromtimestamp(float(timestamp))
                sigLabel.set_markup(str(keyid) + "\t\t" + date.ctime())
                sigLabel.set_line_wrap(True)
    
                self.signaturesBox.pack_start(sigLabel, False, False, 0)
                sigLabel.show()
            
        sigLabel = Gtk.Label()
        sigLabel.set_markup("%d signatures" % len(sigslist))
        sigLabel.set_line_wrap(True)
        self.signaturesBox.pack_start(sigLabel, False, False, 0)
        sigLabel.show()


# Pages for "Get Key" Tab

class ScanFingerprintPage(Gtk.HBox):

    def __init__(self):
        super(ScanFingerprintPage, self).__init__()
        self.set_spacing(10)

        # set up labels
        leftLabel = Gtk.Label()
        leftLabel.set_markup('Type fingerprint')
        rightLabel = Gtk.Label()
        rightLabel.set_markup('... or scan QR code')

        # set up text editor
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()

        # set up scrolled window
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.add(self.textview)

        # set up webcam frame
        self.scanFrame = Gtk.Frame(label='QR Scanner')
        self.scanFrame = BarcodeReaderGTK()
        self.scanFrame.set_size_request(150,150)
        self.scanFrame.show()

        # set up load button: this will be used to load a qr code from a file
        self.loadButton = Gtk.Button('Open Image')
        self.loadButton.set_image(Gtk.Image.new_from_icon_name('gtk-open', Gtk.IconSize.BUTTON))
        self.loadButton.connect('clicked', self.on_loadbutton_clicked)
        self.loadButton.set_always_show_image(True)

        # set up left box
        leftBox = Gtk.VBox(spacing=10)
        leftBox.pack_start(leftLabel, False, False, 0)
        leftBox.pack_start(scrolledwindow, True, True, 0)

        # set up right box
        rightBox = Gtk.VBox(spacing=10)
        rightBox.pack_start(rightLabel, False, False, 0)
        rightBox.pack_start(self.scanFrame, True, True, 0)
        rightBox.pack_start(self.loadButton, False, False, 0)

        # pack up
        self.pack_start(leftBox, True, True, 0)
        self.pack_start(rightBox, True, True, 0)


    def get_text_from_textview(self):
        '''Returns the contents of the fingerprint
        input widget.  Note that this function does
        not format or validate anything.
        '''
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        raw_text = self.textbuffer.get_text(start_iter, end_iter, False)
        
        return raw_text


    def on_loadbutton_clicked(self, *args, **kwargs):
        print("load")


class SignKeyPage(Gtk.VBox):

    def __init__(self):
        super(SignKeyPage, self).__init__()
        self.set_spacing(5)

        self.mainLabel = Gtk.Label()
        self.mainLabel.set_line_wrap(True)

        self.pack_start(self.mainLabel, False, False, 0)


    def display_downloaded_key(self, key, scanned_fpr):

        # FIXME: If the two fingerprints don't match, the button
        # should be disabled
        key_text = GLib.markup_escape_text(str(key))

        markup = """\


Signing the following key

<b>{0}</b>

Press 'Next' if you have checked the ID of the person
and you want to sign all UIDs on this key.""".format(key_text)

        self.mainLabel.set_markup(markup)
        self.mainLabel.show()


class PostSignPage(Gtk.VBox):

    def __init__(self):
        super(PostSignPage, self).__init__()
        self.set_spacing(10)

        # setup the label
        signedLabel = Gtk.Label()
        signedLabel.set_text('The key was signed and an email was sent to key owner! What next?')

        # setup the buttons
        sendBackButton = Gtk.Button('   Resend email   ')
        sendBackButton.set_image(Gtk.Image.new_from_icon_name("gtk-network", Gtk.IconSize.BUTTON))
        sendBackButton.set_always_show_image(True)
        sendBackButton.set_halign(Gtk.Align.CENTER)

        saveButton = Gtk.Button(' Save key locally ')
        saveButton.set_image(Gtk.Image.new_from_icon_name("gtk-save", Gtk.IconSize.BUTTON))
        saveButton.set_always_show_image(True)
        saveButton.set_halign(Gtk.Align.CENTER)

        emailButton = Gtk.Button('Revoke signature')
        emailButton.set_image(Gtk.Image.new_from_icon_name("gtk-clear", Gtk.IconSize.BUTTON))
        emailButton.set_always_show_image(True)
        emailButton.set_halign(Gtk.Align.CENTER)

        # pack them into a container for alignment
        container = Gtk.VBox(spacing=3)
        container.pack_start(signedLabel, False, False, 5)
        container.pack_start(sendBackButton, False, False, 0)
        container.pack_start(saveButton, False, False, 0)
        container.pack_start(emailButton, False, False, 0)
        container.set_valign(Gtk.Align.CENTER)

        self.pack_start(container, True, False, 0)
