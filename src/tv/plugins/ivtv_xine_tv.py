# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ivtv_xine_tv.py - Implementation of live tv timeshift for ivtv
# -----------------------------------------------------------------------
# $Id$
#
# Author:
#   rvpaasen@t3i.nl (Richard van Paasen)
#
# Notes:
#   implements live TV for IVTV class TV cards
#   such as the Haupage PVR x50 series
#
# Todo:
#   - show OSD text once xine supports it
#     http://sourceforge.net/tracker/index.php?func=detail&aid=1631022&group_id=9655&atid=359655
#   - skip to end of buffer on channel change
#     http://sourceforge.net/tracker/index.php?func=detail&aid=1631019&group_id=9655&atid=359655
#   - toggle between live and record mode
#   - implement progressive/accelerated seek mode
#   - implement vcr mode
#
# -----------------------------------------------------------------------
#
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

# guard important config variables

if not config.XINE_TV_VO_DEV:
    config.XINE_TV_VO_DEV = config.XINE_VO_DEV
    _debug_("XINE_TV_VO_DEV set to config.XINE_VO_DEV")

if not config.XINE_TV_AO_DEV:
    config.XINE_TV_AO_DEV = config.XINE_AO_DEV
    _debug_("XINE_TV_AO_DEV set to config.XINE_AO_DEV")

if not config.TV_CHANNELS:
    _debug_("TV_CHANNELS is not configured!")

if not config.VOLUME_TV_IN:
    _debug_("VOLUME_TV_IN is not configured!")

if not config.MAJOR_AUDIO_CTRL:
    _debug_("MAJOR_AUDIO_CTRL is not configured!")

if not config.XINE_COMMAND:
    config.XINE_COMMAND = "xine"
    _debug_("XINE_TV_CHANNELS is not configured!")

if not config.XINE_ARGS_DEF:
    config.XINE_ARGS_DEF = ""
    _debug_("XINE_ARGS_DEF is not configured!")

if not config.XINE_TV_TIMESHIFT_FILEMASK:
    config.XINE_TV_TIMESHIFT_FILEMASK = "/tmp/xinebuf"
    _debug_("XINE_TV_TIMESHIFT_FILEMASK is not configured!")

class PluginInterface(plugin.Plugin):
    """
    Plugin to watch live tv with xine. The plugin supports:

    - Live TV: pause & continue, seek forward & backward
    - Multiple digit channel selection: '1', '12, '123'
    - Channel stack: jump to previously viewed channel

    Requirements:
    -------------

    The following software must be installed:

    - ivtv (e.g. Haupage x50 series TV card)
    - xine (built with xvmc / xxmc if available)

    Configuration:
    --------------

    The following items should be configured in local_conf.py:

    - TV_CHANNELS
    - VOLUME_TV_IN
    - MAJOR_AUDIO_CTRL
    - XINE_COMMAND
    - XINE_ARGS_DEF
    - XINE_TV_VO_DEV
    - XINE_TV_AO_DEV
    - XINE_TV_TIMESHIFT_FILEMASK

    To enable the channel stack, add the following event
    to local_conf.py:

      EVENTS['tv']['SOME_LIRC_CMD'] = Event('POPCHANNEL')

    Refer to the config file for further explanation.
    """

    __author__           = "Richard van Paasen"
    __author_email__     = "rvpaasen@t3i.nl"
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = "$Revision$"

    def __init__(self):

        plugin.Plugin.__init__(self)
        plugin.register(IVTV_XINE_TV(), plugin.TV)


# ======================================================================


