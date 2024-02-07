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
import base64
import logging
import os  # The SigningKeyring uses os.symlink for the agent
from subprocess import check_output
import sys
from tempfile import mkdtemp
import platform

import dbus
import gpg
from gpg.constants import PROTOCOL_OpenPGP, IMPORT_NEW, IMPORT_SIG
from gpg.errors import GPGMEError


from .gpgkey import Key, UID

texttype = unicode if sys.version_info.major < 3 else str

log = logging.getLogger(__name__)


#####
## INTERNAL API
##

class GPGRuntimeError(RuntimeError):
    pass

class GenEdit:
    _ignored_status = (gpg.constants.STATUS_EOF,
                       gpg.constants.STATUS_GOT_IT,
                       gpg.constants.STATUS_NEED_PASSPHRASE,
                       gpg.constants.STATUS_GOOD_PASSPHRASE,
                       gpg.constants.STATUS_BAD_PASSPHRASE,
                       gpg.constants.STATUS_USERID_HINT,
                       gpg.constants.STATUS_SIGEXPIRED,
                       gpg.constants.STATUS_KEYEXPIRED,
                       gpg.constants.STATUS_PROGRESS,
                       gpg.constants.STATUS_KEY_CREATED,
                       gpg.constants.STATUS_ALREADY_SIGNED,
                       gpg.constants.STATUS_KEY_CONSIDERED,
                       gpg.constants.STATUS_CARDCTRL)

    def __init__(self, generator):
        generator.send(None)
        self.generator = generator
        self.last_sink_index = 0

    def edit_cb(self, status, args, sink=None):
        if status in self._ignored_status:
                logging.info("Returning None for %r %r", status, args)
                return
        if not status:
            logging.info("Closing for %r", status)
            self.generator.close()
            return
        # 0 is os.SEEK_SET
        if sink:
            # os.SEEK_CUR = 1
            current = sink.seek(0, 1)
            sink.seek(self.last_sink_index, 0)
            sinkdata = sink.read(current)
            self.last_sink_index = current
        else:
            sinkdata = None
        log.info("edit_cb: %r %r '%s'", status, args, sinkdata)
        data = self.generator.send((status, args)) #, sinkdata))
        log.info("edit_cb data: %r", data)
        return texttype(data)

def del_uids(uids):
    status, arg = yield None
    log.info("status args: %r %r", status, arg)
    #log.info("sinkdata: %s", sinkdata)
    #uids = [l for l in sinkdata.splitlines() if l.startswith('uid:')]
    #log.info("UIDs: %s", uids)
    status, arg = yield "list"
    log.info("status args: %r %r", status, arg)
    for uid in uids:
        status, arg = yield "uid %d" % uid
        log.info("status args: %r %r", status, arg)
    if uids:
        status, arg = yield "deluid"
        log.info("status args: %r %r", status, arg)
        assert status == gpg.constants.STATUS_GET_BOOL, "%r %r" % (status, arg)
        assert arg == 'keyedit.remove.uid.okay'
        status, arg = yield "Y"
        log.info("status args: %r %r", status, arg)
    yield 'save'


