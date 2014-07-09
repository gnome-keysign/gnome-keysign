#!/usr/bin/env python

import logging

from gi.repository import GLib
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
        self.log = logging.getLogger()

        # these are needed later when we need to get details about
        # a selected key
        self.keysPage = KeysPage()
        self.selectedKeyPage = SelectedKeyPage()

        # create notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self.keysPage, None)
        self.notebook.append_page(self.selectedKeyPage, None)
        self.notebook.set_show_tabs(False)

        # create back button
        self.backButton = Gtk.Button('Back')
        self.backButton.set_image(Gtk.Image.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON))
        self.backButton.set_always_show_image(True)
        self.backButton.connect('clicked', self.on_button_clicked)
        # create next button
        self.nextButton = Gtk.Button('Next')
        self.nextButton.set_image(Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        self.nextButton.set_always_show_image(True)
        self.nextButton.connect('clicked', self.on_button_clicked)

        buttonBox = Gtk.HBox()
        buttonBox.pack_start(self.backButton, False, False, 0)
        buttonBox.pack_start(self.nextButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(buttonBox, False, False, 0)

    def on_button_clicked(self, button):
        # get current index of page
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
                        self.selectedKeyPage.display_key_details(openPgpKey)
                    except KeyError:
                        print "No key details can be shown for this id:%s" % (keyid,)
        elif button == self.backButton:
            # switch to the previous page in the notebook
            self.notebook.prev_page()


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


class TempNetworkSection(Gtk.VBox):

    def __init__(self, app):
        super(TempNetworkSection, self).__init__()

        self.app = app
        self.log = logging.getLogger()

        self.set_spacing(5)

        # setup multiline editor
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()

        # setup scrolled window
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.add(self.textview)

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text(progress_bar_text[0])
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.25) #TODO : Fix Hardcoded

        # Temporary scenario: press "Get" button to request data from network.
        # It will make use of the (ip_address, port) avahi has discovered

        # setup button for recieving data
        self.getButton = Gtk.Button("Get")
        self.getButton.connect('clicked', self.on_get_button_clicked)
        self.getButton.set_halign(Gtk.Align.CENTER)

        # button for deleting text inside TextView
        self.clearButton = Gtk.Button("Clear")
        self.clearButton.connect('clicked', self.on_clear_button_clicked)
        self.clearButton.set_halign(Gtk.Align.CENTER)

        # setup box to hold the 2 buttons above
        buttonBox = Gtk.HBox(spacing=10)
        buttonBox.pack_start(self.getButton, False, False, 0)
        buttonBox.pack_start(self.clearButton, False, False, 0)
        buttonBox.set_halign(Gtk.Align.CENTER)

        # pack up
        self.pack_start(scrolledwindow, True, True, 0)
        self.pack_start(buttonBox, True, False, 0)

    def obtain_key_async(self, fingerprint, callback=None, data=None):
        import time
        keydata = str(time.sleep(1))
        GLib.idle_add(callback, keydata, data)
        # If this function is added itself via idle_add, then idle_add will
        # keep adding this function to the loop until this func ret False
        return False

    def on_get_button_clicked(self, button):

        # FIXME: User should be able to type fpr or scan its QR Code
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        fingerprint = self.textbuffer.get_text(start_iter, end_iter, False)
        self.textbuffer.delete(start_iter, end_iter)

        self.textbuffer.set_text("downloading key with fingerprint: \n%s\n...\n"
                                % fingerprint)
        GLib.idle_add(self.obtain_key_async, fingerprint, self.recieved_key, fingerprint)

        # move the progress bar acording to current step
        # self.progressBar.set_fraction((page_index+1) * 0.25)
        # self.progressBar.set_text(progress_bar_text[page_index])


    def recieved_key(self, keydata, *data):
        self.textbuffer.insert_at_cursor(str(keydata))


    def on_clear_button_clicked(self, button):
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.delete(start_iter, end_iter)