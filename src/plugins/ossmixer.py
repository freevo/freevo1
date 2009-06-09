# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# The oss mixer interface for freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# I propose this could replace 'mixer.py' when it's been tested adequately. It
# should also work unchanged under BSD.
#
# Last note, here is the documentation again:
# http://www.python.org/doc/current/lib/mixer-device-objects.html
#
# And to activate:
# plugin.remove('mixer')
# plugin.activate('ossmixer')
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


"""For manipulating the mixer.
"""

import struct
import os

import config
import plugin
import rc
from event import *
import dialog

import ossaudiodev


class PluginInterface(plugin.DaemonPlugin):
    """
    The OSS mixer interface for Freevo

    Last note, here is the documentation again:
    http://www.python.org/doc/current/lib/mixer-device-objects.html

    And to activate:
    | plugin.remove('mixer')
    | plugin.activate('ossmixer')
    """

    SOUND_MIXER_LINE = 7
    SOUND_MASK_LINE = 64

    def __init__(self):
        self.mixfd = None
        self.muted = 0

        # If you're using ALSA or something and you don't set the mixer,
        # why are we trying to open it?
        if config.MIXER_DEVICE:
            try:
                self.mixfd = ossaudiodev.openmixer(config.MIXER_DEVICE)
            except IOError:
                self.reason = 'Couldn\'t open mixer "%s"' % config.MIXER_DEVICE
                return

        # init here
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'MIXER'

        self.default_step = config.MIXER_VOLUME_STEP

        if 0:
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
            return True

        elif event == MIXER_VOLDOWN:
            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.decMainVolume(step)

            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.decPcmVolume(step)

            dialog.show_volume(self.getVolume(), False)
            return True

        elif event == MIXER_MUTE:
            if self.getMuted() == 1:
                self.setMuted(0)
            else:
                self.setMuted(1)

            dialog.show_volume(self.getVolume(), self.getMuted())
            return True

        return False



    def _setVolume(self, device, volume):
        if self.mixfd and (self.mixfd.controls() & (1 << device)):
            if volume < 0:
                volume = 0
            if volume > 100:
                volume = 100
            self.mixfd.set(device, (volume,volume))

    def getMuted(self):
        return(self.muted)

    def setMuted(self, mute):
        self.muted = mute
        if config.MIXER_MAJOR_CTRL == 'VOL':
            if mute == 1:
                self._setVolume(ossaudiodev.SOUND_MIXER_VOLUME, 0)
            else:
                self._setVolume(ossaudiodev.SOUND_MIXER_VOLUME, self.mainVolume)
        elif config.MIXER_MAJOR_CTRL == 'PCM':
            if mute == 1:
                self._setVolume(ossaudiodev.SOUND_MIXER_PCM, 0)
            else:
                self._setVolume(ossaudiodev.SOUND_MIXER_PCM, self.pcmVolume)

    def getVolume(self):
        if config.MIXER_MAJOR_CTRL == 'VOL':
            return self.mainVolume
        elif config.MIXER_MAJOR_CTRL == 'PCM':
            return self.pcmVolume

    def getMainVolume(self):
        return self.mainVolume

    def setMainVolume(self, volume):
        self.mainVolume = volume
        self._setVolume(ossaudiodev.SOUND_MIXER_VOLUME, self.mainVolume)

    def incMainVolume(self, step=5):
        self.mainVolume += step
        if self.mainVolume > 100:
            self.mainVolume = 100
        self._setVolume(ossaudiodev.SOUND_MIXER_VOLUME, self.mainVolume)

    def decMainVolume(self, step=5):
        self.mainVolume -= step
        if self.mainVolume < 0:
            self.mainVolume = 0
        self._setVolume(ossaudiodev.SOUND_MIXER_VOLUME, self.mainVolume)

    def getPcmVolume(self):
        return self.pcmVolume

    def setPcmVolume(self, volume):
        self.pcmVolume = volume
        self._setVolume(ossaudiodev.SOUND_MIXER_PCM, volume)

    def incPcmVolume(self, step=5):
        self.pcmVolume += step
        if self.pcmVolume > 100:
            self.pcmVolume = 100
        self._setVolume( ossaudiodev.SOUND_MIXER_PCM, self.pcmVolume )

    def decPcmVolume(self, step=5):
        self.pcmVolume -= step
        if self.pcmVolume < 0:
            self.pcmVolume = 0
        self._setVolume( ossaudiodev.SOUND_MIXER_PCM, self.pcmVolume )

    def setLineinVolume(self, volume):
        if config.MIXER_CONTROL_ALL:
            self.lineinVolume = volume
            self._setVolume(ossaudiodev.SOUND_MIXER_LINE, volume)

    def getLineinVolume(self):
        return self.lineinVolume

    def setMicVolume(self, volume):
        if config.MIXER_CONTROL_ALL:
            self.micVolume = volume
            self._setVolume(ossaudiodev.SOUND_MIXER_MIC, volume)

    def setIgainVolume(self, volume):
        if config.MIXER_CONTROL_ALL:
            if volume > 100:
                volume = 100
            elif volume < 0:
                volume = 0
            self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def getIgainVolume(self):
        return self.igainVolume

    def decIgainVolume(self, step=5):
        self.igainVolume -= step
        if self.igainVolume < 0:
            self.igainVolume = 0
        self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def incIgainVolume(self, step=5):
        self.igainVolume += step
        if self.igainVolume > 100:
            self.igainVolume = 100
        self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def setOgainVolume(self, volume):
        if volume > 100:
            volume = 100
        elif volume < 0:
            volume = 0
        self.ogainVolume = volume
        self._setVolume(ossaudiodev.SOUND_MIXER_IGAIN, volume)

    def reset(self):
        if config.MIXER_CONTROL_ALL:
            self.setLineinVolume(0)
            self.setMicVolume(0)
            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.setPcmVolume(config.MIXER_VOLUME_MAX)
            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.setMainVolume(config.MIXER_VOLUME_MAX)

        self.setIgainVolume(0) # SB Live input from TV Card.
