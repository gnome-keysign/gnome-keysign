GNOME Keysign
=============

A tool for signing OpenPGP keys.

Its purpose is to ease signing other peoples' keys.
It is similar to caff, PIUS, or monkeysign.  In fact, it is influenced a lot by these tools
and either reimplements ideas or reuses code.
Consider either of the aboved mentioned tools when you need a much more mature codebase.

In contrast to caff or monkeysign, this tool enables you to sign a key without contacting
a key server.
It downloads an authenticated copy of the key from the other party.
For now, the key is authenticated by its fingerprint which is securely transferred via a QR code.
Alternatively, the user may type the fingerprint manually, assuming that it has been transferred
securely via the audible channel.


After having obtained an authentic copy of the key, its UIDs are signed.
The signatures are then encrypted and sent via email.
In contrast to monkeysign, xdg-email is used to pop up a pre-filled email composer windows
of the mail client the user has configured to use.
This greatly reduces complexity as no SMTP configuration needs to be obtained
and gives the user a well known interface.




Installation
=============

The list of dependencies has not yet fully been determined.
However, this list of Ubuntu packages seems to make it work:

    python  avahi-daemon  python-avahi python-gi  gir1.2-glib-2.0   gir1.2-gtk-3.0 python-dbus python-requests monkeysign python-qrencode gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad


    

Portability to older versions
=============================

Currently, these issues are known to pose (minor) problems
when attempting to run with older libraries

Pyton-requests 1.2.3, as shipped with Ubuntu 13.10, cannot handle IPv4
in IPv6 URLs, i.e. http://[[1.2.3.4]]/.
That should be easy to work around, though.

The call to `set_always_show_image`, i.e. in saveButton.set_always_show_image
is available with GTK 3.6, only.  Earlier GTK versions do not need this
call, anyway.  So this should be easy to work around.

GStreamer is more of a problem.  However, the forward-porting guides can
probably be read "reverse", i.e. to back-port the GStreamer library.
Example issues include "videoconvert" being available under "ffmpefcolorspace"
and how to obtain the x-window-id.
