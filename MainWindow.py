#!/usr/bin/env python

import logging

from gi.repository import GLib
from gi.repository import Gtk

from network.AvahiBrowser import AvahiBrowser
from network.AvahiPublisher import AvahiPublisher
from Sections import KeySignSection, GetKeySection

import Keyserver

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Geysign")
        self.log = logging.getLogger()

        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)

        # create notebook container
        notebook = Gtk.Notebook()
        notebook.append_page(KeySignSection(self), Gtk.Label('Keys'))
        notebook.append_page(GetKeySection(self), Gtk.Label('Get Key'))
        self.add(notebook)

        # setup signals
        self.connect("delete-event", Gtk.main_quit)

        self.avahi_browser = None
        self.avahi_service_type = '_geysign._tcp'
        self.discovered_services = []
        GLib.idle_add(self.setup_avahi_browser)

        self.keyserver = None
        self.port = 9001


    def setup_avahi_browser(self):
        # FIXME: place a proper service type
        self.avahi_browser = AvahiBrowser(service=self.avahi_service_type)
        self.avahi_browser.connect('new_service', self.on_new_service)

        return False

    def setup_server(self, keydata='Keydata'):
        self.log.info('Serving now')
        #self.keyserver = Thread(name='keyserver',
        #                        target=Keyserver.serve_key, args=('Foobar',))
        #self.keyserver.daemon = True
        self.log.debug('About to call %r', Keyserver.ServeKeyThread)
        self.keyserver = Keyserver.ServeKeyThread(str(keydata))
        self.log.info('Starting thread %r', self.keyserver)
        self.keyserver.start()
        self.log.info('Finsihed serving')
        return False

    def stop_server(self):
        self.keyserver.shutdown()


    def on_new_service(self, browser, name, address, port):
        self.log.info("Probably discovered something, let me check; %s %s:%i",
            name, address, port)
        if self.verify_service(name, address, port):
            GLib.idle_add(self.add_discovered_service, name, address, port)
        else:
            self.log.warn("Client was rejected: %s %s %i",
                        name, address, port)

    def verify_service(self, name, address, port):
        '''A tiny function to return whether the service
        is indeed something we are interested in'''
        return True

    def add_discovered_service(self, name, address, port):
        self.discovered_services += ((name, address, port), )

        return False
