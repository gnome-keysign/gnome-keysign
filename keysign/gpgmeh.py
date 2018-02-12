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
from __future__ import unicode_literals

import logging
import os  # The SigningKeyring uses os.symlink for the agent
from subprocess import check_output
import sys
from tempfile import mkdtemp

import gpg
from gpg.constants import PROTOCOL_OpenPGP


from .gpgkey import Key, UID

texttype = unicode if sys.version_info.major < 3 else str

log = logging.getLogger(__name__)

#####
## INTERNAL API
##

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
    assert status == gpg.constants.STATUS_GET_LINE
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
        #elif status == gpg.constants.STATUS_INV_SGNR:
            # When does this actually happen?
        #    status, prompt = yield None
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
                raise RuntimeError("Error signing key: %s" % prompt)
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
    """Export each valid and non-revoked UID of a key"""
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
        self.homedir = mkdtemp()
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



##
## END OF INTERNAL API
#####





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
    return openpgpkey.fpr

def get_usable_keys_from_context(ctx, pattern="", secret=False):
    keys = [Key.from_gpgme(key)
            for key in ctx.keylist(pattern=pattern, secret=secret)
            if is_usable(key)]
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

def sign_keydata_and_encrypt(keydata, error_cb=None, homedir=None):
    oldctx = DirectoryContext(homedir)
    ctx = TempContextWithAgent(oldctx)
    # We're trying to sign with all available secret keys
    available_secret_keys = [key for key in ctx.keylist(secret=True)
        if not key.disabled or key.revoked or key.invalid or key.expired]
    log.debug('Setting available sec keys to: %r', available_secret_keys)
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
                uid_data = UIDExport(signed_keydata, i)
                log.debug("Data for uid %d: %r, sigs: %r %r", i, uid, uid.signatures, uid_data)

                ciphertext, _, _ = ctx.encrypt(plaintext=uid_data,
                                               recipients=[key],
                                               # We probably have to set owner trust
                                               # in order for it to work out of the box
                                               always_trust=True,
                                               sign=False)
                yield (UID.from_gpgme(uid), ciphertext)
