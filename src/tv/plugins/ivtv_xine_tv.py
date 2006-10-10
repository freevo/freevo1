# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ivtv_xine_tv.py - Implementation of live tv timeshift for ivtv
# -----------------------------------------------------------------------
# $Id: mplayer.py 8338 2006-10-09 21:47:47Z duncan $
#
# Notes:
# Author: thehog@t3i.nl
# Todo:        
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
# -----------------------------------------------------------------------


import config

import time, os
import threading
import signal
import skin

import rc
import util
import plugin
import childapp
import tv.ivtv as ivtv
import tv.epg_xmltv as epg

from event import *
from gui.AlertBox import AlertBox
from tv.channels import FreevoChannels

DEBUG = config.DEBUG

TRUE = 1
FALSE = 0

class PluginInterface(plugin.Plugin):
    """
    Plugin to watch tv with xine.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)
        plugin.register(IVTV_XINE_TV(), plugin.TV)


class IVTV_XINE_TV:

    def __init__(self):

        self.xine = XineThread()
        self.xine.setDaemon(1)
        self.xine.start()

        self.tuner = TunerControl()
        self.mixer = MixerControl()

        self.app_mode = 'tv'
        self.app = None
        self.videodev = None


    def Play(self, mode, tuner_channel=None, channel_change=0):

        _debug_('PLAY CHAN: %s' % tuner_channel)

        self.mode = mode

        self.prev_app = rc.app()
        rc.app(self)

        self.tuner.SetChannel(mode, tuner_channel)
        self.mixer.prepare()
        self.xine.play()

        # Suppress annoying audio clicks
        time.sleep(0.4)
        self.mixer.start()

        _debug_('%s: started %s app' % (time.time(), self.mode))


    def Pause(self):

        self.xine.pause()


    def Stop(self):

        self.mixer.stop()
        self.xine.stop()
        rc.app(self.prev_app)
        rc.post_event(PLAY_END)

        _debug_('stopped %s app' % self.mode)


    def eventhandler(self, event, menuw=None):

        _debug_('%s: %s app got %s event' % (time.time(), self.mode, event))
        s_event = '%s' % event

        if event == STOP or event == PLAY_END:
            self.Stop()
            return True

        if event == PAUSE or event == PLAY:
            self.Pause()
            return True

        if event in [ TV_CHANNEL_UP, TV_CHANNEL_DOWN] or s_event.startswith('INPUT_'):

            if event == TV_CHANNEL_UP:
                self.tuner.NextChannel()

            elif event == TV_CHANNEL_DOWN:
                self.tuner.PrevChannel()

            else:
                self.tuner.TuneChannel( int(s_event[6]) )

            #cmd = 'osd_show_text "%s"\n' % "CHANNEL CHANGE!"
            #self.xine.app.write(cmd)

            return True


        if event == SEEK:

            pos = int(event.arg)

            if pos < 0:
                action='SeekRelative-'
                pos = 0 - pos

            else:
                action='SeekRelative+'

            if pos <= 15:
                pos = 15

            elif pos <= 30:
                pos = 30

            else:
                pos = 30

            self.xine.app.write('%s%s\n' % (action, pos))
            return TRUE

        if event == TOGGLE_OSD:
            self.xine.app.write('OSDStreamInfos\n')
            return True

# ======================================================================

class TunerControl:

    def __init__(self):

        self.current_vgrp = None
        self.fc = FreevoChannels()
        self.current_chan = 0 # Current channel, index into config.TV_CHANNELS


    def SetChannel(self, mode, channel=None):

        if (channel == None):
            self.current_chan = self.fc.getChannel()

        else:
            self.current_chan = -1

            try:
                for pos in range(len(config.TV_CHANNELS)):
                    entry = config.TV_CHANNELS[pos]
                    if channel == entry[2]:
                        channel_index = pos
                        self.current_chan = channel
                        break

            except ValueError:
                pass

            if (self.current_chan == -1):
                _debug_("ERROR: Cannot find tuner channel '%s' in the TV channel listing" % channel)
                self.current_chan = 0
                channel_index = 0

        _debug_('PLAY CHAN: %s' % self.current_chan)

        vg = self.current_vgrp = self.fc.getVideoGroup(self.current_chan, True)
        _debug_('PLAY GROUP: %s' % vg.desc)

        if (mode == 'tv') and (vg.group_type == 'ivtv'):
            ivtv_dev = ivtv.IVTV(vg.vdev)
            ivtv_dev.init_settings()
            ivtv_dev.setinput(vg.input_num)
            ivtv_dev.print_settings()
            self.TuneChannel(channel_index + 1)

        else:
            _debug_('Mode "%s" is not implemented' % mode)
            pop = AlertBox(text=_('This plugin only supports the ivtv video group in tv mode!'))
            pop.show()
            return


    def NextChannel(self):
        nextchan = self.fc.getNextChannel()
        self.SetVideoGroup(nextchan)


    def PrevChannel(self):
        nextchan = self.fc.getPrevChannel()
        self.SetVideoGroup(nextchan)


    def TuneChannel(self, chan):
        nextchan = self.fc.getManChannel(chan)
        self.SetVideoGroup(nextchan)


    def SetVideoGroup(self, chan):
        _debug_('CHAN: %s' % chan)
        vg = self.fc.getVideoGroup(chan, True)
        _debug_('GROUP: %s' % vg.desc)

        if self.current_vgrp != vg:
            # XXX HANDLE THIS
            self.Stop(channel_change=1)
            self.Play('tv', nextchan)
            return

        #if self.mode == 'vcr':
        #    # XXX HANDLE THIS
        #    return

        if self.current_vgrp.group_type == 'ivtv':
            self.fc.chanSet(chan, True)
            #self.xine.app.write('seek 999999 0\n')

        else:
            freq_khz = self.fc.chanSet(chan, True, app=self.xine.app)
            new_freq = '%1.3f' % (freq_khz / 1000.0)
            #self.xine.app.write('tv_set_freq %s\n' % new_freq)

        self.current_vgrp = self.fc.getVideoGroup(self.fc.getChannel(), True)

        # Display a channel changed message (mplayer ? api osd xine ?)
        tuner_id, chan_name, prog_info = self.fc.getChannelInfo()
        now = time.strftime('%H:%M')
        msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
        cmd = 'osd_show_text "%s"\n' % msg
        #self.xine.app.write(cmd)


    def GetChannelInfo(self):

        '''Get program info for the current channel'''

        tuner_id = config.TV_CHANNELS[self.current_chan][2]
        chan_name = config.TV_CHANNELS[self.current_chan][1]
        chan_id = config.TV_CHANNELS[self.current_chan][0]

        channels = epg.get_guide().GetPrograms(
            start=time.time(),
            stop=time.time(), chanids=[chan_id]
        )

        if channels and channels[0] and channels[0].programs:
            start_s = time.strftime('%H:%M', time.localtime(channels[0].programs[0].start))
            stop_s = time.strftime('%H:%M', time.localtime(channels[0].programs[0].stop))
            ts = '(%s-%s)' % (start_s, stop_s)
            prog_info = '%s %s' % (ts, channels[0].programs[0].title)

        else:
            prog_info = 'No info'

        return tuner_id, chan_name, prog_info


#    def GetChannel(self):

#        return config.TV_CHANNELS[self.current_chan][2]


#    def NextChannel(self):

#        self.current_chan = (self.current_chan+1) % len(config.TV_CHANNELS)


#    def PrevChannel(self):

#        self.current_chan = (self.current_chan-1) % len(config.TV_CHANNELS)


# ======================================================================

class MixerControl:

    # XXX Mixer manipulation code.
    # TV is on line in
    # VCR is mic in
    # btaudio (different dsp device) will be added later

    def __init__(self):

        self.mixer = plugin.getbyname('MIXER')
        self.volume = 0

    def prepare(self):

        if (self.mixer != None):

            if config.MAJOR_AUDIO_CTRL == 'VOL':
                self.volume = self.mixer.getMainVolume()
                self.mixer.setMainVolume(0)

            elif config.MAJOR_AUDIO_CTRL == 'PCM':
                self.volume = self.mixer.getPcmVolume()
                self.mixer.setPcmVolume(0)

    def start(self):


        if (self.mixer != None):

            # XXX Hm.. This is hardcoded and very unflexible.
            if self.mode == 'vcr':
                self.mixer.setMicVolume(config.VCR_IN_VOLUME)

            else:
                self.mixer.setLineinVolume(config.TV_IN_VOLUME)
                self.mixer.setIgainVolume(config.TV_IN_VOLUME)

            if config.MAJOR_AUDIO_CTRL == 'VOL':
                self.mixer.setMainVolume(self.volume)

            elif config.MAJOR_AUDIO_CTRL == 'PCM':
                self.mixer.setPcmVolume(self.volume)


    def stop(self):

        if (self.mixer != None):
            self.mixer.setLineinVolume(0)
            self.mixer.setMicVolume(0)
            self.mixer.setIgainVolume(0) # Input on emu10k cards.


# ======================================================================


class XineApp(childapp.ChildApp2):
    """
    class controlling the in and output from the xine process
    """

    def __init__(self, app, item):

        self.item = item
        childapp.ChildApp2.__init__(self, app)
        _debug_('XineApp: Started, cmd=%s' % app)
        # self.exit_type = None # ??


# ======================================================================


class XineThread(threading.Thread):
    """
    Thread to wait for a xine command to play
    """

    def __init__(self):

        threading.Thread.__init__(self)

        self.app = None
        self.item = None
        self.mode = 'idle'
        self.start_flag = threading.Event()

        print 'DJW: config.CONF.xine=%s' % (config.CONF.xine)
        print 'DJW: config.XINE_COMMAND=%s' % (config.XINE_COMMAND)
        print 'DJW: config.XINE_ARGS_DEF=%s' % (config.XINE_ARGS_DEF)
        print 'DJW: config.XINE_TV_VO_DEV=%s' % (config.XINE_TV_VO_DEV)
        print 'DJW: config.XINE_TV_AO_DEV=%s' % (config.XINE_TV_AO_DEV)
        print 'DJW: config.XINE_TV_TIMESHIFT_FILEMASK=%s' % (config.XINE_TV_TIMESHIFT_FILEMASK)
        self.command = '%s %s -V %s -A %s --stdctl pvr://%s' % (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_VO_DEV, config.XINE_TV_AO_DEV, config.XINE_TV_TIMESHIFT_FILEMASK)

    def play(self):

        if (self.mode == 'idle'):
            self.start_flag.set()

    def pause(self):

        if (self.mode == 'busy') or (self.mode == 'pause'):
            self.mode = 'pause'

    def stop(self):

        if (self.mode == 'busy') or (self.mode == 'pause'):
            self.mode = 'stop'

        while (self.mode == 'busy') or (self.mode == 'pause'):
            sleep(0.1)


    def run(self):

        while 1:

            if self.mode == 'idle':
                self.start_flag.wait()
                self.start_flag.clear()

            else:
                _debug_("XineThread: Should be idle on thread entry!")

            self.app = XineApp(self.command, self.item)
            self.mode = 'busy'

            while self.app.isAlive():

                if self.mode == 'busy':
                    time.sleep(0.1)

                elif self.mode == 'pause':
                    self.app.write('pause\n')
                    self.mode = 'busy'

                elif self.mode == 'stop':
                    self.app.stop("quit\n")


            self.mode = 'idle'

            _debug_('XineThread: Stopped')
            self.mode = 'idle'
