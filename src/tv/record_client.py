# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# record_client.py - A client interface to the Freevo recording server.
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

import kaa.rpc
import kaa.notifier
import time, sys, socket, traceback, string
import xmlrpclib
import epg_types

from util.marmalade import jellyToXML, unjellyFromXML

TRUE  = 1
FALSE = 0

xml_rpc_server = 'http://%s:%s/' % (config.RECORDSERVER_IP, config.RECORDSERVER_PORT)
server = xmlrpclib.Server(xml_rpc_server, allow_none=1)

class RecordClient:
    """
    recordserver access class using kaa.rpc
    """
    def __init__(self):
        """
        """
        _debug_('RecordClient.__init__()', 2)
        self.socket = (config.RECORDSERVER_IP, config.RECORDSERVER_PORT2)
        self.secret = config.RECORDSERVER_SECRET
        self.server = None


    def recordserver_rpc(self, cmd, *args, **kwargs):
        """ call the record server command using kaa rpc """
        _debug_('recordserver_rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs), 2)
        return self.server.rpc(cmd, *args, **kwargs)

    def getScheduledRecordings(self):
        """ get the scheduled recordings, returning an in process object """
        _debug_('getScheduledRecordings()', 2)
        inprogress = self.recordserver_rpc('getScheduledRecordings')
        print 'RecordClient.getScheduledRecordings.inprogress = %r' % (inprogress)
        return inprogress


    def server_rpc(self, cmd, callback, *args, **kwargs):
        """
        Call the server with the command the results will be put in the callback
        Try to reconnect if the connection is down
        """
        _debug_('server_rpc(cmd=%r, callback=%r, args=%r, kwargs=%r)' % (cmd, callback, args, kwargs), 2)
        try:
            if self.server is None:
                try:
                    self.server = kaa.rpc.Client(self.socket, self.secret)
                    _debug_('%r is up' % (self.socket,))
                except kaa.rpc.ConnectError, e:
                    _debug_('%r is down' % (self.socket,))
                    self.server = None
                    return False
            self.server.rpc(cmd, *args, **kwargs).connect(callback)
            return True
        except kaa.rpc.ConnectError, e:
            _debug_('%r is down' % (self.socket,))
            self.server = None
            return False


    def getScheduledRecordings(self, callback):
        """ Get the scheduled recordings, using a callback function """
        _debug_('getScheduledRecordings(callback=%r)' % (callback), 2)
        return self.server_rpc('getScheduledRecordings', callback)


    def findNextProgram(self, callback):
        """ Find the next program using a callback function """
        _debug_('findNextProgram(callback=%r)' % (callback), 2)
        return self.server_rpc('findNextProgram', callback)


    def isPlayerRunning(self, callback):
        """ Find out if a player is running, using a callback function """
        _debug_('isPlayerRunning(callback=%r)' % (callback), 2)
        return self.server_rpc('isPlayerRunning', callback)



#
# Deprecated Twisted calls
#
def returnFromJelly(status, response):
    """ Unjelly the xml from the response """
    _debug_('returnFromJelly(status=%r, response=%r)' % (status, response), 2)
    if status:
        return (status, unjellyFromXML(response))
    return (status, response)


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

    def handler(result):
        """ A callback handler for test functions """
        _debug_('handler(result)=%r' % (result), 2)
        print 'result = %r' % (result)
        raise SystemExit

    rc = RecordClient()
    rc.getScheduledRecordings(handler)
    kaa.main()

    if len(sys.argv) >= 2:
        function = sys.argv[1].lower()
    else:
        function = 'none'

    print 'xml_rpc_server at %r' % (xml_rpc_server)

    if function == "updatefavoritesschedule":
        (result, response) = updateFavoritesSchedule()
        print '%r' % response


    if function == "test":
        (result, response) = connectionTest('connection test')
        print 'result: %s, response: %s ' % (result, response)


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
