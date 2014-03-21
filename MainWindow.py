from gi.repository import Gtk, GdkPixbuf
from Sections import KeysSection, SignedSection

class MainWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Geysign")
        self.set_border_width(10)

        # create notebook container
        notebook = Gtk.Notebook()
        notebook.append_page(KeysSection(), Gtk.Label('Sign'))
        notebook.append_page(SignedSection(), Gtk.Label('Key signed'))
        self.add(notebook)

        # setup signals
        self.connect("delete-event", Gtk.main_quit)
