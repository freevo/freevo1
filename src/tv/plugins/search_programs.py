# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# search_programs.py: searchs for programs
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

import os
import os.path
import datetime
import traceback
import re
import stat
import copy
import time

import rc
import config
import util
import plugin
import osd
import tv.epg_xmltv

from gui import sounds
from gui.PopupBox import PopupBox
from gui.AlertBox import AlertBox
from item import Item
from event import *
from menu import MenuItem, Menu
from tv.programitem import ProgramItem
import tv.record_client as record_client

# Create the skin_object object
import skin
skin_object = skin.get_singleton()
skin_object.register('searchprograms', ('screen', 'textentry', 'buttongroup', 'plugin'))

class PluginInterface(plugin.MainMenuPlugin):
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)

        self._type = 'mainmenu_tv'
        self.parent = None

    def items(self, parent):
        self.parent = parent
        return [SearchPrograms(parent)]

class SearchPrograms(Item):
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='tv')
        self.name = _('Search Programs')
        self.text_entry = skin.TextEntry('')
        self.type = 'searchprograms'

        #
        # Create button groups for alphabet/numbers/symbols
        #

        # Create common buttons
        self.search_button = skin.Button(_('Search'), self.search_for_programs, None)
        self.left_button   = skin.Button(_('Left'), self.move_caret, 'left')
        self.right_button  = skin.Button(_('Right'), self.move_caret, 'right')
        self.delete_button = skin.Button(_('Delete'), self.delete_char, None)


        self.alphabet_button_group = skin.ButtonGroup(6, 7)
        keys = _('ABCDEFGHIJKLMNOPQRSTUVWXYZ ')
        self.__init_keyboard_buttons(keys,  self.alphabet_button_group)

        self.numbers_button_group = skin.ButtonGroup(6, 7)
        keys = _('1234567890')
        self.__init_keyboard_buttons(keys,  self.numbers_button_group)

        self.symbols_button_group = skin.ButtonGroup(6, 7)
        keys = _('!"#$%^&*();:\'@~?,.<>-=+\[]{}')
        self.__init_keyboard_buttons(keys,  self.symbols_button_group)

        characters_button = skin.Button(_('ABC'),  self.change_button_group,
                                                   self.alphabet_button_group)
        numbers_button = skin.Button(_('123'),  self.change_button_group,
                                                self.numbers_button_group)
        symbols_button = skin.Button(_('Symbls'),  self.change_button_group,
                                                   self.symbols_button_group)

        self.numbers_button_group.set_button(0, 5, characters_button)
        self.symbols_button_group.set_button(0, 5, characters_button)

        self.alphabet_button_group.set_button(1, 5, numbers_button)
        self.symbols_button_group.set_button(1, 5, numbers_button)

        self.alphabet_button_group.set_button(2, 5, symbols_button)
        self.numbers_button_group.set_button(2, 5, symbols_button)

        self.button_group = self.alphabet_button_group

        self.__redraw = False

    def actions(self):
        return [(self.show_search, self.name)]


    def show_search(self, arg=None, menuw=None):
        self.menuw = menuw
        #self.__redraw = False
        #rc.app(self)
        #skin_object.draw('searchprograms', self)
        menuw.pushmenu(self)

    def refresh(self):
        self.__redraw = False
        skin_object.draw('searchprograms', self)

    def eventhandler(self, event, menuw=None):
        """
        eventhandler
        """
        consumed = False

