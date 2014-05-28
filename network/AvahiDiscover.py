import dbus
import avahi
import gobject
from dbus.mainloop.glib import DBusGMainLoop

class ServiceDiscover:

    def __init__(self, stype):
        self.domain = ""
        self.stype = stype

    def discover(self):

        loop = DBusGMainLoop()

        self.bus = dbus.SystemBus(mainloop=loop)
        self.server = dbus.Interface( self.bus.get_object(avahi.DBUS_NAME, '/'),
                    'org.freedesktop.Avahi.Server')

        self.sbrowser = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME,
                    self.server.ServiceBrowserNew(avahi.IF_UNSPEC,
                        avahi.PROTO_UNSPEC, self.stype, 'local', dbus.UInt32(0))),
                    avahi.DBUS_INTERFACE_SERVICE_BROWSER)

        self.sbrowser.connect_to_signal("ItemNew", self.handler)

        gobject.MainLoop().run()

    def handler(self, interface, protocol, name, stype, domain, flags):
        print "Found service '%s' type '%s' domain '%s' " % (name, stype, domain)

        if flags & avahi.LOOKUP_RESULT_LOCAL:
            # FIXME: skip local services
            pass

        self.server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=self.service_resolved, error_handler=self.print_error)

    def service_resolved(self, *args):
        print 'service resolved'
        print 'name:', args[2]
        print 'address:', args[7]
        print 'port:', args[8]

    def print_error(self, *args):
        print 'error_handler'
        print args[0]


def test():
    service_discover = ServiceDiscover(stype='_http._tcp')
    service_discover.discover()

if __name__ == "__main__":
    test()