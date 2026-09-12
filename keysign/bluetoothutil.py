#!/usr/bin/env python3
import logging
import os
import socket
import struct
try:
    import fcntl
except ImportError:
    fcntl = None
from xml.etree import ElementTree

import dbus
from _dbus_bindings import BUS_DAEMON_NAME, BUS_DAEMON_PATH, BUS_DAEMON_IFACE

from .errors import NoBluezDbus, NoAdapter, UnpoweredAdapter

log = logging.getLogger(__name__)

def get_bt_addr_for_interface(iface):
    if not fcntl:
        raise NoAdapter("fcntl not available on this platform")

    # Create a Bluetooth socket
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_RAW, socket.BTPROTO_HCI)

    # Get the Bluetooth address
    # SIOCGIFHWADDR is 0x8927
    # struct.pack formats: '256s' means 256-char string
    try:
        address = fcntl.ioctl(sock.fileno(), 0x8927, struct.pack("256s", iface.encode()[:15]))
    except OSError as e:
        if e.errno == 19: # No such device
            raise NoAdapter from e
        else:
            log.exception("cannot ioctl bt")
            raise
    finally:
        # Close the socket
        sock.close()

    # Extract the Bluetooth address from the returned bytes
    bt_address = ':'.join(['%02X' % b for b in address[18:24]])

    log.debug("BT: addr of %s is %s", iface, bt_address)
    return bt_address


def get_bluetooth_addresses():
    addresses = {}

    # Check for Bluetooth interfaces
    bluetooth_dir = '/sys/class/bluetooth'
    if not os.path.exists(bluetooth_dir):
        raise NoAdapter

    # Iterate through all Bluetooth interfaces
    ifaces = os.listdir(bluetooth_dir)
    log.info("BT interfaces: %s", ifaces)
    for interface in ifaces:
        try:
            bt_address = get_bt_addr_for_interface(interface)
            addresses[interface] = bt_address
        except Exception as e:
            addresses[interface] = f"Error: {str(e)}"

    return addresses

def get_local_bt_address():
    """Check if there is a powered on Bluetooth device and return its address.
       This is a blocking method"""

    #addrs = get_bluetooth_addresses()
    #log.info("Local BT addresses: %s", addrs)
    #return list(addrs.values())[0]

    available = False
    bus_name = "org.bluez"
    timeout = 2  # 2 seconds seems to be enough to start a bus service
    bus = dbus.SystemBus()

    try:
        _start_bus(bus_name, timeout)
    except dbus.exceptions.DBusException as e:
        raise NoBluezDbus(e)
    else:
        available_bt = _get_available_bt()
        for bt in available_bt:
            adapter = dbus.Interface(bus.get_object("org.bluez", bt), "org.freedesktop.DBus.Properties")
            power = adapter.Get("org.bluez.Adapter1", "Powered")
            if power:
                available = adapter.Get("org.bluez.Adapter1", "Address")
                break

        if len(available_bt) == 0:
            # Not a single BT adapter available in the system
            raise NoAdapter

        elif not available:
            # Every BT adapters are powered off
            raise UnpoweredAdapter

        return available


def _start_bus(bus_name, timeout, flags=0):
    """Manually start the bus, so we can set a custom timeout"""
    bus = dbus.SystemBus()
    bus.call_blocking(BUS_DAEMON_NAME, BUS_DAEMON_PATH,
                      BUS_DAEMON_IFACE,
                      'StartServiceByName',
                      'su', (bus_name, flags), timeout=timeout)


def _get_available_bt():
    """Returns the list of available Bluetooth"""
    available_bt = []
    bus_name = "org.bluez"
    object_path = "/org/bluez"
    bus = dbus.SystemBus()
    obj = bus.get_object(bus_name, object_path)
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Introspectable')
    xml_string = iface.Introspect()
    for child in ElementTree.fromstring(xml_string):
        if child.tag == 'node':
            bt = '/'.join((object_path, child.attrib['name']))
            available_bt.append(bt)
    log.info("Available Bluetooth interfaces: %s", available_bt)
    return available_bt
