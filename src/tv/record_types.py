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


import sys, time, os, string, codecs
try:
    import cPickle as pickle
except ImportError:
    import pickle

import config
import util.tv_util as tv_util
import time

# The file format version number. It must be updated when incompatible
# changes are made to the file format.
TYPES_VERSION = 4

schedule_locked = False


class ScheduledRecordings:
    """
    The schedule recordings class
    """
    def __init__(self):
        """ Construct the scheduled TV recordings """
        _debug_('ScheduledRecordings.__init__()', 2)
        self.TYPES_VERSION = TYPES_VERSION
        self.program_list = {}
        self.manual_recordings = self.loadManualRecordings()
        self.favorites = self.loadFavorites()
        self.deleted_favorites = {}
        global schedule_locked
        schedule_locked = False


    def __str__(self):
        s = 'Scheduled Recordings v%s\n' % (self.TYPES_VERSION)
        s += 'Program List:\n'
        program_list = self.program_list.keys()
        if program_list:
            program_list.sort()
            for p in program_list:
                s += '  '+String(self.program_list[p])+'\n'
        else:
            s += 'No programs scheduled to record\n'
        s += 'Favorites List:\n'
        favorite_list = self.favorites.keys()
        if favorite_list:
            favorite_list.sort()
            for f in favorite_list:
                s += '  '+String(self.favorites[f])+'\n'
        else:
            s += 'No Favorites\n'
        return s


    def lock(self):
        global schedule_locked
        schedule_locked = True


    def unlock(self):
        global schedule_locked
        if schedule_locked:
            schedule_locked = False
            self.saveRecordSchedule()


    def get_locked(self):
        global schedule_locked
        return schedule_locked


    def loadRecordSchedule(self):
        """ Load the tv recording schedule from a pickle file """
        _debug_('loadRecordSchedule()', 2)
        # may need to use a critical section here
        recordSchedule = None
        try:
            schedule_fh = open(config.TV_RECORD_SCHEDULE, 'rb')
            recordSchedule = pickle.load(schedule_fh)
            schedule_fh.close()
            if recordSchedule.TYPES_VERSION == 3:
                _debug_('Upgrading record schedule to version 4', DINFO)
                recordSchedule.TYPES_VERSION = TYPES_VERSION
                recordSchedule.deleted_favorites = {}
        except IOError, why:
            _debug_('loadRecordSchedule: %s' % why, DWARNING)
            return None
        except EOFError, why:
            _debug_('loadRecordSchedule: %s' % why, DWARNING)
            return None
        except Exception, why:
            import traceback
            traceback.print_exc()
            return None
        return recordSchedule


    def saveRecordSchedule(self):
        """ Save the tv recording schedule to a pickle file """
        global schedule_locked
        if schedule_locked:
            return
        _debug_('saveRecordSchedule()', 2)
        self.cleanPastFavoriteProgDeleted()
        try:
            schedule_fh = open(config.TV_RECORD_SCHEDULE, 'wb')
            pickle.dump(self, schedule_fh)
            schedule_fh.close()
        except IOError, why:
            _debug_('saveRecordSchedule: %s' % why, DWARNING)
            return None
        except Exception, why:
            import traceback
            traceback.print_exc()


    def addProgram(self, prog, key=None):
        """ Add a program to the scheduled recordings list """
        _debug_('addProgram(%r, key=%r)' % (prog, key), 2)
        if not self.program_list.has_key(key):
            self.program_list[key] = prog
            _debug_('%s "%s" added' % (key, prog), 2)
        else:
            _debug_('We already know about this recording \"%s\"' % (key), DINFO)
        _debug_('"%s" items' % len(self.program_list), 2)


    def removeProgram(self, prog, key=None):
        """ Remove a program from the scheduled recordings list """
        _debug_('removeProgram(%r, key=%r)' % (prog, key), 2)
        if self.program_list.has_key(key):
            del self.program_list[key]
            _debug_('%s "%s" removed' % (key, prog), 2)
        else:
            _debug_('We do not know about this recording \"%s\"' % (prog), DINFO)
        _debug_('"%s" items' % len(self.program_list), 2)


    def getProgramList(self):
        """ Get the scheduled recordings list """
        _debug_('getProgramList()', 3)
        return self.program_list


    def setProgramList(self, pl):
        """ Set the scheduled recordings list """
        _debug_('setProgramList(pl=%r)' % (pl,), 2)
        self.program_list = pl


    def loadManualRecordings(self):
        """ Load the manual recordings from a file """
        _debug_('loadManualRecordings()', 2)
        return {}


    def saveManualRecordings(self):
        """ Save the manual recordings to a file """
        _debug_('saveManualRecordings()', 2)
        pass


    def loadFavorites(self):
        """ Load the favourites from a file """
        _debug_('loadFavorites()', 2)
        # may need to use a critical section here
        self.favorites = {}
        try:
            favorites_fh = open(config.TV_RECORD_FAVORITES, 'rb')
            self.favorites = pickle.load(favorites_fh)
            favorites_fh.close()

            if self.__normaliseFavoritePriorities()[0]:
                self.saveFavorites()
            
        except IOError, why:
            _debug_('%s' % (why,), DWARNING)
            return {}
        except EOFError, why:
            _debug_('%s' % (why,), DWARNING)
            return {}
        except Exception, why:
            import traceback
            traceback.print_exc()
            return {}
        return self.favorites


    def saveFavorites(self):
        """ Save the favourties to a file """
        _debug_('saveFavorites()', 2)
        # save the favourites as a pickle file
        try:
            favorites_fh = open(config.TV_RECORD_FAVORITES, 'wb')
            pickle.dump(self.favorites, favorites_fh)
            favorites_fh.close()
        except Exception, why:
            import traceback
            traceback.print_exc()
        # save the favourites as a text file
        try:
            favorites_fh = codecs.open(config.TV_RECORD_FAVORITES_LIST, 'w', encoding='utf-8')
            print >>favorites_fh, TYPES_VERSION
            for favourite in self.favorites.keys():
                f = self.favorites[favourite]
                line = "'%(name)s' '%(title)s' '%(channel)s' '%(dow)s' '%(mod)s' " % f.__dict__
                line += "%(allowDuplicates)s %(onlyNew)s '%(priority)s'" % f.__dict__
                print >>favorites_fh, line
            favorites_fh.close()
        except Exception, why:
            import traceback
            traceback.print_exc()


    def addFavorite(self, fav):
        """ Add a favorite to the favorites dictonary """
        _debug_('addFavorite(fav=%r)' % (fav,), 2)
        if self.favorites and self.favorites.has_key(fav.name):
            _debug_('We already have a favorite called "%s"' % String(fav.name), DINFO)
            return
        _debug_('added favorite "%s"' % String(fav.name), 2)
        if self.favorites is None:
            self.favorites = {}
        self.favorites[fav.name] = fav
        self.__normaliseFavoritePriorities()
        self.saveFavorites()


    def removeFavorite(self, name):
        """ Remove a favorite from the favorites dictonary """
        _debug_('removeFavorite(name=%r)' % (name,), 2)
        if not self.favorites.has_key(name):
            _debug_('We do not have a favorite called "%s"' % String(name), DINFO)
            return
        _debug_('removed favorite: %s' % String(name), 2)
        del self.favorites[name]
        self.__normaliseFavoritePriorities()
        self.saveFavorites()


    def updateFavorite(self, oldname, fav):
        """ Remove old favourite if exists and add new favourite """
        _debug_('updateFavorite(oldname=%r, fav=%r)' % (oldname, fav), 2)
        if oldname and self.favorites.has_key(oldname):
            del self.favorites[oldname]
        self.addFavourite(fav)


    def getFavorites(self):
        """ Get the favorites dictonary """
        _debug_('getFavorites()', 2)
        return self.favorites


    def setFavorites(self, favs):
        """ Set the favorites dictonary """
        _debug_('setFavorites(favs=%r)' % (favs,), 2)
        self.favorites = favs
        self.__normaliseFavoritePriorities()


    def setFavoritesList(self, favs):
        """ Add a list of favorites to the favorites dictonary """
        _debug_('setFavoritesList(favs=%r)' % (favs,), 2)
        newfavs = {}
        for fav in favs:
            if not newfavs.has_key(fav.name):
                newfavs[fav.name] = fav
        self.setFavorites(newfavs)


    def clearFavorites(self):
        """ Delete all favorites from the favorites dictonary """
        _debug_('clearFavorites()', 2)
        self.favorites = {}
    
    def adjustFavoritePriority(self, fav, mod):
        """ Adjust the priority of the specified favorite by mod degrees """
        prio_list = self.__normaliseFavoritePriorities()[1]
        
        pos = prio_list.index(fav)
        new_pos = pos + mod
        if new_pos < 0:
            new_pos = 0
            
        if new_pos > len(prio_list):
            new_pos = len(prio_list)
        # Nothing to do
        if pos == new_pos:
            return False
        
        del prio_list[pos]
        
        
        prio_list.insert(new_pos, fav)
        
        # Update the priorities
        for i, fav in enumerate(prio_list):
            fav.priority = i
        return True
        
    
    def __normaliseFavoritePriorities(self):
        """ Normalise favorite priorities so they run from 0 to len(favs)-1 """
        def fav_priority_cmp(a,b):
            if int(a.priority) == int(b.priority):
                return cmp(a.name, b.name)
            return cmp(int(a.priority), int(b.priority))
            
        prio_list = self.favorites.values()
        prio_list.sort(fav_priority_cmp)
        save = False
        for i, fav in enumerate(prio_list):
            if fav.priority != i:
                save = True
                fav.priority = i
        
        return (save, prio_list)   

    def markFavoriteProgAsDeleted(self, prog, key=None):
        """ Mark a favorite program as not to be schedule when next scheduling favorites"""
        _debug_('markFavoriteProgAsDeleted(%r, key=%r)' % (prog, key), 2)
        if not self.deleted_favorites.has_key(key):
            self.deleted_favorites[key] = prog
            _debug_('%s "%s" added' % (key, prog), 2)
        else:
            _debug_('We already know about this recording \"%s\"' % (key), DINFO)
        _debug_('"%s" items' % len(self.deleted_favorites), 2)


    def unmarkFavoriteProgAsDeleted(self, prog, key=None):
        """ Unmark a favorite program as deleted so that it may be schedule when next scheduling favorites"""
        _debug_('unmarkFavoriteProgAsDeleted(%r, key=%r)' % (prog, key), 2)
        if self.deleted_favorites.has_key(key):
            del self.deleted_favorites[key]
            _debug_('%s "%s" removed' % (key, prog), 2)
        else:
            _debug_('We do not know about this recording \"%s\"' % (prog), 2)
        _debug_('"%s" items' % len(self.deleted_favorites), 2)

    def isFavoriteProgDeleted(self, prog, key=None):
        """ 
        Determine whether the favorite program has been marked as deleted so
        should not be schedule to record when scheduling favorites.
        """
        _debug_('isFavoriteProgDeleted(%r, key=%r)' % (prog, key), 2)
        return self.deleted_favorites.has_key(key)

    def cleanPastFavoriteProgDeleted(self):
        """ Remove any favorite programs that are marked as deleted but are in the past. """
        _debug_('Cleaning deleted favorites (current %d)' % (len(self.deleted_favorites),), 2)
        now = time.time()
        deleted_favorites = {}
        for key,prog in self.deleted_favorites.items():
            _debug_('Prog: %s'% prog, 2)
            if prog.stop > now:
                deleted_favorites[key] = prog
        self.deleted_favorites = deleted_favorites
        _debug_('After clean %d'% (len(self.deleted_favorites),), 2)



