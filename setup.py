#!/usr/bin/env python
#
# Minimal setup.py for custom build commands
# Main configuration is in pyproject.toml

from setuptools import setup
from setuptools.command.build_py import build_py
from distutils.command.build import build
import os


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


# All configuration is in pyproject.toml
# This setup.py only provides custom build commands
setup(
    cmdclass={
        'build': BuildWithCompile,
    },
)
