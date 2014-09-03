#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
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

from gi.repository import Gtk, GdkPixbuf
from qrencode import encode_scaled

log = logging.getLogger()

class QRImage(Gtk.Image):
    """An Image encoding data as a QR Code.
    The image tries to scale as big as possible.
    """
    
    def __init__(self, data='Default String', *args, **kwargs):
        super(QRImage, self).__init__(*args, **kwargs)
        self.log = logging.getLogger()
        # The data to be rendered
        self.data = data
        # FIXME: Rename this to on_size_allocate
        self.connect("size-allocate", self.expose_event)
        self.last_allocation = self.get_allocation()

    def expose_event(self, widget, event):
        # when window is resized, regenerate the QR code
        allocation = self.get_allocation()
        if allocation != self.last_allocation:
            self.last_allocation = allocation
            self.draw_qrcode()

    def draw_qrcode(self, size=None):
        data = self.data
        box = self.get_allocation()
        width, height = box.width, box.height
        size = size or min(width, height) - 10
        if data is not None:
            self.pixbuf = self.image_to_pixbuf(self.create_qrcode(data, size))
            self.set_from_pixbuf(self.pixbuf)
        else:
            self.set_from_icon_name("gtk-dialog-error", Gtk.IconSize.DIALOG)

    @staticmethod
    def create_qrcode(data, size):
        log.debug('Encoding %s', data)
        version, width, image = encode_scaled(data,size,0,1,2,True)
        return image

    @staticmethod
    def image_to_pixbuf(image):
        # convert PIL image instance to Pixbuf
        fd = StringIO.StringIO()
        image.save(fd, "ppm")
        contents = fd.getvalue()
        fd.close()
        loader = GdkPixbuf.PixbufLoader.new_with_type('pnm')
        loader.write(contents)
        pixbuf = loader.get_pixbuf()
        loader.close()
        return pixbuf


class QRWindow():
    pass

def main(data):
    w = Gtk.Window()
    w.connect("delete-event", Gtk.main_quit)
    w.set_default_size(100,100)
    qr = QRImage(data)
    qr.draw_qrcode()
    w.add(qr)
    w.show_all()
    Gtk.main()

if __name__ == '__main__':
    import sys
    data = sys.argv[1]
    main(data)
