# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# diskfree.py - IdleBarplugin for showing the freedisk space for recording
# -----------------------------------------------------------------------
# $Id: __init__.py 8333 2006-10-07 06:11:59Z duncan $
#
# Author: Tanja Kotthaus <owigera@web.de>
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


# python modules
import time
import os

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config
import util.fileops as util


class PluginInterface(IdleBarPlugin):
    """
    Displays the amount of free disk space

    Activate with:
    plugin.activate('idlebar.diskfree', level=30)

    This plugin displays the total amount of free disk space for recordings
    """
    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.diskfree'
        self.time = 0
        self.diskfree = 0


    def getDiskFree(self):
        """
        Determine amount of freedisk space
        Update maximum every 30 seconds

        """
        if (time.time()-self.time)>30:
            self.time = time.time()
            freespace = util.freespace(config.TV_RECORD_DIR)
            self.diskfree = _('%iGb') % (((freespace / 1024) / 1024) / 1024)

    def draw(self, (type,object),x,osd):
        """
        Drawing to idlebar
        """

        self.getDiskFree()
        font = osd.get_font('small0')
        widthdf = 0
        widthdf = font.stringsize(self.diskfree)
        osd.draw_image(os.path.join(config.ICON_DIR, 'misc/chartpie.png' ),(x, osd.y + 7, -1, -1))
        osd.write_text(self.diskfree, font, None, x + 15, osd.y + 55 - font.h, widthdf, font.h, 'left', 'top')

        return widthdf + 15

