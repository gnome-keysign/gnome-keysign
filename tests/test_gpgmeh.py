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
import unittest

import gpg
import pytest

from keysign.gpgmeh import TempContext
from keysign.gpgmeh import DirectoryContext
from keysign.gpgmeh import UIDExport
from keysign.gpgmeh import export_uids
from keysign.gpgmeh import fingerprint_from_keydata
from keysign.gpgmeh import import_signature
from keysign.gpgmeh import openpgpkey_from_data
from keysign.gpgmeh import get_usable_keys
from keysign.gpgmeh import get_usable_secret_keys
from keysign.gpgmeh import get_public_key_data
from keysign.gpgmeh import sign_keydata_and_encrypt
from keysign.gpgmeh import ImportNewCertificationError
from keysign.gpgmeh import get_signatures_for_uids_on_key

from keysign.gpgkey import to_valid_utf8_string

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


def test_uid_export_0():
    "You should not be able to export uid < 1"
    data = read_fixture_file("pubkey-1.asc")
    pytest.raises(ValueError,
        UIDExport,
            data, 0)


def test_uid_export_single():
    # This key contains only one UID
    data = read_fixture_file("pubkey-1.asc")
    try:
        uid1_data = UIDExport(data, 1)
    except KeyboardInterrupt as e:
        log.exception("Meh.")
        raise RuntimeError()

    # The original key
    c = TempContext()
    c.op_import(data)
    result = c.op_import_result()
    logging.info("Result: %r", result)
    fpr = result.imports[0].fpr
    uids = c.get_key(fpr).uids
    assert 1 == len(uids)

    # The first exported UID
    c = TempContext()
    logging.info("uid1: %r", uid1_data)
    c.op_import(uid1_data)
    result = c.op_import_result()
    imports = result.imports
    assert 1 == len(imports)
    uids1_key = c.get_key(fpr).uids
    assert 1 == len(uids1_key)
    uid1 = uids1_key[0]
    # assert uid1 == uids[0]
    assert uid1.uid == uids[0].uid


def test_uid_export_double():
    # This key contains two UIDs
    data = read_fixture_file("pubkey-2-uids.asc")
    try:
        uid1_data = UIDExport(data, 1)
        logging.info("uid1: %r", uid1_data)
        uid2_data = UIDExport(data, 2)
    except KeyboardInterrupt as e:
        log.exception("Meh.")
        raise RuntimeError()

    assert uid1_data != uid2_data

    # The original key
    c = TempContext()
    c.op_import(data)
    result = c.op_import_result()
    logging.info("Result: %r", result)
    fpr = result.imports[0].fpr
    uids = c.get_key(fpr).uids
    assert 2 == len(uids)

    # The first exported UID
    c = TempContext()
    logging.info("uid1: %r", uid1_data)
    c.op_import(uid1_data)
    result = c.op_import_result()
    imports = result.imports
    assert 1 == len(imports)
    uids1_key = c.get_key(fpr).uids
    assert 1 == len(uids1_key)
    uid1 = uids1_key[0]
    # assert uid1 == uids[0]
    assert uid1.uid == uids[0].uid

    # The second exported UID
    c = TempContext()
    c.op_import(uid2_data)
    result = c.op_import_result()
    imports = result.imports
    assert 1 == len(imports)
    uids2_key = c.get_key(fpr).uids
    assert 1 == len(uids2_key)
    uid2 = uids2_key[0]
    # FIXME: The objects don't implement __eq__ it seems :-/
    # assert uid2 == uids[1]
    assert uid2.uid == uids[1].uid


def test_export_uids():
    # This key contains two UIDs
    # We ought to have tests with revoked and invalid UIDs
    data = read_fixture_file("pubkey-2-uids.asc")

    # The original key
    c = TempContext()
    c.op_import(data)
    result = c.op_import_result()
    logging.info("Result: %r", result)
    fpr = result.imports[0].fpr
    uids = c.get_key(fpr).uids
    assert 2 == len(uids)

    exported_uids = list(export_uids(data))
    assert 2 == len(exported_uids)

    exported_uid1 = exported_uids[0]
    uid1, uid1_data = exported_uid1
    exported_uid2 = exported_uids[1]
    uid2, uid2_data = exported_uid2
    assert uids[0].uid == uid1
    assert uids[1].uid == uid2

    # The first exported UID
    c = TempContext()
    c.op_import(uid1_data)
    result = c.op_import_result()
    imports = result.imports
    assert 1 == len(imports)
    uids1_key = c.get_key(fpr).uids
    assert 1 == len(uids1_key)
    uid1_key = uids1_key[0]
    # assert uid1 == uids[0]
    assert uid1_key.uid == uids[0].uid

    # The second exported UID
    c = TempContext()
    c.op_import(uid2_data)
    result = c.op_import_result()
    imports = result.imports
    assert 1 == len(imports)
    uids2_key = c.get_key(fpr).uids
    assert 1 == len(uids2_key)
    uid2_key = uids2_key[0]
    # FIXME: The objects don't implement __eq__ it seems :-/
    # assert uid2 == uids[1]
    assert uid2_key.uid == uids[1].uid


