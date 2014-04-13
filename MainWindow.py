from gi.repository import Gtk
from Sections import KeySignSection, GetKey

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Geysign")
        self.set_border_width(10)

        # create notebook container
        notebook = Gtk.Notebook()
        notebook.append_page(KeySignSection(), Gtk.Label('Keys'))
        notebook.append_page(GetKey(), Gtk.Label('Get Fingerprint'))
        self.add(notebook)

        # setup signals
        self.connect("delete-event", Gtk.main_quit)
