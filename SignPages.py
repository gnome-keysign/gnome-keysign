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