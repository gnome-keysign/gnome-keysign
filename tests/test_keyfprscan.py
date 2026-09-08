"""Tests for the fingerprint scanning widget.

The widget offers two ways of obtaining a fingerprint: scanning a
barcode with the camera, or typing the fingerprint into an entry.
These tests cover the latter.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gst

Gst.init(None)

from keysign.keyfprscan import KeyFprScanWidget


def test_typing_a_fingerprint_emits_changed():
    """Typing into the entry must make the widget emit "changed".

    The ReceiveApp connects to that signal in order to start looking
    for the key, so without it a manually entered fingerprint is
    silently ignored.
    """
    widget = KeyFprScanWidget()
    seen = []
    widget.connect('changed', lambda w, entry: seen.append(entry.get_text()))

    widget.fpr_entry.set_text("A2E97B5573D25E5B4D5AD66EDF71C6E43409E985")

    assert seen == ["A2E97B5573D25E5B4D5AD66EDF71C6E43409E985"]
    assert widget.get_text() == "A2E97B5573D25E5B4D5AD66EDF71C6E43409E985"


def test_falling_back_to_the_device_monitor_works():
    """We fall back to enumerating devices when the portal denies us.

    That is the very moment we need the fallback to work, so it must
    not raise.
    """
    widget = KeyFprScanWidget()

    widget._fallback_to_device_monitor()
