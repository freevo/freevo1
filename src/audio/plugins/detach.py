# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Detach plugin for the audio player
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
logger = logging.getLogger("freevo.audio.plugins.detach")


from kaa import Timer
from kaa import EventHandler

import config
import plugin
import menu
import rc
import audio.player
from event import *

class PluginInterface(plugin.MainMenuPlugin):
    """
    plugin to detach the audio player to e.g. view pictures while listening
    to music
    """
    detached = False

    def __init__(self):
        logger.log( 9, 'detach.PluginInterface.__init__()')
        plugin.MainMenuPlugin.__init__(self)
        config.EVENTS['audio'][config.DETACH_KEY] = Event(FUNCTION_CALL, arg=self.detach)
        self.show_item = menu.MenuItem(_('Show player'), action=self.show)
        self.show_item.type = 'detached_player'
        self.event = EventHandler(self._event_handler)
        self.event.register()


    def config(self):
        """
        config is called automatically,
        freevo plugins -i audio.detach returns the info
        """
        return [
            ('DETACH_KEY', 'DISPLAY', 'Event to activate the detach bar, DISPLAY, ENTER, EXIT'),
        ]


    def detach(self):
        logger.debug('detach()')
        rc.post_event(plugin.event('DETACH'))


    def attach(self):
        logger.debug('attach()')
        rc.post_event(plugin.event('ATTACH'))


    def _event_handler(self, event):
        logger.log( 9, '_event_handler(event=%s)', event)
        gui = audio.player.get()
        if gui:
            p = gui.player
            if event == BUTTON:
                if event.arg == 'FFWD':
                    p.eventhandler(Event('SEEK', arg='10', context='audio'))
                elif event.arg == 'REW':
                    p.eventhandler(Event('SEEK', arg='-10', context='audio'))
                elif event.arg == 'PAUSE':
                    p.eventhandler(Event('PLAY', context='audio'))
                elif event.arg == 'STOP':
                    PluginInterface.detached = False
                    p.eventhandler(Event('STOP'))
                elif event.arg == 'NEXT':
                    p.eventhandler(Event('PLAYLIST_NEXT', context='audio'))
                elif event.arg == 'PREV':
                    p.eventhandler(Event('PLAYLIST_PREV', context='audio'))
            elif plugin.isevent(event) == 'DETACH':
                p.eventhandler(event)
                self._detach()
            elif plugin.isevent(event) == 'ATTACH':
                PluginInterface.detached = False
                p.eventhandler(event)
            elif event == VIDEO_START:
                PluginInterface.detached = False
                p.eventhandler(Event('STOP'))
            elif event == PLAY_START and gui.visible:
                rc.post_event(plugin.event('ATTACH'))


    def _detach(self, menuw=None):
        logger.debug('_detach()')
        if PluginInterface.detached:
            return
        PluginInterface.detached = True

        gui = audio.player.get()
        # hide the menuw's
        gui.hide()
        gui.menuw.show()
        # set all menuw's to None to prevent the next title to be visible again
        gui.menuw = None
        gui.item.menuw = None
        if gui.item.parent:
            gui.item.parent.menuw = None


    def _attach(self, menuw=None):
        logger.debug('_attach()')
        if not PluginInterface.detached:
            return
        PluginInterface.detached = False

        gui = audio.player.get()
        # restore the menuw's
        gui.menuw = menuw
        gui.item.menuw = menuw
        if gui.item.parent:
            gui.item.parent.menuw = menuw
        # hide the menu and show the player
        menuw.hide()
        gui.show()


    def items(self, parent):
        logger.log( 9, 'items(parent=%r)', parent)
        gui = audio.player.get()
        if gui and gui.player.is_playing():
            self.show_item.parent = parent
            return [ self.show_item ]
        return []


    def show(self, arg=None, menuw=None):
        logger.debug('show(arg=%r, menuw=%r)', arg, menuw)
        rc.post_event(plugin.event('ATTACH'))
        self._attach(menuw)
