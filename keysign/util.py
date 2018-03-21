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

import hashlib
import hmac
import logging
import os
import shutil
from subprocess import call
from string import Template
from tempfile import NamedTemporaryFile
try:
    from urllib.parse import urlparse, parse_qs
    from urllib.parse import ParseResult
    from urllib.request import quote
except ImportError:
    from urlparse import urlparse, parse_qs
    from urlparse import ParseResult
    from urllib2 import quote

import requests
import dbus
from gi.repository import Gtk, Gdk, GLib

from .gpgmh import fingerprint_from_keydata
from .gpgmh import sign_keydata_and_encrypt

log = logging.getLogger(__name__)


def mac_generate(key, data):
    mac = hmac.new(key, data, hashlib.sha256).hexdigest().upper()
    log.info("MAC of %r is %r", data[:20], mac[:20])
    # Arbitrary truncation to avoid a QR code size increase
    return mac[:20]


def mac_verify(key, data, mac):
    computed_mac = mac_generate(key, data)
    result = hmac.compare_digest(mac.upper(), computed_mac.upper())
    log.info("MAC of %r seems to be %r. Expected %r (%r)",
             data[:20], computed_mac[:20], mac[:20], result)
    return result


def _email_portal(to, subject=None, body=None, files=None):
    # The following checks are to ensure Python 2 compatibility
    if not hasattr(os, 'O_PATH'):
        os.O_PATH = 2097152
    if not hasattr(os, 'O_CLOEXEC'):
        os.O_CLOEXEC = 524288
    name = "org.freedesktop.portal.Desktop"
    path = "/org/freedesktop/portal/desktop"
    bus = dbus.SessionBus()
    try:
        proxy = bus.get_object(name, path)
    except dbus.exceptions.DBusException:
        log.debug("Desktop portal is not available")
        return None
    iface = "org.freedesktop.portal.Email"
    email = dbus.Interface(proxy, iface)
    # Apparently we are unable to get the parent window XID from the receive class.
    # Until this is sorted out, we leave the parent window empty.
    parent_window = ""
    attrs = []
    # Even if we don't close the file descriptor it should not be a problem because
    # eventually at runtime it will be automatically closed.
    # Designing this class we took the recipes one as reference
    # https://gitlab.gnome.org/GNOME/recipes/blob/4afc9df6/src/gr-mail.c#L293
    if files:
        for file in files:
            fd = os.open(file, os.O_PATH | os.O_CLOEXEC)
            attrs.append(dbus.types.UnixFd(fd))
    opts = {"subject": subject, "address": to, "body": body, "attachment_fds": attrs}
    try:
        ret = email.ComposeEmail(parent_window, opts)
        return ret
    except TypeError:
        log.debug("Email portal is not available")
        return None


def _email_mailto(to, subject=None, body=None, files=None):
    url = "mailto:"
    url += "\"{0}\"".format(to)
    # Apparently we don't need to use urllib.parse.quote_plus
    if subject:
        url += "?subject={0}".format(subject)
    if body:
        if "?" in url:
            url += "&body={0}".format(quote(body))
        else:
            url += "?body={0}".format(quote(body))
    for file in files:
        if "?" in url:
            url += "&attach={0}".format(file)
        else:
            url += "?attach={0}".format(file)
    try:
        Gtk.show_uri(None, url, Gdk.CURRENT_TIME)
        return True
    except GLib.GError as e:
        log.debug("mailto URI is probably not available: %s", e.message)
        return None


def _email_file(to, from_=None, subject=None,
                body=None,
                ccs=None, bccs=None,
                files=None, utf8=True):
    """Calls xdg-email with the appropriate options"""
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

    if not to:
        log.error("email_file: We are seeing an empty 'to': %r", to)

    cmd += [to]

    log.info("Running %s", cmd)
    retval = call(cmd)
    return retval


def _using_flatpak():
    """Check if we are inside flatpak"""
    return os.path.exists("/.flatpak-info")


def _fix_path_flatpak(files):
    """In Flatpak the only special path visible also from outside is /var/tmp/
    To be able to use the files from the host we change the path to the absolute one.
    This fix in the future may not be necessary because the portals should be able
    to automatically handle it."""
    tmp_flat = "/tmp"
    var_flat = "/var"
    var_tmp_flat = "/var/tmp"
    part_1 = os.path.expanduser("~/.var/app/")
    app_id = "org.gnome.Keysign"
    part_2 = "cache/tmp/"
    flatpak_path = os.path.join(part_1, app_id, part_2)
    fixed_files = []
    if files:
        for file in files:
            if file.startswith(tmp_flat):
                shutil.move(file, var_flat + file)
                fixed_files.append(flatpak_path + file[len(var_flat)+1:])
            elif file.startswith(var_tmp_flat):
                # This is a legacy check because in the older versions of flatpak the temp
                # files where placed under /var/tmp/ instead of /tmp/
                fixed_files.append(flatpak_path + file[len(tmp_flat)+1:])
            else:
                fixed_files.append(file)
    return fixed_files


def send_email(to, subject=None, body=None, files=None):
    """Tries to send the email using firstly the portal, then the xdg-email
    and as a last attempt the mailto uri"""
    if _using_flatpak():
        files = _fix_path_flatpak(files)

    if _email_portal(to, subject, body, files):
        return

    try:
        _email_file(to=to, subject=subject, body=body, files=files)
        return
    except FileNotFoundError:
        log.debug("xdg-email is not available")

    if _email_mailto(to, subject, body, files):
        return

    log.error("An error occurred trying to compose the email")


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
    sent via send_email.
    
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
        log.info("Using UID: %r", uid)
        # We expect uid.uid to be a consumable string
        uid_str = uid.uid
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
        send_email(uid.email, subject, body, [filename])
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


def fix_infobar(infobar):
    # Work around https://bugzilla.gnome.org/show_bug.cgi?id=710888
    # Taken from here https://phabricator.freedesktop.org/D1103#34aa2703
    def make_sure_revealer_does_nothing(widget):
        if not isinstance(widget, Gtk.Revealer):
            return
        widget.set_transition_type(Gtk.RevealerTransitionType.NONE)
    infobar.forall(make_sure_revealer_does_nothing)


def get_local_bt_address(hci_number=0):
    bus = dbus.SystemBus()
    adapter = dbus.Interface(bus.get_object("org.bluez", "/org/bluez/hci%i" % hci_number),
                             "org.freedesktop.DBus.Properties")
    return adapter.Get("org.bluez.Adapter1", "Address")


def is_bt_available(hci_number=0):
    """If the bluez object is available it means that there is a working Bluetooth"""
    bus = dbus.SystemBus()
    try:
        dbus.Interface(bus.get_object("org.bluez", "/org/bluez/hci%i" % hci_number),
                             "org.freedesktop.DBus.Properties")
        return True
    except dbus.exceptions.DBusException as e:
        log.debug("Bluetooth is not available: %s", e)
        return False
