#!/usr/bin/env python
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

"""This is a very simple QR Code generator which scans your GnuPG keyring
for keys and selects the one matching your input
"""
import logging
import os
import sys

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


from .gpgmeh import get_usable_keys

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


from .QRCode import QRImage


def build_window(data, application=None):
    """Returns a window showing the data and the QR code encoding it"""
    w = Gtk.Window(application=application)
    w.set_default_size(100, 100)
    v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    v.append(Gtk.Label(label=data))
    v.append(QRImage(data))
    w.set_child(v)
    return w


def main():
    key = sys.argv[1]
    # Heh, we take the first key here. Maybe we should raise a warning
    # or so, when there is more than one key.
    key = list(get_usable_keys(pattern=key))[0]
    fpr = key.fingerprint
    data = 'OPENPGP4FPR:' + fpr

    app = Gtk.Application(application_id='org.gnome.keysign.gpgqrcode')

    def on_activate(app):
        build_window(data, application=app).present()

    app.connect('activate', on_activate)
    # Closing the last window quits the application, which is what the
    # delete-event handler used to do for us.
    return app.run(None)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                        format='%(name)s (%(levelname)s): %(message)s')
    main()
