# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Commmercial removal option for the item menu
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
import logging
logger = logging.getLogger("freevo.video.plugins.removecommercials")

__author__ = 'Andrew Jeffery <short_rz at internode.on.net>'
__revision__ = '$Rev$'.split()[1]

import os
import plugin
import config

from sets import Set

from video.commdetectclient import initCommDetectJob, queueIt, listJobs, connectionTest

class PluginInterface(plugin.ItemPlugin):
    """
    An item menu plugin to remove commercials from video files

    Activate:
    plugin.activate('video.removecommercials')
    """

    def __init__(self):
        plugin.ItemPlugin.__init__(self)

    def actions(self, item):
        self.video = item
        mplayer_suffixes = Set(config.VIDEO_MPLAYER_SUFFIX)
        video_suffixes = mplayer_suffixes | (mplayer_suffixes - Set(config.VIDEO_XINE_SUFFIX))

        # DirItems have a 'type' attribute rather than a 'mode' so fail gracefully
        try:
            # Checking if it's a video file
            if item.mode == 'file' and os.path.splitext(item.filename)[1][1:] in video_suffixes:
                return [ (self.comm_detect, 'Remove Commercials') ]
        except AttributeError:
            pass

        return []

    def comm_detect(self, arg=None, menuw=None):
        """Commercial detection method.

        Code copied from src/helpers/recordserver.py
        """
        video = self.video
        (result, response) = connectionTest('connection test')
        if result:
            (status, idnr) = initCommDetectJob(video.filename)
            (status, output) = listJobs()
            logger.info(output)
            (status, output) = queueIt(idnr, True)
            logger.info(output)
        else:
            logger.info('commdetect server not running')
        menuw.delete_menu(arg, menuw)
