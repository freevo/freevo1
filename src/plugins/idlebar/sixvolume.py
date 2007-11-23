# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# sixvolume.py - IdleBarplugin for showing volume for 5.1 Surround
# -----------------------------------------------------------------------
# $Id$
#
# Author: Michael Beal <mlbeal2003@yahoo.com>
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
import os, pygame

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config

class PluginInterface(IdleBarPlugin):
    """
    This plugin shows the current volume level on the idlebar.
    Activate with:
    plugin.activate('idlebar.volume.Volume', level=0)
    """
    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.volume'

        self.barimg1  = os.path.join(config.ICON_DIR, 'status/volbar1.png')
        self.barimg2  = os.path.join(config.ICON_DIR, 'status/volbar2.png')
        self.barimg3  = os.path.join(config.ICON_DIR, 'status/volbar3.png')
        self.barimg4  = os.path.join(config.ICON_DIR, 'status/volbar4.png')
        self.outimg   = os.path.join(config.ICON_DIR, 'status/volume_out_multi.png')
        self.muteimg  = os.path.join(config.ICON_DIR, 'status/volume_mute_multi.png')
        self.cacheimg = {}
        self.muted    = False
        self.pcmvolume   = -1
        self.survolume   = -1
        self.ctrvolume   = -1
        self.lfevolume   = -1

    def getimage(self, image, osd, cache=False):
        if image.find(config.ICON_DIR) == 0 and image.find(osd.settings.icon_dir) == -1:
            new_image = os.path.join(osd.settings.icon_dir, image[len(config.ICON_DIR)+1:])
            if os.path.isfile(new_image):
                image = new_image
        if cache:
            if image not in self.cacheimg.keys():
                self.cacheimg[image] = pygame.image.load(image)
            return self.cacheimg[image]

        return pygame.image.load(image)

    def draw(self, (type, object), x, osd):
        mixer = plugin.getbyname('MIXER')
        w = 0
        if mixer:
            muted = mixer.getMuted()
            pcmvol = (float(mixer.getPcmVolume())/100)
            survol = (float(mixer.getSurVolume())/100)
            ctrvol = (float(mixer.getCtrVolume())/100)
            lfevol = (float(mixer.getLfeVolume())/100)
            if muted != self.muted or pcmvol != self.pcmvolume or survol != self.survolume or ctrvol != self.ctrvolume or lfevol != self.lfevolume:
                self.muted  = muted
                self.pcmvolume   = pcmvol
                self.survolume   = survol
                self.ctrvolume   = ctrvol
                self.lfevolume   = lfevol
                if muted:
                    self.muted = muted
                    volout = self.getimage(self.muteimg, osd, True)
                    self.cacheimg['cached'] = volout
                else:
                    self.pcmvolume   = pcmvol
                    self.survolume   = survol
                    self.ctrvolume   = ctrvol
                    self.lfevolume   = lfevol
                    volbar1 = self.getimage(self.barimg1, osd, True)
                    volbar2 = self.getimage(self.barimg2, osd, True)
                    volbar3 = self.getimage(self.barimg3, osd, True)
                    volbar4 = self.getimage(self.barimg4, osd, True)
                    volout = self.getimage(self.outimg, osd)
                    w,h = volout.get_size()
                    volout.blit( volbar1, (0,(h-(h*pcmvol))), (0, (h-(h*pcmvol)), w, h ) )
                    volout.blit( volbar2, (0,(h-(h*survol))), (0, (h-(h*survol)), w, h ) )
                    volout.blit( volbar3, (0,(h-(h*ctrvol))), (0, (h-(h*ctrvol)), w, h ) )
                    volout.blit( volbar4, (0,(h-(h*lfevol))), (0, (h-(h*lfevol)), w, h ) )
                    self.cacheimg['cached'] = volout
            else:
                volout = self.getimage('cached', osd, True)

            w =  osd.drawimage(volout, (x, osd.y + 10, -1, -1) )[0]
        return w

    def update(self):
        bar = plugin.getbyname('idlebar')
        if bar: bar.poll()
