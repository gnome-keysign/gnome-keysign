"""Tests for the widget listing the keys a user can pick from."""

import os
import tempfile
from subprocess import check_call

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from keysign.KeysPage import KeysPage
from keysign.gpgmeh import openpgpkey_from_data

thisdir = os.path.dirname(os.path.realpath(__file__))


def import_key_from_file(fixture, homedir):
    fname = os.path.join(thisdir, "fixtures", fixture)
    with open(fname, 'rb') as f:
        original = f.read()
    check_call(["gpg", "--homedir={}".format(homedir), "--import", fname])
    return openpgpkey_from_data(original)


def a_page_with_one_key():
    """A KeysPage listing a single imported secret key"""
    homedir = tempfile.mkdtemp()
    os.environ["GNUPGHOME"] = homedir
    key = import_key_from_file("seckey-no-pw-1.asc", homedir)
    return KeysPage(), key


def listed(page):
    """The rows of the page's model, as tuples"""
    store = page.store
    return [(store.get_item(i).name,
             store.get_item(i).email,
             store.get_item(i).fingerprint)
            for i in range(store.get_n_items())]


def test_says_so_when_there_is_no_private_key():
    os.environ["GNUPGHOME"] = tempfile.mkdtemp()

    page = KeysPage()

    label = page.get_first_child()
    assert "private key" in label.get_text()


def test_lists_the_secret_keys():
    page, key = a_page_with_one_key()

    rows = listed(page)
    assert rows, "the key we imported is not listed"
    assert all(fingerprint == key.fingerprint
               for _, _, fingerprint in rows)


def test_shows_a_name_and_an_email_column():
    page, _ = a_page_with_one_key()

    titles = [column.get_title()
              for column in page.columnView.get_columns()]
    assert titles == ["Name", "Email"]


def test_selecting_a_row_announces_the_selection():
    page, key = a_page_with_one_key()
    seen = []
    page.connect('key-selection-changed', lambda page, fpr: seen.append(fpr))

    page.selection.set_selected(0)

    assert seen == [key.fingerprint]


def test_activating_a_row_selects_the_key():
    page, key = a_page_with_one_key()
    seen = []
    page.connect('key-selected', lambda page, fpr: seen.append(fpr))

    page.columnView.emit('activate', 0)

    assert seen == [key.fingerprint]