def sign_key(uid=0, sign_cmd=u"sign", expire=False, check=3,
             error_cb=None):
    log.info("Signing key uid %r", uid)
    status, prompt = yield None
    if status == u"status_code_lost": # Yeah, such a constant does not exist *sigh*
        # We are here, because the agent on the host is too old for
        # what the guest, e.g. the flatpaked app, expects.
        # Let's hope we can just ignore that.
        log.info("Agent on the host might be too old: %s %s",
            status, prompt)
        status, prompt = yield None

    assert status == gpg.constants.STATUS_GET_LINE, "Expected status to be GET_LINE, but is %r" % status
    assert prompt == u"keyedit.prompt"

    status, prompt = yield u"uid %d" % uid
    # We ignore GOT_IT...
    # assert status == gpg.constants.STATUS_GOT_IT

    #status, prompt = yield None
    assert status == gpg.constants.STATUS_GET_LINE

    status, prompt = yield sign_cmd
    # We ignore GOT_IT...
    # assert status == gpg.constants.STATUS_GOT_IT

    while prompt != 'keyedit.prompt':
        if prompt == 'keyedit.sign_all.okay':
            status, prompt = yield 'Y'
        elif prompt == 'sign_uid.expire':
            status, prompt = yield '%s' % ('Y' if expire else 'N')
        elif prompt == 'sign_uid.class':
            status, prompt = yield '%d' % check
        elif prompt == 'sign_uid.okay':
            status, prompt = yield 'Y'
        elif status == gpg.constants.STATUS_INV_SGNR:
            # seems to happen if you have an expired
            # (or otherwise unusable) signing key.
            # The CONSIDERED line should have been issued
            # with details.
            # We don't maintain that state at the moment which is
            # a bit unfortunate as we cannot properly detect
            # when we have no usable key at all rather than
            # one key being expired.
            log.warn("INV_SGNR: %r", prompt)
            status, prompt = yield None
        elif status == gpg.constants.STATUS_PINENTRY_LAUNCHED:
            status, prompt = yield None
        elif status == gpg.constants.STATUS_GOT_IT:
            status, prompt = yield None
        elif status == gpg.constants.STATUS_ALREADY_SIGNED:
            status, prompt = yield u'Y'
        elif status == gpg.constants.STATUS_ERROR:
            if error_cb:
                error_cb(prompt)
            else:
                raise GPGRuntimeError("Error signing key: %s" % prompt)
            status, prompt = yield None
        else:
            raise AssertionError("Unexpected state %r %r" % (status, prompt))

    yield u"save"




def UIDExport(keydata, uid_i):
    """Export only the UID of a key.
    Unfortunately, GnuPG does not provide smth like
    --export-uid-only in order to obtain a UID and its
    signatures."""
    log.debug("Deletion of UID %r from %r", uid_i, keydata)
    if not uid_i >= 1:
        log.debug("Raising because uid: %r", uid_i)
        raise ValueError("Expected UID to be >= 1, but is %r", uid_i)
    ctx = TempContext()
    ctx.op_import(keydata)
    result = ctx.op_import_result()
    if result.considered != 1 or result.imported != 1:
        raise ValueError("Expected exactly one key in keydata. %r" % result)
    else:
        assert len(result.imports) == 1
        fpr = result.imports[0].fpr
        key = ctx.get_key(fpr)
        uids_to_remove = {i for i in range(1, len(key.uids)+1)}
        uids_to_remove.remove(uid_i)
        if uids_to_remove:
            sink = gpg.Data()
            ctx.interact(key,
                GenEdit(del_uids(uids_to_remove)).edit_cb,
                fnc_value=sink, sink=sink)
            sink.seek(0, 0)
            log.debug("Data after UIDExport: %s", sink.read())
        uid_data = gpg.Data()
        ctx.op_export_keys([key], 0, uid_data)
        uid_data.seek(0, 0)
        uid_bytes = uid_data.read()
        log.debug("UID %r: %r", uid_i, uid_bytes)
        return uid_bytes

def export_uids(keydata):
    """Export each valid and non-revoked UID of a key

    Returns: An iterator over a tuple of the UID, i.e. the string and
    the bytes making the OpenPGP with that UID only.
    """
    ctx = TempContext()
    ctx.op_import(keydata)
    result = ctx.op_import_result()
    log.debug("ExportUIDs: Imported %r", result)
    if result.considered != 1 or result.imported != 1:
        raise ValueError("Expected exactly one key in keydata. %r" % result)
    else:
        assert len(result.imports) == 1
        fpr = result.imports[0].fpr
        key = ctx.get_key(fpr)
        for i, uid in enumerate(key.uids, start=1):
            log.info("Potentially deleting UID %d: %r", i, uid)
            if not uid.invalid and not uid.revoked:
                uid_data = UIDExport(keydata, i)
                yield (uid.uid, uid_data)





