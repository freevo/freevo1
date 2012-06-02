# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A client interface to the Freevo recording server.
# -----------------------------------------------------------------------
# $Id: record_client.py 11917 2012-03-10 09:10:50Z adam $
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
import logging
logger = logging.getLogger("freevo.tv.record_client")


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


class RecordClientActions:
    """
    recordserver access class using kaa.rpc
    """
    recordserverdown = _('TV record server is not available')

    def __init__(self):
        """ """
        logger.log( 9, 'RecordClient.__init__()')
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
        logger.log( 9, '_recordserver_rpc(cmd=%r, args=%r, kwargs=%r)', cmd, args, kwargs)
        if self.channel.status != kaa.rpc.CONNECTED:
            logger.info('record server is down')
            return None
        return self.channel.rpc(cmd, *args, **kwargs)


    def pingNow(self):
        """ Ping the recordserver to see if it is running """
        logger.log( 9, 'pingNow')
        inprogress = self._recordserver_rpc('ping')
        if inprogress is None:
            return False
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'pingNow.result=%r', result)
        return result


    def findNextProgramNow(self, isrecording=False):
        """ Find the next programme to record """
        logger.log( 9, 'findNextProgramNow(isrecording=%r)', isrecording)
        inprogress = self._recordserver_rpc('findNextProgram', isrecording)
        if inprogress is None:
            return None
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'findNextProgramNow.result=%r', result)
        return result


    def getScheduledRecordingsNow(self):
        """ get the scheduled recordings, returning the scheduled recordings object """
        logger.log( 9, 'getScheduledRecordingsNow()')
        inprogress = self._recordserver_rpc('getScheduledRecordings')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'getScheduledRecordingsNow.result=%r', result)
        return (True, result)


    def updateFavoritesScheduleNow(self):
        """ Update the favorites scbedule, returning the object """
        logger.log( 9, 'updateFavoritesScheduleNow()')
        inprogress = self._recordserver_rpc('updateFavoritesSchedule')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'updateFavoritesScheduleNow.result=%r', result)
        return result


    def findProgNow(self, chan=None, start=None):
        """ See if a programme is a favourite """
        logger.log( 9, 'findProgNow(chan=%r, start=%r)', chan, start)
        inprogress = self._recordserver_rpc('findProg', chan, start)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'findProgNow.result=%r', result)
        return result


    def findMatchesNow(self, title=None, movies_only=False):
        """ See if a programme is a favourite """
        logger.log( 9, 'findMatchesNow(title=%r, movies_only=%r)', title, movies_only)
        inprogress = self._recordserver_rpc('findMatches', title, movies_only)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'findMatchesNow.result=%r', result)
        return result


    def isProgScheduledNow(self, prog):
        """ See if a programme is a schedule """
        logger.log( 9, 'isProgScheduledNow(prog=%r, schedule=%r)', prog)
        inprogress = self._recordserver_rpc('isProgScheduled', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'isProgScheduledNow.result=%r', result)
        return result


    def isProgAFavoriteNow(self, prog, favs=None):
        """ See if a programme is a favourite """
        logger.log( 9, 'isProgAFavoriteNow(prog=%r, favs=%r)', prog, favs)
        inprogress = self._recordserver_rpc('isProgAFavorite', prog, favs)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'isProgAFavoriteNow.result=%r', result)
        return result


    def getFavoritesNow(self):
        """ See if a programme is a favourite """
        logger.log( 9, 'getFavoritesNow()')
        inprogress = self._recordserver_rpc('getFavorites')
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'getFavoritesNow.result=%r', result)
        return (True, result)


    def getFavoriteNow(self, name):
        """ See if a programme is a favourite """
        logger.log( 9, 'getFavoriteNow(name=%r)', name)
        inprogress = self._recordserver_rpc('getFavorite', name)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'getFavoriteNow.result=%r', result)
        return result


    def removeFavoriteNow(self, name):
        """ See if a programme is a favourite """
        logger.log( 9, 'removeFavoriteNow(name=%r)', name)
        inprogress = self._recordserver_rpc('removeFavorite', name)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'removeFavoriteNow.result=%r', result)
        return result


    def addEditedFavoriteNow(self, name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
        """ See if a programme is a favourite """
        logger.debug('addEditedFavoriteNow(' + 'name=%r, title=%r, chan=%r, dow=%r, mod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)', name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)


        inprogress = self._recordserver_rpc('addEditedFavorite', \
            name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'addEditedFavoriteNow.result=%r', result)
        return result


    def adjustPriorityNow(self, name, mod=0):
        """ See if a programme is a favourite """
        logger.log( 9, 'adjustPriorityNow(name=%r, mod=%r)', name, mod)
        inprogress = self._recordserver_rpc('adjustPriority', name, mod)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'adjustPriorityNow.result=%r', result)
        return result


    def getFavoriteObjectNow(self, prog):
        """ See if a programme is a favourite """
        logger.log( 9, 'getFavoriteObjectNow(prog=%r)', prog)
        inprogress = self._recordserver_rpc('getFavoriteObject', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'getFavoriteObjectNow.result=%r', result)
        return result


    def scheduleRecordingNow(self, prog):
        """ See if a programme is a favourite """
        logger.log( 9, 'scheduleRecordingNow(prog=%r)', prog)
        inprogress = self._recordserver_rpc('scheduleRecording', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'scheduleRecordingNow.result=%r', result)
        return result


    def removeScheduledRecordingNow(self, prog):
        """ See if a programme is a favourite """
        logger.log( 9, 'removeScheduledRecordingNow(prog=%r)', prog)
        inprogress = self._recordserver_rpc('removeScheduledRecording', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'removeScheduledRecordingNow.result=%r', result)
        return result

    def getConflicts(self, prog):
        """ Retrieve the programs that conflict with the specified prog """
        logger.log( 9, 'getConflicts(prog=%r)', prog)
        inprogress = self._recordserver_rpc('getConflicts', prog)
        if inprogress is None:
            return (None, self.recordserverdown)
        inprogress.wait()
        result = inprogress.result
        logger.log( 9, 'getConflicts.result=%r', result)
        return result

    #--------------------------------------------------------------------------------
    # record server calls using a callback
    #--------------------------------------------------------------------------------

    def _server_rpc(self, cmd, callback, *args, **kwargs):
        """
        Call the server with the command the results will be put in the callback
        Try to reconnect if the connection is down
        """
        logger.log( 9, '_recordserver_rpc(cmd=%r, args=%r, kwargs=%r)', cmd, args, kwargs)
        if self.channel.status != kaa.rpc.CONNECTED:
            logger.info('record server is down')
            return False
        self.channel.rpc(cmd, *args, **kwargs).connect(callback)
        return True


    def findNextProgram(self, callback, isrecording=False):
        """ Find the next program using a callback function """
        logger.log( 9, 'findNextProgram(callback=%r, isrecording=%r)', callback, isrecording)
        return self._server_rpc('findNextProgram', callback, isrecording)


    def scheduleRecording(self, callback, prog):
        """ schedule a programme for recording, using a callback function """
        logger.log( 9, 'scheduleRecording(callback=%r, prog=%r)', callback, prog)
        return self._server_rpc('scheduleRecording', callback, prog)


    def updateFavoritesSchedule(self, callback):
        """ Update the favourites using a callback function """
        logger.log( 9, 'updateFavoritesSchedule(callback=%r)', callback)
        return self._server_rpc('updateFavoritesSchedule', callback)

if __name__ == '__main__':
    config.DEBUG = 2

    def shutdown(message, now):
        print 'shutdown(message, now)'
        print "shutdown.message=%r after %.3f secs" % (message, time.time()-now)
        raise SystemExit

    def handler(result):
        print 'handler(result)'
        """ A callback handler for test functions """
        logger.log( 9, 'handler(result=%r)', result)
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
                    logger.debug('Prog: %s', prog.title)
            else:
                logger.debug('result=%s, response: %s ', result, response)
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
                logger.warning('Save Failed, favorite was lost: %s', msg)
            else:
                logger.debug('Ok!')
                (result, response) = updateFavoritesSchedule()
                logger.debug('%r', response)
        else:
            print 'no data'

    else:
        print 'function %r not found' % (function)
        raise SystemExit

    kaa.OneShotTimer(shutdown, 'bye', time.time()).start(20)
    kaa.main.run()
