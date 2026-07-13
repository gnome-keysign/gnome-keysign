#!/usr/bin/env python
#    Copyright 2014, 2015 Tobias Mueller <muelli@cryptobitch.de>
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

import logging
import signal
import sys

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import Gtk, GdkPixbuf
from gi.repository import GstVideo
from gi.repository import Gdk

log = logging.getLogger(__name__)



class BarcodeReaderGTK(Gtk.Box):

    __gsignals__ = {
        str('barcode'): (GObject.SignalFlags.RUN_LAST, None,
                        (str, # The barcode string
                         Gst.Message.__gtype__, # The GStreamer message itself
                         GdkPixbuf.Pixbuf.__gtype__, # The pixbuf which caused
                                              # the above string to be decoded
                    ),
                   )
    }


    def __init__(self, *args, **kwargs):
        super(BarcodeReaderGTK, self).__init__(*args, **kwargs)
        self.connect('unmap', self.on_unmap)
        self.connect('map', self.on_map)
        self.scaling_image = ScalingImage()
        self.append(self.scaling_image)


    def on_message(self, bus, message):
        #log.debug("Message: %s", message)
        if message:
            struct = message.get_structure()
            if struct:
                struct_name = struct.get_name()
                #log.debug('Message name: %s', struct_name)

                if struct_name == 'GstMessageError':
                    err, debug = message.parse_error()
                    log.error('GstError: %s, %s', err, debug)
                elif struct_name == 'GstMessageWarning':
                    err, debug = message.parse_warning()
                    log.warning('GstWarning: %s, %s', err, debug)
    
                elif struct_name == 'barcode':
                    self.timestamp = struct.get_clock_time("timestamp")[1]
                    log.debug ("at %s", self.timestamp)

                    assert struct.has_field('symbol')
                    barcode = struct.get_string('symbol')
                    log.info("Read Barcode: {}".format(barcode))

                    pixbuf = None
                    if struct.has_field ("frame"):
                        # This is the new zbar, which posts the frame along
                        # with the barcode.
                        sample = struct.get_value ("frame")
                        pixbuf = gst_sample_to_pixbuf(sample)
                        self.emit("barcode", barcode, message, pixbuf)
                    else:
                        # If we do not see the zbar < 1.6, we raise
                        raise Exception("Zbar version is not what we expected")


    def run(self):
        p = "autovideosrc  \n"
        p += " ! tee name=t \n"
        p += "       t. ! queue ! videoconvert \n"
        p += "                  ! zbar cache=true attach_frame=true \n"
        p += "                  ! fakesink \n"
        p += "       t. ! queue ! videoconvert \n"
        p += ("                 ! appsink "
            "sync=false "
            "name=imagesink "
            "emit-signals=true "
            "max-buffers=1 "
            "drop=true "
            "caps=\"video/x-raw,format=RGBA\" "
            "\n"
            )

        pipeline = p
        log.info("Launching pipeline %s", pipeline)
        pipeline = Gst.parse_launch(pipeline)

        self.imagesink = pipeline.get_by_name('imagesink')
        self.imagesink.connect("new-sample", self.on_new_sample)

        self.pipeline = pipeline

        bus = pipeline.get_bus()
        bus.connect('message', self.on_message)
        bus.add_signal_watch()

        pipeline.set_state(Gst.State.PLAYING)


    def on_new_sample(self, appsink):
        sample = appsink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.ERROR

        buf = sample.get_buffer()
        caps = sample.get_caps()
        struct = caps.get_structure(0)
        width = struct.get_value("width")
        height = struct.get_value("height")

        data = buf.extract_dup(0, buf.get_size())
        gbytes = GLib.Bytes.new_take(data)

        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
            gbytes,
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            width,
            height,
            width * 4
        )

        GLib.idle_add(self.scaling_image.set_from_pixbuf, pixbuf)
        return Gst.FlowReturn.OK


    def pause(self):
        self.pipeline.set_state(Gst.State.PAUSED)


    def on_map(self, *args, **kwargs):
        '''It seems this is called when the widget is becoming visible'''
        self.run()


    def on_unmap(self, *args, **kwargs):
        '''Hopefully called when this widget is hidden,
        e.g. when the tab of a notebook has changed'''
        self.pipeline.set_state(Gst.State.PAUSED)
        # Actually, we stop the thing for real
        self.pipeline.set_state(Gst.State.NULL)


    def do_barcode(self, barcode, message, image):
        "This is called by GObject, I think"
        log.debug("Emitting a barcode signal %s, %s, %r",
                  barcode, message, image)





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
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Gtk Gst Barcode Reader")
        reader = BarcodeReaderGTK()
        reader.connect('barcode', self.on_barcode)
        window.set_child(reader)

        window.present()


    def on_barcode(self, reader, barcode, message, image):
        '''All we do is logging the decoded barcode'''
        logging.info('Barcode decoded: %s', barcode)



