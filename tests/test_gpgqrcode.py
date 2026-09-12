"""Tests for the little program that shows a key's QR code."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.GPGQRCode import build_window
from keysign.QRCode import QRImage

DATA = "OPENPGP4FPR:A2E97B5573D25E5B4D5AD66EDF71C6E43409E985"


def test_the_window_shows_the_data_and_its_qr_code():
    window = build_window(DATA)

    box = window.get_child()
    label = box.get_first_child()
    assert label.get_text() == DATA

    qrcode = label.get_next_sibling()
    assert isinstance(qrcode, QRImage)
    assert qrcode.data == DATA
