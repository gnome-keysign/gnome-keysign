import logging
from bluetooth import BluetoothSocket, RFCOMM, PORT_ANY
import dbus
import select
import socket
import sys

if __name__ == "__main__":
    import gi
    gi.require_version('Gtk', '3.0')
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
    from twisted.internet import reactor
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue

if sys.version < '3':
    input = raw_input

if __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    import keysign
    __package__ = str('keysign')

from .gpgmh import get_public_key_data, get_usable_keys
from .i18n import _
from .util import get_local_bt_address, mac_generate

log = logging.getLogger(__name__)


class BluetoothOffer:
    def __init__(self, key, port=3, size=1024):
        self.key = key
        self.port = port
        self.size = size
        self.server_socket = None
        self.message_def = None
        self.stopped = False
        self.code = None

    @inlineCallbacks
    def start(self):
        self.stopped = False
        message = "Back"
        success = False
        try:
            while not self.stopped and not success:
                # server_socket.accept() is not stoppable. So with select we can call accept()
                # only when we are sure that there is already a waiting connection
                ready_to_read, ready_to_write, in_error = yield threads.deferToThread(
                    select.select, [self.server_socket], [], [], 0.5)
                if ready_to_read:
                    # We are sure that a connection is available, so we can call
                    # accept() without deferring it to a thread
                    client_socket, address = self.server_socket.accept()
                    key_data = get_public_key_data(self.key.fingerprint)
                    kd_decoded = key_data.decode('utf-8')
                    yield threads.deferToThread(client_socket.sendall, kd_decoded)
                    log.info("Key has been sent")
                    client_socket.shutdown(socket.SHUT_RDWR)
                    client_socket.close()
                    success = True
                    message = None
        except Exception as e:
            log.error("An error occurred: %s" % e)
            success = False
            message = e

        returnValue((success, message))

    def allocate_code(self):
        try:
            code = get_local_bt_address().upper()
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() == "org.freedesktop.systemd1.NoSuchUnit":
                log.info("No Bluetooth devices found, probably the bluetooth service is not running")
            elif e.get_dbus_name() == "org.freedesktop.DBus.Error.UnknownObject":
                log.info("No Bluetooth devices available")
            else:
                log.error("An unexpected error occurred %s", e.get_dbus_name())
            self.code = None
            return None
        if self.server_socket is None:
            self.server_socket = BluetoothSocket(RFCOMM)
            # We create a bind with the Bluetooth address we have in the system
            self.server_socket.bind((code, PORT_ANY))
            # Number of unaccepted connections that the system will allow before refusing new connections
            backlog = 1
            self.server_socket.listen(backlog)
            log.info("sockname: %r", self.server_socket.getsockname())
        port = self.server_socket.getsockname()[1]
        log.info("BT Code: %s %s", code, port)
        bt_data = "BT={0};PT={1}".format(code, port)
        return bt_data

    def stop(self):
        log.debug("Stopping bt receive")
        self.stopped = True
        if self.server_socket:
            self.server_socket.shutdown(socket.SHUT_RDWR)
            self.server_socket.close()
            self.server_socket = None


def main(args):
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    def cancel():
        input("Press Enter to cancel")
        offer.stop()
        reactor.callFromThread(reactor.stop)

    def _received(result):
        success, error_msg = result
        if success:
            print(_("\nKey successfully sent"))
        else:
            print(_("\nAn error occurred: {}").format(error_msg))
        # We are still waiting for the user to press Enter
        print(_("Press Enter to exit"))

    key = get_usable_keys(pattern=args[0])[0]
    file_key_data = get_public_key_data(key.fingerprint)
    hmac = mac_generate(key.fingerprint.encode('ascii'), file_key_data)
    offer = BluetoothOffer(key)
    data = offer.allocate_code()
    if data:
        # getting the code from "BT=code;...."
        code = data.split("=", 1)[1]
        code = code.split(";", 1)[0]
        port = data.rsplit("=", 1)[1]
        offer.start().addCallback(_received)
        print(_("Offering key: {}").format(key))
        print(_("Discovery info: {}").format(code))
        print(_("HMAC: {}").format(hmac))
        print(_("Port: {}").format(port))
        # Wait for the user without blocking everything
        reactor.callInThread(cancel)
        reactor.run()
    else:
        print(_("Bluetooth not available"))

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1:])
