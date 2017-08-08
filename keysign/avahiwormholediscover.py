import logging

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue
from wormhole.errors import LonelyError

from .bluetoothreceive import BluetoothReceive
from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import is_code_complete, parse_barcode

log = logging.getLogger(__name__)


class AvahiWormholeDiscover:
    def __init__(self, userdata, discovery, app_id=None):
        # if the userdata is a qr code we extract the wormhole and bluetooth codes
        self.worm_code = parse_barcode(userdata).get("WORM", [None])[0]
        self.bt_code = parse_barcode(userdata).get("BT", [None])[0]
        # check if userdata is a valid wormhole code
        if is_code_complete(userdata):
            self.worm_code = userdata
        self.userdata = userdata
        self.app_id = app_id
        if discovery:
            self.discovery = discovery
        else:
            self.discovery = AvahiKeysignDiscoveryWithMac()
        self.worm = None
        self.bt = None
        self.stopped = False

    @inlineCallbacks
    def start(self):
        # First we try Avahi, if it fails we fallback to Bluetooth and lastly
        # Wormhole, because the receiver may be able to use only one of them
        log.info("Trying to use this code with Avahi: %s", self.userdata)
        key_data = yield threads.deferToThread(self.discovery.find_key, self.userdata)
        if key_data and not self.stopped:
            success = True
            message = ""
            returnValue((key_data, success, message))
        if self.bt_code and not self.stopped:
            # We try Bluetooth, if we have it
            log.info("Trying to connect to %s with Bluetooth", self.bt_code)
            self.bt = BluetoothReceive()
            msg_tuple = yield self.bt.find_key(self.bt_code)
            key_data, success, message = msg_tuple
            if key_data:
                # If we found the key, otherwise we continue with wormhole
                returnValue((key_data, success, message))
        elif self.worm_code and not self.stopped:
            # We try the wormhole code, if we have it
            log.info("Trying to use this code with Wormhole: %s", self.worm_code)
            self.worm = WormholeReceive(self.worm_code)
            msg_tuple = yield self.worm.start()
            key_data, success, message = msg_tuple
            returnValue((key_data, success, message))
        else:
            key_data = None
            success = False
            message = LonelyError
            returnValue((key_data, success, message))

    def stop(self):
        self.stopped = True
        # WormholeReceive needs to be stopped because right now after the 'start()'
        # it continues trying to connect until it does or we stop it.
        if self.worm:
            self.worm.stop()
        if self.bt:
            self.bt.stop()
