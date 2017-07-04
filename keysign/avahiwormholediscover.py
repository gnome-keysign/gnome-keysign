import logging

from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import is_code_complete, parse_barcode

log = logging.getLogger(__name__)


class AvahiWormholeDiscover:
    def __init__(self, userdata, discovery=None, callback=None, app_id=None):
        # Check if the given code is a barcode
        parsed = parse_barcode(userdata).get("WORM", [None])[0]
        if parsed:
            # In this way if we have a barcode we directly only use the wormhole code.
            # Maybe we should let the users choose the preferred method or try with one
            # by default and fallback to the other if it fails
            self.userdata = parsed
        else:
            self.userdata = userdata
        self.callback = callback
        self.app_id = app_id
        if discovery:
            self.discovery = discovery
        else:
            self.discovery = AvahiKeysignDiscoveryWithMac()
        self.worm = None

    def start(self):
        # if the code may be a valid wormhole one we try to use wormhole.
        # Otherwise we use avahi
        if is_code_complete(self.userdata):
            log.info("%s may be a good wormhole code", self.userdata)
            self.worm = WormholeReceive(self.userdata, self.callback)
            self.worm.start()
        else:
            log.info("%s is not a valid wormhole code", self.userdata)
            keydata = self.discovery.find_key(self.userdata)
            if keydata and self.callback:
                self.callback(keydata, True)

    def stop(self):
        """ WormholeReceive need to be stopped because right now after the 'start()'
        it continues trying to connect until it does or we stop it."""
        if self.worm:
            self.worm.stop()
