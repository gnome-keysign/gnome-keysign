#!/usr/bin/env python
#    Copyright 2016 Tobias Mueller <muelli@cryptobitch.de>
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

import logging
import os, sys
from subprocess import CalledProcessError, check_call
import tempfile

from nose.tools import *

thisdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(thisdir, "..")
sys.path.insert(0, os.sep.join((parentdir, 'monkeysign')))

from keysign.gpgmh import openpgpkey_from_data
from keysign.gpgmh import fingerprint_from_keydata
from keysign.gpgmh import get_public_key_data
from keysign.gpgmh import get_usable_keys
from keysign.gpgmh import get_usable_secret_keys
from keysign.gpgmh import sign_keydata_and_encrypt

log = logging.getLogger(__name__)

def get_fixture_dir(fixture=""):
    dname = os.path.join(thisdir, "fixtures", fixture)
    return dname

def get_fixture_file(fixture):
    fname = os.path.join(get_fixture_dir(), fixture)
    return fname

def read_fixture_file(fixture):
    fname = get_fixture_file(fixture)
    data = open(fname, 'r').read()
    return data


@raises(ValueError)
def test_openpgpkey_from_no_data():
    r = openpgpkey_from_data(None)
    assert False

@raises(ValueError)
def test_openpgpkey_from_empty_data():
    r = openpgpkey_from_data("")
    assert False


@raises(ValueError)
def test_openpgpkey_from_wrong_data():
    r = openpgpkey_from_data("this is no key!!1")
    assert False


def test_fingerprint_from_data():
    data = read_fixture_file("pubkey-1.asc")
    fingerprint = fingerprint_from_keydata(data)
    assert_equals("ADAB7FCC1F4DE2616ECFA402AF82244F9CD9FD55",
                  fingerprint)


@raises(ValueError)
def test_fingerprint_from_data():
    fingerprint = fingerprint_from_keydata("This is not a key...")
    assert False


class TestKey1:
    def setup(self):
        data = read_fixture_file("pubkey-1.asc")
        self.key = openpgpkey_from_data(data)

    def test_fingerprint(self):
        assert_equals("ADAB7FCC1F4DE2616ECFA402AF82244F9CD9FD55",
                      self.key.fingerprint)

    def test_uids(self):
        uids = self.key.uidslist
        assert_equals(1, len(uids))
        uid = uids[0]
        assert_equals('Joe Random Hacker',
                      uid.name)
        assert_equals('joe@example.com',
                      uid.email)

@raises(ValueError)
def test_get_public_key_no_data():
    tmp = tempfile.mkdtemp()
    d = get_public_key_data(None, homedir=tmp)
    assert_equals("", d)

class TestGetPublicKeyData:
    def setup(self):
        self.fname = get_fixture_file("pubkey-1.asc")
        original = open(self.fname, 'r').read()
        # This should be a new, empty directory
        self.homedir = tempfile.mkdtemp()
        gpgcmd = ["gpg", "--homedir={}".format(self.homedir)]
        # The directory should not have any keys
        # I don't know how to easily check for that, though
        # Now we import a single key
        check_call(gpgcmd + ["--import", self.fname])
    
        self.originalkey = openpgpkey_from_data(original)

    def teardown(self):
        # shutil.rmtree(self.homedir)
        pass

    def test_get_all_public_key_data(self):
        # Hm. The behaviour of something that matches
        # more than one key may change.
        data = get_public_key_data("", homedir=self.homedir)
        newkey = openpgpkey_from_data(data)
        # Hrm. We may be better off checking for a few things
        # we actually care about rather than delegating to the Key() itself.
        assert_equals(self.originalkey, newkey)

    def test_get_public_key_data(self):
        fpr = self.originalkey.fingerprint
        data = get_public_key_data(fpr, homedir=self.homedir)
        newkey = openpgpkey_from_data(data)
        assert_equals(fpr, newkey.fingerprint)

    @raises(ValueError)
    def test_no_match(self):
        data = get_public_key_data("nothing should match this",
                                   homedir=self.homedir)
        newkey = openpgpkey_from_data(data)
        assert False



