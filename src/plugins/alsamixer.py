# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# alsamixer.py - The ALSA mixer interface for freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# I propose this could replace 'mixer.py' when it's been tested adequately.
#
# And to activate:
#
# plugin.remove('mixer')
# plugin.activate('alsamixer')
#
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
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.plugins.alsamixer")


__version__="0.2"
__author__="Stephane Vaxelaire <svax@free.fr>"
__doc__="""For manipulating the mixer. alsamixer.py plugin that works with
the python-alsaaudio module (http://code.google.com/p/python-alsaaudio/).
"""

import struct
import os

import config
import plugin
import rc
from event import *
import dialog

import alsaaudio


class PluginInterface(plugin.DaemonPlugin):
    """
    Mixer for ALSA,. This plugin requires the alsaaudio module from
    http://sourceforge.net/projects/pyalsaaudio/. For Debian, install the
    python-alsaaudio package and you're all set.

    In addition to the plugin specific variables this plugin also uses the
    following general configuration variables:

    | MIXER_MAJOR_CTRL      = 'VOL' # Freevo takes control over one audio ctrl
    |                               # 'VOL', 'PCM' 'OGAIN' etc.
    | MIXER_MAJOR_MUTE_CTRL = 'PCM' # used in alsamixer.py, There are systems
    |                               # where volume and mute use different controls
    | MIXER_CONTROL_ALL     = 1     # Should Freevo take complete control of audio
    | MIXER_VOLUME_STEP     = 5     # Amount to increment the mixer volume
    | MIXER_VOLUME_MAX      = 90    # Set what you want maximum volume level to be.
    | MIXER_VOLUME_DEFAULT  = 40    # Set default volume level.
    """

    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        self.main_mixer = None
        self.pcm_mixer = None
        self.line_mixer = None
        self.mic_mixer = None
        self.sync_mixer = None
        self.muted = 0

        # If you're using ALSA or something and you don't set the mixer,
        # why are we trying to open it?
        try:
            self.main_mixer = alsaaudio.Mixer(config.ALSA_MIXER_NAME, 0, config.ALSA_CARDID)
        except alsaaudio.ALSAAudioError:
            self.init_failed('Couldn\'t open mixer "%s"' % config.ALSA_MIXER_NAME)
            return
        try:
            self.pcm_mixer = alsaaudio.Mixer(config.ALSA_PCMMIXER_NAME, 0, config.ALSA_CARDID)
        except alsaaudio.ALSAAudioError:
            self.init_failed( 'Couldn\'t open mixer "%s"' % config.ALSA_PCMMIXER_NAME)
            return
        try:
            self.line_mixer = alsaaudio.Mixer(config.ALSA_LINEMIXER_NAME, 0, config.ALSA_LINE_CARDID)
        except alsaaudio.ALSAAudioError:
            print 'Couldn\'t open Line-In mixer "%s"' % config.ALSA_LINEMIXER_NAME
            
        try:
            self.mic_mixer = alsaaudio.Mixer(config.ALSA_MICMIXER_NAME, 0, config.ALSA_CARDID)
        except alsaaudio.ALSAAudioError:
            print 'Couldn\'t open Mic mixer "%s"' % config.ALSA_MICMIXER_NAME
            

        try:
            self.sync_mixer = alsaaudio.Mixer(config.ALSA_SYNCMIXER_NAME, 0, config.ALSA_CARDID)
        except alsaaudio.ALSAAudioError:
            print 'Couldn\'t open sync mixer "%s"' % config.ALSA_SYNCMIXER_NAME


        # init here
        
        self.plugin_name = 'MIXER'

        self.default_step = config.MIXER_VOLUME_STEP

        self.mainVolume   = 0
        self.pcmVolume    = 0
        self.lineinVolume = 0
        self.micVolume    = 0
        self.igainVolume  = 0
        self.ogainVolume  = 0

        if config.MIXER_MAJOR_CTRL == 'VOL':
            self.setMainVolume(config.MIXER_VOLUME_DEFAULT)
            if config.MIXER_CONTROL_ALL:
                self.setPcmVolume(config.MIXER_VOLUME_MAX)
                self.setOgainVolume(config.MIXER_VOLUME_MAX)
        elif config.MIXER_MAJOR_CTRL == 'PCM':
            self.setPcmVolume(config.MIXER_VOLUME_DEFAULT)
            if config.MIXER_CONTROL_ALL:
                self.setMainVolume(config.MIXER_VOLUME_MAX)
                self.setOgainVolume(config.MIXER_VOLUME_MAX)
        else:
            _debug_("No appropriate audio channel found for mixer")

        if config.MIXER_CONTROL_ALL:
            self.setLineinVolume(0)
            self.setMicVolume(0)


    def config(self):
        '''config is called automatically, for default settings run:
        freevo plugins -i alsamixer
        '''
        return [
            ('ALSA_CARDID', 0, 'Alsa Card id'),
            ('ALSA_LINE_CARDID', 0, 'Alsa Line Card id'),
            ('ALSA_MIXER_NAME', 'Master', 'Alsa Mixer Name'),
            ('ALSA_PCMMIXER_NAME', 'PCM', 'Alsa PCM Mixer Name'),
            ('ALSA_LINEMIXER_NAME', 'Line', 'Alsa Line Mixer Name'),
            ('ALSA_MICMIXER_NAME', 'Mic', 'Alsa Mic Mixer Name'),
            ('ALSA_SYNCMIXER_NAME', 'Master Surround', 'Alsa Sync Mixer Name'),
            ('ALSA_SYNCMIXER', False, 'Whether to control the Alsa Sync Mixer'),
        ]


    def eventhandler(self, event=None, menuw=None, arg=None):
        """
        eventhandler to handle the VOL events
        """
        if event in (MIXER_VOLUP, MIXER_VOLDOWN):
            step = event.arg
            if not isinstance(step, int):
                _debug_("%s event type '%s' is not 'int'" % (event, step), DWARNING)
                step = self.default_step

        # Handle volume control
        if event == MIXER_VOLUP:
            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.incMainVolume(step)

            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.incPcmVolume(step)

            dialog.show_volume(self.getVolume(), False)
            rc.post_event(Event('MIXER_VOLUME_INFO', arg='%s' % self.getVolume()))

            if config.ALSA_SYNCMIXER:
                self.setSyncVolume(self.getVolume())
            return True

        elif event == MIXER_VOLDOWN:
            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.decMainVolume(step)

            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.decPcmVolume(step)

            dialog.show_volume(self.getVolume(), False)
            rc.post_event(Event('MIXER_VOLUME_INFO', arg='%s' % self.getVolume()))

            if config.ALSA_SYNCMIXER:
                self.setSyncVolume(self.getVolume())
            return True

        elif event == MIXER_MUTE:
            if self.getMuted() == 1:
                rc.post_event(Event('MIXER_VOLUME_INFO', arg='%s' % self.getVolume()))
                self.setMuted(0)

            else:
                rc.post_event(Event('MIXER_MUTE_INFO'))
                self.setMuted(1)

            dialog.show_volume(self.getVolume(), self.getMuted())
            return True

        return False


    def _setVolume(self, device, volume):
        if device:
            if volume < 0:
                volume = 0
            if volume > 100:
                volume = 100
            if device==self.line_mixer:
                device.setvolume(volume, 0)
            else:
                device.setvolume(volume)

    def getMuted(self):
        return(self.muted)

    def setMuted(self, mute):
        self.muted = mute
        if config.MIXER_MAJOR_MUTE_CTRL == 'VOL':
            if mute == 1:
                self.main_mixer.setmute(1)
            else:
                self.main_mixer.setmute(0)
        elif config.MIXER_MAJOR_MUTE_CTRL == 'PCM':
            if mute == 1:
                self.pcm_mixer.setmute(1)
            else:
                self.pcm_mixer.setmute(0)

    def getVolume(self):
        if config.MIXER_MAJOR_CTRL == 'VOL':
            return self.mainVolume
        elif config.MIXER_MAJOR_CTRL == 'PCM':
            return self.pcmVolume

    def getMainVolume(self):
        return self.mainVolume

    def setMainVolume(self, volume):
        self.mainVolume = volume
        self._setVolume(self.main_mixer, self.mainVolume)

    def incMainVolume(self, step=5):
        self.mainVolume += step
        if self.mainVolume > 100:
            self.mainVolume = 100
        self._setVolume(self.main_mixer, self.mainVolume)

    def decMainVolume(self, step=5):
        self.mainVolume -= step
        if self.mainVolume < 0:
            self.mainVolume = 0
        self._setVolume(self.main_mixer, self.mainVolume)

    def getPcmVolume(self):
        return self.pcmVolume

    def setPcmVolume(self, volume):
        self.pcmVolume = volume
        self._setVolume(self.pcm_mixer, volume)

    def setSyncVolume(self, volume):
        self._setVolume(self.sync_mixer, volume)

    def incPcmVolume(self, step=5):
        self.pcmVolume += step
        if self.pcmVolume > 100:
            self.pcmVolume = 100
        self._setVolume(self.pcm_mixer, self.pcmVolume)

    def decPcmVolume(self, step=5):
        self.pcmVolume -= step
        if self.pcmVolume < 0:
            self.pcmVolume = 0
        self._setVolume(self.pcm_mixer, self.pcmVolume)

    def setLineinVolume(self, volume):
        if config.MIXER_CONTROL_ALL and self.line_mixer:
            self.lineinVolume = volume
            self._setVolume(self.line_mixer, volume)

    def getLineinVolume(self):
        return self.lineinVolume

    def setMicVolume(self, volume):
        if config.MIXER_CONTROL_ALL and self.mic_mixer:
            self.micVolume = volume
            self._setVolume(self.mic_mixer, volume)

    def setIgainVolume(self, volume):
        if config.MIXER_CONTROL_ALL:
            if volume > 100:
                volume = 100
            elif volume < 0:
                volume = 0
            #self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def getIgainVolume(self):
        return self.igainVolume

    def decIgainVolume(self, step=5):
        self.igainVolume -= step
        if self.igainVolume < 0:
            self.igainVolume = 0
        #self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def incIgainVolume(self, step=5):
        self.igainVolume += step
        if self.igainVolume > 100:
            self.igainVolume = 100
        #self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def setOgainVolume(self, volume):
        if volume > 100:
            volume = 100
        elif volume < 0:
            volume = 0
        self.ogainVolume = volume
        #self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def reset(self):
        if config.MIXER_CONTROL_ALL:
            self.setLineinVolume(0)
            self.setMicVolume(0)
            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.setPcmVolume(config.MIXER_VOLUME_DEFAULT)
            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.setMainVolume(config.MIXER_VOLUME_DEFAULT)

        self.setIgainVolume(0) # SB Live input from TV Card.
