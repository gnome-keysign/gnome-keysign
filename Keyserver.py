#!/usr/bin/env python

import BaseHTTPServer
import logging
import socket
from SocketServer import ThreadingMixIn

log = logging.getLogger()

class KeyRequestHandlerBase(BaseHTTPServer.BaseHTTPRequestHandler):
    '''This is the "base class" which needs to be given access
    to the key to be served. So you will not use this class,
    but create a use one inheriting from this class. The subclass
    must also define a keydata field.
    '''
    server_version = 'Geysign/' + 'FIXME-Version'
    
    ctype = 'application/openpgpkey' # FIXME: What the mimetype of an OpenPGP key?

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

class ThreadedKeyserver(BaseHTTPServer.HTTPServer, ThreadingMixIn):
    pass


        
def serve_key(keydata, port=9001, **kwargs):
    tries = 10

    kd = keydata
    class KeyRequestHandler(KeyRequestHandlerBase):
        '''You will need to create this during runtime'''
        keydata = kd
    HandlerClass = KeyRequestHandler
    
    for port_i in (port + p for p in range(tries)):
        try:
            log.info('Trying port %d', port_i)
            server_address = ('', port_i)
            httpd = ThreadedKeyserver(server_address, HandlerClass, **kwargs)
            sa = httpd.socket.getsockname()
            try:
                log.info('Serving now, this is probably blocking...')
                httpd.serve_forever()
            finally:
                log.info('finished serving')
                #httpd.dispose()

        except socket.error, value:
            errno = value.errno
            if errno == 10054 or errno == 32:
                # This seems to be harmless
                break
        finally:
            pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    KEYDATA = 'Example data'
    serve_key(KEYDATA)
    log.warn('Last line')
