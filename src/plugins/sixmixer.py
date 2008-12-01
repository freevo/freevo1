# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# sixmixer.py - A 6-channel volume control interface for freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Description:
#  Six-channel audio control for the Freevo Media Center Environment
#
# This program, as a drop in replacement for the original Freevo mixer,
# provides complete control of all six audio channels, more correctly;
# Front (Stereo), Surround (Stereo), Center (Mono) and LFE/Bass (Mono).
# The Front and Surround channels are not balance adjustable.
#
# Notes:
# By default, sixmixer controls all audio system wide via the ALSA mixer
# program: amixer.  I chose amixer due to it's wide ranging use within
# the Linux community.  Practically ALL modern Linux distros have some
# method of handling ALSA device access either through OSS => ALSA
# wrappers or the ALSA system itself.
#
# Todo:
#
# Usage: Simply add the following lines to your local_conf.py:
#    plugin.remove('mixer')
#    plugin.activate('sixmixer')
#    plugin.activate('idlebar.sixvolume')
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

import os

import config
import rc
import plugin
from event import *


class PluginInterface(plugin.DaemonPlugin):

    def __init__(self):
        self.muted = 0

        # init here
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'MIXER'

        # Clear basic variables
        self.mainVolume   = 0
        self.pcmVolume    = 0
        self.surVolume    = 0
        self.ctrVolume    = 0
        self.lfeVolume    = 0
        self.NoAdjust     = 0
        self.CalcVol      = 0
        self.VolSpan      = 0
        self.MaxStep      = 0
        self.ActStep      = 0
        self.StepFactor   = 0
        self.CalcVolList  = []

        self.setMainVolume(config.MAX_VOLUME)
        self.setPcmVolume(config.DEFAULT_PCM_VOLUME)
        self.setSurVolume(config.DEFAULT_SUR_VOLUME)
        self.setCtrVolume(config.DEFAULT_CTR_VOLUME)
        self.setLfeVolume(config.DEFAULT_LFE_VOLUME)


    def eventhandler(self, event = None, menuw=None, arg=None):
        """
        eventhandler to handle the VOL events
        """
        if event == MIXER_VOLUP:
            if not self.muted and self.NoAdjust >= 0:
                self.incPcmVolume(event.arg)
                self.incSurVolume(event.arg)
                self.incCtrVolume(event.arg)
                self.incLfeVolume(event.arg)
                if self.NoAdjust > 0:
                    self.NoAdjust = 0
                self.ShowVolume(event.arg)
            return True

        elif event == MIXER_VOLDOWN:
            if not self.muted and self.NoAdjust <= 0:
                self.decPcmVolume(event.arg)
                self.decSurVolume(event.arg)
                self.decCtrVolume(event.arg)
                self.decLfeVolume(event.arg)
                if self.NoAdjust < 0:
                    self.NoAdjust = 0
                self.ShowVolume(event.arg)
            return True

        elif event == MIXER_SUR_VOLUP:
            self.incSurVolume(event.arg)
            rc.post_event(Event(OSD_MESSAGE, arg=_('Surround: %s%%') % self.getSurVolume()))
            return True

        elif event == MIXER_SUR_VOLDOWN:
            self.decSurVolume(event.arg)
            rc.post_event(Event(OSD_MESSAGE, arg=_('Surround: %s%%') % self.getSurVolume()))
            return True

        elif event == MIXER_CTR_VOLUP:
            self.incCtrVolume(event.arg)
            rc.post_event(Event(OSD_MESSAGE, arg=_('Center: %s%%') % self.getCtrVolume()))
            return True

        elif event == MIXER_CTR_VOLDOWN:
            self.decCtrVolume(event.arg)
            rc.post_event(Event(OSD_MESSAGE, arg=_('Center: %s%%') % self.getCtrVolume()))
            return True

        elif event == MIXER_LFE_VOLUP:
            self.incLfeVolume(event.arg)
            rc.post_event(Event(OSD_MESSAGE, arg=_('LFE: %s%%') % self.getLfeVolume()))
            return True

        elif event == MIXER_LFE_VOLDOWN:
            self.decLfeVolume(event.arg)
            rc.post_event(Event(OSD_MESSAGE, arg=_('LFE: %s%%') % self.getLfeVolume()))
            return True

        elif event == MIXER_MUTE:
            if self.getMuted() == 1:
                rc.post_event(Event(OSD_MESSAGE, arg=_('Volume: %s%%') % self.getVolume()))
                self.setMuted(0)
            else:
                rc.post_event(Event(OSD_MESSAGE, arg=_('Mute')))
                self.setMuted(1)
            return True

        return False


    def _setVolume(self, ctrl_name, volume, mute):
        if volume < 0:
            volume = 0
        if volume > 100:
            volume = 100
        # Yes, there's probably a better way to do this but this is, by far, the safest.
        os.system('amixer -q -c 0 sset %s %s %s' % (ctrl_name, (str(volume)+"%"), mute))

    def getMuted(self):
        return(self.muted)

    def setMuted(self, mute):
        self.muted = mute
        if mute == 1:
            self._setVolume('PCM', 0, 'mute')
            self._setVolume('Surround', 0, 'mute')
            self._setVolume('Center', 0, 'mute')
            self._setVolume('LFE', 0, 'mute')
        else:
            self._setVolume('PCM', self.pcmVolume, 'unmute')
            self._setVolume('Surround', self.surVolume, 'unmute')
            self._setVolume('Center', self.ctrVolume, 'unmute')
            self._setVolume('LFE', self.lfeVolume, 'unmute')

    def getVolume(self):
        return self.CalcVolume()

    def getMainVolume(self):
        return self.mainVolume

    def setMainVolume(self, volume):
        self.mainVolume = volume
        self._setVolume('Master', self.mainVolume, 'unmute')

    def incMainVolume(self, step=5):
        self.mainVolume += step
        if self.mainVolume >= 100:
            self.mainVolume = 100
            self.NoAdjust = -1
        self._setVolume('Master', self.mainVolume, 'unmute')

    def decMainVolume(self, step=5):
        self.mainVolume -= step
        if self.mainVolume <= 0:
            self.mainVolume = 0
            self.NoAdjust = 1
        self._setVolume('Master', self.mainVolume, 'unmute')

    def getPcmVolume(self):
        return self.pcmVolume

    def setPcmVolume(self, volume):
        self.pcmVolume = volume
        self._setVolume('PCM', self.pcmVolume, 'unmute')

    def incPcmVolume(self, step=5):
        self.pcmVolume += step
        if self.pcmVolume >= 100:
            self.pcmVolume = 100
            self.NoAdjust = -1
        self._setVolume('PCM', self.pcmVolume, 'unmute')

    def decPcmVolume(self, step=5):
        self.pcmVolume -= step
        if self.pcmVolume <= 0:
            self.pcmVolume = 0
            self.NoAdjust = 1
        self._setVolume('PCM', self.pcmVolume, 'unmute')

    def getSurVolume(self):
        return self.surVolume

    def setSurVolume(self, volume):
        self.surVolume = volume
        self._setVolume('Surround', self.surVolume, 'unmute')

    def incSurVolume(self, step=5):
        self.surVolume += step
        if self.surVolume >= 100:
            self.surVolume = 100
            self.NoAdjust = -1
        self._setVolume('Surround', self.surVolume, 'unmute')

    def decSurVolume(self, step=5):
        self.surVolume -= step
        if self.surVolume <= 0:
            self.surVolume = 0
            self.NoAdjust = 1
        self._setVolume('Surround', self.surVolume, 'unmute')

    def getLfeVolume(self):
        return self.lfeVolume

    def setLfeVolume(self, volume):
        self.lfeVolume = volume
        self._setVolume('LFE', self.lfeVolume, 'unmute')

    def incLfeVolume(self, step=5):
        self.lfeVolume += step
        if self.lfeVolume >= 100:
            self.lfeVolume = 100
            self.NoAdjust = -1
        self._setVolume('LFE', self.lfeVolume, 'unmute')

    def decLfeVolume(self, step=5):
        self.lfeVolume -= step
        if self.lfeVolume <= 0:
            self.lfeVolume = 0
            self.NoAdjust = 1
        self._setVolume('LFE', self.lfeVolume, 'unmute')

    def getCtrVolume(self):
        return self.ctrVolume

    def setCtrVolume(self, volume):
        self.ctrVolume = volume
        self._setVolume('Center', self.ctrVolume, 'unmute')

    def incCtrVolume(self, step=5):
        self.ctrVolume += step
        if self.ctrVolume >= 100:
            self.ctrVolume = 100
            self.NoAdjust = -1
        self._setVolume('Center', self.ctrVolume, 'unmute')

    def decCtrVolume(self, step=5):
        self.ctrVolume -= step
        if self.ctrVolume <= 0:
            self.ctrVolume = 0
            self.NoAdjust = 1
        self._setVolume('Center', self.ctrVolume, 'unmute')

    def reset(self):
        self.setMainVolume(config.MAX_VOLUME)
        self.setPcmVolume(config.DEFAULT_PCM_VOLUME)
        self.setSurVolume(config.DEFAULT_SUR_VOLUME)
        self.setCtrVolume(config.DEFAULT_CTR_VOLUME)
        self.setLfeVolume(config.DEFAULT_LFE_VOLUME)

    def CalcVolume(self, step=5):
        # Create a lis of our volumes
        self.CalcVolList = [self.getPcmVolume(),self.getSurVolume(),self.getCtrVolume(),self.getLfeVolume()]
        # Sort from low to high
        self.CalcVolList.sort()
        # Determine the total range between the high and low volumes
        self.VolSpan = float(self.CalcVolList[3]-self.CalcVolList[0])
        # Determine the maximum number of steps between max and min volumes
        self.MaxStep = float(100/step)
        # Determine the ACTUAL number of steps we can take
        self.ActStep = float((100-self.VolSpan)/step)
        # Decide how wide those steps can be
        self.StepFactor = float(self.MaxStep)/float(self.ActStep)
        # Calculate the volume to be displayed on screen
        # THIS IS ONLY A REFERENCE NUMBER!!!!  It does not
        # reflect an actual value but a general position based
        # on the mean.
        self.CalcVol = int(self.StepFactor*self.CalcVolList[0])
        return self.CalcVol

    def ShowVolume(self, step=5):
        ShowVol = self.CalcVolume()
        rc.post_event(Event(OSD_MESSAGE, arg=_('Volume: %s%%') % ShowVol))
