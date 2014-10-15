#!/usr/bin/env python

import logging, sys, signal
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format='%(name)s (%(levelname)s): %(message)s')

from gi.repository import GLib

from keysign.MainWindow import MainWindow

def main():
    app = MainWindow()

    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        pass

    exit_status = app.run(None)
    return exit_status

sys.exit(main())

