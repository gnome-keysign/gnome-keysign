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

import signal
import sys
import argparse
import logging
import os


if __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')

from .__init__ import __version__
from .gpgmeh import get_usable_keys, get_public_key_data
from .i18n import _
from .util import mac_generate, format_fingerprint
from . import Keyserver

log = logging.getLogger(__name__)


class AvahiHTTPOffer:
    "Spawns a local HTTP daemon and announces it via Avahi"
    def __init__(self, key):
        self.key = key
        self.fingerprint = fingerprint = key.fingerprint
        self.keydata = keydata = get_public_key_data(fingerprint)
        self.keyserver = Keyserver.ServeKeyThread(keydata, fingerprint)
        self.mac = mac_generate(fingerprint.encode('ascii'), keydata)

    def allocate_code(self):
        """Returns the information necessary to discover the key through Avahi"""
        fingerprint = self.fingerprint.upper()
        mac = self.mac.upper()
        discovery_info = 'OPENPGP4FPR:{0}#MAC={1}'.format(
                                fingerprint, mac)
        return format_fingerprint(self.key.fingerprint), discovery_info

    def start(self):
        """Starts offering the key"""
        log.info("Requesting to start")
        self.keyserver.start()


    def stop(self):
        "Stops offering the key"
        log.info("Requesting to shutdown")
        self.keyserver.shutdown()


def main(args):
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    key = get_usable_keys(pattern=args[0])[0]
    offer = AvahiHTTPOffer(key)
    discovery_info = offer.allocate_code()
    print (_("Offering key: {}").format(key))
    print (_("Discovery info: {}").format(discovery_info))
    offer.start()
    print (_("Press Enter to stop"))
    try: input_ = raw_input
    except NameError: input_ = input
    input_("Press Enter to stop")
    offer.stop()


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