def test_export_alpha_uids():
    """When UIDs get deleted, their index shrinks, of course
    We didn't, however, take that into account so a key with
    three UIDs would break.
    """
    data = read_fixture_file("alpha.asc")

    # The original key
    c = TempContext()
    c.op_import(data)
    result = c.op_import_result()
    logging.info("Result: %r", result)
    fpr = result.imports[0].fpr
    uids = c.get_key(fpr).uids
    logging.info("UIDs: %r", uids)
    assert 3 == len(uids)
    
    for i, uid in enumerate(uids, start=1):
        exported_uid = UIDExport(data, i)
        tmp = TempContext()
        tmp.op_import(exported_uid)
        result = tmp.op_import_result()
        logging.debug("UID %d %r import result: %r", i, uid, result)
        uid_key = tmp.get_key(result.imports[0].fpr)
        assert 1 == len(uid_key.uids)
        key_uid = uid_key.uids[0]
        # FIXME: Enable __eq__
        # assert uids[i-1] == key_uid
        assert uids[i-1].name == key_uid.name
        assert uids[i-1].email == key_uid.email


def test_fingerprint_from_data():
    pytest.raises(ValueError,
        fingerprint_from_keydata,
            "This is not a key...")


class TestKey1:
    def setup(self):
        data = read_fixture_file("pubkey-1.asc")
        self.key = openpgpkey_from_data(data)

    def test_fingerprint(self):
        assert "ADAB7FCC1F4DE2616ECFA402AF82244F9CD9FD55" == self.key.fingerprint

    def test_uids(self):
        uids = self.key.uidslist
        assert 1 == len(uids)
        uid = uids[0]
        assert 'Joe Random Hacker' == uid.name
        assert 'joe@example.com' == uid.email


def test_get_public_key_no_data():
    tmp = tempfile.mkdtemp()
    pytest.raises(ValueError,
        get_public_key_data,
            None, homedir=tmp)


class TestGetPublicKeyData:
    def setup(self):
        self.fname = get_fixture_file("pubkey-1.asc")
        original = open(self.fname, 'rb').read()
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
        assert self.originalkey == newkey

    def test_get_public_key_data(self):
        fpr = self.originalkey.fingerprint
        data = get_public_key_data(fpr, homedir=self.homedir)
        newkey = openpgpkey_from_data(data)
        assert fpr == newkey.fingerprint

    def test_no_match(self):
        pytest.raises(ValueError,
            get_public_key_data,
               "nothing should match this",
                homedir=self.homedir)


def test_get_empty_usable_keys():
    homedir = tempfile.mkdtemp()
    keys = get_usable_keys(homedir=homedir)
    assert 0 == len(keys)


class TestGetUsableKeys:
    def setup(self):
        self.fname = get_fixture_file("pubkey-1.asc")
        original = open(self.fname, 'rb').read()
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
        assert 1 == len(keys)
        key = keys[0]
        assert self.originalkey == key

    def test_get_usable_key_fpr(self):
        fpr = self.originalkey.fingerprint
        keys = get_usable_keys(fpr, homedir=self.homedir)
        assert 1 == len(keys)
        key = keys[0]
        assert self.originalkey == key


class TestGetUsableSecretKeys:
    def setup(self):
        self.fname = get_fixture_file("seckey-no-pw-1.asc")
        original = open(self.fname, 'rb').read()
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
        keys = get_usable_secret_keys(homedir=self.homedir)
        assert 1 == len(keys)
        key = keys[0]
        assert self.originalkey == key

    def test_get_usable_key_fpr(self):
        fpr = self.originalkey.fingerprint
        keys = get_usable_secret_keys(fpr, homedir=self.homedir)
        assert 1 == len(keys)
        key = keys[0]
        assert self.originalkey == key


def export_public_key(keydata):
    "Returns the public portion of the key even if you provide a private key"
    # This might be a secret key, too, so we import and export to
    # get hold of the public portion.
    ctx = TempContext()
    ctx.op_import(keydata)
    result = ctx.op_import_result()
    fpr = result.imports[0].fpr
    sink = gpg.Data()
    ctx.op_export(fpr, 0, sink)
    sink.seek(0, 0)
    public_key = sink.read()
    assert len(public_key) > 0
    return public_key

