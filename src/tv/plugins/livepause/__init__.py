# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# the Freevo Live Pause module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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

import kaa
import config     # Configuration handler. reads config file.
import plugin
import rc         # The RemoteControl class.
import dialog

import tv.dialogs
from tv.channels import FreevoChannels
from event import *

from tv.plugins.livepause.events import *
from tv.plugins.livepause.record import *
from tv.plugins.livepause import backend

from tv.plugins.livepause import display
from tv.plugins.livepause import players

import dialog.dialogs

WAIT_FOR_DATA_COUNT   = 1
WAIT_FOR_DATA_TIMEOUT = 20 # Seconds

STARVED_PAUSE_COUNT = 3

class State:
    IDLE      = 'Idle'
    TUNING    = 'Tuning'
    BUFFERING = 'Buffering'
    PLAYING   = 'Playing'

class PluginInterface(plugin.DaemonPlugin):
    """
    Plugin to allowing pausing live TV.

    This plugin supports the following features:
        - Live TV: pause & continue, seek forward & backward
        - Subtitles: Allows you to toggle though the available languages
          (Requires either vlc or xine)
        - Instant recording of the current program being viewed.
        - Buffers current channel even when you exit back to the guide
          (Buffers up to a configurable number of minutes while in guide)
        - Multiple digit channel selection: '1', '12, '123'
        - OSD messges: volume, channel info and position within the buffer.
        - Streaming from a remote computer using:
            - DVBStreamer for ATSC/DVB from a PCI card or USB adapter
            - HDHomeRun

    ===========================================================================
    Requirements
    ===========================================================================

    A source of digital TV, either DVBStreamer (running locally or remotely) or
    a HDHomeRun box.

    At least one of the following players installed (in order or preferences):
        1. vlc
        2. xine
        3. mplayer

    ===========================================================================
    Configuration
    ===========================================================================
    The following items should be configured in local_conf.py:

    Freevo General Config Items
        - TV_CHANNELS
        - TV_VIDEO_GROUPS

    Plugin specific options
        - LIVE_PAUSE2_BUFFER_PATH
        - LIVE_PAUSE2_BUFFER_SIZE
        - LIVE_PAUSE2_BUFFER_TIMEOUT
        - LIVE_PAUSE2_INSTANT_RECORD_LENGTH
        - LIVE_PAUSE2_PREFERRED_PLAYER

    ===========================================================================
    Video Group Configuration
    ===========================================================================
    Configure your video groups as you would normally (see freevo wiki for more
    details) then follow the instructions below:

    For DVBStreamer::

        vdev = for local DVBStreamer '<dvb adapter number>'
            ie. for DVBStreamer running on adapter 0
            vdev='0'
        for remote DVBStreamer '<remote ip>:<dvb adapter number>'
            ie. for DVBStreamer running on host 192.168.1.5 dvb adapter 1
            vdev='192.168.1.5:1'

        group_type = 'dvb'

    For HDHomeRun::

        vdev = '<HDHomeRun id>:<tuner id>'
        The HDHomeRun id and tuner id are the same as those passed to
        hdhomerun_config.

        group_type = 'hdhomerun'
    """

    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        # Determine size and location of the live buffer

        self.event_listener = True

        self.livepause = LivePauseController(players.get_player())
        plugin.register(self.livepause, plugin.TV, False)

    def shutdown(self):
        """
        Shutdown callback.
        """
        _debug_('Shutting down livepause')
        self.livepause.shutdown()


    def eventhandler(self, event=None, menuw=None):
        """
        Handle PLAY_START events from other players so we stop buffering and give
        the disk a break.
        """
        if event == PLAY_START and self.livepause.state == State.IDLE:
            _debug_('Disabling livepause buffering!')
            self.livepause.disable_buffering()
        return False


    def config(self):
        """
        Gets the required configuration variables
        """
        from tv.plugins.livepause import backend
        return [('LIVE_PAUSE2_BUFFER_PATH', '/tmp/freevo/livepause', 'Location of the buffer file used for pausing live TV'),
                ('LIVE_PAUSE2_BUFFER_SIZE', 2048, 'Maximum size of the pause buffer in MB. (Default 2GB)'),
                ('LIVE_PAUSE2_BUFFER_TIMEOUT', 5*60, 'Timeout to disable buffering after exiting watching tv'),
                ('LIVE_PAUSE2_INSTANT_RECORD_LENGTH', 2*60*60, 'Length of time to record, in seconds, if no program data is available. (Default: 2Hours)'),
                ('LIVE_PAUSE2_PREFERRED_PLAYER', None, 'Preferred player to use (one of vlc,xine,mplayer) or None to select the best one available.'),
                ('LIVE_PAUSE2_PORT', backend.MEDIA_SERVER_PORT, 'TCP Port to use for the livepause server.'),
                ('LIVE_PAUSE2_BACKEND_SERVER_IP', None, 'IP address of the server to use as the backend.'),
                ('LIVE_PAUSE2_BACKEND_SERVER_PORT', backend.BACKEND_SERVER_PORT, 'Port of the remote backend server.'),
                ('LIVE_PAUSE2_BACKEND_SERVER_SECRET', backend.BACKEND_SERVER_SECRET, 'Secret phrase that must match on the backend server.')
                ]

