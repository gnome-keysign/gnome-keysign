#!/usr/bin/env python
# encoding: utf-8
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#
#    This file is part of GNOME Keysign.
#
#    GNOME Keysign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    GNOME Keysign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with GNOME Keysign.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import signal
import sys
import argparse
import logging

from gi.repository import Gtk, GLib
from gi.repository import GObject

from monkeysign.gpg import Keyring

# These are relative imports
from __init__ import __version__

log = logging.getLogger()


class KeysPage(Gtk.VBox):
    '''This represents a list of keys with the option for the user
    to select one key to proceed.
    
    This class emits a `key-selection-changed' signal when the user
    initially selects a key such that it is highlighted.
    
    The `key-selected' signal is emitted when the user commits
    to a key, i.e. by pressing a designated button to make his
    selection public.
    '''
    __gsignals__ = {
        'key-selected': (GObject.SIGNAL_RUN_LAST, None,
                         # Hm, this is a str for now, but ideally
                         # it'd be the full key object
                         (str,)),
        'key-selection-changed': (GObject.SIGNAL_RUN_LAST, None,
                         # Hm, this is a str for now, but ideally
                         # it'd be the full key object
                         (str,)),
    }

    def __init__(self, show_public_keys=False):
        '''Sets the widget up.
        
        The show_public_keys parameter is meant for development
        purposes only.  If set to True, the widget will show
        the public keys, too.  Otherwise, secret keys are shown.
        '''
        super(KeysPage, self).__init__()

        # set up the list store to be filled up with user's gpg keys
        # Note that other functions expect a certain structure to
        # this ListStore, e.g. when parsing the selection of the
        # TreeView, i.e. in get_items_from_selection.
        self.store = Gtk.ListStore(str, str, str)

        # FIXME: this should be moved to KeySignSection
        self.keyring = Keyring() # the user's keyring

        self.keysDict = {}

        # FIXME: this should be a callback function to update the display
        # when a key is changed/deleted
        for key in self.keyring.get_keys(None, secret=True, public=show_public_keys).values():
            if key.invalid or key.disabled or key.expired or key.revoked:
                continue

            uidslist = key.uidslist #UIDs: Real Name (Comment) <email@address>
            keyid = str(key.keyid()) # the key's short id

            if not keyid in self.keysDict:
                self.keysDict[keyid] = key

            for e in uidslist:
                uid = str(e.uid)
                # remove the comment from UID (if it exists)
                com_start = uid.find('(')
                if com_start != -1:
                    com_end = uid.find(')')
                    uid = uid[:com_start].strip() + uid[com_end+1:].strip()

                # split into user's name and email
                tokens = uid.split('<')
                name = tokens[0].strip()
                email = 'unknown'
                if len(tokens) > 1:
                    email = tokens[1].replace('>','').strip()

                self.store.append((name, email, keyid))

        # create the tree view
        self.treeView = Gtk.TreeView(model=self.store)

        # setup 'Name' column
        nameRenderer = Gtk.CellRendererText()
        nameColumn = Gtk.TreeViewColumn("Name", nameRenderer, text=0)

        # setup 'Email' column
        emailRenderer = Gtk.CellRendererText()
        emailColumn = Gtk.TreeViewColumn("Email", emailRenderer, text=1)

        # setup 'Key' column
        keyRenderer = Gtk.CellRendererText()
        keyColumn = Gtk.TreeViewColumn("Key", keyRenderer, text=2)

        self.treeView.append_column(nameColumn)
        self.treeView.append_column(emailColumn)
        self.treeView.append_column(keyColumn)
        
        self.treeView.connect('row-activated', self.on_row_activated)

        # make the tree view resposive to single click selection
        self.treeView.get_selection().connect('changed', self.on_selection_changed)

        # make the tree view scrollable
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.treeView)
        self.scrolled_window.set_min_content_height(200)

        #self.pack_start(self.scrolled_window, True, True, 0)

        self.hpane = Gtk.HPaned()
        self.hpane.pack1(self.scrolled_window, False, False)
        self.right_pane = Gtk.VBox()
        right_label = Gtk.Label(label='Select key on the left')
        self.right_pane.add(right_label)
        # Hm, right now, the width of the right pane changes, when
        # a key is selected, because the right pane's content will be
        # wider when it displays expiration et al.
        # Can we hint at that fact and make the VBox a bit wider than necessary?
        #padded_label = Gtk.Label(label='Select key on the left'*3)
        #self.right_pane.add(padded_label)
        self.hpane.pack2(self.right_pane, True, False)

        self.pack_start(self.hpane, True, True, 0)


    # We could make it a @staticmethod, but the returned items
    # are bound to the model, anyway.  So it probably doesn't
    # make much sense to have a static function, anyway.
    def get_items_from_selection(self, selection=None):
        '''Returns the elements in the ListStore for the given selection'''
        s = selection or self.treeView.get_selection()
        model, paths = s.get_selected_rows()
        name = email = keyid = None
        for path in paths:
            iterator = model.get_iter(path)
            (name, email, keyid) = model.get(iterator, 0, 1, 2)
            break

        return (name, email, keyid)


    def on_selection_changed(self, selection, *args):
        log.debug('Selected new TreeView item %s = %s', selection, args)
        
        name, email, keyid = self.get_items_from_selection(selection)
        
        key = self.keysDict[keyid]
        self.emit('key-selection-changed', keyid)
        
        try:
            exp_date = datetime.fromtimestamp(float(key.expiry))
            expiry = "{:%Y-%m-%d %H:%M:%S}".format(exp_date)
        except ValueError, e:
            expiry = "No expiration date"

        pane = self.right_pane
        for child in pane.get_children():
            # Ouch, this is not very efficient.
            # But this deals with the fact that the first
            # label in the pane is a "Select a key on the left"
            # text.
            pane.remove(child)
        ctx = {'keyid':keyid, 'expiry':expiry, 'sigs':''}
        keyid_label = Gtk.Label(label='Key {keyid}'.format(**ctx))
        expiration_label = Gtk.Label(label='Expires: {expiry}'.format(**ctx))
        #signatures_label = Gtk.Label(label='{sigs} signatures'.format(**ctx))
        publish_button = Gtk.Button(label='Go ahead!'.format(**ctx))
        publish_button.connect('clicked', self.on_publish_button_clicked, key)
        map(pane.add, (keyid_label, expiration_label,
                       #signatures_label,
                       publish_button,))
        pane.show_all()


    def on_row_activated(self, treeview, tree_path, column):
        '''A callback for when the user "activated" a row,
        e.g. by double-clicking an entry.
        
        It emits the key-selected signal.
        '''
        # We just hijack the existing function.
        # I'm sure we could get the required information out of
        # the tree_path and column, but I don't know how.
        name, email, keyid = self.get_items_from_selection()
        self.emit('key-selected', keyid)


    def on_publish_button_clicked(self, button, key, *args):
        '''Callback for when the user has expressed their wish
        to publish a key on the network.  It will emit a "key-selected"
        signal with the ID of the selected key.'''
        log.debug('Clicked publish for key (%s) %s (%s)', type(key), key, args)
        keyid = key.keyid()
        self.emit('key-selected', keyid)