def test_get_empty_usable_keys():
    homedir = tempfile.mkdtemp()
    keys = get_usable_keys(homedir=homedir)
    assert_equals(0, len(keys))

class TestGetUsableKeys:
    def setup(self):
        self.fname = get_fixture_file("pubkey-1.asc")
        original = open(self.fname, 'r').read()
        # This should be a new, empty directory
        self.homedir = tempfile.mkdtemp()
        gpgcmd = ["gpg", "--homedir={}".format(self.homedir)]
        # The directory should not have any keys
        # I don't know how to easily check for that, though
        # Now we import a single key
        check_call(gpgcmd + ["--import", self.fname])
    
        self.originalkey = openpgpkey_from_data(original)

    def teardown(self):
        # shutil.rmtree(self.homedir)
        pass

    def test_get_usable_key_no_pattern(self):
        keys = get_usable_keys(homedir=self.homedir)
        assert_equals(1, len(keys))
        key = keys[0]
        assert_equals(self.originalkey, key)


    def test_get_usable_key_fpr(self):
        fpr = self.originalkey.fingerprint
        keys = get_usable_keys(fpr, homedir=self.homedir)
        assert_equals(1, len(keys))
        key = keys[0]
        assert_equals(fpr, self.originalkey.fingerprint)



class TestGetUsableSecretKeys:
    def setup(self):
        fname = get_fixture_file("seckey-1.asc")
        original = open(fname, 'r').read()
        # This should be a new, empty directory
        self.homedir = tempfile.mkdtemp()
        gpgcmd = ["gpg", "--homedir={}".format(self.homedir)]
        # The directory should not have any keys
        # I don't know how to easily check for that, though
        # Now we import a single key
        check_call(gpgcmd + ["--import", fname])
    
        self.originalkey = openpgpkey_from_data(original)

    def teardown(self):
        # shutil.rmtree(self.homedir)
        pass

    def test_get_usable_key_no_pattern(self):
        keys = get_usable_secret_keys(homedir=self.homedir)
        assert_equals(1, len(keys))
        key = keys[0]
        assert_equals(self.originalkey, key)


    def test_get_usable_key_fpr(self):
        fpr = self.originalkey.fingerprint
        keys = get_usable_secret_keys(fpr, homedir=self.homedir)
        assert_equals(1, len(keys))
        key = keys[0]
        assert_equals(fpr, self.originalkey.fingerprint)





class TestSignAndEncrypt:
    def setup(self):
        self.sender_key = get_fixture_file("seckey-1.asc")
        self.receiver_key = get_fixture_file("seckey-2.asc")
        # This should be a new, empty directory
        self.sender_homedir = tempfile.mkdtemp()
        self.receiver_homedir = tempfile.mkdtemp()
        sender_gpgcmd = ["gpg", "--homedir={}".format(self.sender_homedir)]
        receiver_gpgcmd = ["gpg", "--homedir={}".format(self.receiver_homedir)]
        check_call(sender_gpgcmd + ["--import", self.sender_key])
        check_call(receiver_gpgcmd + ["--import", self.receiver_key])

    def teardown(self):
        # shutil.rmtree(self.sender_homedir)
        # shutil.rmtree(self.receiver_homedir)
        pass

    def test_sign_and_encrypt(self):
        keydata = open(self.sender_key, "r").read()
        keys = get_usable_secret_keys(homedir=self.sender_homedir)
        assert_equals(1, len(keys))
        key = keys[0]
        uids = key.uidslist
        uid_encrypted = list(sign_keydata_and_encrypt(keydata,
            error_cb=None, homedir=self.receiver_homedir))
        assert_equals(len(uids), len(uid_encrypted))
        for uid in uids:
            # The test doesn't work so well, because comments
            # are not rendered :-/
            # assert_in(uid.uid, [e[0] for e in uid_encrypted])
            pass
        # Ideally, we could decrypt the message, parse the email,
        # extract the attached key, and check the signatures...
