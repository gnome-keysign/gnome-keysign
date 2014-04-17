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

        #TODO make notebook change pages according to current step # TODO

        self.notebook.set_show_tabs(True) # TODO

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text("Step 1: Choose a key and click on 'Select' button.")
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.50) #TODO : Fix Hardcoded

        # create proceed button
        self.proceedButton = Gtk.Button('Select')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_YES, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)


class GetKeySection(Gtk.Box):

    def __init__(self):
        super(GetKeySection, self).__init__()

        # create fingerprint label
        self.fingerprintEntryLabel = Gtk.Label()
        self.fingerprintEntryLabel.set_markup('Type fingerprint')
        # self.fingerprintEntryLabel.set_markup('<span size="30000">' + 'Type fingerprint'+ '</span>')

        self.fingerprintEntry = Gtk.Entry()

        leftVBox = Gtk.VBox()
        leftVBox.pack_start(self.fingerprintEntryLabel, False, False, 0)
        leftVBox.pack_start(self.fingerprintEntry, False, False, 5)

        self.scanFrameLabel = Gtk.Label()
        self.scanFrameLabel.set_markup('... or scan QR code')
        # self.scanFrameLabel.set_markup('<span size="30000">' + 'or scan QR code'+ '</span>')

        self.scanFrame = Gtk.Frame(label='QR')
        # frame.set_shadow_type(Gtk.SHADOW_IN)

        self.scanButton = Gtk.Button('Scan')
        self.scanButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_APPLY, Gtk.IconSize.BUTTON))
        self.scanButton.set_always_show_image(True)

        rightVBox = Gtk.VBox()
        rightVBox.pack_start(self.scanFrameLabel, False, False, 0)
        rightVBox.pack_start(self.scanFrame, True, True, 5)
        rightVBox.pack_start(self.scanButton, False, False, 5)

        mainBox = Gtk.HBox()
        mainBox.pack_start(leftVBox, True, True, 0)
        mainBox.pack_start(rightVBox, True, True, 0)

        self.pack_start(mainBox, True, True, 0)
