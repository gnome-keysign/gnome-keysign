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

    python  avahi-daemon  python-avahi python-gi  gir1.2-glib-2.0   gir1.2-gtk-3.0 python-dbus python-requests monkeysign python-qrcode gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad


Once you have the dependencies installed, a

    pip install --user .

should do everything in order to install the program to your
user's home directory.

If you don't have a local copy of the repository, you may try

    pip install --user 'git+https://github.com/muelli/geysigning.git#egg=gnome-keysign'
    


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




Starting
=======

If you have installed the application with pip, a .desktop file
should have been deployed such that you should be able to run the
program from your desktop shell. Search for "Keysign".
If you want to run the program from the command line, you can
add ~/.local/bin to your PATH.  The installation should have put an
exectuable named keysign in that directory.

If you haven't installed via pip or not to your user's home directory
(i.e. with --user), you can start the program from your environment's
./bin/ directory.


Running
=======


Server side
-----------

This describes running the application's server mode in order to allow 
you to have your key signed by others running the application in client 
mode.

Once you've fired up the application, you can see a list of your private keys.
Select one and click "Next".

You will see the details of the key you've selected.  You can revise 
your selected and click "Back".  If you are happy with the key you have 
selected, click "Next".  This will cause the key's availability to be 
published on the local network.  Also, a HTTP server will be spawned in 
order to enable others to download your key.  You also notice a bar 
code.  For now, it encodes the fingerprint of the key you have selected.

Either share the fingerprint or the bar code with someone who wants to 
sign your key.


Client side
-----------

Here, the client side is described. This is to sign someone's key.

If you select the "Get Key" Tab, you can either enter a key's 
fingerprint manually or scan a bar code.  If you meet someone who has 
the server side of the application running, you can scan the bar code
present at the other party.

After you either typed a fingerprint or scanned a bar code, the program
will look for the relevant key on your local network.  Note that you've
transmitted the fingerprint securely, i.e. via a visual channel in form 
of a bar code or the displayed fingerprint.  This data allows to 
find the correct key.  In fact, they client tries to find the correct 
key by comparing the fingerprint of the keys available on the local 
network.

After the correct key has been found, you see details of the key to be 
signed.  If you are happy with what you see, i.e. because you have 
checked the names on the key to be correct, you can click next.  This 
will cause the program to sign the key and open your mail program with 
the encrypted signature preloaded as attachment.
