#!/usr/bin/env python
"""We want our customs UID wrapper to return raw bytes for the raw UID
but decoded strings for email, name, and comment component.
"""
from __future__ import unicode_literals

from keysign import gpgkey

def is_string(s):
    return type(s) == type("string")

def is_bytes(s):
    return type(s) == type(b"bytes")

def assert_string(s):
    assert is_string(s), "Expected String, but got %s (%r)" % (type(s), s)

def assert_bytes(s):
    assert is_bytes(s), "Expected Bytes, but got %s (%r)" % (type(s), s)

class FakeMKSUID:
    uid = b''
    expire = 0

def test_mks_utf8_uid():
    "The normal case"
    uid = FakeMKSUID()
    uid.uid = b'foo bar <foo@bar.com>'
    u = gpgkey.UID.from_monkeysign(uid)
    assert_string(u.name)
    assert_string(u.comment)
    assert_string(u.email)
    assert_bytes(u.uid)

def test_mks_latin_uid():
    uid = FakeMKSUID()
    uid.uid = b"fo\xf6\x65\xe9\x62a"
    u = gpgkey.UID.from_monkeysign(uid)
    assert_string(u.name)
    assert_string(u.comment)
    assert_string(u.email)
    assert_bytes(u.uid)
