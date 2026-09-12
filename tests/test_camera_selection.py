"""Tests for KeyFprScanWidget's camera selection dropdown.

On a PipeWire-enabled desktop (the default since Ubuntu 22.04), the same
physical camera is commonly enumerated twice by GStreamer's plain
Gst.DeviceMonitor: once via the v4l2 device provider (a real /dev/videoN
devnode we can hand to v4l2src), and once via the pipewire device
provider (which only exposes a PipeWire "object.path", not a v4l2
devnode). Blindly falling back to whatever property happens to be
present offers the unusable pipewire duplicate as a "camera", which can
even win the "pick the highest-numbered suitable camera" default
selection -- so the app starts up pointed at a camera it cannot
actually open.
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

from keysign.keyfprscan import KeyFprScanWidget


class FakeProps:
    def __init__(self, d):
        self.d = d

    def get_string(self, key):
        return self.d.get(key)


class FakeDevice:
    def __init__(self, display_name, props):
        self.display_name = display_name
        self.props = FakeProps(props)

    def get_display_name(self):
        return self.display_name

    def get_properties(self):
        return self.props


class FakeMonitor:
    """Stand-in for Gst.DeviceMonitor whose device list is set per-test."""
    devices = []

    def add_filter(self, *a, **kw):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def get_devices(self):
        return FakeMonitor.devices


def _populate(devices, monkeypatch):
    FakeMonitor.devices = devices
    monkeypatch.setattr(Gst.DeviceMonitor, "new", staticmethod(lambda: FakeMonitor()))
    return KeyFprScanWidget()


def test_pipewire_duplicate_of_a_v4l2_camera_is_not_offered(monkeypatch):
    # The same physical webcam, seen through both device providers.
    w = _populate([
        FakeDevice("Integrated Webcam",
                   {"device.api": "v4l2", "device.path": "/dev/video0"}),
        FakeDevice("Integrated Webcam",
                   {"object.path": "/org/freedesktop/pipewire/camera/42"}),
    ], monkeypatch)

    assert w.camera_devices == {"0": "/dev/video0"}
    assert w.reader.device == "/dev/video0"


def test_selecting_a_different_v4l2_camera_still_works(monkeypatch):
    w = _populate([
        FakeDevice("Integrated Webcam",
                   {"device.api": "v4l2", "device.path": "/dev/video0"}),
        FakeDevice("Integrated IR Camera",
                   {"device.api": "v4l2", "device.path": "/dev/video1"}),
        FakeDevice("Logitech USB Camera",
                   {"device.api": "v4l2", "device.path": "/dev/video2"}),
    ], monkeypatch)

    assert w.camera_devices == {"0": "/dev/video0", "1": "/dev/video1", "2": "/dev/video2"}
    # Highest-index suitable (non-IR) camera wins by default.
    assert w.reader.device == "/dev/video2"

    w.camera_selector.set_active_id("0")
    assert w.reader.device == "/dev/video0"
