from twisted.internet import reactor
from wormhole.cli.public_relay import RENDEZVOUS_RELAY
import wormhole
import logging
import os
from builtins import input
from .util import encode_message
from .gpgmh import get_usable_keys, get_public_key_data
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

if __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    __package__ = str('keysign')


log = logging.getLogger(__name__)


class WormholeOffer:
    def __init__(self, key, callback_receive=None, callback_code=None, app_id=None, code=None):
        self.w = None
        self.key = key
        self.callback_receive = callback_receive
        self.callback_code = callback_code
        self.code = code
        if app_id:
            self.app_id = app_id
        else:
            # the following id is needed for interoperability with wormhole cli
            self.app_id = u"lothar.com/wormhole/text-or-file-xfer"

    def start(self):
        log.info("Wormhole: Sending a message")

        self.stop()
        self.w = wormhole.create(self.app_id, RENDEZVOUS_RELAY, reactor)
        if self.code:
            self.w.set_code(self.code)
        else:
            self.w.allocate_code()

            def write_code(code_generated):
                log.info("Invitation Code: {}".format(code_generated))
                wormhole_data = "+WORM:{0}".format(code_generated)
                GLib.idle_add(self.callback_code, code_generated, wormhole_data)

            self.w.get_code().addCallback(write_code)

        key_data = get_public_key_data(self.key.fingerprint)
        kd_decoded = key_data.decode('utf-8')
        # The message needs to be encoded as a json with "message" and "offer" for ensures
        # wormhole cli interoperability
        offer = {"message": kd_decoded}
        data = {"offer": offer}
        m = encode_message(data)
        self.w.send_message(m)

        # wait for reply
        def received(msg):
            log.info("Got data, %d bytes" % len(msg))
            GLib.idle_add(self.callback_receive, key_data, self.code, True)
            self.w.close()

        self.w.get_message().addCallback(received)

    def stop(self):
        if self.w is not None:
            self.w.close()


def main(args):
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    def code_generated(code):
        print("Discovery info: {}".format(code))
        input("Press Enter to stop")
        offer.stop()

    key = get_usable_keys(pattern=args[0])[0]
    offer = WormholeOffer(key, callback_code=code_generated)
    offer.start()
    print("Offering key: {}".format(key))

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
