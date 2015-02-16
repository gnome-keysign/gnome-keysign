#!/usr/bin/env python
#

from keysign import __version__ as version

from setuptools import setup
from setuptools.command.install import install
#import py2exe
import sys


setup(
    name = 'gnome-keysign',
    version = version,
    description = 'OpenPGP key signing helper',
    author = 'Tobias Mueller',
    author_email = 'tobiasmue@gnome.org',
    url = 'http://wiki.gnome.org/GnomeKeysign',
    packages = [
        'keysign',
        'keysign.compat',
        'keysign.network'],
    #package_dir={'keysign': 'keysign'},
    #package_data={'keysign': ['data/']},
    data_files=[
        ('share/applications', ['data/gnome-keysign.desktop']),
        # Hm, hicolor/scalable doesn't seem to work so well
        #('share/icons/hicolor/scalable', ['data/gnome-keysign.svg']),
        ('share/icons', ['data/gnome-keysign.svg']),
    ],
    include_package_data = True,
    #scripts = ['gnome-keysign.py'],
    install_requires=[
        # Note that the dependency on <= 2.2 is only
        # to not confuse Ubuntu 14.04's pip as that
        # seems incompatible with a newer requests library.
        # https://bugs.launchpad.net/ubuntu/+source/python-pip/+bug/1306991
        'requests<=2.2', 
        'qrencode',
        #'monkeysign', # Apparently not in the cheeseshop
        # avahi # Also no entry in the cheeseshop
        # dbus # dbus-python is in the cheeseshop but not pip-able
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
        #'Programming Language :: Python :: 3',

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
        ]
    )
