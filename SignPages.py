#!/usr/bin/env python

import sys
import StringIO

try:
    from gi.repository import Gtk, GdkPixbuf
    from monkeysign.gpg import Keyring
    from qrencode import encode_scaled
except ImportError, e:
    print "A required python module is missing!\n%s" % (e,)
    sys.exit()


from QRCode import QRImage


FINGERPRINT_DEFAULT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeysPage(Gtk.VBox):

    def __init__(self):
        super(KeysPage, self).__init__()

        # create the list store to be filled up with user's gpg keys
        self.store = Gtk.ListStore(str, str, str)

        # an object representing user's keyring
        self.keyring = Keyring()

        self.keysDict = {}

        # FIXME: this should be a callback function to update the display
        # when a key is changed/deleted

        for key in self.keyring.get_keys(None, True, False).values():
            if key.invalid or key.disabled or key.expired or key.revoked:
                continue

            # get a list of UIDs for each key: Real Name (Comment) <email@address>
            uidslist = key.uidslist
            # get the key's short id
            keyid = str(key.keyid())

            if not keyid in self.keysDict:
                self.keysDict[keyid] = key

            for e in uidslist:
                uid = str(e.uid)
                # remove the comment from UID (if it exists)
                com_start = uid.find('(')
                if com_start != -1:
                    com_end = uid.find(')')
                    uid = uid[:com_start].strip() + uid[com_end+1:].strip()

                # split into user's name and email
                tokens = uid.split('<')
                name = tokens[0].strip()
                email = 'unknown'
                if len(tokens) > 1:
                    email = tokens[1].replace('>','').strip()

                # append an uid to the list store
                self.store.append((name, email, keyid))

        # create the treeView
        self.treeView = Gtk.TreeView(model=self.store)

        # setup Name column
        nameRenderer = Gtk.CellRendererText()
        nameColumn = Gtk.TreeViewColumn("Name", nameRenderer, text=0)

        # setup Email column
        emailRenderer = Gtk.CellRendererText()
        emailColumn = Gtk.TreeViewColumn("Email", emailRenderer, text=1)

        # setup Key column
        keyRenderer = Gtk.CellRendererText()
        keyColumn = Gtk.TreeViewColumn("Key", keyRenderer, text=2)

        self.treeView.append_column(nameColumn)
        self.treeView.append_column(emailColumn)
        self.treeView.append_column(keyColumn)

        # make the tree view scrollable
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.treeView)
        self.scrolled_window.set_min_content_height(200)

        self.pack_start(self.scrolled_window, True, True, 0)


class KeyPresentPage(Gtk.HBox):
    def __init__(self):
        super(KeyPresentPage, self).__init__()

        # create left side Key labels
        fingerprintMark = Gtk.Label()
        fingerprintMark.set_markup('<span size="15000">' + 'Key Fingerprint' + '</span>')

        self.fingerprintLabel = Gtk.Label()
        # FIXME: there shouldn't be a default fingerprint, instead the 'Next' button should be
        # disabled until user selects an UID
        self.fingerprintLabel.set_markup('<span size="20000">' + FINGERPRINT_DEFAULT + '</span>')

        # left vertical box
        leftVBox = Gtk.VBox(spacing=10)
        leftVBox.pack_start(fingerprintMark, False, False, 0)
        leftVBox.pack_start(self.fingerprintLabel, False, False, 0)

        self.pixbuf = None # Hold QR code in pixbuf
        self.fpr = None # The fpr of the key selected to sign with

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

    def display_key_details(self, openPgpKey):
        rawfpr = openPgpKey.fpr
        self.fpr = rawfpr
        # display a clean version of the fingerprint
        fpr = ""
        for i in xrange(0, len(rawfpr), 4):

            fpr += rawfpr[i:i+4]
            if i != 0 and (i+4) % 20 == 0:
                fpr += "\n"
            else:
                fpr += " "

        fpr = fpr.rstrip()
        self.fingerprintLabel.set_markup('<span size="20000">' + fpr + '</span>')

        # draw qr code for this fingerprint
        self.draw_qrcode()


    def draw_qrcode(self):
        data = self.fpr
        if data is not None:
            self.qrcode.draw_qrcode(data)
        else:
            self.qrcode.set_from_icon_name("gtk-dialog-error", Gtk.IconSize.DIALOG)

    def create_qrcode(self, fpr):
        box = self.rightVBox.get_allocation()
        if box.width < box.height:
            size = box.width - 30
        else:
            size = box.height - 30
        version, width, image = encode_scaled('OPENPGP4FPR:'+fpr,size,0,1,2,True)
        return image

    def image_to_pixbuf(self, image):
        # convert PIL image instance to Pixbuf
        fd = StringIO.StringIO()
        image.save(fd, "ppm")
        contents = fd.getvalue()
        fd.close()
        loader = GdkPixbuf.PixbufLoader.new_with_type('pnm')
        loader.write(contents)
        pixbuf = loader.get_pixbuf()
        loader.close()
        return pixbuf


class KeyDetailsPage(Gtk.VBox):

    def __init__(self):
        super(KeyDetailsPage, self).__init__()
        self.set_spacing(10)

        uidsLabel = Gtk.Label()
        uidsLabel.set_text("UIDs")

        # this will later be populated with uids when user selects a key
        self.uidsBox = Gtk.HBox(spacing=5)

        expireLabel = Gtk.Label()
        expireLabel.set_text("Expires 0000-00-00")

        signaturesLabel = Gtk.Label()
        signaturesLabel.set_text("Signatures")

        # this will also be populated later
        signaturesBox = Gtk.HBox(spacing=5)

        self.pack_start(uidsLabel, False, False, 0)
        self.pack_start(self.uidsBox, True, True, 0)
        self.pack_start(expireLabel, False, False, 0)
        self.pack_start(signaturesLabel, False, False, 0)
        self.pack_start(signaturesBox, True, True, 0)
