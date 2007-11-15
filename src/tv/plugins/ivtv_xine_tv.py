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
#   - toggle between live and record mode
#
# Dependencies
#   - Xine: [ 1810459 ] [Patch] Configurable OSD fonts
#     http://sourceforge.net/tracker/index.php?func=detail&aid=1810459&group_id=9655&atid=359655
#   - Xine: [ 1814163 ] [Patch] Add SetPosition100%
#     http://sourceforge.net/tracker/index.php?func=detail&aid=1814163&group_id=9655&atid=359655
#
# Changes:
#   - Changed code to conform to new debug style
#   - Stop confirmation: press STOP twice to return to menu
#   - Automatic jump: undo time shift on channel change
#   - OSD messges: volume and channel info
#   - Progressive seek: automatically increase speed
#   - Video groups: enable svideo and composite inputs
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
from config import *
from gui.AlertBox import AlertBox
from tv.channels import FreevoChannels

DEBUG = config.DEBUG
DDEBUG = 0

# guard important config variables

if not hasattr(config, 'TV_CHANNELS'):
    _debug_("TV_CHANNELS is not configured!", DERROR)

if not hasattr(config, 'MIXER_MAJOR_CTRL'):
    _debug_("MIXER_MAJOR_CTRL is not configured!", DERROR)

if not hasattr(config, 'MIXER_VOLUME_TV_IN'):
    config.MIXER_VOLUME_TV_IN = 50
    _debug_("MIXER_VOLUME_TV_IN is not configured!", DWARNING)

if not hasattr(config, 'XINE_COMMAND'):
    config.XINE_COMMAND = "xine"
    _debug_("XINE_TV_CHANNELS is not configured!", DWARNING)

if not hasattr(config, 'XINE_ARGS_DEF'):
    config.XINE_ARGS_DEF = ""
    _debug_("XINE_ARGS_DEF is not configured!", DWARNING)

if not hasattr(config, 'XINE_TV_VO_DEV'):
    config.XINE_TV_VO_DEV = config.XINE_VO_DEV
    _debug_("XINE_TV_VO_DEV set to config.XINE_VO_DEV", DWARNING)

if not hasattr(config, 'XINE_TV_AO_DEV'):
    config.XINE_TV_AO_DEV = config.XINE_AO_DEV
    _debug_("XINE_TV_AO_DEV set to config.XINE_AO_DEV", DWARNING)

if not hasattr(config, 'XINE_TV_TIMESHIFT_FILEMASK'):
    config.XINE_TV_TIMESHIFT_FILEMASK = "/tmp/xinebuf"
    _debug_("XINE_TV_TIMESHIFT_FILEMASK is not configured!", DWARNING)

if not hasattr(config, 'XINE_TV_CONFIRM_STOP'):
    config.XINE_TV_CONFIRM_STOP = True
    _debug_("XINE_TV_CONFIRM_STOP is not configured!", DWARNING)

if not hasattr(config, 'XINE_TV_PROGRESSIVE_SEEK'):
    config.XINE_TV_PROGRESSIVE_SEEK = True
    _debug_("XINE_TV_PROGRESSIVE_SEEK is not configured!", DWARNING)

if config.XINE_TV_PROGRESSIVE_SEEK == True:
    if not hasattr(config, 'XINE_TV_PROGRESSIVE_SEEK_THRESHOLD'):
        config.XINE_TV_PROGRESSIVE_SEEK_THRESHOLD = 2
        _debug_("XINE_TV_PROGRESSIVE_SEEK_THRESHOLD is not configured!", DWARNING)

    if not hasattr(config, 'XINE_TV_PROGRESSIVE_SEEK_INCREMENT'):
        config.XINE_TV_PROGRESSIVE_SEEK_INCREMENT = 5
        _debug_("XINE_TV_PROGRESSIVE_SEEK_INCREMENT is not configured!", DWARNING)


