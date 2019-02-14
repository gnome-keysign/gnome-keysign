#!/usr/bin/env python

import gettext
import locale
import logging
import os

log = logging.getLogger(__name__)

APP = 'keysign'
# We have pretty much no idea what we're doing here.
# We want to be able to find the compiled message catalogues
# not only when the app has been installed, but also
# when it's being run from source.  Hence we're using
# a path relative to this file, hoping that it will cater
# for both use cases.  Feel free to improve.
DIR = os.path.join(os.path.dirname(__file__), 'locale')

## This is for C libraries, I think. I.e. not for pure python
## ones like us.  We do, however, need this for Gtk.Builder
## to load translations
try:
    locale.setlocale(locale.LC_ALL, '')
except locale.Error:
    log.exception("Cannot set locale")
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)
lang = gettext.translation(APP, DIR, fallback=True)

## This seems to cause "_" to be installed into globals.
## Let's not do that to not confuse libraries that we include
# gettext.install(APP, DIR, unicode=1)


from locale import gettext as _

try:
    _ = lang.ugettext
except AttributeError:
    log.info("Cannot get ugettext from lang: %r", lang, exc_info=True)
