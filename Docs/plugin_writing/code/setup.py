#!/usr/bin/env python

"""Setup script for my freevo plugin."""


__revision__ = "$Id$"

from distutils.core import setup, Extension
import distutils.command.install
import freevo.util.plugindistutils

# now start the python magic
setup (name = "nice_plugin",
       version = '0.1',
       description = "My first plugin",
       author = "me",
       author_email = "my@mail.address",
       url = "http://i-also-have-a-web.address",

       package_dir = freevo.util.plugindistutils.package_dir,
       packages = freevo.util.plugindistutils.packages,
       data_files = freevo.util.plugindistutils.data_files
       )
