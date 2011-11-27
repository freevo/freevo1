# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to record tv and extract the subtitles
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#   Clean up the code and remove unused stuff
# Bugs:
#   There is a bug in vbi2srt that causes incorrect timings when vps is
#   used. vbi2srt is currently being rewritten to correct this problem.
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
logger = logging.getLogger("freevo.tv.plugins.vbi2srt_record")

__author__ = "Duncan Webb <duncan@freevo.org>"
__doc__ = """
This module requires vbi2srt, U{http://www.linuxowl.com/vbi2srt.html}
Currently only ivtv cards and teletext is supported
To use this plug-in add the following to local_conf.py
plugin.remove('tv.generic_record')
plugin_record = plugin.activate("tv.vbi2srt_record")
"""

import sys, string
import random
import time, os, string
import threading
import signal

import config
import tv.ivtv
import childapp
import plugin
import rc
import util.tv_util as tv_util

from event import *
from tv.channels import FreevoChannels



class PluginInterface(plugin.Plugin):
    """
    Record subtitles from teletext pages (IVTV cards only)
    Also uses the PDC (Programme Delivery Control) from VPS (Video
    Programming Signal) to start and stop the recording.

    The teletext page number is taken from TV_CHANNELS, eg:

    | TV_CHANNELS = [
    |     #'XMLTV Id',    'Channel Name', 'Freq', 'Times', 'Video Group', 'Teletext Page Number'
    |     ('bbc.co.uk',   'BBC Prime',    'K32',  '',      '0',           '881'),
    |     ('cnn.com',     'CNN Int.',     'S13'),
    |     ('C1.sfdrs.ch', 'SF 1',         'K05',  '',      '0',           '777'),
    |     ('C2.sfdrs.ch', 'SF 2',         'K10',  '',      '0',           '777'),
    | ]
    |
    | TV_FREQUENCY_TABLE = {
    |     'K32' : 559250,
    |     'S13' : 246250,
    |     'K05' : 175500,
    |     'K10' : 211000,
    | }

    Requires: vbi2srt U{http://www.linuxowl.com/vbi2srt.html}

    Updates available from http://www.linuxowl.com/software/.

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    | plugin.remove('tv.generic_record')
    | plugin_record = plugin.activate('tv.vbi2srt_record')
    """

    def __init__(self):
        logger.log( 9, 'PluginInterface.__init__()')
        plugin.Plugin.__init__(self)
        plugin.register(Recorder(), plugin.RECORD)

    def shutdown(self):
        logger.debug('PluginInterface.shutdown()')


class Recorder:
    """
    """
    def __init__(self):
        logger.log( 9, 'Recorder.__init__()')
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        logger.info('ACTIVATING VBI2SRT RECORD PLUGIN')

        self.vg = None
        self.fc = FreevoChannels()
        self.tuner_chidx = 0    # Current channel, index into config.TV_CHANNELS
        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()


    def Record(self, rec_prog):
        logger.log( 9, 'Record(rec_prog=%r)', rec_prog)
        frequency = self.fc.chanSet(str(rec_prog.tunerid), False, 'record plugin')

        rec_prog.filename = tv_util.getProgFilename(rec_prog)
        rec_prog.filename = os.path.splitext(tv_util.getProgFilename(rec_prog))[0] + '.mpeg'
        logger.debug('filename=%r', rec_prog.filename)

        self.vg = self.fc.getVideoGroup(rec_prog.tunerid, False)

        cl_options = { 'channel'  : rec_prog.tunerid,
                       'frequency' : frequency,
                       'frequencyMHz' : float(frequency) / 1000,
                       'filename' : rec_prog.filename,
                       'base_filename' : os.path.basename(rec_prog.filename),
                       'title' : rec_prog.title,
                       'sub-title' : rec_prog.sub_title,
                       'seconds'  : rec_prog.rec_duration,
                       'start'  : rec_prog.start,
                       'pdc-start'  : rec_prog.pdc_start,
        }

        logger.debug('cl_options=%r', cl_options)
        logger.debug('chan_index=%r', self.fc.chan_index)
        logger.debug('vg.vdev=%r', self.vg.vdev)
        logger.debug('vg.vvbi=%r', self.vg.vvbi)
        pagenum = None;
        try:
            pagenum = int(config.TV_CHANNELS[self.fc.chan_index][5])
        except:
            pagenum = None;
        logger.debug('pagenum=%r', pagenum)

        if pagenum:
            # there is a bug in vbi2srt that causes out of sync subtitles when VPS is used
            self.rec_command = \
                'vbi2srt --verbose --video-in=%s --video-out=%s --vbi-device=%s --seconds=%s --vps=%s --page=%s' % \
                (self.vg.vdev, rec_prog.filename, self.vg.vvbi, rec_prog.rec_duration, rec_prog.pdc_start, pagenum)
        else:
            self.rec_command = \
                'vbi2srt --verbose --video-in=%s --video-out=%s --vbi-device=%s --seconds=%s --vps=%s' % \
                (self.vg.vdev, rec_prog.filename, self.vg.vvbi, rec_prog.rec_duration, rec_prog.pdc_start)
        logger.debug('rec_command=%r', self.rec_command)

        self.thread.mode     = 'record'
        self.thread.prog     = rec_prog
        self.thread.command  = self.rec_command
        self.thread.autokill = float(rec_prog.rec_duration + 10)
        self.thread.mode_flag.set()


    def Stop(self):
        logger.log( 9, 'Stop()')
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()


class RecordApp(childapp.ChildApp):
    """
    Record application class
    """
    def __init__(self, app):
        logger.log( 9, 'RecordApp.__init__(app=%r)', app)
        childapp.ChildApp.__init__(self, app, doeslogging=1)

    def kill(self):
        logger.log( 9, 'kill()')
        childapp.ChildApp.kill(self, signal.SIGINT)


class Record_Thread(threading.Thread):
    """
    Record thread to handle the recording states
    """
    def __init__(self):
        logger.log( 9, 'Record_Thread.__init__()')
        threading.Thread.__init__(self)

        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.command  = ''
        self.vg = None
        self.prog = None
        self.app = None

    def run(self):
        logger.log( 9, 'Record_Thread.run()')
        while 1:
            logger.debug('mode=%s', self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()

            elif self.mode == 'record':
                rc.post_event(Event('RECORD_START', arg=self.prog))

                fc = FreevoChannels()
                logger.debug('channel %s', fc.getChannel())

                self.vg = fc.getVideoGroup(self.prog.tunerid, False)

                v = tv.ivtv.IVTV(self.vg.vdev)

                v.init_settings()

                logger.debug('Using video device=%r', self.vg.vdev)

                logger.debug('Setting Channel to %r', self.prog.tunerid)
                fc.chanSet(str(self.prog.tunerid), False)

                logger.debug('command %r', self.command)
                self.app = RecordApp(self.command)
                logger.debug('command pid: %s', self.app.child.pid)

                while self.mode == 'record' and self.app.isAlive():
                    self.autokill -= 0.5
                    time.sleep(0.5)
                    if self.autokill <= 0:
                        logger.debug('autokill timeout, stopping recording')
                        self.mode = 'stop'

                if self.app.isAlive():
                    # might not want to do this is PDC is valid, programme may be delayed
                    logger.debug('past wait!!')
                    self.app.kill()

                rc.post_event(Event('RECORD_STOP', arg=self.prog))
                logger.debug('finished recording')

                self.mode = 'idle'
            else:
                self.mode = 'idle'
            time.sleep(0.5)
