#!/usr/bin/env python

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
    def run(self):
        p = 'v4l2src ! tee name=t ! queue ! videoconvert ! zbar ! fakesink t. ! queue ! xvimagesink'
        Gst.init(sys.argv)
        self.a = a = Gst.parse_launch(p)
        self.bus = bus = a.get_bus()
        
        def my_handler(bus, message):
            message = bus.pop_filtered(Gst.MessageType.ELEMENT)
            if message:
                struct = message.get_structure()
                if struct.get_name() == 'barcode':
                    assert struct.nth_field_name(2) == 'symbol'
                    barcode = struct.get_string('symbol')
                    print("Read Barcode: {}".format(barcode))
        
        bus.connect('message', my_handler)
        bus.add_signal_watch()
    
        a.set_state(Gst.State.PLAYING)
        running = True
        while running and False:
            pass
        #a.set_state(Gst.State.NULL)

if __name__ == '__main__':
    br = BarcodeReader()
    GLib.idle_add(br.run)

    Gtk.main()

