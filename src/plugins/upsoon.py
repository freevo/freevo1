# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# wakeup client
# -----------------------------------------------------------------------
# $Id: upsoon.py $
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('upsoon')
# ToDo:        
#
# -----------------------------------------------------------------------
#
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
# ----------------------------------------------------------------------- */


import plugin
import config
import time, sys, socket, traceback, string
import xmlrpclib
import rc
import thread
from event import *
from util.marmalade import jellyToXML, unjellyFromXML

# set the base debug level
dbglvl=1


class PluginInterface( plugin.DaemonPlugin ):
    """
    plugin to monitor if a recording is about to start and shut down the
    player if the video device is in use

    Requirements:
       none

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    plugin.activate('upsoon')

    """
    __author__           = 'Duncan Webb'
    __author_email__     = 'duncan-freevo@linuxowl.com'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision: 20061003 $'


    def __init__( self ):
        """
        init the upsoon plugin
        """
        _debug_('__init__(self)', dbglvl+1)
        plugin.DaemonPlugin.__init__(self)
        self.lock = thread.allocate_lock()
        self.poll_interval = 3000 #30 secs
        self.poll_menu_only = 0
        self.event_listener = 1
        plugin.register( self, 'upsoon' )

        server_string = 'http://%s:%s/' % (config.TV_RECORD_SERVER_IP, config.TV_RECORD_SERVER_PORT)

        _debug_('%s' % server_string, dbglvl)
        self.server = xmlrpclib.Server(server_string, allow_none=1)
        _debug_('%s' % self.server, dbglvl)

        self.serverup = None
        self.next_program = self.findNextProgram()
        _debug_('up=%s %s' % (self.serverup, self.next_program), dbglvl)


    def findNextProgram(self):
        """
        returns the next program that will be recorded
        """
        _debug_('findNextProgram(self)', dbglvl+1)
        serverup = True
        try:
            (status, message) = self.server.findNextProgram()
            _debug_('status=%s, message=%s' % (status, message), dbglvl+2)
        except TypeError:
            _debug_('TypeError exception')
            status = False
            pass
        except Exception, e:
            serverup = False
            status = False
            if sys.exc_type != socket.error:
                traceback.print_exc()
                _debug_(e, 0)

        if self.serverup != serverup:
            self.serverup = serverup
            if serverup:
                _debug_('The record server is up')
            else:
                _debug_('The record server is down')

        if not status:
            return None

        next_program = unjellyFromXML(message)
        return next_program


    def isPlayerRunning(self):
        """
        Check with the record server if suspended by user
        """
        _debug_('isPlayerRunning(self)', dbglvl+1)
        serverup = True
        try:
            (status, message) = self.server.isPlayerRunning()
            _debug_('status=%s, message=%s' % (status, message), dbglvl+2)
        except Exception, e:
            serverup = False
            message = None
            if sys.exc_type != socket.error:
                traceback.print_exc()
                _debug_(e, 0)

        if self.serverup != serverup:
            self.serverup = serverup
            if serverup:
                _debug_('The record server is up')
            else:
                _debug_('The record server is down')

        if message == None:
            return None

        return status


    def getPlayerRunning(self):
        """
        Return is a player is running
        """
        _debug_('getPlayerRunning(self)', dbglvl+1)
        return self.is_player_running


    def close( self ):
        """
        to be called before the plugin exists.
        It terminates the connection with the server
        """
        _debug_('close(self)')


    def poll( self ):
        """
        Sends a poll message to the record server
        """
        _debug_('poll(self)', dbglvl+1)

        self.player_running = self.isPlayerRunning()
        _debug_('player_running=%s' % self.player_running, dbglvl)
        self.next_program  = self.findNextProgram()
        _debug_('next_program=%s' % self.next_program, dbglvl)
        if self.next_program != None:
            # may need to ensure message is not too long
            start_time = time.strftime('%a %H:%M', time.localtime(self.next_program.start))
            message = '%s %s' % (self.next_program.title, start_time)
            rc.post_event(Event(OSD_MESSAGE, message))


    def eventhandler( self, event, menuw=None ):
        """
        Processes user events
        TODO
            something useful
        """
        _debug_('eventhandler(self, %s, %s) name=%s arg=%s context=%s handler=%s' % \
            (event, menuw, event.name, event.arg, event.context, event.handler), dbglvl+2)

        _debug_('event name=%s arg=%s' % (event.name, event.arg), dbglvl)

        self.lock.acquire()
        if event == BUTTON:
            if event.arg == 'POWER':
                if self.isPlayerRunning():
                    rc.post_event(Event(OSD_MESSAGE, arg=_('Playing')))
                else:
                    rc.post_event(Event(OSD_MESSAGE, arg=_('Not Playing')))
        self.lock.release()

        return 0


# this won't work
if __name__ == '__main__':
    if len(sys.argv) >= 2: 
        function = sys.argv[1]
    else:
        function = 'none'


    if function == "isplayerrunning":
        (result, response) = isPlayerRunning()
        print response
