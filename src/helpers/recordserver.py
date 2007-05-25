#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# record_server.py - A network aware TV recording server.
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


import sys, string, random, time, os, re, pwd, stat, threading, md5, datetime, copy
import cPickle, pickle
import config
from util import vfs

appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
appconf = appname.upper()

# change uid
if __name__ == '__main__':
    uid='config.'+appconf+'_UID'
    gid='config.'+appconf+'_GID'
    try:
        if eval(uid) and os.getuid() == 0:
            os.setgid(eval(gid))
            os.setuid(eval(uid))
            os.environ['USER'] = pwd.getpwuid(os.getuid())[0]
            os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
    except Exception, e:
        print e

from twisted.web import xmlrpc, server
from twisted.internet.app import Application
from twisted.internet import reactor
from twisted.python import log
from util.marmalade import jellyToXML, unjellyFromXML
from video.commdetectclient import initCommDetectJob
from video.commdetectclient import queueIt
from video.commdetectclient import listJobs
from video.commdetectclient import connectionTest

import rc
rc_object = rc.get_singleton(use_pylirc=0, use_netremote=0)

from tv.record_types import TYPES_VERSION
from tv.record_types import ScheduledRecordings

import tv.record_types
import tv.epg_xmltv
import util.tv_util as tv_util
import plugin
import util.popen3
from tv.channels import FreevoChannels
from util.videothumb import snapshot
from event import *


DEBUG = hasattr(config, appconf+'_DEBUG') and eval('config.'+appconf+'_DEBUG') or config.DEBUG

logfile = '%s/%s-%s.log' % (config.LOGDIR, appname, os.getuid())
log.startLogging(open(logfile, 'a'))

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            log.debug(String(text))
        except:
            print String(text)

_debug_('PLUGIN_RECORD: %s' % config.plugin_record)

plugin.init_special_plugin(config.plugin_record)

def print_plugin_warning():
    print '*************************************************'
    print '**  Warning: No recording plugin registered.  **'
    print '**           Check your local_conf.py for a   **'
    print '**           bad "plugin_record =" line or    **'
    print '**           this log for a plugin failure.   **'
    print '**           Recordings will fail!            **'
    print '*************************************************'


if not plugin.getbyname('RECORD'):
    print_plugin_warning()


