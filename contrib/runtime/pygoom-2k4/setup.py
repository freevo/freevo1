#!/usr/bin/env python

import glob, os
from distutils.core import setup, Extension

# Pygoom extension ##############################################

# sources
sources = ['src/pygoom_module.c', 'src/aclib.c', 'src/cpudetect.c']

# includes
includes = ['.',
            './include',
            '/usr/include/goom/',
            '/usr/include/SDL/',
            '/usr/include/python2.4/pygame/',
           ]

# Intel P3 CFLAGS
# AMD 64 CFLAGS
CFLAGS = ['-O9', '-march=k8', '-mtune=k8', '-mmmx', '-msse', '-msse2', '-fpic', '-fomit-frame-pointer', '-Wall']
CFLAGS = ['-O9', '-march=pentium3', '-mtune=pentium3', '-mmmx', '-msse', '-msse2', '-fno-pic', '-fomit-frame-pointer', '-Wall']

# libraries
libdir    = ['/usr/lib/' ]

libraries = ['goom2', 'SDL']

pympav_1 = Extension('pygoom',
                     include_dirs       = includes,
                     sources            = sources,
                     library_dirs       = libdir,
                     extra_compile_args = CFLAGS,
                     libraries          = libraries )


# Setup #########################################################
setup ( name = 'pygoom-2k4',
        version = '0.2.0',
        description = 'Goom-2k4 bindings for Python',
        ext_modules = [pympav_1]
        )
