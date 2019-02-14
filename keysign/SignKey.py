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

from .util import sign_keydata_and_send

if sys.version_info.major < 3:
    input = raw_input


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sign an OpenPGP key from a file.  The program will open each file, exrtact exactly one OpenPGP key, sign each UID separately, encrypt and send each signed UID using xdg-email.")
    parser.add_argument("file", nargs='+', type=argparse.FileType('rb'),
        help="File containing OpenPGP keys")
    args = parser.parse_args()

    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    for fhandle in args.file:
        data = fhandle.read()
        log.info("Calling %r to sign %s", sign_keydata_and_send, fhandle.name)
        tmpfiles = list(sign_keydata_and_send(keydata=data))
    print("Finished signing. " +
             "We're only waiting for the signature " +
             "files to be picked up. " +
             "Press any key to quit the application.")
    input()


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main())
