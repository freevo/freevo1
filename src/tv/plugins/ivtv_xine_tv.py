# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Implementation of live tv timeshift for ivtv
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
import logging
logger = logging.getLogger("freevo.tv.plugins.ivtv_xine_tv")

import config

import time, os
import skin

import rc
import util
import plugin
import childapp
import tv.ivtv as ivtv
import util.tv_util as tvutil

import dialog
from dialog.display import AppTextDisplay

from event import *
from config import *
from gui.AlertBox import AlertBox
from tv.channels import FreevoChannels
from kaa import OneShotTimer

class PluginInterface(plugin.Plugin):
    """
    Plugin to watch live tv with xine. The plugin supports:

        - Live TV: pause & continue, seek forward & backward
        - Multiple digit channel selection: '1', '12, '123'
        - Channel stack: jump to previously viewed channel
        - Channel swap: swap between the current and the previous channel
        - Automatic jump: undo time shift on channel change
        - OSD messages: volume and channel info
        - Progressive seek: automatically increase seek speed
        - Video groups: enable svideo and composite inputs
        - Stop confirmation: press STOP twice to return to menu
        - Record stream: press RECORD to record the current show

    =================================================================
    Requirements:
    =================================================================

    The following software must be installed:

        - ivtv driver (for e.g. Haupage x50 series TV card)
          version ivtv: >= 0.10.6

        - xine media player (built with xvmc / xxmc if available)
          version xine-lib: >= 1.1.9
          version xine-ui: >= 0.99.6

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
        - XINE_TV_INPUT_REAL_CHANNELS
        - XINE_TV_LIVE_RECORD
        - XINE_TV_INDENT_OSD

    =================================================================
    Plugin Specific Events
    =================================================================
    The following additional events can be defined:

    | # go back to the previous viewed channel
    | EVENTS['tv']['SOME_LIRC_CMD'] = Event('POPCHANNEL')
    |
    | # shift the current and the previous viewed channel
    | EVENTS['tv']['SOME_LIRC_CMD'] = Event('TOGGLECHANNEL')
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
    | # Examples:
    | XINE_TV_TIMESHIFT_FILEMASK = '/tmp/xine-buf-!!5'
    | XINE_TV_TIMESHIFT_FILEMASK = '/local/tmp/!/local/saved/!20'

    Note: the format is 'a!b!c', where:
    a = prefix (with path) for temporary file buffers
    b = prefix (with path) for saved recordings
    c = number of file buffers (200MB each) to use

    The path for saved recordings must be on the same partition as
    the path for temporary file buffers. If the save path is empty
    then the saved files will be stored in the path for temporary
    files.

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
    Live Record
    =================================================================
    If live record is enabled, then the RECORD button will cause the
    current show to be recorded permanently. Freevo will set marks
    in the video stream when a new show starts (according to the
    program guide) and when the channel is changed. Recording will
    stop automatically (1) on a channel change, (2) when a new show
    starts according to the program guide or (3) when returning to
    the program guide.

    | XINE_TV_LIVE_RECORD = True

    Note: the performance of channel changes will noticably suffer
    on slow (<1GHz) machines when live recording is enabled. Using a
    fast disk and a fast filesystem will help.

    =================================================================
    Input Real Channels
    =================================================================
    When pressing numbers on the remote control, Freevo will jump to
    a different channel, an index in the TV_CHANNELS array by default.
    Set this to true to use real (cable) channel numbers instead.

    | XINE_TV_INPUT_REAL_CHANNELS = False

    =================================================================
    Indent OSD
    =================================================================
    When using overscan mode, the OSD text in xine may be displayed
    too far to the left. Set this to indent the text somewhat to the
    right.

    | XINE_TV_INDENT_OSD = False

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

    =================================================================
    Configurable items in the xine config file
    =================================================================
    The xine config file is located in '~/.xine/config'.

    Items that change the OSD text appearance:

    | gui.osd_enabled    (set this to '1')
    | gui.osd.fontsize   (set this to '28' or '32' for a TV setup)
    | gui.osd.fontcolor  (choose one: white, yellow, green, cyan)
    | gui.osd.background (set this to '1' for better readibility)

    Owners of VIA EPIA boards might want to set the following:

    | video.device.unichrome_cpu_save


    Refer to the config file for further explanation.
    """
    __author__           = 'Richard van Paasen'
    __author_email__     = 'rvpaasen@t3i.nl'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'

    def __init__(self):
        plugin.Plugin.__init__(self)
        plugin.register(XineIvtv(), plugin.TV)

    def config(self):
        return [
            ('TV_CHANNELS', None, 'TV Channels'),
            ('MIXER_MAJOR_CTRL', None, 'Main Mixer control (mandatory)'),
            ('MIXER_VOLUME_TV_IN', 50, 'TV Line In Volume'),
            ('XINE_COMMAND', config.CONF.xine, 'xine command'),
            ('XINE_ARGS_DEF', config.XINE_ARGS_DEF, 'xine default arguments'),
            ('XINE_TV_VO_DEV', config.XINE_VO_DEV, 'xine video output device'),
            ('XINE_TV_AO_DEV', config.XINE_AO_DEV, 'xine audio output device'),
            ('XINE_TV_TIMESHIFT_FILEMASK', '/tmp/xinebuf', 'xine time shift parameters'),
            ('XINE_TV_CONFIRM_STOP', True, 'require a stop confirmation'),
            ('XINE_TV_PROGRESSIVE_SEEK', True, 'use progressive seek mode'),
            ('XINE_TV_PROGRESSIVE_SEEK_THRESHOLD', 2, 'progressive seek mode threshold (seconds)'),
            ('XINE_TV_PROGRESSIVE_SEEK_INCREMENT', 5, 'progressive seek mode steps (seconds)'),
            ('XINE_TV_INPUT_REAL_CHANNELS', False, 'handle direct input numbers as real channels'),
            ('XINE_TV_LIVE_RECORD', True, 'enable recording (make permanent) of live video'),
            ('XINE_TV_INDENT_OSD', False, 'indent OSD text'),
        ]


