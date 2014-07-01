from gi.repository import Gtk
from SignPages import KeysPage, SelectedKeyPage

progress_bar_text = ["Step 1: Choose a key and click on 'Next' button",
                     "Step 2: Compare the recieved fingerprint with the owner's key fpr",
                     "Step 3: Check if the identification papers match",
                     "Step 4: Key was succesfully signed"
                    ]

class KeySignSection(Gtk.VBox):


    def __init__(self):
        super(KeySignSection, self).__init__()

        # create notebook container
        self.notebook = Gtk.Notebook()
        self.keysPage = KeysPage()
        self.selectedKeyPage = SelectedKeyPage()
        self.notebook.append_page(self.keysPage, None)
        self.notebook.append_page(self.selectedKeyPage, None)

        self.notebook.set_show_tabs(False)

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text(progress_bar_text[0])
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.25) #TODO : Fix Hardcoded

        # create back button
        self.backButton = Gtk.Button('Back')
        # FIXME not working, button is still visible at start
        self.backButton.set_visible(False)
        self.backButton.connect('clicked', self.on_button_clicked)

        # create next button
        self.proceedButton = Gtk.Button('Next')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)
        self.proceedButton.connect('clicked', self.on_button_clicked)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.backButton, False, False, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)

    def on_button_clicked(self, button):
        # current tab index in notebook
        page_index = self.notebook.get_current_page()

        if button == self.proceedButton:
            # switch to the next page in the notebook
            self.notebook.next_page()
            page_index = self.notebook.get_current_page()
            if page_index != 0:
                self.backButton.set_visible(True)

            # get a Gtk.TreeSelection object to process the selected rows
            selection = self.keysPage.treeView.get_selection()
            model, paths = selection.get_selected_rows()

            if page_index == 1:
                for path in paths:
                    iterator = model.get_iter(path)
                    (name, email, keyid) = model.get(iterator, 0, 1, 2)

                    try:
                        openPgpKey = self.keysPage.keysDict[keyid]
                        self.selectedKeyPage.display_key_details(openPgpKey)

                    except KeyError:
                        print "No key details can be shown for this id:%s" % (keyid,)


        elif button == self.backButton:
            # switch to the previous page in the notebook
            self.notebook.prev_page()
            page_index = self.notebook.get_current_page()
            if page_index == 0:
                self.backButton.set_visible(False)

        # move the progress bar acording to current step
        self.progressBar.set_fraction((page_index+1) * 0.25)
        self.progressBar.set_text(progress_bar_text[page_index])


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
