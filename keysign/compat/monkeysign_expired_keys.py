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

# This checks whether monkeysign's OpenPGPkey can
# calculate the expiration.  Currently (2015-02), it cannot,
# but there has been a patch floating around.
if not isinstance(monkeysign.gpg.OpenPGPkey.expired, property):
    def is_expired(self):
        log.info('Running is_expired on %r', self)
        if self.expiry:
            exp = int(self.expiry)
            expiry = datetime.fromtimestamp(int(exp))
            now = datetime.now()
            expired = now > expiry
            return expired
        else:
            return False

    monkeysign.gpg.OpenPGPkey.expired = property(is_expired)


log = logging.getLogger()

def main():
    k = Keyring()
    secret_keys = k.get_keys(public=False, secret=True)
    log.debug('Secret Keys: %s', secret_keys)
    
    for fpr, key in secret_keys.items():
        log.debug("Keys: %s", key)
        exp = key.expiry
        log.debug("Key's expiry: %r", exp)
        if exp:
            expiry = datetime.fromtimestamp(int(exp))
            now = datetime.now()
            expired = now > expiry
        else:
            expired = False
        log.debug("Key's expired: %s - %s", key.expired, expired)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