class XineIvtv:
    """
    Main class of the plugin
    """
    def __init__(self):
        """ XineIvtv constructor """
        self.xine = XineControl()
        self.tuner = TunerControl(self.xine)
        self.mixer = MixerControl(self.xine)
        self.timer = OneShotTimer(self.TimerHandler)

        self.app = None
        self.prev_app = None
        self.event_context = 'tv'

        self.lastinput_time = 0
        self.lastinput_value = None

        self.seeksteps = 0
        self.seektime_start = 0
        self.seektime_previous = 0
        self.seekevent_previous = None

        self.confirmstop_time = 0

        self.recordmenu = False
        self.recordmode = -1


    def ConfirmStop(self, msg):
        """ confirm stop event """
        confirmstop_time = int(time.time())
        # note: the OSD msg is displayed for 5 seconds
        if config.XINE_TV_CONFIRM_STOP and (confirmstop_time - self.confirmstop_time) > 4:
            self.xine.ShowMessage(msg)
            self.confirmstop_time = confirmstop_time
            return False
        else:
            return True

    def InitLiveRecording(self):
        """ start timer to mark show changes """
        self.StartTimer()

    def StartLiveRecording(self, event):
        """ start live recording """
        if event == INPUT_1:
            # record from this point on
            self.recordmode = 0
            name = self.tuner.GetChannelName()
            start = time.localtime()
            self.StopTimer()
            logger.debug('XineIvtv.StartLiveRecording: Record from now on')
        elif event == INPUT_2:
            # record from start of show
            self.recordmode = 1
            start_t, stop_t, name = self.tuner.GetInfo()
            start = time.localtime(start_t)
            self.StartTimer()
            logger.debug('XineIvtv.StartLiveRecording: Record from show start')
        elif event == INPUT_3:
            # record from start of stream
            self.recordmode = 2
            name = self.tuner.GetChannelName()
            start = time.localtime()
            self.StopTimer()
            logger.debug('XineIvtv.StartLiveRecording: Record from stream start')

        if self.recordmode in [ 0, 1, 2 ]:
            # create fil ename and kick xine
            filename_array = { 'progname': String(name), 'title': String('') }
            filemask = config.TV_RECORD_FILE_MASK % filename_array
            filemask = time.strftime(filemask, start)
            filename = tvutil.progname2filename(filemask).rstrip(' -_:')
            self.xine.Record(self.recordmode, filename)
            self.xine.ShowMessage(_('Recording: %s' % String(name)))
            logger.debug('XineIvtv.StartLiveRecording: filename=%s', String(filename))


    def StopLiveRecording(self):
        """ stop the current live recording """
        self.xine.SetMark()
        self.xine.ShowMessage(_('Recording ended'))
        self.recordmode = -1

    def StartTimer(self):
        """ program the timer to start of next show on the current channel """
        logger.debug('XineIvtv.StartTimer: Start timer')

        # set timer to mark the next program
        start_t, stop_t, prog_s = self.tuner.GetInfo()
        if stop_t > 0:
            stop_t = stop_t - time.time()
            if self.recordmode in [ 1 ]:
                # add some padding in show record mode
                stop_t = stop_t + config.TV_RECORD_PADDING_POST
            self.timer.start(stop_t)
            logger.debug('XineIvtv.StartTimer: Timer set to mark next program in: %s seconds', stop_t)
        else:
            self.timer.stop()
            logger.debug('XineIvtv.StartTimer: Timer not set, stop_t not available')
        self.tuner.ShowInfo()

    def StopTimer(self):
        """ stop timer """
        logger.debug('XineIvtv.StopTimer: Stop timer')
        self.timer.stop()

    def TimerHandler(self):
        """ handle timer event """
        logger.debug('XineIvtv.TimerHandler: Timer event, mark new show')
        if self.recordmode in [ 1 ]:
            # stop recording when recording in show mode
            self.StopLiveRecording()
        else:
            self.xine.SetMark()
        self.StartTimer()

    def Play(self, mode, channel=None, channel_change=0):
        """ Start the xine player """
        logger.debug('XineIvtv.Play(mode=%r, channel=%r, channel_change=%r)', mode, channel, channel_change)

        self.mode = mode
        rc.add_app(self)
        self.mixer.Mute()
        self.xine.Start()
        self.tuner.SetChannelByName(channel, True)

        # Suppress annoying audio clicks
        time.sleep(0.6)
        self.mixer.UnMute()

        if config.XINE_TV_LIVE_RECORD:
            self.InitLiveRecording()
        else:
            self.tuner.ShowInfo()

        dialog.enable_overlay_display(AppTextDisplay(self.xine.ShowMessage))

        logger.debug('Started %r app', self.mode)

    def Stop(self):
        """ Stop the xine player """
        logger.debug('XineIvtv.Stop()')
        dialog.disable_overlay_display()
        self.mixer.Stop()
        self.tuner.Stop()
        self.xine.Stop()
        rc.remove_app(self)
        rc.post_event(PLAY_END)
        logger.debug('Stopped %r app', self.mode)

    def eventhandler(self, event, menuw=None):
        """ Event handler """
        logger.debug('XineIvtv.eventhandler(event=%r)', event.name)

        if self.recordmode in [ 0, 1, 2 ]:
            # handle event while live recording is active
            if event in [ TV_START_RECORDING, STOP ]:
                if self.ConfirmStop(_('Live Recording active, please repeat to stop')):
                    self.StopLiveRecording()
                    self.StartTimer()
                return True
            elif event in [ 'POPCHANNEL', TV_CHANNEL_UP, TV_CHANNEL_DOWN,
                            INPUT_0, INPUT_1, INPUT_2, INPUT_3, INPUT_4,
                            INPUT_5, INPUT_6, INPUT_7, INPUT_8, INPUT_9 ]:
                self.xine.ShowMessage(_('Recording in progress!'))
                return True

        if self.recordmenu:
            # handle event while menu mode is displayed
            if event in [ INPUT_1, INPUT_2, INPUT_3 ]:
                self.StartLiveRecording(event)
                self.xine.HideMenu()
                self.recordmenu = False
                return True
            elif event in [ TV_START_RECORDING, STOP ]:
                self.xine.HideMenu()
                self.recordmenu = False
                return True
            elif event in [ 'POPCHANNEL', TV_CHANNEL_UP, TV_CHANNEL_DOWN,
                            INPUT_0, INPUT_4, INPUT_5, INPUT_6,
                            INPUT_7, INPUT_8, INPUT_9 ]:
                # ignore these commands in record menu mode
                return True

        if event in [ TV_START_RECORDING ]:
            if config.XINE_TV_LIVE_RECORD:
                self.xine.ShowMenu("Start Recording~From now on~Current show~Everything")
                self.recordmenu = True
            else:
                self.xine.ShowMessage(_('Live Recording is not enabled'))
            return True

        if event in [ STOP, PLAY_END ]:
            if self.ConfirmStop(_('Please repeat to stop')):
                self.Stop()

        if event in [ PAUSE, PLAY ]:
            self.xine.Pause()

        if event in [ 'POPCHANNEL' ]:
            self.tuner.PopChannel()

        if event in [ 'TOGGLECHANNEL' ]:
            self.tuner.SwapChannel()
            return True

        if event in [ TV_CHANNEL_UP ]:
            # tune next channel
            self.tuner.NextChannel()

        if event in [ TV_CHANNEL_DOWN ]:
            # tune previous channel
            self.tuner.PrevChannel()

        if event in [ INPUT_0, INPUT_1, INPUT_2, INPUT_3, INPUT_4,
                      INPUT_5, INPUT_6, INPUT_7, INPUT_8, INPUT_9 ]:
            s_event = '%r' % event
            eventInput=s_event[6]
            isNumeric=TRUE
            try:
                newinput_value = int(eventInput)
            except:
                # Protected against INPUT_UP, INPUT_DOWN, etc
                isNumeric=FALSE

            if isNumeric:
                # tune explicit channel
                newinput_time = int(time.time())

                if self.lastinput_value is not None:
                    # allow 2 seconds delay for multiple digit channels
                    if newinput_time - self.lastinput_time < 2:
                        # this enables multiple (max 3) digit channel selection
                        if self.lastinput_value >= 100:
                            self.lastinput_value = (self.lastinput_value % 100)
                        newinput_value = self.lastinput_value * 10 + newinput_value

                self.lastinput_value = newinput_value
                self.lastinput_time = newinput_time

                if config.XINE_TV_INPUT_REAL_CHANNELS:
                    self.tuner.SetChannelByNumber(newinput_value)
                else:
                    self.tuner.SetChannelByIndex(newinput_value, 1)

                if newinput_value > 9:
                    # cancel intermediate channels
                    self.tuner.UnpushChannel()

        if event in [ SEEK ]:
            seeksteps = int(event.arg)
            direction = 0

            if seeksteps == 0:
                logger.debug('Ignoring seek 0')
            else:
                if seeksteps < 0:
                    direction = -1
                    seeksteps = 0 - seeksteps
                else:
                    direction = +1

                if config.XINE_TV_PROGRESSIVE_SEEK:
                    seekevent_current = event.arg
                    seeksteps_current = seeksteps
                    seektime_current = int(time.time())
                    seektime_delta = seektime_current - self.seektime_previous

                    if seektime_delta > 2 or seekevent_current != self.seekevent_previous:
                        # init/reset progressive seek mode
                        self.seeksteps = seeksteps
                        self.seektime_start = seektime_current
                        self.seektime_previous = seektime_current
                    else:
                        # continue progressive seek mode
                        if seektime_delta > 0:
                            if (seektime_delta % config.XINE_TV_PROGRESSIVE_SEEK_THRESHOLD) == 0:
                                self.seeksteps += config.XINE_TV_PROGRESSIVE_SEEK_INCREMENT
                                self.seektime_previous = seektime_current

                    self.seekevent_previous = seekevent_current
                    seeksteps = self.seeksteps

                # Note: Xine 2007 versions supports
                # arbitrary SeekRelative+/- steps
                # limit seeksteps to [1 ; 120] seconds
                seeksteps = min( max(1, seeksteps), 120 )

                self.xine.Seek(direction, seeksteps)

        if event in [ TOGGLE_OSD ]:
            self.tuner.ShowInfo()

        if event in [ OSD_MESSAGE ]:
            self.xine.ShowMessage(event.arg)

        if config.XINE_TV_LIVE_RECORD:
            if event in [ 'POPCHANNEL', TV_CHANNEL_UP, TV_CHANNEL_DOWN,
                          INPUT_0, INPUT_1, INPUT_2, INPUT_3, INPUT_4,
                          INPUT_5, INPUT_6, INPUT_7, INPUT_8, INPUT_9 ]:
                # explicitly mark video stream
                self.xine.SetMark()
                # start timer to mark next show
                self.StartTimer()

        return True


