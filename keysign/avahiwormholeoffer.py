from .wormholeoffer import WormholeOffer
from .avahioffer import AvahiHTTPOffer


class AvahiWormholeOffer:
    def __init__(self, key, callback_receive=None, callback_code=None, app_id=None, w_code=None):
        self.key = key
        self.cr = callback_receive
        self.cc = callback_code
        self.app_id = app_id
        self.w_code = w_code
        self.multiple = False  # If we want to start both avahi and wormhole
        self.w_offer = None
        self.a_offer = None
        self.a_data = None
        self.w_data = None

    def start_avahi(self):
        if not self.a_offer:
            self.a_offer = AvahiHTTPOffer(self.key, self.cr, self._callback_avahi_code)
        self.a_offer.start()

    def start_wormhole(self):
        if not self.w_offer:
            self.w_offer = WormholeOffer(self.key, self.app_id)
        self.w_offer.start()

    def start(self):
        self.multiple = True
        self.start_avahi()
        self.start_wormhole()

    def _callback_avahi_code(self, a_code, a_data):
        self.a_data = a_data
        # If we only want avahi
        if not self.multiple:
            self.cc(a_code, a_data)
        # if we also want wormhole, we check if it is already available
        elif self.w_data:
            discovery_data = a_data + ";" + self.w_data
            # As design when we start both we show only the wormhole code
            self.cc(self.w_code, discovery_data)

    def _callback_worm_code(self, w_code, w_data):
        self.w_code = w_code
        self.w_data = w_data
        # If we only want wormhole
        if not self.multiple:
            self.cc(w_code, w_data)
        # if we also want avahi, we check if it is already available
        elif self.a_data:
            discovery_data = self.a_data + ";" + w_data
            # As design when we start both we show only the wormhole code
            self.cc(self.w_code, discovery_data)

    def stop_avahi(self):
        self.a_data = None
        if self.a_offer:
            self.a_offer.stop()
            # We need to deallocate the avahi object or the used port will never be released
            self.a_offer = None

    def stop_wormhole(self):
        self.w_data = None
        if self.w_offer:
            self.w_offer.stop()
            self.w_offer = None

    def stop(self):
        self.multiple = False
        self.stop_avahi()
        self.stop_wormhole()
