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

import cairo
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import Gtk, GdkX11, GdkPixbuf
# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

log = logging.getLogger()





class BarcodeReader(object):

    def on_barcode(self, barcode, message, image):
        '''This is called when a barcode is available
        with barcode being the decoded barcode.
        Message is the GStreamer message containing
        the barcode.'''
        return barcode

    def on_message(self, bus, message):
        log.debug("Message: %s", message)
        if message:
            struct = message.get_structure()
            struct_name = struct.get_name()
            log.debug('Message name: %s', struct_name)
            converted_sample = None
            if struct_name == 'barcode':
                pixbuf = None
                if struct.has_field ("frame"):
                    sample = struct.get_value ("frame")
                    log.info ("uuhh,  found image %s", sample)
                    
                    target_caps = Gst.Caps.from_string('video/x-raw,format=RGBA')
                    converted_sample = GstVideo.video_convert_sample(
                        sample, target_caps, Gst.CLOCK_TIME_NONE)
                                        
                assert struct.has_field('symbol')
                barcode = struct.get_string('symbol')
                log.info("Read Barcode: {}".format(barcode)) 

                self.on_barcode(barcode, message, converted_sample)
                

    def run(self):
        p = "v4l2src "
        #p = "uridecodebin file:///tmp/qr.png "
        p += " ! tee name=t ! queue ! videoconvert "
        p += " ! identity name=ident signal-handoffs=true"
        p += " ! zbar "
        p += " ! fakesink t. ! queue ! videoconvert "
        p += " ! xvimagesink name=imagesink"
        #p += " ! gdkpixbufsink"
        #p = "uridecodebin file:///tmp/qr.png "
        #p += "! tee name=t ! queue ! videoconvert ! zbar ! fakesink t. ! queue ! videoconvert ! xvimagesink name=imagesink'
        self.a = a = Gst.parse_launch(p)
        self.bus = bus = a.get_bus()
        self.imagesink = self.a.get_by_name('imagesink')
        self.ident = self.a.get_by_name('ident')

        bus.connect('message', self.on_message)
        bus.connect('sync-message::element', self.on_sync_message)
        bus.add_signal_watch()
        
        self.ident.connect('handoff', self.on_handoff)

        a.set_state(Gst.State.PLAYING)
        self.running = True
        while self.running and False:
            pass
        #a.set_state(Gst.State.NULL)

    def on_sync_message(self, bus, message):
        log.debug("Sync Message!")
        pass

    
    def on_handoff(self, element, buffer, *args):
        log.debug('Handing of %r', buffer)
        dec_timestamp = buffer.dts
        p_timestamp = buffer.pts
        log.debug("ts: %s", p_timestamp)


class BarcodeReaderGTK(Gtk.DrawingArea, BarcodeReader):

    __gsignals__ = {
        'barcode': (GObject.SIGNAL_RUN_LAST, None,
                    (str, # The barcode string
                     Gst.Message.__gtype__, # The GStreamer message itself
                     Gst.Sample.__gtype__, # The image data containing the barcode
                    ),
                   )
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


    def do_barcode(self, barcode, message, image):
        "This is called by GObject, I think"
        log.debug("Emitting a barcode signal %s, %s", barcode, message)


    def on_barcode(self, barcode, message, image):
        '''You can implement this function to
        get notified when a new barcode has been read.
        If you do, you will not get the GObject "barcode" signal
        as it is emitted from here.'''
        log.debug("About to emit barcode signal: %s", barcode)
        self.emit('barcode', barcode, message, image)



class ReaderApp(Gtk.Application):
    '''A simple application for scanning a bar code
    
    It makes use of the BarcodeReaderGTK class and connects to
    its on_barcode signal.
    
    You need to have called Gst.init() before creating a
    BarcodeReaderGTK.
    '''
    def __init__(self, *args, **kwargs):
        super(ReaderApp, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)

    
    def on_activate(self, data=None):
        window = Gtk.ApplicationWindow()
        window.set_title("Gtk Gst Barcode Reader")
        reader = BarcodeReaderGTK()
        reader.connect('barcode', self.on_barcode)
        window.add(reader)

        window.show_all()
        self.add_window(window)


    def on_barcode(self, reader, barcode, message, image):
        '''All we do is logging the decoded barcode'''
        logging.info('Barcode decoded: %s', barcode)



class SimpleInterface(ReaderApp):
    '''We tweak the UI of the demo ReaderApp a little'''
    def on_activate(self, *args, **kwargs):
        window = Gtk.ApplicationWindow()
        window.set_title("Simple Barcode Reader")
        window.set_default_size(400, 300)

        vbox = Gtk.Box(Gtk.Orientation.HORIZONTAL, 0)
        vbox.set_margin_top(3)
        vbox.set_margin_bottom(3)
        window.add(vbox)

        reader = BarcodeReaderGTK()
        reader.connect('barcode', self.on_barcode)
        vbox.pack_start(reader, True, True, 0)
        self.playing = False

        #self.image = Gtk.Image()
        self.image = ScalingImage()
        vbox.pack_end(self.image, True, True, 0)


        self.playButtonImage = Gtk.Image()
        self.playButtonImage.set_from_stock("gtk-media-play", Gtk.IconSize.BUTTON)
        self.playButton = Gtk.Button.new()
        self.playButton.add(self.playButtonImage)
        self.playButton.connect("clicked", self.playToggled)
        vbox.pack_end(self.playButton, False, False, 0)

        window.show_all()
        self.add_window(window)


    def playToggled(self, w):
        self.run()


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


    def on_barcode(self, reader, barcode, message, sample):
        buffer = sample.get_buffer()
        pixbuf = buffer.extract_dup(0, buffer.get_size())
        
        caps = sample.get_caps()
        struct = caps.get_structure(0)
        
        colorspace = GdkPixbuf.Colorspace.RGB
        alpha = True
        bps = 8
        width_struct = struct.get_int("width")
        assert width_struct[0]
        height_struct = struct.get_int("height")
        assert height_struct[0]
        original_width = width_struct[1]
        original_height = height_struct[1]
        


        for i in range(struct.n_fields()):
            log.debug("Struct field %d name: %s", i, struct.nth_field_name(i))

        rowstride_struct = struct.get_int("stride")
        if rowstride_struct[0] == True:
            # The stride information might be hidden in the struct.
            # For now it doesn't work. I think it's the name of the field.
            rowstride = rowstride_struct[1]
        else:
            rowstride = bps / 8 * 4 * original_width

        log.debug("bytes: %r, colorspace: %r, aplah %r, bps: %r, w: %r, h: %r, r: %r",
            GLib.Bytes.new_take(pixbuf),
            colorspace, alpha, bps, original_width,
            original_height, rowstride,
        )
        gdkpixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new_take(pixbuf),
            colorspace, alpha, bps, original_width,
            original_height, rowstride)


        self.image.set_from_pixbuf(gdkpixbuf, original_width, original_height, rowstride)
        return False



