from twisted.internet import reactor
from wormhole.cli.public_relay import RENDEZVOUS_RELAY
import wormhole
import gi
import logging
import json
gi.require_version('Gtk', '3.0')
from gi.repository import GLib


logger = logging.getLogger(__name__)
server_socket = None

w2 = None
w1 = None
# the following id is needed for interoperability with wormhole cli
app_id = u"lothar.com/wormhole/text-or-file-xfer"


def send(key_data, callback_receive, callback_code=None, code=None):
    global w2
    logger.info("Sending a message")

    w2 = wormhole.create(app_id, RENDEZVOUS_RELAY, reactor)
    if code:
        w2.set_code(code)
    else:
        w2.allocate_code()

        def write_code(code_generated):
            global code
            code = code_generated
            logger.info("Invitation Code: {}".format(code))
            GLib.idle_add(callback_code, code)

        w2.get_code().addCallback(write_code)
    kd_decoded = key_data.decode('utf-8')
    offer = {"message": kd_decoded}
    data = {"offer": offer}
    m = _encode_message(data)
    w2.send_message(m)

    # wait for reply
    def received(msg):
        global code
        logger.info("Got data, %d bytes" % len(msg))
        GLib.idle_add(callback_receive, key_data, code, True)
        w2.close()

    w2.get_message().addCallback(received)


def stop_sending():
    global w2
    if w2 is not None:
        w2.close()


def start_receive(code, callback):
    global w1
    w1 = wormhole.create(app_id, RENDEZVOUS_RELAY, reactor)
    w1.set_code(code)

    def received(message):
        m = _decode_message(message)
        key_data = m["offer"]["message"]
        logger.info("Message received: {}".format(key_data))
        GLib.idle_add(callback, key_data.encode("utf-8"))

        # send a reply with a message ack
        reply = {"answer": {"message_ack": "ok"}}
        reply_encoded = _encode_message(reply)
        return w1.send_message(reply_encoded)

    w1.get_message().addCallback(received)


def stop_receiving(callback):
    global w1
    if w1 is not None:
        w1.close()

    GLib.idle_add(callback)


def _encode_message(message):
    return json.dumps(message).encode("utf-8")


def _decode_message(message):
    return json.loads(message.decode("utf-8"))