def is_usable(key):
    unusable =    key.invalid or key.disabled \
               or key.expired or key.revoked
    log.debug('Key %s is invalid: %s (i:%s, d:%s, e:%s, r:%s)', key, unusable,
        key.invalid, key.disabled, key.expired, key.revoked)
    return not unusable

def filter_usable_keys(keys):
    usable_keys = [Key.from_gpgme(key) for key in keys if is_usable(key)]
    log.debug('Identified usable keys: %s', usable_keys)
    return usable_keys



class DirectoryContext(gpg.Context):
    def __init__(self, homedir):
        super(DirectoryContext, self).__init__()
        self.set_engine_info(PROTOCOL_OpenPGP, None, homedir)
        self.homedir = homedir

class TempContext(DirectoryContext):
    def __init__(self):
        self.homedir = mkdtemp(suffix="-gnome-keysign")
        super(TempContext, self).__init__(homedir=self.homedir)

    def __del__(self):
        try:
            # shutil.rmtree(self.homedir, ignore_errors=True)
            pass
        except:
            log.exception("During cleanup of %r", self.homedir)

def get_agent_socket_path_for_homedir(homedir):
    homedir_cmd = ["--homedir", homedir] if homedir else []
    cmd = ["gpgconf"] + homedir_cmd + \
          ["--list-dirs", "agent-socket"]
    path = check_output(cmd).strip()
    log.info("Path for %r: %r", homedir, path)
    return path


class TempContextWithAgent(TempContext):
    def __init__(self, oldctx):
        super(TempContextWithAgent, self).__init__()
        homedir = self.homedir
        log.info("new homedir: %r", homedir)
        assert (len(list(self.keylist())) == 0)
        assert (len(list(self.keylist(secret=True))) == 0)


        old_homedir = oldctx.engine_info.home_dir if oldctx else None

        log.info("Old homedir: %r", old_homedir)
        old_agent_path = get_agent_socket_path_for_homedir(old_homedir)
        new_agent_path = get_agent_socket_path_for_homedir(homedir)
        os.symlink(old_agent_path, new_agent_path)

        assert len(list(self.keylist())) == 0
        assert len(list(self.keylist(secret=True))) == 0

        secret_keys = list(oldctx.keylist(secret=True))
        log.info("old secret keys: %r", secret_keys)
        for key in secret_keys:
            log.debug("Making %r known in new ctx", key)
            def export_key(fpr):
                # FIXME: The Context should really be able to export()
                public_key = gpg.Data()
                oldctx.op_export(fpr, 0, public_key)
                public_key.seek(0, os.SEEK_SET)
                return public_key
            keydata = export_key(key.subkeys[0].fpr)
            self.op_import(keydata)
            result = self.op_import_result()
            # Hrm. Only gpgme>=1.9 has a repr for the result, I think
            log.debug("Import result: %r", result)
            log.debug("Import result imports: %r", result.imports)
            log.debug("Import result considered: %r", result.considered)
            assert len(result.imports) >= 1
            i = result.imports[0]
            # 0 is success, I guess.
            assert i.result == 0
            log.debug("Import result i result status: %r %r %r", i.result, i.status, i.fpr)
            log.debug("Import result GPGME_IMPORT_NEW: %r", i.status & gpg.constants.IMPORT_NEW)


        assert len(list(self.keylist())) == len(secret_keys)
        log.info("new secret keys: %r", list(self.keylist(secret=True)))
        assert len(secret_keys) == len(list(self.keylist(secret=True)))



def import_signature_dbus(signature):
    "Imports a TPK into the user's keyring by using Seahorse's DBus API"
    name = "org.gnome.seahorse"
    path = "/org/gnome/seahorse/keys"
    bus = dbus.SessionBus()
    result = []

    proxy = bus.get_object(name, path)
    iface = "org.gnome.seahorse.KeyService"
    gpg_iface = dbus.Interface(proxy, iface)
    payload = base64.b64encode(signature).decode('latin-1')
    payload = '\n'.join(payload[i:(i + 64)] for i in range(0, len(payload), 64))
    payload = "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\n" + payload + "\n-----END PGP PUBLIC KEY BLOCK-----"
    result = gpg_iface.ImportKeys("openpgp", payload)
    log.debug("Importing via DBus: %r", result)

    return result

