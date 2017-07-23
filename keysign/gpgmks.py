#!/usr/bin/env python
#    Copyright 2017 Tobias Mueller <muelli@cryptobitch.de>
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

from datetime import datetime
import logging
import os  # The SigningKeyring uses os.symlink for the agent
from tempfile import NamedTemporaryFile

# The UID object is used in one place, at least,
# to get display the name and email address.
# The Key object is returned from a few functions, so it's
# API is somewhat external.
from .gpgkey import Key, UID
log = logging.getLogger(__name__)


#####
## INTERNAL API
##
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(parent_dir, "monkeysign"))
from monkeysign.gpg import Keyring, TempKeyring
from monkeysign.gpg import GpgRuntimeError



def UIDExport(uid, keydata):
    """Export only the UID of a key.
    Unfortunately, GnuPG does not provide smth like
    --export-uid-only in order to obtain a UID and its
    signatures."""
    log = logging.getLogger(__name__ + ".UIDExport")
    tmp = TempKeyring()
    # Hm, apparently this needs to be set, otherwise gnupg will issue
    # a stray "gpg: checking the trustdb" which confuses the gnupg library
    tmp.context.set_option('always-trust')
    tmp.import_data(keydata)
    log.debug("Looking for %r", uid)
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
        Keyring.__init__(self, *args, **kwargs)

        self.context.set_option('primary-keyring', primary_keyring_fname)
        self.context.set_option('trustdb-name', trustdb_fname)
        self.context.set_option('no-default-keyring')


class TempSplitKeyring(SplitKeyring):
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


class TempSigningKeyring(TempSplitKeyring):
    """A temporary keyring which uses the secret keys of a parent keyring
    
    Creates a temporary keyring which can use the orignal keyring's
    secret keys.  If you don't provide a keyring as argument (i.e. None),
    a default Keyring() will be taken which represents the user's
    regular keyring.

    In fact, this is not much different from a TempSplitKeyring,
    but gpg1.4 does not see the public keys for the secret keys when run with
    --no-default-keyring and --primary-keyring.
    So we copy the public parts of the secret keys into the primary keyring.
    """
    def __init__(self, base_keyring=None, *args, **kwargs):
        # Not a new style class...
        if issubclass(self.__class__, object):
            super(TempSigningKeyring, self).__init__(*args, **kwargs)
        else:
            TempSplitKeyring.__init__(self, *args, **kwargs)

        if base_keyring is None:
            base_keyring = Keyring()

        # Copy the public parts of the secret keys to the tmpkeyring
        for fpr, key in base_keyring.get_keys(None,
                                              secret=True,
                                              public=False).items():
            self.import_data (base_keyring.export_data (fpr))

        ## We don't copy the config file, because we're not using a separate
        ## homedir. So we expect gpg to still use it's normal homedir and thus
        ## it's normal configuration.
        # self.copy_agent_socket(base_keyring)

    def copy_agent_socket(self, base_keyring):
        ## Copied from monkeysign/ui.py as of
        ## 741dde1cc242bf125dd206a019028736d9c4a141

        # install the gpg agent socket for GnuPG 2.1 because
        # --secret-keyring silently fails
        # this is apparently how we should do things:
        # https://lists.gnupg.org/pipermail/gnupg-devel/2015-January/029301.html
        # cargo-culted from caff, thanks guilhem!
        src = base_keyring.get_agent_socket()
        dst = self.get_agent_socket()
        log.info(_('installing symlinks for sockets from %s to %s'), src, dst)
        try:
            os.unlink(dst)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        os.symlink(src, dst)




from monkeysign.gpg import Keyring
def parse_sig_list(text):
    '''Parses GnuPG's signature list (i.e. list-sigs)
    
    The format is described in the GnuPG man page'''
    sigslist = []
    for block in text.split("\n"):
        if block.startswith("sig"):
            record = block.split(":")
            log.debug("sig record (%d) %s", len(record), record)
            keyid, timestamp, uid = record[4], record[5], record[9]
            sigslist.append((keyid, timestamp, uid))

    return sigslist


def signatures_for_keyid(keyid, keyring=None):
    '''Returns the list of signatures for a given key id
    
    This will call out to GnuPG list-sigs, using Monkeysign,
    and parse the resulting string into a list of signatures.
    
    A default Keyring will be used unless you pass an instance
    as keyring argument.
    '''
    if keyring is None:
        kr = Keyring()
    else:
        kr = keyring

    # FIXME: this would be better if it was done in monkeysign
    kr.context.call_command(['list-sigs', keyid])
    siglist = parse_sig_list(kr.context.stdout)

    return siglist



## Monkeypatching to get more debug output
import monkeysign.gpg
bc = monkeysign.gpg.Context.build_command
def build_command(*args, **kwargs):
    ret = bc(*args, **kwargs)
    #log.info("Building command %s", ret)
    log.debug("Building cmd: %s", ' '.join(["'%s'" % c for c in ret]))
    return ret
monkeysign.gpg.Context.build_command = build_command


def is_usable(key):
    unusable =    key.invalid or key.disabled \
               or key.expired or key.revoked
    log.debug('Key %s is invalid: %s (i:%s, d:%s, e:%s, r:%s)', key, unusable,
        key.invalid, key.disabled, key.expired, key.revoked)
    return not unusable

def filter_usable_keys(keys):
    usable_keys = [Key.from_monkeysign(key) for key in keys if is_usable(key)]
    log.debug('Identified usable keys: %s', usable_keys)
    return usable_keys


