# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo TV Guide module.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MER-
# CHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------


import time

class timed:
    """
    A decorator class to time function calls
    http://wiki.python.org/moin/PythonDecoratorLibrary
    """
    def __init__(self, func):
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__dict__.update(func.__dict__)
        self.func = func
        self.last = self.start = time.time()


    def __call__(self, *args, **kwargs):
        self.last = self.start = time.time()
        value = self.func(*args, **kwargs)
        self.last = time.time()
        print '%.3f' % (self.last - self.start)
        return value


    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__



if __name__ == '__main__':

    @timed
    def longrunning(n):
        """Wait for n * 100ms"""
        for i in range(n):
            time.sleep(0.1)

    longrunning(2)
    longrunning(12)
    print longrunning
    print longrunning.__name__