def import_signature_gpgme(signature, homedir=None):
    "Imports an OpenPGP TPK into a keyring via GPGME"
    ctx = DirectoryContext(homedir)
    ctx.op_import(signature)
    result = ctx.op_import_result()
    if len(result.imports) < 1:
        raise GPGMEError

    return result



##
## END OF INTERNAL API
#####




def get_signatures_for_uids_on_key(key, homedir=None):
    """It seems to be a bit hard to get a key with its signatures,
    so this is a small helper function"""
    # esp. get_key does not take a SIGS argument.
    # What happens if keylist returns multiple keys, e.g. because there
    # is another key with a UID named as the fpr?  How can I make sure I
    # get the signatures of any given key?
    
    # *sigh* gpgme is killing me. With gpgme 1.8 we have to
    # set_keylist_mode before we can call keylist.  With gpgme 1.9
    # keylist takes a mode argument and overrides whatever has been
    # set before.  In order to come with something compatible with both
    # 1.8 and 1.9 we have to set_keylist_mode and NOT call ctx.keylist
    # but rather the bare op_keylist_all.  In 1.8 that requires two
    # arguments.
    ctx = DirectoryContext(homedir)
    mode = gpg.constants.keylist.mode.LOCAL | gpg.constants.keylist.mode.SIGS
    secret = False
    ctx.set_keylist_mode(mode)
    keys = list(ctx.op_keylist_all(key.fpr, secret))
    # With gpgme 1.9 we can simply do:
    # keys = list(ctx.keylist(key.fpr), mode=mode)
    assert len(keys) == 1
    uid_sigs = {uid.uid: {s.keyid for s in uid.signatures} for uid in keys[0].uids}
    log.info("Signatures: %r", uid_sigs)
    return uid_sigs



def openpgpkey_from_data(keydata):
    c = TempContext()
    c.op_import(gpg.Data(keydata))
    result = c.op_import_result()
    log.debug("Import Result: %s", result)
    if result.imported != 1:
        raise ValueError("Keydata did not contain exactly one key, but %r" %
            result.imported)
    else:
        imported = result.imports
        import_ = imported[0]
        fpr = import_.fpr
        key = c.get_key(fpr)
        return Key.from_gpgme(key)



def get_public_key_data(fpr, homedir=None):
    c = DirectoryContext(homedir)
    c.armor = True
    sink = gpg.Data()
    # FIXME: There will probably be an export() function
    c.op_export(fpr, 0, sink)
    sink.seek(0, os.SEEK_SET)
    keydata = sink.read()
    log.debug("Exported %r: %r", fpr, keydata)
    if not keydata:
        s = "No data to export for {} (in {})".format(fpr, homedir)
        raise ValueError(s)
    return keydata



def fingerprint_from_keydata(keydata):
    '''Returns the OpenPGP Fingerprint for a given key'''
    openpgpkey = openpgpkey_from_data(keydata)
    return openpgpkey.fingerprint

def get_usable_keys_from_context(ctx, pattern="", secret=False):
    keys = [Key.from_gpgme(key)
            for key in ctx.keylist(pattern=pattern, secret=secret)
            if is_usable(key)
                and     # We filter "offline" keys.
                        # If secret=False then it passes.
                        # If secret=True then we require the primary subkey
                        # to be "secret". It is false if the key is offline.
                (not secret or key.subkeys[0].secret)
            ]
    return keys

def get_usable_keys(pattern="", homedir=None):
    '''Uses get_keys on the keyring and filters for
    non revoked, expired, disabled, or invalid keys'''
    log.debug('Retrieving keys for %s, %s', pattern, homedir)
    ctx = DirectoryContext(homedir=homedir)
    return get_usable_keys_from_context(ctx,
    	pattern=pattern, secret=False)

def get_usable_secret_keys(pattern="", homedir=None):
    '''Returns all secret keys which can be used to sign a key'''
    ctx = DirectoryContext(homedir=homedir)
    return get_usable_keys_from_context(ctx,
    	pattern=pattern, secret=True)




