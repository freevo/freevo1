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

# Module variable that contains an initialized RecordClientActions() object
_singleton = None

def RecordClient():
    global _singleton

    # One-time init
    if _singleton is None:
        _singleton = RecordClientActions()

    return _singleton



class RecordClientException(Exception):
    """ RecordClientException """
    def __init__(self):
        pass


class RecordClientActions:
    """
    recordserver access class using kaa.rpc
    """
    recordserverdown = _('TV record server is not available')

    def __init__(self):
        """ """
        _debug_('RecordClient.__init__()', 2)
        socket = (config.RECORDSERVER_IP, config.RECORDSERVER_PORT)
        self.channel = kaa.rpc.connect(socket, config.RECORDSERVER_SECRET, retry=1)
        #kaa.inprogress(self.channel).wait()


    def timeit(self, start=None):
        if start is None:
            return time.strftime("%H:%M:%S", time.localtime(time.time()))
        return '%.3f' % (time.time() - start)


    #--------------------------------------------------------------------------------
    # record server calls using a coroutine and the wait method
    #--------------------------------------------------------------------------------

    def _recordserver_rpc(self, cmd, *args, **kwargs):
        """ call the record server command using kaa rpc """
        _debug_('_recordserver_rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs), 2)
        if self.channel.status != kaa.rpc.CONNECTED:
            _debug_('record server is down', DINFO)
            return None
        return self.channel.rpc(cmd, *args, **kwargs)


    @kaa.coroutine()
    def pingCo(self):
        now = time.time()
        print self.timeit(now)+': pingCo started'
        inprogress = self._recordserver_rpc('ping')
        print self.timeit(now)+': pingCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': pingCo finished=%r' % (inprogress.result,)
        yield inprogress.result


    @kaa.coroutine()
    def findNextProgramCo(self, isrecording=False):
        """ """
        now = time.time()
        print self.timeit(now)+': findNextProgramCo(isrecording=%r) started' % (isrecording,)
        inprogress = self._recordserver_rpc('findNextProgram', isrecording)
        print self.timeit(now)+': findNextProgramCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': findNextProgramCo finished=%r' % (inprogress.result,)
        yield inprogress.result


    @kaa.coroutine()
    def getScheduledRecordingsCo(self):
        """ """
        now = time.time()
        print self.timeit(now)+': getScheduledRecordingsCo() started'
        inprogress = self._recordserver_rpc('getScheduledRecordings')
        print self.timeit(now)+': getScheduledRecordingsCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': getScheduledRecordingsCo finished=%r' % (inprogress.result,)
        yield inprogress.result


    @kaa.coroutine()
    def getFavoritesCo(self):
        """ """
        now = time.time()
        print self.timeit(now)+': getFavoritesCo() started'
        inprogress = self._recordserver_rpc('getFavorites')
        print self.timeit(now)+': getFavoritesCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': getFavoritesCo finished=%r' % (inprogress.result,)
        yield inprogress.result


    @kaa.coroutine()
    def updateFavoritesScheduleCo(self):
        """ """
        now = time.time()
        print self.timeit(now)+': updateFavoritesScheduleCo started'
        inprogress = self._recordserver_rpc('updateFavoritesSchedule')
        print self.timeit(now)+': updateFavoritesScheduleCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': updateFavoritesScheduleCo finished=%r' % (inprogress.result,)
        yield inprogress.result


    @kaa.coroutine()
    def getNextProgramStartCo(self):
        """
        Get the next program using coroutines and yield the result.
        This will be a slow call as the updateFavoritesSchedule can take a time
        """
        now = time.time()
        print self.timeit(now)+': getNextProgramStartCo started'
        inprogress = self._recordserver_rpc('updateFavoritesSchedule')
        yield inprogress
        print self.timeit(now)+': updateFavoritesSchedule.result=%r' % (inprogress.result,)
        inprogress = self._recordserver_rpc('findNextProgram')
        yield inprogress
        print self.timeit(now)+': findNextProgram.result=%r' % (inprogress.result,)
        print self.timeit(now)+': getNextProgramStartCo finished=%r' % (inprogress.result,)
        yield inprogress.result


    def pingNow(self):
        """ Ping the recordserver to see if it is running """
        _debug_('pingNow', 2)
        inprogress = self._recordserver_rpc('ping')
        if inprogress is None:
            return False
        inprogress.wait()
        result = inprogress.result
        _debug_('pingNow.result=%r' % (result,), 2)
        return result


    def findNextProgramNow(self, isrecording=False):
        """ Find the next programme to record """
        _debug_('findNextProgramNow(isrecording=%r)' % (isrecording,), 2)
        inprogress = self._recordserver_rpc('findNextProgram', isrecording)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.result
        _debug_('findNextProgramNow.result=%r' % (result,), 2)
        return result


    def getScheduledRecordingsNow(self):
        """ get the scheduled recordings, returning the scheduled recordings object """
        _debug_('getScheduledRecordingsNow()', 2)
        inprogress = self._recordserver_rpc('getScheduledRecordings')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('getScheduledRecordingsNow.result=%r' % (result,), 2)
        return (True, result)


    def updateFavoritesScheduleNow(self):
        """ Update the favorites scbedule, returning the object """
        _debug_('updateFavoritesScheduleNow()', 2)
        inprogress = self._recordserver_rpc('updateFavoritesSchedule')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('updateFavoritesScheduleNow.result=%r' % (result,), 2)
        return result


    def findProgNow(self, chan=None, start=None):
        """ See if a programme is a favourite """
        _debug_('findProgNow(chan=%r, start=%r)' % (chan, start), 2)
        inprogress = self._recordserver_rpc('findProg', chan, start)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('findProgNow.result=%r' % (result,), 2)
        return result


    def findMatchesNow(self, title=None, movies_only=False):
        """ See if a programme is a favourite """
        _debug_('findMatchesNow(title=%r, movies_only=%r)' % (title, movies_only), 2)
        inprogress = self._recordserver_rpc('findMatches', title, movies_only)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('findMatchesNow.result=%r' % (result,), 2)
        return result


    def isProgScheduledNow(self, prog, schedule=None):
        """ See if a programme is a schedule """
        _debug_('isProgScheduledNow(prog=%r, schedule=%r)' % (prog, schedule), 2)
        inprogress = self._recordserver_rpc('isProgScheduled', prog, schedule)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('isProgScheduledNow.result=%r' % (result,), 2)
        return result


    def isProgAFavoriteNow(self, prog, favs=None):
        """ See if a programme is a favourite """
        _debug_('isProgAFavoriteNow(prog=%r, favs=%r)' % (prog, favs), 2)
        inprogress = self._recordserver_rpc('isProgAFavorite', prog, favs)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('isProgAFavoriteNow.result=%r' % (result,), 2)
        return result


    def clearFavoritesNow(self):
        """ See if a programme is a favourite """
        _debug_('clearFavoritesNow()', 2)
        inprogress = self._recordserver_rpc('clearFavorites')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('clearFavoritesNow.result=%r' % (result,), 2)
        return result


    def getFavoritesNow(self):
        """ See if a programme is a favourite """
        _debug_('getFavoritesNow()', 2)
        inprogress = self._recordserver_rpc('getFavorites')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('getFavoritesNow.result=%r' % (result,), 2)
        return (True, result)


    def getFavoriteNow(self, name):
        """ See if a programme is a favourite """
        _debug_('getFavoriteNow(name=%r)' % (name), 2)
        inprogress = self._recordserver_rpc('getFavorite', name)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('getFavoriteNow.result=%r' % (result,), 2)
        return result


    def removeFavoriteNow(self, name):
        """ See if a programme is a favourite """
        _debug_('removeFavoriteNow(name=%r)' % (name), 2)
        inprogress = self._recordserver_rpc('removeFavorite', name)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('removeFavoriteNow.result=%r' % (result,), 2)
        return result


    def addEditedFavoriteNow(self, name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
        """ See if a programme is a favourite """
        _debug_('addEditedFavoriteNow('+ \
            'name=%r, title=%r, chan=%r, dow=%r, mod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)' % \
            (name, title, chan, dow, mod, priority, allowDuplicates, onlyNew), 1)
        inprogress = self._recordserver_rpc('addEditedFavorite', \
            name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('addEditedFavoriteNow.result=%r' % (result,), 2)
        return result


    def adjustPriorityNow(self, name, mod=0):
        """ See if a programme is a favourite """
        _debug_('adjustPriorityNow(name=%r, mod=%r)' % (name, mod), 2)
        inprogress = self._recordserver_rpc('adjustPriority', name, mod)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('adjustPriorityNow.result=%r' % (result,), 2)
        return result


    def getFavoriteObjectNow(self, prog):
        """ See if a programme is a favourite """
        _debug_('getFavoriteObjectNow(prog=%r)' % (prog), 2)
        inprogress = self._recordserver_rpc('getFavoriteObject', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('getFavoriteObjectNow.result=%r' % (result,), 2)
        return result


    def scheduleRecordingNow(self, prog):
        """ See if a programme is a favourite """
        _debug_('scheduleRecordingNow(prog=%r)' % (prog,), 2)
        inprogress = self._recordserver_rpc('scheduleRecording', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('scheduleRecordingNow.result=%r' % (result,), 2)
        return result


    def removeScheduledRecordingNow(self, prog):
        """ See if a programme is a favourite """
        _debug_('removeScheduledRecordingNow(prog=%r)' % (prog,), 2)
        inprogress = self._recordserver_rpc('removeScheduledRecording', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('removeScheduledRecordingNow.result=%r' % (result,), 2)
        return result


    #--------------------------------------------------------------------------------
    # record server calls using a callback
    #--------------------------------------------------------------------------------

    def _server_rpc(self, cmd, callback, *args, **kwargs):
        """
        Call the server with the command the results will be put in the callback
        Try to reconnect if the connection is down
        """
        _debug_('_recordserver_rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs), 2)
        if self.channel.status != kaa.rpc.CONNECTED:
            _debug_('record server is down', DINFO)
            return False
        self.channel.rpc(cmd, *args, **kwargs).connect(callback)
        return True


    def ping(self, callback):
        """ See if the server is alive """
        _debug_('ping(callback=%r)' % (callback), 2)
        return self._server_rpc('ping', callback)


    def findNextProgram(self, callback, isrecording=False):
        """ Find the next program using a callback function """
        _debug_('findNextProgram(callback=%r, isrecording=%r)' % (callback, isrecording), 2)
        return self._server_rpc('findNextProgram', callback, isrecording)


    def getScheduledRecordings(self, callback):
        """ Get the scheduled recordings, using a callback function """
        _debug_('getScheduledRecordings(callback=%r)' % (callback), 2)
        return self._server_rpc('getScheduledRecordings', callback)


    def scheduleRecording(self, callback, prog):
        """ schedule a programme for recording, using a callback function """
        _debug_('scheduleRecording(callback=%r, prog=%r)' % (callback, prog), 2)
        return self._server_rpc('scheduleRecording', callback, prog)


    def updateFavoritesSchedule(self, callback):
        """ Update the favourites using a callback function """
        _debug_('updateFavoritesSchedule(callback=%r)' % (callback), 2)
        return self._server_rpc('updateFavoritesSchedule', callback)


    def isPlayerRunning(self, callback):
        """ Find out if a player is running, using a callback function """
        _debug_('isPlayerRunning(callback=%r)' % (callback), 2)
        return self._server_rpc('isPlayerRunning', callback)


    def getFavorites(self, callback):
        """ Get favourites """
        _debug_('getFavorites(callback=%r)' % (callback), 2)
        return self._server_rpc('getFavorites', callback)


    def isProgAFavorite(self, callback, prog, favs=None):
        """ See if a programme is a favourite """
        _debug_('isProgAFavorite(callback=%r, prog=%r, favs=%r)' % (callback, prog, favs), 2)
        return self._server_rpc('isProgAFavorite', callback, prog, favs)


if __name__ == '__main__':
    config.DEBUG = 2

    def shutdown(message, now):
        print 'shutdown(message, now)'
        print "shutdown.message=%r after %.3f secs" % (message, time.time()-now)
        raise SystemExit

    def handler(result):
        print 'handler(result)'
        """ A callback handler for test functions """
        _debug_('handler(result=%r)' % (result,), 2)
        print '%s: handler.result=%r' % (rc.timeit(start), result)
        raise SystemExit

    rc = RecordClient()
    try:
        kaa.inprogress(rc.channel).wait()
    except Exception, why:
        print 'Cannot connect to record server'
        raise SystemExit

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
        print '%s: pingCo=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "findnextprogramco":
        result = rc.findNextProgramCo().wait()
        print '%s: findNextProgramCo=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "getscheduledrecordingsco":
        result = rc.getScheduledRecordingsCo().wait()
        print '%s: getScheduledRecordingsCo=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "getfavoritesco":
        result = rc.getFavoritesCo().wait()
        print '%s: getFavoritesCo=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "updatefavoritesscheduleco":
        result = rc.updateFavoritesScheduleCo().wait()
        print '%s: updateFavoritesScheduleCo=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "getnextprogramstartco":
        result = rc.getNextProgramStartCo().wait()
        print '%s: getNextProgramStartCo=%r' % (rc.timeit(start), result)
        raise SystemExit

    #--------------------------------------------------------------------------------
    # kaa.rpc callback tests
    #--------------------------------------------------------------------------------

    elif function == "ping":
        result = rc.ping(handler)
        if not result:
            print '%s: result=%r' % (rc.timeit(start), result)
            raise SystemExit

    elif function == "findnextprogram":
        result = rc.findNextProgram(handler)
        if not result:
            print '%s: result=%r' % (rc.timeit(start), result)
            raise SystemExit

    elif function == "getscheduledrecordings":
        result = rc.getScheduledRecordings(handler)
        if not result:
            print '%s: result=%r' % (rc.timeit(start), result)
            raise SystemExit

    elif function == "getfavorites":
        result = rc.getFavorites(handler)
        if not result:
            print '%s: result=%r' % (rc.timeit(start), result)
            raise SystemExit

    #--------------------------------------------------------------------------------
    # kaa.rpc wait on in-progress tests
    #--------------------------------------------------------------------------------

    elif function == "pingnow":
        result = rc.pingNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "findnextprogramnow":
        result = rc.findNextProgramNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "getscheduledrecordingsnow":
        result = rc.getScheduledRecordingsNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        if config.DEBUG > 2:
            status, schedule = result
            if status:
                print '%s: result=%r' % (schedule.__dict__, result)
            else:
                print 'result=%r' % (result,)
        raise SystemExit

    elif function == "updatefavoritesschedulenow":
        result = rc.updateFavoritesScheduleNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "findnextprogramhandler":
        def findNextProgramHandler(result):
            print 'findNextProgramHandler: %r' % (result,)
            raise SystemExit
        result = rc.findNextProgram(findNextProgramHandler, isrecording=True)
        print '%s: result=%r' % (rc.timeit(start), result)

    elif function == "findprognow":
        result = rc.findProgNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "findmatchesnow":
        result = rc.findMatchesNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "getfavoritesnow":
        result = rc.getFavoritesNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "getfavoritenow":
        result = rc.getFavoriteNow(args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "removefavoritenow":
        result = rc.removeFavoriteNow(*args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "adjustprioritynow":
        result = rc.adjustPriorityNow(args)
        print '%s: result=%r' % (rc.timeit(start), result)
        raise SystemExit

    elif function == "updatefavoritesschedule":
        result = rc.updateFavoritesSchedule(handler)
        if not result:
            print '%s: result=%r' % (rc.timeit(start), result)
            raise SystemExit

    #FIXME the following two calls need fixing
    elif function == "moviesearch":
        if len(sys.argv) >= 3:
            find = Unicode(sys.argv[2])

            (result, response) = findMatches(find, 0)
            if result:
                for prog in response:
                    _debug_('Prog: %s' % prog.title)
            else:
                _debug_('result=%s, response: %s ' % (result, response))
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
        print 'function %r not found' % (function)
        raise SystemExit

    kaa.OneShotTimer(shutdown, 'bye', time.time()).start(20)
    kaa.main.run()
