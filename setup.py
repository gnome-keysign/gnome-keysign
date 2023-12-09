#!/usr/bin/env python
#

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




class BuildWithCompile(build):
    sub_commands = [('compile_catalog', None)] + build.sub_commands

    def run(self):
        from babelglade.translate import translate_desktop_file, translate_appdata_file
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


class PytestTestCommand(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        print ("We're just running pytest...", file=sys.stderr)
        import subprocess
        subprocess.call(['pytest'])


setup(
    name = 'gnome-keysign',
    version = __version__,
    description = 'OpenPGP key signing helper',
    author = 'Tobias Mueller',
    author_email = 'tobiasmue@gnome.org',
    url = 'https://wiki.gnome.org/Apps/Keysign',
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
        ( 'share/metainfo',
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
        'twisted[tls]>=17.5.0',
        'magic-wormhole>=0.10.2',
        # avahi # Also no entry in the cheeseshop
        # dbus # dbus-python is in the cheeseshop but not pip-able
        ],
    extras_require={
        'bluetooth': ['pybluez>=0.22'],
    },
    setup_requires=[
        "babel",
        "BabelGladeExtractor",
    ],
    tests_require=[
        "pytest",
        "pytest_twisted",
        "tox",
        "pycodestyle",
        "pylint",
    ],
    license='GPLv3+',
    long_description=open('README.rst').read(),
    
    entry_points = {
        'console_scripts': [
            'gnome-keysign-sign-key = keysign.SignKey:main',
            'gnome-keysign-split-uids = keysign.export_uids:main',
        ],
        'gui_scripts': [
            'gnome-keysign = keysign:main',
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
            'test': PytestTestCommand,
        },
    )
