# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# xmradioplayer.py - the Freevo XmRadioplayer plugin for radio
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


import time, os
import string
import re
import thread

import config     # Configuration handler. reads config file.
import util       # Various utilities
import plugin

from event import *
from mplayer import MPlayerApp


class PluginInterface(plugin.Plugin):
    """
    This is the player plugin for the radio. Basically it tunes all the
    radio stations set in the radio plugin and does the interaction
    between the radio command line program and freevo. please see the
    audio.radio plugin for setup information  

    """
    def __init__(self):
        plugin.Plugin.__init__(self)

        # register it as the object to play audio
        plugin.register(XmRadioPlayer(), plugin.AUDIO_PLAYER, True)

class XmRadioPlayer:

    def __init__(self):
        self.mode = 'idle'
        self.name = 'xmradioplayer'
        self.app_mode = 'audio'
        self.app = None
        self.starttime = 0

    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        if item.url.startswith('http://'):
            return 2
        return 0


    def play(self, item, playerGUI):
        """
        play a radioitem with radio player
        """
        self.playerGUI = playerGUI
        self.item = item
        self.item.elapsed = 0
        self.starttime = time.time()

        self.mode    = 'play'
        mixer = plugin.getbyname('MIXER')
        if mixer:
            mixer.setLineinVolume(config.TV_IN_VOLUME)
            mixer.setIgainVolume(config.TV_IN_VOLUME)
            mixer.setMicVolume(config.TV_IN_VOLUME)
        else:
            print 'Xm Radio Player failed to find a mixer'
        cmd=('%s -cache 100 -playlist %s' % (config.XM_CMD, self.item.url))
        print(cmd)
        self.app = MPlayerApp(cmd, self)
        return None


    def stop(self):
        """
        Stop mplayer
        """
        self.app.stop('quit\n')


    def is_playing(self):
        self.item.elapsed = int(time.time() - self.starttime)
        return self.app.isAlive()


    def refresh(self):
        self.playerGUI.refresh()


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for mplayer control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        print 'Radio Player event handler %s' % event
        if event in ( STOP, PLAY_END, USER_END ):
            self.playerGUI.stop()
            return self.item.eventhandler(event)

        else:
            # everything else: give event to the items eventhandler
            return self.item.eventhandler(event)

    def __update_thread(self):
        """
        OSD update thread
        """
        while self.is_playing():
            self.refresh()
            time.sleep(0.3)

