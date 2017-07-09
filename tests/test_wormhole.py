import os
import logging
import gi
gi.require_version('Gtk', '3.0')

from nose.twistedtools import deferred
from nose.tools import *
from wormhole.errors import WrongPasswordError

from keysign.gpgmh import openpgpkey_from_data
from keysign.wormholeoffer import WormholeOffer
from keysign.wormholereceive import WormholeReceive
from keysign.gpgmh import get_public_key_data


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


@deferred(timeout=10)
def test_wrmhl():
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    file_key_data = get_public_key_data(key.fingerprint)
    log.info("Running with key %r", key)

    def check_key(downloaded_key_data):
        log.info("Checking with key: %r", key)
        assert_equal(downloaded_key_data, file_key_data)

    def prepare_receive(code, data):
        # Start wormhole receive with the code generated by offer
        WormholeReceive(code, check_key).start()

    # Start offering the key
    offer = WormholeOffer(key, callback_code=prepare_receive)
    offer.start()
    return offer.get_last_deferred()


@deferred(timeout=10)
def test_wrmhl_offline_code():
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    # We assume that this channel, at execution time, is free
    code = "5556-penguin-paw-print"

    def callback_receive(downloaded_key_data):
        file_key_data = get_public_key_data(key.fingerprint)
        assert_equals(file_key_data, downloaded_key_data)

    # Start offering the key
    offer = WormholeOffer(key, code=code)
    offer.start()
    # Start receiving the key
    WormholeReceive(code, callback_receive).start()
    return offer.get_last_deferred()


@deferred(timeout=10)
def test_wrmhl_wrong_code():
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    log.info("Running with key %r", key)

    def on_sent_callback(success, message=None):
        log.info("Sending success: %s", success)
        assert_false(success)
        assert_is_not_none(message)
        assert_equal(message.type, WrongPasswordError)

    def prepare_receive(code, data):
        # Start wormhole receive with a wrong code
        WormholeReceive(code+"-wrong").start()

    def errback_placeholder(msg):
        log.info(msg)

    # Start offering the key
    offer = WormholeOffer(key, on_sent_callback, prepare_receive)
    offer.start()
    return offer.get_last_deferred()
