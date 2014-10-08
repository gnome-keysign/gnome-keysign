#!/usr/bin/env python
#    Copyright 2014 Tobias Mueller <muelli@cryptobitch.de>
#    Copyright 2014 Andrei Macavei <andrei.macavei89@gmail.com>
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


class KeyError(Exception):
    pass

class Key:
    @classmethod
    def is_valid_fingerprint(cls, fingerprint):
        if len(fingerprint) != 40:
            return False
        return True

    def __init__(self, fingerprint):
        if not self.is_valid_fingerprint(fingerprint):
            raise KeyError("Fingerprint {} does not "
                           "appear to be valid".format(fingerprint))

        self.fingerprint = fingerprint

