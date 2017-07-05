import logging

from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import is_code_complete, parse_barcode

log = logging.getLogger(__name__)


class AvahiWormholeDiscover:
    def __init__(self, userdata, discovery, callback, app_id=None):
        # if the userdata is a qr code we extract the wormhole code
        self.worm_code = parse_barcode(userdata).get("WORM", [None])[0]
        # check if userdata is a valid wormhole code
        if is_code_complete(userdata):
            self.worm_code = userdata
        self.userdata = userdata
        self.callback = callback
        self.app_id = app_id
        if discovery:
            self.discovery = discovery
        else:
            self.discovery = AvahiKeysignDiscoveryWithMac()
        self.worm = None

    def start(self):
        # First we try Avahi, and if it fails we fallback to Wormhole
        # because the receiver may not be able to use Internet, so it is
        # safer to try both
        log.info("Trying to use this code with Avahi: %s", self.userdata)
        keydata = self.discovery.find_key(self.userdata)
        if keydata:
            self.callback(keydata, True)
        elif self.worm_code:
            # We try the wormhole code, if we have it
            log.info("Trying to use this code with Wormhole: %s", self.worm_code)
            self.worm = WormholeReceive(self.worm_code, self.callback)
            self.worm.start()

    def stop(self):
        """ WormholeReceive need to be stopped because right now after the 'start()'
        it continues trying to connect until it does or we stop it."""
        if self.worm:
            self.worm.stop()
