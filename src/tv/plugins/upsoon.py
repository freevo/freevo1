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
        _debug_('PluginInterface.__init__()', 1)
        plugin.DaemonPlugin.__init__(self)
        plugin.register(self, 'upsoon')
        self.lock = thread.allocate_lock()
        self.timer = Timer(self.timer_handler).start(15)
        self.event = EventHandler(self.event_handler)
        self.event.register(('VIDEO_START', 'VIDEO_END'))

        self.recordclient = RecordClient()

        self.fc = FreevoChannels()
        self.rdev = config.RADIO_DEVICE

        self.next_program = None
        self.seconds_before_announce = 120
        self.seconds_before_start = 60
        self.pending_lockfile = config.FREEVO_CACHEDIR + '/record.soon'
        self.tv_lockfile = None # lockfile of recordserver
        self.stopped = None     # flag that tells upsoon what stopped


    def findNextProgramHandler(self, result):
        """ Handles the result from the findNextProgram call """
        _debug_('findNextProgramHandler(result=%r)' % (result), 1)
        self.next_program = result

        if self.next_program == None:
            return

        now = time.time()
        _debug_('now=%s next=%s ' % (time.strftime('%T', time.localtime(now)), self.next_program), 2)

        self.vdev = self.getVideoForChannel(self.next_program.channel_id)

        self.tv_lockfile = os.path.join(config.FREEVO_CACHEDIR, 'record.'+self.vdev.split('/')[-1])

        self.seconds_to_next = self.next_program.start - config.TV_RECORD_PADDING_PRE - int(now + 0.5)
        _debug_('next recording in %s secs' % (self.seconds_to_next), 1)

        # announce 120 seconds before recording is due to start
        # stop the player 60 seconds before recording is due to start

        if (self.seconds_to_next > self.seconds_before_announce):
            return

        _debug_('stopping video or radio player')
        self.stopVideoInUse(self.vdev)
        self.stopRadioInUse(self.rdev)
        return


    def getVideoForChannel(self, channel_id):
        """ get the video device given a channel id """
        _debug_('getVideoForChannel(channel_id=%r)' % (channel_id), 1)
        return self.fc.getVideoGroup(channel_id, False).vdev


    def stopVideoInUse(self, vdev):
        """ stop the video device if being used """
        _debug_('stopVideoInUse(vdev=%r)' % (vdev), 1)
        if vdev:
            try:
                dev_fh = os.open(vdev, os.O_TRUNC)
                try:
                    os.read(dev_fh, 1)
                except:
                    if (self.seconds_to_next > self.seconds_before_start):
                        # just announce
                        rc.post_event(Event(OSD_MESSAGE, arg=_('A recording will start in a few minutes')))
                    else:
                        # stop the tv
                        rc.post_event(STOP)
                        self.stopped = _('Radio')
                        open(self.pending_lockfile, 'w').close()
                os.close(dev_fh)
            except Exception, e:
                print '%r: %s' % (vdev, e)
                _debug_('cannot check video device \"%s\"' % (vdev), 0)


    def stopRadioInUse(self, rdev):
        """ stop the radio device if being used """
        _debug_('stopRadioInUse(rdev=%r)' % (rdev), 1)
        if rdev:
            try:
                dev_fh = os.open(rdev, os.O_TRUNC)
                try:
                    os.read(dev_fh, 1)
                except:
                    if (self.seconds_to_next > self.seconds_before_start):
                        rc.post_event(Event(OSD_MESSAGE, arg=_('A recording will start in a few minutes')))
                    else:
                        # stop the radio
                        rc.post_event(STOP)
                        self.stopped = _('TV')
                        open(self.pending_lockfile, 'w').close()
                os.close(dev_fh)
            except:
                _debug_('cannot check radio device \"%s\"' % (rdev), 0)


    def close(self):
        """
        to be called before the plugin exists.
        It terminates the connection with the server
        """
        _debug_('close()', 1)


    def timer_handler(self):
        """
        Sends a poll message to the record server
        """
        _debug_('timer_handler()', 1)

        # Remove the pending record lock file when a record lock file is written
        if self.tv_lockfile:
            if os.path.exists(self.tv_lockfile):
                if os.path.exists(self.pending_lockfile):
                    os.remove(self.pending_lockfile)
                    _debug_("record.soon lockfile removed")
                return True
            else:
                self.tv_lockfile = None

        # Check if a recording is about to start
        if os.path.exists(self.pending_lockfile):
            return True

        self.recordclient.findNextProgram(self.findNextProgramHandler)
        return True


    def event_handler(self, event):
        """
        Processes events, detect the video start and stop events so that the
        alert box will work correctly
        """
        _debug_('event_handler(event=%r)' % (event), 1)
        try:
            _debug_('event_handler(%s) name=%s arg=%s context=%s handler=%s' % \
                (event, event.name, event.arg, event.context, event.handler), 2)
        finally:
            pass

        if (event.name == 'VIDEO_START'):
            self.stopped = None
        if (event.name == 'VIDEO_END'):
            if self.stopped:
                # upsoon stopped the tv, now display a msgbox
                AlertBox(text=_('%s stopped, a recording is about to start!') % self.stopped, height=200).show()
                self.stopped = None
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
