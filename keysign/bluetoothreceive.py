import logging
import select
from bluetooth import BluetoothSocket, BluetoothError, RFCOMM
import socket

if __name__ == "__main__":
    import gi
    gi.require_version('Gtk', '3.0')
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
    from twisted.internet import reactor
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue

if __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')

from .gpgmeh import fingerprint_from_keydata
from .i18n import _
from .util import mac_verify

log = logging.getLogger(__name__)


class BluetoothReceive:
    def __init__(self, port=3, size=1024):
        self.port = port
        self.size = size
        self.client_socket = None
        self.stopped = False

    @inlineCallbacks
    def find_key(self, bt_mac, mac):
        self.client_socket = BluetoothSocket(RFCOMM)
        message = b""
        try:
            self.client_socket.setblocking(False)
            try:
                log.info("Trying to connect to %s port %s", bt_mac, self.port)
                self.client_socket.connect((bt_mac, self.port))
            except BluetoothError as be:
                if be.args[0] == "(115, 'Operation now in progress')":
                    pass
                else:
                    raise be
            success = False
            while not self.stopped and not success:
                r, w, e = yield threads.deferToThread(select.select, [self.client_socket], [], [], 0.5)
                if r:
                    log.info("Connection established")
                    self.client_socket.setblocking(True)
                    success = True
                    # try to receive until the sender closes the connection
                    try:
                        while True:
                            part_message = self.client_socket.recv(self.size)
                            log.debug("Read %d bytes: %r", len(part_message), part_message)
                            message += part_message
                    except BluetoothError as be:
                        if be.args[0] == "(104, 'Connection reset by peer')":
                            log.info("Bluetooth connection closed, let's check if we downloaded the key")
                        else:
                            raise be
            mac_key = fingerprint_from_keydata(message)
            verified = None
            if mac:
                verified = mac_verify(mac_key.encode('ascii'), message, mac)
            if verified:
                success = True
            else:
                log.info("MAC validation failed: %r", verified)
                success = False
                message = b""
        except BluetoothError as be:
            if be.args[0] == "(16, 'Device or resource busy')":
                log.info("Probably has been provided a partial bt mac")
            elif be.args[0] == "(111, 'Connection refused')":
                log.info("The sender refused our connection attempt")
            elif be.args[0] == "(112, 'Host is down')":
                log.info("The sender's Bluetooth is not available")
            elif be.args[0] == "(113, 'No route to host')":
                log.info("An error occurred with Bluetooth, if present probably the device is not powered")
            else:
                log.info("An unknown bt error occurred: %s" % be.args[0])
            key_data = None
            success = False
            returnValue((key_data, success, be))
        except Exception as e:
            log.error("An error occurred connecting or receiving: %s" % e)
            key_data = None
            success = False
            returnValue((key_data, success, e))

        if self.client_socket:
            self.client_socket.close()
        returnValue((message.decode("utf-8"), success, None))

    def stop(self):
        self.stopped = True
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except BluetoothError as be:
                if be.args[0] == "(9, 'Bad file descriptor')":
                    log.info("The old Bluetooth connection was already closed")
                else:
                    log.exception("An unknown bt error occurred")


def main(args):
    log.debug('Running main with args: %s', args)
    if not len(args) == 3:
        raise ValueError("You must provide three arguments: bluetooth code, hmac and port")

    def _received(result):
        key_data, success, error_message = result
        if success:
            print(key_data)
        else:
            print(error_message)

        reactor.callFromThread(reactor.stop)

    print(_("Trying to download the key, please wait"))
    bt_mac = args[0]
    hmac = args[1]
    port = int(args[2])
    receive = BluetoothReceive(port)
    d = receive.find_key(bt_mac, hmac)
    d.addCallback(_received)
    reactor.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    main(sys.argv[1:])
