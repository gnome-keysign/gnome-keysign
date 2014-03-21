from gi.repository import Gtk, GdkPixbuf

FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'
DATA = [(
    "Andrei Macavei",
    "andrei.macavei@example.com",
    "4096R/BC66DFE3"
    ),(
    "Anonymus Hacker",
    "anonymus.hacker@hackit.com",
    "4096R//BC662E46"
    )]
SAMPLE_ID = DATA[0]

class KeysPage(Gtk.HBox):

    def __init__(self):
        super(KeysPage, self).__init__()

        # create and fill up the list store
        self.store = Gtk.ListStore(str, str, str)
        for entry in DATA:
            self.store.append(entry)

        # create the tree
        self.tree = Gtk.TreeView(model=self.store)

        nameRenderer = Gtk.CellRendererText()
        nameColumn = Gtk.TreeViewColumn("Name", nameRenderer, text=0)

        emailRenderer = Gtk.CellRendererText()
        emailColumn = Gtk.TreeViewColumn("Email", emailRenderer, text=1)

        keyRenderer = Gtk.CellRendererText()
        keyColumn = Gtk.TreeViewColumn("Key", keyRenderer, text=2)

        self.tree.append_column(nameColumn)
        self.tree.append_column(emailColumn)
        self.tree.append_column(keyColumn)

        # create key logo
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size('logo.jpg', 200, -1)
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(pixbuf)
        self.image.props.valign = Gtk.Align.START
        self.image.props.margin = 5

        self.pack_start(self.tree, True, True, 0)
        self.pack_start(self.image, False, False, 0)


class FingerprintPage(Gtk.HBox):

    def __init__(self):
        super(FingerprintPage, self).__init__()

        # create the instructions label
        instrLabel = Gtk.Label()
        instrLabel.set_markup('The user should enter the <b>Key signed</b> section.\n' +
                            'Compare the two fingerprints to verify the authenticity of the key.')
        instrLabel.set_justify(Gtk.Justification.LEFT)
        instrLabel.set_halign(Gtk.Align.START)
        instrLabel.set_margin_bottom(10)

        # create the fingerprint label
        self.peerFingerprintLabel = Gtk.Label()
        self.peerFingerprintLabel.set_markup('<span size="30720">' + FINGERPRINT + '</span>')

        # use a container for alignment
        container = Gtk.VBox()
        container.pack_start(instrLabel, False, False, 0)
        container.pack_start(self.peerFingerprintLabel, False, False, 0)
        container.set_valign(Gtk.Align.CENTER)

        self.pack_start(container, True, False, 0)


class IdentityPage(Gtk.HBox):

    def __init__(self):
        super(IdentityPage, self).__init__()

        # create the instructions label
        instrLabel = Gtk.Label()
        instrLabel.set_markup('Check the <b>identification papers</b> of the other person.\n' +
                                     '<b>Make sure</b> the name below and the ID name <b>match</b>!')
        instrLabel.set_justify(Gtk.Justification.LEFT)
        instrLabel.set_halign(Gtk.Align.START)
        instrLabel.set_margin_bottom(10)

        # createthe name label
        self.peerNameLabel = Gtk.Label()
        self.peerNameLabel.set_markup('<span size="30720">' + SAMPLE_ID[0] + '</span>')

        # use a container for alignment
        container = Gtk.VBox()
        container.pack_start(instrLabel, False, False, 0)
        container.pack_start(self.peerNameLabel, False, False, 0)
        container.set_valign(Gtk.Align.CENTER)

        self.pack_start(container, True, False, 0)


class SignedPage(Gtk.HBox):

    def __init__(self):
        super(SignedPage, self).__init__()

        # create label
        signedLabel = Gtk.Label()
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