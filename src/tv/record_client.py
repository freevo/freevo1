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

import kaa
import kaa.rpc
import time, sys, socket, traceback, string
import xmlrpclib
import tv.epg_types

from util.marmalade import jellyToXML, unjellyFromXML

TRUE  = 1
FALSE = 0

xml_rpc_server = 'http://%s:%s/' % (config.RECORDSERVER_IP, config.RECORDSERVER_PORT)
server = xmlrpclib.Server(xml_rpc_server, allow_none=1)


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
            return time.strftime("%M:%S", time.localtime(time.time()))
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


    @kaa.coroutine()
    def pingCo(self):
        now = time.time()
        print self.timeit(now)+': pingCo started'
        inprogress = self.recordserver_rpc('ping')
        print self.timeit(now)+': pingCo.inprogress=%r' % inprogress
        yield inprogress
        print self.timeit(now)+': pingCo.inprogress=%r' % inprogress
        yield inprogress.get_result()
        print self.timeit(now)+': pingCo finished' # we never get here


    @kaa.coroutine()
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


    @kaa.coroutine()
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


    @kaa.coroutine()
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
            return None
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
            return None
        inprogress.wait()
        result = inprogress.get_result()
        _debug_('addEditedFavoriteNow.result=%r' % (result,), 1)
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
            return None
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


    def updateFavoritesSchedule(self, callback):
        """ Update the favourites using a callback function """
        print 'updateFavoritesSchedule(callback=%r)' % (callback)
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


#================================================================================
# Deprecated Twisted calls
#================================================================================

def returnFromJelly(status, response):
    """ Unjelly the xml from the response """
    _debug_('returnFromJelly(status=%r, response=%r)' % (status, response), 2)
    if status:
        return (status, unjellyFromXML(response))
    return (status, response)


def connectionTest(teststr='testing'):
    """ Using Twisted check if the record server is running """
    _debug_('connectionTest(teststr=%r)' % (teststr), 2)
    try:
        (status, message) = server.echotest(teststr)
    except Exception, e:
        _debug_('%s' % e)
        traceback.print_exc()
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def getScheduledRecordings():
    """ Using Twisted get the scheduled recordings """
    _debug_('getScheduledRecordings()', 2)
    try:
        (status, message) = server.getScheduledRecordings()
    except Exception, e:
        _debug_('%s' % e)
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, message)


def saveScheduledRecordings(scheduledRecordings):
    """ Using Twisted save the scheduled recordings """
    _debug_('saveScheduledRecordings(scheduledRecordings)', 2)
    try:
        (status, message) = server.saveScheduledRecordings(scheduledRecordings)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def scheduleRecording(prog=None):
    """ Using Twisted add a programme to recording schedule  """
    _debug_('scheduleRecording(prog=%r)' % (prog), 2)
    if not prog:
        return (FALSE, _('no program'))

    if prog.stop < time.time():
        return (FALSE, _('ERROR')+': '+_('cannot record it if it is over'))

    try:
        (status, message) = server.scheduleRecording(jellyToXML(prog))
    except:
        traceback.print_exc()
        return (FALSE, 'record_client: '+_('connection error'))

    return (status, message)


def removeScheduledRecording(prog=None):
    """ Using Twisted remove a programme from the recording schedule """
    _debug_('removeScheduledRecording(prog=%r)' % (prog), 2)
    if not prog:
        return (FLASE, _('no program'))

    try:
        (status, message) = server.removeScheduledRecording(jellyToXML(prog))
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def cleanScheduledRecordings():
    """ Using Twisted clean the recordings schedule """
    _debug_('cleanScheduledRecordings()', 2)
    try:
        (status, message) = server.cleanScheduledRecordings()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def isProgScheduled(prog, schedule=None):
    """ Using Twisted find out if a programme is scheduled to record """
    _debug_('isProgScheduled(prog=%r, schedule=%r)' % (prog, schedule), 2)
    if schedule or schedule == {}:
        if schedule == {}:
            return (FALSE, _('program not scheduled'))

        for me in schedule.values():
            if me.start == prog.start and me.channel_id == prog.channel_id:
                return (TRUE, _('program is scheduled'))

        return (FALSE, _('program not scheduled'))
    else:
        try:
            (status, message) = server.isProgScheduled(jellyToXML(prog), schedule)
        except:
            return (FALSE, 'record_client: '+_('connection error'))

        return (status, message)


