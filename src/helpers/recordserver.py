# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A network aware TV recording server.
# -----------------------------------------------------------------------
# $Id$
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
logger = logging.getLogger("freevo.helpers.recordserver")


import sys, time, os, re, pwd, stat, threading, hashlib, datetime, copy
from threading import Thread
try:
    import cPickle as pickle
except ImportError:
    import pickle
import logging
import __builtin__

import config
from util import vfs

import kaa
import kaa.rpc
from kaa import EventHandler
from kaa import AtTimer

# The twisted modules will go away when all the recordserver clients
# have been updated to use kaa.rpc

from video.commdetectclient import initCommDetectJob
from video.commdetectclient import queueIt as queueCommdetectJob
from video.commdetectclient import listJobs as listCommdetectJobs
from video.commdetectclient import connectionTest as commdetectConnectionTest

from video.encodingclient import EncodingClientActions

import tv.record_types
from tv.record_types import TYPES_VERSION
from tv.record_types import ScheduledRecordings
import tv.epg
import util.tv_util as tv_util
import plugin
import util.popen3
from tv.channels import FreevoChannels, CHANNEL_ID
from util.videothumb import snapshot
from event import *


logger.info('PLUGIN_RECORD: %s', config.plugin_record)

plugin.init_special_plugin(config.plugin_record)

def print_plugin_warning():
    warning = """
    *************************************************
    **  Warning: No recording plugin registered.   **
    **           Check your local_conf.py for a    **
    **           bad "plugin_record =" line or     **
    **           this log for a plugin failure.    **
    **           Recordings will fail!             **
    *************************************************"""
    logger.warning(warning)


if not plugin.getbyname('RECORD'):
    print_plugin_warning()


