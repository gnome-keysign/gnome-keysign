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

from gi.repository import Gtk, GLib
from gi.repository import GObject

if  __name__ == "__main__" and __package__ is None:
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
from .gpgmh import get_usable_keys, get_public_key_data
from .util import mac_generate
from . import Keyserver

log = logging.getLogger(__name__)


class AvahiHTTPOffer:
    "Spawns a local HTTP daemon and announces it via Avahi"
    def __init__(self, key):
        self.key = key
        self.fingerprint = fingerprint = key.fingerprint
        self.keydata = keydata = get_public_key_data(fingerprint)
        self.keyserver = Keyserver.ServeKeyThread(str(keydata), fingerprint)

        self.mac =  mac = mac_generate(fingerprint, keydata)

    def start(self):
        "Starts offering the key"
        fingerprint = self.fingerprint.upper()
        mac = self.mac.upper()
        discovery_info = 'OPENPGP4FPR:{0}#MAC={1}'.format(
                                fingerprint, mac)

        log.info("Requesting to start")
        self.keyserver.start()

        return discovery_info

    def stop(self):
        "Stops offering the key"
        log.info("Requesting to shutdown")
        self.keyserver.shutdown()


def main(args):
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    key = get_usable_keys(pattern=args[0])[0]
    offer = AvahiHTTPOffer(key)
    discovery_info = offer.start()
    print ("Offering key: {}".format(key))
    print ("Discovery info: {}".format(discovery_info))
    try: input_ = raw_input
    except NameError: input_ = input
    input_("Press Enter to stop")
    offer.stop()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
