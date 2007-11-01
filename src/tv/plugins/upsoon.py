# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Stop the playing and listening when something is upsoon
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('tv.upsoon')
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
from tv.record_client import RecordClient
from kaa.notifier import Timer, EventHandler
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

    | plugin.activate('tv.upsoon')
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
        plugin.register(self, 'upsoon')
        self.lock = thread.allocate_lock()
        self.timer = Timer(self.timer_handler).start(15)
        self.event = EventHandler(self.event_handler)
        self.event.register(('VIDEO_START', 'VIDEO_END'))

        self.recordclient = RecordClient()
        #server_string = 'http://%s:%s/' % (config.RECORDSERVER_IP, config.RECORDSERVER_PORT)
        #_debug_('%s' % server_string)
        #self.server = xmlrpclib.Server(server_string, allow_none=1)
        #_debug_('%s' % self.server)

        #self.serverup = None
        #self.next_program = self.findNextProgram()
        #_debug_('%s' % (self.next_program))
        self.next_program = None

        self.fc = FreevoChannels()
        self.rdev = config.RADIO_DEVICE

        self.seconds_before_announce = 120
        self.seconds_before_start = 60
        self.pending_lockfile = config.FREEVO_CACHEDIR + '/record.soon'
        self.tv_lockfile = None # lockfile of recordserver
        self.stopped = False    # flag that tells upsoon stopped the tv, not the user


    def findNextProgramHandler(self, result):
        """ Handles the result from the findNextProgram call """
        self.next_program = result

        now = time.time()

        _debug_('now=%s next=%s ' % (time.strftime('%T', time.localtime(now)), self.next_program), 2)

        if self.next_program == None:
            return

        self.vdev = self.getVideoForChannel(self.next_program.channel_id)

        self.tv_lockfile = os.path.join(config.FREEVO_CACHEDIR, 'record.'+vdev.split('/')[-1])

        # Remove the pending record lock file when a record lock file is written
        if os.path.exists(self.pending_lockfile):
            if os.path.exists(self.tv_lockfile):
                os.remove(self.pending_lockfile)
                _debug_("record.soon lockfile removed")
            return

        # Check if a recording is in progress
        if os.path.exists(self.tv_lockfile):
            return

        secs_to_next = self.next_program.start - config.TV_RECORD_PADDING_PRE - int(now + 0.5)
        _debug_('next recording in %s secs' % (secs_to_next), 2)

        # announce 120 seconds before recording is due to start
        # stop the player 60 seconds before recording is due to start

        if (secs_to_next > self.seconds_before_announce):
            return

        _debug_('stopping video or radio player')
        self.stopVideoInUse(self.vdev)
        self.stopRadioInUse(self.rdev)
        return


    def getVideoForChannel(self, channel_id):
        """ get the video device given a channel id """
        return self.fc.getVideoGroup(channel_id, False).vdev


    def stopVideoInUse(self, vdev):
        """ stop the video device if being used """
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


    def stopRadioInUse(self, rdev):
        """ stop the radio device if being used """
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


    def timer_handler(self):
        """
        Sends a poll message to the record server
        """
        _debug_('timer_handler()', 2)

        self.recordclient.findNextProgram(self.findNextProgramHandler)

        return True


    def event_handler(self, event):
        """
        Processes events, detect the video start and stop events so that the
        alert box will work correctly
        """
        self.lock.acquire()
        try:
            _debug_('event_handler(%s) name=%s arg=%s context=%s handler=%s' % \
                (event, event.name, event.arg, event.context, event.handler), 2)
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
    config.DEBUG = 2
    function = None
    if len(sys.argv) > 1:
        function = sys.argv[1].lower()
        rc = RecordClient()

    if function == "run":
        pi = PluginInterface()
        Timer(pi.timer_handler).start(15)
        kaa.main()

    elif function == "findnextprogram":
        def handler(result):
            print 'findnextprogram=%r' % (result)
            print result.__dict__
            raise SystemExit
        rc.findNextProgram(handler)
        kaa.main()

    elif function == "isplayerrunning":
        def handler(result):
            print 'isplayerrunning=%r' % (result)
            raise SystemExit
        rc.isPlayerRunning(handler)
        kaa.main()

    else:
        fc = FreevoChannels()
        vg=fc.getVideoGroup('K10', False)
        print "vg=%s" % vg
        print "dir(%s)" % dir(vg)
        for it in dir(vg):
            print "   %s:%s" % (it, eval('vg.'+it))
        vdev=vg.vdev
        print "vdev=%s" % vdev
