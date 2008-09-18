# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo audio player GUI
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
Freevo audio player GUI
"""

from gui.GUIObject import GUIObject

import config
import skin
import rc
import plugin
import event

_player_ = None

def get():
    global _player_
    return _player_

class PlayerGUI(GUIObject):
    def __init__(self, item, menuw):
        GUIObject.__init__(self)
        self.visible = menuw and True or False
        self.menuw = menuw
        self.item = item
        self.player  = None
        self.running = False
        self.pbox    = None
        self.progressbox = None
        self.last_progress = 0

        self.first_drawing = True


    def play(self, player=None):
        global _player_
        if _player_ and _player_.player and _player_.player.is_playing():
            _player_.stop()

        _player_ = self

        if self.player and self.player.is_playing():
            self.stop()

        if player:
            self.player = player

        else:
            self.possible_players = []
            for p in plugin.getbyname(plugin.AUDIO_PLAYER, True):
                rating = p.rate(self.item) * 10
                if config.AUDIO_PREFERED_PLAYER == p.name:
                    rating += 1

                if hasattr(self.item, 'force_player') and p.name == self.item.force_player:
                    rating += 100

                if (rating, p) not in self.possible_players:
                    self.possible_players += [(rating, p)]
            self.possible_players = filter(lambda l: l[0] > 0, self.possible_players)
            self.possible_players.sort(lambda l, o: -cmp(l[0], o[0]))
            if len(self.possible_players) > 0:
                self.player_rating, self.player = self.possible_players[0]

        if self.menuw and self.menuw.visible:
            self.menuw.hide(clear=False)

        self.running = True
        error = self.player.play(self.item, self)
        if error:
            print error
            self.running = False
            if self.visible:
                rc.app(None)
            self.item.eventhandler(event.PLAY_END)

        else:
            if self.visible:
                rc.app(self.player)
            self.refresh()


    def try_next_player(self):
        self.stop()
        _debug_('error, try next player')
        player = None
        next   = False
        for r, p in self.possible_players:
            if next:
                player = p
                break
            if p == self.player:
                next = True

        if player:
            self.play(player=player)
            return 1
        _debug_('no more players found')
        return 0


    def stop(self):
        global _player_
        _player_ = None

        self.player.stop()
        self.running = False
        if self.visible:
            rc.app(None)


    def show(self):
        if not self.visible:
            self.visible = 1
            self.refresh()
            rc.app(self.player)


    def hide(self):
        if self.visible:
            self.visible = 0
            skin.clear()
            rc.app(None)


    def refresh(self):
        """
        Give information to the skin..
        """
        if not self.visible:
            return

        if not self.running:
            return

        # Calculate some new values
        if not self.item.length:
            self.item.remain = 0
        else:
            self.item.remain = self.item.length - self.item.elapsed

        do_blend = config.FREEVO_USE_ALPHABLENDING and self.first_drawing

        self.first_drawing = False
        skin.draw('player', self.item)


# register player to the skin
skin.register('player', ('screen', 'title', 'view', 'info', 'plugin'))