class IVTV_XINE_TV:
    """
    Main class of the plugin
    """

    def __init__(self):

        self.xine = XineThread()
        self.xine.setDaemon(1)
        self.xine.start()

        self.tuner = TunerControl()
        self.mixer = MixerControl()

        self.app_mode = "tv"
        self.app = None
        self.videodev = None

        self.lastinput_value = None
        self.lastinput_time = 0


    def Play(self, mode, channel=None, channel_change=0):

        _debug_("IVTV_XINE_TV: Play channel = '%s'" % channel)

        self.mode = mode

        self.prev_app = rc.app()
        rc.app(self)

        self.tuner.SetChannel(channel, True)
        self.mixer.prepare()
        self.xine.play()

        # Suppress annoying audio clicks
        time.sleep(0.6)
        self.mixer.start()

        _debug_("IVTV_XINE_TV: Started '%s' app" % self.mode)


    def Pause(self):

        self.xine.pause()


    def Stop(self):

        self.mixer.stop()
        self.xine.stop()
        rc.app(self.prev_app)
        rc.post_event(PLAY_END)
        _debug_("IVTV_XINE_TV: Stopped '%s' app" % self.mode)


    def eventhandler(self, event, menuw=None):

        _debug_("IVTV_XINE_TV: '%s' app got '%s' event" % (self.mode, event))

        s_event = "%s" % event

        if event == STOP or event == PLAY_END:

            self.Stop()
            return True


        if event == PAUSE or event == PLAY:

            self.Pause()
            return True


        if event == "POPCHANNEL":

            self.tuner.PopChannel()
            return True


        if event in [ TV_CHANNEL_UP, TV_CHANNEL_DOWN] or s_event.startswith("INPUT_"):

            if event == TV_CHANNEL_UP:

                # tune next channel
                self.tuner.NextChannel()

            elif event == TV_CHANNEL_DOWN:

                # tune previous channel
                self.tuner.PrevChannel()

            else:
                eventInput=s_event[6]
                isNumeric=TRUE
                try:
                    newinput_value = int(eventInput)
                except:
                    #Protected against INPUT_UP, INPUT_DOWN, etc
                    isNumeric=FALSE
                if isNumeric:
                    # tune explicit channel
                    newinput_time = int(time.time())
                    if (self.lastinput_value != None):
                        # allow 2 seconds delay for multiple digit channels
                        if (newinput_time - self.lastinput_time < 2):
                            # this enables multiple (max 3) digit channel selection
                            if (self.lastinput_value >= 100):
                                self.lastinput_value = (self.lastinput_value % 100)
                            newinput_value = self.lastinput_value * 10 + newinput_value
                    self.lastinput_value = newinput_value
                    self.lastinput_time = newinput_time
                    self.tuner.TuneChannelByNumber(newinput_value)
                    if newinput_value > 9:
                        # cancel intermediate channels
                        self.tuner.UnpushChannel()
            return True


        if event == SEEK:

            steps = int(event.arg)

            if steps == 0:

                _debug_("IVTV_XINE_TV: Ignoring seek 0")

                return True

            if steps < 0:

                action = "SeekRelative-"
                steps = 0 - steps

            else:

                action = "SeekRelative+"

            # seeking can only be done in steps of 7, 15, 30 or 60

            if steps <= 7:
                steps = 7
            elif steps <= 15:
                steps = 15
            elif steps <= 30:
                steps = 30
            else:
                steps = 60

            _debug_("IVTV_XINE_TV: Seeking '%s%s' seconds" % (action, steps))

            self.xine.app.write("%s%s\n" % (action, steps))

            return True


        if event == TOGGLE_OSD:

            self.xine.app.write("OSDStreamInfos\n")

            return True


# ======================================================================


