#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
#    Copyright 2015 Jody Hansen <jobediah.hansen@gmail.com>
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

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from socketserver import ThreadingMixIn
except ImportError:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from SocketServer import ThreadingMixIn
import logging
import os
import socket
from threading import Thread

# This is probably really bad...  But doing relative imports only
# works for modules.  However, I want to be able to call this Keyserver.py
# for testing purposes.
if  __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    import keysign
    #mod = __import__('keysign')
    #sys.modules["keysign"] = mod
    __package__ = str('keysign')

from .__init__ import __version__
from .network.AvahiPublisher import AvahiPublisher

from .gpgmeh import fingerprint_from_keydata

log = logging.getLogger(__name__)

class KeyRequestHandlerBase(BaseHTTPRequestHandler):
    '''This is the "base class" which needs to be given access
    to the key to be served. So you will not use this class,
    but create a use one inheriting from this class. The subclass
    must also define a keydata field.
    '''
    server_version = 'GNOME-Keysign/' + '%s' % __version__

    # As per RFC 2015 Section 7
    # https://tools.ietf.org/html/rfc2015#section-7
    ctype = 'application/pgp-keys'

    def do_GET(self):
        f = self.send_head(self.keydata)
        self.wfile.write(self.keydata)

    def send_head(self, keydata=None):
        kd = keydata if keydata else self.keydata
        self.send_response(200)
        self.send_header('Content-Type', self.ctype)
        self.send_header('Content-Length', len(kd))
        self.end_headers()
        return kd

class ThreadedKeyserver(ThreadingMixIn, HTTPServer):
    '''The keyserver in a threaded fashion'''
    address_family = socket.AF_INET6

    def __init__(self, server_address, *args, **kwargs):
        if issubclass(self.__class__, object):
            super(ThreadedKeyserver, self).__init__(server_address, *args, **kwargs)
        else:
            HTTPServer.__init__(self, server_address, *args, **kwargs)
            # WTF? There is no __init__..?
            # ThreadingMixIn.__init__(self, server_address, *args, **kwargs)

        def server_bind(self):
            # Override this method to be sure v6only is false: we want to
            # listen to both IPv4 and IPv6!
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, False)
            HTTPServer.server_bind(self)



class ServeKeyThread(Thread):
    '''Serves requests and manages the server in separates threads.
    You can create an object and call start() to let it run.
    If you want to stop serving, call shutdown().
    '''

    def __init__(self, data, fpr, port=9001, *args, **kwargs):
        '''Initializes the server to serve the data'''
        self.keydata = data
        self.fpr = fpr
        self.port = port
        super(ServeKeyThread, self).__init__(*args, **kwargs)
        self.daemon = True
        self.httpd = None


    def start(self, data=None, fpr=None, port=None, *args, **kwargs):
        '''This is run in the same thread as the caller.
        This calls run() in a separate thread.
        In order to resolve DBus issues, most things
        are done here.
        However, you probably need to start
        dbus.mainloop.glib.DBusGMainLoop (set_as_default=True)
        in order for this work.
        '''

        port = port or self.port or 9001
        fpr = fpr or self.fpr

        tries = 10

        kd = data if data else self.keydata

        class KeyRequestHandler(KeyRequestHandlerBase):
            '''You will need to create this during runtime'''
            keydata = kd
        HandlerClass = KeyRequestHandler

        for port_i in (port + p for p in range(tries)):
            try:
                log.info('Trying port %d', port_i)
                server_address = ('', port_i)
                self.httpd = ThreadedKeyserver(server_address, HandlerClass, **kwargs)

                ###
                # This is a bit of a hack, it really should be
                # in some lower layer, such as the place were
                # the socket is created and listen()ed on.
                service_txt = {
                    'fingerprint': fpr,
                    'version': __version__,
                }


                log.info('Requesting Avahi with txt: %s', service_txt)

                self.avahi_publisher = ap = AvahiPublisher(
                    service_port = port_i,
                    service_name = 'HTTP Keyserver %s' % fpr,
                    service_txt = service_txt,
                    # self.keydata is too big for Avahi; it crashes
                    service_type = '_gnome-keysign._tcp',
                )
                log.info('Trying to add Avahi Service')
                ap.add_service()

            except socket.error as value:
                errno = value.errno
                if errno == 10054 or errno == 32:
                    # This seems to be harmless
                    break
            else:
                break

            finally:
                pass


        super(ServeKeyThread, self).start(*args, **kwargs)


    def serve_key(self, poll_interval=0.15):
        '''An HTTPd is started and being put to serve_forever.
        You need to call shutdown() in order to stop
        serving.
        '''

        #sa = self.httpd.socket.getsockname()
        try:
            log.info('Serving now on %s, this is probably blocking...',
                     self.httpd.socket.getsockname())
            self.httpd.serve_forever(poll_interval=poll_interval)
        finally:
            log.info('finished serving')
            #httpd.dispose()



    def run(self):
        '''This is being run by Thread in a separate thread
        after you call start()'''
        self.serve_key()


    def shutdown(self):
        '''Sends shutdown to the underlying httpd'''
        log.info("Removing Avahi Service")
        self.avahi_publisher.remove_service()
        log.info("Shutting down httpd %r", self.httpd)
        self.httpd.shutdown()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import dbus, time
    dbus.mainloop.glib.DBusGMainLoop (set_as_default=True)
    def stop_thread(t, seconds=5):
        log.info('Sleeping %d seconds, then stopping', seconds)
        time.sleep(seconds)
        t.shutdown()

    import sys
    if len(sys.argv) >= 2:
        fname = sys.argv[1]
        KEYDATA = open(fname, 'rb').read()
        # FIXME: Someone needs to determine the fingerprint
        #        of the data just read
        fpr = fingerprint_from_keydata(KEYDATA)
    else:
        KEYDATA = b'Example data'
        fpr = ''.join('F289 F7BA 977D F414 3AE9  FDFB F70A 0290 6C30 1813'.split())

    if len(sys.argv) >= 3:
        timeout = int(sys.argv[2])
    else:
        timeout = 5

    t = ServeKeyThread(KEYDATA, fpr)
    stop_t = Thread(target=stop_thread, args=(t,timeout))
    stop_t.daemon = True
    t.start()
    stop_t.start()
    while True:
        log.info('joining stop %s', stop_t.isAlive())
        stop_t.join(1)
        log.info('joining t %s', t.isAlive())
        t.join(1)
        if not t.isAlive() or not stop_t.isAlive():
            break
    log.warn('Last line')