###############################################################################
# Live Pause Control Class
###############################################################################
class LivePauseController:
    """
    The main class to control play back.
    """
    def __init__(self, player):
        self.name = 'livepause'
        self.app_mode  = 'tv'

        self.fc = FreevoChannels()

        self.backend = backend.get_backend()
        self.backend.set_mode(player.mode)

        self.last_channel = None
        self.stop_time = 0
        self.data_started_timer = kaa.OneShotTimer(self.__buffering_data_timedout)
        self.disable_buffering_timer = kaa.OneShotTimer(self.__disable_buffering_timeout)

        self.state = State.IDLE
        self.player = player

        self.changing_channel = False

        self.subtitles = None
        self.subtitle_index = -1

        self.audio_langs = None
        self.audio_lang_index = -1

        self.recording = False

        self.state_dialog = None

        # Setup Event Maps
        self.event_maps = {}
        self.event_maps[State.IDLE] = {}

        self.event_maps[State.TUNING] = {
            'DATA_STARTED' : self.__tuning_data_started,
            'DATA_TIMEDOUT': self.__tuning_data_timedout,
            'PLAY_END'     : self.__handle_stop,
            'USER_END'     : self.__handle_stop,
            'STOP'         : self.__handle_stop
            }

        self.event_maps[State.BUFFERING] = {
            'DATA_ACQUIRED': self.__buffering_data_acquired,
            'DATA_TIMEDOUT': self.__buffering_data_timedout,
            'PLAY_END'     : self.__handle_stop,
            'USER_END'     : self.__handle_stop,
            'STOP'         : self.__handle_stop
            }

        self.event_maps[State.PLAYING] = {
            'PLAY'                : self.__playing_play_pause,
            'PAUSE'               : self.__playing_play_pause,
            'PLAY_END'            : self.__handle_stop,
            'USER_END'            : self.__handle_stop,
            'STOP'                : self.__handle_stop,
            'TV_CHANNEL_UP'       : self.__playing_tv_channel_up,
            'TV_CHANNEL_DOWN'     : self.__playing_tv_channel_down,
            'TV_CHANNEL_NUMBER'   : self.__playing_tv_channel_number,
            'TV_START_RECORDING'  : self.__playing_tv_record,
            'SAVE_STARTED'        : self.__playing_tv_record_start,
            'SAVE_FINISHED'       : self.__playing_tv_record_stop,
            'BUTTON'              : self.__playing_button_pressed,
            'TOGGLE_OSD'          : self.__playing_display_info,
            'SEEK'                : self.__playing_seek,
            'READER_OVERTAKEN'    : self.__playing_reader_overtaken,
            'DATA_ACQUIRED'       : None,
            'DATA_TIMEDOUT'       : None,
            'VIDEO_NEXT_FILLMODE' : None,
            'VIDEO_NEXT_AUDIOMODE': None,
            'VIDEO_NEXT_AUDIOLANG': None, #self.__playing_toggle_audo_lang,
            'VIDEO_NEXT_SUBTITLE' : self.__playing_toggle_subtitles,
            }

        self.current_event_map = self.event_maps[self.state]


    def Play(self, mode, tuner_channel=None):
        """
        Start play back.
        """
        if not tuner_channel:
            tuner_channel = self.fc.getChannel()

        if plugin.getbyname('MIXER'):
            plugin.getbyname('MIXER').reset()

        self.disable_buffering_timer.stop()

        rc.app(self)

        # If it's the same channel as last time and we have come back to it after
        # more than 2 minutes start at the end of the buffer, otherwise jump
        # straight back in where we left off.
        if self.last_channel == tuner_channel:
            now = time.time()
            seconds_since_played = now - self.stop_time
            _debug_('Same channel, seconds since last playing this channel %d' % seconds_since_played)
            self.backend.set_events_enabled(True)
            if seconds_since_played > 120.0:
                # Start at the end of the buffer
                buffer_info = self.backend.get_buffer_info()
                self.backend.seekto(buffer_info[2] - 3)

            self.__change_state(State.PLAYING)
        else:
            _debug_('New channel, tuning to %s' % tuner_channel)
            self.backend.set_events_enabled(True)
            self.change_channel(tuner_channel)

        return None


    def stop(self):
        """
        Stop playback and go into idle.
        """
        _debug_('Stopping play back.')
        display.get_osd().hide()
        dialog.disable_overlay_display()
        self.player.stop()
        self.stop_time = time.time()
        self.backend.set_events_enabled(False)
        self.__change_state(State.IDLE)
        self.disable_buffering_timer.start(config.LIVE_PAUSE2_BUFFER_TIMEOUT)
        return True

    def disable_buffering(self):
        """
        Stop buffering the current channel.
        """
        self.stop_time = 0
        self.last_channel = None
        self.disable_buffering_timer.stop()
        self.backend.disable_buffering()
        _debug_('Buffering disabled.')

    def shutdown(self):
        """
        Stop buffering and the slave server.
        """
        self.disable_buffering()


    def change_channel(self, channel):
        """
        Select the correct dvbstreamer instance, change the channel
        and set the primary mrl.
        """

        if self.last_channel == channel:
            # Already tune to this channel so nothing to do!
            return
        self.fc.chanSet(channel, True)

        self.last_channel = channel
        self.backend.change_channel(channel)
        self.__change_state(State.TUNING)


    ###########################################################################
    # Event Handlers
    ###########################################################################
    def eventhandler(self, event, menuw=None):
        """
        Eventhandler for livepause control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        _debug_('Event %s' % event)
        event_consumed = False
        if self.state == State.PLAYING:
            event_consumed = tv.dialogs.handle_channel_number_input(event)

        if not event_consumed and event.name in self.current_event_map:
            handler = self.current_event_map[event.name]
            if handler:
                event_consumed = handler(event, menuw)
            else:
                # Event was in map but no handler so just consume the event.
                event_consumed = True

        if not event_consumed:
            _debug_('Unused event %s in state %s' % (event.name, self.state))

        return event_consumed

    def __handle_stop(self, event, menuw):
        if self.changing_channel:
            self.changing_channel = False
        else:
            self.stop()
        return True

    def __tuning_data_started(self, event, menuw):
        self.__change_state(State.BUFFERING)
        return True

    def __tuning_data_timedout(self, event, menuw):
        # Timeout while waiting for data!
        # We could display a searching for signal graphic or something here
        self.__change_state(State.IDLE)
        return True

    def __buffering_data_acquired(self, event, menuw):
        self.wait_for_data_count -= 1
        self.__draw_state_screen()
        if self.wait_for_data_count <= 0:
            self.__change_state(State.PLAYING)
        return True

    def __buffering_data_timedout(self, event, menuw):
        # Timeout while waiting for data!
        # We could display a searching for signal graphic or something here
        self.__change_state(State.IDLE)
        return True

    def __playing_play_pause(self, event, menuw):
        if self.player.paused:
            self.player.resume()
        else:
            self.player.pause()
        self.osd.display_buffer_pos(self.__get_display_info)
        return True

    def __playing_tv_channel_up(self, event, menuw):
        next_channel = self.fc.getNextChannel()

        self.changing_channel = True
        self.player.stop()

        self.change_channel(next_channel)
        return True

    def __playing_tv_channel_down(self, event, menuw):
        next_channel = self.fc.getPrevChannel()

        self.changing_channel = True
        self.player.stop()

        self.change_channel(next_channel)
        return True

    def __playing_tv_channel_number(self, event, menuw):
        next_channel = self.fc.getManChannel(event.arg)
        if self.last_channel != next_channel:
            self.changing_channel = True
            self.player.stop()

            self.change_channel(next_channel)
        return True

    def __playing_tv_record(self, event, menuw):
        if self.recording:
            self.backend.cancelsave()
            self.recording = False
        else:
            self.recording = True
            record.start_recording(self.backend, self.last_channel)

    def __playing_tv_record_start(self, event, menuw):
        dialog.show_message(_('Recording started'))

    def __playing_tv_record_stop(self, event, menuw):
        if self.state == State.PLAYING:
            dialog.show_message(_('Recording stopped'))
        self.recording = False

    def __playing_reader_overtaken(self, event, menuw):
        if self.player.paused:
            self.player.resume()
        dialog.show_message(_('Out of buffer space'))
        return True

    def __playing_button_pressed(self, event, menuw):
        consumed = False
        _debug_('Button %s' % event.arg)
        if event.arg == 'SUBTITLE':
            self.__playing_toggle_subtitles(event, menuw)
            consumed = True

        return consumed

    def __playing_toggle_subtitles(self, event, menuw):
        # Enable/Disable subtitles
        if self.subtitles:
            self.subtitle_index += 1

        else:
            self.subtitles = self.player.get_subtitles()
            self.subtitle_index = 0

        if self.subtitles:
            if self.subtitle_index >= len(self.subtitles):
                self.subtitle_index = -1

            self.player.set_subtitles(self.subtitle_index)
            if self.subtitle_index == -1:
                subtitle_text = _('Disabled')
            else:
                subtitle_text = self.subtitles[self.subtitle_index]
            dialog.show_message(_('Subtitles: %s') % subtitle_text)
        else:
            dialog.show_message(_('Subtitles not supported'))

        return True

    def __playing_toggle_audio_lang(self, event, menuw):
        if self.audio_langs:
            self.audio_lang_index += 1

        else:
            self.audio_langs = self.player.get_audio_langs()
            self.audio_lang_index = 0

        if self.audio_langs:
            if self.audio_lang_index >= len(self.audio_langs):
                self.audio_lang_index = -1

            self.player.set_audio_lang(self.audio_lang_index)
            if self.audio_lang_index == -1:
                audio_lang_text = _('Default')
            else:
                audio_lang_text = self.subtitles[self.subtitle_index]

            dialog.show_message(_('Audio language: %s') % audio_lang_text)
        else:
            dialog.show_message(_('Audio language selection not supported'))

        return True

    def __playing_display_info(self, event, menuw):
        self.osd.display_info(self.__get_display_info)
        return True

    def __get_display_info(self):
        info_dict = {}
        info_dict['channel'] = self.__get_display_channel()
        buffer_info = self.backend.get_buffer_info()
        info_dict['current_time'] = buffer_info[3]
        info_dict['start_time'] = buffer_info[1]
        info_dict['end_time'] = buffer_info[2]
        info_dict['percent_through_buffer'] = float(buffer_info[3] - buffer_info[1]) / float(buffer_info[2] - buffer_info[1])
        info_dict['percent_buffer_full'] = buffer_info[0]
        info_dict['paused'] = self.player.paused
        info_dict['recording'] = self.recording
        return info_dict

    def __playing_seek(self, event, menuw):
        steps = int(event.arg)
        buffer_info = self.backend.get_buffer_info()
        if steps > 0:
            can_seek = buffer_info[2] != buffer_info[3]
            steps = min(buffer_info[2] - buffer_info[3], steps)
        else:
            steps = max(buffer_info[1] - buffer_info[3], steps)
            can_seek = buffer_info[1] != buffer_info[3]
        if can_seek:
            self.backend.seek(steps)
            self.player.restart()
        time.sleep(0.2)
        self.osd.display_buffer_pos(self.__get_display_info)
        return True

    ###########################################################################
    # State Management
    ###########################################################################

    def __change_state(self, new_state):
        """
        Internal function to move to a new state.
        If new_state is different to the current state, set self.state to
        new_state and perform any state initialisation for the new state.
        """
        if self.state == new_state:
            # No change in state nothing todo!
            return

        _debug_('Changing state from %s to %s' % (self.state, new_state))
        old_state = self.state
        self.state = new_state
        self.current_event_map = self.event_maps[new_state]

        # State Initialisation code

        if self.state == State.IDLE:
            self.state_dialog.hide()
            rc.app(None)
            rc.post_event(PLAY_END)
            self.backend.set_events_enabled(False)

        elif self.state == State.TUNING:
            # Display the current state on the OSD
            self.__draw_state_screen()

        elif self.state == State.BUFFERING:
            self.wait_for_data_count = WAIT_FOR_DATA_COUNT
            # Display the current state on the OSD
            self.__draw_state_screen()

        elif self.state == State.PLAYING:
            # Display the current state on the OSD
            self.__draw_state_screen()

            self.player.start((self.backend.get_server_address(), config.LIVE_PAUSE2_PORT))
            dialog.enable_overlay_display(self.player.get_display())
            self.osd = display.get_osd()



    def __draw_state_screen(self):
        if self.state_dialog is None:
            self.state_dialog = StateDialog()

        percent = 0.0
        if self.state == State.BUFFERING:
            percent = float(WAIT_FOR_DATA_COUNT - self.wait_for_data_count) / float(WAIT_FOR_DATA_COUNT)

        elif self.state == State.PLAYING:
            percent = 1.0

        channel = self.__get_display_channel()
        self.state_dialog.set_state(self.state, percent, channel)
        self.state_dialog.show()

    def __get_display_channel(self):
        channel = self.last_channel

        for entry in config.TV_CHANNELS:
            if self.last_channel == entry[2]:
                channel = entry[1]

        return channel

    def __fire_channel_number(self):
        rc.post_event(TV_CHANNEL_NUMBER)
        self.channel_number_timer = None

    def __disable_buffering_timeout(self):
        self.disable_buffering()

class StateDialog(dialog.dialogs.Dialog):
    def __init__(self):
        super(StateDialog, self).__init__('livepause_state', 0.0)
        self.info_dict = {'state':State.IDLE, 'state_string':None, 'percent':0.0}

    def set_state(self, state, percent, channel):
        self.info_dict['state'] = state
        self.info_dict['percent']= percent
        if state == State.IDLE:
            self.info_dict['state_string'] = None

        elif state == State.TUNING:
            self.info_dict['state_string'] = _('Tuning to %s') % channel

        elif state == State.BUFFERING:
            self.info_dict['state_string'] = _('Buffering %s') % channel

        elif state == State.PLAYING:
            self.info_dict['state_string'] = _('Playing %s') % channel

    def get_info_dict(self):
        return self.info_dict
