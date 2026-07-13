import os
import logging
import pytest
HAVE_CAMERA_DEPS = False
try:
    import qrcode
    from PIL import Image
    HAVE_CAMERA_DEPS = True
except ImportError:
    qrcode = None

pytestmark = pytest.mark.skipif(not HAVE_CAMERA_DEPS, reason="Missing camera test dependencies (qrcode or PIL)")

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gst, GObject, Gtk, GLib

Gst.init(None)

from keysign.scan_barcode import BarcodeReaderGTK

log = logging.getLogger(__name__)

# Define the pad template for the custom Gst.Bin
pad_template = Gst.PadTemplate.new(
    "src",
    Gst.PadDirection.SRC,
    Gst.PadPresence.ALWAYS,
    Gst.Caps.from_string("video/x-raw")
)

# Global flag to ensure we only register once
registered_v4l2src = False

class FakeV4L2Src(Gst.Bin):
    __gsttemplates__ = (pad_template,)

    @GObject.Property(type=str, default="/dev/video0")
    def device(self):
        return self._device

    @device.setter
    def device(self, value):
        self._device = value
        if self.src:
            self.remove(self.src)
            self.src = None
        
        # Resolve test barcode file location
        thisdir = os.path.dirname(os.path.abspath(__file__))
        qr_path = os.path.join(thisdir, "test_barcode.png")

        if value == "/dev/video0":
            # Camera 1: Black stream
            self.src = Gst.ElementFactory.make("videotestsrc", None)
            self.src.set_property("pattern", 2) # black
        elif value == "/dev/video1":
            # Camera 2: Snow/noise stream
            self.src = Gst.ElementFactory.make("videotestsrc", None)
            self.src.set_property("pattern", 1) # snow
        else:
            # Camera 3: Web-camera with barcode/QR code
            self.src = Gst.parse_bin_from_description(
                f"filesrc location={qr_path} ! pngdec ! imagefreeze",
                True
            )
        
        self.add(self.src)
        pad = self.src.get_static_pad("src")
        if not pad:
            pad = self.src.get_pads()[0]
        
        old_pad = self.get_static_pad("src")
        if old_pad:
            self.remove_pad(old_pad)
            
        ghost_pad = Gst.GhostPad.new("src", pad)
        self.add_pad(ghost_pad)

    def __init__(self):
        super().__init__()
        self.src = None
        self._device = "/dev/video0"
        self.set_property("device", "/dev/video0")

def setup_module(module):
    global registered_v4l2src
    
    # Generate test barcode image
    thisdir = os.path.dirname(os.path.abspath(__file__))
    qr_path = os.path.join(thisdir, "test_barcode.png")
    barcode_text = "OPENPGP4FPR:297C02C04C4A9A31E90CEF145F53CA96074E560E"
    img = qrcode.make(barcode_text)
    img.save(qr_path)
    
    if not registered_v4l2src:
        GObject.type_register(FakeV4L2Src)
        Gst.Element.register(None, "v4l2src", Gst.Rank.PRIMARY + 100, FakeV4L2Src.__gtype__)
        registered_v4l2src = True

def teardown_module(module):
    # Remove test barcode image
    thisdir = os.path.dirname(os.path.abspath(__file__))
    qr_path = os.path.join(thisdir, "test_barcode.png")
    if os.path.exists(qr_path):
        os.remove(qr_path)

def test_camera_1_no_barcode():
    # Camera 1 should not detect anything
    loop = GLib.MainLoop()
    reader = BarcodeReaderGTK(device="/dev/video0")
    detected = []
    
    def on_barcode(sender, barcode, message, pixbuf):
        detected.append(barcode)
        loop.quit()
        
    reader.connect("barcode", on_barcode)
    reader.run()
    
    GLib.timeout_add_seconds(2, loop.quit)
    loop.run()
    reader.pipeline.set_state(Gst.State.NULL)
    
    assert len(detected) == 0

def test_camera_2_no_barcode():
    # Camera 2 should not detect anything
    loop = GLib.MainLoop()
    reader = BarcodeReaderGTK(device="/dev/video1")
    detected = []
    
    def on_barcode(sender, barcode, message, pixbuf):
        detected.append(barcode)
        loop.quit()
        
    reader.connect("barcode", on_barcode)
    reader.run()
    
    GLib.timeout_add_seconds(2, loop.quit)
    loop.run()
    reader.pipeline.set_state(Gst.State.NULL)
    
    assert len(detected) == 0

def test_camera_3_detects_barcode():
    # Camera 3 should detect the QR code successfully
    loop = GLib.MainLoop()
    reader = BarcodeReaderGTK(device="/dev/video2")
    detected = []
    
    def on_barcode(sender, barcode, message, pixbuf):
        detected.append(barcode)
        loop.quit()
        
    reader.connect("barcode", on_barcode)
    reader.run()
    
    GLib.timeout_add_seconds(5, loop.quit)
    loop.run()
    reader.pipeline.set_state(Gst.State.NULL)
    
    assert len(detected) == 1
    assert detected[0] == "OPENPGP4FPR:297C02C04C4A9A31E90CEF145F53CA96074E560E"