class SimpleInterface(ReaderApp):
    '''We tweak the UI of the demo ReaderApp a little'''
    def on_activate(self, *args, **kwargs):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Simple Barcode Reader")
        window.set_default_size(400, 300)

        vbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        vbox.set_margin_top(3)
        vbox.set_margin_bottom(3)
        window.set_child(vbox)

        reader = BarcodeReaderGTK()
        reader.connect('barcode', self.on_barcode)
        vbox.append(reader)
        self.reader = reader

        #self.image = Gtk.Image()
        # FIXME: We could show a default image like "no barcode scanned just yet"
        self.image = ScalingImage()
        self.imagebox = Gtk.Box() #expand=True)
        self.imagebox.append(self.image)
        vbox.append(self.imagebox)


        self.playButton = Gtk.ToggleButton()
        self.playButton.set_icon_name("media-playback-pause-symbolic")
        self.playButton.connect("toggled", self.playToggled)
        vbox.append(self.playButton)

        window.present()


    def playToggled(self, button):
        if button.get_active():
            self.reader.pause()
            button.set_icon_name("media-playback-start-symbolic")
        else:
            self.reader.pipeline.set_state(Gst.State.PLAYING)
            button.set_icon_name("media-playback-pause-symbolic")


    def on_barcode(self, reader, barcode, message, pixbuf):
        log.info("Barcode!!1 %r", barcode)

        # Hrm. Somehow, the Gst Widget is allocating
        # space relatively aggressively.  Our imagebox on
        # the right side does not get any space.
        #self.imagebox.remove(self.image)
        #self.image = ScalingImage(pixbuf)
        #self.imagebox.pack_start(self.image, True, True, 0)
        #self.image.set_property('expand', True)
        #self.image.show()
        self.image.set_from_pixbuf(pixbuf)

        # So we just show a window instead...
        w = Gtk.Window()
        w.set_child(ScalingImage(pixbuf))
        w.present()
        return False



def gst_sample_to_pixbuf(sample):
    '''Converts the image from a given GstSample to a GdkPixbuf'''
    caps = Gst.Caps.from_string("video/x-raw,format=RGBA")
    converted_sample = GstVideo.video_convert_sample(sample, caps, Gst.CLOCK_TIME_NONE)

    buffer = converted_sample.get_buffer()
    pixbuf = buffer.extract_dup(0, buffer.get_size())
    
    caps = converted_sample.get_caps()
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

    rowstride_struct = struct.get_int("stride")
    if rowstride_struct[0] == True:
        # The stride information might be hidden in the struct.
        # For now it doesn't work. I think it's the name of the field.
        rowstride = rowstride_struct[1]
    else:
        rowstride = bps / 8 * 4 * original_width

    gdkpixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        GLib.Bytes.new_take(pixbuf),
        colorspace, alpha, bps, original_width,
        original_height, rowstride)
        
    return gdkpixbuf




class ScalingImage(Gtk.DrawingArea):

    def __init__(self, pixbuf=None, width=None, height=None, rowstride=None):
        self.pixbuf = pixbuf
        self.rowstride = rowstride or None
        super(ScalingImage, self).__init__()
        #self.set_property("width_request", 400)
        #self.set_property("height_request", 400)
        #self.set_property("margin", 10)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self.draw_func, None)
    
    def draw_func(self, drawing_area, cr, width, height, user_data):
        self.do_draw(cr, widget_width=width, widget_height=height)
    
    def set_from_pixbuf(self, pixbuf):
        self.pixbuf = pixbuf
        self.queue_draw()


#    def do_size_allocate(self, allocation):
#        log.debug("Size Allocate  %r", allocation)
#        log.debug("w: %r  h: %r",  allocation.width, allocation.height)
#        self.queue_draw()

    def do_draw(self, cr, pixbuf=None, widget_width=None, widget_height=None):
        log.debug('Drawing ScalingImage! %r', self)
        pixbuf = pixbuf or self.pixbuf
        if not pixbuf:
            log.info('No pixbuf to draw! %r', pixbuf)
        else:
            original_width = pixbuf.get_width()
            original_height = pixbuf.get_height()
    
            assert original_width > 0
            assert original_height > 0
    
    
            # Scale the pixbuf down to whatever space we have
            if widget_width is None or widget_height is None:
                allocation = self.get_allocation()
                widget_width = allocation.width
                widget_height = allocation.height
            
            
            # I think we might not need this calculation
            #widget_size = min(widget_width, widget_height)
            log.info('Allocated size: %s, %s', widget_width, widget_height)
            
            # Fill in background
            cr.save()
            #Gtk.render_background(self.get_style_context(),
            #       cr, 0, 0, widget_width, widget_height)
            #cr.set_source_rgb(1, 1, 1)
            #cr.paint()
            
            # Centering and scaling the image to fit the widget
            cr.translate(widget_width / 2.0, widget_height / 2.0)
            scale = min(widget_width / float(original_width), widget_height / float(original_height))
            cr.scale(scale, scale)
            
            cr.translate(-original_width / 2.0, -original_height / 2.0)
            # Note: This function is very inefficient
            # (one could cache the resulting pattern or image surface)!
            Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
            # Should anyone want to set filters, this is the way to do it.
            #pattern = cr.get_source()
            #pattern.set_filter(cairo.FILTER_NEAREST)
            cr.paint()
            cr.restore()
            
            return
            #super(ScalingImage, self).do_draw(cr)



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
