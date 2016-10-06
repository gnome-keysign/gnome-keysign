#!/usr/bin/env python2

import logging, os, sys, signal
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, format='%(name)s (%(levelname)s): %(message)s')

thisdir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, thisdir)
sys.path.insert(0, os.sep.join((thisdir, 'monkeysign')))

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

