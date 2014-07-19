#!/usr/bin/env python

import logging

from gi.repository import GLib
from gi.repository import Gtk

from SignPages import KeysPage, KeyPresentPage, KeyDetailsPage

progress_bar_text = ["Step 1: Choose a key and click on 'Next' button",
                     "Step 2: Compare the recieved fingerprint with the owner's key fpr",
                     "Step 3: Check if the identification papers match",
                     "Step 4: Key was succesfully signed"
                    ]

class KeySignSection(Gtk.VBox):

    def __init__(self):
        super(KeySignSection, self).__init__()
        self.log = logging.getLogger()

        # these are needed later when we need to get details about
        # a selected key
        self.keysPage = KeysPage(self)
        self.keyDetailsPage = KeyDetailsPage()
        self.keyPresentPage = KeyPresentPage()

        # set up notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self.keysPage, None)
        self.notebook.append_page(self.keyDetailsPage, None)
        self.notebook.append_page(self.keyPresentPage, None)
        self.notebook.set_show_tabs(False)

        # create back button
        self.backButton = Gtk.Button('Back')
        self.backButton.set_image(Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON))
        self.backButton.set_always_show_image(True)
        self.backButton.connect('clicked', self.on_button_clicked)
        self.backButton.set_sensitive(False)
        # create next button
        self.nextButton = Gtk.Button('Next')
        self.nextButton.set_image(Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        self.nextButton.set_always_show_image(True)
        self.nextButton.connect('clicked', self.on_button_clicked)
        self.nextButton.set_sensitive(False)

        buttonBox = Gtk.HBox()
        buttonBox.pack_start(self.backButton, False, False, 0)
        buttonBox.pack_start(self.nextButton, False, False, 0)
        # pack up
        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(buttonBox, False, False, 0)

    def on_button_clicked(self, button):
        # get index of current page
        page_index = self.notebook.get_current_page()

        if button == self.nextButton:
            # switch to the next page in the notebook
            self.notebook.next_page()
            page_index = self.notebook.get_current_page()
            # get a Gtk.TreeSelection object to process the selected rows
            selection = self.keysPage.treeView.get_selection()
            model, paths = selection.get_selected_rows()
            if page_index == 1:
                for path in paths:
                    iterator = model.get_iter(path)
                    (name, email, keyid) = model.get(iterator, 0, 1, 2)
                    try:
                        openPgpKey = self.keysPage.keysDict[keyid]
                        self.keyPresentPage.display_key_details(openPgpKey)
                    except KeyError:
                        print "No key details can be shown for this id:%s" % (keyid,)
            # activate 'Back' button
            self.backButton.set_sensitive(True)

        elif button == self.backButton:
            self.notebook.prev_page()
            if page_index-1 == 0:
                self.backButton.set_sensitive(False)

class GetKeySection(Gtk.Box):

    def __init__(self):
        super(GetKeySection, self).__init__()

        # set up main container
        mainBox = Gtk.VBox(spacing=10)
        # set up labels
        self.topLabel = Gtk.Label()
        self.topLabel.set_markup('Type fingerprint')
        midLabel = Gtk.Label()
        midLabel.set_markup('... or scan QR code')
        # set up text editor
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        # set up scrolled window
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.add(self.textview)

        # set up webcam frame
        # FIXME  create the actual webcam widgets
        self.scanFrame = Gtk.Frame(label='QR Scanner')

        # set up download button
        # Scenario: When 'Download' button is clicked it will request data
        # from network using self.app.discovered_services to get address
        self.downloadButton = Gtk.Button('Download Key')
        self.downloadButton.connect('clicked', self.on_button_clicked)
        self.downloadButton.set_image(Gtk.Image.new_from_icon_name("document-save", Gtk.IconSize.BUTTON))
        self.downloadButton.set_always_show_image(True)
        # pack up
        mainBox.pack_start(self.topLabel, False, False, 0)
        mainBox.pack_start(scrolledwindow, False, False, 0)
        mainBox.pack_start(midLabel, False, False, 0)
        mainBox.pack_start(self.scanFrame, True, True, 0)
        mainBox.pack_start(self.downloadButton, False, False, 0)
        self.pack_start(mainBox, True, False, 0)

    def obtain_key_async(self, fingerprint, callback=None, data=None):
        import time
        keydata = str(time.sleep(1))
        GLib.idle_add(callback, keydata, data)
        # If this function is added itself via idle_add, then idle_add will
        # keep adding this function to the loop until this func ret False
        return False

    def on_button_clicked(self, button):

        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        fingerprint = self.textbuffer.get_text(start_iter, end_iter, False)
        self.textbuffer.delete(start_iter, end_iter)

        self.topLabel.set_text("downloading key with fingerprint:\n%s"
                                % fingerprint)
        GLib.idle_add(self.obtain_key_async, fingerprint, self.recieved_key,
                    fingerprint)

    def recieved_key(self, keydata, *data):
        self.textbuffer.insert_at_cursor(str(keydata))
