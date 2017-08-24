GNOME Keysign
=============

A tool for signing OpenPGP keys.

Its purpose is to ease signing other peoples' keys.
It is similar to caff, PIUS, or monkeysign.  In fact, it is influenced a lot by these tools
and either re-implements ideas or reuses code.
Consider either of the above mentioned tools when you need a much more mature codebase.

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

Before you can install GNOME Keysign, you need to have a few
dependencies installed.

The list of dependencies includes:

    * avahi with python bindings
    * dbus with python bindings
    * GStreamer with the good and bad plugins
    * GTK and Cairo
    * gobject introspection for those libraries
    * Magic Wormhole


openSUSE installation
---------------------

openSUSE has `packaged the application <https://build.opensuse.org/package/show/GNOME:Apps/gnome-keysign>`_
so it should be easy for you to install it.


Arch Linux installation
-----------------------

On Arch Linux you can find GNOME-Keysign in the AUR.
For example you can install it with:

.. code::

    pacaur -y gnome-keysign


Debian and Ubuntu dependencies
------------------------------

This list of packages seems to make it work:

    python  avahi-daemon  python-avahi python-gi  gir1.2-glib-2.0   gir1.2-gtk-3.0 python-dbus    gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-bad gstreamer1.0-plugins-good python-gi-cairo python-future

Magic Wormhole can be installed with pip:

.. code::

    pip install magic-wormhole

In Ubuntu, the package
gstreamer1.0-plugins-bad provides the zbar and the gtksink element, and
gstreamer1.0-plugins-good provides the autovideosrc element.

These packages should be optional:

    python-requests monkeysign python-qrcode


Fedora dependencies
--------------------

The following has worked at least once for getting the application running,
assuming that pip and git are already installed:

.. code::

    sudo dnf install -y python-gobject python-avahi dbus-python gstreamer1-plugins-bad-free-gtk gstreamer1-plugins-good  gnupg
    pip install magic-wormhole


Installation with pip
-----------------------

You may try the following in order to install the program to
your user's home directory.

.. code::

    pip install --user 'git+https://github.com/GNOME-Keysign/gnome-keysign.git#egg=gnome-keysign'
    
You should find a script in ~/.local/bin/gnome-keysign as well as a
.desktop launcher in ~/.local/share/applications/.


From git
---------

If you intend to hack on the software (*yay*!),
you may want to clone the repository and install from there.

.. code::

    git clone --recursive https://github.com/gnome-keysign/gnome-keysign.git
    cd gnome-keysign
    virtualenv --system-site-packages --python=python2 /tmp/keysign
    /tmp/keysign/bin/pip install .

Note that this installs the application in the virtual environment,
so you run the program from there, e.g. /tmp/keysign/bin/gnome-keysign.


Starting
=========

If you have installed the application with pip, a .desktop file
should have been deployed such that you should be able to run the
program from your desktop shell. Search for "Keysign".
If you want to run the program from the command line, you can
add ~/.local/bin to your PATH.  The installation should have put an
executable named keysign in that directory.

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
Select one and the application will advance to the next stage.

You will see the details of the key you've selected.
If you are happy with the key you have selected, click "Next".  
This will cause the key's availability to be published on the local network.
Also, a HTTP server will be spawned in order to enable others to download
your key.  In order for others to find you, the app displays both
a string identifying your key and a bar code.

Either share the string or the bar code with someone who wants to
sign your key.


Client side
-----------

Here, the client side is described. This is to sign someone's key.

You are presented with feed of your camera and an entry field to
type in a string.  If you meet someone who has the server side of
the application running, you can scan the bar code present at the
other party.

After you either typed a fingerprint or scanned a bar code, the program
will look for the relevant key on your local network.  Note that you've
transmitted the fingerprint securely, i.e. via a visual channel in form 
of a bar code or the displayed fingerprint.  This data allows to 
find the correct key.  In fact, the client tries to find the correct 
key by comparing the fingerprint of the keys available on the local 
network.

After the correct key has been found, you see details of the key to be 
signed.  If you are happy with what you see, i.e. because you have 
checked the names on the key to be correct, you can click next.  This 
will cause the program to sign the key and open your mail program with 
the encrypted signature preloaded as attachment.
