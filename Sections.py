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

        #TODO make notebook change pages according to current step

        self.notebook.set_show_tabs(False) # TODO

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text("Step 1: Choose a key and click on 'Next' button")
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.25) #TODO : Fix Hardcoded

        # create proceed button
        self.proceedButton = Gtk.Button('Next')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)
        self.proceedButton.connect('clicked', self.on_button_clicked)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)

    def on_button_clicked(self, button):

        if (button == self.proceedButton):
            self.notebook.next_page()

            page_index = self.notebook.get_current_page() + 1
            if page_index == 2:
                progressBar_text = "Step2: Compare the recieved fingerprint with the owner's key fpr"
            elif page_index == 3:
                progressBar_text = "Step3: Check if the identification papers match"
            elif page_index == 4:
                progressBar_text = "Step4: Key was succesfully signed"

            self.progressBar.set_fraction(page_index * 0.25)
            self.progressBar.set_text(progressBar_text)

class GetKeySection(Gtk.Box):

    def __init__(self):
        super(GetKeySection, self).__init__()

        # create main container
        container = Gtk.VBox(spacing=10)

        # create fingerprint entry
        self.fingerprintEntryLabel = Gtk.Label()
        self.fingerprintEntryLabel.set_markup('<span size="15000">' + 'Type fingerprint'+ '</span>')
        self.fingerprintEntryLabel.set_margin_top(10)

        self.fingerprintEntry = Gtk.Entry()

        container.pack_start(self.fingerprintEntryLabel, False, False, 0)
        container.pack_start(self.fingerprintEntry, False, False, 0)

        # create scanner frame
        self.scanFrameLabel = Gtk.Label()
        self.scanFrameLabel.set_markup('<span size="15000">' + '... or scan QR code'+ '</span>')

        self.scanFrame = Gtk.Frame(label='QR Scanner')

        container.pack_start(self.scanFrameLabel, False, False, 0)
        container.pack_start(self.scanFrame, True, True, 0)

        # create save key button
        self.saveButton = Gtk.Button('Save key')
        self.saveButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_SAVE, Gtk.IconSize.BUTTON))
        self.saveButton.set_always_show_image(True)
        self.saveButton.set_margin_bottom(10)

        container.pack_start(self.saveButton, False, False, 0)

        self.pack_start(container, True, False, 0)
