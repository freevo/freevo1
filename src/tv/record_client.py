# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A client interface to the Freevo recording server.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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


import sys
import time
import config
import socket, traceback, string
import xmlrpclib

import kaa
import kaa.rpc
import tv.epg_types
from util.marmalade import jellyToXML, unjellyFromXML

# Module variable that contains an initialized RecordClient() object
_singleton = None

def RecordClientSingleton():
    global _singleton

    # One-time init
    if _singleton == None:
        _singleton = RecordClient()

    return _singleton



class RecordClientException(Exception):
    """ RecordClientException """
    def __init__(self):
        pass


class RecordClient:
    """
    recordserver access class using kaa.rpc
    """
    def __init__(self):
        """ """
        _debug_('RecordClient.__init__()', 2)
        self.socket = (config.RECORDSERVER_IP, config.RECORDSERVER_PORT2)
        self.secret = config.RECORDSERVER_SECRET
        self.server = None


    def timeit(self, start=None):
        if start is None:
            return time.strftime("%H:%M:%S", time.localtime(time.time()))
        return '%.3f' % (time.time() - start)


    def recordserver_rpc(self, cmd, *args, **kwargs):
        """ call the record server command using kaa rpc """
        def closed_handler():
            self.server = None

        _debug_('recordserver_rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs), 2)
        try:
            if self.server is None:
                try:
                    self.server = kaa.rpc.Client(self.socket, self.secret)
                    self.server.signals['closed'].connect(closed_handler)
                    _debug_('%r is up' % (self.socket,), DINFO)
                except kaa.rpc.ConnectError, e:
                    _debug_('%r is down' % (self.socket,), DINFO)
                    self.server = None
                    return None
            return self.server.rpc(cmd, *args, **kwargs)
        except kaa.rpc.ConnectError, e:
            _debug_('%r is down' % (self.socket,), DINFO)
            self.server = None
            return None
        except IOError, e:
            _debug_('%r is down' % (self.socket,), DINFO)
            self.server = None
            return None


    #@kaa.coroutine()
    def pingCo(self):
        now = time.time()
        print self.timeit(now)+': pingCo started'
        inprogress = self.recordserver_rpc('ping')
        print self.timeit(now)+': pingCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': pingCo.inprogress=%r' % inprogress
        yield inprogress.get_result()
        print self.timeit(now)+': pingCo finished' # we never get here


    #@kaa.coroutine()
    def findNextProgramCo(self, isrecording=False):
        """ """
        now = time.time()
        print self.timeit(now)+': findNextProgramCo(isrecording=%r) started' % (isrecording,)
        inprogress = self.recordserver_rpc('findNextProgram', isrecording)
        print self.timeit(now)+': findNextProgramCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': findNextProgramCo.inprogress=%r' % inprogress
        yield inprogress.get_result()
        print self.timeit(now)+': findNextProgramCo finished'


    #@kaa.coroutine()
    def updateFavoritesScheduleCo(self):
        """ """
        now = time.time()
        print self.timeit(now)+': updateFavoritesScheduleCo started'
        inprogress = self.recordserver_rpc('updateFavoritesSchedule')
        print self.timeit(now)+': updateFavoritesScheduleCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': updateFavoritesScheduleCo.inprogress=%r' % inprogress
        yield inprogress.get_result()
        print self.timeit(now)+': updateFavoritesScheduleCo finished'


    #@kaa.coroutine()
    def getNextProgramStart(self):
        """ """
        now = time.time()
        print self.timeit(now)+': getNextProgramStart begin'
        inprogress = self.recordserver_rpc('updateFavoritesSchedule')
        print self.timeit(now)+': getNextProgramStart.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': getNextProgramStart.inprogress=%r' % inprogress
        #yield kaa.NotFinished
        print self.timeit(now)+': getNextProgramStart.NotFinished'
        yield inprogress.get_result()
        print self.timeit(now)+': getNextProgramStart.findNextProgram'
        inprogress = self.recordserver_rpc('findNextProgram')
        print self.timeit(now)+': getNextProgramStart.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': getNextProgramStart.inprogress=%r' % inprogress
        nextstart = inprogress.get_result()
        print self.timeit(now)+': getNextProgramStart.nextstart=%r' % nextstart


    def pingNow(self):
        """ Ping the recordserver to see if it is running """
        _debug_('pingNow', 2)
        inprogress = self.recordserver_rpc('ping')
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('pingNow.result=%r' % (result,), 2)
        return result


    def findNextProgramNow(self, isrecording=False):
        """ Find the next programme to record """
        _debug_('findNextProgramNow(isrecording=%r)' % (isrecording,), 2)
        inprogress = self.recordserver_rpc('findNextProgram', isrecording)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('findNextProgramNow.result=%r' % (result,), 2)
        return result


    def getScheduledRecordingsNow(self):
        """ get the scheduled recordings, returning the scheduled recordings object """
        _debug_('getScheduledRecordingsNow()', 2)
        inprogress = self.recordserver_rpc('getScheduledRecordings')
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('getScheduledRecordingsNow.result=%r' % (result,), 2)
        return result


    def updateFavoritesScheduleNow(self):
        """ Update the favorites scbedule, returning the object """
        _debug_('updateFavoritesScheduleNow()', 2)
        inprogress = self.recordserver_rpc('updateFavoritesSchedule')
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('updateFavoritesScheduleNow.result=%r' % (result,), 2)
        return result


    def findProgNow(self, chan=None, start=None):
        """ See if a programme is a favourite """
        _debug_('findProgNow(chan=%r, start=%r)' % (chan, start), 1)
        inprogress = self.recordserver_rpc('findProg', chan, start)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('findProgNow.result=%r' % (result,), 1)
        return result


    def findMatchesNow(self, title):
        """ See if a programme is a favourite """
        _debug_('findMatchesNow(title=%r)' % (title), 1)
        inprogress = self.recordserver_rpc('findMatches', title)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('findMatchesNow.result=%r' % (result,), 1)
        return result


    def isProgScheduledNow(self, prog, schedule=None):
        """ See if a programme is a schedule """
        _debug_('isProgScheduledNow(prog=%r, schedule=%r)' % (prog, schedule), 1)
        inprogress = self.recordserver_rpc('isProgScheduled', prog, schedule)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('isProgScheduledNow.result=%r' % (result,), 1)
        return result


    def isProgAFavoriteNow(self, prog, favs=None):
        """ See if a programme is a favourite """
        _debug_('isProgAFavoriteNow(prog=%r, favs=%r)' % (prog, favs), 1)
        inprogress = self.recordserver_rpc('isProgAFavorite', prog, favs)
        if inprogress is None:
            return (None, _('Recording server is not available'))
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('isProgAFavoriteNow.result=%r' % (result,), 1)
        return result


    def clearFavoritesNow(self):
        """ See if a programme is a favourite """
        _debug_('clearFavoritesNow()', 1)
        inprogress = self.recordserver_rpc('clearFavorites')
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('clearFavoritesNow.result=%r' % (result,), 1)
        return result


    def getFavoritesNow(self):
        """ See if a programme is a favourite """
        _debug_('getFavoritesNow()', 1)
        inprogress = self.recordserver_rpc('getFavorites')
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('getFavoritesNow.result=%r' % (result,), 1)
        return result


    def getFavoriteNow(self, name):
        """ See if a programme is a favourite """
        _debug_('getFavoriteNow(name=%r)' % (name), 1)
        inprogress = self.recordserver_rpc('getFavorite', name)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('getFavoriteNow.result=%r' % (result,), 1)
        return result


    def removeFavoriteNow(self, name):
        """ See if a programme is a favourite """
        _debug_('removeFavoriteNow(name=%r)' % (name), 1)
        inprogress = self.recordserver_rpc('removeFavorite', name)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('removeFavoriteNow.result=%r' % (result,), 1)
        return result


    def addEditedFavoriteNow(self, name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
        """ See if a programme is a favourite """
        _debug_('addEditedFavoriteNow(name=%r, title=%r, chan=%r, dow=%r, mod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)' % \
            (name, title, chan, dow, mod, priority, allowDuplicates, onlyNew), 1)
        inprogress = self.recordserver_rpc('addEditedFavorite', \
            name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)
        if inprogress is None:
            return (None, _('Recording server is not available'))
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('addEditedFavoriteNow.result=%r' % (result,), 1)
        return result


    def adjustPriorityNow(self, name, mod=0):
        """ See if a programme is a favourite """
        _debug_('adjustPriorityNow(name=%r, mod=%r)' % (name, mod), 1)
        inprogress = self.recordserver_rpc('adjustPriority', name, mod)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('adjustPriorityNow.result=%r' % (result,), 1)
        return result


    def getFavoriteObjectNow(self, prog):
        """ See if a programme is a favourite """
        _debug_('getFavoriteObjectNow(prog=%r)' % (prog), 1)
        inprogress = self.recordserver_rpc('getFavoriteObject', prog)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('getFavoriteObjectNow.result=%r' % (result,), 1)
        return result


    def scheduleRecordingNow(self, prog):
        """ See if a programme is a favourite """
        _debug_('scheduleRecordingNow(prog=%r)' % (prog,), 1)
        inprogress = self.recordserver_rpc('scheduleRecording', prog)
        if inprogress is None:
            return (None, _('Recording server is not available'))
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('scheduleRecordingNow.result=%r' % (result,), 1)
        return result


    def removeScheduledRecordingNow(self, prog):
        """ See if a programme is a favourite """
        _debug_('removeScheduledRecordingNow(prog=%r)' % (prog,), 1)
        inprogress = self.recordserver_rpc('removeScheduledRecording', prog)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('removeScheduledRecordingNow.result=%r' % (result,), 1)
        return result



    def server_rpc(self, cmd, callback, *args, **kwargs):
        """
        Call the server with the command the results will be put in the callback
        Try to reconnect if the connection is down
        """
        def closed_handler():
            self.server = None

        _debug_('server_rpc(cmd=%r, callback=%r, args=%r, kwargs=%r)' % (cmd, callback, args, kwargs), 2)
        try:
            if self.server is None:
                try:
                    self.server = kaa.rpc.Client(self.socket, self.secret)
                    self.server.signals['closed'].connect(closed_handler)
                    _debug_('%r is up' % (self.socket,), DINFO)
                except kaa.rpc.ConnectError, e:
                    _debug_('%r is down' % (self.socket,), DINFO)
                    self.server = None
                    return False
            self.server.rpc(cmd, *args, **kwargs).connect(callback)
            return True
        except kaa.rpc.ConnectError, e:
            _debug_('%r is down' % (self.socket,), DINFO)
            self.server = None
            return False
        except IOError, e:
            _debug_('%r is down' % (self.socket,), DINFO)
            self.server = None
            return False


    def ping(self, callback):
        """ See if the server is alive """
        _debug_('ping(callback=%r)' % (callback), 2)
        return self.server_rpc('ping', callback)


    def findNextProgram(self, callback, isrecording=False):
        """ Find the next program using a callback function """
        _debug_('findNextProgram(callback=%r, isrecording=%r)' % (callback, isrecording), 2)
        return self.server_rpc('findNextProgram', callback, isrecording)


    def getScheduledRecordings(self, callback):
        """ Get the scheduled recordings, using a callback function """
        _debug_('getScheduledRecordings(callback=%r)' % (callback), 2)
        return self.server_rpc('getScheduledRecordings', callback)


    def scheduleRecording(self, callback, prog):
        """ schedule a programme for recording, using a callback function """
        _debug_('scheduleRecording(callback=%r, prog=%r)' % (callback, prog), 2)
        return self.server_rpc('scheduleRecording', callback, prog)


    def updateFavoritesSchedule(self, callback):
        """ Update the favourites using a callback function """
        _debug_('updateFavoritesSchedule(callback=%r)' % (callback), 2)
        return self.server_rpc('updateFavoritesSchedule', callback)


    def isPlayerRunning(self, callback):
        """ Find out if a player is running, using a callback function """
        _debug_('isPlayerRunning(callback=%r)' % (callback), 2)
        return self.server_rpc('isPlayerRunning', callback)


    def getFavorites(self, callback):
        """ Get favourites """
        _debug_('getFavorites(callback=%r)' % (callback), 2)
        return self.server_rpc('getFavorites', callback)


    def isProgAFavorite(self, callback, prog, favs=None):
        """ See if a programme is a favourite """
        _debug_('isProgAFavorite(callback=%r, prog=%r, favs=%r)' % (callback, prog, favs), 2)
        return self.server_rpc('isProgAFavorite', callback, prog, favs)


if __name__ == '__main__':
    config.DEBUG = 2

    def shutdown(message, now):
        print "shutdown.message=%r after %.3f secs" % (message, time.time()-now)
        raise SystemExit

    def handler(result):
        """ A callback handler for test functions """
        _debug_('handler(result=%r)' % (result,), 2)
        print 'handler.result=%r\n"%s"' % (result, result)
        raise SystemExit

    rc = RecordClientSingleton()

    if len(sys.argv) >= 2:
        function = sys.argv[1].lower()
        args = sys.argv[2:]
    else:
        function = 'none'

    start = time.time()
    print 'function=%r args=%r' % (function, args)

    #--------------------------------------------------------------------------------
    # kaa.rpc coroutine tests
    #--------------------------------------------------------------------------------

    if function == "pingco":
        result = rc.pingCo().wait()
        print 'pingCo=%r\n"%s"' % (result, result)

    if function == "findnextprogramco":
        result = rc.findNextProgramCo().wait()
        print 'findNextProgramCo=%r\n"%s"' % (result, result)

    if function == "updatefavoritesscheduleco":
        result = rc.updateFavoritesScheduleCo().wait()
        print 'updateFavoritesScheduleCo=%r' % (result,)

    if function == "getnextprogramstart":
        result = rc.getNextProgramStart().wait()
        print 'getNextProgramStart=%r' % (result,)

    #--------------------------------------------------------------------------------
    # kaa.rpc callback tests
    #--------------------------------------------------------------------------------

    if function == "pingnow":
        result = rc.pingNow()
        print 'result: %r\n"%s"' % (result, result)

    elif function == "findnextprogramnow":
        result = rc.findNextProgramNow(True)
        print 'recording:%r\n"%s"' % (result, result)
        result = rc.findNextProgramNow(False)
        print 'next     :%r\n"%s"' % (result, result)

    elif function == "findnextprogram":
        rc.findNextProgram(handler)

    elif function == "findnextprogramrecording":
        rc.findNextProgram(handler, True)

    elif function == "getscheduledrecordingsnow":
        result = rc.getScheduledRecordingsNow()
        print 'result: %r\n"%s"' % (result, result)

    elif function == "getscheduledrecordings":
        rc.getScheduledRecordings(handler)

    elif function == "updatefavoritesschedulenow":
        result = rc.updateFavoritesScheduleNow()
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "findprognow":
        result = rc.findProgNow(args)
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "findmatchesnow":
        result = rc.findMatchesNow(args)
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "getfavoritesnow":
        result = rc.getFavoritesNow()
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "getfavoritenow":
        result = rc.getFavoriteNow(args)
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "removefavoritenow":
        result = rc.removeFavoriteNow()
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "adjustprioritynow":
        result = rc.adjustPriorityNow(args)
        print '%s: result: %r' % (rc.timeit(start), result)

    elif function == "updatefavoritesschedule":
        rc.updateFavoritesSchedule(handler)

    elif function == "getfavorites":
        rc.getFavorites(handler)

    #FIXME the following two calls need fixing
    elif function == "moviesearch":
        if len(sys.argv) >= 3:
            find = Unicode(sys.argv[2])

            (result, response) = findMatches(find, 0)
            if result:
                for prog in response:
                    _debug_('Prog: %s' % prog.title)
            else:
                _debug_('result: %s, response: %s ' % (result, response))
        else:
            print 'no data'


    elif function == "addfavorite":
        if len(sys.argv) >= 3:
            name=Unicode(string.join(sys.argv[2:]))
            title=name
            channel="ANY"
            dow="ANY"
            mod="ANY"
            priority=0
            allowDuplicates=False
            onlyNew=True

            (result, msg) = addEditedFavorite(name,title,channel,dow,mod,priority,allowDuplicates,onlyNew)
            if not result:
                # it is important to show the user this error,
                # because that means the favorite is removed,
                # and must be created again
                _debug_('Save Failed, favorite was lost: %s' % (msg), DWARNING)
            else:
                _debug_('Ok!')
                (result, response) = updateFavoritesSchedule()
                _debug_('%r' % response)
        else:
            print 'no data'

    else:
        print '%r not found' % (function)

    kaa.notifier.OneShotTimer(shutdown, 'bye', time.time()).start(20)
    kaa.main.run()