class Favorite:
    """
    A favourite TV programme
    """
    def __init__(self, name=None, prog=None, exactchan=False, exactdow=False, exacttod=False, priority=0,
        allowDuplicates=True, onlyNew=False):
        """ Construct a TV favorite recording """
        _debug_('Favorite.__init__(name=%r, prog=%r, chan=%r, dow=%r, tod=%r, priority=%r, duplicates=%r, new=%r)' % \
            (name, prog, exactchan, exactdow, exacttod, priority, allowDuplicates, onlyNew), 2)
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


    def __str__(self):
        week_days = (_('Mon'), _('Tue'), _('Wed'), _('Thu'), _('Fri'), _('Sat'), _('Sun'))
        s = '%-20s' % (String(self.name),)
        s += '%-20s' % ('"'+String(self.title)+'"',)
        s += '%-12s' % (String(self.channel),)
        if isinstance(self.dow, int):
            s += '%-4s ' % (week_days[self.dow],)
        else:
            s += '%-4s ' % (String(self.dow),)
        if isinstance(self.mod, int):
            s += '%02d:%02d  ' % (self.mod / 60, self.mod % 60)
        else:
            s += '%-6s ' % (String(self.mod),)
        s += '%-8s' % (self.allowDuplicates and 'dups' or 'no-dups')
        s += '%-9s' % (self.onlyNew and 'only-new' or 'all-shows')
        return s



class ScheduledTvProgram:
    """
    A scheduled TV programme (Not used)
    """
    LOW_QUALITY  = 1
    MED_QUALITY  = 2
    HIGH_QUALITY = 3

    def __init__(self):
        """ Construct a ScheduledTvProgram instance """
        _debug_('ScheduledTvProgram.__init__()', 2)
        self.tunerid      = None
        self.isRecording  = False
        self.isFavorite   = False
        self.favoriteName = None
        self.removed      = False
        self.quality      = ScheduledTvProgram.HIGH_QUALITY
