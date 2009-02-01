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


import sys, string, random, time, os, re, pwd, stat, threading, hashlib, datetime, copy
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

appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
appconf = appname.upper()

# change uid
if __name__ == '__main__':
    config.DEBUG_STDOUT = 0
    uid = 'config.'+appconf+'_UID'
    gid = 'config.'+appconf+'_GID'
    try:
        if eval(uid) and os.getuid() == 0:
            os.setgid(eval(gid))
            os.setuid(eval(uid))
            os.environ['USER'] = pwd.getpwuid(os.getuid())[0]
            os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
    except Exception, why:
        print why
        sys.exit(1)

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
import tv.epg_xmltv
import util.tv_util as tv_util
import plugin
import util.popen3
from tv.channels import FreevoChannels, CHANNEL_ID
from util.videothumb import snapshot
from event import *


DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG
LOGGING = hasattr(config, 'LOGGING_'+appconf) and eval('config.LOGGING_'+appconf) or config.LOGGING

logfile = '%s/%s-%s.log' % (config.FREEVO_LOGDIR, appname, os.getuid())
sys.stdout = open(logfile, 'a')
sys.stderr = sys.stdout

logging.getLogger('').setLevel(LOGGING)
logging.basicConfig(level=LOGGING, \
    #datefmt='%a, %H:%M:%S', # datefmt does not support msecs :(
    format='%(asctime)s %(levelname)-8s %(message)s', \
    filename=logfile, filemode='a')

try:
    import freevo.version as version
    import freevo.revision as revision
except:
    import version
    import revision

_debug_('PLUGIN_RECORD: %s' % config.plugin_record, DINFO)

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
    _debug_(warning, DWARNING)


if not plugin.getbyname('RECORD'):
    print_plugin_warning()


