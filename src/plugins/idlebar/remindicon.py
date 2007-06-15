# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# remind.py - IdleBarplugin for monitoring the remind command output
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

__author__ = "Christian Lyra"
__version__ = "0.1"
__svnversion__ = "$Revision$"[11:-2]
__date__ = "$Date$"[7:-2]
__copyright__ = "Copyright (c) 2007 Christian Lyra"
__license__ = "GPL"


# python modules
import os
import time

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config



class PluginInterface(IdleBarPlugin):
    """
    Show a icon status based on remind command output.

    Activate with:
    plugin.activate('idlebar.remindicon')

    You can define the remind command with:
    REMINDICON_CMD='<cmd> (defaults to /usr/bin/remind -h )
    remind homepage:http://www.roaringpenguin.com/en/penguin/openSourceProducts/remind

    if the command output something then show the alert button else show the blue button.
    """
    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.remindicon'
        self.time = 0
        self.images = {}
        self.images['alert']   = os.path.join(config.ICON_DIR, 'misc/reminder_on.png')
        self.images['nothing'] = os.path.join(config.ICON_DIR, 'misc/reminder_off.png')
        self.status = self.images['nothing']
        self.cmd = config.REMINDICON_CMD

    def config(self):
        return [ ('REMINDICON_CMD', 'remind -h', 'Command to run the remind (-h is hush)') ]

    def getStatus(self):
        if (time.time()-self.time)>60:
            self.time = time.time()
            try:
                inst = os.popen(self.cmd)
                f = inst.readlines()
                inst.close()
            except:
                pass

            if f:
                self.status = self.images['alert']
                _debug_("Remind: %s" % f, 2)
            else:
                self.status = self.images['nothing']
        return self.status


    def draw(self, (type, object), x, osd):
        return osd.draw_image(self.getStatus(), (x, osd.y + 10, -1, -1))[0]
