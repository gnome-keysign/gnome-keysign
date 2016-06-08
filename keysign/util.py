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

from monkeysign.gpg import Keyring

log = logging.getLogger()


def mac_generate(key, data):
    mac = key + data[:10]
    log.info("MAC of %r is %r", data[:20], mac[:20])
    return mac

def mac_verify(key, data, mac):
    # this is, of course, only a toy example.
    computed_mac = mac_generate(key, data)
    result = computed_mac == mac
    log.info("MAC of %r seems to be %r. Expected %r (%r)",
             data[:20], computed_mac[:20], mac[:20], result)
    return result



def get_public_key_data(fpr):
    keydata = Keyring().export_data(fpr)
    return keydata

