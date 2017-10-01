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
from time import sleep

from .util import sign_keydata_and_send

if sys.version_info.major < 3:
    input = raw_input

def main(args):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        raise ValueError("You need to give filesnames as args: %s" % args)
    for fname in args:
        data = open(fname, 'r').read()
        log.info("Calling %r to sign %s", sign_keydata_and_send, fname)
        tmpfiles = list(sign_keydata_and_send(keydata=data))
    log.info("Finished signing. " +
             "We're only waiting for the signature " +
             "files to be picked up. " +
             "Press any key to quit the application.")
    input()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
