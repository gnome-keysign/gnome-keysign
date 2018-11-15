class BluetoothException(Exception):
    """Parent class for all Bluetooth-related errors"""


class NoBluezDbus(BluetoothException):
    """The required org.bluez dbus is not available"""


class NoAdapter(BluetoothException):
    """There isn't an usable Bluetooth adapter"""


class UnpoweredAdapter(BluetoothException):
    """The Bluetooth adapter is turned off"""


class AvahiException(Exception):
    """Parent class for all Avahi-related errors"""


class NoAvahiDbus(AvahiException):
    """The required avahi dbus is not available"""
