# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to record tv using an ivtv based card.
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
        _debug_('PluginInterface.__init__()', 2)
        plugin.Plugin.__init__(self)
        plugin.register(Recorder(), plugin.RECORD)


class Recorder:

    def __init__(self):
        _debug_('Recorder.__init__()', 2)
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        _debug_('ACTIVATING IVTV RECORD PLUGIN', DINFO)

        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()


    def Record(self, rec_prog):
        _debug_('Record(rec_prog=%r)' % (rec_prog), 2)
        # It is safe to ignore config.TV_RECORD_FILE_SUFFIX here.
        rec_prog.filename = os.path.splitext(tv_util.getProgFilename(rec_prog))[0] + '.mpeg'

        self.thread.mode = 'record'
        self.thread.prog = rec_prog
        self.thread.mode_flag.set()
        _debug_('Recorder::Record: %s' % rec_prog, DINFO)


    def Stop(self):
        _debug_('Stop()', 2)
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()



class Record_Thread(threading.Thread):

    def __init__(self):
        _debug_('Record_Thread.__init__()', 2)
        threading.Thread.__init__(self)

        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.prog = None
        self.app = None


    def run(self):
        _debug_('Record_Thread.run()', 2)
        while 1:
            _debug_('Record_Thread::run: mode=%s' % self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()

            elif self.mode == 'record':
                try:
                    _debug_('Record_Thread::run: started recording', DINFO)

                    fc = FreevoChannels()
                    _debug_('Channel: %s' % (fc.getChannel()))

                    vg = fc.getVideoGroup(self.prog.tunerid, False)

                    _debug_('Opening device %r' % (vg.vdev))
                    v = tv.ivtv.IVTV(vg.vdev)

                    v.init_settings()

                    _debug_('Setting input to %r' % (vg.input_type))
                    v.setinputbyname(vg.input_type)

                    cur_std = v.getstd()
                    try:
                        new_std = V4L2.NORMS.get(vg.tuner_norm)
                        if cur_std != new_std:
                            _debug_('Setting standard to %s' % (new_std))
                            v.setstd(new_std)
                    except:
                        _debug_("Videogroup norm value '%s' not from NORMS: %s" % \
                            (vg.tuner_norm, V4L2.NORMS.keys()), DERROR)

                    _debug_('Setting channel to %r' % self.prog.tunerid)
                    fc.chanSet(str(self.prog.tunerid), False)

                    # Setting the input sound level on the PVR card
                    channel = self.prog.tunerid
                    try:
                        # lookup the channel name in TV_CHANNELS
                        for pos in range(len(config.TV_CHANNELS)):
                            entry = config.TV_CHANNELS[pos]
                            if str(channel) == str(entry[2]):
                                channel_index = pos
                                break
                    except ValueError:
                        pass

                    _debug_('SetAudioByChannel: Channel: %r TV_CHANNEL pos(%d)' % (channel, channel_index))
                    try:
                        ivtv_avol = vg.avol
                    except AttributeError:
                        ivtv_avol = 0
                    if ivtv_avol <= 0:
                        _debug_('SetAudioByChannel: The tv_video group for %r doesn\'t set the volume' % channel)
                    else:
                        # Is there a specific volume level in TV_CHANNELS_VOLUME
                        avol_percent = 100
                        try:
                            # lookup the channel name in TV_CHANNELS
                            for pos in range(len(config.TV_CHANNELS_VOLUME)):
                                if config.TV_CHANNELS_VOLUME[pos][0] == config.TV_CHANNELS[channel_index][0]:
                                    avol_percent = config.TV_CHANNELS_VOLUME[pos][1]
                                    break
                        except:
                            pass

                        try:
                            avol_percent = int(avol_percent)
                        except ValueError:
                            avol_percent = 100

                        avol = int(ivtv_avol * avol_percent / 100)
                        if avol > 65535:
                            avol = 65535
                        if avol < 0:
                            avol = 0
                        _debug_('SetAudioByChannel: Current PVR Sound level is : %s' % v.getctrl(0x00980905))
                        _debug_('SetAudioByChannel: Set the PVR Sound Level to : %s (%s * %s)' % (avol, ivtv_avol, avol_percent))
                        v.setctrl(0x00980905, avol)
                        _debug_('SetAudioByChannel: New PVR Sound level is : %s' % v.getctrl(0x00980905))

                    if vg.cmd != None:
                        _debug_("Running command %r" % vg.cmd)
                        retcode = os.system(vg.cmd)
                        _debug_("exit code: %g" % retcode)

                    now = time.time()
                    stop = now + self.prog.rec_duration

                    rc.post_event(Event('RECORD_START', arg=self.prog))
                    time.sleep(2)

                    v_in  = open(vg.vdev, 'r')
                    v_out = open(self.prog.filename, 'w')

                    _debug_('Recording from %r to %r in %s byte chunks' % (vg.vdev, self.prog.filename, CHUNKSIZE))
                    while time.time() < stop:
                        buf = v_in.read(CHUNKSIZE)
                        v_out.write(buf)
                        if self.mode == 'stop':
                            _debug_('Recording stopped', DINFO)
                            break

                    v_in.close()
                    v_out.close()
                    v.close()
                    v = None

                    self.mode = 'idle'

                    rc.post_event(Event('RECORD_STOP', arg=self.prog))
                    _debug_('Record_Thread::run: finished recording', DINFO)
                except Exception, why:
                    _debug_('%s' % (why), DCRITICAL)
                    return

            else:
                self.mode = 'idle'

            time.sleep(0.5)