class TunerControl:
    """
    Class that controls the tuner device
    """
    def __init__(self, xine):
        """ TunerControl constructor """
        self.xine = xine
        self.ivtv_init = False
        self.fc = FreevoChannels()
        self.curr_channel = None
        self.embed = None
        self.stack = [ ]

    def _kill_(self):
        """ TunerControl destructor """
        if self.embed:
            ivtv_dev.setvbiembed(self.embed)

    def Stop(self):
        """ stop """
        self.ivtv_init = False

    def GetChannelName(self):
        """ get channel info """
        tuner_id, chan_name, prog_info = self.fc.getChannelInfo(showtime=False)
        return (chan_name)

    def GetProgramName(self):
        """ get channel name """
        tuner_id, chan_name, prog_info = self.fc.getChannelInfo(showtime=True)
        return prog_info

    def GetInfo(self):
        """ get channel info """
        tuner_id, chan_id, chan_name, start_t, stop_t, prog_s = self.fc.getChannelInfoRaw()
        return (start_t, stop_t, prog_s)

    def ShowInfo(self):
        """ show channel info """
        if self.curr_channel is not None:
            tuner_id, chan_name, prog_info = self.fc.getChannelInfo(showtime=False)
            self.xine.ShowMessage(msg = '%s: %s' % (chan_name, prog_info))

    def PushChannel(self):
        """ push the current channel on the channel stack """
        if self.curr_channel is not None:
            self.stack.append(self.curr_channel)
            logger.debug('TunerControl: Pushed channel %s', self.curr_channel)
        logger.debug('TunerControl: Channel stack = %s', self.stack)

    def UnpushChannel(self):
        """ remove the top channel from the channel stack """
        if len(self.stack) == 0:
            logger.debug('TunerControl: Channel stack is empty')
        else:
            channel = self.stack.pop()
            logger.debug('TunerControl: Unpushed channel %s', channel)
        logger.debug('TunerControl: Channel stack = %s', self.stack)

    def PopChannel(self):
        """ pop the top channel from the channel stack and switch channel """
        if len(self.stack) == 0:
            logger.debug('TunerControl: Channel stack is empty')
        else:
            channel = self.stack.pop()
            logger.debug('TunerControl: Popped channel %s', channel)
            self.SetVideoGroup(channel)
        logger.debug('TunerControl: Channel stack = %s', self.stack)

    def SwapChannel(self):
        """swap the current display channel and the top of the stack channel """
        if self.curr_channel is not None:
            toswap = self.curr_channel
            if len(self.stack) == 0:
                logger.debug('TunerControl: Channel stack is empty')
            else:
                channel = self.stack.pop()
                logger.debug('TunerControl: Popped channel %s', channel)
                self.SetVideoGroup(channel)
                self.stack.append(toswap)
                logger.debug('TunerControl: Pushed channel %s', toswap)
        logger.debug('TunerControl: Channel stack = %s', self.stack)


    def SetChannelByName(self, channel=None, clearstack=False):
        """ tune to a new channel by name """
        last_channel = self.curr_channel
        next_channel = None
        channel_index = -1

        if clearstack:
            self.stack = [ ]
            self.curr_channel = None

        if channel is None:
            # get a channel
            next_channel = self.fc.getChannel()

        try:
            # lookup the channel name in TV_CHANNELS
            for pos in range(len(config.TV_CHANNELS)):
                entry = config.TV_CHANNELS[pos]
                if str(channel) == str(entry[2]):
                    channel_index = pos
                    next_channel = channel
                    break
        except ValueError:
            pass

        if next_channel is None:
            logger.warning('TunerControl: Cannot find tuner channel %r in the TV channel listing', channel)
        else:
            self.SetChannelByIndex(channel_index + 1)

    def SetChannelByIndex(self, channel, tvlike=0):
        """ tune to a channel by index from the TV_CHANNELS list """
        next_channel = self.fc.getManChannel(channel, tvlike)
        logger.debug('TunerControl: Explicit channel selection by index = %r', next_channel)
        self.PushChannel()
        self.SetVideoGroup(next_channel)

    def SetChannelByNumber(self, channel):
        """ tune to a channel by actual channel number """
        logger.debug('TunerControl: Explicit channel selection by number = %r', channel)
        self.PushChannel()
        self.SetVideoGroup(channel)

    def NextChannel(self):
        """ jump to the next channel in the TV_CHANNELS list """
        next_channel = self.fc.getNextChannel()
        logger.debug('TunerControl: Next channel selection = %r', next_channel)
        self.PushChannel()
        self.SetVideoGroup(next_channel)

    def PrevChannel(self):
        """ jump to the previous channel in the TV_CHANNELS list """
        prev_channel = self.fc.getPrevChannel()
        logger.debug('TunerControl: Previous channel selection = %r', prev_channel)
        self.PushChannel()
        self.SetVideoGroup(prev_channel)

    def SetVideoGroup(self, channel):
        """ select a channel's video group and tune to that channel """
        try:
            channel_num = int(channel)
        except ValueError:
            channel_num = 0
        logger.debug('TunerControl: Channel: %r', channel)
        new_vg = self.fc.getVideoGroup(channel, True)
        logger.debug('TunerControl: Group: type=%r, desc=%r', new_vg.group_type, new_vg.desc)
        logger.debug('TunerControl: Input: type=%r, num=%r', new_vg.input_type, new_vg.input_num)

        if new_vg.group_type != 'ivtv':
            logger.error('TunerControl: VideoGroup %s is not supported', new_vg)
            pop = AlertBox(text=_('This plugin only supports the ivtv video group!'))
            pop.show()
            return

        # check if videogroup switch is needed
        switch_vg = not self.ivtv_init or self.curr_channel is None or \
                    new_vg != self.fc.getVideoGroup(self.curr_channel, True)

        if switch_vg:
            # switch to a different video group
            logger.info('TunerControl: Set VideoGroup: %s', new_vg)
            ivtv_dev = ivtv.IVTV(new_vg.vdev)
            ivtv_dev.init_settings()
            self.xine.SetInput(new_vg.input_num)
            # disable embedded vbi data
            self.embed = ivtv_dev.getvbiembed()
            ivtv_dev.setvbiembed(0)

        if not self.ivtv_init:
            # set channel directly on v4l device, if channel is not negative
            if channel_num >= 0:
                self.fc.chanSet(channel, True)
            self.curr_channel = channel
            self.ivtv_init = True
        else:
            # set channel through xine process
            freq = self.fc.chanSet(channel, True, 'ivtv_xine_tv', None)

            if freq != 0:
                # channel has frequency
                logger.debug('TunerControl: Set frequency: %s', freq)
                self.xine.SetFrequency(freq)
            else:
                # channel has no frequency
                logger.debug('TunerControl: Channel has no frequency')

            self.curr_channel = channel
            self.xine.SeekEnd()
            self.ShowInfo()

        self.SetAudioByChannel(channel)

    def SetAudioByChannel(self, channel=-1):
        """
        Set the PVR sound level
        This is a mix : The base volume is set by the avol
        option in each TV_VIDEO_GROUP. The value is hardware dependant.
        seems bo be between 0 and 65535.
        If this value is missing in the tv_video_group, that sub does nothing
        If the value is present, the actual audio value is this value
        time the 6th field in TV_CHANNELS (expressed in % )
        """
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
        vg = self.fc.getVideoGroup(channel, True)
        try:
            ivtv_avol = vg.avol
        except AttributeError:
            ivtv_avol = 0
        if ivtv_avol <= 0:
            logger.debug('SetAudioByChannel: The tv_video group for %r doesn\'t set the volume', channel)
        else:
            # Is there a specific volume level in TV_CHANNELS_VOLUME
            ivtv_dev = ivtv.IVTV(vg.vdev)
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
            logger.debug('SetAudioByChannel: Current PVR Sound level is : %s', ivtv_dev.getctrl(0x00980905))
            logger.debug('SetAudioByChannel: Set the PVR Sound Level to : %s (%s * %s)', avol, ivtv_avol, avol_percent)
            ivtv_dev.setctrl(0x00980905, avol)
            logger.debug('SetAudioByChannel: New PVR Sound level is : %s', ivtv_dev.getctrl(0x00980905))


