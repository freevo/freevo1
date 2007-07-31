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
import rc

from event import *

class PluginInterface(plugin.ItemPlugin):
    """
    class to handle auto bookmarks
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
        info = mmpython.parse(self.item.filename)
        if (self.item.player.name == 'xine'):
            self.write_playlist(t)
            arg = ("--playlist %s/playlist_xine_%s.tox" % (config.FREEVO_CACHEDIR, t))
        else:
            if hasattr(info, 'seek') and t:
                arg='-sb %s' % info.seek(t)
            else:
                arg='-ss %s' % t
        if menuw:
            menuw.back_one_menu()
        self.item.play(menuw=menuw, arg=arg)

    def write_playlist(self,time):
        t = time
        name = '%s/playlist_xine_%s.tox' % (config.FREEVO_CACHEDIR,t)

        # this file has a companion subtitle file?
        subtitle = None
        try:
            for file in glob.glob('%s.*' % os.path.splitext(self.item.filename)[0]):
                if os.path.splitext(file)[1].lower() in ['.srt', '.sub', '.ssa']:
                    subtitle = file
                    break
        except:
            pass
        playlist = open(name,'w')
        playlist.write ("# toxine playlist\n")
        playlist.write ("entry {\n")
        playlist.write ("       identifier = %s;\n" % self.item.filename)
        playlist.write ("       mrl = %s;\n" % self.item.filename)
        if subtitle:
            playlist.write("       subtitle = %s;\n" % subtitle)
        playlist.write ("       start = %s;\n" % t)
        playlist.write ("};\n")
        playlist.write ("# END\n")
        playlist.close()


    def bookmark_menu(self,arg=None, menuw=None):
        """
        Bookmark list
        """
        bookmarkfile = util.get_bookmarkfile(self.item.filename)
        items = []
        for line in util.readfile(bookmarkfile):
            file = copy.copy(self.item)
            file.info = {}

            sec = int(line)
            hour = int(sec/3600)
            min = int((sec-(hour*3600))/60)
            sec = int(sec%60)
            time = '%0.2d:%0.2d:%0.2d' % (hour,min,sec)
            # set a new title
            file.name = Unicode(_('Jump to %s') % (time))
            if hasattr(file, 'tv_show'):
                del file.tv_show

            if not self.item.mplayer_options:
                self.item.mplayer_options = ''
            if (self.item.player.name == 'xine'):
                self.write_playlist(int(line))
                cmd = ' --playlist %s/playlist_xine_%s.tox' % (config.FREEVO_CACHEDIR,int(line))
                file.mplayer_options = (cmd)
            else:
                file.mplayer_options = str(self.item.mplayer_options) +  ' -ss %s' % time
            items.append(file)

        if items:
            moviemenu = menu.Menu(self.item.name, items, fxd_file=self.item.skin_fxd)
            menuw.pushmenu(moviemenu)
        return


    def eventhandler(self, item, event, menuw):
        if event in (STOP, USER_END):
            playlist_remove = ("%s/playlist_xine*.tox" % config.FREEVO_CACHEDIR)
            for filename in glob.glob(playlist_remove):
                os.remove(filename)
            if item.mode == 'file' and not item.variants and \
                not item.subitems and item.elapsed:
                item.store_info('autobookmark_resume', item.elapsed)
            else:
                _debug_('auto-bookmark not supported for this item')

        if event == PLAY_END:
            item.delete_info('autobookmark_resume')

        # Bookmark the current time into a file
        if event == STORE_BOOKMARK:
            #Get time elapsed for xine video
            videoplayer = self.item.player.name
            if (videoplayer == 'xine'):
                command = ("%s -S get_time" % config.CONF.xine)
                handle = os.popen(command,'r')
                position = handle.read();
                handle.close()
                item.elapsed = int(position)

            bookmarkfile = util.get_bookmarkfile(item.filename)

            handle = open(bookmarkfile,'a+')
            handle.write(str(item.elapsed))
            handle.write('\n')
            handle.close()
            rc.post_event(Event(OSD_MESSAGE, arg='Added Bookmark'))
            return True

        return False
