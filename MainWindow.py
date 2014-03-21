from gi.repository import Gtk, GdkPixbuf
from Sections import KeySignSection, SignedKeysSection

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Geysign")
        self.set_border_width(10)

        # create notebook container
        notebook = Gtk.Notebook()
        notebook.append_page(KeySignSection(), Gtk.Label('Sign'))
        notebook.append_page(SignedKeysSection(), Gtk.Label('Get signed key'))
        self.add(notebook)

        # setup signals
        self.connect("delete-event", Gtk.main_quit)
