
==============
GNOME-Keysign
==============

----------------------------------------------------
Sign another person's key easily and securely
----------------------------------------------------

:Date: 2018-06-08
:Manual group: GNOME Keysign Manual
:Manual section: 1
:Version: 1

SYNOPSIS
========
**gnome-keysign**

DESCRIPTION
===========
**gnome-keysign** is a tool for signing OpenPGP keys easily and securely.
It attempts to follow best practices similar to PIUS or caff.
In fact, it is influenced a lot by these tools
and either re-implements ideas or reuses code.
Consider either of the above mentioned tools when you need a much more mature codebase.

**gnome-keysign** will transfer the OpenPGP key secure between two machines and create encrypted signatures for each UID on the received key.
The UID is then sent to each email address via the MUA the user has configured in their desktop environment (cf. xdg-email).


OPTIONS
=======

none

ENVIRONMENT
===========

GNUPGHOME
    Not really an environment variable GNOME Keysign cares about, but the underlying calls to GnuPG respect that variable. You can use this variable if you want to run two instances of GNOME Keysign on the same machine to experiment around.

FILES
=====

~/.gnupg/gpg.conf
    Not something GNOME Keysign itself cares about, but it greatly affects its working. Please refer to **gnupg** for details.

Receiving an encrypted signature
==================================

If you receive an email with an encrypted signature, you need to decrypt the attachment and import the result. Maybe like so::

    cat '~/.cache/.../gnome-keysign-QtqXDj.asc'   |  gpg --decrypt  | gpg --import
    
You can probably drag and drop the email from your MUA into a terminal to get the path. Otherwise you need to save the attachment first somewhere.


SEE ALSO
========
gpg(1)

