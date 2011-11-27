# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Forces the aspect ratio to the detected one.
# -----------------------------------------------------------------------
# $Id
#
# Notes: Forces the aspect ratio to the detected one by Freevo.
#
# Changelog
#
# 1.0
#
#     Initial release
#
# Todo
#
#    Add a menu to select an aspect ratio manually
#
# Activate by adding the following to local_conf.py:
#
# | plugin.activate('video.mplayer_autoaspect')
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
# with self program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.video.plugins.mplayer_autoaspect")

import config
import plugin
import event as em

class PluginInterface(plugin.ItemPlugin):
    """
    Forces the aspect ratio to the detected one by Freevo.
    To activate add this to your local_conf.py:

    | plugin.activate('video.mplayer_autoaspect')
    """

    def __init__(self):
        """ Initialise the mplayer_autoaspect PluginInterface """
        plugin.ItemPlugin.__init__(self)
        self.plugin_name = 'mplayer_autoaspect'

        self.args_def = config.MPLAYER_ARGS_DEF
        self.player = None


    def actions(self, item):
        """ Perform the action add -aspect to the mplayer command line """
        config.MPLAYER_ARGS_DEF = self.args_def

        for p in plugin.getbyname(plugin.VIDEO_PLAYER, True):
            if config.VIDEO_PREFERED_PLAYER == p.name:
                self.player = p

        if item.type == 'video' and self.player.name == 'mplayer':
            ratio = item['mplayer_aspect']
            if ratio:
                config.MPLAYER_ARGS_DEF = self.args_def + ' -aspect ' + ratio
                logger.debug('Setting movie aspect to: %s', ratio)

        return []