def minimise_key(keydata):
    "Returns the public key exported under the MINIMAL mode"
    ctx = TempContext()
    ctx.op_import(keydata)
    result = ctx.op_import_result()
    if result.considered != 1 and result.imported != 1:
        raise ValueError("Expected to load exactly one key. %r", result)
    else:
        imports = [i for i in result.imports
                   if i.status == gpg.constants.IMPORT_NEW]
        log.debug("Import %r", result)
        assert len(imports) == 1
        fpr = result.imports[0].fpr
        key = ctx.get_key(fpr)
        sink = gpg.Data()
        ctx.op_export_keys([key], gpg.constants.EXPORT_MODE_MINIMAL, sink)
        sink.seek(0, 0)
        minimised_key = sink.read()
        return minimised_key

def local_sign_keydata(keydata, expires_in=60*60*24*1, error_cb=None, homedir=None):
    """Produces non-exportable and expiring signatures.
    This can be useful if we want to enable the user to send an email to 
    the other party right away, without waiting for the protocol to have 
    completed. By letting the signature expire, we limit the time in 
    which a wrongly signed key is harmful. This is a challenge for thx
    UX, because sending emails will stop working pretty much out of 
    the blue. But it can hardly be any worse than it is now.
    And the app ought to inform the user about the fact that it's only 
    ephemeral.

    Returns: nothing
    """
    ctx = DirectoryContext(homedir)

    tmpctx = TempContext()
    available_secret_keys = [key for key in ctx.keylist(secret=True)
        if not key.disabled or key.revoked or key.invalid or key.expired]
    log.debug('Setting available sec keys to: %r', available_secret_keys)
    ctx.signers = available_secret_keys

    tmpctx.op_import(keydata)
    result = tmpctx.op_import_result()
    if result.considered != 1 and result.imported != 1:
        raise ValueError("Expected to load exactly one key. %r", result)
    else:
        imports = result.imports
        assert len(imports) == 1
        fpr = result.imports[0].fpr

        ctx.op_import(keydata)
        key = ctx.get_key(fpr)
        # We need to sign in the regular context, because gpgme does not
        # export local signatures from a keyring.
        ctx.key_sign(key, local=True, expires_in=expires_in)
        # Unfortunately, key_sign does not report back how many
        # signatures were produced (or not produced...)
        # It may raise an error, but I have yet to see that it does...
        log.info("Locally signed key %s with an expiry in %d seconds", fpr, expires_in)


def sign_keydata_and_encrypt(keydata, error_cb=None, homedir=None):
    oldctx = DirectoryContext(homedir)
    ctx = TempContextWithAgent(oldctx)
    # We're trying to sign with all available secret keys
    available_secret_keys = [key for key in ctx.keylist(secret=True)
        if not (key.disabled or key.revoked or key.invalid or key.expired)]
    log.debug('Setting available sec keys to (%d): %r',
        len(available_secret_keys), available_secret_keys)
    ctx.signers = available_secret_keys

    ctx.op_import(minimise_key(keydata))
    result = ctx.op_import_result()
    if result.considered != 1 and result.imported != 1:
        raise ValueError("Expected to load exactly one key. %r", result)
    else:
        imports = result.imports
        assert len(imports) == 1
        fpr = result.imports[0].fpr
        key = ctx.get_key(fpr)
        sink = gpg.Data()
        # There is op_keysign, but it's only available with gpg 2.1.12
        ctx.interact(key, GenEdit(sign_key(error_cb=error_cb)).edit_cb, sink=sink)
        sink.seek(0, 0)
        log.debug("Sink after signing: %r", sink.read())

        signed_sink = gpg.Data()
        ctx.set_keylist_mode(gpg.constants.KEYLIST_MODE_SIGS)
        ctx.armor = True
        ctx.op_export_keys([key], 0, signed_sink)
        signed_sink.seek(0, 0)
        signed_keydata = signed_sink.read()
        log.debug("Signed Key: %s", signed_keydata)
        # Do I have to re-get the key to make the signatures known?
        key = ctx.get_key(fpr)

        for i, uid in enumerate(key.uids, start=1):
            if uid.revoked or uid.invalid:
                continue
            else:
                log.debug("The UID %s has %d signatures",
                    uid, len(uid.signatures))
                if len(uid.signatures) < 2:
                    log.error("We seem to not have produced signatures correctly. "
                        "%s has less than 2 signatures: %s",
                        uid, uid.signatures,
                    )

                uid_data = UIDExport(signed_keydata, i)
                log.debug("Data for uid %d: %r, sigs: %r %r", i, uid, uid.signatures, uid_data)

                ciphertext, _, _ = ctx.encrypt(plaintext=uid_data,
                                               recipients=[key],
                                               # We probably have to set owner trust
                                               # in order for it to work out of the box
                                               always_trust=True,
                                               sign=False)
                yield (UID.from_gpgme(uid), ciphertext, uid_data)


