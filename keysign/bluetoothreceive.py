import logging
from bluetooth import *
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue

from .util import strip_fingerprint


log = logging.getLogger(__name__)


class BluetoothReceive:
    def __init__(self, port=3, size=1024):
        self.port = port
        self.size = size
        self.client_socket = None

    @inlineCallbacks
    def find_key(self, code):
        mac = strip_fingerprint(code)
        self.client_socket = BluetoothSocket(RFCOMM)
        try:
            yield threads.deferToThread(self.client_socket.connect, (mac, self.port))
            message = b""
            while len(message) < 35 or message[-35:] != b"-----END PGP PUBLIC KEY BLOCK-----\n":
                part_message = yield threads.deferToThread(self.client_socket.recv, self.size)
                message += part_message
        except Exception as e:  # TODO better handling
            log.error("An error occurred connecting or receiving: %s" % e)
            key_data = None
            success = False
            returnValue((key_data, success, e))

        if self.client_socket:
            self.client_socket.close()

        success = True
        returnValue((message.decode("utf-8"), success, None))

    def stop(self):
        if self.client_socket:
            self.client_socket.close()