class MixerControl:
    """
    Class that controls the mixer device
    """
    def __init__(self, xine):
        """ MixerControl constructor """
        self.xine = xine
        self.mixer = plugin.getbyname('MIXER')
        self.volume = 0

    def Mute(self):
        """ turn down volume """
        if self.mixer is not None:
            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.volume = self.mixer.getMainVolume()
                self.mixer.setMainVolume(0)

            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.volume = self.mixer.getPcmVolume()
                self.mixer.setPcmVolume(0)

    def UnMute(self):
        """ turn up volume """
        if self.mixer is not None:
            self.mixer.setLineinVolume(config.MIXER_VOLUME_TV_IN)
            self.mixer.setIgainVolume(config.MIXER_VOLUME_TV_IN)

            if config.MIXER_MAJOR_CTRL == 'VOL':
                self.mixer.setMainVolume(self.volume)

            elif config.MIXER_MAJOR_CTRL == 'PCM':
                self.mixer.setPcmVolume(self.volume)

    def Stop(self):
        """ turn down volume """
        if self.mixer is not None:
            self.mixer.setLineinVolume(0)
            self.mixer.setMicVolume(0)
            self.mixer.setIgainVolume(0)


class XineApp(childapp.ChildApp2):
    """
    Class that controls the Xine process
    """
    def __init__(self, app):
        """ XineApp constructor """
        logger.debug('XineApp.__init__(app=%r)', app)
        childapp.ChildApp2.__init__(self, app)
        self.exit_type = None

    def stdout_cb(self, line):
        logger.debug('XineApp.stdout_cb() = %r', line)

    def write(self, line):
        logger.debug('XineApp.write = %r', line)
        childapp.ChildApp2.write(self, line)


