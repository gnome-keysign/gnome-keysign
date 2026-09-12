"""Tests for the sending part of the UI."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.send import App, SendApp


def make_app():
    """A send App holding just the header widgets its handlers touch."""
    app = App.__new__(App)
    app.header_button = Gtk.Button()
    app.internet_toggle = Gtk.ToggleButton()
    return app


def make_send_app():
    """A SendApp holding just the widgets show_result()/deactivate() touch."""
    app = SendApp.__new__(SendApp)
    app.offer = None
    app.stack = Gtk.Stack()
    app.stack_saved_visible_child = None
    app.rb = Gtk.Box()
    app.kpw = Gtk.Box()
    app.stack.add_child(app.kpw)
    app.result_label = Gtk.Label()
    app.success_label = Gtk.Label()
    app.password_error_label = Gtk.Label()
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


def test_show_result_can_be_called_more_than_once():
    """offer.start() hands show_result() (via _received) to one Deferred
    per transport (Avahi, wormhole, Bluetooth), so it can run more than
    once for the same send attempt: it must not crash on the second
    call, after self.kpw is already gone.
    """
    app = make_send_app()

    app.show_result(True, "")
    kpw_after_first_call = app.kpw

    app.show_result(True, "")

    assert kpw_after_first_call is None
    assert app.kpw is None


def test_show_result_after_deactivate_does_not_crash():
    """deactivate() (e.g. the user pressing Back) already clears kpw. A
    transport's Deferred that was still in flight can call show_result()
    afterwards regardless, and it must handle kpw being gone already.
    """
    app = make_send_app()

    app.deactivate()
    assert app.kpw is None

    app.show_result(True, "")
