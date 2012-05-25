# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in for IMDB support
# -----------------------------------------------------------------------
# $Id$
#
# Notes: IMDB plugin. You can add IMDB information for video items
#        with the plugin
#        activate with plugin.activate('video.imdb')
#        You can also set imdb_search on a key (e.g. '1') by setting
#        EVENTS['menu']['1'] = Event(MENU_CALL_ITEM_ACTION, arg='imdb_search_or_cover_search')
#
# Todo:  - function to add to an existing s file
#        - DVD/VCD support
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
import logging
logger = logging.getLogger("freevo.video.plugins.imdb")

# based on original implementation by 'den_RDC (rdc@kokosnoot.com)'
__author__           = 'den_RDC (rdc@kokosnoot.com)'
__maintainer__       = 'Maciej Urbaniak'
__maintainer_email__ = 'maciej@urbaniak.org'
__version__          = '$Revision$'
__license__          = 'GPL'

# Module Imports
import os

import menu
import config
import plugin
import re
import time
import dialog
import dialog.utils 

from util.fxdimdb import FxdImdb, makeVideo, makePart, point_maker, FxdImdb_Error

try:
    import imdb
except ImportError:
    logger.error('It seems that you do not have imdbpy installed!')

class PluginInterface(plugin.ItemPlugin):
    """
    You can add IMDB information for video items with the plugin.

    Make sure you have imdbpy installed, on Debian do:
    | apt-get install python-imdbpy
    
    Check out http://imdbpy.sourceforge.net/?page=download for imdbpy package for your distribution
    
    Activate with:
    | plugin.activate('video.imdb2')

    You can also set imdb_search on a key (e.g. '1') by setting
    | EVENTS['menu']['1'] = Event(MENU_CALL_ITEM_ACTION, arg='imdb_search_or_cover_search')
    """

    def __init__(self, license=None):
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        self.fxd = FxdImdb()
        plugin.ItemPlugin.__init__(self)


    def imdb_get_disc_searchstring(self, item):
        name  = item.media.label
        name  = re.sub('([a-z])([A-Z])', point_maker, name)
        name  = re.sub('([a-zA-Z])([0-9])', point_maker, name)
        name  = re.sub('([0-9])([a-zA-Z])', point_maker, name.lower())
        for r in config.IMDB_REMOVE_FROM_LABEL:
            name  = re.sub(r, '', name)
        parts = re.split('[\._ -]', name)

        name = ''
        for p in parts:
            if p:
                name += '%s ' % p
        if name:
            return name[:-1]
        else:
            return ''

    def actions(self, item):
        self.item = item

        if item.type == 'video' and (not item.files or not item.files.fxd_file):
            if item.mode == 'file' or (item.mode in ('dvd', 'vcd') and \
                                       item.info.has_key('tracks') and not \
                                       item.media):
                self.disc_set = False
                return [ ( self.imdb_search , _('Search IMDB for this file'),
                           'imdb_search_or_cover_search') ]

            elif item.mode in ('dvd', 'vcd') and item.info.has_key('tracks'):
                self.disc_set = True
                s = self.imdb_get_disc_searchstring(self.item)
                if s:
                    return [ ( self.imdb_search , _('Search IMDB for [%s]') % s,
                               'imdb_search_or_cover_search') ]

        if item.type == 'dir' and item.media and item.media.mountdir.find(item.dir) == 0:
            self.disc_set = True
            s = self.imdb_get_disc_searchstring(self.item)
            if s:
                return [ ( self.imdb_search , _('Search IMDB for [%s]') % s,
                           'imdb_search_or_cover_search') ]
        return []


    def imdb_search(self, arg=None, menuw=None):
        """
        search imdb for this item
        """

        items = []
        dlg = dialog.utils.show_message(_('Searching IMDB...'), 'status', 0)

        if self.disc_set:
            self.searchstring = self.item.media.label
        else:
            self.searchstring = self.item.name
    
        try:
            #guess the title from the filename
            results = self.fxd.guessImdb(self.searchstring, self.disc_set)
            
            # loop through the results and create menu
            # should not use imdbpy objects here as imdbpy should be encapsulated by FxdImdb
            # but for now it's to much work to do this the right way. 
            # It works so let's deal with it later.
            for movie in results:
                try:
                    # OK, we have a regular movie here, no nested episodes
                    items.append(menu.MenuItem('%s (%s) (%s)' % (movie['long imdb title'], movie['kind'], movie.movieID), 
                                 self.imdb_create_fxd, (movie.movieID, movie['kind'])))
                except Unicode, e:
                    print e

        except FxdImdb_Error, error:
            logger.warning('%s', error)
            dialog.utils.hide_message(dlg)
            dialog.utils.show_message(_('Connection to IMDB failed'))
            return

        dialog.utils.hide_message(dlg)

        if config.IMDB_AUTOACCEPT_SINGLE_HIT and len(items) == 1:
            self.imdb_create_fxd(arg=items[0].arg, menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('IMDB Query'), items)
            menuw.pushmenu(moviemenu)
            return

        dialog.utils.show_message(_('No information available from IMDB'))
        return


    def imdb_menu_back(self, menuw):
        """
        check how many menus we have to go back to see the item
        """
        import directory

        # check if we have to go one menu back (called directly) or
        # two (called from the item menu)
        back = 1
        if menuw.menustack[-2].selected != self.item:
            back = 2

        # maybe we called the function directly because there was only one
        # entry and we called it with an event
        if menuw.menustack[-1].selected == self.item:
            back = 0

        # update the directory
        if directory.dirwatcher:
            directory.dirwatcher.scan()

        # go back in menustack
        for i in range(back):
            menuw.delete_menu()
        menuw.refresh()


    def imdb_create_fxd(self, arg=None, menuw=None):
        """
        create fxd file for the item
        """
        dlg = dialog.utils.show_message(_('Getting data...'), 'status', 0)

        try:
            self.fxd.retrieveImdbData(arg[0], self.fxd.ctitle[1], self.fxd.ctitle[2])

        except FxdImdb_Error, error:
            logger.warning('%s', error)
            dialog.utils.hide_message(dlg)
            return

        #if this exists we got a cdrom/dvdrom
        if self.item.media and self.item.media.devicename:
            devicename = self.item.media.devicename
        else:
            devicename = None

        if self.disc_set:
            self.fxd.setDiscset(devicename, None)
        else:
            if self.item.subitems:
                for i in range(len(self.item.subitems)):
                    video = makeVideo('file', 'f%s' % i,
                                      os.path.basename(self.item.subitems[i].filename),
                                      device=devicename)
                    self.fxd.setVideo(video)
            else:
                video = makeVideo('file', 'f1', os.path.basename(self.item.filename),
                                  device=devicename)
                self.fxd.setVideo(video)
            self.fxd.setFxdFile(os.path.splitext(self.item.filename)[0])

        self.fxd.writeFxd()
        self.fxd = FxdImdb()
        self.imdb_menu_back(menuw)
        dialog.utils.hide_message(dlg)
   
