# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# channels.py - Freevo module to handle channel changing.
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


import config, plugin
import tv.freq, tv.v4l2
import epg_xmltv
import threading
import time


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
        self.chan_index = 0
        self.lock = threading.Lock()

        if config.plugin_external_tuner:
            plugin.init_special_plugin(config.plugin_external_tuner)


    def getVideoGroup(self, chan, isplayer):
        """
        Gets the VideoGroup object used by this Freevo channel.
        """
        self.lock.acquire()
        try:
            group = 0

            for i in range(len(config.TV_CHANNELS)):
                chan_info = config.TV_CHANNELS[i]
                if chan_info[2] == chan:
                    try:
                        group = int(chan_info[4])
                    except: # XXX: put a better exception here
                        group = 0
            if not isplayer:
                record_group = config.TV_VIDEO_GROUPS[group].record_group
                if record_group:
                    try:
                        # some simple checks
                        group = int(record_group)
                        record_vg = config.TV_VIDEO_GROUPS[group]
                    except:
                        print 'TV_VIDEO_GROUPS[%s].record_group=%s is invalid' % (group, record_group)
        finally:
            self.lock.release()

        return config.TV_VIDEO_GROUPS[group]


    def chanUp(self, isplayer, app=None, app_cmd=None):
        """
        Using this method will not support custom frequencies.
        """
        return self.chanSet(self.getNextChannel(), isplayer, app, app_cmd)


    def chanDown(self, isplayer, app=None, app_cmd=None):
        """
        Using this method will not support custom frequencies.
        """
        return self.chanSet(self.getPrevChannel(), isplayer, app, app_cmd)


    def chanSet(self, chan, isplayer, app=None, app_cmd=None):
        new_chan = None

        for pos in range(len(config.TV_CHANNELS)):
            chan_cfg = config.TV_CHANNELS[pos]
            if str(chan_cfg[2]) == str(chan):
                new_chan = chan
                self.chan_index = pos

        if not new_chan:
            print 'Cannot find tuner channel "%s" in the TV channel listing' % chan
            return

        vg = self.getVideoGroup(new_chan, isplayer)

        if vg.tuner_type == 'external':
            tuner = plugin.getbyname('EXTERNAL_TUNER')
            if tuner:
                tuner.setChannel(new_chan)

            if vg.input_type == 'tuner' and vg.tuner_chan:
                freq = self.tunerSetFreq(vg.tuner_chan, app, app_cmd)
                return freq

            return 0

        else:
            return self.tunerSetFreq(chan, isplayer, app, app_cmd)

        return 0


    def tunerSetFreq(self, chan, isplayer, app=None, app_cmd=None):
        _debug_('tunerSetFreq(chan=%r, isplayer=%r, app=%r, app_cmd=%r' % (chan, isplayer, app, app_cmd), 2)
        chan = str(chan)
        vg = self.getVideoGroup(chan, isplayer)

        freq = config.TV_FREQUENCY_TABLE.get(chan)
        if freq:
            _debug_('Using custom frequency: chan="%s", freq="%s"' % (chan, freq))
        else:
            clist = tv.freq.CHANLIST.get(vg.tuner_chanlist)
            if clist:
                freq = clist.get(chan)
            else:
                if vg.group_type != 'dvb':
                    print 'Unable to get channel list for %s.' % vg.tuner_chanlist
                return 0
            if not freq:
                if vg.group_type != 'dvb':
                    print 'Unable to get channel list for %s.' % vg.tuner_chanlist
                return 0
            _debug_('USING STANDARD FREQUENCY: chan="%s", freq="%s"' % (chan, freq))

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
                    print 'Cannot set input %r for %r, must be one of:\n%r' % \
                        (vg.input_type, vg.vdev, vd.inputs.keys())

                try:
                    vd.setstdbyname(vg.tuner_norm)
                except KeyError:
                    print 'Cannot set standard %r for %r, must be one of:\n%r' % \
                        (vg.tuner_norm, vg.vdev, vd.standards.keys())

                try:
                    vd.setfreq(freq)
                except:
                    vd.setfreq_old(freq)

                vd.close()
            except Exception, e:
                print 'Cannot set frequency for %s/%s/%s: %s' % (vg.input_type, vg.tuner_norm, chan, e)

            if vg.cmd:
                _debug_("run cmd: %s" % vg.cmd)
                import os
                retcode=os.system(vg.cmd)
                _debug_("exit code: %g" % retcode)

        return 0


    def getChannel(self):
        return config.TV_CHANNELS[self.chan_index][2]


    def getChannelNum(self):
        return (self.chan_index) % len(config.TV_CHANNELS)


    def getManChannelNum(self, channel=0):
        return (channel-1) % len(config.TV_CHANNELS)


    def getNextChannelNum(self):
        return (self.chan_index+1) % len(config.TV_CHANNELS)


    def getPrevChannelNum(self):
        return (self.chan_index-1) % len(config.TV_CHANNELS)


    def getManChannel(self, channel=0):
        return config.TV_CHANNELS[(channel-1) % len(config.TV_CHANNELS)][2]


    def getNextChannel(self):
        return config.TV_CHANNELS[(self.chan_index+1) % len(config.TV_CHANNELS)][2]


    def getPrevChannel(self):
        return config.TV_CHANNELS[(self.chan_index-1) % len(config.TV_CHANNELS)][2]


    def setChanlist(self, chanlist):
        self.chanlist = freq.CHANLIST[chanlist]


    def appSend(self, app, app_cmd):
        if not app or not app_cmd:
            return

        app.write(app_cmd)


    def getChannelInfo(self, showtime=True):
        '''Get program info for the current channel'''

        tuner_id = self.getChannel()
        chan_name = config.TV_CHANNELS[self.chan_index][1]
        chan_id = config.TV_CHANNELS[self.chan_index][0]

        channels = epg_xmltv.get_guide().GetPrograms(start=time.time(), stop=time.time(), chanids=[chan_id])

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


if __name__ == '__main__':
    fc = FreevoChannels()
    print 'CHAN: %s' % fc.getChannel()
    fc.chanSet('K35', True)
    print 'CHAN: %s' % fc.getChannel()
    fc.chanSet('K35', False)
    print 'CHAN: %s' % fc.getChannel()
