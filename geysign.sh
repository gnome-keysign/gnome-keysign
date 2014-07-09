#!/usr/bin/env python

import logging, sys
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
    format='%(name)s (%(levelname)s): %(message)s')

from gi.repository import Gtk
from MainWindow import MainWindow

# setup the main window
window = MainWindow()
window.show_all()

Gtk.main()
