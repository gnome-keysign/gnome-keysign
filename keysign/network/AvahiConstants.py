#!/usr/bin/env python
#    Copyright 2018 Ludovico de Nittis <aasonykk+gnome@gmail.com>
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

import sys

import dbus

if sys.version_info[0] >= 3:
    unicode = str


class AvahiConstants:
    SERVER_RUNNING = 2
    SERVER_COLLISION = 3

    ENTRY_GROUP_ESTABLISHED = 2
    ENTRY_GROUP_COLLISION = 3
    ENTRY_GROUP_FAILURE = 4

    PROTO_UNSPEC = -1

    IF_UNSPEC = -1

    LOOKUP_RESULT_LOCAL = 8

    DBUS_NAME = "org.freedesktop.Avahi"
    DBUS_INTERFACE_SERVER = DBUS_NAME + ".Server"
    DBUS_PATH_SERVER = "/"
    DBUS_INTERFACE_ENTRY_GROUP = DBUS_NAME + ".EntryGroup"
    DBUS_INTERFACE_SERVICE_BROWSER = DBUS_NAME + ".ServiceBrowser"

    @staticmethod
    def string_to_byte_array(s):
        if isinstance(s, unicode):
            s = s.encode('utf-8')

        r = []

        for c in s:
            if isinstance(c, int):
                # Python 3: iterating over bytes yields ints
                r.append(dbus.Byte(c))
            else:
                # Python 2: iterating over str yields str
                r.append(dbus.Byte(ord(c)))

        return r

    @staticmethod
    def dict_to_txt_array(txt_dict):
        l = []

        for k, v in txt_dict.items():
            if isinstance(k, unicode):
                k = k.encode('utf-8')

            if isinstance(v, unicode):
                v = v.encode('utf-8')

            l.append(AvahiConstants.string_to_byte_array(b"%s=%s" % (k, v)))

        return l
