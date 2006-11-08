# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# vbi2srt_record.py - A plugin to record tv and extract the subtitles
# -----------------------------------------------------------------------
# $Id: vbi2srt_record.py 5860 2004-07-10 12:33:43Z dischi $
#
# Author: duncan-freevo@linuxowl.com (Duncan Webb)
# Notes: This module requires vbi2srt, see:
#   http://www.linuxowl.com/vbi2srt.html
#   Currently only ivtv cards and teletext is supported
#   To use this plug-in add the following to local_conf.py
#   plugin.remove('tv.generic_record')
#   plugin_record = plugin.activate('tv.vbi2srt_record')
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

DEBUG = config.DEBUG


class PluginInterface(plugin.Plugin):
    """
    Record subtitles from teletext pages (IVTV cards only)

    The teletext page number is taken from TV_CHANNELS, eg:
TV_CHANNELS = [
    #'XMLTV Id',    'Channel Name', 'Freq', 'Times', 'Video Group', 'Teletext Page Number'
    ('bbc.co.uk',   'BBC Prime',    'K32',  '',      '0',           '881'),
    ('cnn.com',     'CNN Int.',     'S13'),
    ('C1.sfdrs.ch', 'SF 1',         'K05',  '',      '0',           '777'),
    ('C2.sfdrs.ch', 'SF 2',         'K10',  '',      '0',           '777'),
]
FREQUENCY_TABLE = {
    'K32' : 559250,
    'S13' : 246250,
    'K05' : 175500,
    'K10' : 211000,
]

    Requirements:
       * vbi2srt: (http://www.linuxowl.com/vbi2srt.html)

    Updates available from http://www.linuxowl.com/software/.

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    plugin.remove('tv.generic_record')
    plugin_record = plugin.activate('tv.vbi2srt_record')

    """
    def __init__(self):
        plugin.Plugin.__init__(self)

        plugin.register(Recorder(), plugin.RECORD)


class Recorder:

    def __init__(self):
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        if DEBUG: print 'ACTIVATING VBI2SRT RECORD PLUGIN'

        self.vg = None
        self.fc = FreevoChannels()
        self.tuner_chidx = 0    # Current channel, index into config.TV_CHANNELS
        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()
        
    def Record(self, rec_prog):
        frequency = self.fc.chanSet(str(rec_prog.tunerid), False, 'record plugin')

        rec_prog.filename = tv_util.getProgFilename(rec_prog)
        rec_prog.filename = os.path.splitext(tv_util.getProgFilename(rec_prog))[0] + '.mpeg'
        if DEBUG: print('Recorder::Record:filename %s' % rec_prog.filename)

        cl_options = { 'channel'  : rec_prog.tunerid,
                       'frequency' : frequency,
                       'filename' : rec_prog.filename,
                       'base_filename' : os.path.basename(rec_prog.filename),
                       'title' : rec_prog.title,
                       'sub-title' : rec_prog.sub_title,
                       'seconds'  : rec_prog.rec_duration,
                       'start'  : rec_prog.start }

        self.vg = self.fc.getVideoGroup(rec_prog.tunerid, False)
        if DEBUG: print('Recorder::Record:cl_options %s' % cl_options)
        if DEBUG: print('Recorder::Record:chan_index %s' % self.fc.chan_index)
        if DEBUG: print('Recorder::Record:vg.vdev %s' % self.vg.vdev)
        if DEBUG: print('Recorder::Record:vg.vvbi %s' % self.vg.vvbi)
        pagenum = None;
        try:
            pagenum = int(config.TV_CHANNELS[self.fc.chan_index][5])
        except:
            pagenum = None;
        if DEBUG: print('Recorder::Record:pagenum "%s"' % pagenum)
        self.rec_command = config.VCR_CMD % cl_options
        if pagenum == None:
            self.rec_command = 'vbi2srt --verbose --video-in=%s --video-out=%s --vbi-device=%s --seconds=%s --vps=%s' % \
                (self.vg.vdev, rec_prog.filename, self.vg.vvbi, rec_prog.rec_duration, rec_prog.start)
        else:
            # there is a bug in vbi2srt that causes out of sync subtitles when VPS is used
            self.rec_command = 'vbi2srt --verbose --video-in=%s --video-out=%s --vbi-device=%s --seconds=%s --vps=%s --page=%s' % \
                (self.vg.vdev, rec_prog.filename, self.vg.vvbi, rec_prog.rec_duration, rec_prog.start, pagenum)
    
        self.thread.mode     = 'record'
        self.thread.prog     = rec_prog
        self.thread.command  = self.rec_command
        self.thread.autokill = float(rec_prog.rec_duration + 10)
        self.thread.mode_flag.set()
        
        if DEBUG: print('Recorder::Record: %s' % self.rec_command)
        
        
    def Stop(self):
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()


class RecordApp(childapp.ChildApp):

    def __init__(self, app):
        if DEBUG: 
            fname_out = os.path.join(config.LOGDIR, 'vbi2srt-stdout.log')
            fname_err = os.path.join(config.LOGDIR, 'vbi2srt-stderr.log')
            try:
                self.log_stdout = open(fname_out, 'a')
                self.log_stderr = open(fname_err, 'a')
            except IOError:
                print
                print (('ERROR: Cannot open "%s" and "%s" for ' +
                        'record logging!') % (fname_out, fname_err))
                print 'Please set DEBUG=0 or '
                print 'start Freevo from a directory that is writeable!'
                print
            else:
                print 'Record logging to "%s" and "%s"' % (fname_out, fname_err)

        childapp.ChildApp.__init__(self, app)
        

    def kill(self):
        childapp.ChildApp.kill(self, signal.SIGINT)

        if DEBUG:
            self.log_stdout.close()
            self.log_stderr.close()


class Record_Thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        
        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.command  = ''
        self.vg = None
        self.prog = None
        self.app = None

    def run(self):
        while 1:
            if DEBUG: print('Record_Thread::run: mode=%s' % self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()
                
            elif self.mode == 'record':
                rc.post_event(Event('RECORD_START', arg=self.prog))
                if DEBUG: print('Record_Thread::run: cmd=%s' % self.command)

                fc = FreevoChannels()
                if DEBUG: print 'CHAN: %s' % fc.getChannel()

                (v_norm, v_input, v_clist, v_dev) = config.TV_SETTINGS.split()

                v = tv.ivtv.IVTV(v_dev)

                v.init_settings()
                self.vg = fc.getVideoGroup(self.prog.tunerid, False)

                if DEBUG: print 'Using video device %s' % self.vg.vdev
                if DEBUG: print 'Setting Input to %s' % self.vg.input_num
                v.setinput(self.vg.input_num)

                if DEBUG: print 'Setting Channel to %s' % self.prog.tunerid
                fc.chanSet(str(self.prog.tunerid), False)

                if DEBUG: v.print_settings()

                self.app = RecordApp(self.command)
                
                while self.mode == 'record' and self.app.isAlive():
                    self.autokill -= 0.5
                    time.sleep(0.5)
                    if self.autokill <= 0:
                        if DEBUG:
                            print 'autokill timeout, stopping recording'
                        self.mode = 'stop'
                        
                if DEBUG: print('Record_Thread::run: past wait()!!')

                rc.post_event(Event(OS_EVENT_KILL, (self.app.child.pid, 15)))
                self.app.kill()

                self.mode = 'idle'

                rc.post_event(Event('RECORD_STOP', arg=self.prog))
                if DEBUG: print('Record_Thread::run: finished recording')
                
            else:
                self.mode = 'idle'
            time.sleep(0.5)

