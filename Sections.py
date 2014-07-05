#!/usr/bin/env python

import logging
from urlparse import ParseResult

import requests
from requests.exceptions import ConnectionError


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

        buttonBox = Gtk.HBox()
        buttonBox.pack_start(self.progressBar, True, True, 0)
        buttonBox.pack_start(self.backButton, False, False, 0)
        buttonBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(buttonBox, False, False, 0)

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


class KeysFromNetworkSection(Gtk.VBox):

    def __init__(self, app):
        '''Initialises the section which lets the user
        start signing a key.

        ``app'' should be the "app" itself. The place
        which holds global app data, especially the discovered
        clients on the network.
        '''
        super(KeysFromNetworkSection, self).__init__()
        self.set_spacing(5)

        self.app = app
        self.log = logging.getLogger()

        # setup label
        topLabel = Gtk.Label()
        topLabel.set_text("Send/Recieve key from network")

        # FIXME: use a proper way of uploading a key (i.e. FileChooserDialog).
        # For now the scenario is simple, you press "SendKey" and it sends a key
        # from the text editor to network, press "GetKey" and it display a key
        # recieved through network.

        # setup multiline editor
        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()

        # setup scrolled window
        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(False)
        scrolledwindow.set_vexpand(False)
        scrolledwindow.add(self.textview)

        # setup button for sending a key
        self.sendKeyButton = Gtk.Button("SendKey")
        self.sendKeyButton.connect('clicked', self.on_sendkey_button_clicked)
        self.sendKeyButton.set_halign(Gtk.Align.CENTER)

        # setup button for recieving a key
        self.getKeyButton = Gtk.Button("GetKey")
        self.getKeyButton.connect('clicked', self.on_getkey_button_clicked)
        self.getKeyButton.set_halign(Gtk.Align.CENTER)

        # button for deleting text inside TextView
        self.clearTextButton = Gtk.Button("Clear")
        self.clearTextButton.connect('clicked', self.on_clear_button_clicked)
        self.clearTextButton.set_halign(Gtk.Align.CENTER)

        # setup box to hold the 2 buttons above
        buttonBox = Gtk.HBox(spacing=10)
        buttonBox.pack_start(self.sendKeyButton, False, False, 0)
        buttonBox.pack_start(self.getKeyButton, False, False, 0)
        buttonBox.pack_start(self.clearTextButton, False, False, 0)
        buttonBox.set_halign(Gtk.Align.CENTER)

        # pack up
        self.pack_start(scrolledwindow, True, True, 0)
        self.pack_start(buttonBox, True, False, 0)


    def download_key_http(self, address, port):
        url = ParseResult(
            scheme='http',
            # This seems to work well enough with both IPv6 and IPv4
            netloc="[[%s]]:%d" % (address, port),
            path='/',
            params='',
            query='',
            fragment='')
        return requests.get(url.geturl()).text

    def try_download_keys(self, clients):
        for client in clients:
            self.log.debug("Getting key from client %s", client)

            name, address, port = client
            try:
                keydata = self.download_key_http(address, port)
                yield keydata
            except ConnectionError, e:
                # FIXME : We probably have other errors to catch
                self.log.exception("While downloading key from %s %i",
                                    address, port)


    def obtain_key_async(self, fingerprint, callback=None, data=None, error_cb=None):
        other_clients = self.app.discovered_services
        self.log.debug("The clients found on the network: %s", other_clients)

        for keydata in self.try_download_keys(other_clients):
            # FIXME : check whether the keydata makes sense,
            # i.e. compute the fingerprint from the obtained key
            # and compare it with the intended key
            is_valid = True
            if is_valid:
                break
        else:
            self.log.error("Could not find fingerprint %s " +\
                           "with the available clients (%s)",
                           fingerprint, other_clients)
            self.log.debug("Calling error callback, if available: %s",
                            error_cb)

            if error_cb:
                GLib.idle_add(error_cb, data)
            # FIXME : don't return here
            return

        GLib.idle_add(callback, keydata, data)
        # If this function is added itself via idle_add, then idle_add will
        # keep adding this function to the loop until this func ret False
        return False

    def on_getkey_button_clicked(self, button):

        # FIXME: User should be able to type fpr or scan its QR Code

        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        fingerprint = self.textbuffer.get_text(start_iter, end_iter, False)
        self.textbuffer.delete(start_iter, end_iter)

        self.textbuffer.set_text("downloading key with fingerprint: \n%s\n...\n"
                                % fingerprint)

        err = lambda x: self.textbuffer.insert_at_cursor("Error downloading")
        GLib.idle_add(self.obtain_key_async, fingerprint,
            self.recieved_key, fingerprint,
            # FIXME: not working as expected - it enters an infinite loop
            err
            )

    def recieved_key(self, keydata, *data):
        self.textbuffer.insert_at_cursor(str(keydata))


    def on_sendkey_button_clicked(self, button):
        pass

    def on_clear_button_clicked(self, button):
        start_iter = self.textbuffer.get_start_iter()
        end_iter = self.textbuffer.get_end_iter()
        self.textbuffer.delete(start_iter, end_iter)