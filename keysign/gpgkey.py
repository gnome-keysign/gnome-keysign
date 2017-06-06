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
from collections import namedtuple
from datetime import datetime
import logging
import warnings

log = logging.getLogger(__name__)

def parse_uid(uid):
    "Parses a GnuPG UID into it's name, comment, and email component"
    # remove the comment from UID (if it exists)
    com_start = uid.find(b'(')
    if com_start != -1:
        com_end = uid.find(b')')
        uid = uid[:com_start].strip() + uid[com_end+1:].strip()

    # FIXME: Actually parse the comment...
    comment = ""
    # split into user's name and email
    tokens = uid.split(b'<')
    name = tokens[0].strip()
    email = 'unknown'
    if len(tokens) > 1:
        email = tokens[1].replace('>','').strip()
    
    log.debug("Parsed %r to name (%d): %r", uid, len(name), name)
    return (name, comment, email)


def parse_expiry(value):
    """Takes either a string, an epoch, or a datetime and converts
    it to a datetime.
    If the string is empty (or otherwise evaluates to False)
    then this function returns None, meaning that no expiry has been set.
    An edge case is the epoch value "0".
    """
    if not value:
        expiry = None
    else:
        try:
            expiry = datetime.fromtimestamp(int(value))
        except TypeError:
            expiry = value

    return expiry




class Key(namedtuple("Key", ["expiry", "fingerprint", "uidslist"])):
    "Represents an OpenPGP Key to extent we care about"
    
    log = logging.getLogger(__name__)

    def __new__(cls, expiry, fingerprint, uidslist,
                       *args, **kwargs):
        exp_date = parse_expiry(expiry)
        self = super(Key, cls).__new__(cls, exp_date, fingerprint, uidslist)
        return self

    def __format__(self, arg):
        s  = "{fingerprint}\r\n"
        s += '\r\n'.join(("  {}".format(uid) for uid in self.uidslist))
# This is what original output looks like:
# pub  [unknown] 3072R/1BF98D6D 1336669781 [expiry: 2017-05-09 19:09:41]
#    Fingerprint = FF52 DA33 C025 B1E0 B910  92FC 1C34 19BF 1BF9 8D6D
# uid 1      [unknown] Tobias Mueller <tobias.mueller2@mail.dcu.ie>
# uid 2      [unknown] Tobias Mueller <4tmuelle@informatik.uni-hamburg.de>
# sub   3072R/3B76E8B3 1336669781 [expiry: 2017-05-09 19:09:41]
        return s.format(**self._asdict())

    @property
    def fpr(self):
        "Legacy compatibility, use fingerprint instead"
        warnings.warn("Legacy fpr, use the fingerprint property",
                      DeprecationWarning)
        return self.fingerprint

    @classmethod
    def from_monkeysign(cls, key):
        "Creates a new Key from an existing monkeysign key"
        log.debug("From mks: %r", key)
        uids = [UID.from_monkeysign(uid) for uid in  key.uidslist]
        expiry = parse_expiry(key.expiry)
        fingerprint = key.fpr
        return cls(expiry, fingerprint, uids)

    @classmethod
    def from_gpgme(cls, key):
        "Creates a new Key from an existing monkeysign key"
        uids = [UID.from_gpgme(uid) for uid in  key.uids]
        expiry = parse_expiry(key.subkeys[0].expires)
        fingerprint = key.fpr
        return cls(expiry, fingerprint, uids)



class UID(namedtuple("UID", "expiry uid name comment email")):
    "Represents an OpenPGP UID - at least to the extent we care about it"

    @classmethod
    def from_monkeysign(cls, uid):
        "Creates a new UID from a monkeysign key"
        # We expect to get raw bytes.
        # While RFC4880 demands UTF-8 encoded data,
        # real-life has produced non UTF-8 keys...
        rawuid = uid.uid
        log.debug("UidStr (%d): %r", len(rawuid), rawuid)
        name, comment, email = parse_uid(rawuid)
        expiry = parse_expiry(uid.expire)

        return cls(expiry, rawuid, name, comment, email)

    @classmethod
    def from_gpgme(cls, uid):
        "Creates a new UID from a monkeysign key"
        rawuid = uid.uid
        name = uid.name
        comment = '' # FIXME: uid.comment
        email = uid.email
        expiry = None  #  FIXME: Maybe UIDs don't expire themselves but via the binding signature

        return cls(expiry, rawuid, name, comment, email)
