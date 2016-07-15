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
import os
from tempfile import NamedTemporaryFile


from monkeysign.gpg import Keyring
from monkeysign.gpg import GpgRuntimeError


# FIXME: This probably wants to go somewhere more central.
# Maybe even into Monkeysign.
log = logging.getLogger(__name__)


def UIDExport(uid, keydata):
    """Export only the UID of a key.
    Unfortunately, GnuPG does not provide smth like
    --export-uid-only in order to obtain a UID and its
    signatures."""
    tmp = TempKeyring()
    # Hm, apparently this needs to be set, otherwise gnupg will issue
    # a stray "gpg: checking the trustdb" which confuses the gnupg library
    tmp.context.set_option('always-trust')
    tmp.import_data(keydata)
    for fpr, key in tmp.get_keys(uid).items():
        for u in key.uidslist:
            key_uid = u.uid
            if key_uid != uid:
                log.info('Deleting UID %s from key %s', key_uid, fpr)
                tmp.del_uid(fingerprint=fpr, pattern=key_uid)
    only_uid = tmp.export_data(uid)

    return only_uid


def MinimalExport(keydata):
    '''Returns the minimised version of a key

    For now, you must provide one key only.'''
    tmpkeyring = TempKeyring()
    ret = tmpkeyring.import_data(keydata)
    log.debug("Returned %s after importing %r", ret, keydata)
    assert ret
    tmpkeyring.context.set_option('export-options', 'export-minimal')
    keys_dict = tmpkeyring.get_keys()
    # We assume the keydata to contain one key only
    keys = list(keys_dict.items())
    log.debug("Keys after importing: %s (%s)", keys, keys)
    fingerprint, key = keys[0]
    stripped_key = tmpkeyring.export_data(fingerprint)
    return stripped_key



class SplitKeyring(Keyring):
    def __init__(self, primary_keyring_fname, trustdb_fname, *args, **kwargs):
        # I don't think Keyring is inheriting from object,
        # so we can't use super()
        Keyring.__init__(self)   #  *args, **kwargs)

        self.context.set_option('primary-keyring', primary_keyring_fname)
        self.context.set_option('trustdb-name', trustdb_fname)
        self.context.set_option('no-default-keyring')


class TempKeyring(SplitKeyring):
    """A temporary keyring which will be discarded after use
    
    It creates a temporary file which will be used for a SplitKeyring.
    You may not necessarily be able to use this Keyring as is, because
    gpg1.4 does not like using secret keys which is does not have the
    public keys of in its pubkeyring.
    
    So you may not necessarily be able to perform operations with
    the user's secret keys (like creating signatures).
    """
    def __init__(self, *args, **kwargs):
        # A NamedTemporaryFile deletes the backing file
        self.kr_tempfile = NamedTemporaryFile(prefix='gpgpy-')
        self.kr_fname = self.kr_tempfile.name
        self.tdb_tempfile = NamedTemporaryFile(prefix='gpgpy-tdb-',
                                               delete=True)
        self.tdb_fname = self.tdb_tempfile.name
        # This should delete the file.
        # Why are we doing it?  Well...
        # Turns out that if you run gpg --trustdb-name with an
        # empty file, it complains about an invalid trustdb.
        # If, however, you give it a non-existent filename,
        # it'll happily create a new trustdb.
        # FWIW: Am empty trustdb file seems to be 40 bytes long,
        # but the contents seems to be non-deterministic.
        # Anyway, we'll leak the file :-/
        self.tdb_tempfile.close()

        SplitKeyring.__init__(self, primary_keyring_fname=self.kr_fname,
                                    trustdb_fname=self.tdb_fname,
                                    *args, **kwargs)



class TempSigningKeyring(TempKeyring):
    """A temporary keyring which uses the secret keys of a parent keyring
    
    Creates a temporary keyring which can use the orignal keyring's
    secret keys.  If you don't provide a keyring as argument (i.e. None),
    a default Keyring() will be taken which represents the user's
    regular keyring.

    In fact, this is not much different from a TempKeyring,
    but gpg1.4 does not see the public keys for the secret keys when run with
    --no-default-keyring and --primary-keyring.
    So we copy the public parts of the secret keys into the primary keyring.
    """
    def __init__(self, base_keyring=None, *args, **kwargs):
        # Not a new style class...
        if issubclass(self.__class__, object):
            super(TempSplitKeyring, self).__init__(*args, **kwargs)
        else:
            TempKeyring.__init__(self, *args, **kwargs)

        if base_keyring is None:
            base_keyring = Keyring()
        # Copy the public parts of the secret keys to the tmpkeyring
        for fpr, key in base_keyring.get_keys(None,
                                              secret=True,
                                              public=False).items():
            self.import_data (base_keyring.export_data (fpr))



def openpgpkey_from_data(keydata):
    "Creates an OpenPGP object from given data"
    keyring = TempKeyring()
    if not keyring.import_data(keydata):
        raise ValueError("Could not import %r  -  stdout: %r, stderr: %r",
                         keydata,
                         keyring.context.stdout, keyring.context.stderr)
    # As we have imported only one key, we should also
    # only have one key at our hands now.
    keys = keyring.get_keys()
    if len(keys) > 1:
        log.debug('Operation on keydata "%s" failed', keydata)
        raise ValueError("Cannot give the fingerprint for more than "
            "one key: %s", keys)
    else:
        # The first (key, value) pair in the keys dict
        # next(iter(keys.items()))[0] might be semantically
        # more correct than list(d.items()) as we don't care
        # much about having a list created, but I think it's
        # more legible.
        fpr_key = list(keys.items())[0]
        # is composed of the fpr as key and an OpenPGP key as value
        key = fpr_key[1]
        return key


