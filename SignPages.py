
try:
    from gi.repository import Gtk, GdkPixbuf
    from monkeysign.gpg import Keyring
except ImportError, e:
    print "A required python module is missing!\n%s" % (e,)
    sys.exit()

import sys


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

        for key in self.keyring.get_keys().values():
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

class SelectedKeyPage(Gtk.HBox):
    def __init__(self):
        super(SelectedKeyPage, self).__init__()

        # create left side Key labels
        fingerprintMark = Gtk.Label()
        fingerprintMark.set_markup('<span size="15000">' + 'Key Fingerprint' + '</span>')

        self.fingerprintLabel = Gtk.Label()
        self.fingerprintLabel.set_markup('<span size="20000">' + FINGERPRINT_DEFAULT + '</span>')

        # left vertical box
        leftVBox = Gtk.VBox(spacing=10)
        leftVBox.pack_start(fingerprintMark, False, False, 0)
        leftVBox.pack_start(self.fingerprintLabel, False, False, 0)

        # display QR code on the right side
        imageLabel = Gtk.Label()
        imageLabel.set_markup('<span size="15000">' + 'Key QR code' + '</span>')

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size('qrsample.png', 200, -1)
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(pixbuf)
        self.image.props.margin = 10

        # right vertical box
        rightVBox = Gtk.VBox(spacing=10)
        rightVBox.pack_start(imageLabel, False, False, 0)
        rightVBox.pack_start(self.image, False, False, 0)

        self.pack_start(leftVBox, True, True, 0)
        self.pack_start(rightVBox, False, False, 0)

    def display_key_details(self, openPgpKey):
        rawfpr = openPgpKey.fpr

        fpr = ""
        for i in xrange(0, len(rawfpr), 4):

            fpr += rawfpr[i:i+4]
            if i != 0 and (i+4) % 20 == 0:
                fpr += "\n"
            else:
                fpr += " "

        fpr = fpr.rstrip()
        self.fingerprintLabel.set_markup('<span size="20000">' + fpr + '</span>')
