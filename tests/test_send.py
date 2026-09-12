"""Regression tests for keysign.send.SendApp.show_result()."""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.send import SendApp


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
