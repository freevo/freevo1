# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# record.py - the Freevo DVBStreamer Recording module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Only supports DVBStreamer instance on localhost.
#
# Todo:        
#
#
# -----------------------------------------------------------------------
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


import time
import os
import re
import copy
import sys
import threading
from socket import *

import config     # Configuration handler. reads config file.
import util
import childapp
import rc
import util.tv_util as tv_util

from tv.channels import FreevoChannels

from event import *
import plugin
from tv.plugins.dvbstreamer.manager import DVBStreamerManager

DEBUG=config.DEBUG

class PluginInterface(plugin.Plugin):
    """
    DVBStreamer plugin use the dvbstreamer application to minimise channel change time.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)
        _debug_('dvbstreamer plugin starting')

        # Create DVBStreamer objects
        username = 'dvbstreamer'
        password = 'control'
        
        try:
            username = config.DVBSTREAMER_USERNAME
            password = config.DVBSTREAMER_PASSWORD
        except:
            pass
 
        manager = DVBStreamerManager(username, password)
        
        # register the DVBStreamer record
        plugin.register(Recorder(manager), plugin.RECORD)

    def config(self):
        return [
                ('DVBSTREAMER_USERNAME', 'dvbstreamer', 'Username to use when connecting to a DVBStreamer server'),
                ('DVBSTREAMER_PASSWORD', 'control', 'Password to use when connecting to a DVBStreamer server')
                ]
    
    
###############################################################################
# Recorder
###############################################################################

class Recorder:
    """
    Class to record to file using dvbstreamer.
    """
    
    def __init__(self, manager):
        """
        Initialise the recorder passing in the DVBStreamerControl object to use to
        control instances of dvbstreamer.
        """
        # Disable this plugin if not loaded by record_server.
        if sys.argv[0].find('recordserver') == -1:
            return

        self.fc = FreevoChannels()
        self.thread = Record_Thread(manager)
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()
        

    def Record(self, rec_prog):
        """
        Start recording the specified program.
        """
        self.thread.prog = rec_prog
        self.thread.mode = 'record'
        self.thread.mode_flag.set()
        
    def Stop(self):
        """
        Stop recording.
        """
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()


class Record_Thread(threading.Thread):
    """
    Thread class that actually does the recording.
    """
    
    def __init__(self, manager):
        """
        Initialise the recording thread passing in the DVBStreamerControl object to use to
        control instances of dvbstreamer.
        """
        threading.Thread.__init__(self)
        self.fc = FreevoChannels()
        self.manager = manager
        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.prog = None
        self.app = None


    def run(self):
        """
        Thread loop.
        """
        while 1:
            if DEBUG: print('Record_Thread::run: mode=%s' % self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()
                
            elif self.mode == 'record':
                rc.post_event(Event('RECORD_START', arg=self.prog))
                if DEBUG: print('Record_Thread::run: started recording')
                
                prog = self.prog
                filename = tv_util.getProgFilename(prog)
                vg = self.fc.getVideoGroup(prog.channel_id, False)
                adapter = int(vg.vdev)
                seconds = prog.rec_duration
                # Select the channel and start streaming to the file.
                self.manager.select(adapter, prog.tunerid)
                self.manager.enable_file_output(adapter,filename)
                
                while (self.mode == 'record') and (seconds > 0):
                    seconds -= 0.5
                    time.sleep(0.5)
                    
                # Close the file
                self.manager.disable_output(adapter)
                
                rc.post_event(Event('RECORD_STOP', arg=self.prog))
                if DEBUG: print('Record_Thread::run: finished recording')

                self.mode = 'idle'
            else:
                self.mode = 'idle'
            time.sleep(0.5)