class TunerControl:
    """
    Class that controls the tuner device
    """

    def __init__(self):

        self.ivtv_init = False
        self.fc = FreevoChannels()
        self.curr_channel = None
        self.embed = None
        self.stack = [ ]


    def _kill_(self):

        if self.embed:

            ivtv_dev.setvbiembed(self.embed)


    def PushChannel(self):

        if self.curr_channel != None:

            self.stack.append(self.curr_channel)
            _debug_("TunerControl: Pushed channel %s" % self.curr_channel)

        _debug_("TunerControl: Channel stack = %s" % self.stack)


    def UnpushChannel(self):

        if len(self.stack) == 0:

            _debug_("TunerControl: Channel stack is empty")

        else:

            channel = self.stack.pop()
            _debug_("TunerControl: Unpushed channel %s" % channel)

        _debug_("TunerControl: Channel stack = %s" % self.stack)


    def PopChannel(self):

        if len(self.stack) == 0:

            _debug_("TunerControl: Channel stack is empty")

        else:

            channel = self.stack.pop()
            _debug_("TunerControl: Popped channel %s" % channel)

            self.SetVideoGroup(channel)

        _debug_("TunerControl: Channel stack = %s" % self.stack)


    def SetChannel(self, channel=None, clearstack=False):

        # set channel by name

        last_channel = self.curr_channel
        next_channel = None
        channel_index = -1

        if clearstack == True:

            self.stack = [ ]
            self.curr_channel = None

        if channel == None:

            # get a channel
            next_channel = self.fc.getChannel()

        try:

            # lookup the channel name in TV_CHANNELS

            for pos in range(len(config.TV_CHANNELS)):

                entry = config.TV_CHANNELS[pos]

                if channel == entry[2]:

                    channel_index = pos
                    next_channel = channel

                    break

        except ValueError:

            pass

        if (next_channel == None):

            _debug_("TunerControl: Cannot find tuner channel '%s' in the TV channel listing" % channel)

        else:

            self.TuneChannelByIndex(channel_index + 1)


    def TuneChannelByIndex(self, channel):

        # tune channel by index

        next_channel = self.fc.getManChannel(channel)
        _debug_("TunerControl: Explicit channel selection = '%s'" % next_channel)

        self.PushChannel()
        self.SetVideoGroup(next_channel)

    def TuneChannelByNumber(self, channel):

        # tune channel by number

        self.PushChannel()
        self.SetVideoGroup(str(channel))


    def NextChannel(self):

        next_channel = self.fc.getNextChannel()
        _debug_("TunerControl: Next channel selection = '%s'" % next_channel)

        self.PushChannel()
        self.SetVideoGroup(next_channel)


    def PrevChannel(self):

        prev_channel = self.fc.getPrevChannel()
        _debug_("TunerControl: Previous channel selection = '%s'" % prev_channel)

        self.PushChannel()
        self.SetVideoGroup(prev_channel)


    def SetVideoGroup(self, channel):

        _debug_("TunerControl: Play channel = '%s'" % channel)
        vg = self.fc.getVideoGroup(channel, True)
        _debug_("TunerControl: Play group = '%s'" % vg.desc)

        if (vg.group_type != "ivtv"):

            _debug_("TunerControl: Video group '%s' is not supported" % vg.group_type)
            pop = AlertBox(text=_("This plugin only supports the ivtv video group in tv mode!"))
            pop.show()
            return

        if self.ivtv_init == False:

            ivtv_dev = ivtv.IVTV(vg.vdev)
            ivtv_dev.init_settings()
            ivtv_dev.setinput(vg.input_num)
            ivtv_dev.print_settings()

            # disable embedded vbi data
            self.embed = ivtv_dev.getvbiembed()
            ivtv_dev.setvbiembed(0)

            self.ivtv_init = True

        self.fc.chanSet(channel, True)
        self.curr_channel = channel

        # todo: skip to end of stream
        # todo: insert xine OSD message here ...

        # tuner_id, chan_name, prog_info = self.fc.getChannelInfo()
        # now = time.strftime(config.TV_TIMEFORMAT)
        # msg = "%s %s (%s): %s" % (now, chan_name, tuner_id, prog_info)
        # cmd = "osd_show_text '%s'\n" % msg
        # todo: insert xine OSD message here ...


# ======================================================================


class MixerControl:
    """
    Class that controls the mixer device
    """

    def __init__(self):

        self.mixer = plugin.getbyname("MIXER")
        self.volume = 0


    def prepare(self):

        if (self.mixer != None):

            if config.MAJOR_AUDIO_CTRL == "VOL":

                self.volume = self.mixer.getMainVolume()
                self.mixer.setMainVolume(0)

            elif config.MAJOR_AUDIO_CTRL == "PCM":

                self.volume = self.mixer.getPcmVolume()
                self.mixer.setPcmVolume(0)


    def start(self):

        if (self.mixer != None):

            self.mixer.setLineinVolume(config.VOLUME_TV_IN)
            self.mixer.setIgainVolume(config.VOLUME_TV_IN)

            if config.MAJOR_AUDIO_CTRL == "VOL":

                self.mixer.setMainVolume(self.volume)

            elif config.MAJOR_AUDIO_CTRL == "PCM":

                self.mixer.setPcmVolume(self.volume)


    def stop(self):

        if (self.mixer != None):

            self.mixer.setLineinVolume(0)
            self.mixer.setMicVolume(0)
            self.mixer.setIgainVolume(0)


