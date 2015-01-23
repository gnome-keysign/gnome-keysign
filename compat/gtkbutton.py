#!/usr/bin/env python
#    Copyright 2015 Tobias Mueller <muelli@cryptobitch.de>
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

"""This is a simple compatibility layer for the Gtk.Button and
its set_always_show_image method which exists from Gtk 3.6 only.
"""
from gi.repository import Gtk
if not hasattr(Gtk.Button, 'set_always_show_image'):
     setattr(Gtk.Button, 'set_always_show_image', lambda x,y: None)
