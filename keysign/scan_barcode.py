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

import argparse
import logging
import signal
import sys

import cairo
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import Gtk, GdkX11, GdkPixbuf
# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo
from gi.repository import Gdk

log = logging.getLogger()





class BarcodeReader(object):

    def __init__(self, *args, **kwargs):
        self.timestamp = None
        self.scanned_barcode = None
        self.zbar_message = None

        return super(BarcodeReader, self).__init__(*args, **kwargs)


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
            if struct:
                struct_name = struct.get_name()
                log.debug('Message name: %s', struct_name)

                if struct_name == 'GstMessageError':
                    err, debug = message.parse_error()
                    log.error('GstError: %s, %s', err, debug)
    
                elif struct_name == 'barcode':
                    self.timestamp = struct.get_clock_time("timestamp")[1]
                    log.debug ("at %s", self.timestamp)

                    assert struct.has_field('symbol')
                    barcode = struct.get_string('symbol')
                    log.info("Read Barcode: {}".format(barcode)) 

                    pixbuf = None
                    if struct.has_field ("frame"):
                        # This is the new zbar, which posts the frame along
                        # with the barcode.  It might be too new for users.
                        sample = struct.get_value ("frame")
                        pixbuf = gst_sample_to_pixbuf(sample)
                        self.on_barcode(barcode, message, pixbuf)
                    else:
                        # If we do not see the newer zbar, we save the
                        # barcode symbol now along with its timestamp.
                        # There should be a pixbuf on the bus with
                        # the same timestamp which we will then collect.
                        self.timestamp = struct.get_clock_time("timestamp")[1]
                        self.scanned_barcode = barcode
                        self.zbar_message = message
                        
                elif struct_name == 'pixbuf':
                    # Here we check whether the pixbuf is unsolicitated,
                    # e.g. a "regular" pixbuf or the one belonging to the
                    # barcode we have just scanned.  Note that if we
                    # haven't scanned a barcode yet, self.timestamp
                    # should be None.  We also use None instead of just
                    # if self.timestamp because the timestamp might be 0.
                    if self.timestamp is not None:
                        pixbuf_timestamp = struct.get_clock_time("timestamp")[1]
                        if pixbuf_timestamp == self.timestamp:
                            log.debug('Pixbuf %r matches barcode seen at %r',
                                      struct, pixbuf_timestamp)

                            if not struct.has_field("pixbuf"):
                                log.error("Why does the pixbuf message not "
                                          "contain a pixbuf field? %r", struct)
                                for i in range(struct.n_fields()):
                                    log.debug("Struct field %d name: %s",
                                              i, struct.nth_field_name(i))
                            else:
                                pixbuf = struct.get_value("pixbuf")
                                barcode = self.scanned_barcode
                                message = self.zbar_message
                                self.timestamp = None
                                self.scanned_barcode = None
                                self.zbar_message = None
                                self.set_pixbuf_post_messages(False)
                                self.on_barcode(barcode, message, pixbuf)
                    


    def run(self):
        p = "v4l2src \n"
        ## FIXME: When using an image, the recorded frame is somewhat
        ##        greenish.  I think we need to investigate that at some stage.
        #p = "uridecodebin uri=file:///tmp/qr.png "
        p += " ! tee name=t \n"
        p += "       t. ! queue ! videoconvert \n"
        p += "                  ! zbar %(attach_frame)s \n"
        p += "       t. ! queue ! videoconvert \n"
        p += "                  ! xvimagesink name=imagesink \n"

        # It's getting ugly down here.  What these lines do is trying to
        # detect whether we have a new enough GStreamer, i.e. 1.6+, where
        # the zbar element has the required "attach-frame" property.
        # If the element does not have such a property, parse_launch will
        # fail.  We try to detect our special case to not break other
        # error messages.  If we detect an old GStreamer version,
        # we simply discard "attach-frame" and work around the limitation
        # of the zbar element.
        pipeline_s = p % {
              # Without the fakesink the zbar element seems to not work
              'attach_frame':'attach-frame=true !  fakesink \n'
        }
        try:
            pipeline = Gst.parse_launch(pipeline_s)
        except GLib.Error as e:
            if 'no property "attach-frame" in element' in e.message:
                # We assume that the zbar element has no attach-frame
                # property, because GStramer is too old.
                # The property was introduced with GStreamer 1.6 with
                # 1246d93f3e32a13c95c70cf3ba0f26b224de5e58
                # https://bugzilla.gnome.org/show_bug.cgi?id=747557
                log.info('Running with GStreamer <1.5.1, '
                         'using a (slow) pixbufsink')
                pipeline_s = p % {
                    'attach_frame':'  ! videoconvert  \n'
                                   '  ! gdkpixbufsink name=pixbufsink \n'
                                   '                  post-messages=false \n'
                }
                try:
                    pipeline = Gst.parse_launch(pipeline_s)
                except:
                    raise
                else:
                    # We install this handler only if we do not
                    # have the newer GStreamer version
                    pipeline.get_bus().set_sync_handler(self.bus_sync_handler)
            else:
                raise
            
        self.bus = bus = pipeline.get_bus()
        self.imagesink = pipeline.get_by_name('imagesink')
        self.pipeline = pipeline

        bus.connect('message', self.on_message)
        bus.connect('sync-message::element', self.on_sync_message)
        bus.add_signal_watch()
        
        pipeline.set_state(Gst.State.PLAYING)
        self.running = True


    def bus_sync_handler(self, bus, message, data=None):
        '''A simple handler which only checks for the message being
        from the zbar element and then makes the pixbufsink post messages
        
        This is to save some computing costs for the pixbuf conversion.
        Some performance impact is measurable, but only a couple of
        percent CPU usage.
        
        Always returns Gst.BusSyncReply.PASS so that messages
        will be dispatched as usual.
        '''
        log.info('Sync handler for message %r', message)
        if message:
            struct = message.get_structure()
            if struct:
                struct_name = struct.get_name()
                if struct_name == 'barcode':
                    self.set_pixbuf_post_messages(True)

        return Gst.BusSyncReply.PASS


    def on_sync_message(self, bus, message):
        log.debug("Sync Message!")
        pass


    def set_pixbuf_post_messages(self, value):
        'Locates the element with the name "pixbufsink" and sets post-messages'
        pixbufsink = self.pipeline.get_by_name('pixbufsink')
        assert(pixbufsink is not None)
        return pixbufsink.set_property('post-messages', value)


