from gi.repository import Gtk
from SignKeysPages import KeysPage, FingerprintPage, IdentityPage, SignedPage

FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeysSection(Gtk.VBox):

    def __init__(self):
        super(KeysSection, self).__init__()

        # create notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(KeysPage(), None)

        self.notebook.set_show_tabs(False)

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text("First step: select a key and click 'Sign'")
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.25)

        # create proceed button
        self.proceedButton = Gtk.Button('Sign')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)
        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)


class SignedSection(Gtk.Box):

    def __init__(self):
        super(SignedSection, self).__init__()

        # create fingerprint label
        self.fingerprintLabel = Gtk.Label()
        self.fingerprintLabel.set_markup('<span size="30720">' + FINGERPRINT + '</span>')

        self.pack_start(self.fingerprintLabel, True, False, 0)
