#!/usr/bin/env python
#    Copyright 2017 Ludovico de Nittis <aasonykk+gnome@gmail.com>
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

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue
from wormhole.errors import LonelyError

from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import is_code_complete, parse_barcode

log = logging.getLogger(__name__)


class AvahiWormholeDiscover:
    def __init__(self, userdata, discovery, app_id=None):
        # if the userdata is a qr code we extract the wormhole code
        self.worm_code = parse_barcode(userdata).get("WORM", [None])[0]
        # check if userdata is a valid wormhole code
        if is_code_complete(userdata):
            self.worm_code = userdata
        self.userdata = userdata
        self.app_id = app_id
        if discovery:
            self.discovery = discovery
        else:
            self.discovery = AvahiKeysignDiscoveryWithMac()
        self.worm = None
        self.stopped = False

    @inlineCallbacks
    def start(self):
        # First we try Avahi, and if it fails we fallback to Wormhole
        # because the receiver may not be able to use Internet, so it is
        # safer to try both
        log.info("Trying to use this code with Avahi: %s", self.userdata)
        key_data = yield threads.deferToThread(self.discovery.find_key, self.userdata)
        if key_data and not self.stopped:
            success = True
            message = ""
            returnValue((key_data, success, message))
        elif self.worm_code and not self.stopped:
            # We try the wormhole code, if we have it
            log.info("Trying to use this code with Wormhole: %s", self.worm_code)
            self.worm = WormholeReceive(self.worm_code)
            msg_tuple = yield self.worm.start()
            key_data, success, message = msg_tuple
            returnValue((key_data, success, message))
        else:
            key_data = None
            success = False
            message = LonelyError
            returnValue((key_data, success, message))

    def stop(self):
        self.stopped = True
        # WormholeReceive needs to be stopped because right now after the 'start()'
        # it continues trying to connect until it does or we stop it.
        if self.worm:
            self.worm.stop()
