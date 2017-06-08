from .wormholeoffer import WormholeOffer
from .avahioffer import AvahiHTTPOffer
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


class AvahiWormholeOffer:
    def __init__(self, key, callback_receive=None, callback_code=None, app_id=None, code=None):
        self.avahi_offer = AvahiHTTPOffer(key)
        self.worm_offer = WormholeOffer(key, callback_receive, self._callback_code, app_id, code)
        self.callback_code = callback_code
        self.avahi_discovery_data = None

    def start(self):
        self.avahi_discovery_data = self.avahi_offer.start()
        self.worm_offer.start()

    def _callback_code(self, wormhole_code, wormhole_data):
        discovery_data = self.avahi_discovery_data + wormhole_data.upper()
        print(wormhole_data)
        wormhole_data.upper()
        print(wormhole_data.upper())
        self.callback_code(wormhole_code, discovery_data)

    def stop(self):
        self.avahi_offer.stop()
        self.worm_offer.stop()