class ScalingImage(Gtk.DrawingArea):

    def __init__(self, pixbuf=None, width=None, height=None, rowstride=None):
        self.pixbuf = pixbuf
        self.width = width or None
        self.height = height or None
        self.rowstride = rowstride or None
        super(ScalingImage, self).__init__()
    
    
    def set_from_pixbuf(self, pixbuf, width=None, height=None, rowstride=None):
        log.debug('Setting Image from Pixbuf (%r x %r)', width, height)
        self.pixbuf = pixbuf

        if width:
            self.width = width

        if height:
            self.height = height

        if rowstride:
            self.rowstride = rowstride


    def do_draw(self, cr, pixbuf=None):
        log.debug('Drawing ScalingImage! %r', self)
        pixbuf = pixbuf or self.pixbuf
        #log.info('Drawing Pixbuf: %r', pixbuf)

        #caps = sample.get_caps()
        #struct = caps.get_structure(0)
        
        #width_struct = struct.get_int("width")
        #assert width_struct[0]
        #height_struct = struct.get_int("height")
        #assert height_struct[0]
        #original_width = width_struct[1]
        #original_height = height_struct[1]
        original_width = self.width
        original_height = self.height
        if not original_width or not original_height:
            log.info('No width in the picture. w: %r, h: %r', original_width, original_height)
            return False
        assert original_width
        assert original_height


        # Scale the pixbuf down to whatever space we have
        allocation = self.get_allocation()
        widget_width = allocation.width
        widget_height = allocation.height
        # I think we might not need this calculation
        widget_size = min(widget_width, widget_height)
        log.info('Allocated size: %s, %s', widget_width, widget_height)
        
        cr.save()
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        cr.set_source_rgb(0, 0, 0)
        cr.translate(widget_width / 2, widget_height / 2)
        # Not sure taking the width here is good
        scale = max(1, widget_width / original_width)
        cr.scale(scale, scale)
        cr.translate(-original_width / 2, -original_width / 2)
        
        pattern = cairo.SurfacePattern(pixbuf)
        pattern.set_filter(cairo.FILTER_NEAREST)
        cr.mask(pattern)
        
        
        cr.restore()
        
        return super(ScalingImage, self).do_draw(cr)
        

        #new_pixbuf = GdkPixbuf.Pixbuf(width=width, height=height)
        new_pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new_take(pixbuf),
            colorspace, alpha, bps,
            width, height,
            width * 4)
        # No idea what all these arguments are...
        ratio = min (1.0 * width / original_width,  1.0 * height / original_height)
        new_width = width * ratio
        new_height = height * ratio
        log.debug("w: %r h: %r (from: %r)", new_width, new_height, ratio)
        assert new_width > 0
        assert new_height > 0
        scaled_pixbuf = gdkpixbuf.scale_simple(
            #0, 0,
            #new_width,  new_height,
            width,  height,
            #0, 0,
            #1.0 * width / original_width,  1.0 * height / original_height,
            GdkPixbuf.InterpType.NEAREST)
        
        self.set_from_pixbuf(scaled_pixbuf)


def main():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                        format='%(name)s (%(levelname)s): %(message)s')

    # We need to have GStreamer initialised before creating a BarcodeReader
    Gst.init(sys.argv)
    app = SimpleInterface()

    try:
        # Exit the mainloop if Ctrl+C is pressed in the terminal.
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : app.quit(), None)
    except AttributeError:
        # Whatever, it is only to enable Ctrl+C anyways
        pass

    app.run()


if __name__ == '__main__':
    main()
