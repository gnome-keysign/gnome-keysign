#!/usr/bin/env python

import signal
import sys

from gi.repository import Gst
from gi.repository import Gtk, GLib

def test():
    print("hello")
    # exist mainloop    
    Gtk.main_quit()
    # Do not run again.
    return False



class BarcodeReader:

    def on_message(self, bus, message):
        if message:
            struct = message.get_structure()
            if struct.get_name() == 'barcode':
                assert struct.has_field('symbol')
                barcode = struct.get_string('symbol')
                print("Read Barcode: {}".format(barcode))
        
    def run(self):
        p = 'v4l2src ! tee name=t ! queue ! videoconvert ! zbar ! fakesink t. ! queue ! xvimagesink'
        self.a = a = Gst.parse_launch(p)
        self.bus = bus = a.get_bus()
        
        bus.connect('message', self.on_message)
        bus.add_signal_watch()
    
        a.set_state(Gst.State.PLAYING)
        running = True
        while running and False:
            pass
        #a.set_state(Gst.State.NULL)

if __name__ == '__main__':
    br = BarcodeReader()
    Gst.init(sys.argv)

    try:
        # Exit the mainloop if Ctrl+C is pressed in the terminal.
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : Gtk.main_quit(), None)
    except AttributeError:
        # Whatever, it is only to enable Ctrl+C anyways
        pass

    GLib.idle_add(br.run)

    Gtk.main()

