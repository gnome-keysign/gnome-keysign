import logging

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue

from .bluetoothreceive import BluetoothReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import parse_barcode

log = logging.getLogger(__name__)


class Discover:
    def __init__(self, userdata, discovery):
        # if the userdata is a qr code we extract the bluetooth code
        self.bt_code = parse_barcode(userdata).get("BT", [None])[0]
        self.userdata = userdata
        if discovery:
            self.discovery = discovery
        else:
            self.discovery = AvahiKeysignDiscoveryWithMac()
        self.bt = None
        self.stopped = False

    @inlineCallbacks
    def start(self):
        # First we try Avahi, if it fails we fallback to Bluetooth because
        # the receiver may be able to use only one of them
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
                # If we found the key
                returnValue((key_data, success, message))
        else:
            key_data = None
            success = False
            message = ""
            returnValue((key_data, success, message))

    def stop(self):
        self.stopped = True
        if self.bt:
            self.bt.stop()
