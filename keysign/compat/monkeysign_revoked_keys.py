#!/usr/bin/env python
#    Copyright 2015 Tobias Mueller <muelli@cryptobitch.de>
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
import sys

from gi.repository import GObject, Gtk, GLib, GdkPixbuf
import monkeysign.gpg
from monkeysign.gpg import Keyring

from datetime import datetime

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

# This checks whether monkeysign's OpenPGPkey can
# calculate the revocation.  Currently (2015-02), it cannot,
# but there has been a patch floating around.
if not isinstance(monkeysign.gpg.OpenPGPkey.revoked, property):
    log.debug('Monkeypatching Revoked into monkeysign')
    def is_revoked2(self):
        log.info('Running is_revoked on %r', self)
        fpr = self.fpr
        command = ['list-sigs']
        command += [fpr]
        # Note that "normal" monkeysign OpenPGPKeys do not
        # know about their keyring of origin.
        # You need to patch that in.
        self.keyring.context.call_command(command)
        rc = self.keyring.context.returncode
        log.debug('Call to list-sigs returned %d', rc)
        for line in self.keyring.context.stdout.splitlines():
            if line.startswith("rev:") or line.startswith('rvk:'):
                log.info('revocation found: %s', line)
                fields = line.split(':')
                revocation_type = fields[11-1]
                # 0x20: Key revocation signature
                # 0x28: Subkey revocation signature
                # 0x30: Certification revocation signature (i.e. UIDs)
                rev_type = int(revocation_type[:2], 16)
                if revocation_type == 0x20:
                    revoked = True
                else:
                    revoked = False
                break
        else:
            revoked = False
        
        return revoked


    def is_revoked(self):
        if self.trust == '-':
            # We cannot determine whether this key has been revoked.
            # Locate the public key and try again.
            is_revoked = None
        elif self.trust == 'r':
            is_revoked = True
        else:
            is_revoked = False

        return is_revoked

    monkeysign.gpg.OpenPGPkey.revoked = property(is_revoked)
    monkeysign.gpg.OpenPGPuid.revoked = property(is_revoked)
else:
    log.info('Monkeysign already patched: %s', monkeysign.gpg.__file__)


def main():
    k = Keyring()
    secret_keys = k.get_keys(public=False, secret=True)
    log.debug('Secret Keys: %s', secret_keys)
    
    for fpr, key in secret_keys.items():
        # Because gnupg does not list whether the key has been revoked
        # when listing secret keys, we need to list public keys
        pub_keys = k.get_keys(fpr, public=True)
        assert len(pub_keys) == 1
        pub_key = pub_keys[fpr]
        
        revoked = pub_key.revoked
        log.debug("Key %s is revoked: %r", pub_key, revoked)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
