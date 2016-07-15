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

import hmac
import logging

from monkeysign.gpg import Keyring

log = logging.getLogger()


def mac_generate(key, data):
    mac = hmac.new(key, data).hexdigest().upper()
    log.info("MAC of %r is %r", data[:20], mac[:20])
    return mac

def mac_verify(key, data, mac):
    computed_mac = mac_generate(key, data)
    result = hmac.compare_digest(mac.upper(), computed_mac.upper())
    log.info("MAC of %r seems to be %r. Expected %r (%r)",
             data[:20], computed_mac[:20], mac[:20], result)
    return result



def get_public_key_data(fpr):
    keydata = Keyring().export_data(fpr)
    return keydata



def email_file(to, from_=None, subject=None,
               body=None,
               ccs=None, bccs=None,
               files=None, utf8=True):
    cmd = ['xdg-email']
    if utf8:
        cmd += ['--utf8']
    if subject:
        cmd += ['--subject', subject]
    if body:
        cmd += ['--body', body]
    for cc in ccs or []:
        cmd += ['--cc', cc]
    for bcc in bccs or []:
        cmd += ['--bcc', bcc]
    for file_ in files or []:
        cmd += ['--attach', file_]

    cmd += [to]

    log.info("Running %s", cmd)
    retval = call(cmd)
    return retval

