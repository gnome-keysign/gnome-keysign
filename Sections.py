from gi.repository import Gtk
from SignPages import KeysPage, SelectedKeyPage

FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeySignSection(Gtk.VBox):

    def __init__(self):
        super(KeySignSection, self).__init__()

        # create notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(KeysPage(), None)
        self.notebook.append_page(SelectedKeyPage(), None)

        #TODO make notebook change pages according to current step and set show tabs to false

        self.notebook.set_show_tabs(True)

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text("Step 1: Choose a key and click on 'Select' button.")
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.50)

        # create proceed button
        self.proceedButton = Gtk.Button('Select')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_YES, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)


class GetKey(Gtk.Box):

    def __init__(self):
        super(GetKey, self).__init__()


        # create fingerprint label
        entryLabel = Gtk.Label()
        entryLabel.set_markup('<span size="30000">' + 'Type fingerprint'+ '</span>')

        self.fingerprintEntry = Gtk.Entry()

        scanLabel = Gtk.Label()
        scanLabel.set_markup('<span size="30000">' + 'or scan QR code'+ '</span>')

        self.frame = Gtk.Frame(label='QR')
        # frame.set_shadow_type(Gtk.SHADOW_IN)

        self.scanButton = Gtk.Button('Scan')
        self.scanButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_APPLY, Gtk.IconSize.BUTTON))
        self.scanButton.set_always_show_image(True)

        container = Gtk.VBox()
        container.pack_start(entryLabel, False, False, 0)
        container.pack_start(self.fingerprintEntry, False, False, 0)
        container.pack_start(scanLabel, False, False, 0)
        container.pack_start(self.frame, False, False, 0)
        container.pack_start(self.scanButton, False, False, 0)

        self.pack_start(container, True, False, 0)


    def entry_callback(self, widget, entry):
        return self.entryLabel.get_text()
