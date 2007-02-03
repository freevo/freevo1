# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# cdstatus.py - IdleBarplugin for monitoring the cdstatus
# -----------------------------------------------------------------------
# $Id$
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


# python modules
import os

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config



class PluginInterface(IdleBarPlugin):
    """
    Show the status of all rom drives.

    Activate with:
    plugin.activate('idlebar.cdstatus')
    """
    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.cdstatus'
        icondir = os.path.join(config.ICON_DIR, 'status')
        self.cdimages = {}
        self.cdimages ['audiocd']     = os.path.join(icondir, 'cd_audio.png')
        self.cdimages ['empty_cdrom'] = os.path.join(icondir, 'cd_inactive.png')
        self.cdimages ['images']      = os.path.join(icondir, 'cd_photo.png')
        self.cdimages ['video']       = os.path.join(icondir, 'cd_video.png')
        self.cdimages ['dvd']         = os.path.join(icondir, 'cd_video.png')
        self.cdimages ['burn']        = os.path.join(icondir, 'cd_burn.png')
        self.cdimages ['cdrip']       = os.path.join(icondir, 'cd_rip.png')
        self.cdimages ['mixed']       = os.path.join(icondir, 'cd_mixed.png')

    def draw(self, (type, object), x, osd):
        image = self.cdimages['empty_cdrom']
        width = 0
        for media in config.REMOVABLE_MEDIA:
            image = self.cdimages['empty_cdrom']
            if media.type == 'empty_cdrom':
                image = self.cdimages['empty_cdrom']
            if media.type and self.cdimages.has_key(media.type):
                image = self.cdimages[media.type]
            else:
                image = self.cdimages['mixed']

            width += osd.draw_image(image, (x+width, osd.y + 10, -1, -1))[0] + 10
        if width:
            width -= 10
        return width

   
