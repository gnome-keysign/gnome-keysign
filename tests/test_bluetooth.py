import os
import logging
import select
import socket
from subprocess import check_call
import tempfile
import unittest
import gi
gi.require_version('Gtk', '3.0')

from twisted.internet import threads
from pytest_twisted import inlineCallbacks

try:
    from keysign.bluetoothoffer import BluetoothOffer
    from keysign.bluetoothreceive import BluetoothReceive, BluetoothError
    HAVE_BT = True
except ImportError:
    HAVE_BT = False
from keysign.gpgmeh import get_public_key_data, openpgpkey_from_data
from keysign.util import mac_generate


log = logging.getLogger(__name__)
thisdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(thisdir, "..")


@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def get_fixture_dir(fixture=""):
    dname = os.path.join(thisdir, "fixtures", fixture)
    return dname


@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def get_fixture_file(fixture):
    fname = os.path.join(get_fixture_dir(), fixture)
    return fname


@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def import_key_from_file(fixture, homedir):
    fname = get_fixture_file(fixture)
    original = open(fname, 'rb').read()
    gpgcmd = ["gpg", "--homedir={}".format(homedir)]
    # Now we import a single key
    check_call(gpgcmd + ["--import", fname])

    return openpgpkey_from_data(original)


@inlineCallbacks
@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def test_bt():
    """This test requires two working Bluetooth devices"""
    # This should be a new, empty directory
    homedir = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = homedir
    key = import_key_from_file("seckey-no-pw-1.asc", homedir)
    file_key_data = get_public_key_data(key.fingerprint)
    log.info("Running with key %r", key)
    hmac = mac_generate(key.fingerprint.encode('ascii'), file_key_data)
    # Start offering the key
    offer = BluetoothOffer(key)
    data = yield offer.allocate_code()
    if data is None:
        log.warning("No code allocated (%r), probably no Bluetooth adapter!", data)
    # getting the code from "BT=code;...."
    code = data.split("=", 1)[1]
    code = code.split(";", 1)[0]
    port = int(data.rsplit("=", 1)[1])
    offer.start()
    receive = BluetoothReceive(port)
    msg_tuple = yield receive.find_key(code, hmac)
    log.debug("Receiving yielded: %r", msg_tuple)
    downloaded_key_data, success, _ = msg_tuple
    assert success, "No success :( %r" % msg_tuple
    log.info("Checking with key: %r", downloaded_key_data)
    assert downloaded_key_data.encode("utf-8") == file_key_data


@inlineCallbacks
@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def test_bt_wrong_hmac():
    """This test requires two working Bluetooth devices"""
    # This should be a new, empty directory
    homedir = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = homedir
    key = import_key_from_file("seckey-no-pw-1.asc", homedir)
    log.info("Running with key %r", key)
    hmac = "wrong_hmac_eg_tampered_key"
    # Start offering the key
    offer = BluetoothOffer(key)
    data = yield offer.allocate_code()
    # getting the code from "BT=code;...."
    code = data.split("=", 1)[1]
    code = code.split(";", 1)[0]
    port = int(data.rsplit("=", 1)[1])
    offer.start()
    receive = BluetoothReceive(port)
    msg_tuple = yield receive.find_key(code, hmac)
    downloaded_key_data, success, err = msg_tuple
    assert not success
    assert not isinstance(err, BluetoothError), "We expect a ValidationError or something else, anyway, than a Bluetooth error, because the transfer ought to have worked. How else do we distinguish a broken Bluetooth (won't work at all) from a tampered connection (may work next time)"


@inlineCallbacks
@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def test_bt_wrong_mac():
    """This test requires one working Bluetooth device"""
    receive = BluetoothReceive()
    msg_tuple = yield receive.find_key("01:23:45:67:89:AB", "hmac")
    downloaded_key_data, success, error = msg_tuple
    assert downloaded_key_data is None
    assert not success
    assert error.args[0] == "(112, 'Host is down')"


@inlineCallbacks
@unittest.skipUnless(HAVE_BT, "requires bluetooth module")
def test_bt_corrupted_key():
    """This test requires two working Bluetooth devices"""

    @inlineCallbacks
    def start(bo):
        success = False
        try:
            while not success:
                # server_socket.accept() is not stoppable. So with select we can call accept()
                # only when we are sure that there is already a waiting connection
                ready_to_read, ready_to_write, in_error = yield threads.deferToThread(
                    select.select, [bo.server_socket], [], [], 0.5)
                if ready_to_read:
                    # We are sure that a connection is available, so we can call
                    # accept() without deferring it to a thread
                    client_socket, address = bo.server_socket.accept()
                    key_data = get_public_key_data(bo.key.fingerprint)
                    kd_decoded = key_data.decode('utf-8')
                    # We send only a part of the key. In this way we can simulate the case
                    # where the connection has been lost
                    half = len(kd_decoded)/2
                    kd_corrupted = kd_decoded[:half]
                    yield threads.deferToThread(client_socket.sendall, kd_corrupted)
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
                    success = True
        except Exception as e:
            log.error("An error occurred: %s" % e)

    # This should be a new, empty directory
    homedir = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = homedir
    key = import_key_from_file("seckey-no-pw-1.asc", homedir)
    log.info("Running with key %r", key)
    file_key_data = get_public_key_data(key.fingerprint)
    hmac = mac_generate(key.fingerprint.encode('ascii'), file_key_data)
    # Start offering the key
    offer = BluetoothOffer(key)
    data = yield offer.allocate_code()
    # getting the code from "BT=code;...."
    code = data.split("=", 1)[1]
    code = code.split(";", 1)[0]
    port = int(data.rsplit("=", 1)[1])
    start(offer)
    receive = BluetoothReceive(port)
    msg_tuple = yield receive.find_key(code, hmac)
    downloaded_key_data, result, error = msg_tuple
    assert not result
    assert isinstance(error, ValueError)
