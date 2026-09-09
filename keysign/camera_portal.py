"""Camera Portal client for XDG Desktop Portal camera access."""

import logging
import os
import re

import dbus
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

log = logging.getLogger(__name__)

PORTAL_BUS_NAME = "org.freedesktop.portal.Desktop"
PORTAL_OBJ_PATH = "/org/freedesktop/portal/desktop"
CAMERA_IFACE = "org.freedesktop.portal.Camera"
REQUEST_IFACE = "org.freedesktop.portal.Request"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"

_request_token_counter = 0


def _using_flatpak():
    """Check if we are inside a Flatpak sandbox."""
    return os.path.exists("/.flatpak-info")


def is_camera_portal_available():
    """Check if the Camera Portal interface exists and has a camera."""
    result = False
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(PORTAL_BUS_NAME, PORTAL_OBJ_PATH)
        props = dbus.Interface(proxy, PROPERTIES_IFACE)
        is_present = props.Get(CAMERA_IFACE, "IsCameraPresent")
        log.info("Camera portal IsCameraPresent: %s", is_present)
        result = bool(is_present)
    except dbus.exceptions.DBusException as e:
        log.debug("Camera portal not available: %s", e)
    return result


def request_camera_access(callback):
    """Request camera access asynchronously.
    
    Calls callback(True, pipewire_fd) on success,
    or callback(False, None) on failure/denial.
    """
    global _request_token_counter

    try:
        bus = dbus.SessionBus()
        portal = bus.get_object(PORTAL_BUS_NAME, PORTAL_OBJ_PATH)

        _request_token_counter += 1
        token = 'keysign_cam_%d' % _request_token_counter
        sender_name = re.sub(r'\.', r'_', bus.get_unique_name()[1:])
        request_path = (
            '/org/freedesktop/portal/desktop/request/%s/%s'
            % (sender_name, token))

        def on_response(response, results):
            if response == 0:
                log.info("Camera access granted")
                try:
                    fd_object = portal.OpenPipeWireRemote(
                        dbus.Dictionary(signature="sv"),
                        dbus_interface=CAMERA_IFACE)
                    pipewire_fd = fd_object.take()
                    log.info("Got PipeWire fd: %d", pipewire_fd)
                    callback(True, pipewire_fd)
                except dbus.exceptions.DBusException as e:
                    log.error("OpenPipeWireRemote failed: %s", e)
                    callback(False, None)
            else:
                log.info("Camera access denied (response=%d)", response)
                callback(False, None)

        bus.add_signal_receiver(
            on_response,
            signal_name='Response',
            dbus_interface=REQUEST_IFACE,
            path=request_path)

        portal.AccessCamera(
            dbus.Dictionary({'handle_token': dbus.String(token)},
                            signature="sv"),
            dbus_interface=CAMERA_IFACE)

        log.info("AccessCamera sent (token=%s)", token)

    except dbus.exceptions.DBusException as e:
        log.error("Failed to request camera access: %s", e)
        callback(False, None)
