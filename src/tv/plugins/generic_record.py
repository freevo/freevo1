# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to record tv using VCR_CMD.
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
import logging
logger = logging.getLogger("freevo.tv.plugins.generic_record")


import sys
import time, os, string
import threading
import signal

import config
import childapp
import plugin
import rc
import util.tv_util as tv_util

from event import *
from tv.channels import FreevoChannels

class PluginInterface(plugin.Plugin):
    """
    Generic TV recording application used with BTTV and DVB cards
    """

    def __init__(self):
        logger.debug('PluginInterface.__init__()')
        plugin.Plugin.__init__(self)
        plugin.register(Recorder(), plugin.RECORD)


class Recorder:

    def __init__(self):
        logger.debug('Recorder.__init__()')
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        logger.info('ACTIVATING GENERIC RECORD PLUGIN')

        self.fc = FreevoChannels()
        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()


    def Record(self, rec_prog):
        logger.debug('Record(rec_prog=%r)', rec_prog)
        vg = self.fc.getVideoGroup(rec_prog.tunerid, False)

        frequency = self.fc.chanSet(str(rec_prog.tunerid), False, 'record plugin')

        rec_prog.filename = tv_util.getProgFilename(rec_prog)

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
                       'group-type' : vg.group_type
        }

        if isinstance(config.VCR_CMD, str) or isinstance(config.VCR_CMD, unicode):
            self.rec_command = config.VCR_CMD % cl_options
        elif isinstance(config.VCR_CMD, list) or isinstance(config.VCR_CMD, tuple):
            self.rec_command = []
            for arg in config.VCR_CMD:
                self.rec_command.append(arg % cl_options)

        self.thread.mode     = 'record'
        self.thread.prog     = rec_prog
        self.thread.command  = self.rec_command
        self.thread.autokill = float(rec_prog.rec_duration + 10)
        self.thread.mode_flag.set()

        logger.debug('Recorder::Record: %s', self.rec_command)


    def Stop(self):
        logger.debug('Stop()')
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()


class RecordApp(childapp.ChildApp):

    def __init__(self, app):
        logger.debug('RecordApp.__init__(app=%r)', app)
        self.log_stdout = None
        self.log_stderr = None
        if config.DEBUG:
            fname_out = os.path.join(config.FREEVO_LOGDIR, 'recorder_stdout.log')
            fname_err = os.path.join(config.FREEVO_LOGDIR, 'recorder_stderr.log')
            try:
                self.log_stdout = open(fname_out, 'a')
                self.log_stderr = open(fname_err, 'a')
            except IOError:
                logger.error('Cannot open "%s" and "%s" for record logging!', fname_out, fname_err)

                print
                print 'Please set DEBUG=0 or start Freevo from a directory that is writeable!'
                print
            else:
                logger.info('Record logging to "%s" and "%s"', fname_out, fname_err)

        childapp.ChildApp.__init__(self, app)


    def kill(self):
        logger.debug('kill()')
        childapp.ChildApp.kill(self, signal.SIGINT)

        if self.log_stdout:
            self.log_stdout.close()
        if self.log_stderr:
            self.log_stderr.close()


class Record_Thread(threading.Thread):

    def __init__(self):
        logger.debug('Record_Thread.__init__()')
        threading.Thread.__init__(self)

        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.command  = ''
        self.prog = None
        self.app = None

    def run(self):
        logger.debug('run()')
        while 1:
            logger.debug('Record_Thread::run: mode=%s', self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()

            elif self.mode == 'record':
                rc.post_event(Event('RECORD_START', arg=self.prog))
                logger.debug('Record_Thread::run: cmd=%s', self.command)

                self.app = RecordApp(self.command)
                logger.debug('app child pid: %s', self.app.child.pid)

                while self.mode == 'record' and self.app.isAlive():
                    self.autokill -= 0.5
                    time.sleep(0.5)
                    if self.autokill <= 0:
                        logger.debug('autokill timeout, stopping recording')
                        self.mode = 'stop'

                if self.app.isAlive():
                    logger.debug('Record_Thread::run: past wait!!')
                    self.app.kill()

                rc.post_event(Event('RECORD_STOP', arg=self.prog))
                logger.debug('Record_Thread::run: finished recording')

                self.mode = 'idle'
            else:
                self.mode = 'idle'
            time.sleep(0.5)
