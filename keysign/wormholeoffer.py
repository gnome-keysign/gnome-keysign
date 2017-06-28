from __future__ import unicode_literals
from binascii import hexlify
from textwrap import dedent
from wormhole.cli.public_relay import RENDEZVOUS_RELAY
from wormhole.errors import TransferError, WrongPasswordError
import wormhole
import logging
import os
from builtins import input
from .util import encode_message, decode_message
from .gpgmh import get_usable_keys, get_public_key_data
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
if __name__ == "__main__":
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
from twisted.internet import reactor

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
            self.app_id = "lothar.com/wormhole/text-or-file-xfer"

    def start(self):
        log.info("Wormhole: Sending a message")

        self.stop()
        self.w = wormhole.create(self.app_id, RENDEZVOUS_RELAY, reactor)
        if self.code:
            self.w.set_code(self.code)
        else:
            self.w.allocate_code()
            self.w.get_code().addCallback(self._write_code)

        # With _handle_failure we catch the WrongPasswordError
        self.w.get_verifier().addCallbacks(self._verified, self._handle_failure)

        key_data = get_public_key_data(self.key.fingerprint)
        kd_decoded = key_data.decode('utf-8')
        # The message needs to be encoded as a json with "message" and "offer" for ensures
        # wormhole cli interoperability
        offer = {"message": kd_decoded}
        data = {"offer": offer}
        m = encode_message(data)
        self.w.send_message(m)

        # wait for reply
        # TODO add a timeout?
        self.w.get_message().addCallback(self._received)

    def _write_code(self, code_generated):
        log.info("Invitation Code: {}".format(code_generated))
        wormhole_data = "WORM={0}".format(code_generated)
        if self.callback_code:
            GLib.idle_add(self.callback_code, code_generated, wormhole_data)

    def _verified(self, verifier):
        # TODO maybe we can show it to the user and ask for a confirm that is the right one
        ver_ascii = hexlify(verifier).decode("ascii")
        log.info("Verified key: %s" % ver_ascii)

    def _handle_failure(self, f):
        error = dedent(f.type.__doc__)
        log.info(error)
        if self.callback_receive:
            GLib.idle_add(self.callback_receive, False, error)
        # self.w.close()

    def _received(self, msg):
        log.info("Got data, %d bytes" % len(msg))
        success, error_msg = self._check_received(msg)
        if self.callback_receive:
            GLib.idle_add(self.callback_receive, success, error_msg)
        self.w.close()

    def _check_received(self, msg):
        """If the received message has a field 'answer' that means that the transfer
        successfully completed. Otherwise something went wrong or we received an
        unexpected message."""
        msg_dict = decode_message(msg)
        if "error" in msg_dict:
            error_msg = "A remote error occurred: %s" % msg_dict["error"]
            success = False
            error = TransferError(error_msg)
            log.info(error_msg)
        elif "answer" in msg_dict:
            success = True
            error = None
        else:
            success = False
            error = "Unrecognized message %r" % (msg_dict,)
            log.info(error)
        return success, error

    def _connection_error(self):
        error = "Connection error, the receiver failed to reply. Please try again"
        log.info(error)
        if self.callback_receive:
            GLib.idle_add(self.callback_receive, False, error)

    def stop(self):
        if self.w:
            try:
                self.w.close()
                self.w = None
            except WrongPasswordError as e:
                # This error is already been handled in _handle_failure, so here
                # we can safely ignore it
                log.debug(e)


def main(args):
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    def code_generated(code, wormhole_data):
        print("Discovery info: {}".format(code))
        # Wait for the user without blocking everything
        reactor.callInThread(cancel)

    def cancel():
        input("Press Enter to cancel")
        offer.stop()
        reactor.callFromThread(reactor.stop)

    def received(success, error_msg):
        if success:
            print("\nKey sent successfully")
        else:
            print("\nAn error occurred: {}".format(error_msg))
        # We are still waiting for the user to press Enter
        print("Press Enter to exit")

    key = get_usable_keys(pattern=args[0])[0]
    offer = WormholeOffer(key, received, callback_code=code_generated)
    offer.start()
    print("Offering key: {}".format(key))
    reactor.run()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
