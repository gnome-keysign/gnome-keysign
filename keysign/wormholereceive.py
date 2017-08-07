from __future__ import unicode_literals
import logging

from twisted.internet.defer import inlineCallbacks, returnValue
from wormhole.cli.public_relay import RENDEZVOUS_RELAY
from wormhole.errors import WrongPasswordError, LonelyError, TransferError
import wormhole
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
if __name__ == "__main__":
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
from twisted.internet import reactor

from .util import decode_message, encode_message, parse_barcode

log = logging.getLogger(__name__)


class WormholeReceive:
    def __init__(self, code, app_id=None):
        self.w = None
        # Check if the given code is a barcode or directly the wormhole code
        parsed = parse_barcode(code).get("WORM", [None])[0]
        if parsed:
            self.code = parsed
        else:
            self.code = code
        if app_id:
            self.app_id = app_id
        else:
            # the following id is needed for interoperability with wormhole cli
            self.app_id = "lothar.com/wormhole/text-or-file-xfer"

    @inlineCallbacks
    def start(self):
        log.info("Wormhole: Trying to receive a message with code: %s", self.code)

        self.stop()
        self.w = wormhole.create(self.app_id, RENDEZVOUS_RELAY, reactor)
        # The following mod is required for Python 2 support
        self.w.set_code("%s" % str(self.code))

        try:
            message = yield self.w.get_message()
            m = decode_message(message)
            key_data = None
            offer = m.get("offer", None)
            if offer:
                key_data = offer.get("message", None)
            if key_data:
                log.info("Message received: %s", key_data)
                success = True
                message = ""
                # send a reply with a message ack, this also ensures wormhole cli interoperability
                reply = {"answer": {"message_ack": "ok"}}
                reply_encoded = encode_message(reply)
                self.w.send_message(reply_encoded)
                returnValue((key_data.encode("utf-8"), success, message))
            else:
                log.info("Unrecognized message: %s", m)
                success = False
                error_message = "Unrecognized message"
                reply = {"error": error_message}
                reply_encoded = encode_message(reply)
                self.w.send_message(reply_encoded)
                returnValue((key_data, success, TransferError))
        except WrongPasswordError as wpe:
            log.info("A wrong password has been used")
            self._handle_failure(wpe)
        except LonelyError as le:
            log.info("Closed the connection before we found anyone")
            self._handle_failure(le)

    @inlineCallbacks
    def stop(self):
        if self.w:
            try:
                yield self.w.close()
            except Exception as e:
                print(e)

    @staticmethod
    def _handle_failure(error):
        success = False
        key_data = None
        returnValue((key_data, success, type(error)))


def main(args):
    log.debug('Running main with args: %s', args)
    if not args:
        raise ValueError("You must provide an argument with the wormhole code")

    @inlineCallbacks
    def receive_key(w_code):
        receive = WormholeReceive(w_code)
        msg_tuple = yield receive.start()
        key_data, success, message = msg_tuple
        if success:
            print("key received:\n")
            print(key_data.decode("utf-8"))
        else:
            print(message)
        # Workaround for the send_message reply (until we find a better solution).
        # If we simply call reactor.stop() the send_message() will never be
        # completed. I think this happens because we are always in the reactor
        # thread and send_message is waiting for a context switch.
        reactor.callLater(1, reactor.stop)

    print("Trying to download the key, please wait")
    code = args[0]
    receive_key(code)
    reactor.run()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
