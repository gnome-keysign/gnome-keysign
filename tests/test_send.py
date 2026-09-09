"""Tests for the sending part of the UI."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.send import App


def make_app():
    """A send App holding just the header widgets its handlers touch."""
    app = App.__new__(App)
    app.header_button = Gtk.Button()
    app.internet_toggle = Gtk.ToggleButton()
    return app


def test_key_list_page_offers_a_refresh_icon():
    app = make_app()

    app.on_keylist_mapped(None)

    assert app.header_button.get_icon_name() == "view-refresh"
    # We do not support refreshing yet
    assert not app.header_button.get_sensitive()


def test_key_present_page_offers_a_back_icon():
    app = make_app()

    app.on_keypresent_mapped(None)

    assert app.header_button.get_icon_name() == "go-previous"
    assert app.header_button.get_sensitive()


def test_result_page_offers_a_back_icon():
    app = make_app()

    app.on_resultbox_mapped(None)

    assert app.header_button.get_icon_name() == "go-previous"
    assert app.header_button.get_sensitive()
