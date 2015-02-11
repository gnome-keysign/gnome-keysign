#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
#    Copyright 2015 Jody Hansen <jobediah.hansen@gmail.com>
#
#    This file is part of GNOME Keysign.
#
#    GNOME Keysign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    GNOME Keysign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with GNOME Keysign.  If not, see <http://www.gnu.org/licenses/>.
import avahi, dbus
from dbus import DBusException
from dbus.mainloop.glib import DBusGMainLoop

from gi.repository import Gio
from gi.repository import GObject

import logging

__all__ = ["AvahiBrowser"]


# This should probably be upstreamed.
# Unfortunately, upstream seems rather inactive.
if getattr(avahi, 'txt_array_to_dict', None) is None:
    # This has been taken from Gajim
    # http://hg.gajim.org/gajim/file/4a3f896130ad/src/common/zeroconf/zeroconf_avahi.py
    # it is licensed under the GPLv3.
    def txt_array_to_dict(txt_array):
        txt_dict = {}
        for els in txt_array:
            key, val = '', None
            for c in els:
                    #FIXME: remove when outdated, this is for avahi < 0.6.14
                    if c < 0 or c > 255:
                        c = '.'
                    else:
                        c = chr(c)
                    if val is None:
                        if c == '=':
                            val = ''
                        else:
                            key += c
                    else:
                        val += c
            if val is None: # missing '='
                val = ''
            txt_dict[key] = val.decode('utf-8')
        return txt_dict

    setattr(avahi, 'txt_array_to_dict', txt_array_to_dict)


class AvahiBrowser(GObject.GObject):
    __gsignals__ = {
        'new_service': (GObject.SIGNAL_RUN_LAST, None,
            # name, address (could be an int too (for IPv4)), port, txt_dict
            (str, str, int, object)),
        'remove_service': (GObject.SIGNAL_RUN_LAST, None,
            # string 'remove'(placeholder: tuple element must be sequence), name
            (str, str)),
    }


    def __init__(self, loop=None, service='_geysign._tcp'):
        GObject.GObject.__init__(self)

        self.log = logging.getLogger()
        self.service = service
        # It seems that these are different loops..?!
        self.loop = loop or DBusGMainLoop()
        self.bus = dbus.SystemBus(mainloop=self.loop)

        self.server = dbus.Interface( self.bus.get_object(avahi.DBUS_NAME, '/'),
                'org.freedesktop.Avahi.Server')

        self.sbrowser = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME,
            self.server.ServiceBrowserNew(avahi.IF_UNSPEC,
                avahi.PROTO_UNSPEC, self.service, 'local', dbus.UInt32(0))),
            avahi.DBUS_INTERFACE_SERVICE_BROWSER)

        self.sbrowser.connect_to_signal("ItemNew", self.on_new_item)
        self.sbrowser.connect_to_signal("ItemRemove", self.on_service_removed)


    def on_new_item(self, interface, protocol, name, stype, domain, flags):
        self.log.info("Found service '%s' type '%s' domain '%s' ", name, stype, domain)

        if flags & avahi.LOOKUP_RESULT_LOCAL:
            # FIXME skip local services
            pass
        self.server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=self.on_service_resolved,
            error_handler=self.on_error)


    def on_service_resolved(self, interface, protocol, name, stype, domain,
                                  host, aprotocol, address, port, txt, flags):
        '''called when the browser successfully found a service'''
        txt = avahi.txt_array_to_dict(txt)
        self.log.info("Service resolved; name: '%s', address: '%s',"
                "port: '%s', and txt: '%s'", name, address, port, txt)
        retval = self.emit('new_service', name, address, port, txt)
        self.log.info("emitted '%s'", retval)


    def on_service_removed(self, interface, protocol, name, stype, domain, flags):
        '''Emits items to be removed from list of discovered services.'''
        self.log.info("Service removed; name: '%s'", name)
        retval = self.emit('remove_service', 'remove', name)
        self.log.info("emitted '%s'", retval)


    def on_error(self, *args):
        print 'error_handler'
        print args[0]


def main():
    loop = GObject.MainLoop()
    # We're not passing the loop to DBus, because... well, it
    # does't work... It seems to expect a DBusMainLoop, not
    # an ordinary main loop...
    ab = AvahiBrowser()

    def print_signal(*args):
        print "Signal ahoi", args

    ab.connect('new_service', print_signal)
    ab.connect('remove_service', print_signal)
    loop.run()


if __name__ == "__main__":
    main()
