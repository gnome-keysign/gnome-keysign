from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac


class AvahiWormholeDiscover:
    def __init__(self, userdata, callback=None, app_id=None):
        self.userdata = userdata
        self.callback = callback
        self.app_id = app_id
        self.discovery = AvahiKeysignDiscoveryWithMac()
        self.worm = None

    def start(self):
        # TODO: We should discuss if avahi first is a desired behaviour
        keydata = self.discovery.find_key(self.userdata)
        if keydata:
            if self.callback:
                self.callback(keydata)
        else:
            self.worm = WormholeReceive(self.userdata, self.callback)
            self.worm.start()

    def stop(self):
        """ WormholeReceive needed to be stopped because right now after the 'start()'
        it continues trying to connect until it does or we stop it."""
        self.worm.stop()