#        if event is MENU_BACK_ONE_MENU:
#            rc.app(None)
#            self.menuw.refresh()
#            consumed = True

        if event is MENU_SELECT:
            sounds.play_sound(sounds.MENU_SELECT)
            self.button_group.selected_button.select()
            consumed = True

        elif event in (MENU_LEFT, MENU_RIGHT, MENU_DOWN, MENU_UP):
            if event is MENU_LEFT:
                self.__redraw = self.button_group.move_left()
            elif event is MENU_RIGHT:
                self.__redraw = self.button_group.move_right()
            elif event is MENU_DOWN:
                self.__redraw = self.button_group.move_down()
            elif event is MENU_UP:
                self.__redraw = self.button_group.move_up()

            if self.__redraw:
                sounds.play_sound(sounds.MENU_NAVIGATE)
            consumed = True

        if self.__redraw:
            skin_object.draw('searchprograms', self)
            self.__redraw = False
        return consumed


    def insert_key(self, arg):
        self.text_entry.insert_char_at_caret(arg)
        self.__redraw = True


    def move_caret(self, arg):
        if arg == 'left':
            self.text_entry.caret_left()
        elif arg == 'right':
            self.text_entry.caret_right()
        self.__redraw = True


    def delete_char(self, arg):
        self.text_entry.delete_char_at_caret()
        self.__redraw = True


    def change_button_group(self, arg):
        self.button_group = arg
        self.button_group.set_selected(self.button_group.buttons[0][0])
        self.__redraw = True


    def __init_keyboard_buttons(self, keys, button_group):
        r = 0
        c = 0
        for key in keys:
            if key == ' ':
                text = _('Space')
            else:
                text = key
            button_group.set_button(r, c, skin.Button(text, self.insert_key, key))
            c += 1
            if c == 5:
                r += 1
                c = 0
        # Add common buttons to the group
        button_group.set_button(0,6, self.search_button)
        button_group.set_button(1,6, self.left_button)
        button_group.set_button(2,6, self.right_button)
        button_group.set_button(3,6, self.delete_button)

    def search_for_programs(self, arg):
        text = self.text_entry.text
        pop = PopupBox(text=_('Searching, please wait...'))
        pop.show()
        (result, matches) = self.findMatches(text)
        pop.destroy()

        items = []
        if result:
            _debug_('search found %s matches' % len(matches))

            f = lambda a, b: cmp(a.start, b.start)
            matches.sort(f)
            for prog in matches:
                items.append(ProgramItem(self, prog, context='search'))
        else:
            if matches == 'no matches':
                msgtext = _('No matches found for %s') % text
                AlertBox(text=msgtext).show()
                return
            AlertBox(text=_('findMatches failed: %s') % matches).show()
            return
        search_menu = Menu(_( 'Search Results' ), items,
                           item_types = 'tv program menu')

        self.menuw.pushmenu(search_menu)
        self.menuw.refresh()

    def findMatches(self, find=None, movies_only=None):
        global guide

        _debug_('findMatches: %s' % find, config.DINFO)

        matches = []
        max_results = 500

        if not find and not movies_only:
            _debug_('nothing to find', config.DINFO)
            return (FALSE, 'no search string')

        self.updateGuide()

        pattern = '.*' + find + '\ *'
        regex = re.compile(pattern, re.IGNORECASE)
        now = time.time()

        for ch in guide.chan_list:
            for prog in ch.programs:
                if now >= prog.stop:
                    continue
                if not find or regex.match(prog.title) or regex.match(prog.desc) \
                   or regex.match(prog.sub_title):
                    if movies_only:
                        # We can do better here than just look for the MPAA
                        # rating.  Suggestions are welcome.
                        if 'MPAA' in prog.getattr('ratings').keys():
                            matches.append(prog)
                            _debug_('PROGRAM MATCH 2: %s' % prog, config.DINFO)
                    else:
                        # We should never get here if not find and not
                        # movies_only.
                        matches.append(prog)
                        _debug_('PROGRAM MATCH 3: %s' % prog, config.DINFO)
                if len(matches) >= max_results:
                    break

        _debug_('Found %d matches.' % len(matches), config.DINFO)

        if matches:
            return (TRUE, matches)
        return (FALSE, 'no matches')


    def updateGuide(self):
        global guide
        guide = tv.epg_xmltv.get_guide()
