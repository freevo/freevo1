# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in to watch tv with xine.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# This plugin is beta and only working with dvb
#
# Todo:
#
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


import time, os, re
import copy

import config     # Configuration handler. reads config file.
import childapp   # Handle child applications
import rc         # The RemoteControl class.
import util
import osd
import dialog
from dialog.display import AppTextDisplay
from tv.channels import FreevoChannels

from event import *
import plugin

osd = osd.get_singleton()

class PluginInterface(plugin.Plugin):
    """
    Xine plugin for tv. The plugin is beta and only works with dvb.

    Your channel list must contain the identifier from the xine channels.conf
    as frequence, e.g.

    | TV_CHANNELS = [
    |     ( 'ard.de', 'ARD', 'Das Erste RB' ),
    |     ( 'zdf.de', 'ZDF', 'ZDF' ),
    |     ( 'ndr.de', 'NDR', 'NDR RB' ),
    |     ( 'rtl.de', 'RTL', 'RTL Television' ),
    |     ( 'sat1.de', 'SAT.1', 'SAT.1' ),
    |     ( 'rtl2.de', 'RTL 2', 'RTL2' ),
    |     ( 'prosieben.de', 'PRO 7', 'ProSieben' ),
    |     ( 'kabel1.de', 'KABEL 1', 'KABEL1' ),
    |     ( 'vox.de', 'VOX', 'VOX' ),
    |     ( 'n24.de', 'N24', 'N24' ),
    |     ( 'arte-tv.com', 'ARTE', 'arte' ),
    |     ( 'C3sat.de', '3SAT', 'Info/3sat' ),
    |     ( 'superrtl.de', 'Super RTL', 'Super RTL' ),
    |     ( 'kika.de', 'Kika', 'Doku/KiKa' )
    | ]
    """

    def __init__(self):
        plugin.Plugin.__init__(self)

        try:
            config.XINE_COMMAND
        except:
            self.reason = _("'XINE_COMMAND' not defined, 'xine' tv plugin deactivated.\n" \
                'please check the xine section in freevo_config.py')
            return

        if config.XINE_COMMAND.find('fbxine') >= 0:
            type = 'fb'
        else:
            type = 'X'

        # register xine as the object to play
        plugin.register(Xine(type), plugin.TV, False)



class Xine:
    """
    the main class to control xine
    """
    def __init__(self, type):
        self.name      = 'xine'

        self.event_context = 'tv'
        self.xine_type = type
        self.app       = None

        self.fc = FreevoChannels()

        self.command = [ '--prio=%s' % config.MPLAYER_NICE ] + \
                       config.XINE_COMMAND.split(' ') + \
                       [ '--stdctl', '-V', config.XINE_VO_DEV,
                         '-A', config.XINE_AO_DEV ] + \
                       config.XINE_ARGS_DEF.split(' ')


    def ShowMessage(self, msg):
        """
        Show a message on the OSD
        """
        _debug_("XINE: Show OSD Message: '%s'" % msg)
        self.app.write("OSDWriteText$     %s\n" % msg)


    def Play(self, mode, tuner_channel=None):
        """
        play with xine
        """
        if not tuner_channel:
            tuner_channel = self.fc.getChannel()

        if plugin.getbyname('MIXER'):
            plugin.getbyname('MIXER').reset()

        command = copy.copy(self.command)

        if not config.XINE_HAS_NO_LIRC and '--no-lirc' in command:
            command.remove('--no-lirc')

        if config.OSD_SINGLE_WINDOW:
            command += ['-W', str(osd.video_window.id), '--no-mouse']
            osd.video_window.show()

        command.append('dvb://' + tuner_channel)

        _debug_('Starting cmd=%s' % command)

        rc.add_app(self)

        self.app = childapp.ChildApp2(command)
        dialog.enable_overlay_display(AppTextDisplay(self.ShowMessage))
        return None


    def stop(self, channel_change=0):
        """
        Stop xine
        """
        if self.app:
            if config.OSD_SINGLE_WINDOW:
                osd.video_window.hide()

            self.app.stop('quit\n')
            rc.remove_app(self)
            dialog.disable_overlay_display()

            if not channel_change:
                pass


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for xine control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        if event in ( PLAY_END, USER_END, STOP ):
            self.stop()
            rc.post_event(PLAY_END)
            return True

        if event == PAUSE or event == PLAY:
            self.app.write('pause\n')
            return True

        elif event in [ TV_CHANNEL_UP, TV_CHANNEL_DOWN] or str(event).startswith('INPUT_'):
            if event == TV_CHANNEL_UP:
                nextchan = self.fc.getNextChannel()
            elif event == TV_CHANNEL_DOWN:
                nextchan = self.fc.getPrevChannel()
            else:
                nextchan = self.fc.getManChannel(int(event.arg))

            self.stop(channel_change=1)
            self.fc.chanSet(nextchan, True)
            self.Play('tv', nextchan)
            return True

        if event == TOGGLE_OSD:
            self.app.write('PartMenu\n')
            return True

        if event == VIDEO_TOGGLE_INTERLACE:
            self.app.write('ToggleInterleave\n')
            return True

        if event == OSD_MESSAGE:
            self.ShowMessage(event.arg)
            return True

        # nothing found
        return False
