#!/usr/bin/env python

import sys

from gi.repository import Gst



def main():
    p = 'v4l2src ! tee name=t ! queue ! videoconvert ! zbar ! fakesink t. ! queue ! xvimagesink'
    Gst.init(sys.argv)
    a = Gst.parse_launch(p)
    a.set_state(Gst.State.PLAYING)
    running = True
    
    while running:
        message = a.get_bus().pop_filtered(Gst.MessageType.ELEMENT)
        if message:
            struct = message.get_structure()
            if struct.get_name() == 'barcode':
                assert struct.nth_field_name(2) == 'symbol'
                barcode = struct.get_string('symbol')
                print("Read Barcode: {}".format(barcode))

    a.set_state(Gst.State.NULL)
     
if __name__ == '__main__':
    main()