class RecordServer(xmlrpc.XMLRPC):

    def __init__(self):
        self.lock = threading.Lock()
        self.fc = FreevoChannels()
        # XXX: In the future we should have one lock per VideoGroup.
        self.tv_lock_file = None
        self.vg = None
        self.previouslyRecordedShows = None
        self.delay_recording = None


    def isRecording(self):
        _debug_('in isRecording', 4)
        return glob.glob(config.FREEVO_CACHEDIR + '/record.*') and TRUE or FALSE


    def progsTimeCompare(self, first, second):
        t1 = first.split(':')[-1]
        t2 = second.split(':')[-1]
        try:
            return int(float(t1)) - int(float(t2))
        except ArithmeticError:
            pass
        return 0


    def findOverlaps(self, scheduledRecordings):
        _debug_('in findOverlaps', 4)
        progs = scheduledRecordings.getProgramList()
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
                _debug_('Overlap:\n%s\n%s' % (thisprog, nextprog), 0)


    def findNextProgram(self):
        _debug_('in findNextProgram', 4)

        next_program = None
        progs = self.getScheduledRecordings().getProgramList()
        proglist = list(progs)
        proglist.sort(self.progsTimeCompare)
        now = time.time()
        timenow = time.localtime(now)
        for progitem in proglist:
            prog = progs[progitem]
            _debug_('%s' % (prog), 2)

            try:
                recording = prog.isRecording
            except:
                recording = FALSE
            endtime = time.strftime(config.TV_TIMEFORMAT, time.localtime(prog.stop+config.TV_RECORD_PADDING_POST))
            _debug_('%s is recording %s stopping at %s' % (prog.title, recording and 'yes' or 'no', endtime), 3)

            if now > prog.stop + config.TV_RECORD_PADDING_POST:
                _debug_('%s: finished %s > %s' % (prog.title, timenow, endtime), 1)
                continue

            if not recording:
                next_program = prog
                break

        self.next_program = next_program
        if next_program == None:
            _debug_('No program scheduled to record', 3)
            return None

        _debug_('next is %s' % (next_program), 2)
        return next_program


    def isPlayerRunning(self):
        '''
        returns the state of a player, mplayer, xine, etc.
        TODO:
            real player running test, check /dev/videoX.
            this could go into the upsoon client
        '''
        _debug_('in isPlayerRunning', 4)
        return (os.path.exists(config.FREEVO_CACHEDIR + '/playing'))


    # note: add locking and r/rw options to get/save funs
    def getScheduledRecordings(self):
        file_ver = None
        scheduledRecordings = None

        if os.path.isfile(config.TV_RECORD_SCHEDULE):
            _debug_('reading cached file (%s)' % config.TV_RECORD_SCHEDULE, 4)
            if hasattr(self, 'scheduledRecordings_cache'):
                mod_time, scheduledRecordings = self.scheduledRecordings_cache
                try:
                    if os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME] == mod_time:
                        _debug_('Return cached data', 4)
                        return scheduledRecordings
                except OSError, e:
                    _debug_('exception=%r' % e, 0)
                    pass

            f = open(config.TV_RECORD_SCHEDULE, 'r')
            scheduledRecordings = unjellyFromXML(f)
            f.close()

            try:
                file_ver = scheduledRecordings.TYPES_VERSION
            except AttributeError:
                _debug_('The cache does not have a version and must be recreated.', 0)

            if file_ver != TYPES_VERSION:
                _debug_(('ScheduledRecordings version number %s is stale (new is %s), must ' +
                        'be reloaded') % (file_ver, TYPES_VERSION), 1)
                scheduledRecordings = None
            else:
                _debug_('Got ScheduledRecordings (version %s).' % file_ver, 0)

        if not scheduledRecordings:
            _debug_('GET: making a new ScheduledRecordings', 0)
            scheduledRecordings = ScheduledRecordings()
            self.saveScheduledRecordings(scheduledRecordings)

        _debug_('ScheduledRecordings has %s items.' % \
                len(scheduledRecordings.programList), 1)

        try:
            mod_time = os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME]
            self.scheduledRecordings_cache = mod_time, scheduledRecordings
        except OSError:
            pass
        return scheduledRecordings


    def saveScheduledRecordings(self, scheduledRecordings=None):
        ''' function to save the schedule to disk '''

        if not scheduledRecordings:
            _debug_('making a new ScheduledRecordings', 0)
            scheduledRecordings = ScheduledRecordings()

        self.findOverlaps(scheduledRecordings)
        _debug_('saving cached file (%s) with %s items' % \
            (config.TV_RECORD_SCHEDULE, len(scheduledRecordings.programList)), 2)
        try:
            f = open(config.TV_RECORD_SCHEDULE, 'w')
        except IOError:
            os.unlink(config.TV_RECORD_SCHEDULE)
            f = open(config.TV_RECORD_SCHEDULE, 'w')

        jellyToXML(scheduledRecordings, f)
        f.close()

        try:
            mod_time = os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME]
            self.scheduledRecordings_cache = mod_time, scheduledRecordings
        except OSError:
            pass

        return TRUE

    def loadPreviouslyRecordedShows(self):
        ''' Load the saved set of recorded shows '''
        if self.previouslyRecordedShows:
            return

        cacheFile = config.FREEVO_CACHEDIR + "/previouslyRecorded.pickle"
        try:
            self.previouslyRecordedShows = cPickle.load(open(cacheFile, "r"))
        except:
            try:
                self.previouslyRecordedShows = pickle.load(open(cacheFile, "r"))
            except IOError:
                self.previouslyRecordedShows = {}
                pass

    def savePreviouslyRecordedShows(self):
        ''' Save the set of recorded shows '''
        if not self.previouslyRecordedShows:
            return

        cacheFile=config.FREEVO_CACHEDIR+"/previouslyRecorded.pickle"
        try:
            cPickle.dump(self.previouslyRecordedShows, open(cacheFile, "w"))
        except:
            pickle.dump(self.previouslyRecordedShows, open(cacheFile, "w"))

    def newEpisode(self, prog=None):
        ''' Return true if this is a new episode of 'prog' '''
        todayStr = datetime.date.today().strftime('%Y%m%d')
        progStr = str(prog.date)
        _debug_('Program Date: "%s"' % progStr, 0)
        _debug_('Todays Date : "%s"' % todayStr, 0)
        if (len(progStr)==8):
            _debug_('Good date format', 0)
            #Year
            todaysYear=(todayStr[0:4])
            progYear=(progStr[0:4])
            #Month
            todaysMonth=(todayStr[4:2])
            progMonth=(progStr[4:2])
            #Day
            todaysDay=(todayStr[6:2])
            progDay=(progStr[6:2])
            if todaysYear > progYear:
                #program from a previous year
                return FALSE
            elif progYear > todaysYear:
                #program in the future
                return TRUE
            else:
                _debug_('Same year', 0)
                #program in the same year
                if todaysMonth > progMonth:
                    #program in a previous month
                    return FALSE
                elif progMonth > todaysMonth:
                    #program in the future
                    return TRUE
                else:
                    _debug_('Same month', 0)
                    #program in the same month
                    if todaysDay > progDay:
                        #program was previous aired this month
                        return FALSE
                    else:
                        _debug_('Same day or in the upcoming month', 0)
                        #program is today or in the upcoming days
                        return TRUE
        else:
            _debug_('No good date format, assuming new Episode to be on the safe side', 0)
            return TRUE

    def shrink(self, text):
        ''' Shrink a string by removing all spaces and making it
        lower case and then returning the MD5 digest of it. '''
        if text:
            text = md5.new(text.lower().replace(' ', '')).hexdigest()
        else:
            text = ''
        return text


    def getPreviousRecordingKey(self, prog):
        '''Return the key to be used for a given prog in the
        previouslyRecordedShows hashtable.'''
        shrunkTitle = self.shrink(prog.title)
        shrunkSub   = self.shrink(prog.sub_title)
        shrunkDesc  = self.shrink(prog.desc);
        return ('%s-%s-%s' % (shrunkTitle, shrunkSub, shrunkDesc), \
                '%s-%s-'   % (shrunkTitle, shrunkSub),             \
                '%s--%s'   % (shrunkTitle, shrunkDesc))


    def getPreviousRecording(self, prog):
        '''Get a previous recording, or None if none.'''
        try:
            return self.previouslyRecordedShows[self.getPreviousRecordingKey(prog)]
        except KeyError:
            return None


    def removeDuplicate(self, prog=None):
        '''Remove a duplicate recording'''
        self.loadPreviouslyRecordedShows()
        previous = self.getPreviousRecording(prog)
        if previous:
            _debug_('Found duplicate, removing', 0)
            del self.previouslyRecordedShows[self.getPreviousRecordingKey(previous)]
            self.savePreviouslyRecordedShows()


    def addDuplicate(self, prog=None):
        '''Add program to duplicates hash'''
        _debug_('No previous recordings for "%s", "%s", "%s", adding to hash and saving' % \
        (prog.title, prog.sub_title, prog.desc), 5)
        self.loadPreviouslyRecordedShows()
        self.previouslyRecordedShows[self.getPreviousRecordingKey(prog)] = prog
        for key in self.getPreviousRecordingKey(prog):
            self.previouslyRecordedShows[key] = prog.start
        self.savePreviouslyRecordedShows()


    def duplicate(self, prog=None):
        '''Identify if the given programme is a duplicate. If not,
        record it as previously recorded.'''
        self.loadPreviouslyRecordedShows()
        previous = self.getPreviousRecording(prog)
        if previous:
            _debug_('Found duplicate for "%s", "%s", "%s", not adding' % \
            (prog.title, prog.sub_title, prog.desc), 5)
            return TRUE
        return FALSE


    def addRecordingToSchedule(self, prog=None, inputSchedule=None):
        if inputSchedule:
            scheduledRecordings=inputSchedule
        else:
            scheduledRecordings = self.getScheduledRecordings()
        scheduledRecordings.addProgram(prog, tv_util.getKey(prog))
        if not inputSchedule:
            if config.DUPLICATE_DETECTION:
                self.addDuplicate(prog)
            self.saveScheduledRecordings(scheduledRecordings)


    def removeRecordingFromSchedule(self, prog=None, inputSchedule=None):
        if inputSchedule:
            scheduledRecordings=inputSchedule
        else:
            scheduledRecordings = self.getScheduledRecordings()
        scheduledRecordings.removeProgram(prog, tv_util.getKey(prog))
        if not inputSchedule:
            if config.DUPLICATE_DETECTION:
                self.removeDuplicate(prog)
            self.saveScheduledRecordings(scheduledRecordings)


    def conflictResolution(self, prog):
        def exactMatch(self, prog):
            if prog.desc:
                descResult=FALSE
                descMatches=None
                (descResult, descMatches)=self.findMatches(prog.desc)
                if descResult:
                    _debug_('Exact Matches %s' % (len(descMatches)), 0)
                    return descMatches

            if prog.sub_title:
                sub_titleResult=FALSE
                sub_titleMatches=None
                (sub_titleResult, sub_titleMatches)=self.findMatches(prog.sub_title)
                if sub_titleResult:
                    _debug_('Exact Matches %s' % (len(sub_titleMatches)), 0)
                    return sub_titleMatches
            return None

        def getConflicts(self, prog, myScheduledRecordings):
            _debug_('Before mySched recordings; ignore all addProgram lines', 0)
            self.addRecordingToSchedule(prog, myScheduledRecordings)
            progs = myScheduledRecordings.getProgramList()
            proglist = list(progs)
            proglist.sort(self.progsTimeCompare)
            conflictRating=0
            conflicts=[]
            for i in range(0, len(proglist)-1):
                thisprog = progs[proglist[i]]
                nextprog = progs[proglist[i+1]]
                if thisprog.stop > nextprog.start:
                    conflictRating=conflictRating+1
                    if thisprog==prog:
                        conflicts.append(nextprog)
                    elif nextprog==prog:
                        conflicts.append(thisprog)
            self.removeRecordingFromSchedule(prog, myScheduledRecordings)
            _debug_('After mySched recordings; stop ignoring all addProgram lines', 0)
            return (conflictRating, conflicts)

        def getRatedConflicts(self, prog, myScheduledRecordings):
            ratedConflicts=[]
            occurances = exactMatch(self, prog)
            if not occurances:
                #program no longer exists
                return (FALSE, None, None)
            #Search through all occurances of looking for a non-conflicted occurance
            for oneOccurance in occurances:
                (rating, conflictedProgs)=getConflicts(self, oneOccurance, myScheduledRecordings)
                if rating==0:
                    _debug_('No Conflict', 0)
                    programsToChange=[]
                    programsToChange.append(('add', oneOccurance))
                    return(TRUE, ratedConflicts, programsToChange)
                _debug_('Conflict Found', 0)
                ratedConflicts.append((rating, conflictedProgs, oneOccurance))
            return (FALSE, ratedConflicts, None)

        if config.CONFLICT_RESOLUTION:
            _debug_('Conflict resolution enabled', 0)
            ratedConflicts=[]
            myScheduledRecordings = copy.deepcopy(self.getScheduledRecordings())

            #Try to record it at its listed time
            (rating, conflictedProg)=getConflicts(self, prog, myScheduledRecordings)
            if rating==0:
                #No need to do anything fancy; this will work at its defaul time
                progsToChange=[]
                progsToChange.append(('add', prog))
                return (TRUE, 'No conflicts, using default time', progsToChange)

            #Default time didn't work, let's try all times known
            (result, ratedConflicts, progsToChange)=getRatedConflicts(self, prog, myScheduledRecordings)
            if result:
                #No conflicts
                return (TRUE, 'No conflicts if new program is added', progsToChange)
            if not ratedConflicts:
                #Program no longer exists, should never hit this unless schedule changes
                return (FALSE, 'Cannot schedule, new prog no longer exists', None)

            _debug_('Going into conflict resolution via scheduled program re-scheduling', 0)
            # No viable time to schedule the program without a conflict
            # Try and reschedule the already scheduled program
            atleastOneSingleConflict=FALSE
            for (scheduledConflictRating, scheduledConflictPrograms, conflictProgram) in ratedConflicts:
                #Only handle one conflict at the moment
                if scheduledConflictRating==1:
                    atleastOneSingleConflict=TRUE
                    scheduledConflictProgram=scheduledConflictPrograms[0]
                    #remove already scheduled program and try to reschedule it with the new program
                    self.removeRecordingFromSchedule(scheduledConflictProgram, myScheduledRecordings)
                    self.addRecordingToSchedule(conflictProgram, myScheduledRecordings)
                    (result, ratedConflicts, progsToChange)=getRatedConflicts(self, \
                        scheduledConflictProgram, myScheduledRecordings)
                    if result:
                        #No conflicts
                        progsToChange.append(('del', scheduledConflictProgram))
                        progsToChange.append(('add', conflictProgram))
                        return (TRUE, 'No conflicts if scheduled program is rescheduled', progsToChange)
                    if not ratedConflicts:
                        #Program no longer exists, should never hit this unless schedule changes
                        progsToChange.append(('del', scheduledConflictProgram))
                        progsToChange.append(('add', conflictProgram))
                        return (TRUE, 'Cannot find conflicted program, adding new', progsToChange)
                    #Return this to original state
                    self.addRecordingToSchedule(scheduledConflictProgram, myScheduledRecordings)
                    self.removeRecordingFromSchedule(conflictProgram, myScheduledRecordings)
            if not atleastOneSingleConflict:
                #Dirty way to (not) handle multiple conflicts
                return (FALSE, 'Cannot handle multiple conflicts: %s not scheduled' % (prog.title), None)

            _debug_('Going into conflict resolution via priority', 0)
            # No viable option to reschedule the original program
            # Time to resolve the conflict via priority
            tempRating=1000
            tempConflicted=None
            tempProg=None
            #Find least conflicted
            for (conflictedRating, conflictedPrograms, tempProgram) in ratedConflicts:
                #Cannot handle multiple conflicts
                conflictedProgram=conflictedPrograms[0]
                if conflictedRating < tempRating:
                    tempRating=conflictedRating
                    tempConflicted=conflictedProgram
                    tempProg=tempProgram
            conflictedProgram=tempConflicted
            prog=tempProgram

            #Here is where it gets ugly
            (isProgFav, progFav) = self.getFavoriteObject(prog)
            (isConfFav, confFav) = self.getFavoriteObject(conflictedProgram)
            if not isProgFav and isConfFav:
                #Regular recording has higher priority then favorite
                progsToChange=[]
                progsToChange.append(('del', conflictedProgram))
                progsToChange.append(('add', prog))
                reason='New program is a regular recording(added), scheduled is a Favorite(removed)'
                return (TRUE, reason, progsToChange)
            elif isProgFav and not isConfFav:
                #Regular recording has higher priority then favorite
                progsToChange=[]
                progsToChange.append(('del', prog))
                progsToChange.append(('add', conflictedProgram))
                reason='Scheduled program is a regular recording(added), new is a Favorite(removed)'
                return (TRUE, reason, progsToChange)
            elif not isProgFav and not isConfFav:
                return (FALSE, 'Both are regular programs, not adding new recording', None)
            elif isProgFav and isConfFav:
                #Both are favorites, go by priority (lower is better)
                if progFav.priority < confFav.priority:
                    progsToChange=[]
                    progsToChange.append(('del', conflictedProgram))
                    progsToChange.append(('add', prog))
                    reason='New program is higher rated(added), Scheduled is lower(removed)'
                    return (TRUE, reason, progsToChange)
                elif confFav.priority < progFav.priority:
                    progsToChange=[]
                    progsToChange.append(('del', prog))
                    progsToChange.append(('add', conflictedProgram))
                    reason='Scheduled program is higher rated(added), New is lower(removed)'
                    return (TRUE, reason, progsToChange)
                else:
                    #Equal priority, not adding new program
                    return (FALSE, 'Both are regular programs, not adding new recording', None)
            else:
                return (FALSE, 'No viable way to schedule', None)
        else:
            progsToChange=[]
            progsToChange.append(('add', prog))
            return (TRUE, 'Conflict resolution disabled', progsToChange)


    def checkOnlyNewDetection(self, prog=None):
        if config.ONLY_NEW_DETECTION:
            _debug_('Only new episode detection enabled', 0)
            if not self.doesFavoriteRecordOnlyNewEpisodes(prog):
                return (TRUE, 'Favorite records all episodes, record')
            if self.newEpisode(prog):
                return (TRUE, 'New episode, record')
            else:
                return (FALSE, 'Old episode, do not record')
        else:
            return (TRUE, 'Only new episode detection disabled, record')


    def checkDuplicateDetection(self, prog=None):
        if config.DUPLICATE_DETECTION:
            _debug_('Duplicate detection enabled', 0)
            if self.doesFavoriteAllowDuplicates(prog):
                return (TRUE, 'Favorite allows duplicates, record')
            if not self.duplicate(prog):
                return (TRUE, 'Not a duplicate, record')
            else:
                return (FALSE, 'Duplicate recording, do not record')
        else:
            return (TRUE, 'Duplicate detection is disabled, record')


    def setTunerid(self, prog):
        for chan in guide.chan_list:
            if prog.channel_id == chan.id:
                prog.tunerid = chan.tunerid
                _debug_('%s tuner: %s' % (prog, prog.tunerid), 1)
        return prog


    def scheduleRecording(self, prog=None):
        global guide

        if not prog:
            return (FALSE, 'no prog')

        now = time.time()
        if now > prog.stop:
            return (FALSE, 'cannot record it if it is over')

        self.updateGuide()

        (isFav, favorite) = self.isProgAFavorite(prog)
        if isFav:
            (onlyNewBool, onlyNewReason) = self.checkOnlyNewDetection(prog)
            _debug_('Only new episode detection: %s reason %s' % (onlyNewBool, onlyNewReason), 2)
            if not onlyNewBool:
                #failed only new episode check (old episode, etc)
                return (FALSE, onlyNewReason)

            (duplicateBool, duplicateReason) = self.checkDuplicateDetection(prog)
            _debug_('Duplicate detection: %s reason %s' % (duplicateBool, duplicateReason), 2)
            if not duplicateBool:
                #failed duplicate check (duplicate, etc)
                return (FALSE, duplicateReason)

        (ableToResolveBool, resolutionReason, progsToChange) = self.conflictResolution(prog)
        _debug_('Conflict resolution: %s reason %s' % (ableToResolveBool, resolutionReason), 2)
        if not ableToResolveBool:
            #No viable solution was found
            return (FALSE, resolutionReason)

        if progsToChange:
            for (cmd, prog) in progsToChange:
                prog=self.setTunerid(prog)
                if cmd=='add':
                    _debug_('adding %s to schedule' % (prog.title), 2)
                    self.addRecordingToSchedule(prog)
                elif cmd=='del':
                    _debug_('removed %s from schedule' % (prog.title), 2)
                    self.removeRecordingFromSchedule(prog)
        else:
            prog=self.setTunerid(prog)
            _debug_('added %s to schedule' % (prog.title), 0)
            self.addRecordingToSchedule(prog)

        # check, maybe we need to start right now
        self.checkToRecord()

        return (TRUE, 'recording scheduled')


    def removeScheduledRecording(self, prog=None):
        if not prog:
            return (FALSE, 'no prog')

        # get our version of 'prog'
        # It's a bad hack, but we can use isRecording than
        sr = self.getScheduledRecordings()
        progs = sr.getProgramList()

        for saved_prog in progs.values():
            if String(saved_prog) == String(prog):
                prog = saved_prog
                break

        try:
            recording = prog.isRecording
        except Exception, e:
            recording = FALSE

        self.removeRecordingFromSchedule(prog)

        now = time.time()

        # if now >= prog.start and now <= prog.stop and recording:
        if recording:
            _debug_('stopping current recording %s' % (prog), 0)
            rec_plugin = plugin.getbyname('RECORD')
            if rec_plugin:
                rec_plugin.Stop()

        return (TRUE, 'recording removed')


    def isProgScheduled(self, prog, schedule=None):

        if schedule == {}:
            return (FALSE, 'prog not scheduled')

        if not schedule:
            schedule = self.getScheduledRecordings().getProgramList()

        for me in schedule.values():
            if me.start == prog.start and me.channel_id == prog.channel_id:
                return (TRUE, 'prog is scheduled')

        return (FALSE, 'prog not scheduled')


    def findProg(self, chan=None, start=None):
        global guide

        _debug_('findProg: %s, %s' % (chan, start), 0)

        if not chan or not start:
            return (FALSE, 'no chan or no start')

        self.updateGuide()

        for ch in guide.chan_list:
            if chan == ch.id:
                _debug_('CHANNEL MATCH: %s' % ch.id, 0)
                for prog in ch.programs:
                    if start == '%s' % prog.start:
                        _debug_('PROGRAM MATCH 1: %s' % prog, 0)
                        return (TRUE, prog.utf2str())

        return (FALSE, 'prog not found')


    def findMatches(self, find=None, movies_only=None):
        global guide

        _debug_('findMatches: %s' % find, 0)

        matches = []
        max_results = 500

        if not find and not movies_only:
            _debug_('nothing to find', 0)
            return (FALSE, 'no search string')

        self.updateGuide()

        pattern = '.*' + find + '\ *'
        regex = re.compile(pattern, re.IGNORECASE)
        now = time.time()

        for ch in guide.chan_list:
            for prog in ch.programs:
                if now >= prog.stop:
                    continue
                if not find or regex.match(prog.title) or regex.match(prog.desc) \
                   or regex.match(prog.sub_title):
                    if movies_only:
                        # We can do better here than just look for the MPAA
                        # rating.  Suggestions are welcome.
                        if 'MPAA' in prog.utf2str().getattr('ratings').keys():
                            matches.append(prog.utf2str())
                            _debug_('PROGRAM MATCH 2: %s' % prog, 0)
                    else:
                        # We should never get here if not find and not
                        # movies_only.
                        matches.append(prog.utf2str())
                        _debug_('PROGRAM MATCH 3: %s' % prog, 0)
                if len(matches) >= max_results:
                    break

        _debug_('Found %d matches.' % len(matches), 0)

        if matches:
            return (TRUE, matches)
        return (FALSE, 'no matches')


    def updateGuide(self):
        global guide
        guide = tv.epg_xmltv.get_guide()


    def checkToRecord(self):
        _debug_('checkToRecord %s' % (time.strftime('%H:%M:%S', time.localtime(time.time()))), 1)
        rec_cmd = None
        rec_prog = None
        cleaned = None

        sr = self.getScheduledRecordings()
        progs = sr.getProgramList()

        currently_recording = None
        for prog in progs.values():
            try:
                recording = prog.isRecording
            except:
                recording = FALSE

            if recording:
                currently_recording = prog

        now = time.time()
        for prog in progs.values():
            _debug_('progloop=%s' % prog, 4)

            try:
                recording = prog.isRecording
            except:
                recording = FALSE

            if not recording \
                and now >= (prog.start - config.TV_RECORD_PADDING_PRE) \
                and now < (prog.stop + config.TV_RECORD_PADDING_POST):
                # just add to the 'we want to record this' list
                # then end the loop, and figure out which has priority,
                # remember to take into account the full length of the shows
                # and how much they overlap, or chop one short
                duration = int(prog.stop) - int(now)
                if duration < 10:
                    _debug_('duration %s too small' % duration, 0)
                    return

                if currently_recording:
                    # Hey, something is already recording!
                    overlap_duration = currently_recording.stop - prog.start
                    _debug_('overlap_duration=%r' % overlap_duration, 0)
                    if prog.start - 10 <= now:
                        # our new recording should start no later than now!
                        # check if the new prog is a favorite and the current running is
                        # not. If so, the user manually added something, we guess it
                        # has a higher priority.
                        if self.isProgAFavorite(prog)[0] \
                            and not self.isProgAFavorite(currently_recording)[0] \
                            and now < (prog.stop + config.TV_RECORD_PADDING_POST):
                            _debug_('Ignoring %s' % prog, 0)
                            continue
                        sr.removeProgram(currently_recording,
                                         tv_util.getKey(currently_recording))
                        plugin.getbyname('RECORD').Stop()
                        _debug_('CALLED RECORD STOP 1: %s' % currently_recording, 0)
                    else:
                        # at this moment we must be in the pre-record padding
                        if currently_recording.stop - 10 <= now:
                            # The only reason we are still recording is because of the post-record padding.
                            # Therefore we have overlapping paddings but not real stop / start times.
                            overlap = (currently_recording.stop + config.TV_RECORD_PADDING_POST) - \
                                      (prog.start - config.TV_RECORD_PADDING_PRE)
                            if overlap <= ((config.TV_RECORD_PADDING_PRE +
                                            config.TV_RECORD_PADDING_POST)/4):
                                sr.removeProgram(currently_recording,
                                                 tv_util.getKey(currently_recording))
                                plugin.getbyname('RECORD').Stop()
                                _debug_('CALLED RECORD STOP 2: %s' % currently_recording, 0)
                    self.delay_recording = prog
                else:
                    self.delay_recording = None

                if self.delay_recording:
                    _debug_('delaying: %s' % prog, 0)
                else:
                    _debug_('going to record: %s' % prog, 0)
                    prog.isRecording = TRUE
                    prog.rec_duration = duration + config.TV_RECORD_PADDING_POST - 10
                    prog.filename = tv_util.getProgFilename(prog)
                    rec_prog = prog

        for prog in progs.values():
            # If the program is over remove the entry.
            if now > (prog.stop + config.TV_RECORD_PADDING_POST):
                _debug_('found a program to clean: %s' % prog, 0)
                cleaned = TRUE
                del progs[tv_util.getKey(prog)]

        if rec_prog or cleaned:
            sr.setProgramList(progs)
            self.saveScheduledRecordings(sr)

        if rec_prog:
            _debug_('start recording: %s' % rec_prog, 0)
            self.record_app = plugin.getbyname('RECORD')

            if not self.record_app:
                print_plugin_warning()
                _debug_('ERROR:  Recording %s failed.' % rec_prog.title, 0)
                self.removeScheduledRecording(rec_prog)
                return

            self.vg = self.fc.getVideoGroup(rec_prog.channel_id, FALSE)
            suffix=self.vg.vdev.split('/')[-1]
            self.tv_lock_file = config.FREEVO_CACHEDIR + '/record.'+suffix
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
                        _debug_('Low on disk space - delete oldest recording: %s' % oldestrec, 0)
                        os.remove(os.path.join(path, oldestrec))
                        os.remove(os.path.join(path, oldestfxd))
                        freespace = util.freespace(path)
                        i = i + 1

    def addFavorite(self, name, prog, exactchan=FALSE, exactdow=FALSE, exacttod=FALSE):
        if not name:
            return (FALSE, 'no name')

        (status, favs) = self.getFavorites()
        priority = len(favs) + 1
        fav = tv.record_types.Favorite(name, prog, exactchan, exactdow, exacttod, priority, allowDuplicates, onlyNew)

        scheduledRecordings = self.getScheduledRecordings()
        scheduledRecordings.addFavorite(fav)
        self.saveScheduledRecordings(scheduledRecordings)
        self.addFavoriteToSchedule(fav)

        return (TRUE, 'favorite added')


    def addEditedFavorite(self, name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
        fav = tv.record_types.Favorite()

        fav.name = name
        fav.title = title
        fav.channel = chan
        fav.dow = dow
        fav.mod = mod
        fav.priority = priority
        fav.allowDuplicates = allowDuplicates
        fav.onlyNew = onlyNew

        scheduledRecordings = self.getScheduledRecordings()
        scheduledRecordings.addFavorite(fav)
        self.saveScheduledRecordings(scheduledRecordings)
        self.addFavoriteToSchedule(fav)

        return (TRUE, 'favorite added')


    def removeFavorite(self, name=None):
        if not name:
            return (FALSE, 'no name')

        (status, fav) = self.getFavorite(name)
        self.removeFavoriteFromSchedule(fav)
        scheduledRecordings = self.getScheduledRecordings()
        scheduledRecordings.removeFavorite(name)
        self.saveScheduledRecordings(scheduledRecordings)

        return (TRUE, 'favorite removed')


    def clearFavorites(self):
        scheduledRecordings = self.getScheduledRecordings()
        scheduledRecordings.clearFavorites()
        self.saveScheduledRecordings(scheduledRecordings)

        return (TRUE, 'favorites cleared')


    def getFavorites(self):
        return (TRUE, self.getScheduledRecordings().getFavorites())


    def getFavorite(self, name):
        (status, favs) = self.getFavorites()

        if favs.has_key(name):
            fav = favs[name]
            return (TRUE, fav)
        else:
            return (FALSE, 'not a favorite')


    def adjustPriority(self, favname, mod=0):
        save = []
        mod = int(mod)
        (status, me) = self.getFavorite(favname)
        oldprio = int(me.priority)
        newprio = oldprio + mod

        _debug_('ap: mod=%s' % mod, 0)

        sr = self.getScheduledRecordings()
        favs = sr.getFavorites().values()

        _debug_('adjusting prio of '+favname, 0)
        for fav in favs:
            fav.priority = int(fav.priority)

            if fav.name == me.name:
                _debug_('MATCH', 0)
                fav.priority = newprio
                _debug_('moved prio of %s: %s => %s' % (fav.name, oldprio, newprio), 0)
                continue
            if mod < 0:
                if fav.priority < newprio or fav.priority > oldprio:
                    _debug_('fp: %s, old: %s, new: %s' % (fav.priority, oldprio, newprio), 0)
                    _debug_('skipping: %s' % fav.name, 0)
                    continue
                fav.priority = fav.priority + 1
                _debug_('moved prio of %s: %s => %s' % (fav.name, fav.priority-1, fav.priority), 0)

            if mod > 0:
                if fav.priority > newprio or fav.priority < oldprio:
                    _debug_('skipping: %s' % fav.name, 0)
                    continue
                fav.priority = fav.priority - 1
                _debug_('moved prio of %s: %s => %s' % (fav.name, fav.priority+1, fav.priority), 0)

        sr.setFavoritesList(favs)
        self.saveScheduledRecordings(sr)

        return (TRUE, 'priorities adjusted')

    def getFavoriteObject(self, prog, favs=None):
        #more liberal favorite check that returns an object
        if not favs:
            (status, favs) = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                return (TRUE, fav)
        # if we get this far prog is not a favorite
        return (FALSE, 'not a favorite')

    def isProgAFavorite(self, prog, favs=None):
        if not favs:
            (status, favs) = self.getFavorites()

        lt = time.localtime(prog.start)
        dow = '%s' % lt[6]
        mod = '%s' % ((lt[3]*60)+(lt[4] / 30 * 30))
        mod = '%s' % ((lt[3]*60)+lt[4])

        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                if fav.channel == tv_util.get_chan_displayname(prog.channel_id) \
                or fav.channel == 'ANY':
                    if Unicode(fav.dow) == Unicode(dow) or Unicode(fav.dow) == u'ANY':
                        if Unicode(fav.mod) == Unicode(mod) \
                        or Unicode(fav.mod) == u'ANY':
                            return (TRUE, fav.name)

        # if we get this far prog is not a favorite
        return (FALSE, 'not a favorite')

    def doesFavoriteRecordOnlyNewEpisodes(self, prog, favs=None):
        if not favs:
            (status, favs) = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                _debug_('NEW: %s'%fav.onlyNew, 0)
                if fav.onlyNew == '1':
                    return TRUE

    def doesFavoriteAllowDuplicates(self, prog, favs=None):
        if not favs:
            (status, favs) = self.getFavorites()
        for fav in favs.values():
            if Unicode(prog.title).lower().find(Unicode(fav.title).lower()) >= 0:
                _debug_('DUP: %s'%fav.allowDuplicates, 0)
                if fav.allowDuplicates == '1':
                    return TRUE

    def removeFavoriteFromSchedule(self, fav):
        # TODO: make sure the program we remove is not
        #       covered by another favorite.

        tmp = {}
        tmp[fav.name] = fav

        scheduledRecordings = self.getScheduledRecordings()
        progs = scheduledRecordings.getProgramList()
        for prog in progs.values():
            (isFav, favorite) = self.isProgAFavorite(prog, tmp)
            if isFav:
                self.removeScheduledRecording(prog)

        return (TRUE, 'favorite unscheduled')


    def addFavoriteToSchedule(self, fav):
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

        return (TRUE, 'favorite scheduled')


    def updateFavoritesSchedule(self):
        #  TODO: do not re-add a prog to record if we have
        #        previously decided not to record it.

        global guide

        self.updateGuide()

        # First get the timeframe of the guide.
        last = 0
        for ch in guide.chan_list:
            for prog in ch.programs:
                if prog.start > last: last = prog.start

        scheduledRecordings = self.getScheduledRecordings()

        (status, favs) = self.getFavorites()

        if not len(favs):
            return (FALSE, 'there are no favorites to update')


        # Then remove all scheduled favorites in that timeframe to
        # make up for schedule changes.
        progs = scheduledRecordings.getProgramList()
        for prog in progs.values():

            # try:
            #     favorite = prog.isFavorite
            # except:
            #     favorite = FALSE

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

        return (TRUE, 'favorites schedule updated')


    #################################################################
    #  Start XML-RPC published methods.                             #
    #################################################################

    def xmlrpc_isPlayerRunning(self):
        (status, message) = (FALSE, 'RecordServer::isPlayerRunning: cannot acquire lock')
        self.lock.acquire()
        try:
            status = self.isPlayerRunning()
            message = status and 'player is running' or 'player is not running'
        finally:
            self.lock.release()
        return (status, message)

    def xmlrpc_isRecording(self):
        (status, message) = (FALSE, 'RecordServer::isRecording: cannot acquire lock')
        self.lock.acquire()
        try:
            status = self.isRecording()
            message = status and 'is recording' or 'is not recording'
        finally:
            self.lock.release()
        return (status, message)

    def xmlrpc_findNextProgram(self):
        (status, message) = (FALSE, 'RecordServer::findNextProgram: cannot acquire lock')
        self.lock.acquire()
        try:
            response = self.findNextProgram()
            status = response != None
            return (status, jellyToXML(response))
        finally:
            self.lock.release()
        return (status, message)

    def xmlrpc_getScheduledRecordings(self):
        (status, message) = (FALSE, 'RecordServer::getScheduledRecordings: cannot acquire lock')
        self.lock.acquire()
        try:
            return (TRUE, jellyToXML(self.getScheduledRecordings()))
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_saveScheduledRecordings(self, scheduledRecordings=None):
        (status, message) = (FALSE, 'RecordServer::saveScheduledRecordings: cannot acquire lock')
        self.lock.acquire()
        try:
            status = self.saveScheduledRecordings(scheduledRecordings)
            message = status and 'saveScheduledRecordings::success' or 'saveScheduledRecordings::failure'
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_scheduleRecording(self, prog=None):
        if not prog:
            return (FALSE, 'RecordServer::scheduleRecording:  no prog')

        (status, message) = (FALSE, 'RecordServer::scheduleRecording: cannot acquire lock')
        self.lock.acquire()
        try:
            prog = unjellyFromXML(prog)
            (status, response) = self.scheduleRecording(prog)
            message = 'RecordServer::scheduleRecording: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_removeScheduledRecording(self, prog=None):
        if not prog:
            return (FALSE, 'RecordServer::removeScheduledRecording:  no prog')

        (status, message) = (FALSE, 'RecordServer::removeScheduledRecording: cannot acquire lock')
        self.lock.acquire()
        try:
            prog = unjellyFromXML(prog)
            (status, response) = self.removeScheduledRecording(prog)
            message = 'RecordServer::removeScheduledRecording: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_isProgScheduled(self, prog=None, schedule=None):
        if not prog:
            return (FALSE, 'removeScheduledRecording::failure:  no prog')

        (status, message) = (FALSE, 'RecordServer::removeScheduledRecording: cannot acquire lock')
        self.lock.acquire()
        try:
            prog = unjellyFromXML(prog)
            if schedule:
                schedule = unjellyFromXML(schedule)
            (status, response) = self.isProgScheduled(prog, schedule)
            message = 'RecordServer::isProgScheduled: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_findProg(self, chan, start):
        (status, message) = (FALSE, 'RecordServer::findProg: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.findProg(chan, start)
            message = status and jellyToXML(response) or ('RecordServer::findProg: %s' % response)
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_findMatches(self, find, movies_only):
        (status, message) = (FALSE, 'RecordServer::findMatches: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.findMatches(find, movies_only)
            message = status and jellyToXML(response) or ('RecordServer::findMatches: %s' % response)
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_echotest(self, blah):
        (status, message) = (FALSE, 'RecordServer::echotest: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, message) = (TRUE, 'RecordServer::echotest: %s' % blah)
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_addFavorite(self, name, prog, exactchan=FALSE, exactdow=FALSE, exacttod=FALSE):
        (status, message) = (FALSE, 'RecordServer::addFavorite: cannot acquire lock')
        self.lock.acquire()
        try:
            prog = unjellyFromXML(prog)
            (status, response) = self.addFavorite(name, prog, exactchan, exactdow, exacttod)
            message = 'RecordServer::addFavorite: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_addEditedFavorite(self, name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
        (status, message) = (FALSE, 'RecordServer::addEditedFavorite: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.addEditedFavorite(unjellyFromXML(name), \
            unjellyFromXML(title), chan, dow, mod, priority, allowDuplicates, onlyNew)
            message = 'RecordServer::addEditedFavorite: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_removeFavorite(self, name=None):
        (status, message) = (FALSE, 'RecordServer::removeFavorite: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.removeFavorite(name)
            message = 'RecordServer::removeFavorite: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_clearFavorites(self):
        (status, message) = (FALSE, 'RecordServer::clearFavorites: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.clearFavorites()
            message = 'RecordServer::clearFavorites: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_getFavorites(self):
        (status, message) = (FALSE, 'RecordServer::getFavorites: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, message) = (TRUE, jellyToXML(self.getScheduledRecordings().getFavorites()))
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_getFavorite(self, name):
        (status, message) = (FALSE, 'RecordServer::getFavorite: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.getFavorite(name)
            message = status and jellyToXML(response) or 'RecordServer::getFavorite: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_adjustPriority(self, favname, mod=0):
        (status, message) = (FALSE, 'RecordServer::adjustPriority: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.adjustPriority(favname, mod)
            message = 'RecordServer::adjustPriority: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_isProgAFavorite(self, prog, favs=None):
        (status, message) = (FALSE, 'RecordServer::adjustPriority: cannot acquire lock')
        self.lock.acquire()
        try:
            prog = unjellyFromXML(prog)
            if favs:
                favs = unjellyFromXML(favs)
            (status, response) = self.isProgAFavorite(prog, favs)
            message = 'RecordServer::adjustPriority: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_removeFavoriteFromSchedule(self, fav):
        (status, message) = (FALSE, 'RecordServer::removeFavoriteFromSchedule: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.removeFavoriteFromSchedule(fav)
            message = 'RecordServer::removeFavoriteFromSchedule: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_addFavoriteToSchedule(self, fav):
        (status, message) = (FALSE, 'RecordServer::addFavoriteToSchedule: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.addFavoriteToSchedule(fav)
            message = 'RecordServer::addFavoriteToSchedule: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    def xmlrpc_updateFavoritesSchedule(self):
        (status, message) = (FALSE, 'updateFavoritesSchedule: cannot acquire lock')
        self.lock.acquire()
        try:
            (status, response) = self.updateFavoritesSchedule()
            message = 'RecordServer::updateFavoritesSchedule: %s' % response
        finally:
            self.lock.release()
        return (status, message)


    #################################################################
    #  End XML-RPC published methods.                               #
    #################################################################


    def create_fxd(self, rec_prog):
        from util.fxdimdb import FxdImdb, makeVideo
        fxd = FxdImdb()

        (filebase, fileext) = os.path.splitext(rec_prog.filename)
        fxd.setFxdFile(filebase, overwrite=TRUE)

        video = makeVideo('file', 'f1', os.path.basename(rec_prog.filename))
        fxd.setVideo(video)
        fxd.info['tagline'] = fxd.str2XML(rec_prog.sub_title)
        fxd.info['plot'] = fxd.str2XML(rec_prog.desc)
        fxd.info['runtime'] = None
        fxd.info['recording_timestamp'] = str(time.time())
        fxd.info['year'] = time.strftime('%m-%d ' + config.TV_TIMEFORMAT,
                                         time.localtime(rec_prog.start))
        fxd.title = rec_prog.title
        fxd.writeFxd()


    def startMinuteCheck(self):
        next_minute = (int(time.time()/60) * 60 + 60) - int(time.time())
        _debug_('top of the minute in %s seconds' % next_minute, 0)
        reactor.callLater(next_minute, self.minuteCheck)

    def minuteCheck(self):
        next_minute = (int(time.time()/60) * 60 + 60) - int(time.time())
        if next_minute != 60:
            # Compensate for timer drift
            _debug_('top of the minute in %s seconds' % next_minute, 0)
            reactor.callLater(next_minute, self.minuteCheck)
        else:
            reactor.callLater(60, self.minuteCheck)

        self.checkToRecord()


    def eventNotice(self):
        #print 'RECORDSERVER GOT EVENT NOTICE'
        # Use callLater so that handleEvents will get called the next time
        # through the main loop.
        reactor.callLater(0, self.handleEvents)


    def handleEvents(self):
        event = rc_object.get_event()

        if event:
            if event == OS_EVENT_POPEN2:
                pid = event.arg[1]
                _debug_('OS_EVENT_POPEN2 pid: %s' % pid, 0)
                event.arg[0].child = util.popen3.Popen3(event.arg[1])

            elif event == OS_EVENT_WAITPID:
                pid = event.arg[0]
                _debug_('waiting for pid %s' % (pid), 0)

                for i in range(20):
                    try:
                        wpid = os.waitpid(pid, os.WNOHANG)[0]
                    except OSError:
                        # forget it
                        continue
                    if wpid == pid:
                        _debug_('pid %s terminated' % (pid), 0)
                        break
                    time.sleep(0.1)
                else:
                    _debug_('pid %s still running' % (pid), 0)

            elif event == OS_EVENT_KILL:
                pid = event.arg[0]
                sig = event.arg[1]

                _debug_('killing pid %s with signal %s' % (pid, sig), 0)
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
                        _debug_('killed pid %s with signal %s' % (pid, sig), 0)
                        break
                    time.sleep(0.1)
                # We fall into this else from the for loop when break is not executed
                else:
                    _debug_('killing pid %s with signal 9' % (pid), 0)
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
                            _debug_('killed pid %s with signal 9' % (pid), 0)
                            break
                        time.sleep(0.1)
                    else:
                        _debug_('failed to kill pid %s' % (pid), 0)

            elif event == RECORD_START:
                prog = event.arg
                _debug_('RECORD_START %s' % (prog), 0)
                open(self.tv_lock_file, 'w').close()
                self.create_fxd(prog)
                if config.VCR_PRE_REC:
                    util.popen3.Popen3(config.VCR_PRE_REC)

            elif event == RECORD_STOP:
                prog = event.arg
                _debug_('RECORD_STOP %s' % (prog), 0)
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
                if config.REMOVE_COMMERCIALS:
                    (result, response) = connectionTest('connection test')
                    if result:
                        (status, idnr) = initCommDetectJob(prog.filename)
                        (status, output) = listJobs()
                        _debug_(output, 0)
                        (status, output) = queueIt(idnr, True)
                        _debug_(output, 0)
                    else:
                        _debug_('commdetect server not running', 0)
                # This is a really nasty hack but if it fixes the problem then great
                if self.delay_recording:
                    prog = self.delay_recording
                    #sr.setProgramList(progs)
                    #self.saveScheduledRecordings(sr)
                    prog.isRecording = TRUE
                    duration = int(prog.stop) - int(time.time())
                    prog.rec_duration = duration + config.TV_RECORD_PADDING_POST - 10
                    prog.filename = tv_util.getProgFilename(prog)
                    rec_prog = prog
                    _debug_('start delayed recording: %s' % rec_prog, 0)
                    self.record_app = plugin.getbyname('RECORD')
                    self.vg = self.fc.getVideoGroup(rec_prog.channel_id, FALSE)
                    suffix=self.vg.vdev.split('/')[-1]
                    self.record_app.Record(rec_prog)
                    self.delay_recording = None
                else:
                    os.remove(self.tv_lock_file)
            else:
                _debug_('%s not handled' % (event), 0)
                return
        else:
            # Should never happen
            _debug_('%s unknown' % (event), 0)


def main():
    app = Application("RecordServer")
    rs = RecordServer()
    if (DEBUG < 0):
        app.listenTCP(config.RECORDSERVER_PORT, server.Site(rs, logPath='/dev/null'))
    else:
        app.listenTCP(config.RECORDSERVER_PORT, server.Site(rs))
    rs.startMinuteCheck()
    rc_object.subscribe(rs.eventNotice)
    app.run(save=0)


if __name__ == '__main__':
    import traceback
    import time
    import glob

    locks = glob.glob(config.FREEVO_CACHEDIR + '/record.*')
    for f in locks:
        _debug_('Removed old record lock \"%s\"' % f, 0)
        os.remove(f)

    while 1:
        try:
            start = time.time()
            main()
            break
        except:
            traceback.print_exc()
            if start + 10 > time.time():
                _debug_('server problem, sleeping 1 min', 0)
                time.sleep(60)
