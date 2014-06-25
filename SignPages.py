
import sys

try:
    from gi.repository import Gtk, GdkPixbuf
    from monkeysign.gpg import Keyring
except ImportError, e:
    print "A required python module is missing!\n%s" % (e,)
    sys.exit()


FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeysPage(Gtk.VBox):

    def __init__(self):
        super(KeysPage, self).__init__()

        # create and fill up the list store with sample values
        self.store = Gtk.ListStore(str, str, str)

        # FIXME use a callback function to refresh the display when keys change
        for key in Keyring().get_keys().values():
            if key.invalid or key.disabled or key.expired or key.revoked:
                continue
            # get all UIDs for key
            uidslist = key.uidslist
            for e in uidslist:
                # UID general format: Real Name (Comment) <email@address>
                uid = str(e.uid)
                # Remove (Comment) if exists
                com_start = uid.find('(')
                if com_start != -1:
                    com_end = uid.find(')')
                    uid = uid[:com_start].strip() + uid[com_end+1:].strip()

                name = uid.split('<')[0].strip()
                email = uid.split('<')[1].replace('>','').strip()

                self.store.append((name, email, str(key.keyid())))

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

        # Use ScrolledWindow to make the TreeView scrollable
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.tree)
        self.scrolled_window.set_min_content_height(200)

        self.pack_start(self.scrolled_window, True, True, 0)


class SelectedKeyPage(Gtk.HBox):
    def __init__(self):
        super(SelectedKeyPage, self).__init__()

        # create fingerprint label
        fingerprintMark = Gtk.Label()
        fingerprintMark.set_markup('<span size="15000">' + 'Your key Fingerprint' + '</span>')

        self.fingerprintLabel = Gtk.Label()
        self.fingerprintLabel.set_markup('<span size="20000">' + FINGERPRINT + '</span>')

        containerLeft = Gtk.VBox(spacing=10)
        containerLeft.pack_start(fingerprintMark, False, False, 0)
        containerLeft.pack_start(self.fingerprintLabel, False, False, 0)

        # create QR image
        imageLabel = Gtk.Label()
        imageLabel.set_markup('<span size="15000">' + 'Your QR code' + '</span>')

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size('qrsample.png', 200, -1)
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(pixbuf)
        self.image.props.margin = 10

        containerRight = Gtk.VBox(spacing=10)
        containerRight.pack_start(imageLabel, False, False, 0)
        containerRight.pack_start(self.image, False, False, 0)

        self.pack_start(containerLeft, True, True, 0)
        self.pack_start(containerRight, False, False, 0)