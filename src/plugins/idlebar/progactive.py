# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# osd.py - Low level graphics routines
# -----------------------------------------------------------------------
# $Id$
#
# Notes: do not use the OSD object inside a thread
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

import time
import os
import locale
import config
import plugin
import skin

from pygame import image, transform
from plugins.idlebar import IdleBarPlugin

__version__='1.0'
__author__='mail@despeyer.de'
__doc__='''Display an Icon if prog (defined in local_conf.py) is active or not.
The Prog-Name is also drawn over the icon.
'''

class PluginInterface(IdleBarPlugin):
    """
    Display an Icon if prog is active.

    To activate put following Lines in local_conf.py:
    | plugin.activate('idlebar.progactive')
    """

    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.plugin_name='idlebar.progactive'
        self.time = 0
        self.progname = config.PROGACTIVE_PROGRAM
        icondir = os.path.join(config.ICON_DIR, 'status')
        self.images = {}
        self.images['cross'] = os.path.join(icondir, 'cross.png')
        self.images['check'] = os.path.join(icondir, 'check.png')
        self.image = self.images['cross']

    def config(self):
        '''config is called automatically, for default settings run:
        freevo plugins -i idlebar.progactive'''
        return [ ('PROGACTIVE_PROGRAM', None, 'Program that you want to monitor') ]

    def getstatus(self):
        '''
        Update every 30 secs
        '''
        if (time.time()-self.time) > 30:
            self.time = time.time()
            cmd = 'ps -A | grep ' + self.progname
            fin, fout = os.popen4(cmd)
            result = fout.read()
            if result == '':
                self.image = self.images['cross']
            else:
                self.image = self.images['check']

    def draw(self, (type, object), x, osd):
        self.getstatus()
        font = osd.get_font('small0')
        widthmt = font.stringsize(config.PROGACTIVE_PROGRAM)
        osd.write_text(config.PROGACTIVE_PROGRAM, font, None, x + 15, osd.y + 55 - font.h, \
            widthmt, font.h, 'left', 'top')
        if not self.image:
            return widthmt + 15
        return osd.drawimage(self.image, (x, osd.y + 10, -1, 45))[0]
