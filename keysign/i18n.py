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
locale.setlocale(locale.LC_ALL, '')
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)
gettext.bindtextdomain(APP, DIR)
gettext.textdomain(APP)
lang = gettext.translation(APP, DIR, fallback=True)

## This seems to cause "_" to be installed into globals.
## Let's not do that to not confuse libraries that we include
# gettext.install(APP, DIR, unicode=1)


from locale import gettext as _
# TRANSLATORS: Please include your locale, e.g. "de". We're trying to debug native gettext
log.debug (_("Translated for gettext (C)"))

_ = lang.ugettext
# TRANSLATORS: Please include your locale, e.g. "de". We're trying to debug pure python gettext
log.debug (_("Translated for Python (C)"))
