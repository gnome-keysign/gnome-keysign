"""Tests for offering a key over Bluetooth.

These do not need a Bluetooth adapter: we hand the offer a stand-in for
the listening socket and read the key off an ordinary socketpair.
"""

import os
import socket
import tempfile
from subprocess import check_call

from pytest_twisted import inlineCallbacks

from keysign.bluetoothoffer import BluetoothOffer
from keysign.gpgmeh import get_public_key_data, openpgpkey_from_data

thisdir = os.path.dirname(os.path.realpath(__file__))


def import_key_from_file(fixture, homedir):
    fname = os.path.join(thisdir, "fixtures", fixture)
    original = open(fname, 'rb').read()
    check_call(["gpg", "--homedir={}".format(homedir), "--import", fname])
    return openpgpkey_from_data(original)


class FakeListeningSocket:
    """Stands in for the RFCOMM socket the offer listens on.

    select() wants a real file descriptor, so we back this with one end
    of a socketpair which we make readable straight away.  accept() then
    hands out the connection that the test reads the key from.
    """

    def __init__(self, connection):
        self._readable, self._trigger = socket.socketpair()
        self._trigger.sendall(b"a connection is pending")
        self._connection = connection

    def fileno(self):
        return self._readable.fileno()

    def accept(self):
        return self._connection, ("00:11:22:33:44:55", 3)


@inlineCallbacks
def test_offer_sends_the_key_as_bytes():
    """The key has to go onto the socket as bytes.

    socket.sendall() takes bytes only; handing it a str raises a
    TypeError which start() swallows, so the receiver would never get
    the key and the sender would merely report a failure.
    """
    homedir = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = homedir
    key = import_key_from_file("seckey-no-pw-1.asc", homedir)
    keydata = get_public_key_data(key.fingerprint)

    offering, receiving = socket.socketpair()
    offer = BluetoothOffer(key)
    offer.server_socket = FakeListeningSocket(offering)

    success, message = yield offer.start()

    assert success, "Offering the key failed: %r" % (message,)

    received = b""
    while True:
        part = receiving.recv(1024)
        if not part:
            break
        received += part

    assert received == keydata
