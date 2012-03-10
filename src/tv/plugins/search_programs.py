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
import tv.epg

from gui import sounds
from item import Item

from menu import MenuItem, Menu
from tv.programitem import ProgramItem
from skin.widgets import TextEntryScreen

import dialog
from dialog.dialogs import ProgressDialog

MAX_RESULTS = 500

class PluginInterface(plugin.MainMenuPlugin):
    """
    Search for programs
    """

    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)

        self._type = 'mainmenu_tv'
        self.parent = None
        self.prog_menu = SearchProgramMenu()
        plugin.register(self.prog_menu, "Search Program")
        plugin.activate(self.prog_menu)


    def items(self, parent):
        self.parent = parent
        return [SearchPrograms(parent)]

class SearchProgramMenu(plugin.Plugin):
    def __init__(self):
        plugin.Plugin.__init__(self)
        self._type = 'tv_program'
        self.current_prog = None

    def items(self, prog):
        """
        Get actions for prog.
        """
        self.current_prog = prog
        if prog.context == 'more_programs':
            return []
        return [(self.more_programs, _('Search for more of this program'))]
        

    def more_programs(self, arg=None, menuw=None):
        pdialog = ProgressDialog(_('Searching, please wait...'))
        pdialog.show()
        now = time.time()
        programs = tv.epg.search(title=self.current_prog.prog.title, time=(now, 0))
        items = []
        for prog in programs:
            items.append(ProgramItem(self.current_prog, prog, context='more_programs'))

        items.sort(lambda x,y: cmp(x.prog.start, y.prog.start))
        pdialog.hide()
        search_menu = Menu(_('Search Results'), items, item_types='tv program menu')
        menuw.pushmenu(search_menu)
        menuw.refresh()

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
        if not text:
            dialog.show_alert(_('Please specify something to search for!'))
            return
        pdialog = ProgressDialog(_('Searching, please wait...'))
        pdialog.show()

        programs = tv.epg.search(keyword=text, time=(time.time(),0))
        items = []
        for prog in programs:
            items.append(ProgramItem(self.parent, prog, context='search'))

            if len(items) >= MAX_RESULTS:
                break

        items.sort(lambda x,y: cmp(x.prog.start, y.prog.start))
        pdialog.hide()

        if len(items) == 0:
            dialog.show_alert(_('No matches found for %s') % text)
            return      

        search_menu = Menu(_('Search Results'), items, item_types='tv program menu')
        menuw.pushmenu(search_menu)
        menuw.refresh()

        