# FIXME: We should rename that to "from_data"
#        otherwise someone might think we operate on
#        a key rather than bytes.
def fingerprint_for_key(keydata):
    '''Returns the OpenPGP Fingerprint for a given key'''
    openpgpkey = openpgpkey_from_data(keydata)
    return openpgpkey.fpr


def get_usable_keys(keyring=None, *args, **kwargs):
    '''Uses get_keys on the keyring and filters for
    non revoked, expired, disabled, or invalid keys'''
    log.debug('Retrieving keys for %s, %s', args, kwargs)
    if keyring is None:
        keyring = Keyring()
    keys_dict = keyring.get_keys(*args, **kwargs)
    assert keys_dict is not None, keyring.context.stderr
    def is_usable(key):
        unusable =    key.invalid or key.disabled \
                   or key.expired or key.revoked
        log.debug('Key %s is invalid: %s (i:%s, d:%s, e:%s, r:%s)', key, unusable,
            key.invalid, key.disabled, key.expired, key.revoked)
        return not unusable
    keys_fpr = keys_dict.items()
    keys = keys_dict.values()
    usable_keys = [key for key in keys if is_usable(key)]

    log.debug('Identified usable keys: %s', usable_keys)
    return usable_keys



def get_usable_secret_keys(keyring=None, pattern=None):
    '''Returns all secret keys which can be used to sign a key
    
    Uses get_keys on the keyring and filters for
    non revoked, expired, disabled, or invalid keys'''
    if keyring is None:
        keyring = Keyring()
    secret_keys_dict = keyring.get_keys(pattern=pattern,
                                        public=False,
                                        secret=True)
    secret_key_fprs = secret_keys_dict.keys()
    log.debug('Detected secret keys: %s', secret_key_fprs)
    usable_keys_fprs = filter(lambda fpr: get_usable_keys(keyring, pattern=fpr, public=True), secret_key_fprs)
    usable_keys = [secret_keys_dict[fpr] for fpr in usable_keys_fprs]

    log.info('Returning usable private keys: %s', usable_keys)
    return usable_keys


def sign_keydata_and_encrypt(keydata):
    "Signs OpenPGP keydata with your regular GnuPG secret keys"

    log = logging.getLogger(__name__ + ':sign_keydata_encrypt')

    tmpkeyring = TempSigningKeyring()
    tmpkeyring.context.set_option('export-options', 'export-minimal')
    # Eventually, we want to let the user select their keys to sign with
    # For now, we just take whatever is there.
    secret_keys = get_usable_secret_keys(tmpkeyring)
    log.info('Signing with these keys: %s', secret_keys)

    stripped_key = MinimalExport(keydata)
    fingerprint = fingerprint_for_key(stripped_key)

    log.debug('Trying to import key\n%s', stripped_key)
    if tmpkeyring.import_data(stripped_key):
        # 3. for every user id (or all, if -a is specified)
        # 3.1. sign the uid, using gpg-agent
        keys = tmpkeyring.get_keys(fingerprint)
        log.info("Found keys %s for fp %s", keys, fingerprint)
        assert len(keys) == 1, "We received multiple keys for fp %s: %s" % (fingerprint, keys)
        key = keys[fingerprint]
        uidlist = key.uidslist
        
        for secret_key in secret_keys:
            secret_fpr = secret_key.fpr
            log.info('Setting up to sign with %s', secret_fpr)
            # We need to --always-trust, because GnuPG would print
            # warning about the trustdb.  I think this is because
            # we have a newly signed key whose trust GnuPG wants to
            # incorporate into the trust decision.
            tmpkeyring.context.set_option('always-trust')
            tmpkeyring.context.set_option('local-user', secret_fpr)
            # FIXME: For now, we sign all UIDs. This is bad.
            ret = tmpkeyring.sign_key(uidlist[0].uid, signall=True)
            log.info("Result of signing %s on key %s: %s", uidlist[0].uid, fingerprint, ret)


        for uid in uidlist:
            uid_str = uid.uid
            log.info("Processing uid %s %s", uid, uid_str)

            # 3.2. export and encrypt the signature
            # 3.3. mail the key to the user
            signed_key = UIDExport(uid_str, tmpkeyring.export_data(uid_str))
            log.info("Exported %d bytes of signed key", len(signed_key))

            # self.signui.tmpkeyring.context.set_option('armor')
            tmpkeyring.context.set_option('always-trust')
            encrypted_key = tmpkeyring.encrypt_data(data=signed_key, recipient=uid_str)
            yield (uid.uid, encrypted_key)




## Monkeypatching to get more debug output
import monkeysign.gpg
bc = monkeysign.gpg.Context.build_command
def build_command(*args, **kwargs):
    ret = bc(*args, **kwargs)
    #log.info("Building command %s", ret)
    log.debug("Building cmd: %s", ' '.join(["'%s'" % c for c in ret]))
    return ret
monkeysign.gpg.Context.build_command = build_command




