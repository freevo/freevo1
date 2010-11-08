# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# bookmarker.py - Plugin to handle bookmarking
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#     1. while watching a movie file, hit the 'record' button and it'll save a
#        bookmark. There is no visual feedback though.
#     2. Later, to get back there, choose the actions button in the menu, and it'll
#        have a list of bookmarks in a submenu, click on one of those to resume from
#        where you saved.
#     3. When stopping a movie while blackback, the current playtime will be stored
#        in an auto bookmark file. After that, a RESUME action is in the item
#        menu to start were the plackback stopped.
#
# Todo:
#     Currently this only works for files without subitems or variant.
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


import os, time, copy
import glob
import kaa.metadata as mmpython

import plugin
import config
import util
import menu
import item
import rc
import dialog

from event import *

class PluginInterface(plugin.ItemPlugin):
    """
    Automatically bookmark where you were when pausing or stopping.
    Can resume play back afterward from the Bookmarks menu item
    """

    def actions(self, item):
        self.item = item
        items = []
        if item['autobookmark_resume']:
            items.append((self.resume, _('Resume playback')))
        if item.type == 'dir' or item.type == 'playlist':
            return items
        if hasattr(item, 'mode'):
            if item.mode == 'file' and not item.variants and \
                   not item.subitems and os.path.exists(util.get_bookmarkfile(item.filename)):
                items.append(( self.bookmark_menu, _('Bookmarks')))

        return items


    def resume(self, arg=None, menuw=None):
        """
        resume playback
        """
        t    = max(0, self.item['autobookmark_resume'] - 10)
        self.item['resume'] = t
        if menuw:
            menuw.back_one_menu()
        self.item.play(menuw=menuw, arg=arg)

    def bookmark_menu(self,arg=None, menuw=None):
        """
        Bookmark list
        """
        bookmarkfile = util.get_bookmarkfile(self.item.filename)
        items = []
        for line in util.readfile(bookmarkfile):
            item = BookmarkItem(self.item, int(line))
            items.append(item)

        if items:
            item = menu.MenuItem(name=_('Clear all Bookmarks'), action=self.__clear_bookmarks, arg=self.item)
            items.append(item)
            moviemenu = menu.Menu(self.item.name, items, fxd_file=self.item.skin_fxd)
            menuw.pushmenu(moviemenu)
        return


    def __clear_bookmarks(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Do you want to delete all bookmarks?'),
                                    self.__clear_bookmarks_do, proceed_text=_('Delete bookmarks'))

    def __clear_bookmarks_do(self):
        bookmarkfile = util.get_bookmarkfile(self.item.filename)
        os.remove(bookmarkfile)
        menuw.back_one_menu()

    def eventhandler(self, item, event, menuw):
        if event in (STOP, USER_END):
            if item.mode == 'file' and not item.variants and \
                not item.subitems and item.elapsed:
                item.store_info('autobookmark_resume', item.elapsed)
            else:
                _debug_('auto-bookmark not supported for this item')

        if event == PLAY_END:
            item.delete_info('autobookmark_resume')

        # Bookmark the current time into a file
        if event == STORE_BOOKMARK:
            bookmarkfile = util.get_bookmarkfile(item.filename)

            handle = open(bookmarkfile,'a+')
            handle.write(str(item.elapsed))
            handle.write('\n')
            handle.close()
            rc.post_event(Event(OSD_MESSAGE, arg='Added Bookmark'))
            return True

        return False

class BookmarkItem(item.Item):
    def __init__(self, video_item, time):
        item.Item.__init__(self)
        self.item = video_item
        self.time = time
        sec = time
        hour = int(sec/3600)
        min = int((sec-(hour*3600))/60)
        sec = int(sec%60)
        self.time_str = '%0.2d:%0.2d:%0.2d' % (hour,min,sec)
        self.name = _('Jump to %s') % self.time_str

    def actions(self):
        return [(self.play, _('Play from here')), (self.delete, _('Delete'))]

    def play(self, arg=None, menuw=None):
        self.item['resume'] = self.time
        if menuw:
            menuw.back_one_menu()
        self.item.play(menuw=menuw, arg=None)

    def delete(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Do you want to delete bookmark \'%s\'?') % self.time_str,
                                    self.__delete_do, proceed_text=_('Delete bookmark'))
    def __delete_do(self):
        bookmarkfile = util.get_bookmarkfile(self.item.filename)
        handle = open(bookmarkfile)
        bookmarks = ''
        for line in handle:
            if int(line) != self.time:
                bookmarks += line
        handle.close()
        handle = open(bookmarkfile, 'w')
        handle.write(bookmarks)
        handle.close()
        self.menuw.back_one_menu()
