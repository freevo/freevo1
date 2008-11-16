# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to add options to play bilingual recordings.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# ToDo:
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
from os.path import join, split

import config
import plugin
import menu
from gui.AlertBox import AlertBox
from gui.PopupBox import PopupBox


class PluginInterface(plugin.ItemPlugin):
    """
    Plug-in to play tv recordings which have bilingual audio

    To activate, put the following line in local_conf.py:
    | plugin.activate('video.bilingual')
    """

    def __init__(self):
        _debug_('bilingual.PluginInterface.__init__(self)', 2)
        plugin.ItemPlugin.__init__(self)
        self.item = None


    def config(self):
        """
        config is called automatically,
        freevo plugins -i video.bilingual returns the info
        """
        _debug_('config(self)', 2)
        return [
        ]


    def actions(self, item):
        """
        Determines if an action applies to the menu

        Normally, the only way to record bilingual audio is with a recent
        version of the ivtv driver (>=0.8.2) the ideas is that you can select the
        left, right or both channels and this information is passed to the player
        as part of the item, i.e. item.language_selection.
        """
        _debug_('actions(self, item)', 2)
        if item.type == 'video' and item.mode == 'file':
            if hasattr(item, 'audio'):
                _debug_('len(item.info[\'audio\'])=%d' % (len(item.info['audio'])))
            if len(item.info['audio']) == 1:
                _debug_('item[\'audio\'][0][\'codec\']=%r' % (item['audio'][0]['codec']))
                if item['audio'][0]['codec'] == 'MP2A':
                    self.item = item
                    return [ (self.language_selection_menu, _('Bilingual language selection')) ]
        return []


    def language_selection_menu(self, menuw=None, arg=None):
        _debug_('language_selection_menu(self, menuw=%r, arg=%r)' % (menuw, arg), 2)
        menu_items = []
        menu_items += [ menu.MenuItem(_('Play Both Channels'), self.language_selection, (self.item, 'both'))  ]
        menu_items += [ menu.MenuItem(_('Play Left Channel'),  self.language_selection, (self.item, 'left'))  ]
        menu_items += [ menu.MenuItem(_('Play Right Channel'), self.language_selection, (self.item, 'right')) ]
        moviemenu = menu.Menu(_('Language Menu'), menu_items)
        menuw.pushmenu(moviemenu)


    def language_selection(self, menuw=None, arg=None):
        _debug_('language_selection(self, menuw=%r, arg=%r)' % (menuw, arg), 2)
        arg[0].selected_language = arg[1]
        menuw.back_one_menu()
