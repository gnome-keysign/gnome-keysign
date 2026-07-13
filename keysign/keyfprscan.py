#!/usr/bin/env python
# encoding: utf-8
#    Copyright 2016 Andrei Macavei <andrei.macavei89@gmail.com>
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

import sys
import logging
import os

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')

from gi.repository import Gtk, Gst, GdkPixbuf
from gi.repository import GObject


if  __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')

from .scan_barcode import BarcodeReaderGTK

log = logging.getLogger(__name__)



class KeyFprScanWidget(Gtk.Box):
    """A widget for obtaining a key fingerprint.

    The fingerprint can be obtain by inserting it into
    a text entry, or by scanning a barcode with the
    built-in camera.
    """

    __gsignals__ = {
        # This is the Gtk widget signal's name
        str('changed'): (GObject.SignalFlags.RUN_LAST, None,
                        (GObject.TYPE_PYOBJECT,)),
        # It's probably not the best name for that signal.
        # While "barcode_scanned" might be better, it is probably
        # unnecessarily specific.
        str('barcode'): (GObject.SignalFlags.RUN_LAST, None,
                        (str, # The barcode string
                         Gst.Message.__gtype__, # The GStreamer message itself
                         GdkPixbuf.Pixbuf.__gtype__,),) # The pixbuf which caused
                                              # the above string to be decoded
    }

    def __init__(self, builder=None):
        log.debug("Init KFSW %r %r", self, builder)
        if issubclass(self.__class__, object):
            super(KeyFprScanWidget, self).__init__(orientation=Gtk.Orientation.VERTICAL)
        else:
            Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        log.debug("Inited parent KFSW %r", self)

        widget_name = 'scanner_widget'
        if not builder:
            thisdir = os.path.dirname(os.path.abspath(__file__))
            builder = Gtk.Builder()
            builder.add_objects_from_file(os.path.join(thisdir, 'receive4.ui'),
                [widget_name])
        widget = builder.get_object(widget_name)
        parent = widget.get_parent()
        if parent:
            parent.remove(widget)
        self.append(widget)
        

        self.scanner = builder.get_object("scanner")

        if not Gst.is_initialized():
            log.error("Gst does not seem to be initialised. Call Gst.init()!")
            # This needs to be called before creating a BarcodeReaderGTK
            Gst.init(None)
        reader = BarcodeReaderGTK()
        reader.set_size_request(150,150)
        reader.connect('barcode', self.on_barcode)
        self.scanner.append(reader)
        # We keep a reference here to not "lose" the object.
        # If we don't, Gtk crashes. With a segfault. Probably
        # because the object is freed but still used.
        # Somebody should look at that...
        self.reader = reader

        self.camera_selector = builder.get_object("comboboxtext1")
        self.camera_devices = {}
        if self.camera_selector:
            self.populate_cameras()

        self.fpr_entry = builder.get_object("fingerprint_entry")
        self.fpr_entry.connect('changed', self.on_text_changed)
        
        self.set_hexpand(True)
        self.set_vexpand(True)

        # Temporary measure...
        self.barcode_scanner = self

    def populate_cameras(self):
        self.camera_selector.remove_all()
        
        monitor = Gst.DeviceMonitor.new()
        monitor.add_filter("Video/Source", None)
        monitor.start()
        devices = monitor.get_devices()
        monitor.stop()
        
        self.camera_devices = {}
        best_suitable_idx = -1
        best_suitable_v4l2 = -1
        
        best_unsuitable_idx = -1
        best_unsuitable_v4l2 = -1
        
        import re
        def get_v4l2_index(path):
            if not path:
                return -1
            m = re.search(r'\d+$', path)
            return int(m.group(0)) if m else -1
        
        for idx, device in enumerate(devices):
            display_name = device.get_display_name()
            props = device.get_properties()
            device_path = None
            if props:
                for key in ["api.v4l2.path", "device.path", "object.path"]:
                    val = props.get_string(key)
                    if val:
                        if val.startswith("v4l2:"):
                            val = val[5:]
                        device_path = val
                        break
            
            if not device_path:
                continue
                
            name_lower = display_name.lower()
            is_unsuitable = "ir" in name_lower or "infrared" in name_lower or "infra-red" in name_lower
            
            v4l2_num = get_v4l2_index(device_path)
            current_idx = len(self.camera_devices)
            item_id = str(current_idx)
            self.camera_devices[item_id] = device_path
            
            if is_unsuitable:
                label = f"⚠️ {display_name} ({device_path}) [IR / Unsuitable]"
                if v4l2_num > best_unsuitable_v4l2:
                    best_unsuitable_v4l2 = v4l2_num
                    best_unsuitable_idx = current_idx
            else:
                label = f"{display_name} ({device_path})"
                if v4l2_num > best_suitable_v4l2:
                    best_suitable_v4l2 = v4l2_num
                    best_suitable_idx = current_idx
            
            self.camera_selector.append(item_id, label)
            
        if self.camera_devices:
            self.camera_selector.connect("changed", self.on_camera_changed)
            if best_suitable_idx != -1:
                default_index = best_suitable_idx
            elif best_unsuitable_idx != -1:
                default_index = best_unsuitable_idx
            else:
                default_index = 0
            self.camera_selector.set_active(default_index)
            default_path = self.camera_devices.get(str(default_index))
            if default_path:
                self.reader.set_device(default_path)

    def on_camera_changed(self, combo):
        active_id = combo.get_active_id()
        if active_id and active_id in self.camera_devices:
            device_path = self.camera_devices[active_id]
            log.info("Camera changed in dropdown to ID %s: %s", active_id, device_path)
            self.reader.set_device(device_path)

    def on_text_changed(self, entryObject, *args):
        self.emit('changed', entryObject, *args)

    def on_barcode(self, sender, barcode, message, image):
        self.emit('barcode', barcode, message, image)

    def get_text(self):
        "Returns the text present in the Entry"
        text = self.fpr_entry.get_text()
        return text

class KeyScanApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super(KeyScanApp, self).__init__(*args, **kwargs)
        self.connect('activate', self.on_activate)
        self.scanwidget = None

        self.log = logging.getLogger(__name__)

    def on_activate(self, app):
        window = Gtk.ApplicationWindow()
        window.set_title("Key Fingerprint Scanner Widget")
        window.set_size_request(600, 400)

        if not self.scanwidget:
            self.scanwidget = KeyFprScanWidget()
        self.scanwidget.connect('changed', self.on_text_changed)
        self.scanwidget.connect('barcode', self.on_barcode)
        window.set_child(self.scanwidget)
        window.present()
        self.add_window(window)

    def on_text_changed(self, keyFprScanWidget, entryObject, *args):
        self.log.debug ("Text changed! %s" % (entryObject.get_text(),))

    def on_barcode(self, sender, barcode, message, image):
        self.log.debug ("Barcode signal %r %r", barcode, message)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    Gst.init(None)
    app = KeyScanApp()
    app.run()
