import logging
from bluetooth import *
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks

from .gpgmh import get_public_key_data
from .util import get_local_bt_address


log = logging.getLogger(__name__)


class BluetoothOffer:
    def __init__(self, key, port=3, size=1024):
        self.key = key
        self.port = port
        self.size = size
        self.server_socket = None
        self.message_def = None
        self.stopped = False

    @inlineCallbacks
    def start(self):
        self.stopped = False
        message = None
        success = False
        if self.server_socket is None:
            self.server_socket = BluetoothSocket(RFCOMM)
            self.server_socket.bind(("", self.port))
            # Number of unaccepted connections that the system will allow before refusing new connections
            backlog = 1
            self.server_socket.listen(backlog)
        try:
            while not self.stopped and not success:
                # server_socket.accept() is not stoppable. So with select we can call accept()
                # only when we are sure that there is already a waiting connection
                ready_to_read, ready_to_write, in_error = yield threads.deferToThread(
                    select.select, [self.server_socket], [], [], True)
                if ready_to_read:
                    client_socket, address = yield threads.deferToThread(self.server_socket.accept)
                    key_data = get_public_key_data(self.key.fingerprint)
                    kd_decoded = key_data.decode('utf-8')
                    yield threads.deferToThread(client_socket.sendall, kd_decoded)
                    log.info("Key has been sent")
                    success = True
        except Exception as e:
            log.error("An error occurred: %s" % e)
            success = False
            message = e

        if not self.stopped:
            return success, message

    @staticmethod
    def generate_code():
        code = get_local_bt_address().upper()
        log.info("BT Code: %s", code)
        bt_data = "BT={0}".format(code)
        return code, bt_data

    def stop(self):
        self.stopped = True

    def stop_receive(self):
        # FIXME right now it seems that even after stop()
        # the used port is not released
        log.debug("Stopping bt receive")
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
