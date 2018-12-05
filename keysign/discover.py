import logging

from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue
from wormhole.errors import LonelyError

from .wormholereceive import WormholeReceive
from .avahidiscovery import AvahiKeysignDiscoveryWithMac
from .util import is_code_complete, parse_barcode
try:
    from .bluetoothreceive import BluetoothReceive
except ImportError:
    BluetoothReceive = None

log = logging.getLogger(__name__)


class Discover:
    def __init__(self, userdata, discovery, app_id=None):
        # if the userdata is a qr code we extract the wormhole and bluetooth codes
        self.worm_code = parse_barcode(userdata).get("WORM", [None])[0]
        self.bt_code = parse_barcode(userdata).get("BT", [None])[0]
        self.bt_port = parse_barcode(userdata).get("PT", [None])[0]
        if self.bt_port:
            self.bt_port = int(self.bt_port)
        self.mac = parse_barcode(userdata).get("MAC", [None])[0]
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
        success = False
        message = LonelyError
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

        if key_data:
            success = True
            message = ""
        else:
            if self.bt_code and BluetoothReceive and not self.stopped:
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
                    log.exception("Pybluez may be missing.")
                else:
                    key_data, success, message = msg_tuple
                    if key_data:
                        # If we found the key
                        log.debug("Found the key via bluetooth: %r", key_data[:32])

            if not key_data and self.worm_code and not self.stopped:
                # We try the wormhole code, if we have it
                log.info("Trying to use this code with Wormhole: %s", self.worm_code)
                self.worm = WormholeReceive(self.worm_code, self.mac)
                msg_tuple = yield self.worm.start()
                key_data, success, message = msg_tuple

        if self.stopped:
            key_data = None
            success = False
            # We use the LonelyError in a similar way as Wormhole does.
            # That is to indicate that the connection as been stopped before a transfer.
            message = LonelyError

        log.debug("Returning key: %r, success: %r, message: %r",
                  key_data, success, message)
        returnValue((key_data, success, message))

    def stop(self):
        self.stopped = True
        # WormholeReceive needs to be stopped because right now after the 'start()'
        # it continues trying to connect until it does or we stop it.
        if self.worm:
            self.worm.stop()
        if self.bt:
            self.bt.stop()