# ======================================================================


class XineApp(childapp.ChildApp2):
    """
    Class that controls the Xine process
    """

    def __init__(self, app, item):

        self.item = item
        _debug_("XineApp: Starting xine, cmd = '%s'" % app)
        childapp.ChildApp2.__init__(self, app)
        self.exit_type = None
        self.done = False

    def _kill_(self):

        _debug_("XineApp: Killing xine...")
        childapp.ChildApp2.kill(self,signal.SIGTERM)
        self.done = True


# ======================================================================


class XineThread(threading.Thread):
    """
    Thread that handles Xine commands
    """

    def __init__(self):

        threading.Thread.__init__(self)

        self.app = None
        self.item = None
        self.state = "idle"
        self.start_flag = threading.Event()

        try:

            xinecmd = config.XINE_COMMAND.split(' ')[0].split('/')[-1]
            self.fbxine = xinecmd in ("fbxine", "df_xine")

        except:

            xinecmd = ""
            self.fbxine = False

        _debug_( "XineThread: configuration overview" )
        _debug_( "    config.CONF.xine = '%s'" % (config.CONF.xine) )
        _debug_( "    config.XINE_COMMAND = '%s'" % (config.XINE_COMMAND) )
        _debug_( "    config.XINE_ARGS_DEF = '%s'" % (config.XINE_ARGS_DEF) )
        _debug_( "    config.XINE_TV_VO_DEV = '%s'" % (config.XINE_TV_VO_DEV) )
        _debug_( "    config.XINE_TV_AO_DEV = '%s'" % (config.XINE_TV_AO_DEV) )
        _debug_( "    config.XINE_TV_TIMESHIFT_FILEMASK = '%s'" % (config.XINE_TV_TIMESHIFT_FILEMASK) )
        _debug_( "    effective xinecmd = '%s'" % (xinecmd) )
        _debug_( "    effective self.fbxine = '%s'" % (self.fbxine) )

        if self.fbxine:

            self.command = "%s %s --stdctl pvr://%s" % \
                (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_TIMESHIFT_FILEMASK)

        else:

            self.command = "%s %s -V %s -A %s --stdctl pvr://%s" % \
                (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_VO_DEV, \
                config.XINE_TV_AO_DEV, config.XINE_TV_TIMESHIFT_FILEMASK)


    def play(self):

        if self.state == "idle":

            self.start_flag.set()


    def pause(self):

        if self.state == "busy":

            self.state = "pause"


    def stop(self):

        if self.state == "busy":

            self.state = "stop"

            if self.fbxine:

                while not self.app.done:

                    _debug_("XineThread: Waiting for xine to end...")
                    time.sleep(0.1)

                _debug_("XineThread: Xine ended")


    def run(self):

        while 1:

            if self.state == "idle":

                self.start_flag.wait()
                self.start_flag.clear()

            else:

                _debug_("XineThread: Should be idle on thread entry!")

            self.app = XineApp(self.command, self.item)
            self.state = "busy"

            laststate = None

            while self.app.isAlive():

                if laststate != self.state:

                    _debug_("XineThread: state '%s' -> '%s'" % (laststate, self.state))
                    laststate = self.state

                if self.state == "busy":

                    time.sleep(0.1)

                elif self.state == "pause":

                    self.app.write("pause\n")
                    self.state = "busy"

                elif self.state == "stop":

                    _debug_("XineThread: Stoppping xine")
                    self.app.stop("quit\n")

                    if self.fbxine:

                            # directfb needs xine to be killed
                            # else the display is messed up
                            # and freevo crashes
                        time.sleep(1.0)
                        _debug_("XineThread: Killing xine")
                        self.app._kill_()

                    self.state = "busy"

            _debug_("XineThread: Stopped")

            self.state = 'idle'
