import logging
from bluetooth import *

if __name__ == "__main__":
    import gi
    gi.require_version('Gtk', '3.0')
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
    from twisted.internet import reactor
from twisted.internet import threads
from twisted.internet.defer import inlineCallbacks, returnValue

log = logging.getLogger(__name__)


class BluetoothReceive:
    def __init__(self, port=3, size=1024):
        self.port = port
        self.size = size
        self.client_socket = None

    @inlineCallbacks
    def find_key(self, mac):
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


def main(args):
    log.debug('Running main with args: %s', args)
    if not args:
        raise ValueError("You must provide an argument with the bluetooth code")

    def _received(result):
        key_data, success, error_message = result
        if success:
            print(key_data)
        else:
            print(error_message)

        reactor.callFromThread(reactor.stop)

    print("Trying to download the key, please wait")
    bt_mac = args[0]
    receive = BluetoothReceive()
    d = receive.find_key(bt_mac)
    d.addCallback(_received)
    reactor.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    main(sys.argv[1:])
