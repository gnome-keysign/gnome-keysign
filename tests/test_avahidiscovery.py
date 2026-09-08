"""Tests for discovering a key via Avahi.

A peer announces the fingerprint of the key it offers in its Avahi TXT
record, but that record is not authenticated in any way.  So whatever we
download has to be checked against the fingerprint we are looking for.
"""

import os
from unittest.mock import patch

from keysign.avahidiscovery import AvahiKeysignDiscovery
from keysign.gpgmeh import openpgpkey_from_data

thisdir = os.path.dirname(os.path.realpath(__file__))


def read_fixture(fixture):
    with open(os.path.join(thisdir, "fixtures", fixture), "rb") as f:
        return f.read()


def make_discovery(services):
    """An AvahiKeysignDiscovery which has "found" the given services."""
    with patch('keysign.avahidiscovery.AvahiBrowser'):
        discovery = AvahiKeysignDiscovery()
    discovery.discovered_services = services
    return discovery


def test_finds_the_advertised_key():
    keydata = read_fixture("pubkey-1.asc")
    fingerprint = openpgpkey_from_data(keydata).fingerprint

    discovery = make_discovery([("Some Peer", "192.0.2.1", 9001, fingerprint)])

    with patch('keysign.avahidiscovery.download_key_http',
               return_value=keydata):
        found = discovery.find_key("OPENPGP4FPR:%s" % fingerprint)

    assert found == keydata


def test_rejects_a_key_that_does_not_match_the_fingerprint():
    """A peer may announce one fingerprint and then serve another key.

    We must not hand that key to the caller: without a MAC (i.e. when
    the user typed the fingerprint rather than scanning a barcode) the
    fingerprint is the only thing authenticating the download, and the
    key ends up being presented for signing.
    """
    wanted = read_fixture("pubkey-1.asc")
    served = read_fixture("pubkey-2-uids.asc")
    fingerprint = openpgpkey_from_data(wanted).fingerprint

    discovery = make_discovery([("Lying Peer", "192.0.2.1", 9001, fingerprint)])

    with patch('keysign.avahidiscovery.download_key_http',
               return_value=served):
        found = discovery.find_key("OPENPGP4FPR:%s" % fingerprint)

    assert found is None
