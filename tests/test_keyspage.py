"""Tests for the widget listing the keys a user can pick from."""

import os
import tempfile
from subprocess import check_call

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.KeysPage import KeysPage

thisdir = os.path.dirname(os.path.realpath(__file__))


def import_key_from_file(fixture, homedir):
    fname = os.path.join(thisdir, "fixtures", fixture)
    check_call(["gpg", "--homedir={}".format(homedir), "--import", fname])


def test_says_so_when_there_is_no_private_key():
    os.environ["GNUPGHOME"] = tempfile.mkdtemp()

    page = KeysPage()

    label = page.get_first_child()
    assert "private key" in label.get_text()


def test_lists_the_secret_keys():
    homedir = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = homedir
    import_key_from_file("seckey-no-pw-1.asc", homedir)

    page = KeysPage()

    uids = [(row[0], row[1]) for row in page.store]
    assert uids, "the key we imported is not listed"
    assert all(fingerprint for fingerprint in
               (row[2] for row in page.store))
