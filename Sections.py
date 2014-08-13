#!/usr/bin/env python

import logging

from gi.repository import GLib
from gi.repository import Gtk

from SignPages import KeysPage, KeyPresentPage, KeyDetailsPage
from SignPages import ScanFingerprintPage, SignKeyPage, PostSignPage

from monkeysign.gpg import OpenPGPkey


progress_bar_text = ["Step 1: Scan QR Code or type fingerprint and click on 'Download' button",
                     "Step 2: Compare the received fpr with the owner's fpr and click 'Sign'",
                     "Step 3: Key was succesfully signed and an email was send to owner."]

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

        page_index = self.notebook.get_current_page() # current page index

        if button == self.nextButton: # switch to next page
            self.notebook.next_page()
            page_index = self.notebook.get_current_page()

            selection = self.keysPage.treeView.get_selection()
            model, paths = selection.get_selected_rows()

            for path in paths:
                iterator = model.get_iter(path)
                (name, email, keyid) = model.get(iterator, 0, 1, 2)
                try:
                    openPgpKey = self.keysPage.keysDict[keyid]
                except KeyError:
                    print "No key details can be shown for this id:%s" % (keyid,)
                    openPgpKey = OpenPGPkey(None)

            if page_index == 1:
                self.keyDetailsPage.display_uids_signatures_page(openPgpKey)
            elif page_index == 2:
                self.keyPresentPage.display_fingerprint_qr_page(openPgpKey)

            self.backButton.set_sensitive(True)

        elif button == self.backButton: # switch to previous page
            self.notebook.prev_page()
            if page_index-1 == 0:
                self.backButton.set_sensitive(False)

class GetKeySection(Gtk.VBox):

    def __init__(self):
        super(GetKeySection, self).__init__()

        # set up notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(ScanFingerprintPage(), None)
        self.notebook.append_page(SignKeyPage(), None)
        self.notebook.append_page(PostSignPage(), None)
        self.notebook.set_show_tabs(False)

        # set up the progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text(progress_bar_text[0])
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(1.0/3)

        self.downloadButton = Gtk.Button('Download')
        self.downloadButton.connect('clicked', self.on_button_clicked)
        self.downloadButton.set_image(Gtk.Image.new_from_icon_name("document-save", Gtk.IconSize.BUTTON))
        self.downloadButton.set_always_show_image(True)

        bottomBox = Gtk.HBox()
        bottomBox.pack_start(self.progressBar, True, True, 0)
        bottomBox.pack_start(self.downloadButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(bottomBox, False, False, 0)

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
