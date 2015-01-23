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

__version__ = '0.2'


def main():
    # These imports were moved here because the keysign module
    # can be imported without wanting to run it, e.g. setup.py
    # imports the __version__
    import logging, sys, signal
    
    from gi.repository import GLib, Gtk
    
    from .MainWindow import MainWindow

    app = MainWindow()

    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        pass

    exit_status = app.run(None)

    return exit_status



if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr,
        level=logging.DEBUG,
        format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main())

