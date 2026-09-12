"""Exercises switching cameras at runtime, the way the camera selection
dropdown in keyfprscan.py does via BarcodeReaderGTK.set_device()."""

import os
import logging

import qrcode

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gst, GObject, GLib

Gst.init(None)

from keysign.scan_barcode import BarcodeReaderGTK
from test_camera import FakeV4L2Src

log = logging.getLogger(__name__)

registered_v4l2src = False

BARCODE_TEXT = "OPENPGP4FPR:297C02C04C4A9A31E90CEF145F53CA96074E560E"


def setup_module(module):
    global registered_v4l2src

    thisdir = os.path.dirname(os.path.abspath(__file__))
    qr_path = os.path.join(thisdir, "test_barcode.png")
    img = qrcode.make(BARCODE_TEXT)
    img.save(qr_path)

    if not registered_v4l2src:
        GObject.type_register(FakeV4L2Src)
        Gst.Element.register(None, "v4l2src", Gst.Rank.PRIMARY + 100, FakeV4L2Src.__gtype__)
        registered_v4l2src = True


def teardown_module(module):
    thisdir = os.path.dirname(os.path.abspath(__file__))
    qr_path = os.path.join(thisdir, "test_barcode.png")
    if os.path.exists(qr_path):
        os.remove(qr_path)


def test_switching_from_a_blank_camera_to_the_barcode_camera_detects_it():
    # Start on camera 1 (black, no barcode) like the app does by default,
    # then switch to camera 3 (has the barcode) the way the dropdown's
    # on_camera_changed() does, and confirm the barcode now gets detected.
    loop = GLib.MainLoop()
    reader = BarcodeReaderGTK(device="/dev/video0")
    detected = []

    def on_barcode(sender, barcode, message, pixbuf):
        detected.append(barcode)
        loop.quit()

    reader.connect("barcode", on_barcode)
    reader.run()

    GLib.timeout_add_seconds(1, lambda: (reader.set_device("/dev/video2"), False)[1])
    GLib.timeout_add_seconds(6, loop.quit)
    loop.run()

    reader.pipeline.set_state(Gst.State.NULL)

    assert len(detected) == 1
    assert detected[0] == BARCODE_TEXT
