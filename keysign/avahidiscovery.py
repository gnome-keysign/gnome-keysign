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
import os
import sys

from requests.exceptions import ConnectionError

from gi.repository import GObject, GLib


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


from .util import strip_fingerprint, download_key_http, parse_barcode

try:
    from .gpgmeh import fingerprint_from_keydata
except ImportError:
    # FIXME: Remove this conditional
    from .gpgmeh import fingerprint_for_key as fingerprint_from_keydata

from .network.AvahiBrowser import AvahiBrowser
from .util import mac_verify

log = logging.getLogger(__name__)

class AvahiKeysignDiscovery(GObject.GObject):
    "A client discovery using Avahi"

    __gsignals__ = {
        # Gets emitted whenever a new server has been found or has been removed.
        # Is also emitted shortly after an object has been created.
        str("list-changed"): (GObject.SignalFlags.RUN_LAST, None, (int,)),
    }

    def __init__(self, *args, **kwargs):
        super(AvahiKeysignDiscovery, self).__init__(*args, **kwargs)
        self.log = logging.getLogger(__name__)
        # We should probably try to put this constant in a more central place
        avahi_service_type = '_gnome-keysign._tcp'
        self.avahi_browser = AvahiBrowser(service=avahi_service_type)
        self.avahi_browser.connect('new_service', self.on_new_service)
        self.avahi_browser.connect('remove_service', self.on_remove_service)
        self.discovered_services = []
        # It seems we cannot emit directly...
        GLib.idle_add(lambda: self.emit("list-changed",
            len(self.discovered_services)))

    def on_new_service(self, browser, name, address, port, txt_dict):
        published_fpr = txt_dict.get('fingerprint', None)
        self.log.info("discovered something: %s %s:%i:%s",
                      name, address, port, published_fpr)
        if not address.startswith('fe80::'):
            # We intend to ignore IPv6 link local addresses, because it seems
            # that you cannot just connect to that address without also
            # knowing which NIC the address belongs to.
            # http://serverfault.com/a/794967
            # FIXME: Use something more sane like attr.s instead of the tuple
            self.discovered_services += ((name, address, port, published_fpr), )
            self.emit("list-changed", len(self.discovered_services))

    def on_remove_service(self, browser, service_type, name):
        '''Handler for the on_remove signal from AvahiBrowser

        Removes a service from the internal list by calling
        remove_discovered_service.
        '''
        self.log.info("Received a remove signal, let's check; %s:%s",
                      service_type, name)
        self.remove_discovered_service(name)

    def remove_discovered_service(self, name):
        '''Removes server-side clients from discovered_services list
        when the server name with fpr is a match.'''
        for client in self.discovered_services:
            if client[0] == name:
                self.discovered_services.remove(client)
                self.emit("list-changed", len(self.discovered_services))
        self.log.info("Clients currently in list '%s'",
                      self.discovered_services)

    def find_key(self, userdata):
        "Returns the key if it thinks it found one..."
        self.log.info("Trying to find key with %r", userdata)
        parsed = parse_barcode(userdata)
        cleaned = strip_fingerprint(parsed["fingerprint"])
        downloaded_key = None
        # FIXME: Replace with attr.ib
        for (name, address, port, fpr) in self.discovered_services:
            if cleaned == fpr:
                # This is blocking :-/
                try:
                    downloaded_key = download_key_http(address, port)
                    if fingerprint_from_keydata(downloaded_key) != cleaned:
                        continue
                except ConnectionError:
                    self.log.exception("Error downloading from %r:%r",
                                  address, port)
        return downloaded_key

class AvahiKeysignDiscoveryWithMac(AvahiKeysignDiscovery):
    def find_key(self, userdata):
        "Returns the key if it thinks it found one which also matched the MAC"
        key = super(AvahiKeysignDiscoveryWithMac, self).find_key(userdata)
        if key:
            # For now, we cannot assume that a MAC exists, simply because
            # currently the MAC is only transferred via the barcode.
            # The user, however, might as well enter the fingerprint
            # manually.  Unless we stop allowing that, we won't have a MAC.
            mac = parse_barcode(userdata).get("MAC", [None])[0]
            if mac is None:
                # This is the ugly shortcut which exists for legacy reasons
                verified_key = key
            else:
                mac_key = fingerprint_from_keydata(key)
                verified = mac_verify(mac_key.encode('ascii'), key, mac)
                if verified:
                    verified_key = key
                else:
                    self.log.info("MAC validation failed: %r", verified)
                    verified_key = None
        else:
            verified_key = None

        return verified_key

def main(args):
    log = logging.getLogger(__name__)
    log.debug('Running main with args: %s', args)
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    loop = GObject.MainLoop()

    arg = args[0]
    # FIXME: Enable parameter
    timeout = 5
    GObject.timeout_add_seconds(timeout, lambda: loop.quit())

    discover = AvahiKeysignDiscovery()
    # We quickly attach the found to the object to maintain state
    discover.found_key = None
    def find_key():
        keydata = discover.find_key(arg)
        if keydata:
            log.info("Found %d key bytes", len(keydata))
            discover.found_key = keydata
            print (keydata)
            loop.quit()
        return not keydata

    discover.avahi_browser.connect('new_service', lambda *args: find_key())
    # Instead of using this implementation detail for getting the notification,
    # it would be possible to repeatedly call find_key.
    # GObject.timeout_add(25, lambda: find_key() and False)
    # GObject.timeout_add(500, find_key)
    loop.run()
    if not discover.found_key:
        log.error("No Key found for %r!!1", arg)

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv[1:]))
