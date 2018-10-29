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
import os  # The SigningKeyring uses os.symlink for the agent

# The UID object is used in one place, at least,
# to get display the name and email address.
# The Key object is returned from a few functions, so it's
# API is somewhat external.
from .gpgkey import Key, UID
log = logging.getLogger(__name__)


# We allow for disabling the gpgme based library for now,
# because it may turn out to be not working as well as expected.
# We also use the standard monkeysign module for now, because
# we know it better.  Expect that to change, though.
from . import gpgmeh as gpg


# We expect these functions:
get_usable_keys = gpg.get_usable_keys
openpgpkey_from_data = gpg.openpgpkey_from_data
get_public_key_data = gpg.get_public_key_data
fingerprint_from_keydata = gpg.fingerprint_from_keydata
get_usable_secret_keys = gpg.get_usable_secret_keys
sign_keydata_and_encrypt = gpg.sign_keydata_and_encrypt

