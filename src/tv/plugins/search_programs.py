# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Search for similar TV programs
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

from menu import MenuItem, Menu
from tv.programitem import ProgramItem
from skin.widgets import TextEntryScreen


class PluginInterface(plugin.MainMenuPlugin):
    """
    Search for programs
    """

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


    def actions(self):
        return [(self.show_search, self.name)]


    def show_search(self, arg=None, menuw=None):
        text_entry = TextEntryScreen((_('Search'), self.search_for_programs), self.name)
        text_entry.show(menuw)


    def search_for_programs(self, menuw, text):
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
            AlertBox(text=_('Cannot find program: %s') % matches).show()
            return
        search_menu = Menu(_('Search Results'), items, item_types='tv program menu')
        menuw.pushmenu(search_menu)
        menuw.refresh()


    def findMatches(self, find=None, movies_only=None):
        global guide

        _debug_('findMatches: %s' % find, DINFO)

        matches = []
        max_results = 500

        if not find and not movies_only:
            _debug_('nothing to find', DINFO)
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
                            _debug_('PROGRAM MATCH 2: %s' % prog, DINFO)
                    else:
                        # We should never get here if not find and not
                        # movies_only.
                        matches.append(prog)
                        _debug_('PROGRAM MATCH 3: %s' % prog, DINFO)
                if len(matches) >= max_results:
                    break

        _debug_('Found %d matches.' % len(matches), DINFO)

        if matches:
            return (TRUE, matches)
        return (FALSE, 'no matches')


    def updateGuide(self):
        global guide
        guide = tv.epg_xmltv.get_guide()
