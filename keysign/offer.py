import logging
from twisted.internet.defer import inlineCallbacks, returnValue

from .bluetoothoffer import BluetoothOffer
from .wormholeoffer import WormholeOffer
from .avahioffer import AvahiHTTPOffer

log = logging.getLogger(__name__)


class Offer:
    def __init__(self, key, app_id=None, w_code=None):
        self.key = key
        self.app_id = app_id
        self.w_code = w_code
        self.w_offer = None
        self.a_offer = None
        self.bt_offer = None
        self.b_data = ""

    @inlineCallbacks
    def allocate_code(self, worm=True):
        self.a_offer = AvahiHTTPOffer(self.key)
        a_info = self.a_offer.start()
        code, a_data = a_info
        if worm:
            self.w_offer = WormholeOffer(self.key)
            w_info = yield self.w_offer.allocate_code()
            code, w_data = w_info
        else:
            w_data = ""
        self.bt_offer = BluetoothOffer(self.key)
        _, self.b_data = self.bt_offer.allocate_code()
        discovery_data = a_data + ";" + w_data + ";" + self.b_data
        # As design when we use both avahi and wormhole we only display
        # the wormhole code
        returnValue((code, discovery_data))

    def start(self):
        # With the current workflow avahi needs to be started
        # for allocate the code
        d = []
        if self.w_offer:
            w_d = self.w_offer.start()
            d.append(w_d)
        # If we have a Bluetooth code, so if the Bluetooth has been
        # correctly initialized
        if self.b_data == "":
            log.info("Bluetooth as been skipped")
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
