# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ivtv_record.py - A plugin to record tv using an ivtv based card.
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


import sys, string
import random
import time, os
import threading
import signal

import config
import tv.ivtv
import childapp
import plugin
import rc
import util.tv_util as tv_util

from event import Event
from tv.channels import FreevoChannels
import tv.v4l2 as V4L2


CHUNKSIZE = 65536


class PluginInterface(plugin.Plugin):
    """
    A plugin to record tv using an ivtv based card
    """

    def __init__(self):
        plugin.Plugin.__init__(self)
        plugin.register(Recorder(), plugin.RECORD)


class Recorder:

    def __init__(self):
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        _debug_('ACTIVATING IVTV RECORD PLUGIN', DINFO)

        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()


    def Record(self, rec_prog):
        # It is safe to ignore config.TV_RECORD_FILE_SUFFIX here.
        rec_prog.filename = os.path.splitext(tv_util.getProgFilename(rec_prog))[0] + '.mpeg'

        self.thread.mode = 'record'
        self.thread.prog = rec_prog
        self.thread.mode_flag.set()

        _debug_('Recorder::Record: %s' % rec_prog, DINFO)


    def Stop(self):
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()



class Record_Thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)

        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.prog = None
        self.app = None


    def run(self):
        while 1:
            _debug_('Record_Thread::run: mode=%s' % self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()

            elif self.mode == 'record':
                rc.post_event(Event('RECORD_START', arg=self.prog))
                _debug_('Record_Thread::run: started recording', DINFO)

                fc = FreevoChannels()
                _debug_('CHAN: %s' % fc.getChannel())

                (v_norm, v_input, v_clist, v_dev) = config.TV_SETTINGS.split()

                v = tv.ivtv.IVTV(v_dev)

                v.init_settings()
                vg = fc.getVideoGroup(self.prog.tunerid, False)

                _debug_('Setting Input to %s' % vg.input_num)
                v.setinput(vg.input_num)

                cur_std = v.getstd()
                try:
                    new_std = V4L2.NORMS.get(vg.tuner_norm)
                    if cur_std != new_std:
                        v.setstd(new_std)
                except:
                    _debug_("Videogroup norm value '%s' not from NORMS: %s" % \
                        (vg.tuner_norm, V4L2.NORMS.keys()), DERROR)
                _debug_('Setting Channel to %s' % self.prog.tunerid)
                fc.chanSet(str(self.prog.tunerid), False)

                if vg.cmd != None:
                    _debug_("run cmd: %s" % vg.cmd)
                    retcode=os.system(vg.cmd)
                    _debug_("exit code: %g" % retcode)

                _debug_('%s' % v.print_settings())

                now = time.time()
                stop = now + self.prog.rec_duration

                time.sleep(2)

                v_in  = open(v_dev, 'r')
                v_out = open(self.prog.filename, 'w')

                while time.time() < stop:
                    buf = v_in.read(CHUNKSIZE)
                    v_out.write(buf)
                    if self.mode == 'stop':
                        break

                v_in.close()
                v_out.close()
                v.close()
                v = None

                self.mode = 'idle'

                rc.post_event(Event('RECORD_STOP', arg=self.prog))
                _debug_('Record_Thread::run: finished recording', DINFO)

            else:
                self.mode = 'idle'

            time.sleep(0.5)
