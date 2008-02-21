# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Some classes that are important to recording.
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


import sys, time, os, string, threading
try:
    import cPickle as pickle
except ImportError:
    import pickle

import config
import util.tv_util as tv_util

# The file format version number. It must be updated when incompatible
# changes are made to the file format.
TYPES_VERSION = 2

critical_section = threading.Lock()

class ScheduledRecordings:

    def __init__(self):
        self.TYPES_VERSION = TYPES_VERSION
        self.favorites_file_name = os.path.join(config.FREEVO_STATICDIR, 'favorites.pickle')
        self.schedule_file_name = os.path.join(config.FREEVO_STATICDIR, 'schedule.pickle')
        self.programList = {}
        self.favorites = self.loadFavorites()


    def addProgram(self, prog, key=None):
        if not key:
            # key = rec_interface.getKey(prog)
            pass

        if not self.programList.has_key(key):
            self.programList[key] = prog
            _debug_('added \"%s\" %s"' % (String(key), prog), 2)
        else:
            _debug_('We already know about this recording \"%s\"' % (key), DINFO)
        _debug_('"%s" items' % len(self.programList), 2)


    def removeProgram(self, prog, key=None):
        if not key:
            # key = rec_interface.getKey(prog)
            pass

        if self.programList.has_key(key):
            del self.programList[key]
            _debug_('removed \"%s\" %s"' % (String(key), prog), 2)
        else:
            _debug_('We do not know about this recording \"%s\"' % (prog), DINFO)


    def getProgramList(self):
        return self.programList


    def setProgramList(self, pl):
        self.programList = pl


    def loadFavorites(self):
        """ """
        # may need to use a critical section here
        try:
            favorites_fh = open(self.favorites_file_name, 'rb')
            self.favorites = pickle.load(favorites_fh)
            favorites_fh.close()
        except IOError, why:
            self.favorites = {}


    def saveFavorites(self):
        """ """
        favorites_fh = open(self.favorites_file_name, 'wb')
        pickle.dump(self.favorites, favorites_fh)
        favorites_fh.close()
        print 'DJW:self.favorites=%r' % (self.favorites,)
        for favorite in self.favorites:
            print 'DJW:favorite=%r' % (favorite,)
            #print 'exactchan=%r, exactdow=%r, exacttod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r' % \
            #    (exactchan, exactdow, exacttod, priority, allowDuplicates, onlyNew)


    def addFavorite(self, fav):
        print 'self.favorites=%r' % (self.favorites,)
        if self.favorites and self.favorites.has_key(fav.name):
            _debug_('We already have a favorite called "%s"' % String(fav.name), DINFO)
        else:
            _debug_('added favorite "%s"' % String(fav.name), 1)
            if self.favorites is None:
                self.favorites = {}
            self.favorites[fav.name] = fav
            self.saveFavorites()


    def removeFavorite(self, name):
        if not self.favorites.has_key(name):
            _debug_('We do not have a favorite called "%s"' % String(name), DINFO)
        else:
            _debug_('removed favorite: %s' % String(name), 1)
            del self.favorites[name]
            self.saveFavorites()


    def getFavorites(self):
        return self.favorites


    def setFavorites(self, favs):
        self.favorites = favs


    def setFavoritesList(self, favs):
        newfavs = {}

        for fav in favs:
            if not newfavs.has_key(fav.name):
                newfavs[fav.name] = fav

        self.setFavorites(newfavs)


    def clearFavorites(self):
        self.favorites = {}


class Favorite:

    def __init__(self, name=None, prog=None, exactchan=FALSE, exactdow=FALSE,
                 exacttod=FALSE, priority=0, allowDuplicates=TRUE, onlyNew=FALSE):
        self.TYPES_VERSION = TYPES_VERSION

        self.name = name
        if name:
            self.name = tv_util.progname2favname(name)
        self.priority = priority
        self.allowDuplicates = allowDuplicates
        self.onlyNew = onlyNew

        if prog:
            self.title = prog.title

            if exactchan:
                self.channel = tv_util.get_chan_displayname(prog.channel_id)
            else:
                self.channel = 'ANY'

            if exactdow:
                lt = time.localtime(prog.start)
                self.dow = lt[6]
            else:
                self.dow = 'ANY'

            if exacttod:
                lt = time.localtime(prog.start)
                self.mod = (lt[3]*60)+lt[4]
            else:
                self.mod = 'ANY'

        else:
            self.title = 'NONE'
            self.channel = 'NONE'
            self.dow = 'NONE'
            self.mod = 'NONE'


class ScheduledTvProgram:

    LOW_QUALTY  = 1
    MED_QUALTY  = 2
    HIGH_QUALTY = 3

    def __init__(self):
        self.tunerid      = None
        self.isRecording  = FALSE
        self.isFavorite   = FALSE
        self.favoriteName = None
        self.removed      = FALSE
        self.quality      = self.HIGH_QUALITY
