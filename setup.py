#!/usr/bin/env python

import os
from setuptools import setup
from distutils.command.build import build

os.chdir(os.path.dirname(os.path.realpath(__file__)))

with open(os.path.join('keysign', '_version.py')) as f:
    exec(f.read())

class BuildWithCompile(build):
    """Custom build command that translates desktop and appdata files"""
    sub_commands = [('compile_catalog', None)] + build.sub_commands

    def run(self):
        from babelglade.translate import translate_desktop_file, translate_appdata_file
        translate_desktop_file('data/org.gnome.Keysign.raw.desktop', 
                               'data/org.gnome.Keysign.desktop', 
                               'keysign/locale')
        translate_appdata_file('data/org.gnome.Keysign.raw.appdata.xml', 
                              'data/org.gnome.Keysign.appdata.xml', 
                              'keysign/locale')
        build.run(self)

setup(
    version=__version__,
    cmdclass={
        'build': BuildWithCompile,
    },
    message_extractors={
        '': [
           ('**.raw.desktop', 'babelglade:extract_desktop', None),
           ('**.raw.appdata.xml', 'babelglade:extract_glade', None),
        ],
        'keysign': [
            ('**.py', 'python', None),
            ('**.ui', 'babelglade:extract_glade', None),
        ],
    },
)
