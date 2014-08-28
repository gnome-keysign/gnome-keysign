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

from datetime import datetime

from scan_barcode import BarcodeReaderGTK

FINGERPRINT_DEFAULT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeysPage(Gtk.VBox):

    def __init__(self, keySection):
        super(KeysPage, self).__init__()

        # pass a reference to KeySignSection in order to access its widgets
        self.keySection = keySection

        # set up the list store to be filled up with user's gpg keys
        self.store = Gtk.ListStore(str, str, str)

        # FIXME: this should be moved to KeySignSection
        self.keyring = Keyring() # the user's keyring

        self.keysDict = {}

        # FIXME: this should be a callback function to update the display
        # when a key is changed/deleted
        for key in self.keyring.get_keys(None, True, False).values():
            if key.invalid or key.disabled or key.expired or key.revoked:
                continue

            uidslist = key.uidslist #UIDs: Real Name (Comment) <email@address>
            keyid = str(key.keyid()) # the key's short id

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

                self.store.append((name, email, keyid))

        # create the tree view
        self.treeView = Gtk.TreeView(model=self.store)

        # setup 'Name' column
        nameRenderer = Gtk.CellRendererText()
        nameColumn = Gtk.TreeViewColumn("Name", nameRenderer, text=0)

        # setup 'Email' column
        emailRenderer = Gtk.CellRendererText()
        emailColumn = Gtk.TreeViewColumn("Email", emailRenderer, text=1)

        # setup 'Key' column
        keyRenderer = Gtk.CellRendererText()
        keyColumn = Gtk.TreeViewColumn("Key", keyRenderer, text=2)

        self.treeView.append_column(nameColumn)
        self.treeView.append_column(emailColumn)
        self.treeView.append_column(keyColumn)

        # make the tree view resposive to single click selection
        self.treeView.get_selection().connect('changed', self.on_selection_changed)

        # make the tree view scrollable
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.treeView)
        self.scrolled_window.set_min_content_height(200)

        self.pack_start(self.scrolled_window, True, True, 0)

    def on_selection_changed(self, *args):
        self.keySection.nextButton.set_sensitive(True)


class KeyPresentPage(Gtk.HBox):
    def __init__(self):
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
        self.fpr = None # The fpr of the key selected to sign with

        # display QR code on the right side
        rightTopLabel = Gtk.Label()
        rightTopLabel.set_markup('<span size="15000">' + 'Fingerprint QR code' + '</span>')

        self.qrcode = Gtk.Image()
        self.qrcode.props.margin = 10

        scroll_win = Gtk.ScrolledWindow()
        scroll_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_win.add_with_viewport(self.qrcode)

        # right vertical box
        self.rightVBox = Gtk.VBox(spacing=10)
        self.rightVBox.pack_start(rightTopLabel, False, False, 0)
        self.rightVBox.pack_start(scroll_win, True, True, 0)

        self.rightVBox.connect("size-allocate", self.expose_event)
        self.last_allocation = self.rightVBox.get_allocation()

        self.pack_start(leftVBox, True, True, 0)
        self.pack_start(self.rightVBox, True, True, 0)

    def display_fingerprint_qr_page(self, openPgpKey):
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

    def expose_event(self, widget, event):
        # when window is resized, regenerate the QR code
        if self.rightVBox.get_allocation() != self.last_allocation:
            self.last_allocation = self.rightVBox.get_allocation()
            self.draw_qrcode()

    def draw_qrcode(self):
        if self.fpr is not None:
            self.pixbuf = self.image_to_pixbuf(self.create_qrcode(self.fpr))
            self.qrcode.set_from_pixbuf(self.pixbuf)
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

        # FIXME: this should be moved to KeySignSection
        self.keyring = Keyring()

        uidsLabel = Gtk.Label()
        uidsLabel.set_text("UIDs")

        # this will later be populated with uids when user selects a key
        self.uidsBox = Gtk.VBox(spacing=5)

        self.expireLabel = Gtk.Label()
        self.expireLabel.set_text("Expires 0000-00-00")

        signaturesLabel = Gtk.Label()
        signaturesLabel.set_text("Signatures")

        # this will also be populated later
        self.signaturesBox = Gtk.VBox(spacing=5)

        self.pack_start(uidsLabel, False, False, 0)
        self.pack_start(self.uidsBox, True, True, 0)
        self.pack_start(self.expireLabel, False, False, 0)
        self.pack_start(signaturesLabel, False, False, 0)
        self.pack_start(self.signaturesBox, True, True, 0)

    def parse_sig_list(self, text):
        sigslist = []
        for block in text.split("\n"):
            record = block.split(":")
            if record[0] != "sig":
                continue
            (rectype, null, null, algo, keyid, timestamp, null, null, null, uid, null, null) = record
            sigslist.append((keyid, timestamp, uid))

        return sigslist

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

        # FIXME: this would be better if it was done in monkeysign
        self.keyring.context.call_command(['list-sigs', str(openPgpKey.keyid())])

        sigslist = self.parse_sig_list(self.keyring.context.stdout)
        # FIXME: what do we actually want to show here: the numbers of signatures
        # for this key or the number of times this key was used to signed others
        for (keyid,timestamp,uid) in sigslist:
            sigLabel = Gtk.Label()
            date = datetime.fromtimestamp(float(timestamp))
            sigLabel.set_markup(str(keyid) + "\t\t" + date.ctime())
            sigLabel.set_line_wrap(True)

            self.signaturesBox.pack_start(sigLabel, False, False, 0)
            sigLabel.show()

# Pages shown on "Get Key" Tab

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

    def format_fingerprint(self, fpr, scanner=False):

        if not scanner: # if fingerprint was typed

            fpr = ''.join(fpr.replace(" ", '').split('\n'))

            # a simple check to detect bad fingerprints
            if len(fpr) != 40:
                print("Fingerprint %s has not enough characters", fpr)
                fpr = ''

        return fpr


    def get_text_from_textview(self):
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        raw_fpr = self.textbuffer.get_text(start_iter, end_iter, False)
        fpr = self.format_fingerprint(raw_fpr)

        self.textbuffer.delete(start_iter, end_iter)

        return fpr


    def on_loadbutton_clicked(self, *args, **kwargs):
        print "load"


class SignKeyPage(Gtk.VBox):

    def __init__(self):
        super(SignKeyPage, self).__init__()
        self.set_spacing(10)

        self.topLabel = Gtk.Label()
        self.topLabel.set_markup("Downloading key with fingerprint ")
        self.topLabel.set_line_wrap(True)

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.textview)

        hBox = Gtk.HBox(spacing=10)
        hBox.pack_start(self.topLabel, False, False, 0)
        hBox.pack_start(self.scrolled_window, True, True, 0)
        self.pack_start(hBox, True, True, 0)

    def display_downloaded_key(self, fpr, keydata):
        self.topLabel.set_markup("Downloading key with fingerprint \n%s" % fpr)
        self.topLabel.show()

        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.delete(start_iter, end_iter)

        self.textbuffer.insert_at_cursor(keydata, len(keydata))


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
