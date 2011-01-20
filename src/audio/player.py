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
from event import *

if config.DEBUG_DEBUGGER:
    import pdb, pprint, traceback

_player_ = None

def get():
    global _player_
    _debug_('get() _player_=%r' % (_player_,), 2)
    return _player_

class PlayerGUI(GUIObject):
    def __init__(self, item, menuw, arg=None):
        _debug_('PlayerGUI.__init__(item=%r, menuw=%r, arg=%r)' % (item, menuw, arg))
        GUIObject.__init__(self)
        self.visible = menuw and True or False
        self.item = item
        self.menuw = menuw
        self.arg = arg
        self.succession = PlayListSuccession(arg)
        self.player  = None
        self.running = False
        self.pbox    = None
        self.progressbox = None
        self.last_progress = 0
        self.first_drawing = True


    def play(self, player=None):
        _debug_('%s.play(player=%r)' % (self.__module__, player))
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
                rc.remove_app(self.player)
            self.item.eventhandler(PLAY_END)
        else:
            if self.visible:
                rc.add_app(self.player)
            self.refresh()


    def try_next_player(self):
        _debug_('try_next_player()')
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


    def stop(self, restore_menu=False):
        _debug_('stop(restore_menu=%r)' % (restore_menu,))
        global _player_
        _player_ = None
        self.player.stop()
        self.running = False
        if self.visible:
            rc.remove_app(self.player)
            skin.draw('player', self.item, transition=skin.TRANSITION_OUT)

        if self.menuw and not self.menuw.visible and restore_menu:
            self.menuw.show()


    def show(self):
        _debug_('show()')
        if not self.visible:
            self.visible = True
            self.refresh()
            rc.add_app(self.player)


    def hide(self):
        _debug_('hide()')
        if self.visible:
            self.visible = False
            skin.clear()
            rc.remove_app(self.player)


    def refresh(self):
        """
        Give information to the skin
        """
        _debug_('refresh() visible=%r running=%r' % (self.visible, self.running), 3)
        if not self.visible:
            return

        if not self.running:
            return

        # Calculate some new values
        if not self.item.length:
            self.item.remain = 0
        else:
            self.item.remain = self.item.length - self.item.elapsed

        if self.first_drawing:
            transition = skin.TRANSITION_IN
            self.first_drawing = False
        else:
            transition = skin.TRANSITION_NONE
        skin.draw('player', self.item, transition=transition)



class PlayListSuccession:
    """
    Play list succession class, it determines if the audio item is the first,
    next, last or only item in a play list. Unfortunately it cannot detect the
    only item in a play list.

    mplayervis uses this class to determine what to do with the visualisation.

    Possibly move this class to audioitem
    """
    UNKNOWN = 0 # don't know
    FIRST   = 1 # first item in play list
    NEXT    = 2 # next item in play list
    LAST    = 3 # last item in play list
    ONLY    = 4 # single item play list

    def __init__(self, mode=UNKNOWN):
        self.mode = self.setmode(mode)

    def setmode(self, s):
        #mode if isinstance(mode, PlayListSuccession) else
        return PlayListSuccession.FIRST if s is None    else \
               PlayListSuccession.FIRST if s == 'first' else \
               PlayListSuccession.NEXT  if s == 'next'  else \
               PlayListSuccession.LAST  if s == 'last'  else \
               PlayListSuccession.ONLY  if s == 'only'  else \
               PlayListSuccession.UNKNOWN

    def __repr__(self):
        if self.mode == PlayListSuccession.FIRST: return 'FIRST'
        if self.mode == PlayListSuccession.NEXT:  return 'NEXT'
        if self.mode == PlayListSuccession.LAST:  return 'LAST'
        if self.mode == PlayListSuccession.ONLY:  return 'ONLY'
        return 'UNKNOWN'

    def __cmp__(self, other):
        if isinstance(other, PlayListSuccession):
            if self.mode > other.mode: return 1
            if self.mode < other.mode: return -1
        else:
            if self.mode > other: return 1
            if self.mode < other: return -1
        return 0

    def __index__(self):
        return self.mode

    def __int__(self):
        return self.mode

    def __add__(self, other):
        self.mode = (self.mode + int(other)) % 3
        return self

    def __sub__(self, other):
        self.mode = (self.mode - int(other)) % 3
        return self



# register player to the skin
skin.register('player', ('screen', 'title', 'view', 'info', 'plugin'))
