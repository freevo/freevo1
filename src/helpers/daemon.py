#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# daemon.py - helper script to start freevo on keypress
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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


import os
import sys
import config
import pylirc
import time
from optparse import Option, BadOptionError, OptionValueError, OptionParser, IndentedHelpFormatter

def start():
    try:
        pylirc.init('freevo', config.LIRCRC)
        pylirc.blocking(1)
    except RuntimeError:
        print 'WARNING: Could not initialize PyLirc!'
        sys.exit(0)
    except IOError:
        print 'WARNING: %s not found!' % config.LIRCRC
        sys.exit(0)


def stop():
    pylirc.exit()


def parse_options():
    """
    Parse command line options
    """
    import version
    formatter=IndentedHelpFormatter(indent_increment=2, max_help_position=36, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="""
Freevo helper script to start Freevo on lirc command.  Everytime Freevo is not
running and EXIT or POWER is pressed, this script will start Freevo. If the
display in freevo.conf is x11 or dga, this script will start Freevo in a new X
session.""", version='%prog ' + version.version)
    parser.add_option('--start', action='store_true', default=False,
        help='start the daemon [default:%default]')
    parser.add_option('--stop', action='store_true', default=False,
        help='stop the daemon [default:%default]')
    return parser.parse_args()


if __name__ == '__main__':
    (options, args) = parse_options()


start()
while True:
    time.sleep(1)
    code = pylirc.nextcode();
    if code and code[0] in ( 'EXIT', 'POWER' ):
        stop()
        if config.CONF.display in ( 'x11', 'dga' ):
            options = '--fullscreen'
        else:
            options = ''

        os.system('%s %s >/dev/null 2>/dev/null' % (os.environ['FREEVO_SCRIPT'], options))
        start()
