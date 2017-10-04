Translations
==============

This document describes operations we anticipate to
occur every so often, but not often enough to remember.

    

Updating existing translations
-------------------------------

Everytime a translatable string has changed, the .pot file needs
to be updated.  This can be done with

    python setup.py extract_messages


From the .pot file, the actual to-be-translated .po files need to be
generated.  This can be done with

    python setup.py update_catalog


Now, you can edit the .po file of your language.
Later, the .po files need to be compiled into .mo files.
That, however, should be done by the setup.py when building
the package.  To do that manually, you can try to

    python setup.py compile_catalog





Testing translations
----------------------

In order to test whether the translation works as expected,
you can run the (built and installed) program with the locale
of your desire set via the environment, i.e.

    env LC_MESSAGES=de_DE.utf-8


Check the output of  locale -a  to determine which locales you have installed.



Starting a new translation
---------------------------

For providing a new language, the .pot file has to be generated (or 
updated) using:

    python setup.py extract_messages
    
Now, the initial .po file can be created using the command below,
replacing "en" with the language code you want to translate to:

    python setup.py init_catalog --locale en
