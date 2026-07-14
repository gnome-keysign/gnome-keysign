#!/usr/bin/env python3

import logging, sys, os
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

thisdir = os.path.dirname(os.path.realpath(__file__))
# Add parent directory to path so we can import keysign module
sys.path.insert(0, os.path.dirname(thisdir))
from keysign.keyconfirm import PreSignApp

class TestImportApp(PreSignApp):
    def on_activate(self, app):
        super().on_activate(app)
        # Force the "certifications produced" infobar to be visible
        # This contains our new Import button!
        self.psw.infobar_success.set_visible(True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = TestImportApp()
    app.run(sys.argv[1:])
