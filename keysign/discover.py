import logging

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue

from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import parse_barcode
try:
    from .bluetoothreceive import BluetoothReceive
except ImportError:
    BluetoothReceive = None

log = logging.getLogger(__name__)


class Discover:
    def __init__(self, userdata, discovery):
        # if the userdata is a qr code we extract the bluetooth code
        self.bt_code = parse_barcode(userdata).get("BT", [None])[0]
        self.bt_port = parse_barcode(userdata).get("PT", [None])[0]
        if self.bt_port:
            self.bt_port = int(self.bt_port)
        self.mac = parse_barcode(userdata).get("MAC", [None])[0]
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
            try:
                if self.bt is not None:
                   self.bt = BluetoothReceive(self.bt_port)
             except ImportError:
                print("You are probably missing pybuez ")
            msg_tuple = yield self.bt.find_key(self.bt_code, self.mac)
            key_data, success, message = msg_tuple
            if key_data:
                # If we found the key
                returnValue((key_data, success, message))

        key_data = None
        success = False
        message = ""
        returnValue((key_data, success, message))

    def stop(self):
        self.stopped = True
        if self.bt:
            self.bt.stop()