def get_usable_keys_from_keyring(keyring, pattern, public, secret):
    keys_dict = keyring.get_keys(pattern=pattern,
    							 public=public,
    							 secret=secret) or {}
    assert keys_dict is not None, keyring.context.stderr
    # keys_fpr = keys_dict.items()
    keys = keys_dict.values()
    return filter_usable_keys(keys)


def sign_keydata(keydata, error_cb=None, homedir=None):
    """Signs OpenPGP keydata with your regular GnuPG secret keys
    
    If error_cb is provided, that function is called with any exception
    occuring during signing of the key.  If error_cb is False, any
    exception is raised.
    
    yields pairs of (uid, signed_uid)
    """
    log = logging.getLogger(__name__ + ':sign_keydata_encrypt')

    tmpkeyring = TempSigningKeyring(homedir=homedir,
        base_keyring=Keyring(homedir=homedir))
    # Eventually, we want to let the user select their keys to sign with
    # For now, we just take whatever is there.
    secret_keys = get_usable_secret_keys(homedir=homedir)
    log.info('Signing with these keys: %s', secret_keys)

    stripped_key = MinimalExport(keydata)
    fingerprint = fingerprint_from_keydata(stripped_key)

    log.debug('Trying to import key\n%s', stripped_key)
    if tmpkeyring.import_data(stripped_key):
        # 3. for every user id (or all, if -a is specified)
        # 3.1. sign the uid, using gpg-agent
        keys = tmpkeyring.get_keys(fingerprint)
        log.info("Found keys %s for fp %s", keys, fingerprint)
        if len(keys) != 1:
            raise ValueError("We received multiple keys for fp %s: %s"
                             % (fingerprint, keys))
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
            try:
                ret = tmpkeyring.sign_key(fingerprint, signall=True)
            except GpgRuntimeError as e:
                uid = uidlist[0].uid
                log.exception("Error signing %r with secret key %r. stdout: %r, stderr: %r",
                    uid, secret_key, tmpkeyring.context.stdout, tmpkeyring.context.stderr)
                if error_cb:
                    e.uid = uid
                    error_cb (e)
                else:
                    raise
                continue
            log.info("Result of signing %s on key %s: %s", uidlist[0].uid, fingerprint, ret)


        for uid in uidlist:
            uid_str = uid.uid
            log.info("Processing uid %r %s", uid, uid_str)

            # 3.2. export and encrypt the signature
            # 3.3. mail the key to the user
            signed_key = UIDExport(uid_str, tmpkeyring.export_data(uid_str))
            log.info("Exported %d bytes of signed key", len(signed_key))
            yield (uid, signed_key)

##
## END OF INTERNAL API
#####





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
    if len(keys) != 1:
        log.debug('Operation on keydata "%s" failed', keydata)
        raise ValueError("Expected exactly one key, but got %d: %r" % (
        				 len(keys), keys))
    else:
        # The first (key, value) pair in the keys dict
        # next(iter(keys.items()))[0] might be semantically
        # more correct than list(d.items()) as we don't care
        # much about having a list created, but I think it's
        # more legible.
        fpr_key = list(keys.items())[0]
        # is composed of the fpr as key and an OpenPGP key as value
        key = fpr_key[1]
        return Key.from_monkeysign(key)



def get_public_key_data(fpr, homedir=None):
    """Returns keydata for a given fingerprint
    
    In fact, fpr could be anything that gpg happily exports.
    """
    keyring = Keyring(homedir=homedir)
    keydata = keyring.export_data(fpr)
    if not keydata:
        s = "No data to export for {} (in {})".format(fpr, homedir)
        raise ValueError(s)
    return keydata




def fingerprint_from_keydata(keydata):
    '''Returns the OpenPGP Fingerprint for a given key'''
    openpgpkey = openpgpkey_from_data(keydata)
    return openpgpkey.fpr


def get_usable_keys(pattern="", homedir=None):
    '''Uses get_keys on the keyring and filters for
    non revoked, expired, disabled, or invalid keys'''
    log.debug('Retrieving keys for %s, %s', pattern, homedir)
    keyring = Keyring(homedir=homedir)
    return get_usable_keys_from_keyring(keyring=keyring,
    	pattern=pattern, public=True, secret=False)


def get_usable_secret_keys(pattern="", homedir=None):
    '''Returns all secret keys which can be used to sign a key'''
    keyring = Keyring(homedir=homedir)
    return get_usable_keys_from_keyring(keyring=keyring,
    	pattern=pattern, public=False, secret=True)



def sign_keydata_and_encrypt(keydata, error_cb=None, homedir=None):
    """Signs OpenPGP keydata with your regular GnuPG secret keys
    and encrypts the result under the given key
    
    error_cb can be a function that is called with any exception
    occuring during signing of the key.
    """
    tmpkeyring = TempKeyring()
    tmpkeyring.import_data(keydata)
    fingerprint = fingerprint_from_keydata(keydata)
    tmpkeyring.context.set_option('always-trust')
    for (uid, signed_key) in sign_keydata(keydata,
        error_cb=error_cb, homedir=homedir):
            if not uid.revoked:
                encrypted_key = tmpkeyring.encrypt_data(data=signed_key,
                    # We use the fingerprint rather than the email address,
                    # because we cannot get a reliable representation of the
                    # UID, i.e. when it contains non-UTF-8 bytes.
                    recipient=fingerprint)
                yield (UID.from_monkeysign(uid), encrypted_key)
