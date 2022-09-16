import logging
from twisted.internet.defer import inlineCallbacks, returnValue

from .wormholeoffer import WormholeOffer
from .avahioffer import AvahiHTTPOffer
try:
    from .bluetoothoffer import BluetoothOffer
except ImportError:
    BluetoothOffer = None

log = logging.getLogger(__name__)


class Offer:
    def __init__(self, key, app_id=None, w_code=None):
        self.key = key
        self.app_id = app_id
        self.w_code = w_code
        self.w_offer = None
        self.a_offer = None
        self.bt_offer = None
        self.b_data = None

    @inlineCallbacks
    def allocate_code(self, worm=True):
        self.a_offer = AvahiHTTPOffer(self.key)
        code, a_data = self.a_offer.allocate_code()
        discovery_data = [a_data]
        if worm:
            self.w_offer = WormholeOffer(self.key)
            w_info = yield self.w_offer.allocate_code()
            code, w_data = w_info
            if w_data:
                discovery_data.append(w_data)
        if BluetoothOffer:
            self.bt_offer = BluetoothOffer(self.key)
            self.b_data = yield self.bt_offer.allocate_code()
            if self.b_data:
                discovery_data.append(self.b_data)
        discovery_data = ";".join(discovery_data)
        # As design when we use both avahi and wormhole we only display
        # the wormhole code
        returnValue((code, discovery_data))

    def start(self):
        avahi_defers = self.a_offer.start()
        d = [avahi_defers] if avahi_defers else []
        if self.w_offer:
            w_d = self.w_offer.start()
            d.append(w_d)
        # If we have a Bluetooth code, so if the Bluetooth has been
        # correctly initialized
        if not self.b_data:
            log.info("Bluetooth has been skipped")
        else:
            bt_d = self.bt_offer.start()
            d.append(bt_d)
        return d

    def stop_avahi(self):
        if self.a_offer:
            self.a_offer.stop()
            # We need to deallocate the avahi object or the used port will never be released
            self.a_offer = None

    def stop_wormhole(self):
        if self.w_offer:
            self.w_offer.stop()
            self.w_offer = None

    def stop_bt(self):
        if self.bt_offer:
            self.bt_offer.stop()
            self.bt_offer = None

    def stop(self):
        self.stop_avahi()
        self.stop_wormhole()
        self.stop_bt()
