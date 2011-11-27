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
import logging
logger = logging.getLogger("freevo.tv.plugins.ivtv_record")


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
        logger.log( 9, 'PluginInterface.__init__()')
        plugin.Plugin.__init__(self)
        plugin.register(Recorder(), plugin.RECORD)


class Recorder:

    def __init__(self):
        logger.log( 9, 'Recorder.__init__()')
        # Disable this plugin if not loaded by record_server.
        if string.find(sys.argv[0], 'recordserver') == -1:
            return

        logger.info('ACTIVATING IVTV RECORD PLUGIN')

        self.thread = Record_Thread()
        self.thread.setDaemon(1)
        self.thread.mode = 'idle'
        self.thread.start()


    def Record(self, rec_prog):
        logger.log( 9, 'Record(rec_prog=%r)', rec_prog)
        # It is safe to ignore config.TV_RECORD_FILE_SUFFIX here.
        rec_prog.filename = os.path.splitext(tv_util.getProgFilename(rec_prog))[0] + '.mpeg'

        self.thread.mode = 'record'
        self.thread.prog = rec_prog
        self.thread.mode_flag.set()
        logger.info('Recorder::Record: %s', rec_prog)


    def Stop(self):
        logger.log( 9, 'Stop()')
        self.thread.mode = 'stop'
        self.thread.mode_flag.set()



class Record_Thread(threading.Thread):

    def __init__(self):
        logger.log( 9, 'Record_Thread.__init__()')
        threading.Thread.__init__(self)

        self.mode = 'idle'
        self.mode_flag = threading.Event()
        self.prog = None
        self.app = None


    def run(self):
        logger.log( 9, 'Record_Thread.run()')
        while 1:
            logger.debug('Record_Thread::run: mode=%s', self.mode)
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()

            elif self.mode == 'record':
                try:
                    logger.info('Record_Thread::run: started recording')

                    fc = FreevoChannels()
                    logger.debug('Channel: %s', fc.getChannel())

                    vg = fc.getVideoGroup(self.prog.tunerid, False)

                    logger.debug('Opening device %r', vg.vdev)
                    v = tv.ivtv.IVTV(vg.vdev)

                    v.init_settings()

                    logger.debug('Setting input to %r', vg.input_type)
                    v.setinputbyname(vg.input_type)

                    cur_std = v.getstd()
                    try:
                        new_std = V4L2.NORMS.get(vg.tuner_norm)
                        if cur_std != new_std:
                            logger.debug('Setting standard to %s', new_std)
                            v.setstd(new_std)
                    except:
                        logger.error("Videogroup norm value '%s' not from NORMS: %s", vg.tuner_norm, V4L2.NORMS.keys())


                    logger.debug('Setting channel to %r', self.prog.tunerid)
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

                    logger.debug('SetAudioByChannel: Channel: %r TV_CHANNEL pos(%d)', channel, channel_index)
                    try:
                        ivtv_avol = vg.avol
                    except AttributeError:
                        ivtv_avol = 0
                    if ivtv_avol <= 0:
                        logger.debug('SetAudioByChannel: The tv_video group for %r doesn\'t set the volume', channel)
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
                        logger.debug('SetAudioByChannel: Current PVR Sound level is : %s', v.getctrl(0x00980905))
                        logger.debug('SetAudioByChannel: Set the PVR Sound Level to : %s (%s * %s)', avol, ivtv_avol, avol_percent)
                        v.setctrl(0x00980905, avol)
                        logger.debug('SetAudioByChannel: New PVR Sound level is : %s', v.getctrl(0x00980905))

                    if vg.cmd != None:
                        logger.debug("Running command %r", vg.cmd)
                        retcode = os.system(vg.cmd)
                        logger.debug("exit code: %g", retcode)

                    now = time.time()
                    stop = now + self.prog.rec_duration

                    rc.post_event(Event('RECORD_START', arg=self.prog))
                    time.sleep(2)

                    v_in  = open(vg.vdev, 'r')
                    v_out = open(self.prog.filename, 'w')

                    logger.debug('Recording from %r to %r in %s byte chunks', vg.vdev, self.prog.filename, CHUNKSIZE)
                    while time.time() < stop:
                        buf = v_in.read(CHUNKSIZE)
                        v_out.write(buf)
                        if self.mode == 'stop':
                            logger.info('Recording stopped')
                            break

                    v_in.close()
                    v_out.close()
                    v.close()
                    v = None

                    self.mode = 'idle'

                    rc.post_event(Event('RECORD_STOP', arg=self.prog))
                    logger.info('Record_Thread::run: finished recording')
                except Exception, why:
                    logger.critical('%s', why)
                    return

            else:
                self.mode = 'idle'

            time.sleep(0.5)