class RecordServer:

    def __init__(self, debug=False):
        """ Initialise the Record Server class """
        _debug_('RecordServer.__init__(debug=%r)' % (debug), 2)
        self.debug = debug
        self.lock = threading.RLock()
        self.schedule_lock = threading.Lock()
        self.fc = FreevoChannels()
        # XXX: In the future we should have one lock per VideoGroup.
        self.tv_lockfile = None
        self.vg = None
        self.previouslyRecordedShows = None
        self.delay_recording = None
        self.schedule = ScheduledRecordings()
        self.updateFavoritesSchedule()
        self.es = EncodingClientActions()


    @kaa.rpc.expose('ping')
    def pingtest(self):
        _debug_('pingtest()', 2)
        return True


    @kaa.rpc.expose('isRecording')
    def isRecording(self):
        _debug_('isRecording()', 2)
        recording = glob.glob(config.FREEVO_CACHEDIR + '/record.*')
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
        _debug_('findOverlaps(schedule=%r)' % (schedule,), 2)
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
                _debug_('Overlap:\n%s\n%s' % (thisprog, nextprog), DINFO)


    @kaa.rpc.expose('findNextProgram')
    def findNextProgram(self, isrecording=False):
        _debug_('findNextProgram(isrecording=%r)' % (isrecording), 2)

        next_program = None
        progs = self.getScheduledRecordings().getProgramList()
        proglist = list(progs)
        proglist.sort(self.progsTimeCompare)
        now = time.time()
        timenow = time.localtime(now)
        for progitem in proglist:
            prog = progs[progitem]
            _debug_('%s' % (prog), 2)

            if now >= prog.start-config.TV_RECORD_PADDING_PRE and now < prog.stop+config.TV_RECORD_PADDING_POST:
                recording = True
                if isrecording:
                    _debug_('isrecording is %s' % (prog), 2)
                    return (True, prog)
            else:
                recording = False

            endtime = time.strftime(config.TV_TIME_FORMAT, time.localtime(prog.stop+config.TV_RECORD_PADDING_POST))
            _debug_('%s is recording %s stopping at %s' % (prog.title, recording and 'yes' or 'no', endtime), 2)

            if now > prog.stop + config.TV_RECORD_PADDING_POST:
                _debug_('%s: finished %s > %s' % (prog.title, time.strftime('%H:%M:%S', timenow), endtime), 2)
                continue

            if not recording:
                next_program = prog
                break

        if next_program is None:
            _debug_('No program scheduled to record', 2)
            return (False, next_program)

        _debug_('next is %s' % (next_program), 2)
        return (True, next_program)


    @kaa.rpc.expose('isPlayerRunning')
    def isPlayerRunning(self):
        """
        Test is the player is running

        TODO: real player running test, check /dev/videoX.  This could go into the upsoon client
        @returns: the state of a player, mplayer, xine, etc.
        """
        _debug_('isPlayerRunning()', 2)
        res = (os.path.exists(config.FREEVO_CACHEDIR + '/playing'))
        _debug_('isPlayerRunning=%r' % (res), 2)
        return res


    @kaa.rpc.expose('getScheduledRecordings')
    def getScheduledRecordings(self):
        _debug_('getScheduledRecordings()', 2)
        file_ver = None
        schedule = None

        if os.path.isfile(config.TV_RECORD_SCHEDULE):
            _debug_('reading cache (%r)' % config.TV_RECORD_SCHEDULE, 2)
            if hasattr(self, 'schedule_cache'):
                mod_time, schedule = self.schedule_cache
                try:
                    if os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME] == mod_time:
                        _debug_('using cached schedule', 2)
                        return schedule
                except OSError, why:
                    _debug_('Failed to stat %r: %s' % (config.TV_RECORD_SCHEDULE, why), DERROR)
                    pass

            schedule = self.schedule.loadRecordSchedule()

            try:
                file_ver = schedule.TYPES_VERSION
            except AttributeError:
                _debug_('The cache does not have a version and must be recreated', DINFO)

            if file_ver != TYPES_VERSION:
                _debug_(('ScheduledRecordings version number %s is stale (new is %s), must be reloaded') % \
                    (file_ver, TYPES_VERSION), DINFO)
                schedule = None
            else:
                _debug_('Got ScheduledRecordings (version %s).' % file_ver, DINFO)

        if not schedule:
            _debug_('Created a new ScheduledRecordings', DINFO)
            schedule = ScheduledRecordings()
            self.saveScheduledRecordings(schedule)

        _debug_('ScheduledRecordings has %s items.' % len(schedule.program_list))

        try:
            mod_time = os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME]
            self.schedule_cache = mod_time, schedule
        except OSError:
            pass
        return schedule


    #@kaa.rpc.expose('saveScheduledRecordings')
    def saveScheduledRecordings(self, schedule=None):
        """ Save the schedule to disk """
        _debug_('saveScheduledRecordings(schedule=%r)' % (schedule), 2)

        if not schedule:
            _debug_('making a new ScheduledRecordings', DINFO)
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
        _debug_('loadPreviouslyRecordedShows()', 2)
        if self.previouslyRecordedShows:
            return

        cacheFile = config.FREEVO_CACHEDIR + "/previouslyRecorded.pickle"
        try:
            self.previouslyRecordedShows = pickle.load(open(cacheFile, "r"))
        except IOError:
            self.previouslyRecordedShows = {}
            pass


    def savePreviouslyRecordedShows(self):
        """ Save the set of recorded shows """
        _debug_('savePreviouslyRecordedShows()', 2)
        if not self.previouslyRecordedShows:
            return

        cacheFile = config.FREEVO_CACHEDIR+"/previouslyRecorded.pickle"
        pickle.dump(self.previouslyRecordedShows, open(cacheFile, "w"))


    def newEpisode(self, prog=None):
        """ Return true if this is a new episode of 'prog' """
        _debug_('newEpisode(prog=%r)' % (prog,), 2)
        todayStr = datetime.date.today().strftime('%Y%m%d')
        progStr = str(prog.date)
        _debug_('Program Date: "%s"' % progStr, DINFO)
        _debug_('Todays Date : "%s"' % todayStr, DINFO)
        if (len(progStr) == 8):
            _debug_('Good date format', DINFO)
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
                _debug_('Same year', DINFO)
                #program in the same year
                if todaysMonth > progMonth:
                    #program in a previous month
                    return False
                elif progMonth > todaysMonth:
                    #program in the future
                    return True
                else:
                    _debug_('Same month', DINFO)
                    #program in the same month
                    if todaysDay > progDay:
                        #program was previous aired this month
                        return False
                    else:
                        _debug_('Same day or in the upcoming month', DINFO)
                        #program is today or in the upcoming days
                        return True
        else:
            _debug_('No good date format, assuming new Episode to be on the safe side', DINFO)
            return True


    def shrink(self, text):
        """ Shrink a string by removing all spaces and making it
        lower case and then returning the MD5 digest of it. """
        _debug_('shrink(text=%r)' % (text,), 2)
        if text:
            text = hashlib.md5(text.lower().replace(' ', '')).hexdigest()
        else:
            text = ''
        return text


    def getPreviousRecordingKey(self, prog):
        """Return the key to be used for a given prog in the
        previouslyRecordedShows hashtable."""
        _debug_('getPreviousRecordingKey(prog=%r)' % (prog,), 2)
        shrunkTitle = self.shrink(prog.title)
        shrunkSub   = self.shrink(prog.sub_title)
        shrunkDesc  = self.shrink(prog.desc);
        return ('%s-%s-%s' % (shrunkTitle, shrunkSub, shrunkDesc), \
                '%s-%s-'   % (shrunkTitle, shrunkSub),             \
                '%s--%s'   % (shrunkTitle, shrunkDesc))


    def getPreviousRecording(self, prog):
        """Get a previous recording, or None if none."""
        _debug_('getPreviousRecording(prog=%r)' % (prog,), 2)
        try:
            return self.previouslyRecordedShows[self.getPreviousRecordingKey(prog)]
        except KeyError:
            return None


    def removeDuplicate(self, prog=None):
        """Remove a duplicate recording"""
        _debug_('removeDuplicate(prog=%r)' % (prog,), 2)
        self.loadPreviouslyRecordedShows()
        previous = self.getPreviousRecording(prog)
        if previous:
            _debug_('Found duplicate, removing', DINFO)
            del self.previouslyRecordedShows[self.getPreviousRecordingKey(previous)]
            self.savePreviouslyRecordedShows()


    def addDuplicate(self, prog=None):
        """Add program to duplicates hash"""
        _debug_('addDuplicate(prog=%r)' % (prog,), 2)
        self.loadPreviouslyRecordedShows()
        self.previouslyRecordedShows[self.getPreviousRecordingKey(prog)] = prog
        for key in self.getPreviousRecordingKey(prog):
            self.previouslyRecordedShows[key] = prog.start
        self.savePreviouslyRecordedShows()


    def duplicate(self, prog=None):
        """Identify if the given programme is a duplicate. If not,
        record it as previously recorded."""
        _debug_('duplicate(prog=%r)' % (prog,), 2)
        self.loadPreviouslyRecordedShows()
        previous = self.getPreviousRecording(prog)
        if previous:
            _debug_('Found duplicate for "%s", "%s", "%s", not adding' % \
            (prog.title, prog.sub_title, prog.desc), 2)
            return True
        return False


    def addRecordingToSchedule(self, prog=None, inputSchedule=None):
        _debug_('addRecordingToSchedule(%r, inputSchedule=%r)' % (prog, inputSchedule), 2)
        if inputSchedule:
            schedule = inputSchedule
        else:
            schedule = self.getScheduledRecordings()
        schedule.addProgram(prog, tv_util.getKey(prog))
        if not inputSchedule:
            if config.TV_RECORD_DUPLICATE_DETECTION:
                self.addDuplicate(prog)
            self.saveScheduledRecordings(schedule)


    def removeRecordingFromSchedule(self, prog=None, inputSchedule=None):
        _debug_('removeRecordingFromSchedule(%r, inputSchedule=%r)' % (prog, inputSchedule), 2)
        if inputSchedule:
            schedule = inputSchedule
        else:
            schedule = self.getScheduledRecordings()
        schedule.removeProgram(prog, tv_util.getKey(prog))
        if not inputSchedule:
            if config.TV_RECORD_DUPLICATE_DETECTION:
                self.removeDuplicate(prog)
            self.saveScheduledRecordings(schedule)


    def conflictResolution(self, prog):
        _debug_('conflictResolution(prog=%r)' % (prog,), 2)
        def exactMatch(self, prog):
            _debug_('exactMatch(prog=%r)' % (prog,), 2)
            if prog.desc:
                descResult = False
                descMatches = None
                (descResult, descMatches) = self.findMatches(prog.desc)
                if descResult:
                    _debug_('Exact Matches %s' % (len(descMatches)), DINFO)
                    return descMatches

            if prog.sub_title:
                sub_titleResult = False
                sub_titleMatches = None
                (sub_titleResult, sub_titleMatches) = self.findMatches(prog.sub_title)
                if sub_titleResult:
                    _debug_('Exact Matches %s' % (len(sub_titleMatches)), DINFO)
                    return sub_titleMatches
            return None


        def getConflicts(self, prog, myScheduledRecordings):
            _debug_('getConflicts(prog=%r, myScheduledRecordings=%r)' % (prog, myScheduledRecordings), 2)
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
                    conflictRating = conflictRating+1
                    if thisprog == prog:
                        conflicts.append(nextprog)
                    elif nextprog == prog:
                        conflicts.append(thisprog)
            self.removeRecordingFromSchedule(prog, myScheduledRecordings)
            return (conflictRating, conflicts)


        def getRatedConflicts(self, prog, myScheduledRecordings):
            _debug_('getRatedConflicts(prog=%r, myScheduledRecordings=%r)' % (prog, myScheduledRecordings), 2)
            ratedConflicts = []
            occurances = exactMatch(self, prog)
            if not occurances:
                #program no longer exists
                return (False, None, None)
            #Search through all occurances of looking for a non-conflicted occurance
            for oneOccurance in occurances:
                (rating, conflictedProgs) = getConflicts(self, oneOccurance, myScheduledRecordings)
                if rating == 0:
                    _debug_('No Conflict', DINFO)
                    programsToChange = []
                    programsToChange.append(('add', oneOccurance))
                    return(True, ratedConflicts, programsToChange)
                _debug_('Conflict Found', DINFO)
                ratedConflicts.append((rating, conflictedProgs, oneOccurance))
            return (False, ratedConflicts, None)

        if config.TV_RECORD_CONFLICT_RESOLUTION:
            _debug_('Conflict resolution enabled', DINFO)
            ratedConflicts = []
            myScheduledRecordings = copy.deepcopy(self.getScheduledRecordings())

            #Try to record it at its listed time
            (rating, conflictedProg) = getConflicts(self, prog, myScheduledRecordings)
            if rating == 0:
                #No need to do anything fancy; this will work at its defaul time
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

            _debug_('Going into conflict resolution via scheduled program re-scheduling', DINFO)
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

            _debug_('Going into conflict resolution via priority', DINFO)
            # No viable option to reschedule the original program
            # Time to resolve the conflict via priority
            tempRating = 1000
            tempConflicted = None
            tempProg = None
            #Find least conflicted
            for (conflictedRating, conflictedPrograms, tempProgram) in ratedConflicts:
                #Cannot handle multiple conflicts
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
        _debug_('checkOnlyNewDetection(prog=%r)' % (prog,), 2)
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
        _debug_('checkDuplicateDetection(prog=%r)' % (prog,), 2)
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
        _debug_('setTunerid(prog=%r)' % (prog,), 2)
        for chan in guide.chan_list:
            if prog.channel_id == chan.id:
                prog.tunerid = chan.tunerid
                _debug_('%s tuner: %s' % (prog, prog.tunerid), 2)
        return prog


    @kaa.rpc.expose('scheduleRecording')
    def scheduleRecording(self, prog=None):
        _debug_('scheduleRecording(%r)' % (prog,), 2)
        global guide

        if prog is None:
            return (False, _('program is not set'))

        now = time.time()
        if now > prog.stop:
            return (False, _('program cannot record as it is over'))

        self.updateGuide()

        (isFav, favorite) = self.isProgAFavorite(prog)
        if isFav:
            (onlyNewBool, onlyNewReason) = self.checkOnlyNewDetection(prog)
            _debug_('Only new episode detection: %s reason %s' % (onlyNewBool, onlyNewReason), 2)
            if not onlyNewBool:
                #failed only new episode check (old episode, etc)
                return (False, onlyNewReason)

            (duplicateBool, duplicateReason) = self.checkDuplicateDetection(prog)
            _debug_('Duplicate detection: %s reason %s' % (duplicateBool, duplicateReason), 2)
            if not duplicateBool:
                #failed duplicate check (duplicate, etc)
                return (False, duplicateReason)

        (ableToResolveBool, resolutionReason, progsToChange) = self.conflictResolution(prog)
        _debug_('Conflict resolution: %s reason %s' % (ableToResolveBool, resolutionReason), 2)
        if not ableToResolveBool:
            #No viable solution was found
            return (False, resolutionReason)

        if progsToChange:
            for (cmd, prog) in progsToChange:
                prog = self.setTunerid(prog)
                if cmd == 'add':
                    _debug_('adding %s to schedule' % (prog.title), 2)
                    self.addRecordingToSchedule(prog)
                elif cmd == 'del':
                    _debug_('removed %s from schedule' % (prog.title), 2)
                    self.removeRecordingFromSchedule(prog)
        else:
            prog = self.setTunerid(prog)
            _debug_('added %s to schedule' % (prog.title), DINFO)
            self.addRecordingToSchedule(prog)

        # check, maybe we need to start right now
        self.checkToRecord()

        return (True, _('program scheduled to record'))


    @kaa.rpc.expose('removeScheduledRecording')
    def removeScheduledRecording(self, prog=None):
        _debug_('removeScheduledRecording(prog=%r)' % (prog,), 2)
        if prog is None:
            return (False, _('program is not set'))

        schedule = self.getScheduledRecordings()
        progs = schedule.getProgramList()

        for saved_prog in progs.values():
            if String(saved_prog) == String(prog):
                prog = saved_prog
                break

        try:
            recording = prog.isRecording
        except Exception, e:
            recording = False

        self.removeRecordingFromSchedule(prog)

        now = time.time()

        # if now >= prog.start and now <= prog.stop and recording:
        if recording:
            _debug_('stopping current recording %s' % (prog), DINFO)
            rec_plugin = plugin.getbyname('RECORD')
            if rec_plugin:
                rec_plugin.Stop()

        return (True, _('program removed from record schedule'))


    @kaa.rpc.expose('isProgScheduled')
    def isProgScheduled(self, prog, schedule=None):
        _debug_('isProgScheduled(prog=%r, schedule=%r)' % (prog, schedule), 2)

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
        _debug_('findProg(chan=%r, start=%r' % (chan, start), 2)
        global guide

        if chan is None or start is None:
            return (False, None)

        self.updateGuide()

        for ch in guide.chan_list:
            if chan == ch.id:
                _debug_('CHANNEL MATCH: %s' % ch.id, DINFO)
                for prog in ch.programs:
                    if start == '%s' % prog.start:
                        _debug_('PROGRAM MATCH 1: %s' % prog, DINFO)
                        return (True, prog.utf2str())

        return (False, None)


    @kaa.rpc.expose('findMatches')
    def findMatches(self, find=None, movies_only=False):
        _debug_('findMatches(find=%r, movies_only=%r)' % (find, movies_only), 2)
        global guide

        matches = []
        max_results = 500

        if find:
            find = Unicode(find).replace('(','\(').replace(')','\)').replace('.','\.')
        elif not movies_only:
            _debug_('nothing to find', DINFO)
            return (False, _('nothing to find'))

        self.updateGuide()

        pattern = '.*' + find + '\ *'
        regex = re.compile(pattern, re.IGNORECASE)
        now = time.time()

        for ch in guide.chan_list:
            for prog in ch.programs:
                if now >= prog.stop:
                    continue
                if not find or regex.match(prog.title) or regex.match(prog.desc) or regex.match(prog.sub_title):
                    if movies_only:
                        # We can do better here than just look for the MPAA rating.
                        # Suggestions are welcome.
                        if 'MPAA' in prog.utf2str().getattr('ratings').keys():
                            matches.append(prog.utf2str())
                            _debug_('PROGRAM MATCH 2: %s' % prog, DINFO)
                    else:
                        matches.append(prog.utf2str())
                        _debug_('PROGRAM MATCH 3: %s' % prog, DINFO)
                if len(matches) >= max_results:
                    break

        _debug_('Found %d matches.' % len(matches), DINFO)

        if len(matches) == 0:
            return (False, _('no programs match'))
        return (True, matches)


    def updateGuide(self):
        _debug_('updateGuide()', 2)
        global guide
        guide = tv.epg_xmltv.get_guide()


    def addFavoritesToSchedule(self):
        _debug_('addFavoritesToSchedule()', 2)
        pass


    def checkToRecord(self):
        _debug_('checkToRecord %s' % (time.strftime('%H:%M:%S', time.localtime(time.time()))), 2)
        rec_cmd = None
        rec_prog = None
        cleaned = None

        schedule = self.getScheduledRecordings()
        if schedule is None:
            _debug_('no scheduled recordings')
            return

        progs = schedule.getProgramList()

        currently_recording = None
        for prog in progs.values():
            try:
                recording = prog.isRecording
            except:
                recording = False

            if recording:
                currently_recording = prog

        now = time.time()
        for prog in progs.values():
            _debug_('progloop=%s' % prog, 2)

            try:
                recording = prog.isRecording
            except:
                recording = False

            if not recording \
                and now >= (prog.start - config.TV_RECORD_PADDING_PRE) \
                and now < (prog.stop + config.TV_RECORD_PADDING_POST):
                # just add to the 'we want to record this' list
                # then end the loop, and figure out which has priority,
                # remember to take into account the full length of the shows
                # and how much they overlap, or chop one short
                duration = int(prog.stop) - int(now)
                if duration < 10:
                    _debug_('duration %s too small' % duration, DINFO)
                    return

                if currently_recording:
                    # Hey, something is already recording!
                    overlap_duration = currently_recording.stop - prog.start
                    _debug_('overlap_duration=%r' % overlap_duration, DINFO)
                    if prog.start - 10 <= now:
                        # our new recording should start no later than now!
                        # check if the new prog is a favorite and the current running is
                        # not. If so, the user manually added something, we guess it
                        # has a higher priority.
                        if self.isProgAFavorite(prog)[0] \
                            and not self.isProgAFavorite(currently_recording)[0] \
                            and now < (prog.stop + config.TV_RECORD_PADDING_POST):
                            _debug_('Ignoring %s' % prog, DINFO)
                            continue
                        schedule.removeProgram(currently_recording,
                                         tv_util.getKey(currently_recording))
                        plugin.getbyname('RECORD').Stop()
                        _debug_('CALLED RECORD STOP 1: %s' % currently_recording, DINFO)
                    else:
                        # at this moment we must be in the pre-record padding
                        if currently_recording.stop - 10 <= now:
                            # The only reason we are still recording is because of the post-record padding.
                            # Therefore we have overlapping paddings but not real stop / start times.
                            overlap = (currently_recording.stop + config.TV_RECORD_PADDING_POST) - \
                                      (prog.start - config.TV_RECORD_PADDING_PRE)
                            if overlap <= ((config.TV_RECORD_PADDING_PRE + config.TV_RECORD_PADDING_POST)/4):
                                schedule.removeProgram(currently_recording,
                                    tv_util.getKey(currently_recording))
                                plugin.getbyname('RECORD').Stop()
                                _debug_('CALLED RECORD STOP 2: %s' % currently_recording, DINFO)
                    self.delay_recording = prog
                else:
                    self.delay_recording = None

                if self.delay_recording:
                    _debug_('delaying: %s' % prog, DINFO)
                else:
                    _debug_('going to record: %s' % prog, DINFO)
                    prog.isRecording = True
                    prog.rec_duration = duration + config.TV_RECORD_PADDING_POST - 10
                    prog.filename = tv_util.getProgFilename(prog)
                    rec_prog = prog

        for prog in progs.values():
            # If the program is over remove the entry.
            if now > (prog.stop + config.TV_RECORD_PADDING_POST):
                _debug_('found a program to clean: %s' % prog, DINFO)
                cleaned = True
                del progs[tv_util.getKey(prog)]

        if rec_prog or cleaned:
            schedule.setProgramList(progs)
            self.saveScheduledRecordings(schedule)

        if rec_prog:
            _debug_('start recording: %s' % rec_prog, DINFO)
            self.record_app = plugin.getbyname('RECORD')

            if not self.record_app:
                print_plugin_warning()
                _debug_('Recording %s failed.' % rec_prog.title, DERROR)
                self.removeScheduledRecording(rec_prog)
                return

            self.vg = self.fc.getVideoGroup(rec_prog.channel_id, False, CHANNEL_ID)
            suffix = self.vg.vdev.split('/')[-1]
            self.tv_lockfile = config.FREEVO_CACHEDIR + '/record.'+suffix
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
                        _debug_('Low on disk space - delete oldest recording: %s' % oldestrec, DINFO)
                        os.remove(os.path.join(path, oldestrec))
                        os.remove(os.path.join(path, oldestfxd))
                        freespace = util.freespace(path)
                        i = i + 1


    @kaa.rpc.expose('addFavorite')
    def addFavorite(self, name, prog, exactchan=False, exactdow=False, exacttod=False):
        _debug_('addFavorite(name=%r, prog=%r, exactchan=%r, exactdow=%r, exacttod=%r)' % (name, prog, exactchan, exactdow, exacttod), 2)
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
        _debug_('addEditedFavorite(name=%r, title=%r, chan=%r, dow=%r, mod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)' % (name, title, chan, dow, mod, priority, allowDuplicates, onlyNew), 2)
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
        _debug_('removeFavorite(name=%r)' % (name), 2)
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
        _debug_('clearFavorites()', 2)
        schedule = self.getScheduledRecordings()
        schedule.clearFavorites()
        self.saveScheduledRecordings(schedule)

        return (True, _('favorites cleared'))


    @kaa.rpc.expose('getFavorites')
    def getFavorites(self):
        _debug_('getFavorites()', 2)
        return self.getScheduledRecordings().getFavorites()


    @kaa.rpc.expose('getFavorite')
    def getFavorite(self, name):
        _debug_('getFavorite(name=%r)' % (name), 2)
        favs = self.getFavorites()

        if favs.has_key(name):
            fav = favs[name]
            return (True, fav)
        else:
            return (False, _('not a favorite'))


    @kaa.rpc.expose('adjustPriority')
    def adjustPriority(self, favname, mod=0):
        _debug_('adjustPriority(favname=%r, mod=%r)' % (favname, mod), 2)
        save = []
        mod = int(mod)
        (status, me) = self.getFavorite(favname)
        oldprio = int(me.priority)
        newprio = oldprio + mod

        _debug_('ap: mod=%s' % mod, DINFO)

        schedule = self.getScheduledRecordings()
        favs = schedule.getFavorites().values()

        _debug_('adjusting prio of %r' % (favname,), DINFO)
        for fav in favs:
            fav.priority = int(fav.priority)

            if fav.name == me.name:
                _debug_('MATCH', DINFO)
                fav.priority = newprio
                _debug_('moved prio of %s: %s => %s' % (fav.name, oldprio, newprio), DINFO)
                continue
            if mod < 0:
                if fav.priority < newprio or fav.priority > oldprio:
                    _debug_('fp: %s, old: %s, new: %s' % (fav.priority, oldprio, newprio), DINFO)
                    _debug_('skipping: %s' % fav.name, DINFO)
                    continue
                fav.priority = fav.priority + 1
                _debug_('moved prio of %s: %s => %s' % (fav.name, fav.priority-1, fav.priority), DINFO)

            if mod > 0:
                if fav.priority > newprio or fav.priority < oldprio:
                    _debug_('skipping: %s' % fav.name, DINFO)
                    continue
                fav.priority = fav.priority - 1
                _debug_('moved prio of %s: %s => %s' % (fav.name, fav.priority+1, fav.priority), DINFO)

        schedule.setFavoritesList(favs)
        self.saveScheduledRecordings(schedule)

        return (True, _('priority adjusted'))


    @kaa.rpc.expose('getFavoriteObject')
    def getFavoriteObject(self, prog, favs=None):
        """ more liberal favorite check that returns an object """
        _debug_('getFavoriteObject(prog=%r, favs=%r)' % (prog, favs), 2)
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
        _debug_('isProgAFavorite(%s)' % (prog,), 2)
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
        _debug_('doesFavoriteRecordOnlyNewEpisodes(prog=%r, favs=%r)' % (prog, favs), 2)
        if not favs:
            favs = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                if not hasattr(fav, 'onlyNew'):
                    return True
                _debug_('NEW: %s' % fav.onlyNew, DINFO)
                if fav.onlyNew == '1':
                    return True


    def doesFavoriteAllowDuplicates(self, prog, favs=None):
        _debug_('doesFavoriteAllowDuplicates(prog=%r, favs=%r)' % (prog, favs), 2)
        if not favs:
            favs = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                if not hasattr(fav, 'allowDuplicates'):
                    return True
                _debug_('DUP: %s' % fav.allowDuplicates, DINFO)
                if fav.allowDuplicates == '1':
                    return True


    @kaa.rpc.expose('removeFavoriteFromSchedule')
    def removeFavoriteFromSchedule(self, fav):
        _debug_('removeFavoriteFromSchedule(fav=%r)' % (fav), 2)
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
        return (True, 'favorite unscheduled')


    @kaa.rpc.expose('addFavoriteToSchedule')
    def addFavoriteToSchedule(self, fav):
        _debug_('addFavoriteToSchedule(fav=%r)' % (fav), 2)
        global guide
        favs = {}
        favs[fav.name] = fav

        self.updateGuide()

        for ch in guide.chan_list:
            for prog in ch.programs:
                (isFav, favorite) = self.isProgAFavorite(prog, favs)
                if isFav:
                    prog.isFavorite = favorite
                    self.scheduleRecording(prog)

        return (True, _('favorite scheduled'))


    @kaa.rpc.expose('updateFavoritesSchedule')
    def updateFavoritesSchedule(self):
        #  TODO: do not re-add a prog to record if we have
        #        previously decided not to record it.
        _debug_('updateFavoritesSchedule()', 2)

        global guide

        self.updateGuide()

        # First get the timeframe of the guide.
        last = 0
        for ch in guide.chan_list:
            for prog in ch.programs:
                if prog.start > last: last = prog.start

        schedule = self.getScheduledRecordings()

        favs = self.getFavorites()
        if not len(favs):
            return False

        schedule.lock()

        # Then remove all scheduled favorites in that timeframe to
        # make up for schedule changes.
        progs = schedule.getProgramList()
        for prog in progs.values():

            # try:
            #     favorite = prog.isFavorite
            # except:
            #     favorite = False

            # if prog.start <= last and favorite:
            (isFav, favorite) = self.isProgAFavorite(prog, favs)
            if prog.start <= last and isFav:
                # do not yet remove programs currently being recorded:
                isRec = hasattr(prog, "isRecording") and prog.isRecording
                if not isRec:
                    self.removeScheduledRecording(prog)

        for ch in guide.chan_list:
            for prog in ch.programs:
                (isFav, favorite) = self.isProgAFavorite(prog, favs)
                isRec = hasattr(prog, "isRecording") and prog.isRecording
                if isFav and not isRec:
                    prog.isFavorite = favorite
                    self.scheduleRecording(prog)

        schedule.unlock()
        return True


    def create_fxd(self, rec_prog):
        _debug_('create_fxd(rec_prog=%r)' % (rec_prog,), 2)
        from util.fxdimdb import FxdImdb, makeVideo
        fxd = FxdImdb()

        (filebase, fileext) = os.path.splitext(rec_prog.filename)
        fxd.setFxdFile(filebase, overwrite=True)

        desc = rec_prog.desc.replace('\n\n','\n').replace('\n','&#10;')
        video = makeVideo('file', 'f1', os.path.basename(rec_prog.filename))
        fxd.setVideo(video)
        fxd.info['tagline'] = fxd.str2XML(rec_prog.sub_title)
        fxd.info['plot'] = fxd.str2XML(desc)
        fxd.info['runtime'] = None
        fxd.info['recording_timestamp'] = str(rec_prog.start)
        # bad use of the movie year field :)
        try:
            fxd.info['year'] = time.strftime(config.TV_RECORD_YEAR_FORMAT, time.localtime(rec_prog.start))
        except:
            fxd.info['year'] = '2007'
        fxd.title = rec_prog.title
        if plugin.is_active('tv.recordings_manager'):
            fxd.info['watched'] = 'False'
            fxd.info['keep'] = 'False'
        fxd.writeFxd()


    def handleEvents(self, event):
        if event:
            if hasattr(event, 'arg'):
                _debug_('handleEvents(event=%s arg=%r)' % (event, event.arg))
            else:
                _debug_('handleEvents(event=%s)' % (event))

            if event == OS_EVENT_KILL:
                pass

            elif event == RECORD_START:
                prog = event.arg
                _debug_('RECORD_START %s' % (prog), DINFO)
                open(self.tv_lockfile, 'w').close()
                self.create_fxd(prog)
                if config.VCR_PRE_REC:
                    util.popen3.Popen3(config.VCR_PRE_REC)

            elif event == RECORD_STOP:
                prog = event.arg
                _debug_('RECORD_STOP %s' % (prog), DINFO)
                try:
                    snapshot(prog.filename)
                except:
                    # If automatic pickling fails, use on-demand caching when
                    # the file is accessed instead.
                    os.rename(vfs.getoverlay(prog.filename + '.raw.tmp'),
                              vfs.getoverlay(os.path.splitext(prog.filename)[0] + '.png'))
                    pass

                if config.VCR_POST_REC:
                    util.popen3.Popen3(config.VCR_POST_REC)

                if config.TV_RECORD_REMOVE_COMMERCIALS:
                    (result, response) = commdetectConnectionTest('connection test')
                    if result:
                        (status, idnr) = initCommDetectJob(prog.filename)
                        (status, output) = listCommdetectJobs()
                        _debug_(output, DINFO)
                        (status, output) = queueCommdetectJob(idnr, True)
                        _debug_(output, DINFO)
                    else:
                        _debug_('commdetect server not running', DINFO)

                if config.TV_REENCODE:
                    result = self.es.ping()
                    if result:
                        source = prog.filename
                        output = prog.filename
                        multipass = config.REENCODE_NUMPASSES > 1

                        (status, resp) = self.es.initEncodingJob(source, output, prog.title, None,
                            config.TV_REENCODE_REMOVE_SOURCE)
                        _debug_('initEncodingJob:status:%s resp:%s' % (status, resp))

                        idnr = resp

                        (status, resp) = self.es.setContainer(idnr, config.REENCODE_CONTAINER)
                        _debug_('setContainer:status:%s resp:%s' % (status, resp))

                        (status, resp) = self.es.setVideoCodec(idnr, config.REENCODE_VIDEOCODEC, 0, multipass,
                            config.REENCODE_VIDEOBITRATE, config.REENCODE_ALTPROFILE)
                        _debug_('setVideoCodec:status:%s resp:%s' % (status, resp))

                        (status, resp) = self.es.setAudioCodec(idnr, config.REENCODE_AUDIOCODEC,
                            config.REENCODE_AUDIOBITRATE)
                        _debug_('setAudioCodec:status:%s resp:%s' % (status, resp))

                        (status, resp) = self.es.setNumThreads(idnr, config.REENCODE_NUMTHREADS)
                        _debug_('setNumThreads:status:%s resp:%s' % (status, resp))

                        (status, resp) = self.es.setVideoRes(idnr, config.REENCODE_RESOLUTION)
                        _debug_('setVideoRes:status:%s resp:%s' % (status, resp))

                        (status, resp) = self.es.listJobs()
                        _debug_('listJobs:status:%s resp:%s' % (status, resp))

                        (status, resp) = self.es.queueIt(idnr, True)
                        _debug_('queueIt:status:%s resp:%s' % (status, resp))
                    else:
                        _debug_('encoding server not running', DINFO)

                # This is a really nasty hack but if it fixes the problem then great
                if self.delay_recording:
                    prog = self.delay_recording
                    #schedule.setProgramList(progs)
                    #self.saveScheduledRecordings(schedule)
                    prog.isRecording = True
                    duration = int(prog.stop) - int(time.time())
                    prog.rec_duration = duration + config.TV_RECORD_PADDING_POST - 10
                    prog.filename = tv_util.getProgFilename(prog)
                    rec_prog = prog
                    _debug_('start delayed recording: %s' % rec_prog, DINFO)
                    self.record_app = plugin.getbyname('RECORD')
                    self.vg = self.fc.getVideoGroup(rec_prog.channel_id, False, CHANNEL_ID)
                    suffix = self.vg.vdev.split('/')[-1]
                    self.record_app.Record(rec_prog)
                    self.delay_recording = None
                else:
                    os.remove(self.tv_lockfile)
            else:
                _debug_('%s not handled' % (event), DINFO)
        else:
            # Should never happen
            _debug_('%s unknown' % (event), DINFO)


    def handleAtTimer(self):
        _debug_('handleAtTimer()', 2)
        self.checkToRecord()


