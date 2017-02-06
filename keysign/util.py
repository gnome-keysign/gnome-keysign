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
from subprocess import call
from string import Template
from tempfile import NamedTemporaryFile
from urlparse import urlparse, parse_qs
from urlparse import ParseResult

import requests

from .gpgmh import fingerprint_from_keydata
from .gpgmh import sign_keydata_and_encrypt

log = logging.getLogger(__name__)


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



def email_file(to, from_=None, subject=None,
               body=None,
               ccs=None, bccs=None,
               files=None, utf8=True):
    "Calls xdg-email with the appriopriate options"
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



SUBJECT = 'Your signed key $fingerprint'
BODY = '''Hi $uid,


I have just signed your key

      $fingerprint


Thanks for letting me sign your key!

--
GNOME Keysign
'''


def sign_keydata_and_send(keydata, error_cb=None):
    """Creates, encrypts, and send signatures for each UID on the key
    
    You are supposed to give OpenPGP data which will be passed
    onto sign_keydata_and_encrypt.
    
    For the resulting signatures, emails are created and
    sent via email_file.
    
    Return value:  NamedTemporaryFiles used for saving the signatures.
    If you let them go out of scope they should get deleted.
    But don't delete too early as the MUA needs to pick them up.
    """
    log = logging.getLogger(__name__ + ':sign_keydata')

    fingerprint = fingerprint_from_keydata(keydata)
    # FIXME: We should rather use whatever GnuPG tells us
    keyid = fingerprint[-8:]
    # We list() the signatures, because we believe that it's more
    # acceptable if all key operations are done before we go ahead
    # and spawn an email client.
    log.info("About to create signatures for key with fpr %r", fingerprint)
    for uid, encrypted_key in list(sign_keydata_and_encrypt(keydata, error_cb)):
            # FIXME: get rid of this redundant assignment
            uid_str = "{}".format(uid)
            ctx = {
                'uid' : uid_str,
                'fingerprint': fingerprint,
                'keyid': keyid,
            }
            tmpfile = NamedTemporaryFile(prefix='gnome-keysign-',
                                         suffix='.asc',
                                         delete=True)
            filename = tmpfile.name
            log.info('Writing keydata to %s', filename)
            tmpfile.write(encrypted_key)
            # Interesting, sometimes it would not write the
            # whole thing out, so we better flush here
            tmpfile.flush()
            # If we close the actual file descriptor to free
            # resources. Calling tmpfile.close would get the file deleted.
            tmpfile.file.close()

            subject = Template(SUBJECT).safe_substitute(ctx)
            body = Template(BODY).safe_substitute(ctx)
            email_file (to=uid.email, subject=subject,
                        body=body, files=[filename])
            yield tmpfile


def format_fingerprint(fpr):
    """Formats a given fingerprint (160bit, so 20 characters) in the
    GnuPG typical way
    """
    s = ''
    for i in range(10):
        # output 4 chars
        s += ''.join(fpr[4*i:4*i+4])
        # add extra space between the block
        if i == 4: s += '\n'
        # except at the end
        elif i < 9: s += ' '
    return s




def parse_barcode(barcode_string):
    """Parses information contained in a barcode

    It returns a dict with the parsed attributes.
    We expect the dict to contain at least a 'fingerprint'
    entry. Others might be added in the future.
    """
    # The string, currently, is of the form
    # openpgp4fpr:foobar?baz=qux#frag=val
    # Which urlparse handles perfectly fine.
    p = urlparse(barcode_string)
    log.debug("Parsed %r into %r", barcode_string, p)
    fpr = p.path
    query = parse_qs(p.query)
    fragments = parse_qs(p.fragment)
    rest = {}
    rest.update(query)
    rest.update(fragments)
    # We should probably ensure that we have only one
    # item for each parameter and flatten them accordingly.
    rest['fingerprint'] = fpr

    log.debug('Parsed barcode into %r', rest)
    return rest



FPR_PREFIX = "OPENPGP4FPR:"

def strip_fingerprint(input_string):
    '''Strips a fingerprint of any whitespaces and returns
    a clean version. It also drops the "OPENPGP4FPR:" prefix
    from the scanned QR-encoded fingerprints'''
    # The split removes the whitespaces in the string
    cleaned = ''.join(input_string.split())

    if cleaned.upper().startswith(FPR_PREFIX.upper()):
        cleaned = cleaned[len(FPR_PREFIX):]

    log.warning('Cleaned fingerprint to %s', cleaned)
    return cleaned




def download_key_http(address, port):
    url = ParseResult(
        scheme='http',
        # This seems to work well enough with both IPv6 and IPv4
        netloc="[[%s]]:%d" % (address, port),
        path='/',
        params='',
        query='',
        fragment='')
    log.debug("Starting HTTP request")
    data = requests.get(url.geturl(), timeout=5).content
    log.debug("finished downloading %d bytes", len(data))
    return data
