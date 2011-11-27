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
import logging
logger = logging.getLogger("freevo.tv.record_types")


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
        logger.log( 9, 'ScheduledRecordings.__init__()')
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
        logger.log( 9, 'loadRecordSchedule()')
        # may need to use a critical section here
        recordSchedule = None
        try:
            schedule_fh = open(config.TV_RECORD_SCHEDULE, 'rb')
            recordSchedule = pickle.load(schedule_fh)
            schedule_fh.close()
            if recordSchedule.TYPES_VERSION == 3:
                logger.info('Upgrading record schedule to version 4')
                recordSchedule.TYPES_VERSION = TYPES_VERSION
                recordSchedule.deleted_favorites = {}
        except IOError, why:
            logger.warning('loadRecordSchedule: %s', why)
            return None
        except EOFError, why:
            logger.warning('loadRecordSchedule: %s', why)
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
        logger.log( 9, 'saveRecordSchedule()')
        self.cleanPastFavoriteProgDeleted()
        try:
            schedule_fh = open(config.TV_RECORD_SCHEDULE, 'wb')
            pickle.dump(self, schedule_fh)
            schedule_fh.close()
        except IOError, why:
            logger.warning('saveRecordSchedule: %s', why)
            return None
        except Exception, why:
            import traceback
            traceback.print_exc()


    def addProgram(self, prog, key=None):
        """ Add a program to the scheduled recordings list """
        logger.log( 9, 'addProgram(%r, key=%r)', prog, key)
        if not self.program_list.has_key(key):
            self.program_list[key] = prog
            logger.log( 9, '%s "%s" added', key, prog)
        else:
            logger.info('We already know about this recording \"%s\"', key)
        logger.log( 9, '"%s" items', len(self.program_list))


    def removeProgram(self, prog, key=None):
        """ Remove a program from the scheduled recordings list """
        logger.log( 9, 'removeProgram(%r, key=%r)', prog, key)
        if self.program_list.has_key(key):
            del self.program_list[key]
            logger.log( 9, '%s "%s" removed', key, prog)
        else:
            logger.info('We do not know about this recording \"%s\"', prog)
        logger.log( 9, '"%s" items', len(self.program_list))


    def getProgramList(self):
        """ Get the scheduled recordings list """
        logger.log( 8, 'getProgramList()')
        return self.program_list


    def setProgramList(self, pl):
        """ Set the scheduled recordings list """
        logger.log( 9, 'setProgramList(pl=%r)', pl)
        self.program_list = pl


    def loadManualRecordings(self):
        """ Load the manual recordings from a file """
        logger.log( 9, 'loadManualRecordings()')
        return {}


    def saveManualRecordings(self):
        """ Save the manual recordings to a file """
        logger.log( 9, 'saveManualRecordings()')
        pass


    def loadFavorites(self):
        """ Load the favourites from a file """
        logger.log( 9, 'loadFavorites()')
        # may need to use a critical section here
        self.favorites = {}
        try:
            favorites_fh = open(config.TV_RECORD_FAVORITES, 'rb')
            self.favorites = pickle.load(favorites_fh)
            favorites_fh.close()

            if self.__normaliseFavoritePriorities()[0]:
                self.saveFavorites()
            
        except IOError, why:
            logger.warning('%s', why)
            return {}
        except EOFError, why:
            logger.warning('%s', why)
            return {}
        except Exception, why:
            import traceback
            traceback.print_exc()
            return {}
        return self.favorites


    def saveFavorites(self):
        """ Save the favourties to a file """
        logger.log( 9, 'saveFavorites()')
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
        logger.log( 9, 'addFavorite(fav=%r)', fav)
        if self.favorites and self.favorites.has_key(fav.name):
            logger.info('We already have a favorite called "%s"', String(fav.name))
            return
        logger.log( 9, 'added favorite "%s"', String(fav.name))
        if self.favorites is None:
            self.favorites = {}
        self.favorites[fav.name] = fav
        self.__normaliseFavoritePriorities()
        self.saveFavorites()


    def removeFavorite(self, name):
        """ Remove a favorite from the favorites dictonary """
        logger.log( 9, 'removeFavorite(name=%r)', name)
        if not self.favorites.has_key(name):
            logger.info('We do not have a favorite called "%s"', String(name))
            return
        logger.log( 9, 'removed favorite: %s', String(name))
        del self.favorites[name]
        self.__normaliseFavoritePriorities()
        self.saveFavorites()


    def updateFavorite(self, oldname, fav):
        """ Remove old favourite if exists and add new favourite """
        logger.log( 9, 'updateFavorite(oldname=%r, fav=%r)', oldname, fav)
        if oldname and self.favorites.has_key(oldname):
            del self.favorites[oldname]
        self.addFavourite(fav)


    def getFavorites(self):
        """ Get the favorites dictonary """
        logger.log( 9, 'getFavorites()')
        return self.favorites


    def setFavorites(self, favs):
        """ Set the favorites dictonary """
        logger.log( 9, 'setFavorites(favs=%r)', favs)
        self.favorites = favs
        self.__normaliseFavoritePriorities()


    def setFavoritesList(self, favs):
        """ Add a list of favorites to the favorites dictonary """
        logger.log( 9, 'setFavoritesList(favs=%r)', favs)
        newfavs = {}
        for fav in favs:
            if not newfavs.has_key(fav.name):
                newfavs[fav.name] = fav
        self.setFavorites(newfavs)


    def clearFavorites(self):
        """ Delete all favorites from the favorites dictonary """
        logger.log( 9, 'clearFavorites()')
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
        logger.log( 9, 'markFavoriteProgAsDeleted(%r, key=%r)', prog, key)
        if not self.deleted_favorites.has_key(key):
            self.deleted_favorites[key] = prog
            logger.log( 9, '%s "%s" added', key, prog)
        else:
            logger.info('We already know about this recording \"%s\"', key)
        logger.log( 9, '"%s" items', len(self.deleted_favorites))


    def unmarkFavoriteProgAsDeleted(self, prog, key=None):
        """ Unmark a favorite program as deleted so that it may be schedule when next scheduling favorites"""
        logger.log( 9, 'unmarkFavoriteProgAsDeleted(%r, key=%r)', prog, key)
        if self.deleted_favorites.has_key(key):
            del self.deleted_favorites[key]
            logger.log( 9, '%s "%s" removed', key, prog)
        else:
            logger.log( 9, 'We do not know about this recording \"%s\"', prog)
        logger.log( 9, '"%s" items', len(self.deleted_favorites))

    def isFavoriteProgDeleted(self, prog, key=None):
        """ 
        Determine whether the favorite program has been marked as deleted so
        should not be schedule to record when scheduling favorites.
        """
        logger.log( 9, 'isFavoriteProgDeleted(%r, key=%r)', prog, key)
        return self.deleted_favorites.has_key(key)

    def cleanPastFavoriteProgDeleted(self):
        """ Remove any favorite programs that are marked as deleted but are in the past. """
        logger.log( 9, 'Cleaning deleted favorites (current %d)', len(self.deleted_favorites))
        now = time.time()
        deleted_favorites = {}
        for key,prog in self.deleted_favorites.items():
            logger.log( 9, 'Prog: %s', prog)
            if prog.stop > now:
                deleted_favorites[key] = prog
        self.deleted_favorites = deleted_favorites
        logger.log( 9, 'After clean %d', len(self.deleted_favorites))



class Favorite:
    """
    A favourite TV programme
    """
    def __init__(self, name=None, prog=None, exactchan=False, exactdow=False, exacttod=False, priority=0,
        allowDuplicates=True, onlyNew=False):
        """ Construct a TV favorite recording """
        logger.log( 9, 'Favorite.__init__(name=%r, prog=%r, chan=%r, dow=%r, tod=%r, priority=%r, duplicates=%r, new=%r)', name, prog, exactchan, exactdow, exacttod, priority, allowDuplicates, onlyNew)

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
        logger.log( 9, 'ScheduledTvProgram.__init__()')
        self.tunerid      = None
        self.isRecording  = False
        self.isFavorite   = False
        self.favoriteName = None
        self.removed      = False
        self.quality      = ScheduledTvProgram.HIGH_QUALITY
