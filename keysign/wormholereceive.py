from twisted.internet import reactor
from wormhole.cli.public_relay import RENDEZVOUS_RELAY
import wormhole
import logging

from .util import decode_message, encode_message
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

log = logging.getLogger(__name__)


class WormholeReceive:
    def __init__(self, code, callback=None, app_id=None):
        self.w = None
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
        # TODO check if code is None
        self.w.set_code("%s" % str(self.code))

        def received(message):
            m = decode_message(message)
            key_data = m["offer"]["message"]
            log.info("Message received: {}".format(key_data))
            GLib.idle_add(self.callback, key_data.encode("utf-8"))

            # send a reply with a message ack, this also ensures wormhole cli interoperability
            reply = {"answer": {"message_ack": "ok"}}
            reply_encoded = encode_message(reply)
            return self.w.send_message(reply_encoded)

        self.w.get_message().addCallback(received)

    def stop(self, callback=None):
        if self.w is not None:
            self.w.close()

        if callback is not None:
            GLib.idle_add(callback)