def main():
    socket = ('', config.RECORDSERVER_PORT)
    secret = config.RECORDSERVER_SECRET
    _debug_('socket=%r, secret=%r' % (socket, secret))

    recordserver = RecordServer()

    try:
        rpc = kaa.rpc.Server(socket, secret)
    except Exception:
        raise

    rpc.connect(recordserver)

    eh = EventHandler(recordserver.handleEvents)
    eh.register()


    _debug_('kaa.AtTimer starting')
    kaa.AtTimer(recordserver.handleAtTimer).start(sec=45)
    _debug_('kaa.main starting')
    kaa.main.run()
    _debug_('kaa.main finished')


if __name__ == '__main__':
    import socket
    import glob

    sys.stdout = config.Logger(sys.argv[0] + ':stdout')
    sys.stderr = config.Logger(sys.argv[0] + ':stderr')

    locks = glob.glob(config.FREEVO_CACHEDIR + '/record.*')
    for f in locks:
        _debug_('Removed old record lock \"%s\"' % f, DINFO)
        os.remove(f)

    try:
        _debug_('main() starting')
        main()
        _debug_('main() finished')
    except SystemExit:
        _debug_('main() stopped')
        pass
    except Exception, why:
        import traceback
        traceback.print_exc()
        _debug_(why, DWARNING)
