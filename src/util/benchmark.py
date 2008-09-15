# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is decorator class to time function calls
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

"""
This is decorator class to time function calls
"""

import time


class benchmark:
    """
    A decorator class to time function calls
    http://wiki.python.org/moin/PythonDecoratorLibrary
    """
    _indentation = 0

    def __init__(self, enabled=True, dumpcall=False):
        """
        Contructs an instance of benchmark.
        @param enabled: enables the benchmark timings
        @type enabled: bool
        """
        self.enabled = enabled
        self.dumpcall = dumpcall
        self.start = time.time()


    def __call__(self, func):
        """
        Call the benchmarking code, when enabled otherwise call the old
        function.
        @param func: enables the benchmark timings
        @type func: function
        """
        if self.enabled:
            fname = func.func_name
            argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
            def newfunc(*args, **kwargs):
                indentation = '  ' * benchmark._indentation
                benchmark._indentation += 1
                argstr = ''
                resstr = ''
                if self.dumpcall:
                    argstr = '('+', '.join('%s=%r' % entry for entry in zip(argnames,args) + kwargs.items())+')'
                print '%s-> %s%s' % (indentation, func.__name__, argstr)
                self.start = time.time()
                try:
                    result = func(*args, **kwargs)
                    if self.dumpcall:
                        resstr = ' => '+'%r' % (result,)
                finally:
                    print '%s<- %s%s: %.4f' % (indentation, func.__name__, resstr, time.time() - self.start)
                    benchmark._indentation -= 1
                return result
            newfunc.__name__ = func.__name__
            newfunc.__doc__ = func.__doc__
            newfunc.__module__ = func.__module__
            newfunc.__dict__.update(func.__dict__)
            return newfunc

        def origfunc(*args, **kwargs):
            return func(*args, **kwargs)
        origfunc.__name__ = func.__name__
        origfunc.__doc__ = func.__doc__
        origfunc.__module__ = func.__module__
        origfunc.__dict__.update(func.__dict__)
        return origfunc


if __name__ == '__main__':

    @benchmark(False)
    def not_benchmarked():
        """print a message"""
        print 'not benchmarked'


    @benchmark()
    def quickrunning(n):
        """Wait for n * 1us"""
        for i in range(n):
            time.sleep(0.000001)


    @benchmark(dumpcall=True)
    def longrunning(n):
        """Wait for n * 100ms"""
        quickrunning(n)
        for i in range(n):
            time.sleep(0.1)
        return n,


    @benchmark()
    def failure():
        """Generate an exception"""
        return 1/0

    not_benchmarked()
    print '__name__:', not_benchmarked.__name__
    longrunning(12)
    longrunning(2)
    print '__repr__:', longrunning
    print '__name__:', longrunning.__name__
    print '__doc__:', longrunning.__doc__
    print '__module__:', longrunning.__module__
    print '__dict__:', longrunning.__dict__
    try:
        failure()
    except:
        import traceback
        traceback.print_exc()
    print '__name__:', failure.__name__
    print '__doc__:', failure.__doc__

    class MyClass:
        @benchmark(dumpcall=True)
        def myfunc(*args):
            pass

    myclass = MyClass()
    print myclass
    myclass.myfunc(100, 200)