class XineControl:
    """
    Thread that handles Xine commands
    """
    def __init__(self):
        """ XineControl constructor """
        logger.debug('XineControl.__init__()')
        self.app = None
        self.session_id = 0
        self.notahead = False
        self.ispaused = False

        try:
            xinecmd = config.XINE_COMMAND.split(' ')[0].split('/')[-1]
            self.fbxine = xinecmd in ('fbxine', 'df_xine')
        except:
            xinecmd = ''
            self.fbxine = False

        logger.debug('XineControl: configuration overview')
        logger.debug('    config.CONF.xine = %r', config.CONF.xine)
        logger.debug('    config.XINE_COMMAND = %r', config.XINE_COMMAND)
        logger.debug('    config.XINE_ARGS_DEF = %r', config.XINE_ARGS_DEF)
        logger.debug('    config.XINE_TV_VO_DEV = %r', config.XINE_TV_VO_DEV)
        logger.debug('    config.XINE_TV_AO_DEV = %r', config.XINE_TV_AO_DEV)
        logger.debug('    config.XINE_TV_TIMESHIFT_FILEMASK = %r', config.XINE_TV_TIMESHIFT_FILEMASK)
        logger.debug('    effective xinecmd = %r', xinecmd)
        logger.debug('    effective self.fbxine = %r', self.fbxine)

        if self.fbxine:
            self.command = '%s %s --stdctl pvr://%s' % \
                (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_TIMESHIFT_FILEMASK)
        else:
            self.command = '%s %s -V %s -A %s --stdctl pvr://%s' % \
                (config.XINE_COMMAND, config.XINE_ARGS_DEF, config.XINE_TV_VO_DEV, \
                config.XINE_TV_AO_DEV, config.XINE_TV_TIMESHIFT_FILEMASK)

    def ShowMessage(self, msg):
        """ display a message in the xine player """
        logger.debug('XineControl.ShowMessage=%r', msg)
        if config.XINE_TV_INDENT_OSD:
            msg = '    %s' % msg
        self.app.write('OSDWriteText$%s\n' % String(msg))

    def ShowMenu(self, menu):
        """ display a menu in the xine player """
        logger.debug('XineControl.ShowMenu=%r', menu)
        self.app.write("OSDShowCustomMenu$%s\n" % menu)

    def HideMenu(self):
        """ hide menu in the xine player """
        logger.debug('XineControl.HideMenu')
        self.app.write("OSDHideCustomMenu\n")

    def SetInput(self, input):
        """ set a different input """
        logger.debug('XineControl.SetInput=%r', input)
        self.app.write('PVRSetInput#%s\n' % input)

    def SetFrequency(self, freq):
        """ set a different frequency """
        logger.debug('XineControl.SetFrequency=%r', freq)
        self.app.write('PVRSetFrequency#%s\n' % freq)

    def SetMark(self):
        """ set a mark in the video stream """
        logger.debug('XineControl.SetMark()')
        if self.ispaused:
            self.Pause()

        self.session_id = self.session_id + 1
        self.app.write('PVRSetMark#%s\n' % self.session_id)

    def Seek(self, direction, steps):
        """ Skip in stream """
        logger.debug('XineControl.Seek(direction=%r, steps=%r)', direction, steps)
        if direction < 0:
            self.app.write('%s#%s\n' % ('SeekRelative-', steps))
        if direction > 0:
            self.app.write('%s#%s\n' % ('SeekRelative+', steps))

    def SeekEnd(self):
        """ Skip to end of stream
        The notahead flag indicates if the user has used the pause or rewind
        buttons. That implies that the seek is needed.
        """
        logger.debug('XineControl.SeekEnd()')
        if self.ispaused:
            self.Pause()
        if self.notahead:
            self.app.write('SetPosition100%\n')
            self.notahead = False

    def Start(self):
        """ start playing """
        logger.debug('XineControl.Start()')
        self.app = XineApp(self.command)
        self.ispaused = False

    def Pause(self):
        """ pause playing """
        logger.debug('XineControl.Pause() / Unpause')
        self.app.write('pause\n')
        self.ispaused = not self.ispaused
        self.notahead = True

    def Record(self, mode, name):
        """ record stream """
        logger.debug('XineControl.Record(mode=%r, name=%r)', mode, name)
        self.app.write('PVRSave#%s\n' % mode)
        self.app.write('PVRSetName$%s\n' % name)

    def Stop(self):
        """ stop playing """
        logger.debug('XineControl.Stop()')
        self.app.stop('quit\n')
        logger.debug('XineControl: Xine ended')
