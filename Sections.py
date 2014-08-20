#!/usr/bin/env python

import logging
from urlparse import ParseResult

import requests
from requests.exceptions import ConnectionError

import sys
import re

try:
    from monkeysign.gpg import Keyring, TempKeyring
    from monkeysign.ui import MonkeysignUi
except ImportError, e:
    print "A required python module is missing!\n%s" % (e,)
    sys.exit()

import Keyserver
from SignPages import KeysPage, KeyPresentPage, KeyDetailsPage
from SignPages import ScanFingerprintPage, SignKeyPage, PostSignPage
import MainWindow

import key

from gi.repository import Gst, Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import GdkX11
# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GstVideo

Gst.init([])


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
        self.tmpkeyring = None

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

        self.signui = SignUi(self.app)

    def set_progress_bar(self):
        page_index = self.notebook.get_current_page()
        self.progressBar.set_text(progress_bar_text[page_index])
        self.progressBar.set_fraction((page_index+1)/3.0)


    def on_barcode(self, sender, barcode, message=None):
        '''This is connected to the "barcode" signal.
        The message argument is a GStreamer message that created
        the barcode.'''
        # barcode string starts with 'OPENPGP4FPR:' followed by the fingerprint
        m = re.search("((?:[0-9A-F]{4}\s*){10})", barcode, re.IGNORECASE)
        if m != None:
            fpr = m.group(1).replace(' ', '')
            try:
                pgpkey = key.Key(fpr)
            except key.KeyError:
                self.log.exception("Could not create key from %s", barcode)
            else:
                self.log.info("Barcode signal %s %s" %( pgpkey.fingerprint, message))
                self.on_button_clicked(self.nextButton, pgpkey, message)
        else:
            self.log.error("data found in barcode does not match a OpenPGP fingerprint pattern: %s", barcode)


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

        #FIXME: should we create a new TempKeyring for each key we want
        # to sign it ?
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

        GLib.idle_add(callback, fingerprint, keydata, data)

        # If this function is added itself via idle_add, then idle_add will
        # keep adding this function to the loop until this func ret False
        return False



    def sign_key_async(self, fingerprint, callback=None, data=None, error_cb=None):
        self.log.debug("I will sign key with fpr {}".format(fingerprint))

        self.signui.pattern = fingerprint
        # 1. fetch the key into a temporary keyring
        # 1.a) from the local keyring
        self.log.debug("looking for key %s in your keyring", self.signui.pattern)
        self.signui.keyring.context.set_option('export-options', 'export-minimal')
        if self.signui.tmpkeyring.import_data(self.signui.keyring.export_data(self.signui.pattern)):

            # 2. copy the signing key secrets into the keyring
            self.signui.copy_secrets()
            # 3. for every user id (or all, if -a is specified)
            # 3.1. sign the uid, using gpg-agent
            self.signui.sign_key()

            # 3.2. export and encrypt the signature
            # 3.3. mail the key to the user
            # FIXME: for now only export it to a file
            self.save_to_file()
            # self.sign.export_key()


            # 3.4. optionnally (-l), create a local signature and import in
            # local keyring
            # 4. trash the temporary keyring


        else:
            self.log.error('data found in barcode does not match a OpenPGP fingerprint pattern: %s', fingerprint)

        return False

    def save_to_file(self):
        #FIXME: this is a temporary function to export signed key,
        # it should send an email to the key owner
        if len(self.signui.signed_keys) < 1:
            self.log.error('no key signed, nothing to export')


        for fpr, key in self.signui.signed_keys.items():
            filename = "%s_signed.gpg" %fpr
            f = open(filename, "wt")

            f.write(self.signui.tmpkeyring.export_data(fpr))

            self.log.info("Key with fpr %s was signed and exported to file %s", fpr, filename)

        return False

    def send_email(self, fingerprint, *data):
        pass

    def on_button_clicked(self, button, *args, **kwargs):

        if button == self.nextButton:
            self.notebook.next_page()
            self.set_progress_bar()

            page_index = self.notebook.get_current_page()
            if page_index == 1:
                if args:
                    # If we call on_button_clicked() from on_barcode()
                    # then we get extra arguments
                    pgpkey = args[0]
                    message = args[1]
                    fingerprint = pgpkey.fingerprint
                else:
                    fingerprint = self.scanPage.get_text_from_textview()

                # save a reference to the last received fingerprint
                self.last_received_fingerprint = fingerprint

                # error callback function
                err = lambda x: self.signPage.topLabel.set_markup("Error downloading"
                                    " key with fpr \n%s" %fingerprint)
                # use GLib.idle_add to use a separate thread for the downloading of
                # the keydata
                GLib.idle_add(self.obtain_key_async, fingerprint, self.recieved_key,
                        fingerprint, err)


            if page_index == 2:
                # signing of key and sending an email is done on separate
                # threads also
                GLib.idle_add(self.sign_key_async, self.last_received_fingerprint,
                    self.send_email, self.last_received_fingerprint)


        elif button == self.backButton:
            self.notebook.prev_page()
            self.set_progress_bar()


    def recieved_key(self, fingerprint, keydata, *data):
        self.signPage.display_downloaded_key(fingerprint, keydata)




class SignUi(MonkeysignUi):
    """sign a key in a safe fashion.

This program assumes you have gpg-agent configured to prompt for
passwords."""

    def __init__(self, app, args = None):
        super(SignUi, self).__init__(args)

        self.app = app


    def main(self):

        MonkeysignUi.main(self)

    def yes_no(self, prompt, default = None):
        dialog = Gtk.MessageDialog(self.app.window, 0, Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK_CANCEL, prompt)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.OK

    def choose_uid(self, prompt, key):
        dialog = Gtk.Dialog(prompt, self.app.window, 0,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))

        label = Gtk.Label(prompt)
        self.box = dialog.get_content_area()
        self.box.add(label)
        label.show()

        self.uid_radios = None
        for uid in key.uidslist:
            r = Gtk.RadioButton(self.uid_radios, uid.uid)
            r.show()
            self.box.add(r)
            if self.uid_radios is None:
                self.uid_radios = r
                self.uid_radios.set_active(True)

        response = dialog.run()

        label = None
        if response == Gtk.ResponseType.OK:
            self.log(_('okay, signing'))
            label = [ r for r in self.uid_radios.get_group() if r.get_active()][0].get_label()
        else:
            self.log(_('user denied signature'))

        dialog.destroy
        return label
