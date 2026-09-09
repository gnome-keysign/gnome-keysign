"""Tests for the receiving side of the UI.

When a transfer fails, the transports hand us wildly different things as
the "message": an exception class, an exception instance, a plain string
meant for the user, or nothing at all.  All of them end up in the same
label.
"""

import logging
from unittest.mock import MagicMock

from wormhole.errors import TransferError

from keysign.receive import ReceiveApp


def shown_error(message):
    """The text ReceiveApp puts in front of the user for this message."""
    receive = ReceiveApp.__new__(ReceiveApp)
    receive.log = logging.getLogger(__name__)
    receive.stack = MagicMock()
    receive.rb = MagicMock()
    receive.result_label = MagicMock()

    receive.on_message_received(None, False, message)

    receive.result_label.set_label.assert_called_once()
    return receive.result_label.set_label.call_args[0][0]


def test_error_from_an_exception_class():
    """Wormhole reports failures as the exception class itself."""
    assert "transfer" in shown_error(TransferError).lower()


def test_error_from_a_string():
    """Discover reports some failures as a ready-made sentence.

    Rendering __doc__ of a str shows the user the docstring of Python's
    str type, which tells them nothing about their key.
    """
    message = "Error downloading key, maybe it has been altered in transit"

    assert shown_error(message) == message


def test_error_from_an_exception_instance():
    """Bluetooth reports failures as the exception it caught."""
    shown = shown_error(OSError(113, "No route to host"))

    assert "No route to host" in shown


def test_error_without_a_message():
    """Bluetooth reports a failed MAC check without any message at all.

    There is nothing to say beyond "it did not work", but we still have
    to say something rather than raise.
    """
    shown = shown_error(None)

    assert shown
