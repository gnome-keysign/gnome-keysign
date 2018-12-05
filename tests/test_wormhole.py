#!/usr/bin/env python
#    Copyright 2017 Ludovico de Nittis <aasonykk+gnome@gmail.com>
#
#    This file is part of GNOME Keysign.
#
#    GNOME Keysign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    GNOME Keysign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with GNOME Keysign.  If not, see <http://www.gnu.org/licenses/>.

import os
import logging
import gi
gi.require_version('Gtk', '3.0')

from nose.twistedtools import deferred
from nose.tools import *
from wormhole.errors import WrongPasswordError
from twisted.internet.defer import inlineCallbacks

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
@inlineCallbacks
def test_wrmhl():
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    file_key_data = get_public_key_data(key.fingerprint)
    log.info("Running with key %r", key)
    # Start offering the key
    offer = WormholeOffer(key)
    info = yield offer.allocate_code()
    code, _ = info
    offer.start()
    receive = WormholeReceive(code)
    msg_tuple = yield receive.start()
    downloaded_key_data, success, _ = msg_tuple
    assert_true(success)
    log.info("Checking with key: %r", downloaded_key_data)
    assert_equal(downloaded_key_data, file_key_data)


@deferred(timeout=10)
@inlineCallbacks
def test_wrmhl_offline_code():
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    file_key_data = get_public_key_data(key.fingerprint)
    # We assume that this channel, at execution time, is free
    code = u"5556-penguin-paw-print"
    # Start offering the key
    offer = WormholeOffer(key)
    offer.allocate_code(code)
    offer.start()
    # Start receiving the key
    receive = WormholeReceive(code)
    msg_tuple = yield receive.start()
    downloaded_key_data, success, _ = msg_tuple
    assert_true(success)
    log.info("Checking with key: %r", downloaded_key_data)
    assert_equal(downloaded_key_data, file_key_data)


@deferred(timeout=10)
@inlineCallbacks
def test_wrmhl_wrong_code():
    data = read_fixture_file("seckey-no-pw-1.asc")
    key = openpgpkey_from_data(data)
    log.info("Running with key %r", key)
    # Start offering the key
    offer = WormholeOffer(key)
    info = yield offer.allocate_code()
    code, _ = info
    offer.start()
    receive = WormholeReceive(code+"-wrong")
    msg_tuple = yield receive.start()
    downloaded_key_data, success, message = msg_tuple
    assert_false(success)
    assert_is_not_none(message)
    assert_equal(message, WrongPasswordError)

