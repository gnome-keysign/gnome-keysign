from gi.repository import Gtk, GdkPixbuf

FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'
SAMPLE = [(
    "Andrei Macavei",
    "andrei.macavei@example.com",
    "4096R/BC66DFE1"
    ),(
    "Anonymus Hacker",
    "anonymus.hacker@hackit.com",
    "4096R//BC662E46"
    )]
SAMPLE_ID = SAMPLE[0]

class KeysPage(Gtk.VBox):

    def __init__(self):
        super(KeysPage, self).__init__()

        # create and fill up the list store with sample values
        self.store = Gtk.ListStore(str, str, str)
        for entry in SAMPLE:
            self.store.append(entry)

        # create the tree
        self.tree = Gtk.TreeView(model=self.store)

        nameRenderer = Gtk.CellRendererText()
        nameColumn = Gtk.TreeViewColumn("Name", nameRenderer, text=0)

        emailRenderer = Gtk.CellRendererText()
        emailColumn = Gtk.TreeViewColumn("Email", emailRenderer, text=1)

        # keyRenderer = Gtk.CellRendererText()
        # keyColumn = Gtk.TreeViewColumn("Key", keyRenderer, text=2)

        self.tree.append_column(nameColumn)
        self.tree.append_column(emailColumn)
        # self.tree.append_column(keyColumn)

        self.pack_start(self.tree, True, True, 0)

class SelectedKeyPage(Gtk.HBox):
    def __init__(self):
        super(SelectedKeyPage, self).__init__()

        # create labelFingerprint
        labelFingerprint = Gtk.Label()
        labelFingerprint.set_markup('Your key Fingerprint')
        labelFingerprint.set_justify(Gtk.Justification.CENTER)
        labelFingerprint.set_halign(Gtk.Align.CENTER)
        labelFingerprint.set_margin_bottom(10)

        # create fingerprint labelFingerprint
        self.fingerprintLabel = Gtk.Label()
        self.fingerprintLabel.set_markup('<span size="20000">' + FINGERPRINT + '</span>')

        containerLeft = Gtk.VBox()
        containerLeft.pack_start(labelFingerprint, False, False, 0)
        containerLeft.pack_start(self.fingerprintLabel, False, False, 0)


        # create label and QR image

        labelImage = Gtk.Label()
        labelImage.set_markup('Your QR code')
        labelImage.set_justify(Gtk.Justification.CENTER)
        labelImage.set_halign(Gtk.Align.CENTER)
        labelImage.set_margin_bottom(10)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size('qr_code_sample.png', 200, -1)
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(pixbuf)
        self.image.props.valign = Gtk.Align.CENTER
        self.image.props.margin = 5


        containerRight = Gtk.VBox()
        containerRight.pack_start(labelImage, False, False, 0)
        containerRight.pack_start(self.image, False, False, 0)



        self.pack_start(containerLeft, True, True, 0)
        self.pack_start(containerRight, False, False, 0)


class FingerprintPage(Gtk.HBox):

    def __init__(self):
        super(FingerprintPage, self).__init__()

        # create the instructions labelFingerprint
        instrLabel = Gtk.labelFingerprint()
        instrLabel.set_markup('The user should enter the <b>Fingerprint</b> section.\n' +
                            'Compare the two fingerprints to verify the authenticity of the key.')
        instrLabel.set_justify(Gtk.Justification.LEFT)
        instrLabel.set_halign(Gtk.Align.START)
        instrLabel.set_margin_bottom(10)

        # create the fingerprint labelFingerprint
        self.peerFingerprintLabel = Gtk.labelFingerprint()
        self.peerFingerprintLabel.set_markup('<span size="10000">' + FINGERPRINT + '</span>')

        # use a container for alignment
        container = Gtk.VBox()
        container.pack_start(instrLabel, False, False, 0)
        container.pack_start(self.peerFingerprintLabel, False, False, 0)
        container.set_valign(Gtk.Align.CENTER)

        self.pack_start(container, True, False, 0)


class IdentityPage(Gtk.HBox):

    def __init__(self):
        super(IdentityPage, self).__init__()

        # create the instructions labelFingerprint
        instrLabel = Gtk.labelFingerprint()
        instrLabel.set_markup('Check the <b>identification papers</b> of the other person.\n' +
                                     '<b>Make sure</b> the name below and the ID name <b>match</b>!')
        instrLabel.set_justify(Gtk.Justification.LEFT)
        instrLabel.set_halign(Gtk.Align.START)
        instrLabel.set_margin_bottom(10)

        # create name labelFingerprint
        self.peerNameLabel = Gtk.labelFingerprint()
        self.peerNameLabel.set_markup('<span size="10000">' + SAMPLE_ID[0] + '</span>')

        # use a container for alignment
        container = Gtk.VBox()
        container.pack_start(instrLabel, False, False, 0)
        container.pack_start(self.peerNameLabel, False, False, 0)
        container.set_valign(Gtk.Align.CENTER)

        self.pack_start(container, True, False, 0)


class SignedPage(Gtk.HBox):

    def __init__(self):
        super(SignedPage, self).__init__()

        # create labelFingerprint
        signedLabel = Gtk.labelFingerprint()
        signedLabel.set_text('Key signed!')

        # create buttons
        sendBackButton = Gtk.Button('Send back to owner')
        sendBackButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_GO_BACK, Gtk.IconSize.BUTTON))
        sendBackButton.set_always_show_image(True)
        sendBackButton.set_halign(Gtk.Align.CENTER)

        saveButton = Gtk.Button('Save the key locally')
        saveButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_SAVE, Gtk.IconSize.BUTTON))
        saveButton.set_always_show_image(True)
        saveButton.set_halign(Gtk.Align.CENTER)

        emailButton = Gtk.Button('Email the key owner')
        emailButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_GO_FORWARD, Gtk.IconSize.BUTTON))
        emailButton.set_always_show_image(True)
        emailButton.set_halign(Gtk.Align.CENTER)

        # use a container for alignment
        container = Gtk.VBox(spacing=3)
        container.pack_start(signedLabel, False, False, 8)
        container.pack_start(sendBackButton, False, False, 0)
        container.pack_start(saveButton, False, False, 0)
        container.pack_start(emailButton, False, False, 0)
        container.set_valign(Gtk.Align.CENTER)

        self.pack_start(container, True, False, 0)