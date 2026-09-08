#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
#    Copyright 2014 Srdjan Grubor <sgnn7@sgnn7.org>
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

'''This is an exercise to see how we can combine Python threads
with the Gtk mainloop
'''

import logging
import os
import sys

from threading import Thread

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib
from gi.repository import Gtk
from dbus.mainloop.glib import DBusGMainLoop

if  __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')

from . import Keyserver

class ServerWindow(Gtk.Window):
    def __init__(self):
        self.log = logging.getLogger(__name__)

        Gtk.Window.__init__(self, title="Gtk and Python threads")
        self.keyserver = None

        hBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hBox.set_margin_top(10)
        hBox.set_margin_bottom(10)
        hBox.set_margin_start(10)
        hBox.set_margin_end(10)
        self.button = Gtk.ToggleButton(label='Start')
        hBox.append(self.button)
        self.set_child(hBox)

        self.button.connect('toggled', self.on_button_toggled)

        #GLib.idle_add(self.setup_server)

    def on_button_toggled(self, button):
        self.log.debug('toggled button')
        if button.get_active():
            self.log.debug("I am being switched on")
            self.setup_server()
        else:
            self.log.debug("I am being switched off")
            self.stop_server()

    def setup_server(self):
        self.log.info('Serving now')
        self.log.debug('About to call %r', Keyserver.ServeKeyThread)
        self.keyserver = Keyserver.ServeKeyThread(b'Keydata', 'fingerprint')
        self.log.info('Starting thread %r', self.keyserver)
        self.keyserver.start()
        self.log.info('Finsihed serving')

        return False

    def stop_server(self):
        self.keyserver.shutdown()

def main(args):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)

    DBusGMainLoop(set_as_default=True)

    app = Gtk.Application(application_id='org.gnome.keysign.gtkkeyserver')

    def on_activate(app):
        w = ServerWindow()
        w.set_application(app)
        w.present()

    app.connect('activate', on_activate)
    log.debug('Starting main')
    # Closing the last window quits the application, which is what the
    # delete-event handler used to do for us.
    return app.run(None)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    # From http://stackoverflow.com/a/16486080/2015768
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(main(sys.argv))
