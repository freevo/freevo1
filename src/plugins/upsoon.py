# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Stop the playing and listening when something is upsoon
# -----------------------------------------------------------------------
# $Id$
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
# -----------------------------------------------------------------------


import config
import plugin
import time, sys, os, socket, traceback, string
import xmlrpclib
import rc
import glob
import thread
import tv.v4l2
from tv.channels import FreevoChannels
from util.marmalade import jellyToXML, unjellyFromXML
from gui import AlertBox
from event import *


class PluginInterface(plugin.DaemonPlugin):
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
    __author_email__     = 'duncan@freevo.org'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'


    def __init__(self):
        """
        init the upsoon plugin
        """
        _debug_('__init__(self)', 2)
        plugin.DaemonPlugin.__init__(self)
        self.lock = thread.allocate_lock()
        self.poll_interval = 1500 #15 secs
        self.poll_menu_only = 0
        self.event_listener = 1
        plugin.register(self, 'upsoon')

        server_string = 'http://%s:%s/' % (config.RECORDSERVER_IP, config.RECORDSERVER_PORT)
        _debug_('%s' % server_string)
        self.server = xmlrpclib.Server(server_string, allow_none=1)
        _debug_('%s' % self.server)

        self.serverup = None
        self.next_program = self.findNextProgram()
        _debug_('%s' % (self.next_program))

        self.fc = FreevoChannels()

        self.seconds_before_announce = 120
        self.seconds_before_start = 60
        self.pending_lockfile = config.FREEVO_CACHEDIR + '/record.soon'
        self.tv_lockfile = None # lockfile of recordserver
        self.stopped = False    # flag that tells upsoon stopped the tv, not the user


    def findNextProgram(self):
        """ returns the next program that will be recorded """
        _debug_('findNextProgram(self)', 2)
        serverup = True
        try:
            (status, message) = self.server.findNextProgram()
            _debug_('status=%s, message=%s' % (status, message), 2)
        except TypeError, e:
            _debug_('findNextProgram:%s' % e, 0)
            status = False
            pass
        except Exception, e:
            serverup = False
            status = False
            if sys.exc_type != socket.error:
                traceback.print_exc()
                _debug_('findNextProgram:%s' % e, 0)

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
        _debug_('isPlayerRunning(self)', 2)
        serverup = True
        try:
            (status, message) = self.server.isPlayerRunning()
            _debug_('status=%s, message=%s' % (status, message), 2)
        except Exception, e:
            serverup = False
            message = None
            if sys.exc_type != socket.error:
                traceback.print_exc()
                _debug_('isPlayerRunning:%s' % e, 0)

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
        _debug_('getPlayerRunning(self)', 2)
        return self.is_player_running


    def close(self):
        """
        to be called before the plugin exists.
        It terminates the connection with the server
        """
        _debug_('close(self)')


    def poll(self):
        """
        Sends a poll message to the record server
        """
        now=time.time()
        _debug_('poll(self)', 2)

        self.next_program  = self.findNextProgram()

        _debug_('now=%s next=%s ' % (time.strftime('%T', time.localtime(now)), self.next_program))

        if self.next_program == None:
            return None

        vdev=self.fc.getVideoGroup(self.next_program.channel_id, False).vdev
        rdev=config.RADIO_DEVICE

        # Remove the pending record lock file when a record lock file is written
        if os.path.exists(self.pending_lockfile):
            if os.path.exists(self.tv_lockfile):
                os.remove(self.pending_lockfile)
                _debug_("record.soon lockfile removed")
            return None

        # Check if a recording is in progress
        self.tv_lockfile = config.FREEVO_CACHEDIR + '/record.'+vdev.split('/')[-1]
        if os.path.exists(self.tv_lockfile):
            return None

        secs_to_next = self.next_program.start - config.TV_RECORD_PADDING_PRE - int(now + 0.5)
        _debug_('next recording in %s secs' % (secs_to_next))

        # announce 120 seconds before recording is due to start
        # stop the player 60 seconds before recording is due to start

        if (secs_to_next > self.seconds_before_announce):
            return None

        # check the video
        if vdev:
            try:
                dev_fh = os.open(vdev, os.O_TRUNC)
                try:
                    os.read(dev_fh, 1)
                except:
                    if (secs_to_next > self.seconds_before_start):
                        # just announce
                        rc.post_event(Event(OSD_MESSAGE, arg=_('A recording will start in a few minutes')))
                    else:
                        # stop the tv
                        rc.post_event(STOP)
                        self.stopped = True
                        open(self.pending_lockfile, 'w').close()
                os.close(dev_fh)
            except:
                _debug_('cannot check video device \"%s\"' % (vdev), 0)

        # check the radio
        if rdev:
            try:
                dev_fh = os.open(rdev, os.O_TRUNC)
                try:
                    os.read(dev_fh, 1)
                except:
                    if (secs_to_next > self.seconds_before_start):
                        rc.post_event(Event(OSD_MESSAGE, arg=_('A recording will start in a few minutes')))
                    else:
                        # stop the radio
                        rc.post_event(STOP)
                        self.stopped = True
                        # write lockfile, not sure if this is needed
                        open(self.pending_lockfile, 'w').close()
                os.close(dev_fh)
            except:
                _debug_('cannot check radio device \"%s\"' % (rdev), 0)

        return None


    def eventhandler(self, event, menuw=None):
        """ Processes events
        detect the video start and stop events so that the
        alert box will work correctly """
        self.lock.acquire()
        try:
            _debug_('eventhandler(self, %s, %s) name=%s arg=%s context=%s handler=%s' % \
                (event, menuw, event.name, event.arg, event.context, event.handler), 2)
            _debug_('event name=%s arg=%s' % (event.name, event.arg))
        finally:
            self.lock.release()

        if (event.name == 'VIDEO_START'):
            self.stopped = False
        if (event.name == 'VIDEO_END'):
            if self.stopped:
                # upsoon stopped the tv, now display a msgbox
                AlertBox(text=_('TV stopped, a recording is about to start!'), height=200).show()
        return 0


if __name__ == '__main__':
    # test code, run with freevo execute /path/to/upsoon.py
    if len(sys.argv) >= 2:
        function = sys.argv[1]
    else:
        function = 'none'

    if function == "isplayerrunning":
        (result, response) = isPlayerRunning()
        print response

    # looks like devinfo...
    fc = FreevoChannels()
    vg=fc.getVideoGroup('K10', False)
    print "vg=%s" % vg
    print "dir(%s)" % dir(vg)
    for it in dir(vg):
        print "   %s:%s" % (it, eval('vg.'+it))
    vdev=vg.vdev
    print "vdev=%s" % vdev