#class BarcodeReaderGTK(Gtk.DrawingArea, BarcodeReader):
class BarcodeReaderGTK(BarcodeReader, Gtk.DrawingArea):

    __gsignals__ = {
        str('barcode'): (GObject.SIGNAL_RUN_LAST, None,
                        (str, # The barcode string
                         Gst.Message.__gtype__, # The GStreamer message itself
                         GdkPixbuf.Pixbuf.__gtype__, # The pixbuf which caused
                                              # the above string to be decoded
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
        if "X11" in window.__format__(""):
            xid = window.get_xid()
        elif "Wayland" in window.__format__(""):
            self.window_xid = 0
        else:
            log.warning("Don't know how to handle windowing system %r",
                        window.__format__(""))
            self.window_xid = 0


        self._x_window_id = xid
        return xid

    def on_message(self, bus, message):
        log.debug("Message: %s %r", message, message.type)
        struct = message.get_structure()
        if not struct:
            log.debug('Message has no struct')
        else:
            name = struct.get_name()
            log.debug("Name: %s", name)
            if name == "prepare-window-handle":
                log.debug('XWindow ID')
                message.src.set_window_handle(self.x_window_id)

                return

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
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.DrawingArea.do_unrealize(self)


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


    def on_barcode(self, reader, barcode, message, pixbuf):
        self.image.set_from_pixbuf(pixbuf)
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
        self.width = width or None
        self.height = height or None
        self.rowstride = rowstride or None
        super(ScalingImage, self).__init__()
    
    
    def set_from_pixbuf(self, pixbuf):
        self.pixbuf = pixbuf
        self.queue_draw()


    def do_draw(self, cr, pixbuf=None):
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
            allocation = self.get_allocation()
            widget_width = allocation.width
            widget_height = allocation.height
            
            
            # I think we might not need this calculation
            #widget_size = min(widget_width, widget_height)
            #log.info('Allocated size: %s, %s', widget_width, widget_height)
            
            # Fill in background
            cr.save()
            cr.set_source_rgb(1, 1, 1)
            cr.paint()
            
            # Centering and scaling the image to fit the widget
            cr.translate(widget_width / 2.0, widget_height / 2.0)
            scale = min(widget_width / float(original_width), widget_width / float(original_width))
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
