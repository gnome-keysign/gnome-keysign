from gi.repository import Gst
from gi.repository import Gtk, GLib
# Because of https://bugzilla.gnome.org/show_bug.cgi?id=698005
from gi.repository import Gtk, GdkX11
# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
from gi.repository import GdkX11, GstVideo

from SignPages import KeysPage, SelectedKeyPage

from key import Key, KeyError

Gst.init([])

FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeySignSection(Gtk.VBox):

    def __init__(self):
        super(KeySignSection, self).__init__()

        # create notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(KeysPage(), None)
        self.notebook.append_page(SelectedKeyPage(), None)

        #TODO make notebook change pages according to current step

        self.notebook.set_show_tabs(True) # TODO

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text("Step 1: Choose a key and click on 'Next' button.")
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.50) #TODO : Fix Hardcoded

        # create proceed button
        self.proceedButton = Gtk.Button('Next')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)


class GetKeySection(Gtk.Box):

    def __init__(self):
        super(GetKeySection, self).__init__()

        # create main container
        container = Gtk.VBox(spacing=10)

        # create fingerprint entry
        self.fingerprintEntryLabel = Gtk.Label()
        self.fingerprintEntryLabel.set_markup('<span size="15000">' + 'Type fingerprint'+ '</span>')
        self.fingerprintEntryLabel.set_margin_top(10)

        self.fingerprintEntry = Gtk.Entry()

        container.pack_start(self.fingerprintEntryLabel, False, False, 0)
        container.pack_start(self.fingerprintEntry, False, False, 0)

        # create scanner frame
        self.scanFrameLabel = Gtk.Label()
        self.scanFrameLabel.set_markup('<span size="15000">' + '... or scan QR code'+ '</span>')

        self.scanFrame = Gtk.Frame(label='QR Scanner')
        from scan_barcode import BarcodeReaderGTK
        self.scanFrame = BarcodeReaderGTK()
        self.scanFrame.set_size_request(150,150)
        self.scanFrame.show()
        # We *could* overwrite the on_barcode function, but
        # let's rather go with a GObject signal
        #self.scanFrame.on_barcode = self.on_barcode
        self.scanFrame.connect('barcode', self.on_barcode)
        #GLib.idle_add(        self.scanFrame.run)

        container.pack_start(self.scanFrameLabel, False, False, 0)
        container.pack_start(self.scanFrame, True, True, 0)

        # create save key button
        self.load_button = Gtk.Button('Open Image')
        self.load_button.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_OPEN, Gtk.IconSize.BUTTON))
        self.load_button.set_always_show_image(True)
        self.load_button.set_margin_bottom(10)
        
        self.load_button.connect('clicked', self.on_loadbutton_clicked)

        container.pack_start(self.load_button, False, False, 0)

        self.pack_start(container, True, True, 0)


    def on_loadbutton_clicked(self, *args, **kwargs):
        print "load"
        
    
    def on_barcode(self, sender, barcode, message=None):
        '''This is connected to the "barcode" signal.
        The message argument is a left over of an experimental
        API design.'''
        try:
            key = Key(barcode)
        except KeyError:
            log.exception("Could not create key from %s", barcode)
        else:
            print("barcode signal %s %s" %( barcode, message))

