#!/usr/bin/env python

import logging
import sys, os

import gi
gi.require_version('Gtk', "3.0")
from gi.repository import Gtk, GLib


from keysign import gpgmeh
from keysign.KeyPresent import KeyPresentWidget
from keysign.keyconfirm import PreSignWidget
from keysign.keylistwidget import KeyListWidget


## We should unify this fixture related code somehow
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


def load_key(key):
    f = read_fixture_file(key)
    k = gpgmeh.openpgpkey_from_data(f)
    return k


def load_latin1_key():
    key = "seckey-latin1.asc"
    return load_key(key)


def _gui_test(widget):
    widget.show_all()
    GLib.timeout_add_seconds(2,  Gtk.main_quit)
    Gtk.main()


def test_kpw():
    """We had problems with non-UTF-8 UIDs and KPW. We try to load one"""
    key = load_latin1_key()
    log.info("Loaded %r", key)
    kpw = KeyPresentWidget(key=key, discovery_code="")
    _gui_test(kpw)


def test_psw():
    """We had problems with non UTF-8 UIDs and PSW. We try to load one"""
    key = load_latin1_key()
    psw = PreSignWidget(key=key)
    _gui_test(psw)


def test_klw():
    """We had problems with non UTF-8 UIDs and KLW. We try to load one"""
    key = load_latin1_key()
    klw = KeyListWidget(keys=[key])
    _gui_test(klw)