class TestSignAndEncrypt:
    SENDER_KEY = "seckey-no-pw-1.asc"
    RECEIVER_KEY = "seckey-no-pw-2.asc"

    def setup(self):
        # The "sender" sends its certificate to have it certified by the receiver
        self.key_sender_key = get_fixture_file(self.SENDER_KEY)
        # The "receiver" will receive the certificate, certify it, and send it back to the "sender"
        self.key_receiver_key = get_fixture_file(self.RECEIVER_KEY)
        # This should be a new, empty directory
        self.key_sender_homedir = tempfile.mkdtemp()
        self.key_receiver_homedir = tempfile.mkdtemp()
        sender_gpgcmd = ["gpg", "--homedir={}".format(self.key_sender_homedir)]
        receiver_gpgcmd = ["gpg", "--homedir={}".format(self.key_receiver_homedir)]
        check_call(sender_gpgcmd + ["--import", self.key_sender_key])
        check_call(receiver_gpgcmd + ["--import", self.key_receiver_key])

    def teardown(self):
        # shutil.rmtree(self.sender_homedir)
        # shutil.rmtree(self.receiver_homedir)
        pass

    def test_sign_and_encrypt(self):
        # This might be a secret key, too, so we import and export to
        # get hold of the public portion.
        keydata = open(self.key_sender_key, "rb").read()
        # We get the public portion of the key
        sender = TempContext()
        sender.op_import(keydata)
        result = sender.op_import_result()
        fpr = result.imports[0].fpr
        sink = gpg.Data()
        sender.op_export(fpr, 0, sink)
        sink.seek(0, 0)
        # This is the key that we will sign
        public_sender_key = sink.read()

        keys = get_usable_keys(homedir=self.key_sender_homedir)
        assert 1 == len(keys)
        key = keys[0]
        uids = key.uidslist
        # Now finally call the function under test
        uid_encrypted = list(sign_keydata_and_encrypt(public_sender_key,
                             error_cb=None, homedir=self.key_receiver_homedir))
        assert len(uids) == len(uid_encrypted)

        # We need to explicitly request signatures
        uids_before = uids
        assert len(uids_before) == len(sender.get_key(fpr).uids)

        sigs_before = [s for l in get_signatures_for_uids_on_key(key,
                                    homedir=sender.homedir).values() for s in l]
        # FIXME: Refactor this a little bit.
        # We have duplication of code with the other test below.
        for uid, uid_enc in zip(uids_before, uid_encrypted):
            uid_enc_str = uid_enc[0].uid
            # The test doesn't work so well, because comments
            # are not rendered :-/
            # assert uid == uid_enc[0]
            assert uid.name in uid_enc_str
            assert uid.email in uid_enc_str
            ciphertext = uid_enc[1]
            log.debug("Decrypting %r", ciphertext)
            plaintext, result, vrfy = sender.decrypt(ciphertext)
            log.debug("Decrypt Result: %r", result)
            sender.op_import(plaintext)
            import_result = sender.op_import_result()
            log.debug("Import Result: %r", import_result)
            assert 1 == import_result.new_signatures
            updated_key = sender.get_key(fpr)
            log.debug("updated key: %r", updated_key)
            log.debug("updated key sigs: %r", [(uid, uid.signatures) for uid in updated_key.uids])

        sigs_after = [s for l in get_signatures_for_uids_on_key(key,
                                    homedir=sender.homedir).values() for s in l]
        assert len(sigs_after) > len(sigs_before)

    def test_sign_and_encrypt_double_secret(self):
        "We want to produce as many signatures as possible"
        recv = DirectoryContext(homedir=self.key_receiver_homedir)
        params = """<GnupgKeyParms format="internal">
            %transient-key
            Key-Type: RSA
            Key-Length: 1024
            Name-Real: Joe Genkey Tester
            Name-Comment: with stupid passphrase
            Name-Email: joe+gpg@example.org
            %no-protection
            #Passphrase: Crypt0R0cks
            #Expire-Date: 2020-12-31
        </GnupgKeyParms>
        """
        recv.op_genkey(params, None, None)
        gen_result = recv.op_genkey_result()
        assert 2 == len(list(recv.keylist(secret=True)))
        
        sender = DirectoryContext(homedir=self.key_sender_homedir)
        sender.set_keylist_mode(gpg.constants.KEYLIST_MODE_SIGS)
        sender_keys = list(sender.keylist())
        assert 1 == len(sender_keys)
        sender_key = sender_keys[0]
        fpr = sender_key.fpr
        sink = gpg.Data()
        sender.op_export_keys(sender_keys, 0, sink)
        sink.seek(0, 0)
        public_sender_key = sink.read()
        # Now finally call the function under test
        uid_encrypted = list(sign_keydata_and_encrypt(public_sender_key,
                             error_cb=None, homedir=self.key_receiver_homedir))
        assert len(sender_key.uids) == len(uid_encrypted)

        uids_before = sender.get_key(fpr).uids
        sigs_before = [s for l in get_signatures_for_uids_on_key(sender_key,
                                    sender.homedir).values() for s in l]
        for uid, uid_enc in zip(uids_before, uid_encrypted):
            uid_enc_str = uid_enc[0].uid
            log.info("Uid enc str: %r", uid_enc_str)
            log.info("Uid name: %r", uid.name)
            # FIXME: assert uid == uid_enc[0]
            # It's a bit weird to re-use the string treatment here.
            # But gpgme may return unencodable bytes (and uid, here, is
            # coming straight from gpgme).  We opted for our UID wrapper
            # to return consumable strings, i.e. safe to encode
            assert to_valid_utf8_string(uid.name) in uid_enc_str
            assert to_valid_utf8_string(uid.email) in uid_enc_str
            ciphertext = uid_enc[1]
            log.debug("Decrypting %r", ciphertext)
            plaintext, result, vrfy = sender.decrypt(ciphertext)
            log.debug("Decrypt Result: %r", result)
            sender.op_import(plaintext)
            import_result = sender.op_import_result()
            log.debug("Import Result: %r", import_result)
            # Here is the important check for two new signatures
            assert 2 == import_result.new_signatures
            updated_key = sender.get_key(fpr)
            log.debug("updated key: %r", updated_key)
            log.debug("updated key sigs: %r", [(uid, uid.signatures) for uid in updated_key.uids])

        sigs_after = [s for l in get_signatures_for_uids_on_key(sender_key,
                                    sender.homedir).values() for s in l]

        assert len(sigs_after) > len(sigs_before)




    def test_third_party_key(self):
        """This test tries to trick the receiver by sending
        an unrelated key of a third party.
        The receiver must not import that key.
        """
        THIRD_PARTY_KEY = "third_party.pgp.asc"
        self.third_party_key = get_fixture_file(THIRD_PARTY_KEY)
        self.key_third_party_homedir = tempfile.mkdtemp()
        third_party_gpgcmd = ["gpg", "--homedir={}".format(self.key_third_party_homedir)]
        check_call(third_party_gpgcmd + ["--import", self.third_party_key])

        keydata = open(self.third_party_key, "rb").read()
        public_third_party_key = export_public_key(keydata)
        # The "sender" sends its certificate via the app and then receives the email with the certification
        public_sender_key = export_public_key(open(self.key_sender_key, 'rb'))


        sender = DirectoryContext(homedir=self.key_sender_homedir)
        before = list(sender.keylist())
        third_party = DirectoryContext(homedir=self.key_third_party_homedir)

        third_party.op_import(public_sender_key)
        result = third_party.op_import_result()
        if result.considered != 1 and result.imported != 1:
            raise ValueError("Expected to load exactly one key. %r", result)
        else:
            imports = result.imports
            assert len(imports) == 1, "Imported %d instead of 1" % len(imports)
            fpr = result.imports[0].fpr
            target_key = third_party.get_key(fpr)
            ciphertext, _, _ = third_party.encrypt(
                plaintext=public_third_party_key,
                recipients=[target_key],
                always_trust=True,
                sign=False,
            )

            # Now we have transferred the ciphertext to the victim
            plaintext, result, vrfy = sender.decrypt(ciphertext)
            log.debug("Decrypt Result: %r", result)
            result = pytest.raises(ImportNewCertificationError,
                import_signature,
                    plaintext,
                    homedir=self.key_sender_homedir)
            log.debug("Import result: %s", result)

            after = list(sender.keylist())

            assert len(before) == len(after)

class TestLatin1(TestSignAndEncrypt):
    SENDER_KEY = "seckey-latin1.asc"
    RECEIVER_KEY = "seckey-2.asc"


class TestColon(TestSignAndEncrypt):
    SENDER_KEY = "seckey-colon.asc"
    RECEIVER_KEY = "seckey-2.asc"


class TestMultipleUID(TestSignAndEncrypt):
    SENDER_KEY = "seckey-multiple-uid-colon.asc"
    RECEIVER_KEY = "seckey-2.asc"


class TestUtf8(TestSignAndEncrypt):
    SENDER_KEY = "seckey-utf8.asc"
    RECEIVER_KEY = "seckey-utf8-2.asc"


# There is little we can do here.
# That OpenPGP key is incomplete, i.e. it lacks the "d" needed to
# do anything meaningful with the key.
#class TestSubKeys(TestSignAndEncrypt):
#    SENDER_KEY = "seckey-2.asc"
#    RECEIVER_KEY = "seckey-subkeys.asc"
