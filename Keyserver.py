#!/usr/bin/env python

import BaseHTTPServer
from SocketServer import ThreadingMixIn

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


if __name__ == '__main__':
    KEYDATA = 'Example data'
    class ExampleKeyRequestHandler(KeyRequestHandlerBase):
        '''You will need to create this during runtime'''
        keydata = KEYDATA

    BaseHTTPServer.test(ExampleKeyRequestHandler, ThreadedKeyserver)
