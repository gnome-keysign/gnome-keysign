import os
import pytest
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
from unittest.mock import MagicMock, patch

# Initialize Gst and Adw for GUI tests
gi.require_version('Gst', '1.0')
from gi.repository import Gst
Gst.init(None)
Adw.init()

from keysign.app import KeysignApp

@patch('gi.repository.Gtk.Window.present')
def test_keysign_app_shortcuts(mock_present):
    app = KeysignApp(application_id="org.gnome.Keysign.TestShortcuts")
    with patch('keysign.app.SendApp') as MockSendApp, \
         patch('keysign.app.PswMappingReceiveApp') as MockReceiveApp:
        
        mock_send = MockSendApp.return_value
        mock_send.stack = Gtk.Stack()
        
        mock_receive = MockReceiveApp.return_value
        mock_receive.stack = Gtk.Stack()
        mock_receive.scanner = Gtk.Box()
        
        # Call on_activate to initialize UI and register GActions
        app.on_activate(app)
        
        # Check that our Alt+S and Alt+R GAction shortcuts are registered
        assert app.lookup_action("switch-to-send") is not None
        assert app.lookup_action("switch-to-receive") is not None
        
        # Verify that activating the actions switches the visible child of send_receive_stack
        send_action = app.lookup_action("switch-to-send")
        receive_action = app.lookup_action("switch-to-receive")
        
        # Switch to receive tab
        receive_action.activate()
        assert app.send_receive_stack.get_visible_child_name() == "receive_stack"
        
        # Switch to send tab
        send_action.activate()
        assert app.send_receive_stack.get_visible_child_name() == "send_stack"

@patch('gi.repository.Gtk.Window.present')
def test_scanner_mapped_callback(mock_present):
    app = KeysignApp(application_id="org.gnome.Keysign.TestScannerMap")
    with patch('keysign.app.SendApp') as MockSendApp, \
         patch('keysign.app.PswMappingReceiveApp') as MockReceiveApp:
        
        mock_send = MockSendApp.return_value
        mock_send.stack = Gtk.Stack()
        
        mock_receive = MockReceiveApp.return_value
        mock_receive.stack = Gtk.Stack()
        mock_receive.scanner = Gtk.Box()
        
        app.on_activate(app)
        
        # Call the activation callback directly
        app.on_scanner_mapped(mock_receive.scanner)
        
        # Assert that the header button properties were correctly updated
        assert not app.header_button.get_sensitive()
        assert app.header_button.get_icon_name() == "go-previous"


def test_a_machine_without_avahi_gets_the_dialog():
    """Without avahi-daemon the app falls back to explaining itself.

    The dialog is built from dialog_avahi4.ui, which kept a GTK3-only
    type_hint property long enough to turn that explanation into a
    traceback, and its title was set before the dialog was looked up.
    """
    from keysign.errors import NoAvahiDbus

    presented = []
    app = KeysignApp(application_id="org.gnome.Keysign.TestNoAvahi")
    with patch('keysign.app.SendApp') as MockSendApp, \
         patch('keysign.app.PswMappingReceiveApp',
               side_effect=NoAvahiDbus("no avahi on the bus")), \
         patch('gi.repository.Gtk.Window.present',
               new=lambda window: presented.append(window)):
        MockSendApp.return_value.stack = Gtk.Stack()
        app.on_activate(app)

    assert presented, "nothing was shown at all"
    dialog = presented[0]
    assert isinstance(dialog, Gtk.MessageDialog)
    assert dialog.get_title() == "GNOME Keysign"


def test_get_toplevel_finds_the_window_the_widget_is_in():
    """Signing a key needs the window to parent the email portal on."""
    from keysign.app import PswMappingReceiveApp

    window = Gtk.Window()
    psw = Gtk.Box()
    window.set_child(psw)

    receive = PswMappingReceiveApp.__new__(PswMappingReceiveApp)
    receive.psw = psw

    assert receive.get_toplevel() is window
