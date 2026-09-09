"""Tests for camera_portal.py — D-Bus interactions and pipewiresrc pipeline."""

import os
import logging
import pytest
from unittest import mock
from unittest.mock import MagicMock, patch, call

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '4.0')
from gi.repository import Gst, GObject, GLib
Gst.init(None)

import qrcode
from keysign.scan_barcode import BarcodeReaderGTK

log = logging.getLogger(__name__)


# ===== Group A: D-Bus Mock Tests =====

class TestIsCameraPortalAvailable:
    """Test is_camera_portal_available() D-Bus queries."""

    @patch('keysign.camera_portal.dbus')
    def test_returns_true_when_camera_present(self, mock_dbus):
        """IsCameraPresent=True → returns True."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_proxy = MagicMock()
        mock_bus.get_object.return_value = mock_proxy
        mock_props = MagicMock()
        mock_dbus.Interface.return_value = mock_props
        mock_props.Get.return_value = True

        from keysign.camera_portal import is_camera_portal_available
        result = is_camera_portal_available()

        assert result is True
        mock_bus.get_object.assert_called_once_with(
            'org.freedesktop.portal.Desktop',
            '/org/freedesktop/portal/desktop')
        mock_props.Get.assert_called_once_with(
            'org.freedesktop.portal.Camera',
            'IsCameraPresent')

    @patch('keysign.camera_portal.dbus')
    def test_returns_false_when_no_camera(self, mock_dbus):
        """IsCameraPresent=False → returns False."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_proxy = MagicMock()
        mock_bus.get_object.return_value = mock_proxy
        mock_props = MagicMock()
        mock_dbus.Interface.return_value = mock_props
        mock_props.Get.return_value = False

        from keysign.camera_portal import is_camera_portal_available
        assert is_camera_portal_available() is False

    @patch('keysign.camera_portal.dbus')
    def test_returns_false_on_dbus_exception(self, mock_dbus):
        """DBusException (portal not present) → returns False."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_dbus.exceptions.DBusException = Exception
        mock_bus.get_object.side_effect = Exception(
            "No such interface")

        from keysign.camera_portal import is_camera_portal_available
        assert is_camera_portal_available() is False


class TestRequestCameraAccess:
    """Test request_camera_access() D-Bus call sequence."""

    @patch('keysign.camera_portal.DBusGMainLoop')
    @patch('keysign.camera_portal.dbus')
    def test_calls_access_camera(self, mock_dbus, mock_mainloop):
        """Verify AccessCamera is called with handle_token."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_bus.get_unique_name.return_value = ':1.42'
        mock_portal = MagicMock()
        mock_bus.get_object.return_value = mock_portal
        mock_dbus.Dictionary = dict
        mock_dbus.String = str

        callback = MagicMock()
        from keysign.camera_portal import request_camera_access
        request_camera_access(callback)

        # Verify AccessCamera was called
        mock_portal.AccessCamera.assert_called_once()
        call_args = mock_portal.AccessCamera.call_args
        options = call_args[0][0]
        assert 'handle_token' in options

        # Verify signal receiver was added for Response
        mock_bus.add_signal_receiver.assert_called_once()
        sig_kwargs = mock_bus.add_signal_receiver.call_args
        assert sig_kwargs[1]['signal_name'] == 'Response'

    @patch('keysign.camera_portal.DBusGMainLoop')
    @patch('keysign.camera_portal.dbus')
    def test_granted_calls_open_pipewire_remote(self, mock_dbus,
                                                 mock_mainloop):
        """response=0 → OpenPipeWireRemote called, fd passed to callback."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_bus.get_unique_name.return_value = ':1.42'
        mock_portal = MagicMock()
        mock_bus.get_object.return_value = mock_portal
        mock_dbus.Dictionary = dict
        mock_dbus.String = str
        mock_dbus.exceptions.DBusException = Exception

        # Mock OpenPipeWireRemote to return an fd object
        mock_fd_obj = MagicMock()
        mock_fd_obj.take.return_value = 42
        mock_portal.OpenPipeWireRemote.return_value = mock_fd_obj

        callback = MagicMock()
        from keysign.camera_portal import request_camera_access
        request_camera_access(callback)

        # Extract the on_response handler that was registered
        on_response = mock_bus.add_signal_receiver.call_args[0][0]

        # Simulate portal granting access
        on_response(0, {})

        # Verify OpenPipeWireRemote was called
        mock_portal.OpenPipeWireRemote.assert_called_once()
        mock_fd_obj.take.assert_called_once()
        callback.assert_called_once_with(True, 42)

    @patch('keysign.camera_portal.DBusGMainLoop')
    @patch('keysign.camera_portal.dbus')
    def test_denied_calls_callback_false(self, mock_dbus, mock_mainloop):
        """response!=0 → callback(False, None)."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_bus.get_unique_name.return_value = ':1.42'
        mock_portal = MagicMock()
        mock_bus.get_object.return_value = mock_portal
        mock_dbus.Dictionary = dict
        mock_dbus.String = str

        callback = MagicMock()
        from keysign.camera_portal import request_camera_access
        request_camera_access(callback)

        on_response = mock_bus.add_signal_receiver.call_args[0][0]
        on_response(1, {})  # Denied

        callback.assert_called_once_with(False, None)

    @patch('keysign.camera_portal.DBusGMainLoop')
    @patch('keysign.camera_portal.dbus')
    def test_dbus_exception_calls_callback_false(self, mock_dbus,
                                                  mock_mainloop):
        """DBusException during AccessCamera → callback(False, None)."""
        mock_bus = MagicMock()
        mock_dbus.SessionBus.return_value = mock_bus
        mock_dbus.exceptions.DBusException = Exception
        mock_bus.get_object.side_effect = Exception("No portal")

        callback = MagicMock()
        from keysign.camera_portal import request_camera_access
        request_camera_access(callback)

        callback.assert_called_once_with(False, None)


