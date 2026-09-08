"""Tests for the little program that serves a key from a window."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

import keysign.GtkKeyserver
from keysign.GtkKeyserver import ServerWindow


class FakeServeKeyThread:
    """Stands in for Keyserver.ServeKeyThread, which binds a socket."""

    def __init__(self, keydata, fingerprint):
        self.keydata = keydata
        self.fingerprint = fingerprint
        self.events = []

    def start(self):
        self.events.append("start")

    def shutdown(self):
        self.events.append("shutdown")


def test_the_window_offers_a_button(monkeypatch):
    monkeypatch.setattr(keysign.GtkKeyserver.Keyserver,
                        "ServeKeyThread", FakeServeKeyThread)

    window = ServerWindow()

    assert window.button.get_label() == "Start"


def test_toggling_the_button_starts_and_stops_serving(monkeypatch):
    monkeypatch.setattr(keysign.GtkKeyserver.Keyserver,
                        "ServeKeyThread", FakeServeKeyThread)
    window = ServerWindow()

    window.button.set_active(True)
    assert window.keyserver.events == ["start"]

    window.button.set_active(False)
    assert window.keyserver.events == ["start", "shutdown"]
