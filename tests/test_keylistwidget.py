"""Tests for the list of keys we offer to send."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.keylistwidget import KeyListWidget


def test_says_so_when_there_are_no_keys():
    """With no usable secret key there is nothing to list, so we say that.

    This is the first thing a user without a key sees, so it had better
    not raise.
    """
    widget = KeyListWidget([])

    row = widget.listbox.get_first_child()
    assert row is not None, "nothing was put in the list box"
    label = row.get_child()
    assert "OpenPGP keys" in label.get_text()