# ===== Group B: Pipeline Construction Tests =====


class TestPipelineConstruction:
    """Verify correct pipeline source element selection."""

    @patch.object(Gst, 'parse_launch')
    def test_default_uses_autovideosrc(self, mock_parse):
        """No device, no fd → autovideosrc."""
        mock_parse.return_value = MagicMock()
        reader = BarcodeReaderGTK()
        reader.run()
        pipeline_str = mock_parse.call_args[0][0]
        assert 'autovideosrc' in pipeline_str
        assert 'v4l2src' not in pipeline_str
        assert 'pipewiresrc' not in pipeline_str

    @patch.object(Gst, 'parse_launch')
    def test_device_uses_v4l2src(self, mock_parse):
        """device="/dev/video0" → v4l2src device=/dev/video0."""
        mock_parse.return_value = MagicMock()
        reader = BarcodeReaderGTK(device="/dev/video0")
        reader.run()
        pipeline_str = mock_parse.call_args[0][0]
        assert 'v4l2src device=/dev/video0' in pipeline_str

    @patch.object(Gst, 'parse_launch')
    def test_pipewire_fd_uses_pipewiresrc(self, mock_parse):
        """pipewire_fd=42 → pipewiresrc fd=42."""
        mock_parse.return_value = MagicMock()
        reader = BarcodeReaderGTK(pipewire_fd=42)
        reader.run()
        pipeline_str = mock_parse.call_args[0][0]
        assert 'pipewiresrc fd=42' in pipeline_str
        assert 'v4l2src' not in pipeline_str

    @patch.object(Gst, 'parse_launch')
    def test_pipewire_fd_takes_priority_over_device(self, mock_parse):
        """Both pipewire_fd and device set → pipewiresrc wins."""
        mock_parse.return_value = MagicMock()
        reader = BarcodeReaderGTK(device="/dev/video0", pipewire_fd=42)
        reader.run()
        pipeline_str = mock_parse.call_args[0][0]
        assert 'pipewiresrc fd=42' in pipeline_str


