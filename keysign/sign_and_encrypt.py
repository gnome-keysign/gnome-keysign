#!/usr/bin/env python
#    Copyright 2020 Tobias Mueller <tobi@cryptobit.ch>
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

import argparse

import logging
import sys

from .gpgmeh import sign_keydata_and_encrypt, fingerprint_from_keydata

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sign an OpenPGP key from a file. "
        "The program will open each file, extract exactly one OpenPGP key, "
        "sign each UID separately, encrypt and write the result out to a file.")
    parser.add_argument('-v', '--verbose', action='count', default=0,
        help="Increase detail of logging")
    parser.add_argument("--preserve", action='store_true',
        help="Write files with plaintext next to the ciphertext, e.g. .plain.pgp")
    parser.add_argument("file", nargs='+', type=argparse.FileType('rb'),
        help="File containing OpenPGP keys")
    args = parser.parse_args()

    log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    log_level = log_levels[min(len(log_levels)-1, args.verbose)]
    logging.basicConfig(level=log_level)

    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)

    for fhandle in args.file:
        data = fhandle.read()
        fingerprint = fingerprint_from_keydata(data)
        for i, (uid, ciphertext, plaintext) in enumerate(sign_keydata_and_encrypt(keydata=data)):
            fname = "%s-%d.pgp" % (fingerprint, i)
            with open(fname, 'wb') as outfile:
                outfile.write(ciphertext)
                print ("Written to %s \t for UID %s" % (fname, uid))

            fname = "%s-%d.plain.pgp" % (fingerprint, i)
            with open(fname, 'wb') as outfile:
                outfile.write(plaintext)
                print ("Written Plaintext to %s \t for UID %s" % (fname, uid))



if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main())
