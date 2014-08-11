#!/usr/bin/env python

import logging, sys, signal
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format='%(name)s (%(levelname)s): %(message)s')

from gi.repository import GLib
from MainWindow import MainWindow

def main():
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : Gtk.main_quit(), None)
    except AttributeError:
        pass

    app = MainWindow()
    exit_status = app.run(None)
    return exit_status

sys.exit(main())