class PluginInterface(plugin.Plugin):
    """
    Plugin to watch live tv with xine. The plugin supports:

    - Live TV: pause & continue, seek forward & backward
    - Multiple digit channel selection: '1', '12, '123'
    - Channel stack: jump to previously viewed channel
    - Automatic jump: undo time shift on channel change
    - OSD messges: volume and channel info
    - Progressive seek: automatically increase seek speed
    - Video groups: enable svideo and composite inputs
    - Stop confirmation: press STOP twice to return to menu

    =================================================================
    Requirements:
    =================================================================

    The following software must be installed:

    - ivtv (e.g. Haupage x50 series TV card)
    - xine (built with xvmc / xxmc if available)

    =================================================================
    Configuration:
    =================================================================

    The following items should be configured in local_conf.py:

    Freevo General Config Items
    - TV_CHANNELS
    - MIXER_VOLUME_TV_IN
    - MIXER_MAJOR_CTRL
    - XINE_COMMAND
    - XINE_ARGS_DEF

    Plugin Specific Config Items
    - XINE_TV_VO_DEV
    - XINE_TV_AO_DEV
    - XINE_TV_TIMESHIFT_FILEMASK
    - XINE_TV_CONFIRM_STOP
    - XINE_TV_PROGRESSIVE_SEEK
    - XINE_TV_PROGRESSIVE_SEEK_THRESHOLD
    - XINE_TV_PROGRESSIVE_SEEK_INCREMENT

    =================================================================
    Plugin Specific Events
    =================================================================
    The following additional events can be defined:

    | # go back to the previous viewed channel
    | EVENTS['tv']['SOME_LIRC_CMD'] = Event('POPCHANNEL')
    |
    | # show program info
    | EVENTS['tv']['SOME_LIRC_CMD'] = Event('TOGGLE_OSD')
    |
    | # normal seek forward/backward by 1 second
    | EVENTS['tv']['SOME_LIRC_CMD'] = Event(SEEK, arg=-1)
    | EVENTS['tv']['SOME_LIRC_CMD'] = Event(SEEK, arg=+1)

    =================================================================
    Timeshift Filemask
    =================================================================
    The LIVE TV functionality requires a large buffer on disk
    where the TV stream is being recorded while watching.

    | # This specifies the path and filemask that xine uses for
    | # timeshifting. File can get quite big (several gigabytes)
    | XINE_TV_TIMESHIFT_FILEMASK = "/local/tmp/xine-buf-!!20"

    =================================================================
    STOP Confirmation
    =================================================================
    The STOP event will cancel the history of the TV stream. To
    prevent that this happens by accident, a confirmation can be
    requested.

    | # Stop confirmation: press STOP twice to return to menu
    | XINE_TV_CONFIRM_STOP = True

    =================================================================
    Progressive Seek
    =================================================================
    If progressive is enabled, then seeking in the TV stream
    will speed up by 'increment' seconds every 'threshold'
    seconds. Note, set the starting seek event to 1 second to
    allow fine control.

    | # This enables the progressive seek feature. The speed
    | # for seeking (fast forward and rewind) is increased
    | # automatically. The speed is increased every [THRESHOLD]
    | # seconds in steps of [INCREMENT] secnds.
    | XINE_TV_PROGRESSIVE_SEEK = True
    | XINE_TV_PROGRESSIVE_SEEK_THRESHOLD = 2
    | XINE_TV_PROGRESSIVE_SEEK_INCREMENT = 5

    =================================================================
    Video Groups Setup Example
    =================================================================
    The following shows an example of a configuration for a 1-tuner
    PVR 250 card and adds S-VIDEO and Composite Inputs. Note that the
    audio input is selected automatically by ivtv.

    | TV_VIDEO_GROUPS = [
    |         VideoGroup(
    |             vdev='/dev/video0',
    |             adev=None,
    |             input_type='Tuner 1',
    |             tuner_norm='pal',
    |             tuner_chanlist='europe-west',
    |             desc='Regular Cable',
    |             group_type='ivtv',
    |             record_group = None
    |         ),
    |         VideoGroup(
    |             vdev='/dev/video0',
    |             adev=None,
    |             input_type='S-Video 1',
    |             tuner_type='external',
    |             desc='S-Video Input',
    |             group_type='ivtv',
    |             record_group = None
    |         ),
    |         VideoGroup(
    |             vdev='/dev/video0',
    |             adev=None,
    |             input_type='Composite 2',
    |             tuner_type='external',
    |             desc='Composite Input',
    |             group_type='ivtv',
    |             record_group = None
    |         ),
    | ]
    |
    | TV_CHANNELS = [
    |     ('ned1',        'NED 1',                'C22', '', 0),
    |     ...
    |     ('natg',        'National Geographic',  'C47', '', 0),
    |     ...
    |     ('svideo',      'S-Video Input',        'EX1', '', 1),
    |     ('composite',   'Composite Input',      'EX2', '', 2),
    | ]

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

    #========================================================================
    # __init__
    # constructor
    #========================================================================

    def __init__(self):

        self.xine = XineThread()
        self.xine.setDaemon(1)
        self.xine.start()

        self.tuner = TunerControl()
        self.tuner.setParent(self)
        self.mixer = MixerControl()

        self.app_mode = "tv"
        self.app = None
        self.videodev = None

        self.lastinput_time = 0
        self.lastinput_value = None

        self.notahead = False

        self.seeksteps = 0
        self.seektime_start = 0
        self.seektime_previous = 0
        self.seekevent_previous = None

        self.confirmstop_time = 0

    #========================================================================
    # Play
    # start xine player
    #========================================================================

    def Play(self, mode, channel=None, channel_change=0):

        _debug_("IVTV_XINE_TV: Play channel = '%s'" % channel, DDEBUG)

        self.mode = mode

        self.prev_app = rc.app()
        rc.app(self)

        self.mixer.prepare()
        self.tuner.SetChannel(channel, True)
        self.xine.play()

        # Suppress annoying audio clicks
        time.sleep(0.6)
        self.mixer.start()

        _debug_("IVTV_XINE_TV: Started '%s' app" % self.mode, DDEBUG)


    #========================================================================
    # Stop
    # stop xine player
    #========================================================================

    def Stop(self):

        confirmstop_time = int(time.time())
        # note: the OSD msg is displayed for 5 seconds
        if (config.XINE_TV_CONFIRM_STOP == True) and (confirmstop_time - self.confirmstop_time > 4):
            self.ShowMessage("Please repeat to stop\n")
            self.confirmstop_time = confirmstop_time
        else:
            self.mixer.stop()
            self.xine.stop()
            rc.app(self.prev_app)
            rc.post_event(PLAY_END)
            _debug_("IVTV_XINE_TV: Stopped '%s' app" % self.mode, DDEBUG)


    #========================================================================
    # ShowMessage
    # show a message on the OSD
    #========================================================================

    def ShowMessage(self, msg):

        _debug_("IVTV_XINE_TV: Show OSD Message: '%s'" % msg, DDEBUG)
        self.xine.write("OSDWriteText$%s\n" % msg)


    #========================================================================
    # SeekEnd
    # Skip to end of stream
    # The notahead flag indicates if the user has used the pause or rewind
    # buttons. That implies that the seek is needed.
    #========================================================================

    def SeekEnd(self):

        if self.notahead == True:
            _debug_("IVTV_XINE_TV: Executing SeekEnd", DDEBUG)

            self.xine.write("SetPosition100%\n")
            self.notahead = False

        else:
            _debug_("IVTV_XINE_TV: SeekEnd not needed", DDEBUG)


    #========================================================================
    # eventhandler
    # freevo eventhandler
    #========================================================================

    def eventhandler(self, event, menuw=None):

        _debug_("IVTV_XINE_TV: '%s' app got '%s' event" % (self.mode, event), DDEBUG)

        s_event = "%s" % event

        if event == STOP or event == PLAY_END:

            self.Stop()
            return True


        if event == PAUSE or event == PLAY:

            self.xine.pause()
            self.notahead = True
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
                    self.tuner.TuneChannelByIndex(newinput_value)

                    if newinput_value > 9:
                        # cancel intermediate channels
                        self.tuner.UnpushChannel()

            return True


        if event == SEEK:

            seeksteps = int(event.arg)

            if seeksteps == 0:

                _debug_("IVTV_XINE_TV: Ignoring seek 0", DDEBUG)

                return True

            if seeksteps < 0:

                action = "SeekRelative-"
                seeksteps = 0 - seeksteps
                self.notahead = True

            else:

                action = "SeekRelative+"

            if config.XINE_TV_PROGRESSIVE_SEEK:

                seekevent_current = event.arg
                seeksteps_current = seeksteps
                seektime_current = int(time.time())
                seektime_delta = seektime_current - self.seektime_previous

                if (seektime_delta > 2) or (seekevent_current != self.seekevent_previous):
                    # init/reset progressive seek mode
                    self.seeksteps = seeksteps
                    self.seektime_start = seektime_current
                    self.seektime_previous = seektime_current
                else:
                    # continue progressive
                    if (
                        (seektime_delta > 0) and
                        ((seektime_delta % config.XINE_TV_PROGRESSIVE_SEEK_THRESHOLD) == 0)
                       ):
                        self.seeksteps += config.XINE_TV_PROGRESSIVE_SEEK_INCREMENT
                        self.seektime_previous = seektime_current

                self.seekevent_previous = seekevent_current
                seeksteps = self.seeksteps

            # Note: Xine 2007 versions support
            # arbitrary SeekRelative+/- steps
            # limit seeksteps to [1 ; 120] seconds
            seeksteps = min( max(1, seeksteps), 120 )

            _debug_("IVTV_XINE_TV: Seeking '%s%s' seconds" % (action, seeksteps), DDEBUG)

            self.xine.write("%s#%s\n" % (action, seeksteps))

            return True


        if event == TOGGLE_OSD:

            self.tuner.ShowInfo()

            return True


        if event == OSD_MESSAGE:

            self.ShowMessage(event.arg)

            return True


# ======================================================================


class TunerControl:
    """
    Class that controls the tuner device
    """

    #========================================================================
    # __init__
    # constructor
    #========================================================================

    def __init__(self):

        self.ivtv_init = False
        self.fc = FreevoChannels()
        self.curr_channel = None
        self.embed = None
        self.stack = [ ]


    #========================================================================
    # __kill__
    # destructor
    #========================================================================

    def _kill_(self):

        if self.embed:

            ivtv_dev.setvbiembed(self.embed)


    #========================================================================
    # ShowInfo
    # show channle info
    #========================================================================

    def ShowInfo(self):

        # show channel info
        vg = self.fc.getVideoGroup(self.curr_channel, True)
        if vg.input_type == 'tuner':
            tuner_id, chan_name, prog_info = self.fc.getChannelInfo(showtime=False)
            msg = "%s: %s" % (chan_name, prog_info)
            self.parent.ShowMessage("%s" % msg)
        else:
            # show channel info
            self.parent.ShowMessage(vg.desc)

    #========================================================================
    # setParent
    # keep a reference to the IVTV_XINE_TV object
    #========================================================================

    def setParent(self, parent):

        self.parent = parent


    #========================================================================
    # PushChannel
    # push the current channel on the channel stack
    #========================================================================

    def PushChannel(self):

        if self.curr_channel != None:

            self.stack.append(self.curr_channel)
            _debug_("TunerControl: Pushed channel %s" % self.curr_channel, DDEBUG)

        _debug_("TunerControl: Channel stack = %s" % self.stack, DDEBUG)


    #========================================================================
    # UnpushChannel
    # remove the top channel fromthe channel stack
    #========================================================================

    def UnpushChannel(self):

        if len(self.stack) == 0:

            _debug_("TunerControl: Channel stack is empty", DDEBUG)

        else:

            channel = self.stack.pop()
            _debug_("TunerControl: Unpushed channel %s" % channel, DDEBUG)

        _debug_("TunerControl: Channel stack = %s" % self.stack, DDEBUG)


    #========================================================================
    # PopChannel
    # pop the top channel from the channel stack and switch channel
    #========================================================================

    def PopChannel(self):

        if len(self.stack) == 0:

            _debug_("TunerControl: Channel stack is empty", DDEBUG)

        else:

            channel = self.stack.pop()
            _debug_("TunerControl: Popped channel %s" % channel, DDEBUG)

            self.SetVideoGroup(channel)

        _debug_("TunerControl: Channel stack = %s" % self.stack, DDEBUG)


    #========================================================================
    # SetChannel
    # select a new channel
    #========================================================================

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

            _debug_("TunerControl: Cannot find tuner channel '%s' in the TV channel listing" % channel, DWARNING)

        else:

            self.TuneChannelByIndex(channel_index + 1)


    #========================================================================
    # TuneChannelByIndex
    # tune to a channel by index from the TV_CHANNELS list
    #========================================================================

    def TuneChannelByIndex(self, channel):

        # tune channel by index
        next_channel = self.fc.getManChannel(channel)
        _debug_("TunerControl: Explicit channel selection = '%s'" % next_channel, DDEBUG)

        self.PushChannel()
        self.SetVideoGroup(next_channel)


    #========================================================================
    # NextChannel
    # jump to the next channel in the TV_CHANNELS list
    #========================================================================

    def NextChannel(self):

        next_channel = self.fc.getNextChannel()
        _debug_("TunerControl: Next channel selection = '%s'" % next_channel, DDEBUG)

        self.PushChannel()
        self.SetVideoGroup(next_channel)


    #========================================================================
    # PrevChannel
    # jump to the previous channel in the TV)CHANNELS list
    #========================================================================

    def PrevChannel(self):

        prev_channel = self.fc.getPrevChannel()
        _debug_("TunerControl: Previous channel selection = '%s'" % prev_channel, DDEBUG)

        self.PushChannel()
        self.SetVideoGroup(prev_channel)


    #========================================================================
    # SetVideoGroup
    # select a channel's video group and tune to that channel
    #========================================================================

    def SetVideoGroup(self, channel):

        _debug_("TunerControl: Channel: '%s'" % channel, DDEBUG)
        new_vg = self.fc.getVideoGroup(channel, True)
        _debug_("TunerControl: Group: 'type=%s, desc=%s'" % (new_vg.group_type, new_vg.desc), DDEBUG)
        _debug_("TunerControl: Input: 'type=%s, num=%s'" % (new_vg.input_type, new_vg.input_num), DDEBUG)

        if (new_vg.group_type != "ivtv"):

            _debug_("TunerControl: Video group '%s' is not supported" % new_vg.group_type, DERROR)
            pop = AlertBox(text=_("This plugin only supports the ivtv video group!"))
            pop.show()
            return

        # check if videogroup switch is needed
        switch_vg = (self.ivtv_init == False) or \
                    (self.curr_channel == None) or \
                    (new_vg != self.fc.getVideoGroup(self.curr_channel, True))

        if switch_vg == True:

            # switch to a different video group
            ivtv_dev = ivtv.IVTV(new_vg.vdev)
            ivtv_dev.init_settings()
            ivtv_dev.setinput(new_vg.input_num)
            ivtv_dev.print_settings()

            # disable embedded vbi data
            self.embed = ivtv_dev.getvbiembed()
            ivtv_dev.setvbiembed(0)

            self.ivtv_init = True

        # set channel
        self.fc.chanSet(channel, True)
        self.curr_channel = channel
        self.ShowInfo()
        self.parent.SeekEnd()


# ======================================================================


class MixerControl:
    """
    Class that controls the mixer device
    """

    #========================================================================
    # __init__
    # constructor
    #========================================================================

    def __init__(self):

        self.mixer = plugin.getbyname("MIXER")
        self.volume = 0


    #========================================================================
    # prepare
    # turn down volume
    #========================================================================

    def prepare(self):

        if (self.mixer != None):

            if config.MIXER_MAJOR_CTRL == "VOL":

                self.volume = self.mixer.getMainVolume()
                self.mixer.setMainVolume(0)

            elif config.MIXER_MAJOR_CTRL == "PCM":

                self.volume = self.mixer.getPcmVolume()
                self.mixer.setPcmVolume(0)


    #========================================================================
    # start
    # turn up volume
    #========================================================================

    def start(self):

        if (self.mixer != None):

            self.mixer.setLineinVolume(config.MIXER_VOLUME_TV_IN)
            self.mixer.setIgainVolume(config.MIXER_VOLUME_TV_IN)

            if config.MIXER_MAJOR_CTRL == "VOL":

                self.mixer.setMainVolume(self.volume)

            elif config.MIXER_MAJOR_CTRL == "PCM":

                self.mixer.setPcmVolume(self.volume)


    #========================================================================
    # stop
    # turn down volume
    #========================================================================

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

    #========================================================================
    # __init__
    # constructor
    #========================================================================

    def __init__(self, app, item):

        self.item = item
        _debug_("XineApp: Starting xine, cmd = '%s'" % app, DDEBUG)
        childapp.ChildApp2.__init__(self, app)
        self.exit_type = None
        self.done = False

    #========================================================================
    # __kill__
    # destructor
    #========================================================================

    def _kill_(self):

        _debug_("XineApp: Killing xine...", DDEBUG)
        childapp.ChildApp2.kill(self,signal.SIGTERM)
        self.done = True


#========================================================================


class XineThread(threading.Thread):
    """
    Thread that handles Xine commands
    """

    #========================================================================
    # __init__
    # constructor
    #========================================================================

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

        _debug_("XineThread: configuration overview", DDEBUG)
        _debug_("    config.CONF.xine = '%s'" % (config.CONF.xine), DDEBUG)
        _debug_("    config.XINE_COMMAND = '%s'" % (config.XINE_COMMAND), DDEBUG)
        _debug_("    config.XINE_ARGS_DEF = '%s'" % (config.XINE_ARGS_DEF), DDEBUG)
        _debug_("    config.XINE_TV_VO_DEV = '%s'" % (config.XINE_TV_VO_DEV), DDEBUG)
        _debug_("    config.XINE_TV_AO_DEV = '%s'" % (config.XINE_TV_AO_DEV), DDEBUG)
        _debug_("    config.XINE_TV_TIMESHIFT_FILEMASK = '%s'" % (config.XINE_TV_TIMESHIFT_FILEMASK), DDEBUG)
        _debug_("    effective xinecmd = '%s'" % (xinecmd), DDEBUG)
        _debug_("    effective self.fbxine = '%s'" % (self.fbxine), DDEBUG)

        if self.fbxine:

            self.command = "%s %s --stdctl pvr://%s" % \
                (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_TIMESHIFT_FILEMASK)

        else:

            self.command = "%s %s -V %s -A %s --stdctl pvr://%s" % \
                (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_VO_DEV, \
                config.XINE_TV_AO_DEV, config.XINE_TV_TIMESHIFT_FILEMASK)


    #========================================================================
    # write
    # send a command to the xine player
    #========================================================================

    def write(self, msg):

        if self.state != "idle":

            self.app.write(msg)


    #========================================================================
    # play
    # start playing
    #========================================================================

    def play(self):

        if self.state == "idle":

            self.start_flag.set()


    #========================================================================
    # pause
    # pause playing
    #========================================================================

    def pause(self):

        if self.state == "busy":

            self.state = "pause"


    #========================================================================
    # stop
    # stop playing
    #========================================================================

    def stop(self):

        if self.state == "busy":

            self.state = "stop"

            if self.fbxine:

                while not self.app.done:

                    _debug_("XineThread: Waiting for xine to end...", DDEBUG)
                    time.sleep(0.1)

                _debug_("XineThread: Xine ended", DDEBUG)


    #========================================================================
    # run
    # worker method
    #========================================================================

    def run(self):

        while 1:

            if self.state == "idle":

                self.start_flag.wait()
                self.start_flag.clear()

            else:

                _debug_("XineThread: Should be idle on thread entry!", DWARNING)

            self.app = XineApp(self.command, self.item)
            self.state = "busy"

            laststate = None

            while self.app.isAlive():

                if laststate != self.state:

                    _debug_("XineThread: state '%s' -> '%s'" % (laststate, self.state), DDEBUG)
                    laststate = self.state

                if self.state == "busy":

                    time.sleep(0.1)

                elif self.state == "pause":

                    self.app.write("pause\n")
                    self.state = "busy"

                elif self.state == "stop":

                    _debug_("XineThread: Stoppping xine", DDEBUG)
                    self.app.stop("quit\n")

                    if self.fbxine:

                        # directfb needs xine to be killed
                        # else the display is messed up
                        # and freevo crashes

                        time.sleep(1.0)
                        _debug_("XineThread: Killing xine", DDEBUG)
                        self.app._kill_()

                    self.state = "busy"

            _debug_("XineThread: Stopped", DDEBUG)

            self.state = 'idle'
