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
        
        try:
            key_data = yield threads.deferToThread(self.discovery.find_key, self.userdata)
        except ValueError as e:
            key_data = None
            success = False
            message = "Error downloading key, maybe it has been altered in transit"
            log.warning(message, exc_info=e)
        else:
            # Actually.. key_data can very well be None as an indication of failure. We might change that API to throw.
            log.debug("We may have found a key: %r", key_data)

        if self.stopped:
            key_data = None
            success = False
            message = ""
        else:
            if key_data:
                success = True
                message = ""
            elif self.bt_code:
                # We try Bluetooth, if we have it
                log.info("Trying to connect to %s with Bluetooth", self.bt_code)
                # We try to see if Bluetooth was imported,
                # else we log an event of missing Pybluez.
                try:
                    self.bt = BluetoothReceive(self.bt_port)
                    msg_tuple = yield self.bt.find_key(self.bt_code, self.mac)
                except TypeError as e:
                    key_data = None
                    success = False
                    message = ""
                    log.exception("Pybluez may be missing.")
                else:
                    key_data, success, message = msg_tuple
                    if key_data:
                        # If we found the key
                        log.debug("Found the key via bluetooth: %r", key_data[:32])
            else:
                message = ""
                success = False
                key_data = None
                log.warning("Neither key_data nor btcode. Weird")

        log.debug("Returning key: %r, succes: %r, message: %r",
            key_data, success, messages)
        returnValue((key_data, success, message))


    def stop(self):
        self.stopped = True
        if self.bt:
            self.bt.stop()
