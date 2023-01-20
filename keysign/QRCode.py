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

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk, GObject
import qrcode

## It seems python3-cairo does not implement Surface.create_for_data
## https://bugs.freedesktop.org/show_bug.cgi?id=99855
## Also, the gi version of cairo seems to be mostly useless,
## so either pycairo or cairocffi needs to exist.
## Rumour has it, though, that cairocffi cannot work well together
## with the CairoContext exposed in the do_draw method that we are trying to
## overwrite.  So we're back to square one and need to take pycairo.
import cairo


log = logging.getLogger(__name__)

class QRImage(Gtk.DrawingArea):
    """An Image encoding data as a QR Code.
    The image tries to scale as big as possible.
    """
    
    def __init__(self, data='Default String', handle_events=True,
                       background=0xff, *args, **kwargs):
        """The QRImage widget inherits from Gtk.Image,
        but it probably cannot be used as one, as there
        is an event handler for resizing events which will
        overwrite to currently loaded image.
        
        You made set data now, or later simply via the property.
        
        handle_events can be set to False if the fullscreen
        window should not be created on click.
        
        The background can be set to 0x00 (or 0xff) creating a
        black (or white) background onto which the code is rendered.
        """
        super(QRImage, self).__init__(*args, **kwargs)
        self.log = logging.getLogger(__name__)

        self.background = background
        # We invert the background
        self.foreground = 0xff ^ background

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
            top_level_window = self.get_toplevel()
            if top_level_window.is_toplevel():
                w.set_transient_for(top_level_window)


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

        background = self.background
        foreground = self.foreground

        # This seems to set the background,
        # but I'm not sure...
        cr.set_source_rgb(background, background, background)
        #cr.fill()
        # And have it painted
        cr.paint()
        # Now, I think we set the colour of the turtle
        # paint whatever is coming next.
        cr.set_source_rgb(foreground, foreground, foreground)
        # All of the rest I do not really understand,
        # but it seems to work reasonably well, without
        # weird PIL to Pixbuf hacks.
        cr.translate(width / 2, height / 2)
        scale = max(1, size / img_size)
        cr.scale(scale, scale)
        cr.translate(-img_size / 2, -img_size / 2)

        pattern = cairo.SurfacePattern(qrcode)
        pattern.set_filter(cairo.FILTER_NEAREST)
        cr.mask(pattern)

        cr.restore()

    def create_qrcode(self, data):
        log.debug('Encoding %s', data)
        code = qrcode.QRCode()

        code.add_data(data)

        matrix = code.get_matrix()
        size = len(matrix)
        stride = (size + 3) // 4 * 4
        log.debug("stride: %r  size: %r", stride, size)
        data = bytearray(stride * size)

        background = self.background
        foreground = self.foreground

        for x in range(size):
            for y in range(size):
                # Here we seem to be defining what
                # is going to be put on the surface.
                # I don't know what the semantic is,
                # though. Is 0 black? Or no modification
                # of the underlying background?
                # Anyway, this give us a nice white
                # QR Code.  Note that we do [y][x],
                # otherwise the generated code is diagonally
                # mirrored.
                if matrix[y][x]:
                    data[x + y * stride] = background
                else:
                    data[x + y * stride] = foreground

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
        
        self.set_tooltip_text(data)

    def get_data(self):
        return self._data

    data = GObject.Property(getter=get_data, setter=set_data)


def fullscreen_at_monitor(window, n):
    """Fullscreens a given window on the n-th monitor

    This is because Gtk's fullscreen_on_monitor seems to
    be buggy.
    http://stackoverflow.com/a/39386341/2015768
    """
    screen = Gdk.Screen.get_default()

    monitor_n_geo = screen.get_monitor_geometry(n)
    x = monitor_n_geo.x
    y = monitor_n_geo.y

    window.move(x,y)

    window.fullscreen()


class FullscreenQRImageWindow(Gtk.Window):
    '''Displays a QRImage in a fullscreen window
    
    The window is supposed to close itself when a button is
    clicked.'''

    def __init__(self, data, *args, **kwargs):
        '''The data will be passed to the QRImage'''
        self.log = logging.getLogger(__name__)
        if issubclass(self.__class__, object):
            super(FullscreenQRImageWindow, self).__init__(*args, **kwargs)
        else:
            Gtk.Window.__init__(*args, **kwargs)

        self.fullscreen()
        
        self.qrimage = QRImage(data=data, handle_events=False)
        self.qrimage.set_has_tooltip(False)
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
        elif keyname == 'left' or keyname == 'right':
            # We're trying to switch monitors
            screen = self.get_screen()
            # Determines the monitor the window is currently most visible in
            n = screen.get_monitor_at_window(screen.get_active_window())
            n_monitors = screen.get_n_monitors()

            if keyname == 'left':
                delta = -1
            elif keyname == 'right':
                delta = 1
            else:
                raise ValueError()

            new_n = (n+delta) % n_monitors
            log.info("Moving from %d to %d/%d", n, new_n, n_monitors)
            if n != new_n:
                # This call would make it animate a little,
                # but it looks weird for me, so we don't unfullscreen.
                # self.unfullscreen()
                fullscreen_at_monitor(self, new_n)
                # The following call is broken, unfortunately.
                # https://bugzilla.gnome.org/show_bug.cgi?id=752677
                # self.fullscreen_on_monitor(self.get_screen(), new_n)


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
    try:
        data = sys.argv[1]
    except:
        raise ValueError("Not Enough Arguments passed as data for the QR code encoding")
    main(data)
