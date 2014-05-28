from gi.repository import Gtk
from Sections import KeySignSection, GetKeySection

from network.AvahiPublisher import ServicePublisher
from network.AvahiDiscover import ServiceDiscover

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Geysign")
        self.set_border_width(10)

        # create notebook container
        notebook = Gtk.Notebook()
        notebook.append_page(KeySignSection(), Gtk.Label('Keys'))
        notebook.append_page(GetKeySection(), Gtk.Label('Get Key'))
        self.add(notebook)

        # setup signals
        self.connect("delete-event", Gtk.main_quit)

        # setup avahi publisher
        service_publisher = ServicePublisher(name="GeysignService", port=9999)
        service_publisher.publish()

        # FIXME: gobject.MainLoop().run is blocking the main thread
        # setup avahi discover
        # service_discover = ServiceDiscover(stype='_http._tcp')
        # service_discover.discover()