class Keys(Gtk.Application):
    """A widget which displays keys in a user's Keyring.
    
    Once the user has selected a key, the key-selected
    signal will be thrown.
    """
    def __init__(self, *args, **kwargs):
        #super(Keys, self).__init__(*args, **kwargs)
        Gtk.Application.__init__(
            self, application_id="org.gnome.keysign.keys")
        self.connect("activate", self.on_activate)
        self.connect("startup", self.on_startup)

        self.log = logging.getLogger()

        self.keys_page = KeysPage()
        self.keys_page.connect('key-selection-changed',
            self.on_key_selection_changed)
        self.keys_page.connect('key-selected', self.on_key_selected)


    def on_quit(self, app, param=None):
        self.quit()


    def on_startup(self, app):
        self.log.info("Startup")
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title ("Keysign - Keys")
        self.window.add(self.keys_page)


    def on_activate(self, app):
        self.log.info("Activate!")
        #self.window = Gtk.ApplicationWindow(application=app)

        self.window.show_all()
        # In case the user runs the application a second time,
        # we raise the existing window.
        self.window.present()


    def on_key_selection_changed(self, button, key):
        """This is the connected to the KeysPage's key-selection-changed
        signal
        
        As a user of that widget, you would show more details
        in the GUI or prepare for a final commitment by the user.
        """
        self.log.info('Selection changed to: %s', key)


    def on_key_selected(self, button, key):
        """This is the connected to the KeysPage's key-selected signal
        
        As a user of that widget, you would enable buttons or proceed
        with the GUI.
        """
        self.log.info('User committed to a key! %s', key)

                                                
def parse_command_line(argv):
    """Parse command line argument. See -h option

    :param argv: arguments on the command line must include caller file name.
    """
    formatter_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description='Auxiliary helper program '+
                                                 'display keys',
                                     formatter_class=formatter_class)
    parser.add_argument("--version", action="version",
                        version="%(prog)s {}".format(__version__))
    parser.add_argument("-v", "--verbose", dest="verbose_count",
                        action="count", default=0,
                        help="increases log verbosity for each occurence.")
    #parser.add_argument('-o', metavar="output",
    #                    type=argparse.FileType('w'), default=sys.stdout,
    #                    help="redirect output to a file")
    #parser.add_argument('input', metavar="input",
    ## nargs='+', # argparse.REMAINDER,
    #help="input if any...")
    arguments = parser.parse_args(argv[1:])
    # Sets log level to WARN going more verbose for each new -v.
    log.setLevel(max(3 - arguments.verbose_count, 0) * 10)
    return arguments


def main(args=sys.argv):
    """This is an example program of how to use the Keys widget"""
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                        format='%(name)s (%(levelname)s): %(message)s')
    try:
        arguments = parse_command_line(args)
        
        app = Keys()
        try:
            GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
        except AttributeError:
            pass
    
        exit_status = app.run(None)
    
        return exit_status

        
    finally:
        logging.shutdown()

if __name__ == "__main__":
    sys.exit(main())
