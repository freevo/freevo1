# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Radio player plugin for radio
# -----------------------------------------------------------------------
# $Id$
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

"""
Radio player plugin for radio
"""
import logging
logger = logging.getLogger("freevo.audio.plugins.radioplayer")

import time, os
import string
import re
import thread

import config     # Configuration handler. reads config file.
import rc         # To post events
import util       # Various utilities
import plugin
from event import *


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
        plugin.register(RadioPlayer(), plugin.AUDIO_PLAYER, True)



class RadioPlayer:
    """
    Radio player control class

    @ivar mode: current mode of the radio
    @ivar name: name if the plug-in
    @ivar event_context: mode of the application
    @ivar app: None
    @ivar starttime: counter
    """
    def __init__(self):
        self.mode = 'idle'
        self.name = 'radioplayer'
        self.event_context = 'audio'
        self.app = None
        self.starttime = 0


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        try:
            logger.log( 9, 'url=%r', item.url)
            logger.log( 8, 'item.__dict__=%r', item.__dict__)
        except Exception, why:
            logger.debug('%s', why)
        if item.url.startswith('radio://'):
            logger.log( 9, '%r good', item.url)
            return 2
        logger.log( 9, '%r unplayable', item.url)
        return 0


    def play(self, item, playerGUI):
        """
        play a radioitem with radio player
        """
        logger.debug('%s.play(item=%r, playerGUI=%r)', self.__module__, item, playerGUI)
        self.playerGUI = playerGUI
        self.item = item
        #self.item.elapsed = 0
        self.starttime = time.time()

        try:
            logger.debug('play %r', self.item.station)
        except AttributeError:
            return 'Cannot play with RadioPlayer - no station'

        self.mode = 'play'

        mixer = plugin.getbyname('MIXER')
        if mixer:
            mixer_vol = config.MIXER_VOLUME_RADIO_IN
            mixer.setLineinVolume(mixer_vol)
            mixer.setIgainVolume(mixer_vol)
            mixer.setMicVolume(mixer_vol)
        logger.debug('RadioPlayer mixer is %s', mixer)

        if config.RADIO_CMD.find('ivtv-radio') >= 0:
            # IVTV cards
            logger.debug('%s -f %s &', config.RADIO_CMD, self.item.station)
            os.system('%s -f %s &' % (config.RADIO_CMD, self.item.station))
        else:
            # BTTV cards
            logger.debug('%s', config.RADIO_CMD_START%self.item.station)
            os.system('%s' % (config.RADIO_CMD_START % self.item.station))
        #thread.start_new_thread(self.__update_thread, ())

        rc.add_app(self)
        rc.post_event(PLAY_START)
        return None


    def stop(self):
        """
        Stop mplayer and set thread to idle
        """
        logger.debug('Radio Player Stop')
        self.mode = 'stop'
        mixer = plugin.getbyname('MIXER')
        if mixer:
            mixer.setLineinVolume(0)
            mixer.setMicVolume(0)
            mixer.setIgainVolume(0) # Input on emu10k cards.
        else:
            logger.warning('Radio Player failed to find a mixer')

        if config.RADIO_CMD.find('ivtv-radio') >= 0:
            # IVTV cards
            os.system('killall -9 aplay')
        else:
            # BTTV cards
            logger.debug('%s', config.RADIO_CMD_STOP)
            os.system('%s' % config.RADIO_CMD_STOP)

        rc.post_event(PLAY_END)
        rc.remove_app(self)


    def is_playing(self):
        logger.log( 9, 'Radio Player IS PLAYING?')
        return self.mode == 'play'


    def refresh(self):
        logger.log( 8, 'Radio Player refresh')
        #self.item.elapsed = int(time.time() - self.starttime)
        #self.item.elapsed = ''
        self.playerGUI.refresh()


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for mplayer control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        logger.debug('Radio Player event handler %s', event)
        if event in (STOP, PLAY_END, USER_END):
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
