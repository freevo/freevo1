# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo module to handle channel changing.
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
logger = logging.getLogger("freevo.tv.channels")


import threading
import time
import os

import config, plugin
import tv.freq, tv.v4l2
import epg_xmltv

CHANNEL_ID = 0
DISPLAY_NAME = 1
TUNER_ID = 2


# Sample for local_conf.py:
# Three video cards and one web camera.
#TV_VIDEO_GROUPS = [
#    VideoGroup(vdev='/dev/video0',
#               adev=None,
#               input_type='tuner',
#               tuner_type='external',
#               tuner_chan='3',
#               desc='Bell ExpressVu (for playing)',
#               record_group=1),
#    VideoGroup(vdev='/dev/video1',
#               adev=None,
#               input_type='tuner',
#               tuner_type='external',
#               tuner_chan='3',
#               desc='Bell ExpressVu (for recording)',
#               record_group=None),
#    VideoGroup(vdev='/dev/video2',
#               adev='/dev/dsp1',
#               input_type='tuner',
#               desc='ATI TV-Wonder (both playing and recording)',
#               record_group=None),
#    VideoGroup(vdev='/dev/video3',
#               adev=None,
#               input_type='webcam',
#               desc='Logitech Quickcam',
#               record_group=None),
#]

class FreevoChannels:

    def __init__(self):
        logger.log( 9, 'FreevoChannels.__init__()')
        self.chan_index = 0
        self.lock = threading.Lock()

        if config.plugin_external_tuner:
            plugin.init_special_plugin(config.plugin_external_tuner)


    def _findVideoGroup(self, chan, isplayer, chan_index):
        """
        Find the VideoGroup number used by this Freevo channel.
        """
        group = 0
        for i in range(len(config.TV_CHANNELS)):
            chan_info = config.TV_CHANNELS[i]
            if chan_info[chan_index] == chan:
                try:
                    group = int(chan_info[4])
                except (IndexError, ValueError):
                    pass
                break
        else: # Channel not found
            #DJW this should be noticed
            import traceback
            traceback.print_stack()

        return group


    def getVideoGroup(self, chan, isplayer, chan_index=TUNER_ID):
        """
        Gets the VideoGroup object used by this Freevo channel.
        """
        logger.debug('getVideoGroup(chan=%r, isplayer=%r, chan_index=%r)', chan, isplayer, chan_index)

        vg = config.TV_VIDEO_GROUPS[0]

        self.lock.acquire()
        try:
            try:
                channel = int(chan)
                if channel <= 0: # channels start at 1
                    group = -channel
                else:
                    group = self._findVideoGroup(chan, isplayer, chan_index)
            except ValueError:
                group = self._findVideoGroup(chan, isplayer, chan_index)

            vg = config.TV_VIDEO_GROUPS[group]
            if not isplayer:
                record_group = vg.record_group
                if record_group:
                    try:
                        # some simple checks
                        vg = config.TV_VIDEO_GROUPS[int(record_group)]
                    except:
                        logger.warning('TV_VIDEO_GROUPS[%s].record_group=%s is invalid', group, record_group)
        finally:
            self.lock.release()

        return vg


    def chanUp(self, isplayer, app=None, app_cmd=None):
        """
        Using this method will not support custom frequencies.
        """
        logger.log( 9, 'chanUp(isplayer=%r, app=%r, app_cmd=%r)', isplayer, app, app_cmd)
        return self.chanSet(self.getNextChannel(), isplayer, app, app_cmd)


    def chanDown(self, isplayer, app=None, app_cmd=None):
        """
        Using this method will not support custom frequencies.
        """
        logger.log( 9, 'chanDown(isplayer=%r, app=%r, app_cmd=%r)', isplayer, app, app_cmd)
        return self.chanSet(self.getPrevChannel(), isplayer, app, app_cmd)


    def chanSet(self, chan, isplayer, app=None, app_cmd=None):
        logger.log( 9, 'chanSet(char=%r, isplayer=%r, app=%r, app_cmd=%r)', chan, isplayer, app, app_cmd)
        new_chan = None

        dup_dict = dict()
        for pos in range(len(config.TV_CHANNELS)):
            chan_cfg = config.TV_CHANNELS[pos]
            if str(chan_cfg[2]) == str(chan):
                dup_dict[str(pos)] = chan_cfg
                new_chan = chan
                self.chan_index = pos

        if not new_chan:
            logger.warning('Cannot find tuner channel "%s" in the TV channel listing', chan)
            return

        # Trying to choose the correct TV_CHANNELS if the channel is in more than one line
        if len(dup_dict) > 1 and new_chan >= 0:
            # Normally, negative channels are for external tuners, don't care ... yet !
            cwday = time.localtime()[6] + 1
            ctime = str(time.localtime()[3]) + str(time.localtime()[4])
            # check if some lines can be removed from dup_dict
            for key in dup_dict.keys():
                swday  = '1234567'
                sstime = '0000'
                setime = '2359'
                if len(dup_dict[key]) > 3:
                    cal = dup_dict[key][3]
                    if len(cal) > 0:
                        swday = cal[0]
                    if len(cal) > 1:
                        sstime = cal[1]
                    if len(cal) > 2:
                        setime = cal[2]

                if swday.count(str(cwday)) == 0: # current day is not in the schedule
                    del dup_dict[key]
                else:
                    if (sstime > setime and (ctime > setime and ctime < sstime)) \
                    or (sstime < setime and (ctime < sstime or ctime > setime)):
                        # current time not in this schedule
                        del dup_dict[key]

            if len(dup_dict) > 1:
                logger.warning('At current day/time (%s, %s), still %s active TV_Channels for channel %s', cwday, ctime, len(dup_dict), chan)


            for key in dup_dict.keys():
                self.chan_index = int(key)

        vg = self.getVideoGroup(new_chan, isplayer)
        if vg.tuner_type == 'external':
            tuner = plugin.getbyname('EXTERNAL_TUNER')
            if tuner:
                tuner.setChannel(new_chan)

            if vg.input_type == 'tuner' and vg.tuner_chan:
                freq = self.tunerSetFreq(vg.tuner_chan, app, app_cmd)
                return freq

            return 0
        return self.tunerSetFreq(chan, isplayer, app, app_cmd)


    def tunerSetFreq(self, chan, isplayer, app=None, app_cmd=None):
        logger.log( 9, 'tunerSetFreq(chan=%r, isplayer=%r, app=%r, app_cmd=%r', chan, isplayer, app, app_cmd)
        chan = str(chan)
        vg = self.getVideoGroup(chan, isplayer)

        freq = config.TV_FREQUENCY_TABLE.get(chan)
        if freq:
            logger.debug('Using custom frequency: chan="%s", freq="%s"', chan, freq)
        else:
            clist = tv.freq.CHANLIST.get(vg.tuner_chanlist)
            if clist:
                freq = clist.get(chan)
            else:
                if vg.group_type != 'dvb':
                    logger.warning('Unable to get channel list for %s.', vg.tuner_chanlist)
                return 0
            if not freq:
                if vg.group_type != 'dvb':
                    logger.warning('Unable to get channel list for %s.', vg.tuner_chanlist)
                return 0
            logger.debug('USING STANDARD FREQUENCY: chan="%s", freq="%s"', chan, freq)

        if app:
            if app_cmd:
                self.appSend(app, app_cmd)
            else:
                # If we have app and not app_cmd we return the frequency so
                # the caller (ie: mplayer/tvtime/mencoder plugin) can set it
                # or provide it on the command line.
                return freq
        else:
            # XXX: add code here for TUNER_LOW capability, the last time that I
            #      half-heartedly tried this it din't work as expected.
            # XXX Moved here by Krister, only return actual values
            freq *= 16
            freq /= 1000

            # Lets set the freq ourselves using the V4L device.
            try:
                vd = tv.v4l2.Videodev(vg.vdev)

                try:
                    vd.setinputbyname(vg.input_type)
                except KeyError:
                    logger.warning('Cannot set input %r for %r, must be one of:\n%r', vg.input_type, vg.vdev, vd.inputs.keys())


                try:
                    vd.setstdbyname(vg.tuner_norm)
                except KeyError:
                    logger.warning('Cannot set standard %r for %r, must be one of:\n%r', vg.tuner_norm, vg.vdev, vd.standards.keys())


                try:
                    vd.setfreq(freq)
                except:
                    vd.setfreq_old(freq)

                vd.close()
            except Exception, e:
                logger.warning('Cannot set frequency for %s/%s/%s: %s', vg.input_type, vg.tuner_norm, chan, e)

            if vg.cmd:
                logger.debug('run cmd: %s', vg.cmd)
                retcode = os.system(vg.cmd)
                logger.debug('exit code: %g', retcode)

        return 0


    def getChannel(self):
        logger.log( 9, 'getChannel()')
        return config.TV_CHANNELS[self.chan_index][2]


    def getChannelNum(self):
        logger.log( 9, 'getChannelNum()')
        return (self.chan_index) % len(config.TV_CHANNELS)


    def getManChannelNum(self, channel=0, tvlike=0):
        logger.log( 9, 'getManChannelNum(channel=%r)', channel)
        if tvlike:
            physchan = '9999'
            key = channel
            for pos in range(len(config.TV_CHANNELS)):
                if pos == channel -1:
                    key = channel
                if config.TV_CHANNELS[pos][2] == physchan:
                    channel = channel + 1
                physchan = config.TV_CHANNELS[pos][2]
            if key > len(config.TV_CHANNELS) + 1:
                key = len(config.TV_CHANNELS) + 1
            return key-1
        else:
            return (channel-1) % len(config.TV_CHANNELS)

    def getNextChannelNum(self):
        logger.log( 9, 'getNextChannelNum()')
        curnum=self.chan_index
        curchan=config.TV_CHANNELS[curnum][2]
        while config.TV_CHANNELS[curnum][2] == curchan:
            curnum = (curnum + 1) % len(config.TV_CHANNELS)
        return curnum


    def getPrevChannelNum(self):
        logger.log( 9, 'getPrevChannelNum()')
        curnum=self.chan_index
        curchan=config.TV_CHANNELS[curnum][2]
        while config.TV_CHANNELS[curnum][2] == curchan:
            curnum = (curnum - 1) % len(config.TV_CHANNELS)
        return curnum


    def getManChannel(self, channel=0, tvlike=0):
        logger.log( 9, 'getManChannel(channel=%r)', channel)
        return config.TV_CHANNELS[self.getManChannelNum(channel, tvlike)][2]


    def getNextChannel(self):
        logger.log( 9, 'getNextChannel()')
        return config.TV_CHANNELS[self.getNextChannelNum()][2]


    def getPrevChannel(self):
        logger.log( 9, 'getPrevChannel()')
        return config.TV_CHANNELS[self.getPrevChannelNum()][2]


    def setChanlist(self, chanlist):
        logger.log( 9, 'setChanlist(chanlist=%r)', chanlist)
        self.chanlist = freq.CHANLIST[chanlist]


    def appSend(self, app, app_cmd):
        logger.log( 9, 'appSend(app=%r, app_cmd=%r)', app, app_cmd)
        if not app or not app_cmd:
            return
        app.write(app_cmd)


    def getChannelInfo(self, showtime=True):
        """Get program info for the current channel"""
        logger.log( 9, 'getChannelInfo(showtime=%r)', showtime)

        tuner_id = self.getChannel()
        chan_name = config.TV_CHANNELS[self.chan_index][1]
        chan_id = config.TV_CHANNELS[self.chan_index][0]

        channels = epg_xmltv.get_guide().get_programs(time.time(), time.time(), chan_id)

        if channels and channels[0] and channels[0].programs:
            if showtime:
                start_s = time.strftime(config.TV_TIME_FORMAT, time.localtime(channels[0].programs[0].start))
                stop_s = time.strftime(config.TV_TIME_FORMAT, time.localtime(channels[0].programs[0].stop))
                ts = '(%s-%s)' % (start_s, stop_s)
                prog_info = '%s %s' % (ts, channels[0].programs[0].title)
            else:
                prog_info = channels[0].programs[0].title
        else:
            prog_info = 'No info'

        return tuner_id, chan_name, prog_info


    def getChannelInfoRaw(self):
        """Get program info for the current channel"""
        logger.log( 9, 'getChannelInfoRaw()')

        tuner_id = self.getChannel()
        chan_name = config.TV_CHANNELS[self.chan_index][1]
        chan_id = config.TV_CHANNELS[self.chan_index][0]

        channels = epg_xmltv.get_guide().get_programs(time.time(), time.time(), chan_id)

        if channels and channels[0] and channels[0].programs:
            start_t = channels[0].programs[0].start
            stop_t = channels[0].programs[0].stop
            prog_s = channels[0].programs[0].title
        else:
            start_t = 0
            stop_t = 0
            prog_s = 'No info'

        return tuner_id, chan_id, chan_name, start_t, stop_t, prog_s


if __name__ == '__main__':
    fc = FreevoChannels()
    print 'CHAN: %s' % fc.getChannel()
    fc.chanSet('K35', True)
    print 'CHAN: %s' % fc.getChannel()
    fc.chanSet('K35', False)
    print 'CHAN: %s' % fc.getChannel()
