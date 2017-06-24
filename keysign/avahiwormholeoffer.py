from .util import format_fingerprint
from .wormholeoffer import WormholeOffer
from .avahioffer import AvahiHTTPOffer
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


class AvahiWormholeOffer:
    def __init__(self, key, callback_receive=None, callback_code=None, app_id=None, code=None):
        self.fingerprint = key.fingerprint
        self.avahi_offer = AvahiHTTPOffer(key)
        self.worm_offer = WormholeOffer(key, callback_receive, self._callback_code, app_id, code)
        self.callback_code = callback_code
        self.avahi_discovery_data = ""

    def start_avahi(self):
        self.avahi_discovery_data = self.avahi_offer.start()
        self._callback_code(format_fingerprint(self.fingerprint), self.avahi_discovery_data)

    def start_wormhole(self):
        self.worm_offer.start()

    def start(self):
        self.start_avahi()
        self.start_wormhole()

    def _callback_code(self, code, data):
        self.callback_code(code, data)

    def stop_avahi(self):
        self.avahi_discovery_data = ""
        if self.avahi_offer:
            self.avahi_offer.stop()
            self.avahi_offer = None

    def stop_wormhole(self):
        self.worm_offer.stop()

    def stop(self):
        self.stop_avahi()
        self.stop_wormhole()