def findProg(chan, start):
    """ Using Twisted find a program using the channel and the start time """
    _debug_('findProg(chan=%r, start=%r)' % (chan, start), 2)
    try:
        (status, response) = server.findProg(chan, start)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def findMatches(find='', movies_only=0):
    """ Using Twisted find matching programmes """
    _debug_('findMatches(find=%r, movies_only=%r)' % (find, movies_only), 2)
    try:
        (status, response) = server.findMatches(find, movies_only)
    except Exception, e:
        _debug_('Search error for \'%s\' %s' % (find, e), DWARNING)
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def addFavorite(name, prog, exactchan, exactdow, exacttod):
    """ Using Twisted add a favourite programme """
    _debug_('addFavorite(name=%r, prog=%r, exactchan=%r, exactdow=%r, exacttod=%r)' % \
        (name, prog, exactchan, exactdow, exacttod), 2)
    try:
        (status, message) = server.addFavorite(name, prog, exactchan, exactdow, exacttod)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def addEditedFavorite(name, title, chan, dow, mod, priority, allowDuplicates, onlyNew):
    """ Using Twisted add an edited favourite programme """
    _debug_( \
        'addEditedFavorite(name=%r, title=%r, chan=%r, dow=%r, mod=%r, priority=%r, allowDuplicates=%r, onlyNew=%r)' % \
        (name, title, chan, dow, mod, priority, allowDuplicates, onlyNew), 2)
    try:
        (status, message) = \
            server.addEditedFavorite(jellyToXML(name), \
            jellyToXML(title), chan, dow, mod, priority, allowDuplicates, onlyNew)
    except Exception, e:
        _debug_('%s' % e, DERROR)
        traceback.print_exc()
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def removeFavorite(name):
    """ Using Twisted remove a favourite programme """
    _debug_('removeFavorite(name=%r)' % (name), 2)
    try:
        (status, message) = server.removeFavorite(name)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def clearFavorites():
    """ Using Twisted clear favourites """
    _debug_('clearFavorites()', 2)
    try:
        (status, message) = server.clearFavorites()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def getFavorites():
    """ Using Twisted get favourites """
    _debug_('getFavorites()', 2)
    try:
        (status, response) = server.getFavorites()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def getFavorite(name):
    """ Using Twisted get a favourite """
    _debug_('getFavorite(name=%r)' % (name), 2)
    try:
        (status, response) = server.getFavorite(name)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def getFavoriteObject(prog, favs=None):
    """ Using Twisted get a favourite object """
    _debug_('getFavoriteObject(prog=%r, favs=%r)' % (prog, favs), 2)
    try:
        (status, response) = server.getFavoriteObject(jellyToXML(prog), jellyToXML(favs))
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return returnFromJelly(status, response)


def adjustPriority(favname, mod):
    """ Using Twisted adjust the priority of a favourite programme """
    _debug_('adjustPriority(favname=%r, mod=%r)' % (favname, mod), 2)
    try:
        (status, message) = server.adjustPriority(favname, mod)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def isProgAFavorite(prog, favs=None):
    """ Using Twisted find out if a programme is a favourite """
    _debug_('isProgAFavorite(prog=%r, favs=%r)' % (prog, favs), 2)
    try:
        (status, message) = server.isProgAFavorite(jellyToXML(prog), jellyToXML(favs))
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def removeFavoriteFromSchedule(fav):
    """ Using Twisted remove a favourite from the schedule """
    _debug_('removeFavoriteFromSchedule(fav=%r)' % (fav), 2)
    try:
        (status, message) = server.removeFavoriteFromSchedule(fav)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def addFavoriteToSchedule(fav):
    """ Using Twisted add a favourite to the schedule """
    _debug_('addFavoriteToSchedule(fav=%r)' % (fav), 2)
    try:
        (status, message) = server.addFavoriteToSchedule(fav)
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


def updateFavoritesSchedule():
    """ Using Twisted update the recoding schedule with the favourites """
    _debug_('updateFavoritesSchedule()', 2)
    try:
        (status, message) = server.updateFavoritesSchedule()
    except:
        return (FALSE, 'record_client: '+_('connection error'))
    return (status, message)


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

    rc = RecordClient()

    if len(sys.argv) >= 2:
        function = sys.argv[1].lower()
        args = sys.argv[2:]
    else:
        function = 'none'

    start = time.time()
    print 'xml_rpc_server at %r' % (xml_rpc_server)
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

    if function == "findnextprogramnow":
        result = rc.findNextProgramNow(True)
        print 'recording:%r\n"%s"' % (result, result)
        result = rc.findNextProgramNow(False)
        print 'next     :%r\n"%s"' % (result, result)

    if function == "findnextprogram":
        rc.findNextProgram(handler)

    if function == "findnextprogramrecording":
        rc.findNextProgram(handler, True)

    if function == "getscheduledrecordingsnow":
        result = rc.getScheduledRecordingsNow()
        print 'result: %r\n"%s"' % (result, result)

    if function == "getscheduledrecordings":
        rc.getScheduledRecordings(handler)

    if function == "updatefavoritesschedulenow":
        result = rc.updateFavoritesScheduleNow()
        print '%s: result: %r' % (rc.timeit(start), result)

    if function == "updatefavoritesschedule":
        rc.updateFavoritesSchedule(handler)

    if function == "findmatchesnow":
        result = rc.findMatchesNow(args)
        print '%s: result: %r' % (rc.timeit(start), result)

    if function == "getfavoritesnow":
        result = rc.getFavoritesNow()
        print '%s: result: %r' % (rc.timeit(start), result)

    if function == "removefavoritenow":
        result = rc.removeFavoriteNow()
        print '%s: result: %r' % (rc.timeit(start), result)


    #--------------------------------------------------------------------------------
    # Twisted xmlrpc tests
    #--------------------------------------------------------------------------------

    if function == "test":
        (result, response) = connectionTest('connection test')
        print 'result: %s, response: %s ' % (result, response)

    if function == "getfavorites":
        (result, response) = getFavorites()
        print '%r' % response

    if function == "moviesearch":
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


    if function == "addfavorite":
        if len(sys.argv) >= 3:
            name=Unicode(string.join(sys.argv[2:]))
            title=name
            channel="ANY"
            dow="ANY"
            mod="ANY"
            priority=0
            allowDuplicates=FALSE
            onlyNew=TRUE

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

    kaa.notifier.OneShotTimer(shutdown, 'bye', time.time()).start(20)
    kaa.main.run()
