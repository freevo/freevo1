#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# a small tkinter example remote program
# -----------------------------------------------------------------------
# $Id$
#
# Notes: very basic layout.
#        need ENABLE_NETWORK_REMOTE = 1 in you local_conf.py
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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


import sys
import socket
from optparse import Option, BadOptionError, OptionValueError, OptionParser, IndentedHelpFormatter

import config

def parse_options():
    """
    Parse command line options
    """
    import version, revision
    _version = version.__version__
    if _version.endswith('-svn'):
        _version = _version.split('-svn')[0] + ' r%s' % revision.__revision__
    formatter=IndentedHelpFormatter(indent_increment=2, max_help_position=36, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="""
A small tkinter example remote program

You need to set ENABLE_NETWORK_REMOTE = 1 in you local_conf.py""", version='%prog ' + _version)
    parser.add_option('--host', default=config.REMOTE_CONTROL_TCP_HOST,
        help='The host to control [default:%default]')
    parser.add_option('--port', type='int', default=config.REMOTE_CONTROL_TCP_PORT,
        help='The port for the host [default:%default]')
    return parser.parse_args()


try:
    from Tkinter import *
except:
    print 'Warning: Tkinter not found. This script won\'t work.'
    print
    usage()


panels = [
    ['1',       '2',       '3'],
    ['4',       '5',       '6'],
    ['7',       '8',       '9'],
    ['ENTER',   '0',       'EXIT'],
    ['MENU',    'UP',      'GUIDE'],
    ['LEFT',    'SELECT',  'RIGHT'],
    ['DISPLAY', 'DOWN',    'SUBTITLE'],
    ['CH+',     'VOL+',    'PIP_ONOFF'],
    ['CH-',     'VOL-',    'PIP_SWAP'],
    ['PREV_CH', 'MUTE',    'PIP_MOVE'],
    ['PLAY',    'PAUSE',   'REC'],
    ['REW',     'STOP',    'FFWD'],
    ['EJECT',   'SLEEP',   'TV_VCR'],
]

# the big remote. can possibly be embedded in other stuff.
class FreevoRemote(Frame):
    def __init__(self, options, args, parent=None):
        Frame.__init__(self, parent)
        self.pack(expand=YES, fill=BOTH)
        self.host = options.host
        self.port = options.port
        # add the power button
        Button(self, text='POWER', command=self.PowerClick).pack(expand=YES, fill=BOTH)
        #create the frame for panel
        bframe = Frame(self)
        rcnt = 0
        for r in panels:
            ccnt = 0
            for b in r:
                #create the button for each element
                btn = Button(bframe, text=b, command=(lambda b=b: self.ButtonClick(b)))
                btn.grid(row=rcnt, column=ccnt, sticky=NSEW)

                ccnt = ccnt + 1
            # add the now complete row to panel
            bframe.rowconfigure(rcnt, weight=1)
            rcnt = rcnt + 1
        bframe.columnconfigure(0, weight=1)
        bframe.columnconfigure(1, weight=1)
        bframe.columnconfigure(2, weight=1)
        #add the panel to self
        bframe.pack(side=TOP, expand=YES, fill=BOTH)

    def PowerClick(self):
        self.ButtonClick('POWER')
        self.quit()

    def ButtonClick(self, b):
        print b
        #sockobj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockobj.connect((self.host, self.port))
        sockobj.send(b)
        sockobj.close()

if __name__ == '__main__':
    (options, args) = parse_options()

    root = FreevoRemote(options, args)
    root.master.title('Freevo Remote')
    root.mainloop()
