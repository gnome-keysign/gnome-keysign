#!/usr/bin/env python

import logging
import signal
import sys

from gi.repository import Gtk, GLib, Gio
from Sections import KeySignSection, GetKeySection

class MainWindow(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(
            self, application_id='org.gnome.Geysign')
        self.connect("activate", self.on_activate)
        self.connect("startup", self.on_startup)
        
        self.log = logging.getLogger()
        self.log = logging


    def on_quit(self, app, param=None):
        self.quit()


    def on_startup(self, app):
        self.log.error("Startup")
        self.window = Gtk.ApplicationWindow(application=app)
        
        self.window.set_border_width(10)

        # create notebook container
        notebook = Gtk.Notebook()
        notebook.append_page(KeySignSection(), Gtk.Label('Keys'))
        notebook.append_page(GetKeySection(), Gtk.Label('Get Key'))
        self.window.add(notebook)

        quit = Gio.SimpleAction(name="quit", parameter_type=None)
        self.add_action(quit)
        self.add_accelerator("<Primary>q", "app.quit", None)
        quit.connect("activate", self.on_quit)
        
        ## App menus
        appmenu = Gio.Menu.new()
        section = Gio.Menu.new()
        appmenu.append_section(None, section)

        some_item = Gio.MenuItem.new("Scan Image", "app.scan-image")
        section.append_item(some_item)

        quit_item = Gio.MenuItem.new("Quit", "app.quit")
        section.append_item(quit_item)

        self.set_app_menu(appmenu)


    def on_activate(self, app):
        self.log.error("Activate!")
        #self.window = Gtk.ApplicationWindow(application=app)
        
        self.window.show_all()
        # In case the user runs the application a second time,
        # we raise the existing window.
        self.window.present()


def main():
    try:
        GLib.unix_signal_add_full(GLib.PRIORITY_HIGH, signal.SIGINT, lambda *args : Gtk.main_quit(), None)
    except AttributeError:
        pass

    app = MainWindow()
    exit_status = app.run(None)

    return exit_status

if __name__ == '__main__':
    sys.exit(main())
