"""Tests for saving the certifications we produced to a file."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gio, GLib

import keysign.receive
from keysign.receive import ReceiveApp


def test_write_certifications_writes_every_plaintext(tmp_path):
    target = tmp_path / "certifications.asc"

    ReceiveApp.write_certifications(str(target), [b"first\n", b"second\n"])

    assert target.read_bytes() == b"first\nsecond\n"


class FakeFileDialog:
    """Enough of Gtk.FileDialog to drive the save without a user."""

    instances = []

    def __init__(self):
        self.title = None
        self.result = None
        FakeFileDialog.instances.append(self)

    def set_title(self, title):
        self.title = title

    def set_initial_name(self, name):
        self.initial_name = name

    def save(self, parent, cancellable, callback):
        callback(self, "an opaque GAsyncResult")

    def save_finish(self, result):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_saving_writes_to_the_file_the_user_chose(tmp_path, monkeypatch):
    target = tmp_path / "chosen.asc"

    def make_dialog():
        dialog = FakeFileDialog()
        dialog.result = Gio.File.new_for_path(str(target))
        return dialog

    monkeypatch.setattr(keysign.receive.Gtk, "FileDialog", make_dialog)

    receive = ReceiveApp.__new__(ReceiveApp)
    receive.log = keysign.receive.log
    receive.get_toplevel = lambda: None

    receive.save_certifications([b"a certification"])

    assert target.read_bytes() == b"a certification"


def test_cancelling_the_save_writes_nothing(tmp_path, monkeypatch):
    """save_finish() raises when the user dismisses the dialog."""

    def make_dialog():
        dialog = FakeFileDialog()
        dialog.result = GLib.Error("Dismissed by user")
        return dialog

    monkeypatch.setattr(keysign.receive.Gtk, "FileDialog", make_dialog)

    receive = ReceiveApp.__new__(ReceiveApp)
    receive.log = keysign.receive.log
    receive.get_toplevel = lambda: None

    receive.save_certifications([b"a certification"])

    assert list(tmp_path.iterdir()) == []
