from twisted.internet import reactor
from wormhole.cli.public_relay import RENDEZVOUS_RELAY
import wormhole
import logging

from .util import decode_message, encode_message, parse_barcode
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

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
            self.app_id = u"lothar.com/wormhole/text-or-file-xfer"

    def start(self):
        log.info("Wormhole: Trying to receive a message with code: {}".format(self.code))

        self.stop()
        self.w = wormhole.create(self.app_id, RENDEZVOUS_RELAY, reactor)
        # The following mod is required for Python 2 support
        self.w.set_code("%s" % str(self.code))

        # callback when we receive a message
        self.w.get_message().addCallback(self._received)

    def _received(self, message):
        m = decode_message(message)
        key_data = None
        offer = m.get("offer", None)
        if offer:
            key_data = offer.get("message", None)
        if key_data:
            log.info("Message received: {}".format(key_data))
            if self.callback:
                GLib.idle_add(self.callback, key_data.encode("utf-8"))
            # send a reply with a message ack, this also ensures wormhole cli interoperability
            reply = {"answer": {"message_ack": "ok"}}
            reply_encoded = encode_message(reply)
            return self.w.send_message(reply_encoded)
        else:
            log.info("Unknown message received")
            reply = {"error": "Unrecognized message: {}".format(m)}
            reply_encoded = encode_message(reply)
            return self.w.send_message(reply_encoded)
            # TODO display the error to the user

    def stop(self, callback=None):
        if self.w:
            self.w.close()

        if callback:
            GLib.idle_add(callback)
