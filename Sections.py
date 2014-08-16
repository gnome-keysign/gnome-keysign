#!/usr/bin/env python

import logging
from urlparse import ParseResult

import requests
from requests.exceptions import ConnectionError

import sys

try:
    from monkeysign.gpg import Keyring, TempKeyring
except ImportError, e:
    print "A required python module is missing!\n%s" % (e,)
    sys.exit()

import Keyserver
from SignPages import KeysPage, KeyPresentPage, KeyDetailsPage
from SignPages import ScanFingerprintPage, SignKeyPage, PostSignPage

from gi.repository import Gst, Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import GdkX11
# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GstVideo

import key
Gst.init([])

### FIXME !!!! This should be replaced with the fingerprint of the key
# you want it signed. This is the fingerprint that should be scanned
SCAN_FINGERPRINT = '140162A978431A0258B3EC24E69EEE14181523F4'


progress_bar_text = ["Step 1: Scan QR Code or type fingerprint and click on 'Download' button",
                     "Step 2: Compare the received fpr with the owner's fpr and click 'Sign'",
                     "Step 3: Key was succesfully signed and an email was send to owner."]


class KeySignSection(Gtk.VBox):

    def __init__(self, app):
        '''Initialises the section which lets the user
        choose a key to be signed by other person.

        ``app'' should be the "app" itself. The place
        which holds global app data, especially the discovered
        clients on the network.
        '''
        super(KeySignSection, self).__init__()

        self.app = app
        self.log = logging.getLogger()
        self.keyring = Keyring()

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

        # this will hold a reference to the last key selected
        self.last_selected_key = None

    def on_button_clicked(self, button):

        page_index = self.notebook.get_current_page()

        if button == self.nextButton:
            # switch to the next page in the notebook
            self.notebook.next_page()

            selection = self.keysPage.treeView.get_selection()
            model, paths = selection.get_selected_rows()

            if page_index+1 == 1:
                for path in paths:
                    iterator = model.get_iter(path)
                    (name, email, keyid) = model.get(iterator, 0, 1, 2)
                    try:
                        openPgpKey = self.keysPage.keysDict[keyid]
                    except KeyError:
                        m = "No key details can be shown for id {}".format(keyid)
                        self.log.info(m)

                # display uids, exp date and signatures
                self.keyDetailsPage.display_uids_signatures_page(openPgpKey)
                # save a reference for later use
                self.last_selected_key = openPgpKey

            elif page_index+1 == 2:
                self.keyPresentPage.display_fingerprint_qr_page(self.last_selected_key)

                keyid = self.last_selected_key.keyid()
                self.keyring.export_data(fpr=str(keyid), secret=False)
                keydata = self.keyring.context.stdout

                self.log.debug("Keyserver switched on")
                self.app.setup_server(keydata)

            self.backButton.set_sensitive(True)

        elif button == self.backButton:

            if page_index == 2:
                self.log.debug("Keyserver switched off")
                self.app.stop_server()
            elif page_index-1 == 0:
                self.backButton.set_sensitive(False)

            self.notebook.prev_page()


