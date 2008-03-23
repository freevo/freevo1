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
    """
    """
    def __init__(self):
        """ """
        _debug_('ScheduledRecordings.__init__()', 2)
        self.TYPES_VERSION = TYPES_VERSION
        self.favorites_file_name = os.path.join(config.FREEVO_STATICDIR, 'favorites.pickle')
        self.favorites_text_name = os.path.join(config.FREEVO_STATICDIR, 'favorites.txt')
        self.schedule_file_name = os.path.join(config.FREEVO_STATICDIR, 'schedule.pickle')
        self.program_list = {}
        #self.favorites = self.loadFavorites()
        self.favorites = {}


    def initialize(self):
        if not hasattr(self, 'favorites_file_name'):
            self.favorites_file_name = os.path.join(config.FREEVO_STATICDIR, 'favorites.pickle')
        if not hasattr(self, 'favorites_text_name'):
            self.favorites_text_name = os.path.join(config.FREEVO_STATICDIR, 'favorites.txt')
        if not hasattr(self, 'schedule_file_name'):
            self.schedule_file_name = os.path.join(config.FREEVO_STATICDIR, 'schedule.pickle')
        if not hasattr(self, 'program_list'):
            self.program_list = {}
        if not hasattr(self, 'favorites'):
            self.favorites = self.loadFavorites()


    def loadRecordSchedule(self):
        """ Load the recording schedule from a file """
        _debug_('loadRecordSchedule()', 2)
        # may need to use a critical section here
        self.schedules = {}
        try:
            schedules_fh = open(self.schedule_file_name, 'rb')
            self.program_list = pickle.load(schedules_fh)
            schedules_fh.close()
        except IOError, why:
            return {}
        return self.schedules


    def saveRecordSchedule(self):
        """ Save the recording schedule to a file """
        _debug_('saveRecordSchedule()', 2)
        # save the favourites as a pickle file
        try:
            schedules_fh = open(self.schedule_file_name, 'wb')
            pickle.dump(self.program_list, schedules_fh)
            schedules_fh.close()
        except Exception, why:
            import traceback
            traceback.print_stack()
            print why


    def addProgram(self, prog, key=None):
        """ """
        _debug_('addProgram(prog=%r, key=%r)' % (prog, key), 2)
        if not key:
            # key = rec_interface.getKey(prog)
            pass

        if not self.program_list.has_key(key):
            self.program_list[key] = prog
            _debug_('added \"%s\" %s"' % (String(key), prog), 2)
        else:
            _debug_('We already know about this recording \"%s\"' % (key), DINFO)
        _debug_('"%s" items' % len(self.program_list), 2)


    def removeProgram(self, prog, key=None):
        """ """
        _debug_('removeProgram(prog=%r, key=%r)' % (prog, key), 2)
        if not key:
            # key = rec_interface.getKey(prog)
            pass

        if self.program_list.has_key(key):
            del self.program_list[key]
            _debug_('removed %r %s"' % (key, prog), 2)
        else:
            _debug_('We do not know about this recording \"%s\"' % (prog), DINFO)


    def getProgramList(self):
        """ """
        _debug_('getProgramList()', 3)
        return self.program_list


    def setProgramList(self, pl):
        """ """
        _debug_('setProgramList(pl=%r)' % (pl,), 2)
        self.program_list = pl


    def loadFavorites(self):
        """ Load the favourites from a file """
        _debug_('loadFavorites()', 2)
        # may need to use a critical section here
        self.favorites = {}
        try:
            favorites_fh = open(self.favorites_file_name, 'rb')
            self.favorites = pickle.load(favorites_fh)
            favorites_fh.close()
        except IOError, why:
            return {}
        return self.favorites


    def saveFavorites(self):
        """ Save the favourties to a file """
        _debug_('saveFavorites()', 2)
        # save the favourites as a pickle file
        try:
            favorites_fh = open(self.favorites_file_name, 'wb')
            pickle.dump(self.favorites, favorites_fh)
            favorites_fh.close()
        except Exception, why:
            import traceback
            traceback.print_stack()
            print why
        # save the favourites as a text file
        try:
            favorites_fh = open(self.favorites_text_name, 'w')
            print >>favorites_fh, TYPES_VERSION
            for favourite in self.favorites.keys():
                f = self.favorites[favourite]
                print >>favorites_fh, \
                    '%(name)r %(title)r %(channel)r %(dow)r %(mod)r %(allowDuplicates)r %(onlyNew)r %(priority)r' % \
                    f.__dict__
            favorites_fh.close()
        except Exception, why:
            import traceback
            traceback.print_stack()
            print why


    def addFavorite(self, fav):
        """ """
        _debug_('addFavorite(fav=%r)' % (fav,), 2)
        if self.favorites and self.favorites.has_key(fav.name):
            _debug_('We already have a favorite called "%s"' % String(fav.name), DINFO)
            return
        _debug_('added favorite "%s"' % String(fav.name), 2)
        if self.favorites is None:
            self.favorites = {}
        self.favorites[fav.name] = fav
        self.saveFavorites()


    def removeFavorite(self, name):
        """ """
        _debug_('removeFavorite(name=%r)' % (name,), 2)
        if not self.favorites.has_key(name):
            _debug_('We do not have a favorite called "%s"' % String(name), DINFO)
            return
        _debug_('removed favorite: %s' % String(name), 2)
        del self.favorites[name]
        self.saveFavorites()


    def updateFavorite(self, oldname, fav):
        """ Remove old favourite if exists and add new favourite
        """
        _debug_('updateFavorite(oldname=%r, fav=%r)' % (oldname, fav), 2)
        if oldname:
            self.removeFavorite(name)
        self.addFavourite(fav)


    def getFavorites(self):
        """ """
        _debug_('getFavorites()', 2)
        return self.favorites


    def setFavorites(self, favs):
        """ """
        _debug_('setFavorites(favs=%r)' % (favs,), 2)
        self.favorites = favs


    def setFavoritesList(self, favs):
        """ """
        _debug_('setFavoritesList(favs=%r)' % (favs,), 2)
        newfavs = {}
        for fav in favs:
            if not newfavs.has_key(fav.name):
                newfavs[fav.name] = fav
        self.setFavorites(newfavs)


    def clearFavorites(self):
        """ """
        _debug_('clearFavorites()', 2)
        self.favorites = {}


class Favorite:
    """
    A favourite TV programme
    """
    def __init__(self, name=None, prog=None, exactchan=FALSE, exactdow=FALSE, exacttod=FALSE, priority=0,
        allowDuplicates=TRUE, onlyNew=FALSE):
        """ """
        _debug_('Favorite.__init__(self, name=%r, prog=%r, exactchan=%r, exactdow=%r, exacttod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)' % (name, prog, exactchan, exactdow, exacttod, priority, allowDuplicates, onlyNew), 2)
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
    """
    """
    LOW_QUALTY  = 1
    MED_QUALTY  = 2
    HIGH_QUALTY = 3

    def __init__(self):
        """ """
        _debug_('ScheduledTvProgram.__init__()', 2)
        self.tunerid      = None
        self.isRecording  = FALSE
        self.isFavorite   = FALSE
        self.favoriteName = None
        self.removed      = FALSE
        self.quality      = self.HIGH_QUALITY
