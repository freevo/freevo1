# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in to browse the TV guide via categories
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
"""
Plugin to browse the TV guide via categories.
"""

from gui.PopupBox import PopupBox
import os.path

import plugin

from item import Item
from event import *
from menu import MenuItem, Menu

import tv.epg_xmltv
from tv.programitem import ProgramItem

class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to browse the TV guide via categories.

    Activate with:
    | plugin.activate('tv.categories',level=5)

    """

    def __init__(self):
        """
        normal plugin init, but sets _type to 'mainmenu_tv'
        """
        plugin.MainMenuPlugin.__init__(self)
        self._type = 'mainmenu_tv'
        self.parent = None

    def items(self, parent):
        self.parent = parent
        return [CategoriesItem(parent)]

# ======================================================================
# Recordings Directory Browsing Class
# ======================================================================
class CategoriesItem(Item):
    """
    class for browsing the TV guide
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='tv')
        self.name = _('Browse Categories')


    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name)]
        return items


    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        msgtext = _('Preparing the program guide')
        guide = tv.epg_xmltv.get_guide(PopupBox(text=msgtext))
        items = []
        for category in sorted(guide.categories):
            items.append(CategoryItem(self, category))

        if arg == 'update':

            if not self.menu.choices:
                selected_pos = -1
            else:
                # store the current selected item
                selected_id  = self.menu.selected.id()
                selected_pos = self.menu.choices.index(self.menu.selected)

            self.menu.choices = items
            self.menu.selected = None

            if selected_pos !=-1 and items:
                for i in items:
                    # find the selected item
                    if Unicode(i.id()) == Unicode(selected_id):
                        # item is still there, select it
                        self.menu.selected = i
                        break
                if not self.menu.selected:
                    # item is gone now, try to the selection close
                    # to the old item
                    pos = max(0, min(selected_pos-1, len(items)-1))
                    self.menu.selected = items[pos]

                self.menuw.rebuild_page()
                self.menuw.refresh()
            else:
                self.menuw.init_page()
                self.menuw.refresh()
        else:
            # normal menu build
            item_menu = Menu(self.name, items, reload_func=self.reload, item_types='tv')
            menuw.pushmenu(item_menu)

            self.menu  = item_menu
            self.menuw = menuw


    # ======================================================================
    # Helper methods
    # ======================================================================

    def reload(self):
        """
        Rebuilds the menu.
        """
        self.browse(arg='update')
        return None

class CategoryItem(Item):
    """
    class for browsing the TV guide
    """
    def __init__(self, parent, category):
        Item.__init__(self, parent, skin_type='tv')
        self.name = category
        self.category = category

    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name)]
        return items


    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        msgtext = _('Preparing the program guide')
        guide = tv.epg_xmltv.get_guide(PopupBox(text=msgtext))
        showings = {}

        for c in guide.get_programs(category=self.category):
            for p in c.programs:
                if p.title in showings:
                    s = showings[p.title]
                else:
                    s = []
                    showings[p.title] = s
                s.append(ProgramItem(self, p))
        items = []
        for show in sorted(showings.keys()):
            s = showings[show]
            if len(s) > 1:
                items.append(ProgamShowings(self, show, s))
            else:
                items.append(s[0])

        if arg == 'update':

            if not self.menu.choices:
                selected_pos = -1
            else:
                # store the current selected item
                selected_id  = self.menu.selected.id()
                selected_pos = self.menu.choices.index(self.menu.selected)

            self.menu.choices = items
            self.menu.selected = None

            if selected_pos !=-1 and items:
                for i in items:
                    # find the selected item
                    if Unicode(i.id()) == Unicode(selected_id):
                        # item is still there, select it
                        self.menu.selected = i
                        break
                if not self.menu.selected:
                    # item is gone now, try to the selection close
                    # to the old item
                    pos = max(0, min(selected_pos-1, len(items)-1))
                    self.menu.selected = items[pos]

                self.menuw.rebuild_page()
                self.menuw.refresh()
            else:
                self.menuw.init_page()
                self.menuw.refresh()
        else:
            # normal menu build
            item_menu = Menu(self.name, items, reload_func=self.reload, item_types='tv')
            menuw.pushmenu(item_menu)

            self.menu  = item_menu
            self.menuw = menuw


    # ======================================================================
    # Helper methods
    # ======================================================================

    def reload(self):
        """
        Rebuilds the menu.
        """
        self.browse(arg='update')
        return None

class ProgamShowings(Item):
    def __init__(self, parent, name, programs):
        Item.__init__(self, parent, skin_type='tv')
        self.name = name
        self.items = []
        for program in programs:
            if hasattr(program, 'sub_title') and program.sub_title:
                program.name = program.sub_title
                del program.sub_title
            else:
                program.name = program.start
        self.items = programs

    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name)]
        return items


    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        item_menu = Menu(self.name, self.items, item_types='tv')
        menuw.pushmenu(item_menu)

        self.menu  = item_menu
        self.menuw = menuw
