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
import logging
import os

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject

if __name__ == "__main__" and __package__ is None:
    logging.getLogger().error("You seem to be trying to execute " +
                              "this script directly which is discouraged. " +
                              "Try python -m instead.")
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.sys.path.insert(0, parent_dir)
    os.sys.path.insert(0, os.path.join(parent_dir, 'monkeysign'))
    __package__ = str('keysign')

from .AvahiConstants import AvahiConstants as avahi

from ..errors import NoAvahiDbus

__all__ = ["AvahiBrowser"]

DBusGMainLoop( set_as_default=True )

log = logging.getLogger(__name__)

# This should probably be upstreamed.
# Unfortunately, upstream seems rather inactive.
if getattr(avahi, 'txt_array_to_dict', None) is None:
    # This has been taken from Gajim
    # https://dev.gajim.org/gajim/gajim/blob/2d6e7d2e/gajim/common/zeroconf/zeroconf_avahi.py#L131
    # it is licensed under the GPLv3.
    # https://github.com/lathiat/avahi/pull/133
    def txt_array_to_dict(txt_array):
        txt_dict = {}
        for els in txt_array:
            key, val = '', None
            for c in els:
                c = chr(c)
                if val is None:
                    if c == '=':
                        val = ''
                    else:
                        key += c
                else:
                    val += c
            if val is None:  # missing '='
                val = ''
            txt_dict[key] = val
        return txt_dict

    setattr(avahi, 'txt_array_to_dict', txt_array_to_dict)


class AvahiBrowser(GObject.GObject):
    __gsignals__ = {
        str('new_service'): (GObject.SignalFlags.RUN_LAST, None,
            # name, address (could be an int too (for IPv4)), port, txt_dict
            (str, str, int, object)),
        str('remove_service'): (GObject.SignalFlags.RUN_LAST, None,
            # string 'remove'(placeholder: tuple element must be sequence), name
            (str, str)),
    }


    def __init__(self, loop=None, service='_gnome-keysign._tcp'):
        GObject.GObject.__init__(self)

        self.log = logging.getLogger(__name__)
        self.service = service
        # It seems that these are different loops..?!
        self.loop = loop or DBusGMainLoop()
        self.bus = dbus.SystemBus(mainloop=self.loop)

        try:
            self.server = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME, '/'),
                                         'org.freedesktop.Avahi.Server')
        except dbus.exceptions.DBusException as de:
            log.exception("Avahi cannot be started: %s", de)
            raise NoAvahiDbus(de)

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
        print('error_handler')
        print(args[0])


def main():
    loop = GObject.MainLoop()
    # We're not passing the loop to DBus, because... well, it
    # doesn't work... It seems to expect a DBusMainLoop, not
    # an ordinary main loop...
    ab = AvahiBrowser()

    def print_signal(*args):
        print("Signal ahoi", args)

    ab.connect('new_service', print_signal)
    ab.connect('remove_service', print_signal)
    loop.run()


if __name__ == "__main__":
    main()
