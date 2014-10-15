#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
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

import argparse
import logging
import signal
import sys

from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import Gtk, GdkX11
# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

log = logging.getLogger()



def test():
    print("hello")
    # exist mainloop
    Gtk.main_quit()
    # Do not run again.
    return False



class BarcodeReader(object):

    def on_barcode(self, barcode, message):
        '''This is called when a barcode is available
        with barcode being the decoded barcode.
        Message is the GStreamer message containing
        the barcode.'''
        return barcode

    def on_message(self, bus, message):
        log.debug("Message: %s", message)
        if message:
            struct = message.get_structure()
            if struct.get_name() == 'barcode':
                assert struct.has_field('symbol')
                barcode = struct.get_string('symbol')
                log.info("Read Barcode: {}".format(barcode))
                self.on_barcode(barcode, message)

    def run(self):
        p = 'v4l2src ! tee name=t ! queue ! videoconvert ! zbar ! fakesink t. ! queue ! videoconvert ! xvimagesink'
        #p = 'uridecodebin file:///tmp/image.jpg ! tee name=t ! queue ! videoconvert ! zbar ! fakesink t. ! queue ! videoconvert ! xvimagesink'
        self.a = a = Gst.parse_launch(p)
        self.bus = bus = a.get_bus()

        bus.connect('message', self.on_message)
        bus.connect('sync-message::element', self.on_sync_message)
        bus.add_signal_watch()

        a.set_state(Gst.State.PLAYING)
        self.running = True
        while self.running and False:
            pass
        #a.set_state(Gst.State.NULL)

    def on_sync_message(self, bus, message):
        log.debug("Sync Message!")
        pass

class BarcodeReaderGTK(Gtk.DrawingArea, BarcodeReader):

    __gsignals__ = {
        'barcode': (GObject.SIGNAL_RUN_LAST, None,
                    (str, Gst.Message.__gtype__))
    }


    def __init__(self, *args, **kwargs):
        super(BarcodeReaderGTK, self).__init__(*args, **kwargs)

    @property
    def x_window_id(self, *args, **kwargs):
        window = self.get_property('window')
        # If you have not requested a size, the window might not exist
        assert window, "Window is %s (%s), but not a window" % (window, type(window))
        self._x_window_id = xid = window.get_xid()
        return xid

    def on_message(self, bus, message):
        log.debug("Message: %s", message)
        struct = message.get_structure()
        assert struct
        name = struct.get_name()
        log.debug("Name: %s", name)
        if name == "prepare-window-handle":
            log.debug('XWindow ID')
            message.src.set_window_handle(self.x_window_id)
        else:
            return super(BarcodeReaderGTK, self).on_message(bus, message)

    def do_realize(self, *args, **kwargs):
        #super(BarcodeReaderGTK, self).do_realize(*args, **kwargs)
        # ^^^^ does not work :-\
        Gtk.DrawingArea.do_realize(self)
        #self.run()
        #self.connect('hide', self.on_hide)
        self.connect('unmap', self.on_unmap)
        self.connect('map', self.on_map)


    def on_map(self, *args, **kwargs):
        '''It seems this is called when the widget is becoming visible'''
        self.run()

    def do_unrealize(self, *args, **kwargs):
        '''This appears to be called when the app is destroyed,
        not when a tab is hidden.'''
        self.a.set_state(Gst.State.NULL)
        Gtk.DrawingArea.do_unrealize(self)


    def on_unmap(self, *args, **kwargs):
        '''Hopefully called when this widget is hidden,
        e.g. when the tab of a notebook has changed'''
        self.a.set_state(Gst.State.PAUSED)
        # Actually, we stop the thing for real
        self.a.set_state(Gst.State.NULL)


    def do_barcode(self, barcode, message):
        "This is called by GObject, I think"
        log.debug("Emitting a barcode signal %s, %s", barcode, message)


    def on_barcode(self, barcode, message):
        '''You can implement this function to
        get notified when a new barcode has been read.
        If you do, you will not get the GObject "barcode" signal
        as it is emitted from here.'''
        log.debug("About to emit barcode signal: %s", barcode)
        self.emit('barcode', barcode, message)

class SimpleInterface(BarcodeReader):
    def __init__(self, *args, **kwargs):
        super(SimpleInterface, self).__init__(*args, **kwargs)

        self.playing = False

        # GTK window and widgets
        self.window = Gtk.Window()
        self.window.set_size_request(300,350)
        self.window.connect('delete-event', Gtk.main_quit)

        vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
        vbox.set_margin_top(3)
        vbox.set_margin_bottom(3)
        self.window.add(vbox)

        self.da = Gtk.DrawingArea()
        self.da.set_size_request (250, 200)
        self.da.show()
        #self.window.add(self.da)
        #vbox.add(self.da)
        vbox.pack_start(self.da, False, False, 0)


        self.playButtonImage = Gtk.Image()
        self.playButtonImage.set_from_stock("gtk-media-play", Gtk.IconSize.BUTTON)
        self.playButton = Gtk.Button.new()
        self.playButton.add(self.playButtonImage)
        self.playButton.connect("clicked", self.playToggled)
        vbox.pack_start(self.playButton, False, False, 1)

        self.window.show_all()


        da_win = self.da.get_property('window')
        assert da_win
        self.xid = da_win.get_xid()


    def playToggled(self, w):
        print("Play!")
        self.run()
        pass

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        if message.structure.get_name() == 'prepare-window-handle':
            #self.videoslot.set_sink(message.src)
            message.src.set_window_handle(self.xid)


    def on_message(self, bus, message):
        log.debug("Message: %s", message)
        struct = message.get_structure()
        assert struct
        name = struct.get_name()
        log.debug("Name: %s", name)
        if name == "prepare-window-handle":
            log.debug('XWindow ID')
            #self.videoslot.set_sink(message.src)
            message.src.set_window_handle(self.xid)
        else:
            return super(SimpleInterface, self).on_message(bus, message)






def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                        format='%(name)s (%(levelname)s): %(message)s')
    br = BarcodeReader()
    Gst.init(sys.argv)

    try:
        # Exit the mainloop if Ctrl+C is pressed in the terminal.
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : Gtk.main_quit(), None)
    except AttributeError:
        # Whatever, it is only to enable Ctrl+C anyways
        pass

    #GLib.idle_add(br.run)

    SimpleInterface()
    Gtk.main()


if __name__ == '__main__':
    main()
