#!/usr/bin/env python
#    Copyright 2017 Ludovico de Nittis <aasonykk+gnome@gmail.com>
#
#    This file is part of GNOME Keysign.
#
#    GNOME Keysign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    GNOME Keysign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with GNOME Keysign.  If not, see <http://www.gnu.org/licenses/>.

from binascii import hexlify
from textwrap import dedent
import logging
import os
from builtins import input

from wormhole.cli.public_relay import RENDEZVOUS_RELAY
from wormhole.errors import TransferError, ServerConnectionError, WrongPasswordError, LonelyError
import wormhole
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
if __name__ == "__main__":
    from twisted.internet import gtk3reactor
    gtk3reactor.install()
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue

if __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    __package__ = str('keysign')

from .gpgmeh import get_usable_keys, get_public_key_data
from .util import encode_message, decode_message

log = logging.getLogger(__name__)


class WormholeOffer:
    def __init__(self, key, app_id=None):
        self.message_def = None
        self.key = key
        if not app_id:
            # the following id is needed for interoperability with wormhole cli
            app_id = "lothar.com/wormhole/text-or-file-xfer"
        self.w = wormhole.create(app_id, RENDEZVOUS_RELAY, reactor)

    @inlineCallbacks
    def allocate_code(self, code=None):
        if code:
            self.w.set_code(code)
        else:
            # ServerConnectionError may be raised
            self.w.allocate_code()
            code = yield self.w.get_code()
        log.info("Invitation Code: %s", code)
        wormhole_data = "WORM={0}".format(code)
        returnValue((code, wormhole_data))

    @inlineCallbacks
    def start(self):
        log.info("Wormhole: Sending a message")
        try:
            verifier = yield self.w.get_verifier()
            # TODO maybe we can show it to the user and ask for a confirm that is the right one
            ver_ascii = hexlify(verifier).decode("ascii")
            log.info("Verified key: %s", ver_ascii)

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
            msg = yield self.w.get_message()

            log.info("Got data, %d bytes" % len(msg))
            success, error_msg = self._check_received(msg)
            self.stop()
            returnValue((success, error_msg))

        except (ServerConnectionError, WrongPasswordError) as e:
            error = dedent(e.__doc__)
            log.error("Error: %s" % error)
            success = False
            returnValue((success, e))
        except LonelyError as le:
            log.info("Lonely, close() was called before the peer connection could be established")
            success = False
            returnValue((success, le))
        except Exception as e:
            error = dedent(e.__doc__)
            log.error("An unknown error occurred: %s" % error)
            success = False
            returnValue((success, e))

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

    def stop(self):
        if self.w:
            try:
                self.w.close().addErrback(log.debug)
            except (TransferError, ServerConnectionError, WrongPasswordError) as error:
                # These errors should be already handled previously
                # so here we can safely ignore them
                log.debug("Error: %s", error.type)
            self.w = None


def main(args):
    if not args:
        raise ValueError("You must provide an argument to identify the key")

    def code_generated(result):
        code, _ = result
        print("Discovery info: {}".format(code))
        # Wait for the user without blocking everything
        reactor.callInThread(cancel)

    def cancel():
        input("Press Enter to cancel")
        offer.stop()
        reactor.callFromThread(reactor.stop)

    def received(result):
        success, error_msg = result
        if success:
            print("\nKey successfully sent")
        else:
            print("\nAn error occurred: {}".format(error_msg))
        # We are still waiting for the user to press Enter
        print("Press Enter to exit")

    key = get_usable_keys(pattern=args[0])[0]
    offer = WormholeOffer(key)
    offer.allocate_code().addCallback(code_generated)
    offer.start().addCallback(received)
    print("Offering key: {}".format(key))
    reactor.run()

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