# ===== Group C: End-to-End QR Decode via Fake pipewiresrc =====

# Pad template for fake pipewiresrc
_pw_pad_template = Gst.PadTemplate.new(
    "src",
    Gst.PadDirection.SRC,
    Gst.PadPresence.ALWAYS,
    Gst.Caps.from_string("video/x-raw")
)

_registered_pipewiresrc = False

class FakePipeWireSrc(Gst.Bin):
    """Mock pipewiresrc that produces a QR code video stream.

    Accepts an 'fd' property (like the real pipewiresrc) but ignores
    it and instead generates frames from a QR code PNG image.
    """
    __gsttemplates__ = (_pw_pad_template,)

    @GObject.Property(type=int, default=-1)
    def fd(self):
        return self._fd

    @fd.setter
    def fd(self, value):
        self._fd = value

    def __init__(self):
        super().__init__()
        self._fd = -1
        self.src = None

        # Generate QR code image
        thisdir = os.path.dirname(os.path.abspath(__file__))
        qr_path = os.path.join(thisdir, "test_portal_barcode.png")
        if not os.path.exists(qr_path):
            barcode_text = (
                "OPENPGP4FPR:"
                "A2E97B5573D25E5B4D5AD66EDF71C6E43409E985")
            img = qrcode.make(barcode_text)
            img.save(qr_path)

        self.src = Gst.parse_bin_from_description(
            f"filesrc location={qr_path} ! pngdec ! imagefreeze",
            True)
        self.add(self.src)

        pad = self.src.get_static_pad("src")
        if not pad:
            pad = self.src.get_pads()[0]
        ghost_pad = Gst.GhostPad.new("src", pad)
        self.add_pad(ghost_pad)


def _register_fake_pipewiresrc():
    """Register FakePipeWireSrc as 'pipewiresrc' at high priority."""
    global _registered_pipewiresrc
    if not _registered_pipewiresrc:
        GObject.type_register(FakePipeWireSrc)
        Gst.Element.register(
            None, "pipewiresrc",
            Gst.Rank.PRIMARY + 100,
            FakePipeWireSrc.__gtype__)
        _registered_pipewiresrc = True


def setup_module(module):
    """Module-level setup: register fake pipewiresrc and generate QR."""
    _register_fake_pipewiresrc()

    thisdir = os.path.dirname(os.path.abspath(__file__))
    qr_path = os.path.join(thisdir, "test_portal_barcode.png")
    barcode_text = (
        "OPENPGP4FPR:"
        "A2E97B5573D25E5B4D5AD66EDF71C6E43409E985")
    img = qrcode.make(barcode_text)
    img.save(qr_path)


def teardown_module(module):
    thisdir = os.path.dirname(os.path.abspath(__file__))
    qr_path = os.path.join(thisdir, "test_portal_barcode.png")
    if os.path.exists(qr_path):
        os.remove(qr_path)


def test_pipewiresrc_barcode_decodes_qr():
    """End-to-end: pipewiresrc fd=99 → QR stream → barcode signal."""
    loop = GLib.MainLoop()
    reader = BarcodeReaderGTK(pipewire_fd=99)
    detected = []

    def on_barcode(sender, barcode, message, pixbuf):
        detected.append(barcode)
        loop.quit()

    reader.connect("barcode", on_barcode)
    reader.run()

    # Timeout after 5 seconds
    GLib.timeout_add_seconds(5, loop.quit)
    loop.run()
    reader.pipeline.set_state(Gst.State.NULL)

    assert len(detected) == 1
    assert detected[0] == (
        "OPENPGP4FPR:"
        "A2E97B5573D25E5B4D5AD66EDF71C6E43409E985")
