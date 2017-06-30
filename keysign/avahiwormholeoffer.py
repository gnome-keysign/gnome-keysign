from .util import format_fingerprint
from .wormholeoffer import WormholeOffer
from .avahioffer import AvahiHTTPOffer


class AvahiWormholeOffer:
    def __init__(self, key, callback_receive=None, callback_code=None, app_id=None, code=None):
        self.key = key
        self.worm_offer = WormholeOffer(key, callback_receive, self._callback_worm_code, app_id, code)
        self.callback_code = callback_code
        self.avahi_offer = None
        self.avahi_discovery_data = ""

    def start_avahi(self):
        # If avahi is already running we simply call the callback_code
        if not self.avahi_offer:
            self.avahi_offer = AvahiHTTPOffer(self.key)
            self.avahi_discovery_data = self.avahi_offer.start()
        self._callback_code(format_fingerprint(self.key.fingerprint), self.avahi_discovery_data)

    def start_wormhole(self):
        self.worm_offer.start()

    def start(self):
        self.start_avahi()
        self.start_wormhole()

    def _callback_code(self, code, data):
        self.callback_code(code, data)

    def _callback_worm_code(self, code, data):
        discovery_data = self.avahi_discovery_data + ";" + data
        self._callback_code(code, discovery_data)

    def stop_avahi(self):
        self.avahi_discovery_data = ""
        if self.avahi_offer:
            self.avahi_offer.stop()
            # We need to deallocate the avahi object or the used port will never be released
            self.avahi_offer = None

    def stop_wormhole(self):
        self.worm_offer.stop()

    def stop(self):
        self.stop_avahi()
        self.stop_wormhole()
