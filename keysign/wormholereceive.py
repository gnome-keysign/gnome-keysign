from __future__ import unicode_literals
import logging
from textwrap import dedent

from wormhole.cli.public_relay import RENDEZVOUS_RELAY
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
    def __init__(self, code, callback=None, app_id=None):
        self.w = None
        # Check if the given code is a barcode or directly the wormhole code
        parsed = parse_barcode(code).get("WORM", [None])[0]
        if parsed:
            self.code = parsed
        else:
            self.code = code

        self.callback = callback

        if app_id:
            self.app_id = app_id
        else:
            # the following id is needed for interoperability with wormhole cli
            self.app_id = "lothar.com/wormhole/text-or-file-xfer"

    def start(self):
        log.info("Wormhole: Trying to receive a message with code: %s", self.code)

        self.stop()
        self.w = wormhole.create(self.app_id, RENDEZVOUS_RELAY, reactor)
        # The following mod is required for Python 2 support
        self.w.set_code("%s" % str(self.code))

        # callback when we receive a message, here we catch the WrongPasswordError
        self.w.get_message().addCallbacks(self._received, self._handle_failure)

    def _received(self, message):
        m = decode_message(message)
        key_data = None
        offer = m.get("offer", None)
        if offer:
            key_data = offer.get("message", None)
        if key_data:
            log.info("Message received: %s", key_data)
            if self.callback:
                self.callback(key_data.encode("utf-8"))
            # send a reply with a message ack, this also ensures wormhole cli interoperability
            reply = {"answer": {"message_ack": "ok"}}
            reply_encoded = encode_message(reply)
            return self.w.send_message(reply_encoded)
        else:
            log.info("Unrecognized message: %s", m)
            error_message = "Unrecognized message"
            success = False
            if self.callback:
                self.callback(key_data, success, error_message)
            reply = {"error": error_message}
            reply_encoded = encode_message(reply)
            return self.w.send_message(reply_encoded)

    def _handle_failure(self, f):
        success = False
        key_data = None
        error_message = dedent(f.type.__doc__)
        if self.callback:
            self.callback(key_data, success, error_message)

    def stop(self, callback=None):
        if self.w:
            self.w.close()

        if callback:
            callback()


def main(args):
    log.debug('Running main with args: %s', args)
    if not args:
        raise ValueError("You must provide an argument with the wormhole code")

    def received_callback(key_data, success=True, error_message=None):
        if success:
            print(key_data)
        else:
            print(error_message)

        reactor.callFromThread(reactor.stop)

    code = args[0]
    receive = WormholeReceive(code, received_callback)
    receive.start()
    reactor.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    main(sys.argv[1:])