class GetKeySection(Gtk.VBox):

    def __init__(self, app):
        '''Initialises the section which lets the user
        start signing a key.

        ``app'' should be the "app" itself. The place
        which holds global app data, especially the discovered
        clients on the network.
        '''
        super(GetKeySection, self).__init__()

        self.app = app
        self.log = logging.getLogger()

        # the temporary keyring we operate in
        self.tempkeyring = None

        self.scanPage = ScanFingerprintPage()
        self.signPage = SignKeyPage()
        # set up notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(self.scanPage, None)
        self.notebook.append_page(self.signPage, None)
        self.notebook.append_page(PostSignPage(), None)
        self.notebook.set_show_tabs(False)

        # set up the progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text(progress_bar_text[0])
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(1.0/3)

        self.nextButton = Gtk.Button('Next')
        self.nextButton.connect('clicked', self.on_button_clicked)
        self.nextButton.set_image(Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.BUTTON))
        self.nextButton.set_always_show_image(True)

        self.backButton = Gtk.Button('Back')
        self.backButton.connect('clicked', self.on_button_clicked)
        self.backButton.set_image(Gtk.Image.new_from_icon_name('go-previous', Gtk.IconSize.BUTTON))
        self.backButton.set_always_show_image(True)

        bottomBox = Gtk.HBox()
        bottomBox.pack_start(self.progressBar, True, True, 0)
        bottomBox.pack_start(self.backButton, False, False, 0)
        bottomBox.pack_start(self.nextButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(bottomBox, False, False, 0)

        # We *could* overwrite the on_barcode function, but
        # let's rather go with a GObject signal
        #self.scanFrame.on_barcode = self.on_barcode
        self.scanPage.scanFrame.connect('barcode', self.on_barcode)
        #GLib.idle_add(        self.scanFrame.run)

    def set_progress_bar(self):
        page_index = self.notebook.get_current_page()
        self.progressBar.set_text(progress_bar_text[page_index])
        self.progressBar.set_fraction((page_index+1)/3.0)


    def on_barcode(self, sender, barcode, message=None):
        '''This is connected to the "barcode" signal.
        The message argument is a GStreamer message that created
        the barcode.'''
        # we're using the monkeysign format where we insert the
        # string 'OPENPGP4FPR:'' in front of the fingerprint
        fpr = barcode.split(':')[-1]
        try:
            pgpkey = key.Key(fpr)
        except key.KeyError:
            self.log.exception("Could not create key from %s", barcode)
        else:
            self.log.info("Barcode signal %s %s" %( pgpkey.fingerprint, message))
            self.on_button_clicked(self.nextButton, pgpkey, message)

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

    def verify_downloaded_key(self, downloaded_data, fingerprint):
        # FIXME: implement a better and more secure way to verify the key
        if self.tmpkeyring.import_data(downloaded_data):
            imported_key_fpr = self.tmpkeyring.get_keys().keys()[0]
            if imported_key_fpr == fingerprint:
                result = True
            else:
                self.log.info("Key does not have equal fp: %s != %s", imported_key_fpr, fingerprint)
                result = False
        else:
            self.log.info("Failed to import downloaded data")
            result = False

        self.log.debug("Trying to validate %s against %s: %s", downloaded_data, fingerprint, result)
        return result


    def obtain_key_async(self, fingerprint, callback=None, data=None, error_cb=None):
        other_clients = self.app.discovered_services
        self.log.debug("The clients found on the network: %s", other_clients)

        # create a temporary keyring to not mess up with the user's own keyring
        self.tmpkeyring = TempKeyring()

        for keydata in self.try_download_keys(other_clients):
            if self.verify_downloaded_key(keydata, fingerprint):
                is_valid = True
            else:
                is_valid = False

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


    def on_button_clicked(self, button, *args, **kwargs):

        if button == self.nextButton:
            self.notebook.next_page()
        else:
            self.notebook.prev_page()

        self.set_progress_bar()

        page_index = self.notebook.get_current_page()
        if page_index == 1:
            if args:
                pgpkey = args[0]
                message = args[1]
                fingerprint = pgpkey.fingerprint
            else:
                fingerprint = self.scanPage.get_text_from_scanner()
                if fingerprint is None:
                    fingerprint = self.scanPage.get_text_from_textview()

            GLib.idle_add(self.obtain_key_async, fingerprint, self.recieved_key,
                    fingerprint)


        if page_index == 2:
            pass


    def recieved_key(self, fingerprint, keydata, *data):
        self.signPage.display_downloaded_key(fingerprint, keydata)


    # def on_download_button_clicked(self, button):

    #     start_iter = self.textbuffer.get_start_iter()
    #     end_iter = self.textbuffer.get_end_iter()
    #     raw_fpr = self.textbuffer.get_text(start_iter, end_iter, False)
    #     fpr = self.decode_fingerprint(raw_fpr)
    #     fpr = fpr if fpr != '' else SCAN_FINGERPRINT

    #     self.textbuffer.delete(start_iter, end_iter)
    #     self.topLabel.set_text("downloading key with fingerprint:\n%s"
    #                             % fpr)

    #     err = lambda x: self.textbuffer.set_text("Error downloading")
    #     GLib.idle_add(self.obtain_key_async, fpr,
    #         self.recieved_key, fpr,
    #         err
    #         )

    # def recieved_key(self, keydata, *data):
    #     self.textbuffer.insert_at_cursor("Key succesfully imported with"
    #                             " fingerprint:\n{}\n{}".format(data[0], keydata))
