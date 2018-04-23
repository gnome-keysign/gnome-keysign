#!/usr/bin/env python
#
from __future__ import print_function
# We can't use unicode_literals because there seems to be
# a bug in setuptools:
# https://stackoverflow.com/a/23175194/2015768
# from __future__ import unicode_literals

import codecs
import glob
import logging

from setuptools import setup
from setuptools.command.install import install
from setuptools.command.test import test as TestCommand
from distutils.command.build import build
#import py2exe
import os
import sys

logging.basicConfig(level=logging.WARN)

# Just in case we're attempting to execute this setup.py
# when cwd != thisdir...
os.chdir(os.path.dirname(os.path.realpath(__file__)))
with open(os.path.join('keysign', '_version.py')) as f:
    # This should define __version__
    exec(f.read())


def translate_desktop_file(infile, outfile, localedir):
    infp = codecs.open(infile, 'rb', encoding='utf-8')
    outfp = codecs.open(outfile, 'wb', encoding='utf-8')

    catalogs = get_catalogs(localedir)

    for line in (x.strip() for x in infp):
        logging.debug('Found in original (%s): %r', type(line), line)
        # We intend to ignore the first line
        if line.startswith('[Desktop'):
            additional_lines = []
        else:
            additional_lines = []
            # This is a rather primitive approach to generating the translated
            # desktop file.  For example we don't really care about all the
            # keys in the file.  But its simplicity is a feature and we
            # ignore the runtime overhead, because it should only run centrally
            # once.
            key, value = line.split('=', 1)
            logging.debug("Found key: %r", key)
            for locale, catalog in catalogs.items():
                translated = catalog.get(value)
                logging.debug("Translated %r[%r]=%r: %r (%r)",
                    key, locale, value, translated,
                    translated.string if translated else '')
                if translated and translated.string \
                              and translated.string != value:
                    additional_line = u'{keyword}[{locale}]={translated}'.format(
                                        keyword=key,
                                        locale=locale,
                                        translated=translated.string,
                                    )
                    additional_lines.append(additional_line)
                logging.debug("Writing more lines: %s", additional_lines)

        # Write the new file.
        # First the original line found it in the file, then the translations.
        outfp.writelines((outline+'\n' for outline in ([line] + additional_lines)))


def translate_appdata_file(infile, outfile, localedir):
    from lxml import etree
    catalogs = get_catalogs(localedir)
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(infile, parser)
    root = tree.getroot()
    for elem in root.iter():
        # We remove any possible tailing whitespaces to allow lxml to format the output
        elem.tail = None
        if elem.get("translatable") == "yes":
            elem.attrib.pop("translatable", None)
            elem.attrib.pop("comments", None)  # Are comments allowed?
            message = elem.text
            parent = elem.getparent()
            pos = parent.getchildren().index(elem) + 1
            for locale, catalog in catalogs.items():
                translated = catalog.get(message)
                if translated and translated.string \
                        and translated.string != message:
                    logging.debug("Translated [%s]%r: %r (%r)",
                                  locale, message, translated, translated.string)
                    tr = etree.Element(elem.tag)
                    attrib = tr.attrib
                    attrib["{http://www.w3.org/XML/1998/namespace}lang"] = str(locale)
                    tr.text = translated.string
                    parent.insert(pos, tr)
    tree.write(outfile, encoding='utf-8', pretty_print=True)


def get_catalogs(localedir):
    # We import it here rather than globally because
    # we don't have a guarantee for babel to be available
    # globally. The setup_requires can only be evaluated after
    # this file has been loaded. And it can't load if the import
    # cannot be resolved.
    from babel.messages.pofile import read_po

    # glob in Python 3.5 takes ** syntax
    # pofiles = glob.glob(os.path.join(localedir, '**.po', recursive=True))
    pofiles = [os.path.join(dirpath, f)
               for dirpath, dirnames, files in os.walk(localedir)
               for f in files if f.endswith('.po')]
    logging.debug('Loading %r', pofiles)
    catalogs = {}

    for pofile in pofiles:
        catalog = read_po(codecs.open(pofile, 'r', encoding="utf-8"))
        catalogs[catalog.locale] = catalog
        logging.info("Found %d strings for %s", len(catalog), catalog.locale)
        # logging.debug("Strings for %r", catalog, catalog.values())
    if not catalogs:
        logging.warning("Could not find pofiles in %r", pofiles)
    return catalogs


class BuildWithCompile(build):
    sub_commands = [('compile_catalog', None)] + build.sub_commands

    def run(self):
        translate_desktop_file('data/org.gnome.Keysign.raw.desktop', 'data/org.gnome.Keysign.desktop', 'keysign/locale')
        translate_appdata_file('data/org.gnome.Keysign.raw.appdata.xml', 'data/org.gnome.Keysign.appdata.xml', 'keysign/locale')
        build.run(self)


