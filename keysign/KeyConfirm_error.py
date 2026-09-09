import sys
import os
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

# Setup Python path to import keysign
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))

from keysign.keyconfirm import PreSignWidget

class DummyUID:
    def __init__(self, uid):
        self.uid = uid

class DummyKey:
    def __init__(self):
        self.fingerprint = "1234567890ABCDEF1234567890ABCDEF12345678"
        self.uidslist = [DummyUID("Test User <test@example.com>")]

def on_activate(app):
    window = Gtk.ApplicationWindow(application=app)
    window.set_title("Key Pre Sign Error Test")
    window.set_default_size(600, 400)

    key = DummyKey()
    psw = PreSignWidget(key)
    
    window.set_child(psw)
    window.present()
    
    # Programmatically trigger the error info bar
    try:
        raise RuntimeError("This is a simulated GPG error during certification!")
    except Exception as e:
        psw.infobar_errors.show(e)
        print("Error triggered! Click the 'Details' button in the UI to see the dialog.")

if __name__ == "__main__":
    app = Gtk.Application()
    app.connect('activate', on_activate)
    app.run(sys.argv)
