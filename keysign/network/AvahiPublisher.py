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
DBusGMainLoop(set_as_default=True)


class AvahiPublisher:

    def __init__(self,
            service_name='Demo Service',
            service_type='_demo._tcp',
            service_port=8899,
            service_txt={},
            domain='',
            host=''):
        self.log = logging.getLogger(__name__)
        #self.loop = loop or DBusGMainLoop()
        self.bus = dbus.SystemBus()
        self.server = dbus.Interface(
            self.bus.get_object( avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER ),
            avahi.DBUS_INTERFACE_SERVER )

        self.service_name = service_name
        #See http://www.dns-sd.org/ServiceTypes.html
        self.service_type = service_type
        self.service_port = service_port
        self.service_txt = avahi.dict_to_txt_array(service_txt) #TXT record for the service
        self.domain = domain # Domain to publish on, default to .local
        self.host = host # Host to publish records for, default to localhost

        self.group = None
        # Counter so we only rename after collisions a sensible number of times
        self.rename_count = 12


    def add_service(self):
        if self.group is None:
            group = dbus.Interface(
                    self.bus.get_object(
                        avahi.DBUS_NAME, self.server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)
            group.connect_to_signal('StateChanged',
                self.entry_group_state_changed)

            self.group = group

        self.log.info("Adding service '%s' of type '%s' with fpr '%s'",
            self.service_name, self.service_type, self.service_txt)

        group = self.group
        group.AddService(
                avahi.IF_UNSPEC,    #interface
                avahi.PROTO_UNSPEC, #protocol
                dbus.UInt32 (0),    #flags
                self.service_name, self.service_type,
                self.domain, self.host,
                dbus.UInt16 (self.service_port),
                self.service_txt)
        group.Commit()

    def remove_service(self):
        '''Publishes services to be removed with name, stype, and domain.'''
        self.log.info("Removing with fpr '%s'", self.service_txt)
        if not self.group is None:
            self.group.Reset()

    def server_state_changed(self, state):
        if state == avahi.SERVER_COLLISION:
            self.log.warn("Server name collision (%s)", self.service_name)
            self.remove_service()
        elif state == avahi.SERVER_RUNNING:
            self.add_service()

    def entry_group_state_changed(self, state, error):
        self.log.debug("state change: %i", state)

        if state == avahi.ENTRY_GROUP_ESTABLISHED:
            self.log.info("Service established.")

        elif state == avahi.ENTRY_GROUP_COLLISION:
            self.rename_count -= 1
            if self.rename_count > 0:
                name = self.server.GetAlternativeServiceName(self.service_name)
                self.log.warn("Service name collision, changing name to '%s'",
                    name)
                self.remove_service()
                self.add_service()

            else:
                # FIXME: max_renames is not defined. We probably want to restructure
                # this a little bit, anyway. i.e. have a self.max_renames
                # and a self.rename_count or so
                m = "No suitable service name found after %i retries, exiting."
                self.log.error(m, self.max_renames)
                raise RuntimeError(m % self.max_renames)

        elif state == avahi.ENTRY_GROUP_FAILURE:
            m = "Error in group state changed %s"
            self.log.error(m, error)
            raise RuntimeError(m % error)


DBusGMainLoop( set_as_default=True )
if __name__ == '__main__':
    ap = AvahiPublisher()
    ap.add_service()

    main_loop = GObject.MainLoop()
    bus = dbus.SystemBus()

    server = dbus.Interface(
            bus.get_object( avahi.DBUS_NAME, avahi.DBUS_PATH_SERVER ),
            avahi.DBUS_INTERFACE_SERVER )

    server.connect_to_signal( "StateChanged", ap.server_state_changed )
    ap.server_state_changed( server.GetState() )


    try:
        main_loop.run()
    except KeyboardInterrupt:
        pass

    if not ap.group is None:
        ap.group.Free()

