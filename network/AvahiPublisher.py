import avahi
import dbus

from dbus.mainloop.glib import DBusGMainLoop

__all__ = ["AvahiPublisher"]

# Publishes a service of type '_demo._tcp'

TYPE = '_demo._tcp'

class AvahiPublisher:
    """A simple class to publish a network service with zeroconf using
    avahi.

    """

    def __init__(self, name, port, stype="_demo._tcp",
                 domain="", host="", text=""):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text

    def publish(self):
        bus = dbus.SystemBus()
        server = dbus.Interface(bus.get_object(
                                    avahi.DBUS_NAME,
                                    avahi.DBUS_PATH_SERVER),
                                avahi.DBUS_INTERFACE_SERVER)

        group = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)

        group.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,dbus.UInt32(0),
                     self.name, self.stype, self.domain, self.host,
                     dbus.UInt16(self.port), self.text)

        group.Commit()
        self.group = group

    def unpublish(self):
        self.group.Reset()


def main():
    name = "DemoService"
    service = AvahiPublisher(name=name, port=9001)
    print "Adding service '%s' of type '%s' ..." % (name, TYPE)

    service.publish()
    raw_input("Press any key to unpublish the service ")
    service.unpublish()


if __name__ == "__main__":
    main()