class NoNewSignatures(GPGMEError):
    "We couldn't find a new certification, so the certification is already known"
    def __init__(self, signature, import_result):
        self.signature = signature
        self.import_result = import_result
        super().__init__()
class NewRevocations(GPGMEError):
    pass
class NewSubkey(GPGMEError):
    pass

def decrypt_signature(encrypted_sig, homedir=None):
    """
    Takes an encrypted signture, tries to decrypt it, and returns the
    decrypted signature if it is does indeed contain a certification only
    """
    ctx = DirectoryContext(homedir)

    # Check if we are really importing a signature
    temp_ctx = TempContextWithAgent(ctx)
    signature = temp_ctx.decrypt(encrypted_sig)
    log.debug("signature decryption result: %r", signature)
    decrypted_sig = signature[0]
    temp_ctx.op_import(decrypted_sig)
    result = temp_ctx.op_import_result()
    log.debug("signature import result: %r", result)

    if result.imported != 0:
        log.warning("Trying to import a new key instead of a signature!")
        raise GPGMEError

    if result.new_signatures == 0:
        raise NoNewSignatures(signature=decrypted_sig, import_result=result)
    if result.new_revocations != 0:
        raise NewRevocations()
    if result.new_sub_keys != 0:
        raise NewSubkey()

    return decrypted_sig

def decrypt_and_import_signature(encrypted_sig, homedir=None):
    signature = decrypt_signature(encrypted_sig, homedir=homedir)
    import_signature(signature)
    return signature




class ImportNewCertificationError(GPGMEError):
    "The import of a TPK failed, probably due to containing a new certificate rather than new 'signatures'"


def import_signature(signature, homedir=None):
    """
    Imports an OpenPGP TPK to the local keyring

    The purpose is to import a certification (hence the name of the function)
    but it is in fact agnostic about what the TPK contains.

    This function will try to import the TPK via DBus first and,
    if that failed, resort to using gpgme directly.
    """
    result = []

    ctx = TempContextWithAgent(DirectoryContext(homedir=homedir))
    ctx.op_import(signature)
    res = ctx.op_import_result()
    log.debug("ImportSignature: Testing for new certificate: %r", res)
    imports = res.imports
    if len(imports) != 1:
        log.error("We expected to import only one certificate, "
                  "but it seems we have %d", len(import_))
        raise ImportNewCertificationError
    else:
        import_ = imports[0]
        if import_.status & gpg.constants.IMPORT_NEW:
            log.error("We did not expect to import a *new* certificate, "
                      "but this seems to be new: %r", import_)
            raise ImportNewCertificationError
        else:
            assert import_.status & gpg.constants.IMPORT_SIG

            if not homedir:
                # If a homedir is requested, we have to use the gpgme API, because we cannot specify a GnuPG keyring via DBus
                try:
                    # Try Seahorse DBus
                    result = import_signature_dbus(signature)
                except dbus.exceptions.DBusException:
                    log.debug("Seahorse DBus is not available")

            # If Seahorse failed we try op_import
            if len(result) < 1:
                result = import_signature_gpgme(signature, homedir=homedir)

        return result
