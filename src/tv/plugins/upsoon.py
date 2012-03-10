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
import logging
logger = logging.getLogger("freevo.tv.plugins.upsoon")


import config
import plugin
import time, sys, os, socket, traceback, string
import xmlrpclib
import rc
import glob
import thread
import tv.v4l2
from tv.record_client import RecordClient
import kaa
from kaa import Timer
from kaa import EventHandler
from tv.channels import FreevoChannels, CHANNEL_ID
from util.marmalade import jellyToXML, unjellyFromXML
from gui import AlertBox
from event import *


class PluginInterface(plugin.DaemonPlugin):
    """
    plugin to monitor if a recording is about to start and shut down the
    player if the video device is in use

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    | plugin.activate('tv.upsoon')
    """
    __author__           = 'Duncan Webb'
    __author_email__     = 'duncan@freevo.org'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'


    def __init__(self, standalone=False):
        """
        init the upsoon plugin
        """
        logger.log( 9, 'upsoon.PluginInterface.__init__()')
        plugin.DaemonPlugin.__init__(self)
        plugin.register(self, 'upsoon')
        self.standalone = standalone
        self.lock = thread.allocate_lock()
        self.running = True
        self.timer = Timer(self.timer_handler).start(15)
        self.event = EventHandler(self.event_handler)
        #self.event.register(('VIDEO_START', 'VIDEO_END'))
        self.event.register()

        self.recordclient = RecordClient()

        self.fc = FreevoChannels()
        self.rdev = config.RADIO_DEVICE

        self.next_program = None
        self.announced = False
        self.seconds_before_announce = config.TV_UPSOON_ANNOUNCE
        self.seconds_before_start = config.TV_UPSOON_BEFORE_START
        self.pending_lockfile = config.FREEVO_CACHEDIR + '/record.soon'
        self.tv_lockfile = None # lockfile of recordserver
        self.stopped = None     # flag that tells upsoon what stopped
        if os.path.exists(self.pending_lockfile):
            os.remove(self.pending_lockfile)
            logger.debug('%r lockfile removed', self.pending_lockfile)


    def config(self):
        return [
            ('TV_UPSOON_BEFORE_START', 1*60, 'Number of seconds before start of recording to stop player'),
            ('TV_UPSOON_ANNOUNCE', 1*60+60, 'Number of seconds before start of recording to announce starting'),
        ]


    def getVideoForChannel(self, channel_id):
        """ get the video device given a channel id """
        logger.log( 9, 'getVideoForChannel(channel_id=%r)', channel_id)
        return self.fc.getVideoGroup(channel_id, False, CHANNEL_ID).vdev


    def stopVideoInUse(self, vdev):
        """ stop the video device if being used """
        logger.log( 9, 'stopVideoInUse(vdev=%r)', vdev)
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
                        self.stopped = _('TV')
                os.close(dev_fh)
            except Exception, why:
                logger.warning('cannot check video device %r: %s', vdev, why)


    def stopRadioInUse(self, rdev):
        """ stop the radio device if being used """
        logger.log( 9, 'stopRadioInUse(rdev=%r)', rdev)
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
                        self.stopped = _('Radio')
                os.close(dev_fh)
            except:
                logger.info('cannot check radio device \"%s\"', rdev)


    def close(self):
        """
        to be called before the plugin exists.
        It terminates the connection with the server
        """
        logger.log( 9, 'close()')


    def shutdown(self):
        """ Showdown handler """
        logger.log( 9, 'shutdown()')
        self.running = False


    def findNextProgramHandler(self, result):
        """ Handles the result from the findNextProgram call """
        logger.log( 9, 'findNextProgramHandler(result=%r)', result)
        (status, self.next_program) = result

        if not status:
            return

        now = time.time()
        logger.log( 9, 'now=%s next=%s ', time.strftime('%T', time.localtime(now)), self.next_program)

        self.seconds_to_next = self.next_program.start - config.TV_RECORD_PADDING_PRE - int(now + 0.5)
        logger.log( 9, 'next recording in %s secs', self.seconds_to_next)

        self.vdev = self.getVideoForChannel(self.next_program.channel_id)
        self.tv_lockfile = os.path.join(config.FREEVO_CACHEDIR, 'record.'+self.vdev.split('/')[-1])

        #print 'now=%s next=%s secs=%s file=%s' % (time.strftime('%T', time.localtime(now)),
        #    self.next_program, self.seconds_to_next, os.path.basename(self.tv_lockfile))

        if os.path.exists(self.pending_lockfile):
            self.announced = False
            if os.path.exists(self.tv_lockfile):
                os.remove(self.pending_lockfile)
                logger.debug('%r lockfile removed tv lock detected', self.pending_lockfile)
            elif self.seconds_to_next < -self.seconds_before_start:
                os.remove(self.pending_lockfile)
                logger.debug('%r lockfile removed recording in-progress', self.pending_lockfile)
        else:
            if os.path.exists(self.tv_lockfile):
                logger.debug('%r not creating tv lock detected', self.pending_lockfile)
                return
            if self.seconds_to_next < 0:
                logger.debug('%r not creating recording in-progress', self.pending_lockfile)
                return
            # announce 120 seconds before recording is due to start
            # stop the player 60 seconds before recording is due to start
            if self.seconds_to_next <= self.seconds_before_start:
                open(self.pending_lockfile, 'w').close()
                logger.debug('%r lockfile created', self.pending_lockfile)

                self.stopVideoInUse(self.vdev)
                self.stopRadioInUse(self.rdev)
                logger.debug('stopped video or radio player')
            elif self.seconds_to_next <= self.seconds_before_announce:
                if not self.announced:
                    rc.post_event(Event(OSD_MESSAGE, arg=_('A recording will start in a few minutes')))
                    logger.debug('announced')
                    self.announced = True


    def timer_handler(self):
        """
        Sends a poll message to the record server
        """
        if not self.running:
            return self.running
        logger.log( 9, 'timer_handler()')
        try:
            self.recordclient.findNextProgram(self.findNextProgramHandler, isrecording=True)
        except Exception, why:
            logger.error('findNextProgram: %s', why)

        return self.running


    def event_handler(self, event):
        """
        Processes events, detect the video start and stop events so that the
        alert box will work correctly
        """
        logger.log( 9, 'event_handler(event=%r)', event.name)
        try:
            logger.log( 9, 'event_handler(%s) name=%s arg=%s context=%s handler=%s', event, event.name, event.arg, event.context, event.handler)

        finally:
            pass

        if (event.name == 'VIDEO_START'):
            self.stopped = None
        if (event.name == 'VIDEO_END'):
            if self.stopped:
                # upsoon stopped the tv, now display a msgbox
                if not self.standalone:
                    AlertBox(text=_('%s stopped, a recording is about to start!') % self.stopped, height=200).show()
                self.stopped = None
        return 0


if __name__ == '__main__':
    # test code, run with freevo execute /path/to/upsoon.py
    config.DEBUG = 2
    function = None
    if len(sys.argv) > 1:
        function = sys.argv[1].lower()
        server = RecordClient()

    if function == 'run':
        #import rc as rctrl
        #rc = rctrl.get_singleton(False)
        pi = PluginInterface()
        kaa.main.run()

    elif function == 'findnextprogram':
        def handler(result):
            print 'findnextprogram=%r' % (result,)
            print result.__dict__
            raise SystemExit
        server.findNextProgram(handler)
        kaa.main.run()

    else:
        fc = FreevoChannels()
        vg=fc.getVideoGroup('K10', False)
        print 'vg=%s' % vg
        print 'dir(%s)' % dir(vg)
        for it in dir(vg):
            print '   %s:%s' % (it, eval('vg.'+it))
        vdev=vg.vdev
        print 'vdev=%s' % vdev
