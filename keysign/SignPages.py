#!/usr/bin/env python
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
#    Copyright 2014, 2015 Tobias Mueller <muelli@cryptobitch.de>
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

from gi.repository import GObject, Gtk, GLib

from datetime import datetime

from compat import gtkbutton
from QRCode import QRImage
from scan_barcode import BarcodeReaderGTK, ScalingImage


from .util import mac_verify, mac_generate

from .gpgmh import get_public_key_data
from .gpgmh import signatures_for_keyid


log = logging.getLogger(__name__)





class KeyPresentPage(Gtk.HBox):
    def __init__(self, fpr):
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

        self.setup_fingerprint_widget(self.fpr)
        self.draw_qrcode()


    def setup_fingerprint_widget(self, fingerprint):
        '''The purpose of this function is to populate the label holding
        the fingerprint with a formatted version.
        '''
        fpr = ""
        for i in range(0, len(fingerprint), 4):

            fpr += fingerprint[i:i+4]
            if i != 0 and (i+4) % 20 == 0:
                fpr += "\n"
            else:
                fpr += " "

        fpr = fpr.rstrip()
        self.fingerprintLabel.set_markup('<span size="20000">' + fpr + '</span>')


    def draw_qrcode(self):
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
        self.qrcode.data = data



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


class SignKeyPage(Gtk.HBox):

    def __init__(self):
        super(SignKeyPage, self).__init__()
        self.set_spacing(5)

        self.mainLabel = Gtk.Label()
        self.mainLabel.set_line_wrap(True)

        self.pack_start(self.mainLabel, False, True, 0)
        
        self.barcode_image = ScalingImage()
        self.pack_start(self.barcode_image, True, True, 0)


    def display_downloaded_key(self, key, scanned_fpr, image):

        # FIXME: If the two fingerprints don't match, the button
        # should be disabled
        key_text = GLib.markup_escape_text("{}".format(key))

        markup = """\


Signing the following key

<b>{0}</b>

Press 'Next' if you have checked the ID of the person
and you want to sign all UIDs on this key.""".format(key_text)

        self.mainLabel.set_markup(markup)
        self.mainLabel.show()
        
        # The image *can* be None, if the user typed the fingerprint manually,
        # e.g. did not use Web cam to scan a QR-code
        if image:
            self.barcode_image.set_from_pixbuf(image)


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
