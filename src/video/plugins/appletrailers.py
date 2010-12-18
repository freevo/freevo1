# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# appletrailers.py - Plugin for streaming trailers from apple.com
# -----------------------------------------------------------------------
#
# Notes:
#   Add "plugin.activate('video.appletrailers')" in local_conf.py
#   to activate
# Todo:
#
# -----------------------------------------------------------------------
# Copyright (C) 2006 Pierre Ossman
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
import urllib

import socket
socket.setdefaulttimeout(5)

import config
import plugin
import menu
import stat
import time
import threading
import util.fileops
import util.misc

import kaa

from item import Item
from video.videoitem import VideoItem
from gui.ProgressBox import ProgressBox

import applelib

MAX_CACHE_AGE = (60 * 60) * 8 # 8 hours

cachedir = os.path.join(config.FREEVO_CACHEDIR, 'appletrailers')
if not os.path.isdir(cachedir):
    os.mkdir(cachedir,
            stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))

def _fetch_image(url, download=False):
    idx = url.rfind('/')
    if idx == -1:
        return None

    fn = url.replace('/','_')
    fn = os.path.join(cachedir, fn)

    if download and not os.path.exists(fn):
        urllib.FancyURLopener.version = 'QuickTime/7.5'
        urllib.urlretrieve(url,fn)

    return fn

class PluginInterface(plugin.MainMenuPlugin):
    """
    A freevo interface to http://www.apple.com/trailers

    plugin.activate('video.appletrailers')
    """
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
        # Clean up any old pickle files
        old_pfile = os.path.join(cachedir, 'data')
        if os.path.isfile(old_pfile):
            os.unlink(old_pfile)
        

    def config(self):

        return [('APPLETRAILERS_RESOLUTION',
                 '',
                 'Selects the resolution of the trailers, options are \'\'(Default) for 640p, \'480p\' and \'720p\'' ),
                 ('APPLETRAILERS_DATE_FORMAT',
                 '%y-%m-%d',
                 'How to format the release date of a film')]

    def items(self, parent):
        return [ BrowseMainMenu(parent) ]
        


class TrailerItem(VideoItem):
    def __init__(self, trailer, parent):
        VideoItem.__init__(self, trailer.preview_url, parent)
        self.trailer = trailer
        self.name = trailer.title
        self.type = 'video'
        self.mplayer_options = '-user-agent QuickTime/7.5'

        self.mode = ''
        self.files = ''
        self.image = _fetch_image(trailer.poster)
        self.description = trailer.description
        self.description += _('\n\nGenres: ') + ','.join(trailer.genres)
        if trailer.release_date:
            self.description += _('\n\nDate: ') + trailer.release_date.strftime(config.APPLETRAILERS_DATE_FORMAT)
        else:
            self.description += _('\n\nDate: Unknown')
        self.description += ('\n\nRating: ') + trailer.rating
        self.description += ('\n\nDirector: ') + trailer.director
        self.description += ('\n\nRuntime: %d minutes') % trailer.runtime
        self.plot = self.description


class BrowseByTitle(Item):
    def __init__(self, name, items, parent):
        Item.__init__(self, parent)
        self.name = name
        self.title = _('Trailers')
        self.items = items

    def actions(self):
        return [ (self.make_menu, _('Titles')) ]

    def make_menu(self, arg=None, menuw=None):
        entries = []
        for trailer in self.items:
            entries.append(TrailerItem(trailer, self))
        thread = threading.Thread(target=self.download_posters)
        thread.start()
        menuw.pushmenu(menu.Menu(self.title, entries))

    def download_posters(self):
        for trailer in self.items:
            _fetch_image(trailer.poster, True)


class BrowseByMenu(Item):
    def __init__(self, title, hash, parent):
        Item.__init__(self, parent)
        self.name = title
        self.hash = hash


    def actions(self):
        return [ (self.make_menu, _('Browse')) ]


    def make_menu(self, arg=None, menuw=None):
        items = []
        for key,trailers in self.hash.items():
            items.append(BrowseByTitle(unicode(key), trailers, self))
        items.sort(lambda x,y: cmp(x.name, y.name))
        menuw.pushmenu(menu.Menu(self.name, items))


class BrowseByReleaseDate(BrowseByMenu):
    def __init__(self, hash, parent):
        BrowseByMenu.__init__(self, _('Browse by Release Date'), hash, parent)


    def make_menu(self, arg=None, menuw=None):
        items = []
        dates = self.hash.keys()
        def cmp_date(x,y):
            if x == y:
                return 0
            if x == None:
                return 1
            if y == None:
                return -1
            return cmp(x,y)
        dates.sort(cmp_date)
        
        for date in dates:
            trailers = self.hash[date]
            if date is None:
                title = _('Unknown')
            else:
                title = date.strftime(config.APPLETRAILERS_DATE_FORMAT)
            items.append(BrowseByTitle(title, trailers, self))

        menuw.pushmenu(menu.Menu(self.name, items))


class BrowseMainMenu(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.name = 'Apple Trailers'
        self.type = 'trailers'
        self.image = config.IMAGE_DIR + '/apple-trailers.png'
        self.trailers = None
        self.inprogress = kaa.ThreadCallable(self.download_trailers)()

    def download_trailers(self):
        pfile = os.path.join(cachedir, 'trailers.pickle')
        if os.path.isfile(pfile):
            self.trailers = util.fileops.read_pickle(pfile)
            old_posters = []
            for trailer in self.trailers.trailers:
                old_posters.append(_fetch_image(trailer.poster))
            old_posters = set(old_posters)

            s = os.stat(pfile)

            if self.trailers.resolution == config.APPLETRAILERS_RESOLUTION or  \
              (time.time() - s.st_mtime) > (60*60): # Over an hour ago
                if self.trailers.update_feed():
                    new_posters = []
                    for trailer in self.trailers.trailers:
                        new_posters.append(_fetch_image(trailer.poster))
                    new_posters = set(new_posters)
                else:
                    new_posters = old_posters
        
            else:
                self.trailers = None
        else:
            old_posters = set()


        if self.trailers is None:
            self.trailers = applelib.Trailers(config.APPLETRAILERS_RESOLUTION)
            util.fileops.save_pickle(self.trailers, pfile)
            new_posters = []
            for trailer in self.trailers.trailers:
                new_posters.append(_fetch_image(trailer.poster))
            new_posters = set(new_posters)
        
        # Remove any posters that are no longer required
        for poster_file in old_posters - set(new_posters):
            try:
                os.unlink(poster_file)
            except:
                pass


    def actions(self):
        return [ (self.make_menu, 'Browse by') ]


    def make_menu(self, arg=None, menuw=None):
        self.inprogress.wait()
        menuw.pushmenu(menu.Menu('Apple Trailers',
                [ BrowseByTitle(_("Browse by Title"), self.trailers.trailers, self),
                  BrowseByReleaseDate(self.trailers.release_dates, self),
                  BrowseByMenu(_('Browse by Genre'), self.trailers.genres, self),
                  BrowseByMenu(_('Browse by Actor'), self.trailers.actors, self),
                  BrowseByMenu(_('Browse by Director'), self.trailers.directors, self),
                  BrowseByMenu(_('Browse by Studio'), self.trailers.studios, self),
                  BrowseByMenu(_('Browse by Rating'), self.trailers.ratings, self)]))
