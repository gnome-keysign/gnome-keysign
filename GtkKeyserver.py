#!/usr/bin/env python
'''This is an exercise to see how we can combine Python threads
with the Gtk mainloop
'''

import logging
import sys
#from multiprocessing import Process as Thread
from threading import Thread


from gi.repository import GLib
from gi.repository import Gtk

import Keyserver

log = logging.getLogger()

class ServerWindow(Gtk.Window):

    def __init__(self):
        self.log = logging.getLogger()
    
        Gtk.Window.__init__(self, title="Gtk and Python threads")

        self.connect("delete-event", Gtk.main_quit)
        
        GLib.idle_add(self.setup_server)


    def setup_server(self):
        self.log.info('Serving now')
        #self.keyserver = Thread(name='keyserver',
        #                        target=Keyserver.serve_key, args=('Foobar',))
        #self.keyserver.daemon = True
        self.log.debug('About to call %r', Keyserver.ServeKeyThread)
        self.keyserver = Keyserver.ServeKeyThread('Keydata')
        self.log.info('Starting thread %r', self.keyserver)
        self.keyserver.start()
        self.log.info('Finsihed serving')
        return False

    def dispose(self):
        self.keyserver.stop()

def main(args):
    log.debug('Running main with args: %s', args)
    w = ServerWindow()
    w.show_all()
    log.debug('Starting main')
    Gtk.main()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
            format='%(name)s (%(levelname)s): %(message)s')
    sys.exit(main(sys.argv))
