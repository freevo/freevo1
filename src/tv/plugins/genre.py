# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# genre.py - Browse EPG by Genre
# -----------------------------------------------------------------------------
# $Id$
#
# This plugin lists all the available genres found in the TV guide. Selecting
# a genre will show a program list of that genre.
#
# -----------------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2007 Dirk Meyer, et al.
#
# First Edition: Jose Taza <jose4freevo@chello.nl>
# Maintainer:    Jose Taza <jose4freevo@chello.nl>
#
# Please see the file AUTHORS for a complete list of authors.
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
# -----------------------------------------------------------------------------

# python imports
import logging
import time
import sys

# freevo imports
import tv.epg_xmltv
from item import Item
from menu import MenuItem, Menu
from tv.programitem import ProgramItem
from plugin import MainMenuPlugin

# get logging object
log = logging.getLogger('tv')

if 'epydoc' in sys.modules:
    # make epydoc happy because gettext is not running
    __builtins__['_'] = lambda x: x

EXCLUDE_GENRES = ('unknown', 'none', '')

class GenreItem(Item):
    """
    Item for the TV genre
    """
    def __init__(self, parent, category=None):
        Item.__init__(self, parent)
        self.name = category
        self.cat = category


    def actions(self):
        return [ (self.browse, _('Browse list'))]


    def browse(self, arg=None, menuw=None):
        """
        Find all the programs with this genre/category
        """
        guide = tv.epg_xmltv.get_guide()

        if not guide:
            AlertBox(text=_('TVServer not running') % matches).show()
            return
        items = []
        now = time.time()

        #get programs
        for ch in guide.chan_list:
            for prog in ch.programs:
                if now >= prog.stop:
                    continue
                if self.cat in prog.categories:
                    items.append(ProgramItem(self, prog, context='search'))

        # create menu for programs
        menu = Menu(self.cat, items, item_types='tv program menu')
        menuw.pushmenu(menu)
        menuw.refresh()


class CategoryListItem(Item):
    """
    Item for a TV category list
    """
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.parent = parent
        self.name = _('Browse by Genre')


    def actions(self):
        return [ (self.browse, _('Browse list'))]


    def browse(self, arg=None, menuw=None):
        """
        Find all genres/categories
        """
        guide = tv.epg_xmltv.get_guide()

        if not guide:
            AlertBox(text=_('TVServer not running') % matches).show()
            return
        items = []
        categories = []
        now = time.time()

        #get categories
        for ch in guide.chan_list:
            for prog in ch.programs:
                if now >= prog.stop:
                    continue
                query_data = prog.categories
                for genre in query_data:
                    if genre and genre.lower() not in EXCLUDE_GENRES:
                        if genre not in categories:
                            categories.append(genre)
                            items.append(GenreItem(self.parent, genre))

        # create menu
        menu = Menu(self.name, items, item_types='tv listing')
        menuw.pushmenu(menu)
        menuw.refresh()



#
# the plugin is defined here
#

class PluginInterface(MainMenuPlugin):
    """
    Add 'Browse by Genre' to the TV menu.
    """

    def __init__(self):
        MainMenuPlugin.__init__(self)

        self._type = 'mainmenu_tv'
        self.parent = None

    def items(self, parent):
        """
        Return the main menu item.
        """
        self.parent = parent
        return [ CategoryListItem(parent) ]
