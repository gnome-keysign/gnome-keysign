#!/usr/bin/env python

import BaseHTTPServer
import logging
import socket
from SocketServer import ThreadingMixIn
from threading import Thread

from AvahiPublish import AvahiPublisher

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
    '''The keyserver in a threaded fashion'''
    pass


        


class ServeKeyThread(Thread):
    '''Serves requests and manages the server in separates threads.
    You can create an object and call start() to let it run.
    If you want to stop serving, call shutdown().
    '''
    
    def __init__(self, data, port=9001, *args, **kwargs):
        '''Initializes the server to serve the data'''
        self.keydata = data
        self.port = port
        super(ServeKeyThread, self).__init__(*args, **kwargs)
        self.daemon = True
        self.httpd = None
    

    def start(self, data=None, port=None, *args, **kwargs):
        '''This is run in the same thread as the caller.
        This calls run() in a separate thread.
        In order to resolve DBus issues, most things
        are done here.
        '''

        port = port or self.port or 9001
        
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
                self.avahi_publisher = ap = AvahiPublisher(
                    service_port = port_i,
                    service_name = 'HTTP Keyserver',
                    service_txt = 'FIXME fingeprint', #FIXME Fingerprint
                    # self.keydata is too big for Avahi; it chrashes
                    service_type = '_geysign._tcp',
                )
                log.info('Trying to add Avahi Service')
                ap.add_service()
    
            except socket.error, value:
                errno = value.errno
                if errno == 10054 or errno == 32:
                    # This seems to be harmless
                    break
            else:
                break
 
            finally:
                pass


        super(ServeKeyThread, self).start(*args, **kwargs)
        

    def serve_key(self):
        '''An HTTPd is started and being put to serve_forever.
        You need to call shutdown() in order to stop
        serving.
        '''
        
        #sa = self.httpd.socket.getsockname()
        try:
            log.info('Serving now on %s, this is probably blocking...',
                     self.httpd.socket.getsockname())
            self.httpd.serve_forever()
        finally:
            log.info('finished serving')
            #httpd.dispose()
    
    

    def run(self):
        '''This is being run by Thread in a separate thread
        after you call start()'''
        self.serve_key()


    def shutdown(self):
        '''Sends shutdown to the underlying httpd'''
        log.info("Shutting down httpd %r", self.httpd)
        self.httpd.shutdown()
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import time
    def stop_thread(t, seconds=5):
        log.info('Sleeping %d seconds, then stopping', seconds)
        time.sleep(seconds)
        t.shutdown()

    KEYDATA = 'Example data'
    t = ServeKeyThread(KEYDATA)
    stop_t = Thread(target=stop_thread, args=(t,5))
    t.start()
    stop_t.start()
    log.warn('Last line')