class RecordServer:

    def __init__(self, debug=False):
        """ Initialise the Record Server class """
        logger.log( 9, 'RecordServer.__init__(debug=%r)', debug)
        self.debug = debug
        self.lock = threading.RLock()
        self.schedule_lock = threading.Lock()
        self.fc = FreevoChannels()
        # XXX: In the future we should have one lock per VideoGroup.
        self.tv_lockfile = None
        self.vg = None
        self.previouslyRecordedShows = None
        self.delayed_recording = None
        self.schedule = ScheduledRecordings()
        self.updateFavoritesSchedule()
        self.es = EncodingClientActions()


    @kaa.rpc.expose('ping')
    def pingtest(self):
        logger.log( 9, 'pingtest()')
        return True


    @kaa.rpc.expose('isRecording')
    def isRecording(self):
        logger.log( 9, 'isRecording()')
        recording = glob.glob(os.path.join(config.FREEVO_CACHEDIR + 'record.*'))
        return (len(recording) > 0, recording)


    def progsTimeCompare(self, first, second):
        t1 = first.split(':')[-1]
        t2 = second.split(':')[-1]
        try:
            return int(float(t1)) - int(float(t2))
        except ArithmeticError:
            pass
        return 0


    def findOverlaps(self, schedule):
        logger.log( 9, 'findOverlaps(schedule=%r)', schedule)
        progs = schedule.getProgramList()
        proglist = list(progs)
        proglist.sort(self.progsTimeCompare)
        for progitem in proglist:
            progs[progitem].overlap = 0
        for i in range(0, len(proglist)-1):
            thisprog = progs[proglist[i]]
            nextprog = progs[proglist[i+1]]
            if thisprog.stop > nextprog.start:
                thisprog.overlap = 1
                nextprog.overlap = 1
                logger.info('Overlap:\n%s\n%s', thisprog, nextprog)


    @kaa.rpc.expose('findNextProgram')
    def findNextProgram(self, isrecording=False):
        logger.log( 9, 'findNextProgram(isrecording=%r)', isrecording)

        next_program = None
        progs = self.getScheduledRecordings().getProgramList()
        proglist = list(progs)
        proglist.sort(self.progsTimeCompare)
        now = self.timenow()
        timenow = time.localtime(now)
        for progitem in proglist:
            prog = progs[progitem]
            logger.log( 9, '%s', prog)

            if now >= prog.start-config.TV_RECORD_PADDING_PRE and now < prog.stop+config.TV_RECORD_PADDING_POST:
                recording = True
                if isrecording:
                    logger.log( 9, 'isrecording is %s', prog)
                    return (True, prog)
            else:
                recording = False

            endtime = time.strftime(config.TV_TIME_FORMAT, time.localtime(prog.stop+config.TV_RECORD_PADDING_POST))
            logger.log( 9, '%s is recording %s stopping at %s', prog.title, recording and 'yes' or 'no', endtime)

            if now > prog.stop + config.TV_RECORD_PADDING_POST:
                logger.log( 9, '%s: finished %s > %s', prog.title, time.strftime('%H:%M:%S', timenow), endtime)
                continue

            if not recording:
                next_program = prog
                break

        if next_program is None:
            logger.log( 9, 'No program scheduled to record')
            return (False, next_program)

        logger.log( 9, 'next is %s', next_program)
        return (True, next_program)


    @kaa.rpc.expose('isPlayerRunning')
    def isPlayerRunning(self):
        """
        Test is the player is running

        TODO: real player running test, check /dev/videoX.  This could go into the upsoon client
        @returns: the state of a player, mplayer, xine, etc.
        """
        logger.log( 9, 'isPlayerRunning()')
        res = (os.path.exists(os.path.join(config.FREEVO_CACHEDIR, 'playing')))
        logger.log( 9, 'isPlayerRunning=%r', res)
        return res


    @kaa.rpc.expose('getScheduledRecordings')
    def _getScheduledRecordings(self):
        schedule = self.getScheduledRecordings()
        return schedule.program_list.values()

    def getScheduledRecordings(self):
        logger.log( 9, 'getScheduledRecordings()')
        file_ver = None
        schedule = None

        if os.path.isfile(config.TV_RECORD_SCHEDULE):
            logger.log( 9, 'reading cache (%r)', config.TV_RECORD_SCHEDULE)
            if hasattr(self, 'schedule_cache'):
                mod_time, schedule = self.schedule_cache
                try:
                    if os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME] == mod_time:
                        logger.log( 9, 'using cached schedule')
                        return schedule
                except OSError, why:
                    logger.error('Failed to stat %r: %s', config.TV_RECORD_SCHEDULE, why)
                    pass

            schedule = self.schedule.loadRecordSchedule()

            try:
                file_ver = schedule.TYPES_VERSION
            except AttributeError:
                logger.info('The cache does not have a version and must be recreated')

            if file_ver != TYPES_VERSION:
                logger.info('ScheduledRecordings version number %s is stale (new is %s), must be reloaded', file_ver, TYPES_VERSION)

                schedule = None
            else:
                logger.info('Got ScheduledRecordings (version %s).', file_ver)

        if not schedule:
            logger.info('Created a new ScheduledRecordings')
            schedule = ScheduledRecordings()
            self.saveScheduledRecordings(schedule)

        logger.debug('ScheduledRecordings has %s items.', len(schedule.program_list))

        try:
            mod_time = os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME]
            self.schedule_cache = mod_time, schedule
        except OSError:
            pass
        return schedule


    #@kaa.rpc.expose('saveScheduledRecordings')
    def saveScheduledRecordings(self, schedule=None):
        """ Save the schedule to disk """
        logger.log( 9, 'saveScheduledRecordings(schedule=%r)', schedule)

        if not schedule:
            logger.info('making a new ScheduledRecordings')
            schedule = ScheduledRecordings()

        self.findOverlaps(schedule)

        schedule.saveRecordSchedule()

        try:
            mod_time = os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME]
            self.schedule_cache = mod_time, schedule
        except OSError:
            pass

        return (True, _('scheduled recordings saved'))


    def loadPreviouslyRecordedShows(self):
        """ Load the saved set of recorded shows """
        logger.log( 9, 'loadPreviouslyRecordedShows()')
        if self.previouslyRecordedShows:
            return

        cacheFile = os.path.join(config.FREEVO_CACHEDIR, 'previouslyRecorded.pickle')
        try:
            self.previouslyRecordedShows = pickle.load(open(cacheFile, 'r'))
        except IOError:
            self.previouslyRecordedShows = {}
            pass


    def savePreviouslyRecordedShows(self):
        """ Save the set of recorded shows """
        logger.log( 9, 'savePreviouslyRecordedShows()')
        if not self.previouslyRecordedShows:
            return

        cacheFile = os.path.join(config.FREEVO_CACHEDIR, 'previouslyRecorded.pickle')
        pickle.dump(self.previouslyRecordedShows, open(cacheFile, 'w'))


    def newEpisode(self, prog=None):
        """ Return true if this is a new episode of 'prog' """
        logger.log( 9, 'newEpisode(prog=%r)', prog)
        todayStr = datetime.date.today().strftime('%Y%m%d')
        progStr = str(prog.date)
        logger.info('Program Date: "%s"', progStr)
        logger.info('Todays Date : "%s"', todayStr)
        if (len(progStr) == 8):
            logger.info('Good date format')
            #Year
            todaysYear = (todayStr[0:4])
            progYear = (progStr[0:4])
            #Month
            todaysMonth = (todayStr[4:-2])
            progMonth = (progStr[4:-2])
            #Day
            todaysDay = (todayStr[6:])
            progDay = (progStr[6:])
            if todaysYear > progYear:
                #program from a previous year
                return False
            elif progYear > todaysYear:
                #program in the future
                return True
            else:
                logger.info('Same year')
                #program in the same year
                if todaysMonth > progMonth:
                    #program in a previous month
                    return False
                elif progMonth > todaysMonth:
                    #program in the future
                    return True
                else:
                    logger.info('Same month')
                    #program in the same month
                    if todaysDay > progDay:
                        #program was previous aired this month
                        return False
                    else:
                        logger.info('Same day or in the upcoming month')
                        #program is today or in the upcoming days
                        return True
        else:
            logger.info('No good date format, assuming new Episode to be on the safe side')
            return True


    def shrink(self, text):
        """ Shrink a string by removing all spaces and making it
        lower case and then returning the MD5 digest of it. """
        logger.log( 9, 'shrink(text=%r)', text)
        if text:
            text = hashlib.md5(text.lower().replace(' ', '')).hexdigest()
        else:
            text = ''
        return text


    def getPreviousRecordingKey(self, prog):
        """Return the key to be used for a given prog in the
        previouslyRecordedShows hashtable."""
        logger.log( 9, 'getPreviousRecordingKey(prog=%r)', prog)
        shrunkTitle = self.shrink(prog.title)
        shrunkSub   = self.shrink(prog.sub_title)
        shrunkDesc  = self.shrink(prog.desc);
        return ('%s-%s-%s' % (shrunkTitle, shrunkSub, shrunkDesc), \
                '%s-%s-'   % (shrunkTitle, shrunkSub),             \
                '%s--%s'   % (shrunkTitle, shrunkDesc))


    def getPreviousRecording(self, prog):
        """Get a previous recording, or None if none."""
        logger.log( 9, 'getPreviousRecording(prog=%r)', prog)
        try:
            return self.previouslyRecordedShows[self.getPreviousRecordingKey(prog)]
        except KeyError:
            return None


    def removeDuplicate(self, prog=None):
        """Remove a duplicate recording"""
        logger.log( 9, 'removeDuplicate(prog=%r)', prog)
        self.loadPreviouslyRecordedShows()
        previous = self.getPreviousRecording(prog)
        if previous:
            logger.info('Found duplicate, removing')
            del self.previouslyRecordedShows[self.getPreviousRecordingKey(previous)]
            self.savePreviouslyRecordedShows()


    def addDuplicate(self, prog=None):
        """Add program to duplicates hash"""
        logger.log( 9, 'addDuplicate(prog=%r)', prog)
        self.loadPreviouslyRecordedShows()
        self.previouslyRecordedShows[self.getPreviousRecordingKey(prog)] = prog
        for key in self.getPreviousRecordingKey(prog):
            self.previouslyRecordedShows[key] = prog.start
        self.savePreviouslyRecordedShows()


    def duplicate(self, prog=None):
        """Identify if the given programme is a duplicate. If not,
        record it as previously recorded."""
        logger.log( 9, 'duplicate(prog=%r)', prog)
        self.loadPreviouslyRecordedShows()
        previous = self.getPreviousRecording(prog)
        if previous:
            logger.log( 9, 'Found duplicate for "%s", "%s", "%s", not adding', prog.title, prog.sub_title, prog.desc)

            return True
        return False


    def addRecordingToSchedule(self, prog=None, inputSchedule=None):
        logger.log( 9, 'addRecordingToSchedule(%r, inputSchedule=%r)', prog, inputSchedule)
        if inputSchedule:
            schedule = inputSchedule
        else:
            schedule = self.getScheduledRecordings()
        schedule.addProgram(prog, tv_util.getKey(prog))
        if not inputSchedule:
            if config.TV_RECORD_DUPLICATE_DETECTION:
                self.addDuplicate(prog)
            schedule.unmarkFavoriteProgAsDeleted(prog, tv_util.getKey(prog))
            self.saveScheduledRecordings(schedule)


    def removeRecordingFromSchedule(self, prog=None, inputSchedule=None, mark_fav_deleted=True):
        logger.log( 9, 'removeRecordingFromSchedule(%r, inputSchedule=%r)', prog, inputSchedule)
        if inputSchedule:
            schedule = inputSchedule
        else:
            schedule = self.getScheduledRecordings()
        schedule.removeProgram(prog, tv_util.getKey(prog))
        if not inputSchedule:
            if config.TV_RECORD_DUPLICATE_DETECTION:
                self.removeDuplicate(prog)
            favs = self.getFavorites()
            is_fav, favorite = self.isProgAFavorite(prog, favs)
            if mark_fav_deleted and is_fav:
                schedule.markFavoriteProgAsDeleted(prog, tv_util.getKey(prog))
            self.saveScheduledRecordings(schedule)


    @kaa.rpc.expose('getConflicts')
    def getConflicts(self, prog):
        conflictRating, conflicts = self.checkForConflicts(prog)
        return (conflictRating, [conflicts])


    def checkForConflicts(self, prog):
        logger.log( 9, 'checkForConflicts(prog=%r)', prog)
        progs = self.getScheduledRecordings().getProgramList()
        proglist = list(progs)
        proglist.sort(self.progsTimeCompare)
        conflictRating = 0
        conflicts = []
        for i in range(0, len(proglist)):
            otherprog = progs[proglist[i]]
            if (prog.start >= otherprog.start) and (prog.start < otherprog.stop) or \
                (prog.stop > otherprog.start) and (prog.stop < otherprog.stop) or \
                (otherprog.start >= prog.start) and (otherprog.start < prog.stop) or \
                (otherprog.stop > prog.start) and (otherprog.stop < prog.stop):
                conflictRating += 1
                conflicts.append(otherprog)
        return (conflictRating, conflicts)


    def conflictResolution(self, prog):
        logger.log( 9, 'conflictResolution(prog=%r)', prog)
        def exactMatch(self, prog):
            logger.log( 9, 'exactMatch(prog=%r)', prog)
            if prog.desc:
                descResult = False
                descMatches = None
                (descResult, descMatches) = self.findMatches(prog.desc)
                if descResult:
                    logger.info('Exact Matches %s', len(descMatches))
                    return descMatches

            if prog.sub_title:
                sub_titleResult = False
                sub_titleMatches = None
                (sub_titleResult, sub_titleMatches) = self.findMatches(prog.sub_title)
                if sub_titleResult:
                    logger.info('Exact Matches %s', len(sub_titleMatches))
                    return sub_titleMatches
            return None


        def getConflicts(self, prog, myScheduledRecordings):
            logger.log( 9, 'getConflicts(prog=%r, myScheduledRecordings=%r)', prog, myScheduledRecordings)
            self.addRecordingToSchedule(prog, myScheduledRecordings)
            progs = myScheduledRecordings.getProgramList()
            proglist = list(progs)
            proglist.sort(self.progsTimeCompare)
            conflictRating = 0
            conflicts = []
            for i in range(0, len(proglist)-1):
                thisprog = progs[proglist[i]]
                nextprog = progs[proglist[i+1]]
                if thisprog.stop > nextprog.start:
                    if thisprog == prog:
                        conflictRating += 1
                        conflicts.append(nextprog)
                    elif nextprog == prog:
                        conflictRating += 1
                        conflicts.append(thisprog)
            self.removeRecordingFromSchedule(prog, myScheduledRecordings)
            return (conflictRating, conflicts)


        def getRatedConflicts(self, prog, myScheduledRecordings):
            logger.log( 9, 'getRatedConflicts(prog=%r, myScheduledRecordings=%r)', prog, myScheduledRecordings)
            ratedConflicts = []
            occurrences = exactMatch(self, prog)
            if not occurrences:
                #program no longer exists
                return (True, None, [])
            #Search through all occurrences of looking for a non-conflicted occurrence
            for oneOccurrence in occurrences:
                (rating, conflictedProgs) = getConflicts(self, oneOccurrence, myScheduledRecordings)
                if rating == 0:
                    logger.info('No Conflict')
                    programsToChange = []
                    programsToChange.append(('add', oneOccurrence))
                    return(True, ratedConflicts, programsToChange)
                logger.info('Conflict Found')
                ratedConflicts.append((rating, conflictedProgs, oneOccurrence))
            return (False, ratedConflicts, [])

        if config.TV_RECORD_CONFLICT_RESOLUTION:
            ratedConflicts = []
            myScheduledRecordings = copy.deepcopy(self.getScheduledRecordings())

            #Try to record it at its listed time
            (rating, conflictedProg) = getConflicts(self, prog, myScheduledRecordings)
            if rating == 0:
                #No need to do anything fancy; this will work at its default time
                progsToChange = []
                progsToChange.append(('add', prog))
                return (True, 'No conflicts, using default time', progsToChange)

            #Default time didn't work, let's try all times known
            (result, ratedConflicts, progsToChange) = getRatedConflicts(self, prog, myScheduledRecordings)
            if result:
                #No conflicts
                return (True, 'No conflicts if new program is added', progsToChange)
            if not ratedConflicts:
                #Program no longer exists, should never hit this unless schedule changes
                return (False, 'Cannot schedule, new prog no longer exists', None)

            logger.info('Going into conflict resolution via scheduled program re-scheduling')
            # No viable time to schedule the program without a conflict
            # Try and reschedule the already scheduled program
            atleastOneSingleConflict = False
            for (scheduledConflictRating, scheduledConflictPrograms, conflictProgram) in ratedConflicts:
                #Only handle one conflict at the moment
                if scheduledConflictRating == 1:
                    atleastOneSingleConflict = True
                    scheduledConflictProgram = scheduledConflictPrograms[0]
                    #remove already scheduled program and try to reschedule it with the new program
                    self.removeRecordingFromSchedule(scheduledConflictProgram, myScheduledRecordings)
                    self.addRecordingToSchedule(conflictProgram, myScheduledRecordings)
                    (result, ratedConflicts, progsToChange) = getRatedConflicts(self, \
                        scheduledConflictProgram, myScheduledRecordings)
                    if result:
                        #No conflicts
                        progsToChange.append(('del', scheduledConflictProgram))
                        progsToChange.append(('add', conflictProgram))
                        return (True, 'No conflicts if scheduled program is rescheduled', progsToChange)
                    if not ratedConflicts:
                        #Program no longer exists, should never hit this unless schedule changes
                        progsToChange.append(('del', scheduledConflictProgram))
                        progsToChange.append(('add', conflictProgram))
                        return (True, 'Cannot find conflicted program, adding new', progsToChange)
                    #Return this to original state
                    self.addRecordingToSchedule(scheduledConflictProgram, myScheduledRecordings)
                    self.removeRecordingFromSchedule(conflictProgram, myScheduledRecordings)
            if not atleastOneSingleConflict:
                #Dirty way to (not) handle multiple conflicts
                return (False, 'Cannot handle multiple conflicts: %s not scheduled' % (prog.title), None)

            logger.info('Going into conflict resolution via priority')
            # No viable option to reschedule the original program
            # Time to resolve the conflict via priority
            tempRating = 1000
            tempConflicted = None
            tempProg = None
            #Find least conflicted
            for (conflictedRating, conflictedPrograms, tempProgram) in ratedConflicts:
                #Cannot handle multiple conflicts
                if conflictedPrograms:
                    conflictedProgram = conflictedPrograms[0]
                    if conflictedRating < tempRating:
                        tempRating = conflictedRating
                        tempConflicted = conflictedProgram
                        tempProg = tempProgram
            conflictedProgram = tempConflicted
            prog = tempProgram

            #Here is where it gets ugly
            (isProgFav, progFav) = self.getFavoriteObject(prog)
            (isConfFav, confFav) = self.getFavoriteObject(conflictedProgram)
            if not isProgFav and isConfFav:
                #Regular recording has higher priority then favorite
                progsToChange = []
                progsToChange.append(('del', conflictedProgram))
                progsToChange.append(('add', prog))
                reason = 'New program is a regular recording(added), scheduled is a Favorite(removed)'
                return (True, reason, progsToChange)
            elif isProgFav and not isConfFav:
                #Regular recording has higher priority then favorite
                progsToChange = []
                progsToChange.append(('del', prog))
                progsToChange.append(('add', conflictedProgram))
                reason = 'Scheduled program is a regular recording(added), new is a Favorite(removed)'
                return (True, reason, progsToChange)
            elif not isProgFav and not isConfFav:
                return (False, 'Both are regular programs, not adding new recording', None)
            elif isProgFav and isConfFav:
                #Both are favorites, go by priority (lower is better)
                if progFav.priority < confFav.priority:
                    progsToChange = []
                    progsToChange.append(('del', conflictedProgram))
                    progsToChange.append(('add', prog))
                    reason = 'New program is higher rated(added), Scheduled is lower(removed)'
                    return (True, reason, progsToChange)
                elif confFav.priority < progFav.priority:
                    progsToChange = []
                    progsToChange.append(('del', prog))
                    progsToChange.append(('add', conflictedProgram))
                    reason = 'Scheduled program is higher rated(added), New is lower(removed)'
                    return (True, reason, progsToChange)
                else:
                    #Equal priority, not adding new program
                    return (False, 'Both are regular programs, not adding new recording', None)
            else:
                return (False, 'No viable way to schedule', None)
        else:
            progsToChange = []
            progsToChange.append(('add', prog))
            return (True, 'Conflict resolution disabled', progsToChange)


    def checkOnlyNewDetection(self, prog=None):
        logger.log( 9, 'checkOnlyNewDetection(prog=%r)', prog)
        if config.TV_RECORD_ONLY_NEW_DETECTION:
            if not self.doesFavoriteRecordOnlyNewEpisodes(prog):
                return (True, 'Favorite records all episodes, record')
            if self.newEpisode(prog):
                return (True, 'New episode, record')
            else:
                return (False, 'Old episode, do not record')
        else:
            return (True, 'Only new episode detection disabled, record')


    def checkDuplicateDetection(self, prog=None):
        logger.log( 9, 'checkDuplicateDetection(prog=%r)', prog)
        if config.TV_RECORD_DUPLICATE_DETECTION:
            if self.doesFavoriteAllowDuplicates(prog):
                return (True, 'Favorite allows duplicates, record')
            if not self.duplicate(prog):
                return (True, 'Not a duplicate, record')
            else:
                return (False, 'Duplicate recording, do not record')
        else:
            return (True, 'Duplicate detection is disabled, record')


    def setTunerid(self, prog):
        logger.log( 9, 'setTunerid(prog=%r)', prog)
        for chan in tv.epg.channels:
            if prog.channel_id == chan.id:
                prog.tunerid = chan.tunerid
                logger.log( 9, '%s tuner: %s', prog, prog.tunerid)
        return prog


    @kaa.rpc.expose('scheduleRecording')
    def scheduleRecording(self, prog=None):
        """
        """
        logger.log( 9, 'scheduleRecording(%r)', prog)

        if prog is None:
            return ('error', _('program is not set'))

        now = self.timenow()
        if now > prog.stop:
            return ('error', _('program cannot record as it is over'))

        (isFav, favorite) = self.isProgAFavorite(prog)
        if isFav:
            (onlyNewBool, onlyNewReason) = self.checkOnlyNewDetection(prog)
            logger.log( 9, 'Only new episode detection: %s reason %s', onlyNewBool, onlyNewReason)
            if not onlyNewBool:
                #failed only new episode check (old episode, etc)
                return ('error', onlyNewReason)

            (duplicateBool, duplicateReason) = self.checkDuplicateDetection(prog)
            logger.log( 9, 'Duplicate detection: %s reason %s', duplicateBool, duplicateReason)
            if not duplicateBool:
                #failed duplicate check (duplicate, etc)
                return ('error', duplicateReason)
            schedule = self.getScheduledRecordings()
            if schedule.isFavoriteProgDeleted(prog, tv_util.getKey(prog)):
                schedule.unmarkFavoriteProgAsDeleted(prog, tv_util.getKey(prog))

        if config.TV_RECORD_CONFLICT_RESOLUTION:
            (ableToResolveBool, resolutionReason, progsToChange) = self.conflictResolution(prog)
            logger.log( 9, 'Conflict resolution: %s reason %s', ableToResolveBool, resolutionReason)
            if not ableToResolveBool:
                #No viable solution was found
                return ('error', resolutionReason)
            
            if progsToChange:
                for (cmd, prog) in progsToChange:
                    prog = self.setTunerid(prog)
                    if cmd == 'add':
                        logger.log( 9, 'adding %s to schedule', prog.title)
                        self.addRecordingToSchedule(prog)
                    elif cmd == 'del':
                        logger.log( 9, 'removed %s from schedule', prog.title)
                        self.removeRecordingFromSchedule(prog)
            else:
                prog = self.setTunerid(prog)
                logger.info('added %s to schedule', prog.title)
                self.addRecordingToSchedule(prog)
        else:
            conflicts,conflictingProgs = self.checkForConflicts(prog)
            if conflicts:
                return ('conflict', [conflictingProgs])
            prog = self.setTunerid(prog)
            logger.info('added %s to schedule', prog.title)
            self.addRecordingToSchedule(prog)

        # check, maybe we need to start right now
        self.check_to_record()

        return ('ok', _('program scheduled to record'))


    @kaa.rpc.expose('removeScheduledRecording')
    def removeScheduledRecording(self, prog=None, mark_fav_deleted=True):
        logger.log( 9, 'removeScheduledRecording(prog=%r)', prog)
        if prog is None:
            return (False, _('program is not set'))

        schedule = self.getScheduledRecordings()
        progs = schedule.getProgramList()

        for saved_prog in progs.values():
            if String(saved_prog) == String(prog):
                prog = saved_prog
                break

        recording = hasattr(prog, 'isRecording') and prog.isRecording

        self.removeRecordingFromSchedule(prog, mark_fav_deleted=mark_fav_deleted)

        now = self.timenow()

        # if now >= prog.start and now <= prog.stop and recording:
        if recording:
            logger.info('stopping current recording %s', prog)
            rec_plugin = plugin.getbyname('RECORD')
            if rec_plugin:
                rec_plugin.Stop()

        return (True, _('program removed from record schedule'))


    @kaa.rpc.expose('isProgScheduled')
    def isProgScheduled(self, prog, schedule=None):
        logger.log( 9, 'isProgScheduled(prog=%r, schedule=%r)', prog, schedule)

        if schedule is None:
            schedule = self.getScheduledRecordings()
            if schedule is None:
                return (False, _('scheduled programs is empty'))

        if schedule.getProgramList() == {}:
            return (False, _('program list is empty'))

        for me in schedule.getProgramList().values():
            if me.start == prog.start and me.channel_id == prog.channel_id:
                return (True, _('program is scheduled'))
        return (False, _('program is not scheduled'))


    @kaa.rpc.expose('findProg')
    def findProg(self, chan=None, start=None):
        logger.log( 9, 'findProg(chan=%r, start=%r', chan, start)

        if chan is None or start is None:
            return (False, None)

        progs = tv.epg.search(channel_id=chan.id, time=start)
        if progs:
            return (True, progs[0].utf2str())

        return (False, None)


    @kaa.rpc.expose('findMatches')
    def findMatches(self, find=None, movies_only=False):
        logger.log( 9, 'findMatches(find=%r, movies_only=%r)', find, movies_only)

        matches = tv.epg.search(keyword=find)
        logger.info('Found %d matches.', len(matches))

        if len(matches) == 0:
            return (False, _('no programs match'))
        return (True, matches)


    def timenow(self):
        """
        Round up the timer to the nearest minute; the loop runs once a minute.
        The RECORDSERVER_ATTIMER is a value to allow the recording to start at
        the number of seconds of the minute. The AtTimer is not 100% accurate
        need to allow a few seconds for it.

        @returns: the time in seconds
        """
        now = list(time.localtime(time.time() + 60 - 3))
        # round down to the nearest minute
        now[5] = 0
        return time.mktime(now)


    def check_to_record(self):
        """
        This is the real main loop of the record server
        """
        now = self.timenow()
        logger.log( 9, 'check_to_record %s', time.strftime('%H:%M:%S'))
        rec_cmd = None
        rec_prog = None
        cleaned = None

        schedule = self.getScheduledRecordings()
        if schedule is None:
            logger.debug('no scheduled recordings')
            return

        progs = schedule.getProgramList()

        currently_recording = None
        for prog in progs.values():
            recording = hasattr(prog, 'isRecording') and prog.isRecording
            if recording:
                currently_recording = prog

        if currently_recording is not None:
            logger.info('currently_recording=%s', currently_recording)
        if self.delayed_recording is not None:
            logger.info('delayed_recording=%s', self.delayed_recording)

        for prog in progs.values():
            recording = hasattr(prog, 'isRecording') and prog.isRecording

            logger.log( 9, 'prog=%s recording=%s', prog, recording)

            if not recording and \
                now >= (prog.start - config.TV_RECORD_PADDING_PRE) and \
                now < (prog.stop + config.TV_RECORD_PADDING_POST):
                # just add to the 'we want to record this' list then end the
                # loop, and figure out which has priority, remember to take
                # into account the full length of the shows and how much they
                # overlap, or chop one short
                duration = int(prog.stop) - int(now)
                if duration < 10:
                    logger.info('duration %s too small', duration)
                    return

                if currently_recording:
                    # Hey, something is already recording!
                    overlap_duration = currently_recording.stop - prog.start
                    logger.debug('overlap_duration=%r', overlap_duration)
                    if prog.start - 10 <= now:
                        # our new recording should start no later than now!
                        # check if the new prog is a favorite and the current
                        # running is not. If so, the user manually added
                        # something, we guess it has a higher priority.
                        if self.isProgAFavorite(prog)[0] and \
                            not self.isProgAFavorite(currently_recording)[0] and \
                            now < (prog.stop + config.TV_RECORD_PADDING_POST):
                            logger.info('Ignoring %s', prog)
                            continue
                        schedule.removeProgram(currently_recording, tv_util.getKey(currently_recording))
                        plugin.getbyname('RECORD').Stop()
                        logger.info('CALLED RECORD STOP 1: %s', currently_recording)
                    else:
                        # at this moment we must be in the pre-record padding
                        if currently_recording.stop - 10 <= now:
                            # The only reason we are still recording is because
                            # of the post-record padding.  Therefore we have
                            # overlapping paddings but not real stop / start
                            # times.
                            overlap = (currently_recording.stop + config.TV_RECORD_PADDING_POST) - \
                                      (prog.start - config.TV_RECORD_PADDING_PRE)
                            if overlap <= ((config.TV_RECORD_PADDING_PRE + config.TV_RECORD_PADDING_POST) / 4):
                                schedule.removeProgram(currently_recording,
                                    tv_util.getKey(currently_recording))
                                plugin.getbyname('RECORD').Stop()
                                logger.info('CALLED RECORD STOP 2: %s', currently_recording)
                    self.delayed_recording = prog
                else:
                    self.delayed_recording = None

                if self.delayed_recording:
                    logger.info('delaying: %s', prog)
                else:
                    logger.debug('going to record: %s', prog)
                    prog.isRecording = True
                    prog.rec_duration = duration + config.TV_RECORD_PADDING_POST
                    prog.filename = tv_util.getProgFilename(prog)
                    rec_prog = prog

        for prog in progs.values():
            # If the program is over remove the entry.
            if now > (prog.stop + config.TV_RECORD_PADDING_POST):
                logger.info('found a program to clean: %s', prog)
                cleaned = True
                del progs[tv_util.getKey(prog)]

        if rec_prog or cleaned:
            schedule.setProgramList(progs)
            self.saveScheduledRecordings(schedule)

        if rec_prog:
            logger.debug('start recording: %s', rec_prog)
            self.record_app = plugin.getbyname('RECORD')

            if not self.record_app:
                print_plugin_warning()
                logger.error('Recording %s failed.', rec_prog.title)
                self.removeScheduledRecording(rec_prog)
                return

            self.vg = self.fc.getVideoGroup(rec_prog.channel_id, False, CHANNEL_ID)
            suffix = self.vg.vdev.split('/')[-1]
            self.tv_lockfile = os.path.join(config.FREEVO_CACHEDIR, 'record.'+suffix)
            self.record_app.Record(rec_prog)

            # Cleanup old recordings (if enabled)
            if config.RECORDSERVER_CLEANUP_THRESHOLD > 0:
                space_threshold = config.RECORDSERVER_CLEANUP_THRESHOLD * 1024 * 1024 * 1024
                path = config.TV_RECORD_DIR
                freespace = util.freespace(path)
                if freespace < space_threshold:
                    files = os.listdir(path)
                    files = util.find_matches(files, config.VIDEO_SUFFIX)
                    files = [(f, os.stat(os.path.join(path, f)).st_mtime) for f in files]
                    files.sort(lambda x, y: cmp(x[1], y[1]))
                    i = 0
                    while freespace < space_threshold and i < len(files):
                        oldestrec = files[i][0]
                        oldestfxd = oldestrec[:oldestrec.rfind('.')] + '.fxd'
                        logger.info('Low on disk space - delete oldest recording: %s', oldestrec)
                        os.remove(os.path.join(path, oldestrec))
                        os.remove(os.path.join(path, oldestfxd))
                        freespace = util.freespace(path)
                        i = i + 1


    def handleEvents(self, event):
        if event:
            if event == RECORD_START:
                prog = event.arg
                logger.info('RECORD_START %s', prog)
                open(self.tv_lockfile, 'w').close()
                self.create_fxd(prog)
                if config.VCR_PRE_REC:
                    util.popen3.Popen3(config.VCR_PRE_REC)

            elif event == RECORD_STOP:
                prog = event.arg
                logger.info('RECORD_STOP %s', prog)
                prog.isRecording = False

                # Create and run the post processing thread
                postprocess = RecordPostProcess(prog)
                postprocess.setDaemon(0) # wait for the thread to end
                postprocess.start()

                # This is a really nasty hack but if it fixes the problem then great
                if self.delayed_recording:
                    self.delayed_recording = None
                    self.check_to_record()
                else:
                    os.remove(self.tv_lockfile)

            elif event == OS_EVENT_POPEN2:
                pid = event.arg[1]
                logger.info('OS_EVENT_POPEN2 pid: %s', pid)
                event.arg[0].child = util.popen3.Popen3(event.arg[1])

            elif event == OS_EVENT_WAITPID:
                pid = event.arg[0]
                logger.info('waiting for pid %s', pid)

                for i in range(20):
                    try:
                        wpid = os.waitpid(pid, os.WNOHANG)[0]
                    except OSError:
                        # forget it
                        continue
                    if wpid == pid:
                        logger.info('pid %s terminated', pid)
                        break
                    time.sleep(0.1)
                else:
                    logger.info('pid %s still running', pid)

            elif event == OS_EVENT_KILL:
                pid = event.arg[0]
                sig = event.arg[1]

                logger.info('killing pid %s with signal %s', pid, sig)
                try:
                    os.kill(pid, sig)
                except OSError:
                    pass

                for i in range(20):
                    try:
                        wpid = os.waitpid(pid, os.WNOHANG)[0]
                    except OSError:
                        # forget it
                        continue
                    if wpid == pid:
                        logger.info('killed pid %s with signal %s', pid, sig)
                        break
                    time.sleep(0.1)
                # We fall into this else from the for loop when break is not executed
                else:
                    logger.info('killing pid %s with signal 9', pid)
                    try:
                        os.kill(pid, 9)
                    except OSError:
                        pass
                    for i in range(20):
                        try:
                            wpid = os.waitpid(pid, os.WNOHANG)[0]
                        except OSError:
                            # forget it
                            continue
                        if wpid == pid:
                            logger.info('killed pid %s with signal 9', pid)
                            break
                        time.sleep(0.1)
                    else:
                        logger.info('failed to kill pid %s', pid)

            else:
                if hasattr(event, 'arg'):
                    logger.warning('event=%s arg=%r not handled', event, event.arg)
                else:
                    logger.warning('event=%s not handled', event)

        else:
            # Should never happen
            logger.error('event not defined')


    @kaa.rpc.expose('addFavorite')
    def addFavorite(self, name, prog, exactchan=False, exactdow=False, exacttod=False):
        logger.log( 9, 'addFavorite(name=%r, prog=%r, exactchan=%r, exactdow=%r, exacttod=%r)', name, prog, exactchan, exactdow, exacttod)

        if not name:
            return (False, _('no favorite name'))

        favs = self.getFavorites()
        priority = len(favs) + 1
        fav = tv.record_types.Favorite(name, prog, exactchan, exactdow, exacttod, priority, allowDuplicates, onlyNew)

        schedule = self.getScheduledRecordings()
        schedule.addFavorite(fav)
        self.saveScheduledRecordings(schedule)
        self.addFavoriteToSchedule(fav)

        return (True, _('favorite added'))


    @kaa.rpc.expose('addEditedFavorite')
    def addEditedFavorite(self, name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
        logger.log( 9, 'addEditedFavorite(name=%r, title=%r, chan=%r, dow=%r, mod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)', name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)
        fav = tv.record_types.Favorite()

        fav.name = name
        fav.title = title
        fav.channel = chan
        fav.dow = dow
        fav.mod = mod
        fav.priority = priority
        fav.allowDuplicates = allowDuplicates
        fav.onlyNew = onlyNew
        schedule = self.getScheduledRecordings()
        schedule.addFavorite(fav)
        self.saveScheduledRecordings(schedule)
        self.addFavoriteToSchedule(fav)

        return (True, _('favorite added'))


    @kaa.rpc.expose('removeFavorite')
    def removeFavorite(self, name=None):
        logger.log( 9, 'removeFavorite(name=%r)', name)
        if name is None:
            return (False, _('name is not set'))

        (status, fav) = self.getFavorite(name)
        self.removeFavoriteFromSchedule(fav)
        schedule = self.getScheduledRecordings()
        schedule.removeFavorite(name)
        self.saveScheduledRecordings(schedule)

        return (True, _('favorite removed'))


    @kaa.rpc.expose('clearFavorites')
    def clearFavorites(self):
        logger.log( 9, 'clearFavorites()')
        schedule = self.getScheduledRecordings()
        schedule.clearFavorites()
        self.saveScheduledRecordings(schedule)

        return (True, _('favorites cleared'))


    @kaa.rpc.expose('getFavorites')
    def getFavorites(self):
        logger.log( 9, 'getFavorites()')
        return self.getScheduledRecordings().getFavorites()


    @kaa.rpc.expose('getFavorite')
    def getFavorite(self, name):
        logger.log( 9, 'getFavorite(name=%r)', name)
        favs = self.getFavorites()

        if favs.has_key(name):
            fav = favs[name]
            return (True, fav)
        else:
            return (False, _('not a favorite'))


    @kaa.rpc.expose('adjustPriority')
    def adjustPriority(self, favname, mod=0):
        logger.log( 9, 'adjustPriority(favname=%r, mod=%r)', favname, mod)
        mod = int(mod)
        if mod == 0:
            return (False, _('nothing to do'))
            
        (status, me) = self.getFavorite(favname)
        if not status:
            return (status, me)
            
        logger.info('ap: mod=%s', mod)

        schedule = self.getScheduledRecordings()
        status = schedule.adjustFavoritePriority(me, mod)
        if status:
            self.saveScheduledRecordings(schedule)
            return (True, _('priority changed'))
        return (False, _('priority not changed'))
            


    @kaa.rpc.expose('getFavoriteObject')
    def getFavoriteObject(self, prog, favs=None):
        """ more liberal favorite check that returns an object """
        logger.log( 9, 'getFavoriteObject(prog=%r, favs=%r)', prog, favs)
        if not favs:
            favs = self.getFavorites()
        # first try the strict test
        name = tv_util.progname2favname(prog.title)
        if favs.has_key(name):
            fav = favs[name]
            return (True, fav)
        # try harder to find this favorite in a more liberal search
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                return (True, fav)
        # if we get this far prog is not a favorite
        return (False, _('not a favorite'))


    @kaa.rpc.expose('isProgAFavorite')
    def isProgAFavorite(self, prog, favs=None):
        #_debug_('isProgAFavorite(prog=%s, favs=%r)' % (prog, favs), 2)
        logger.log( 9, 'isProgAFavorite(%s)', prog)
        if not favs:
            favs = self.getFavorites()

        if favs is None:
            return (False, _('no favorites'))

        lt = time.localtime(prog.start)
        dow = '%s' % lt[6]
        mod = '%s' % ((lt[3]*60)+lt[4])

        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                if fav.channel == tv_util.get_chan_displayname(prog.channel_id) \
                or fav.channel == 'ANY':
                    if Unicode(fav.dow) == Unicode(dow) or Unicode(fav.dow) == u'ANY':
                        if Unicode(fav.mod) == u'ANY' \
                        or abs(int(fav.mod) - int(mod)) <= config.TV_RECORD_FAVORITE_MARGIN:
                            return (True, fav.name)

        # if we get this far prog is not a favorite
        return (False, _('not a favorite'))


    def doesFavoriteRecordOnlyNewEpisodes(self, prog, favs=None):
        logger.log( 9, 'doesFavoriteRecordOnlyNewEpisodes(prog=%r, favs=%r)', prog, favs)
        if not favs:
            favs = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                if not hasattr(fav, 'onlyNew'):
                    return True
                logger.info('NEW: %s', fav.onlyNew)
                if fav.onlyNew == '1':
                    return True


    def doesFavoriteAllowDuplicates(self, prog, favs=None):
        logger.log( 9, 'doesFavoriteAllowDuplicates(prog=%r, favs=%r)', prog, favs)
        if not favs:
            favs = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                if not hasattr(fav, 'allowDuplicates'):
                    return True
                logger.info('DUP: %s', fav.allowDuplicates)
                if fav.allowDuplicates == '1':
                    return True


    @kaa.rpc.expose('removeFavoriteFromSchedule')
    def removeFavoriteFromSchedule(self, fav):
        logger.log( 9, 'removeFavoriteFromSchedule(fav=%r)', fav)
        # TODO: make sure the program we remove is not
        #       covered by another favorite.

        tmp = {}
        tmp[fav.name] = fav

        schedule = self.getScheduledRecordings()
        schedule.lock()
        progs = schedule.getProgramList()
        for prog in progs.values():
            (isFav, favorite) = self.isProgAFavorite(prog, tmp)
            if isFav:
                self.removeScheduledRecording(prog)

        schedule.unlock()
        return (True, _('favorite removed from schedule'))


    def addFavoriteToSchedule(self, fav):
        logger.log( 9, 'addFavoriteToSchedule(fav=%r)', fav)
        favs = {}
        favs[fav.name] = fav
        kwargs = {'title' : fav.title}
        if fav.channel != u'ANY':
            kwargs['channel_id'] = tv.epg.channels_by_display_name[fav.channel].id
        progs = tv.epg.search(**kwargs)
        for prog in progs:
            (isFav, favorite) = self.isProgAFavorite(prog, favs)
            if isFav:
                prog.isFavorite = favorite
                self.scheduleRecording(prog)

        return (True, _('favorite added to schedule'))


    @kaa.rpc.expose('updateFavoritesSchedule')
    def updateFavoritesSchedule(self):
        #  TODO: do not re-add a prog to record if we have
        #        previously decided not to record it.
        logger.log( 9, 'updateFavoritesSchedule()')

        schedule = self.getScheduledRecordings()

        favs = self.getFavorites()
        if not len(favs):
            return False

        schedule.lock()

        # Then remove all scheduled favorites in that time-frame to
        # make up for schedule changes.
        progs = schedule.getProgramList()
        for prog in progs.values():
            # if prog.start <= last and favorite:
            (isFav, favorite) = self.isProgAFavorite(prog, favs)
            if isFav:
                # do not yet remove programs currently being recorded:
                isRec = hasattr(prog, 'isRecording') and prog.isRecording
                if not isRec:
                    self.removeScheduledRecording(prog, mark_fav_deleted=False)

        titles = []
        for fav in favs.values():
            if fav.title not in titles:
                titles.append(fav.title)
        for title in titles:

            programs = tv.epg.search(title=title)
            for prog in programs:
                (isFav, favorite) = self.isProgAFavorite(prog, favs)
                isDeleted = self.getScheduledRecordings().isFavoriteProgDeleted(prog, tv_util.getKey(prog))
                isRec = hasattr(prog, 'isRecording') and prog.isRecording
                if isFav and not isDeleted and not isRec:
                    prog.isFavorite = favorite
                    self.scheduleRecording(prog)

        schedule.unlock()
        return True


    @kaa.rpc.expose('getGrid')
    def getGrid(self, start, end, channels):
        import tv.epg
        schedule = self.getScheduledRecordings()
        progs = schedule.getProgramList()
        channels = tv.epg.get_programs(start, end, channels)
        for channel in channels:
            for prog in channel.programs:
                for scheduled_prog in progs.values():
                    if scheduled_prog.start == prog.start and scheduled_prog.channel_id == prog.channel_id:
                        prog.scheduled = True
                        prog.overlap = scheduled_prog.overlap
                        if hasattr(scheduled_prog, 'isFavorite') and scheduled_prog.isFavorite:
                            prog.favorite = True
        return channels


    def create_fxd(self, rec_prog):
        logger.log( 9, 'create_fxd(rec_prog=%r)', rec_prog)
        from util.fxdimdb import FxdImdb, makeVideo
        fxd = FxdImdb()

        (filebase, fileext) = os.path.splitext(rec_prog.filename)
        fxd.setFxdFile(filebase, overwrite=True)

        desc = rec_prog.desc.replace('\n\n','\n').replace('\n','&#10;')
        video = makeVideo('file', 'f1', os.path.basename(rec_prog.filename))
        fxd.setVideo(video)
        fxd.info['channel'] = fxd.str2XML(rec_prog.channel_id)
        fxd.info['tunerid'] = fxd.str2XML(rec_prog.tunerid)
        fxd.info['tagline'] = fxd.str2XML(rec_prog.sub_title)
        fxd.info['plot'] = fxd.str2XML(desc)
        fxd.info['runtime'] = None
        fxd.info['recording_timestamp'] = str(rec_prog.start)
        try:
            fxd.info['userdate'] = time.strftime(config.TV_RECORD_YEAR_FORMAT, time.localtime(rec_prog.start))
        except:
            fxd.info['userdate'] = time.strftime(config.TV_RECORD_YEAR_FORMAT)
        fxd.title = rec_prog.title
        if plugin.is_active('tv.recordings_manager'):
            fxd.info['watched'] = 'False'
            fxd.info['keep'] = 'False'
        fxd.writeFxd()


    def handleAtTimer(self):
        logger.log( 9, 'handleAtTimer()')
        self.check_to_record()



class RecordPostProcess(Thread):
    def __init__(self, prog):
        Thread.__init__(self)
        self.prog = prog
        self.es = EncodingClientActions()


    def run(self):
        logger.info('post-processing started for %s', self.prog)
        filebase = os.path.splitext(self.prog.filename)[0]
        try:
            ss_file = filebase + '.png'
            snapshot(self.prog.filename, ss_file)
        except:
            pass

        # Touch the fxd file after creating the thumbnail so that the recordings
        # manager picks it up.
        os.utime(filebase + '.fxd', None)

        if config.VCR_POST_REC:
            util.popen3.Popen3(config.VCR_POST_REC % self.prog.__dict__)

        if config.TV_RECORD_REMOVE_COMMERCIALS:
            (result, response) = commdetectConnectionTest('connection test')
            if result:
                (status, idnr) = initCommDetectJob(self.prog.filename)
                (status, output) = listCommdetectJobs()
                logger.info(output)
                (status, output) = queueCommdetectJob(idnr, True)
                logger.info(output)
            else:
                logger.info('commdetect server not running')

        if config.TV_REENCODE:
            result = self.es.ping()
            if result:
                source = self.prog.filename
                output = self.prog.filename
                multipass = config.REENCODE_NUMPASSES > 1

                (status, resp) = self.es.initEncodingJob(source, output, self.prog.title, None,
                    config.TV_REENCODE_REMOVE_SOURCE)
                logger.debug('initEncodingJob:status:%s resp:%s', status, resp)

                idnr = resp

                (status, resp) = self.es.setContainer(idnr, config.REENCODE_CONTAINER)
                logger.debug('setContainer:status:%s resp:%s', status, resp)

                (status, resp) = self.es.setVideoCodec(idnr, config.REENCODE_VIDEOCODEC, 0, multipass,
                    config.REENCODE_VIDEOBITRATE, config.REENCODE_ALTPROFILE)
                logger.debug('setVideoCodec:status:%s resp:%s', status, resp)

                (status, resp) = self.es.setAudioCodec(idnr, config.REENCODE_AUDIOCODEC,
                    config.REENCODE_AUDIOBITRATE)
                logger.debug('setAudioCodec:status:%s resp:%s', status, resp)

                (status, resp) = self.es.setNumThreads(idnr, config.REENCODE_NUMTHREADS)
                logger.debug('setNumThreads:status:%s resp:%s', status, resp)

                (status, resp) = self.es.setVideoRes(idnr, config.REENCODE_RESOLUTION)
                logger.debug('setVideoRes:status:%s resp:%s', status, resp)

                (status, resp) = self.es.listJobs()
                logger.debug('listJobs:status:%s resp:%s', status, resp)

                (status, resp) = self.es.queueIt(idnr, True)
                logger.debug('queueIt:status:%s resp:%s', status, resp)
            else:
                logger.info('encoding server not running')

        logger.info('post-processing finished for %s', self.prog)



def main():
    if config.TV_RECORD_CONFLICT_RESOLUTION:
        logger.info('Conflict resolution enabled')

    socket = ('', config.RECORDSERVER_PORT)
    secret = config.RECORDSERVER_SECRET
    logger.debug('socket=%r, secret=%r', socket, secret)

    recordserver = RecordServer()
    try:
        rpc = kaa.rpc.Server(socket, secret)
    except Exception:
        raise
    rpc.register(recordserver)

    eh = EventHandler(recordserver.handleEvents)
    eh.register()

    logger.debug('kaa.AtTimer starting')
    kaa.AtTimer(recordserver.handleAtTimer).start(sec=config.RECORDSERVER_ATTIMER)
    logger.debug('kaa.main starting')
    kaa.main.run()
    logger.debug('kaa.main finished')



if __name__ == '__main__':
    import socket
    import glob

    locks = glob.glob(os.path.join(config.FREEVO_CACHEDIR, 'record.*'))
    for f in locks:
        logger.info('removed old record lock %r', f)
        os.remove(f)

    try:
        logger.info('main() starting')
        main()
        logger.info('main() finished')
    except SystemExit:
        logger.info('main() stopped')
        pass
    except Exception:

        logger.warning('Caught exception from main()',exc_info=True)
        import traceback
        traceback.print_exc()
