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

import signal
import sys
import argparse
import logging

from gi.repository import Gtk, GLib

# These are relative imports
from __init__ import __version__
from SignPages import KeysPage

log = logging.getLogger()


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
