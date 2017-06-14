import logging
from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import is_code_complete


log = logging.getLogger(__name__)


class AvahiWormholeDiscover:
    def __init__(self, userdata, callback=None, app_id=None):
        self.userdata = userdata
        self.callback = callback
        self.app_id = app_id
        self.discovery = AvahiKeysignDiscoveryWithMac()
        self.worm = None

    def start(self):
        # if the code may be a valid wormhole one we try to use wormhole.
        # Otherwise we use avahi
        if is_code_complete(self.userdata):
            log.info("{} may be a good wormhole code".format(self.userdata))
            self.worm = WormholeReceive(self.userdata, self.callback)
            self.worm.start()
        else:
            log.info("{} is not a valid wormhole code".format(self.userdata))
            keydata = self.discovery.find_key(self.userdata)
            if keydata and self.callback:
                self.callback(keydata)

    def stop(self):
        """ WormholeReceive need to be stopped because right now after the 'start()'
        it continues trying to connect until it does or we stop it."""
        self.worm.stop()
