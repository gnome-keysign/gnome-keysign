import os
import logging
import gi
gi.require_version('Gtk', '3.0')

from nose.twistedtools import deferred
from nose.tools import *
from twisted.internet.defer import inlineCallbacks

from keysign.bluetoothoffer import BluetoothOffer
from keysign.bluetoothreceive import BluetoothReceive
from keysign.gpgmh import get_public_key_data, openpgpkey_from_data
from keysign.util import mac_generate


log = logging.getLogger(__name__)
thisdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(thisdir, "..")


def get_fixture_dir(fixture=""):
    dname = os.path.join(thisdir, "fixtures", fixture)
    return dname


def get_fixture_file(fixture):
    fname = os.path.join(get_fixture_dir(), fixture)
    return fname


def read_fixture_file(fixture):
    fname = get_fixture_file(fixture)
    data = open(fname, 'rb').read()
    return data


@deferred(timeout=15)
@inlineCallbacks
def test_bt():
    """This test requires two working Bluetooth devices"""
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    file_key_data = get_public_key_data(key.fingerprint)
    log.info("Running with key %r", key)
    hmac = mac_generate(key.fingerprint.encode('ascii'), file_key_data)
    # Start offering the key
    offer = BluetoothOffer(key)
    info = yield offer.generate_code()
    code, _ = info
    offer.start()
    receive = BluetoothReceive()
    msg_tuple = yield receive.find_key(code, hmac)
    downloaded_key_data, success, _ = msg_tuple
    assert_true(success)
    log.info("Checking with key: %r", downloaded_key_data)
    assert_equal(downloaded_key_data.encode("utf-8"), file_key_data)


@deferred(timeout=15)
@inlineCallbacks
def test_bt_wrong_mac():
    """This test requires one working Bluetooth device"""
    receive = BluetoothReceive()
    msg_tuple = yield receive.find_key("01:23:45:67:89:AB", "hmac")
    downloaded_key_data, success, error = msg_tuple
    assert_is_none(downloaded_key_data)
    assert_false(success)
    assert_equal(error.args[0], "(112, 'Host is down')")
