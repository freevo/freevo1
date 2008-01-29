# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dvdimage.py - A video plugin handling images as dvd
# Author: Viggo Fredriksen <viggo@katatonic.org>
# -----------------------------------------------------------------------
# $Id$
#
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

# imports
import config, plugin, os, rc
from event  import *
from gui    import PopupBox

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin adds 'Play image as DVD' in the item menu for files with .iso
    and .img extensions. It simply creates a temporary symlink to the selected
    file, and passes this symlink as the --dvd-device to mplayer.

    Activate with:
    | plugin.activate('video.dvdimage')

    Remember to add .img and .iso to VIDEO_MPLAYER_SUFFIX found in
    share/freevo/freevo_config.py. Override this in your local_conf.py

    Usage:

    Select your image in the video menu, bring up the submenu and select
    <Play image as DVD>. You will be prompted for title, answer with numeric
    input.
    """

    def __init__(self):
        plugin.ItemPlugin.__init__(self)
        self.symlink = vfs.join(config.OVERLAY_DIR,'dvdlink')


    def actions(self, item):
        self.player = None
        for p in plugin.getbyname(plugin.VIDEO_PLAYER, True):
            if config.VIDEO_PREFERED_PLAYER == p.name:
                self.player = p

        if item.type == 'video' and self.player and self.player.name == 'mplayer':

            self.files = []
            self.item  = item
            if not item.files:
                return []

            fs = item.files.get()
            for f in fs:
                if f.endswith('.img') or f.endswith('.iso'):
                    self.files.append(f)

            if len(self.files)>0:
                return [ ( self.play_dvd , _('Play image as DVD')) ]

        return []

    def eventhandler(self, event, menuw=None, arg=None):
        try:
            if event in INPUT_ALL_NUMBERS:

                if self.selected == None:
                    self.selected = event.arg
                elif self.schapter == None:
                    self.schapter = event.arg

                if self.pop:
                    self.pop.destroy()
                    self.pop = None
                    rc.app(None)

                self.chapter()
        except: pass

    def chapter(self):
        if self.schapter == None:
            rc.app(self)
            rc.set_context('input')
            self.pop = PopupBox(_('Choose title to play. <1-9>'))
            self.pop.show()
        else:
            self.play()

    def play(self):
        if self.player and (self.selected-1) < len(self.files):

            self.item.network_play = False # prevents crash on my system
            self.item.url          = 'dvd://%s' % self.schapter
            self.item.mode         = 'dvd'
            self.item.filename     = self.symlink

            os.system('ln -sf  %s %s' % (self.files[self.selected-1],
                                         self.symlink) )
            self.player.play( [], self.item )

    def play_dvd(self, arg=None, menuw=None):
        self.schapter = None
        self.selected = None

        if len(self.files)>1:
            rc.app(self)
            rc.set_context('input')
            self.pop = PopupBox(_('Choose disc (%i discs available).' % len(self.files) ))
            self.pop.show()
        else:
            self.selected = 1
            self.chapter()
