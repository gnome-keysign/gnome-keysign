#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#    Copyright 2015 Benjamin Berg <benjamin@sipsolutions.de>
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
import StringIO

from gi.repository import Gdk, Gtk, GObject
import qrcode
import cairo

log = logging.getLogger()

class QRImage(Gtk.DrawingArea):
    """An Image encoding data as a QR Code.
    The image tries to scale as big as possible.
    """
    
    def __init__(self, data='Default String', handle_events=True,
                       *args, **kwargs):
        """The QRImage widget inherits from Gtk.Image,
        but it probably cannot be used as one, as there
        is an event handler for resizing events which will
        overwrite to currently loaded image.
        
        You made set data now, or later simply via the property.
        
        handle_events can be set to False if the fullscreen
        window should not be created on click.
        """
        super(QRImage, self).__init__(*args, **kwargs)
        self.log = logging.getLogger()
        # The data to be rendered
        self._surface = None
        self.data = data
        self.set_app_paintable(True)

        self.handle_events = handle_events
        if handle_events:
            self.connect('button-release-event', self.on_button_released)
            self.add_events(
                Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)


    def on_button_released(self, widget, event):
        self.log.info('Event %s', dir(event))
        if event.button == 1:
            w = FullscreenQRImageWindow(data=self.data)


    def do_size_allocate(self, event):
        """This is the event handler for the resizing event, i.e.
        when window is resized. We then want to regenerate the QR code.
        """
        allocation = self.get_allocation()
        if allocation != event:
            self.queue_draw()
        Gtk.DrawingArea.do_size_allocate(self, event)

    def do_draw(self, cr):
        """This scales the QR Code up to the widget's
        size. You may define your own size, but you must
        be careful not to cause too many resizing events.
        When you request a too big size, it may loop to death
        trying to fit the image.
        """
        data = self.data
        box = self.get_allocation()
        width, height = box.width, box.height
        size = min(width, height)

        qrcode = self.qrcode
        img_size = qrcode.get_width()

        cr.save()
        cr.set_source_rgb(1, 1, 1)
        cr.paint()
        cr.set_source_rgb(0, 0, 0)
        cr.translate(width / 2, height / 2)
        scale = max(1, size / img_size)
        cr.scale(scale, scale)
        cr.translate(-img_size / 2, -img_size / 2)

        pattern = cairo.SurfacePattern(qrcode)
        pattern.set_filter(cairo.FILTER_NEAREST)
        cr.mask(pattern)

        cr.restore()

    @staticmethod
    def create_qrcode(data):
        log.debug('Encoding %s', data)
        code = qrcode.QRCode()

        code.add_data(data)

        matrix = code.get_matrix()
        size = len(matrix)
        stride = (size + 3) / 4 * 4
        data = bytearray(stride * size)

        for x in xrange(size):
            for y in xrange(size):
                if matrix[x][y]:
                    data[x + y * stride] = 0xff

        surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_A8, size, size, stride)

        return surface

    @property
    def qrcode(self):
        if self._surface is not None:
            return self._surface

        self._surface = self.create_qrcode(self.data)
        return self._surface

    def set_data(self, data):
        # FIXME: Full screen window is not updated in here ...
        self._data = data
        self._surface = None

        size = self.qrcode.get_width()
        self.set_size_request(size, size)

        self.queue_draw()

    def get_data(self):
        return self._data

    data = GObject.property(getter=get_data, setter=set_data)

class FullscreenQRImageWindow(Gtk.Window):
    '''Displays a QRImage in a fullscreen window
    
    The window is supposed to close itself when a button is
    clicked.'''

    def __init__(self, data, *args, **kwargs):
        '''The data will be passed to the QRImage'''
        self.log = logging.getLogger()
        if issubclass(self.__class__, object):
            super(FullscreenQRImageWindow, self).__init__(*args, **kwargs)
        else:
            Gtk.Window.__init__(*args, **kwargs)

        self.fullscreen()
        
        self.qrimage = QRImage(data=data, handle_events=False)
        self.add(self.qrimage)
        
        self.connect('button-release-event', self.on_button_released)
        self.connect('key-release-event', self.on_key_released)
        self.add_events(
            Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.KEY_RELEASE_MASK |
            Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
            )

        self.show_all()


    def on_button_released(self, widget, event):
        '''Connected to the button-release-event and closes this
        window''' # It's unclear whether all resources are free()d
        self.log.info('Event on fullscreen: %s', event)
        if event.button == 1:
            self.unfullscreen()
            self.hide()
            self.close()

    def on_key_released(self, widget, event):
        self.log.info('Event on fullscreen: %s', dir(event))
        self.log.info('keycode: %s', event.get_keycode())
        self.log.info('keyval: %s', event.get_keyval())
        self.log.info('keyval: %s', Gdk.keyval_name(event.keyval))
        keyname = Gdk.keyval_name(event.keyval).lower()
        if keyname == 'escape' or keyname == 'f' or keyname == 'q':
            self.unfullscreen()
            self.hide()
            self.close()


def main(data):
    w = Gtk.Window()
    w.connect("delete-event", Gtk.main_quit)
    w.set_default_size(100,100)
    qr = QRImage(data)

    global fullscreen
    fullscreen = False

    def on_released(widget, event):
        global fullscreen
 
        if event.button == 1:
            fullscreen = not fullscreen
            if fullscreen:
                w.fullscreen()
            else:
                w.unfullscreen()
        
    #qr.connect('button-release-event', on_released)
    #qr.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.BUTTON_PRESS_MASK)
    w.add(qr)
    w.show_all()
    Gtk.main()

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    data = sys.argv[1]
    main(data)
