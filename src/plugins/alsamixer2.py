# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# alsamixer2.py - An ALSA mixer interface for freevo.
# -----------------------------------------------------------------------
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

import config
import plugin
import rc
from event import *

import alsaaudio

#
# Indices into the ALSAMIXER2_CTRLS tuples
#
__CTRL_NAME__      = 0
__CARD_NAME__      = 1
__DEFAULT_VOLUME__ = 2
__MIN_VOLUME__     = 3
__MAX_VOLUME__     = 4

class PluginInterface(plugin.DaemonPlugin):
    """
    Another mixer for ALSA. This plugin requires the alsaaudio module from
    http://sourceforge.net/projects/pyalsaaudio/. For Debian, install the
    python-alsaaudio package and you're all set.

    The plugin uses the following configuration variables, which need to be
    defined in local_conf.py:

    | ALSAMIXER2_MAIN_CTRL = <control name>
    |     This is the mixer control that the plugin will use for handling volume
    |     (up and down) events. The control name needs to be a string as returned
    |     by 'amixer scontrols', i.e., 'PCM', 'Vol', or such.
    |     If this variable is not set, the first entry in the controls list (see
    |     below) will be used.
    |
    | ALSAMIXER2_MUTE_CTRL = <control name>
    |     This is the mixer control that the plugin will use for handling mute
    |     events. Some systems use different controls for volume and muting.
    |     If this variable is not set, the main control will be used for muting.
    |
    | ALSAMIXER2_CTRLS = [
    |     ( <control name>, <card name>, <default vol>, <min vol>, <max vol> ),
    |     ...
    | ]

    This is a list of mixer controls that the plugin will use. Each entry of
    the list represent one control and contains the following items:
        - <control name>  The name of this mixer control.
        - <card name>     The name of the card that this control lives on. Use
                          something like 'hw:0'. To use the default card, use
                          'default' or leave it empty ('').
        - <default vol>   Default volume for this control. The plugin will set
                          this control to this value upon initialization if the
                          value is >= 0,
        - <min vol>       Minimum volume. This is the minimum volume that can be
                          reached with 'volume down' events. This item makes only
                          sense for the main control and can be omitted for other
                          controls.
        - <max vol>       Maximum volume. This is the maximum volume that can be
                          reached with 'volume up' events. This item makes only
                          sense for the main control and can be omitted for other
                          controls.

    Example:
    | ALSAMIXER2_MAIN_CTRL = 'PCM'
    | ALSAMIXER2_MUTE_CTRL = 'Headphone'
    | ALSAMIXER2_CTRLS = [
    |    ('PCM',       'default', 50, 0, 100),
    |    ('Headphone', 'default', -1),
    | ]
    """

    __author__        = 'Juerg Haefliger'
    __author_email__  = 'Juerg Haefliger <juergh at gmail.com>'
    __version__       = '0.0.2'

    def __init__(self):
        """
        Initialise the Alsa Mixer 2 plug-in
        """
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'MIXER'

        #
        # Set the main and mute mixer control names
        #
        try:
            main_ctrl_name = config.ALSAMIXER2_MAIN_CTRL
        except NameError:
            main_ctrl_name = None
        try:
            mute_ctrl_name = config.ALSAMIXER2_MUTE_CTRL
        except NameError:
            mute_ctrl_name = None

        #
        # The main and mute mixer controls
        #
        self.main_ctrl = None
        self.main_ctrl_min = 0
        self.main_ctrl_max = 100
        self.mute_ctrl = None

        #
        # Open all mixer controls, identify the main and mute mixer controls
        # and and set the default volumes
        #
        ctrl = None
        for attr in config.ALSAMIXER2_CTRLS:
            # Open the mixer control
            try:
                if attr[__CARD_NAME__] == '':
                    ctrl = alsaaudio.Mixer(attr[__CTRL_NAME__])
                else:
                    ctrl = alsaaudio.Mixer(attr[__CTRL_NAME__], 0,
                                           attr[__CARD_NAME__])
            except alsaaudio.ALSAAudioError:
                print 'Failed to open mixer control "%s"' % attr[__CTRL_NAME__]
                return

            # Set the default volume
            if attr[__DEFAULT_VOLUME__] >= 0:
                ctrl.setvolume(attr[__DEFAULT_VOLUME__])

            # Set the main mixer control
            if self.main_ctrl is None or \
               (main_ctrl_name is not None and
               attr[__CTRL_NAME__] == main_ctrl_name):
                self.main_ctrl = ctrl

                # Set the min volume
                if attr[__MIN_VOLUME__] >= 0:
                    self.main_ctrl_min = attr[__MIN_VOLUME__]

                # Set the max volume
                if attr[__MAX_VOLUME__] >= 0:
                    self.main_ctrl_max = attr[__MAX_VOLUME__]

            # Set the mute mixer control
            if mute_ctrl_name is not None and \
               attr[__CTRL_NAME__] == mute_ctrl_name:
                self.mute_ctrl = ctrl

        #
        # Fix the mute mixer control if necessary
        #
        if self.mute_ctrl is None:
            self.mute_ctrl = self.main_ctrl


    def config(self):
        """
        Config is called automatically. For default settings run:
        freevo plugins -i alsamixer2
        """
        return [
            ('ALSAMIXER2_MAIN_CTRL', 'PCM', 'Alsa main mixer control'),
            ('ALSAMIXER2_MUTE_CTRL', 'PCM', 'Alsa mute mixer control'),
            ('ALSAMIXER2_CTRLS', [('PCM', 'default', 50, 0, 100)], 'Alsa mixer control list'),
        ]


    def eventhandler(self, event=None, menuw=None, arg=None):
        """
        Event handler to handle VOLUME and MUTE events
        """
        if event == MIXER_VOLUP:
            rc.post_event(Event(OSD_MESSAGE, arg=_('Volume: %s%%') % self.incVolume()))
            rc.post_event(Event('MIXER_VOLUME_INFO', arg='%s' % self.getVolume()))
            return True

        elif event == MIXER_VOLDOWN:
            rc.post_event(Event(OSD_MESSAGE, arg=_('Volume: %s%%') % self.decVolume()))
            rc.post_event(Event('MIXER_VOLUME_INFO', arg='%s' % self.getVolume()))
            return True

        elif event == MIXER_MUTE:
            if self.getMute() == 1:
                rc.post_event(Event(OSD_MESSAGE, arg=_('Volume: %s%%') % self.getVolume()))
                rc.post_event(Event('MIXER_VOLUME_INFO', arg='%s' % self.getVolume()))
                self.setMute(0)
            else:
                rc.post_event(Event(OSD_MESSAGE, arg=_('Mute')))
                rc.post_event(Event('MIXER_MUTE_INFO'))
                self.setMute(1)
            return True

        return False


    def getVolume(self):
        """ Get the volume level of a control """
        return self.main_ctrl.getvolume()[0]


    def setVolume(self, val=0):
        """ Set the volume level of a control (default 0) """
        if val < self.main_ctrl_min:
            val = self.main_ctrl_min
        if val > self.main_ctrl_max:
            val = self.main_ctrl_max
        self.main_ctrl.setvolume(val)


    def incVolume(self, step=5):
        """ Increase the volume level by the step (default 5) """
        self.setVolume(self.getVolume() + step)
        return self.getVolume()


    def decVolume(self, step=5):
        """ Decrease the volume level by the step (default 5) """
        self.setVolume(self.getVolume() - step)
        return self.getVolume()


    def getMute(self):
        """ Get the muting of a control """
        return self.mute_ctrl.getmute()[0]


    def setMute(self, val=0):
        """ Set the muting of a control (default 0) """
        self.mute_ctrl.setmute(val)


    def reset(self):
        """ Resets the audio to defaults """
        pass