# Pretty much from http://stackoverflow.com/a/41120180/2015768
class InstallWithCompile(install):
    def run(self):
        try:
            from babel.messages.frontend import compile_catalog
            compiler = compile_catalog(self.distribution)
            option_dict = self.distribution.get_option_dict('compile_catalog')
            compiler.domain = [option_dict['domain'][1]]
            compiler.directory = option_dict['directory'][1]
            compiler.run()
        except Exception as e:
            print ("Error compiling message catalogs: {}".format(e),
                file=sys.stderr)
            print ("Do you have Babel (python-babel) installed?",
                file=sys.stderr)
        #super(InstallWithCompile, self).run()
        install.run(self)


# Inspired by the example at https://pytest.org/latest/goodpractises.html
class NoseTestCommand(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # Run nose ensuring that argv simulates running nosetests directly
        import nose
        nose.run_exit(argv=['nosetests' , 'tests'])


setup(
    name = 'gnome-keysign',
    version = __version__,
    description = 'OpenPGP key signing helper',
    author = 'Tobias Mueller',
    author_email = 'tobiasmue@gnome.org',
    url = 'http://wiki.gnome.org/GnomeKeysign',
    packages = [
        'keysign',
        'keysign.compat',
        'keysign.network',
        ],
    package_dir={
        'keysign': 'keysign',
    },
    package_data={
        'keysign': [
            '*.ui',
            'locale/*/*/*.mo',
            # The PO files are added in the MANIFEST, because they
            # should be part of the source distribution.
            # 'locale/*/*/*.po'
        ]
    },
    include_package_data = True,
    data_files=[
        ( 'share/applications',
            ['data/org.gnome.Keysign.desktop']),
        ( 'share/appdata',
            ['data/org.gnome.Keysign.appdata.xml']),
        ( 'share/icons/hicolor/scalable/apps',
            ['data/org.gnome.Keysign.svg']),
        #( 'share/locale/',
        # # We cannot use the glob below, because it only copies the file
        # # into the directory mentioned above, i.e. keysign.po, rather
        # # than de/LC_MESSAGES/keysign.po including the de/... directories.
        #    ([f for f in glob.glob('keysign/locale/*/*/*.po')] +
        #     [f for f in glob.glob('keysign/locale/*')])
        #    ),
    ],
    #scripts = ['gnome-keysign.py'],
    install_requires=[
        # Note that the dependency on <= 2.2 is only
        # to not confuse Ubuntu 14.04's pip as that
        # seems incompatible with a newer requests library.
        # https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1306991
        # 'requests<=2.2',
        # But this version seems to be requiring an old pyopenssl
        # with SSLv3 support which doesn't work with Ubuntu's 16.04.
        # So let's require a more modern requests.
        'requests>=2.6',
        
        'qrcode',
        'twisted'
        #'monkeysign', # Apparently not in the cheeseshop
        # avahi # Also no entry in the cheeseshop
        # dbus # dbus-python is in the cheeseshop but not pip-able
        ],
    extras_require={
        'bluetooth': ['pybluez>=0.22'],
    },
    setup_requires=[
        "babel",
        "lxml",
    ],
    tests_require=[
        "pgpy",
        "nose",
        "tox",
        "pep8",
        "pylint",
    ],
    license='GPLv3+',
    long_description=open('README.rst').read(),
    
    entry_points = {
        #'console_scripts': [
        #    'keysign = keysign.main'
        #],
        'gui_scripts': [
            'gnome-keysign = keysign:main',
            'gks-qrcode = keysign.GPGQRCode:main',
        ],
    },
    
    classifiers = [
        # Maybe not yet...
        #'Development Status :: 4 - Beta',
        
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Telecommunications Industry',    
    
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        # I think we are only 2.7 compatible
        'Programming Language :: Python :: 2.7',
        # We're still lacking support for 3
        'Programming Language :: Python :: 3',

        'License :: OSI Approved :: GNU General Public License (GPL)',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',

        'Operating System :: POSIX :: Linux',

        'Environment :: X11 Applications :: GTK',

        'Topic :: Desktop Environment',

        'Natural Language :: English',

        'Topic :: Communications :: Email',
        'Topic :: Multimedia :: Video :: Capture',
        'Topic :: Security :: Cryptography',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
        message_extractors = {
            '': [
               ('**.raw.desktop', 'babelglade:extract_desktop', None),
               ('**.raw.appdata.xml', 'babelglade:extract_glade', None),
            ],
            'keysign': [
                ('**.py', 'python', None),
                ('**.ui', 'babelglade:extract_glade', None),
            ],
        },
        cmdclass={
            'build': BuildWithCompile,
            #'install': InstallWithCompile,
            'test': NoseTestCommand,
        },
        # test_suite = 'nose.collector',
    )
