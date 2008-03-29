# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# __init__.py - the Freevo Live Pause module for tv
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
import socket
import sys
import threading
import time
import traceback

import childapp
import config     # Configuration handler. reads config file.
import osd
import plugin
import rc         # The RemoteControl class.
import util


from tv.channels import FreevoChannels
from event import *

from tv.plugins.livepause.events import *
from tv.plugins.livepause.record import Recorder
from tv.plugins.livepause.chunk_buffer import ChunkBuffer

from tv.plugins.livepause import display
from tv.plugins.livepause import players
from tv.plugins.livepause import controllers

WAIT_FOR_DATA_COUNT   = 3
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

    For DVBStreamer:
        vdev = for local DVBStreamer '<dvb adapter number>'
                ie. for DVBStreamer running on adapter 0
                    vdev='0'
               for remote DVBStreamer '<remote ip>:<dvb adapter number>'
                ie. for DVBStreamer running on host 192.168.1.5 dvb adapter 1
                    vdev='192.168.1.5:1'

        group_type = 'dvb'

    For HDHomeRun:
        vdev = '<HDHomeRun id>:<tuner id>'
                The HDHomeRun id and tuner id are the same as those passed to
                hdhomerun_config.

        group_type = 'hdhomerun'
    """

    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        # Determine size and location of the live buffer
        size = config.LIVE_PAUSE2_BUFFER_SIZE
        path = config.LIVE_PAUSE2_BUFFER_PATH
        self.event_listener = True

        _debug_('live pause started: Path=%s Max Size=%dMB' % (path, size))

        self.livepause = LivePauseController(path, size, players.get_player())
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
        return [('LIVE_PAUSE2_BUFFER_PATH', '/tmp/freevo/livepause', 'Location of the buffer file used for pausing live TV'),
                ('LIVE_PAUSE2_BUFFER_SIZE', 2048, 'Maximum size of the pause buffer in MB. (Default 2GB)'),
                ('LIVE_PAUSE2_BUFFER_TIMEOUT', 5*60, 'Timeout to disable buffering after exiting watching tv'),
                ('LIVE_PAUSE2_INSTANT_RECORD_LENGTH', 2*60*60, 'Length of time to record, in seconds, if no program data is available. (Default: 2Hours)'),
                ('LIVE_PAUSE2_PREFERRED_PLAYER', None, 'Preferred player to use (one of vlc,xine,mplayer) or None to select the best one available.')
                ]

###############################################################################
# Live Pause Control Class
###############################################################################
class LivePauseController:
    """
    The main class to control play back.
    """
    def __init__(self, path, max_size, player):
        self.name = 'livepause'
        self.app_mode  = 'tv'

        self.fc = FreevoChannels()
        self.buffer = ChunkBuffer(path, max_size * (1024*1024))
        self.reader = self.buffer.get_reader()

        self.recording = None

        self.controller = None
        self.device_in_use = None
        self.last_channel = None
        self.stop_time = 0
        self.disable_buffering_timer = None

        self.state = State.IDLE
        self.player = player
        self.osd = display.get_osd(player)

        self.slave_server = SlaveServer(self.reader, self)
        self.slave_server.start()

        self.channel_number = ''
        self.channel_number_timer = None

        self.changing_channel = False

        self.subtitles = None
        self.subtitle_index = -1

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
            'PLAY'              : self.__playing_play_pause,
            'PAUSE'             : self.__playing_play_pause,
            'PLAY_END'          : self.__handle_stop,
            'USER_END'          : self.__handle_stop,
            'STOP'              : self.__handle_stop,
            'TV_CHANNEL_UP'     : self.__playing_tv_channel_up,
            'TV_CHANNEL_DOWN'   : self.__playing_tv_channel_down,
            'TV_CHANNEL_NUMBER' : self.__playing_tv_channel_number,
            'TV_START_RECORDING': self.__playing_tv_record,
            'RECORD_START'      : self.__playing_tv_record_start,
            'RECORD_STOP'       : self.__playing_tv_record_stop,
            'BUTTON'            : self.__playing_button_pressed,
            'OSD_MESSAGE'       : self.__playing_osd_message,
            'TOGGLE_OSD'        : self.__playing_display_info,
            'SEEK'              : self.__playing_seek,
            'READER_OVERTAKEN'  : self.__playing_reader_overtaken,
            'DATA_ACQUIRED'     : None,
            'DATA_TIMEDOUT'     : None,
            'INPUT_1'           : self.__playing_handle_number,
            'INPUT_2'           : self.__playing_handle_number,
            'INPUT_3'           : self.__playing_handle_number,
            'INPUT_4'           : self.__playing_handle_number,
            'INPUT_5'           : self.__playing_handle_number,
            'INPUT_6'           : self.__playing_handle_number,
            'INPUT_7'           : self.__playing_handle_number,
            'INPUT_8'           : self.__playing_handle_number,
            'INPUT_9'           : self.__playing_handle_number,
            'INPUT_0'           : self.__playing_handle_number,
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

        if self.disable_buffering_timer:
            self.disable_buffering_timer.cancel()
            self.disable_buffering_timer = None

        rc.app(self)

        # If it's the same channel as last time and we have come back to it after
        # more than 2 minutes start at the end of the buffer, otherwise jump
        # straight back in where we left off.
        if self.last_channel == tuner_channel:
            now = time.time()
            seconds_since_played = now - self.stop_time
            _debug_('Same channel, seconds since last playing this channel %d' % seconds_since_played)
            self.controller.enable_events(True)
            if seconds_since_played > 120.0:
                self.slave_server.start_at_end = True
            else:
                self.slave_server.start_at_end = False

            self.__change_state(State.PLAYING)
        else:
            _debug_('New channel, tuning to %s' % tuner_channel)
            self.change_channel(tuner_channel)

        return None


    def stop(self):
        """
        Stop playback and go into idle.
        """
        _debug_('Stopping play back.')
        self.player.stop()
        self.stop_time = time.time()
        self.controller.enable_events(False)
        self.__change_state(State.IDLE)
        self.disable_buffering_timer = threading.Timer(config.LIVE_PAUSE2_BUFFER_TIMEOUT, self.__disable_buffering_timeout)
        self.disable_buffering_timer.start()
        return True

    def disable_buffering(self):
        """
        Stop buffering the current channel.
        """
        if self.device_in_use:
            self.stop_time = 0
            self.last_channel = None
            self.controller.stop_filling()
            self.controller = None
            self.device_in_use = None
            _debug_('Buffering disabled.')

    def shutdown(self):
        """
        Stop buffering and the slave server.
        """
        if self.device_in_use:
            self.disable_buffering()

        if self.slave_server:
            self.slave_server.stop()
            self.slave_server = None
        
        if self.osd:
            self.osd.shutdown()

    def change_channel(self, channel):
        """
        Select the correct dvbstreamer instance, change the channel
        and set the primary mrl.
        """

        if self.last_channel == channel:
            # Already tune to this channel so nothing to do!
            return


        if self.device_in_use:
            self.controller.stop_filling()
            self.controller = None
            self.device_in_use = None

        # Find the controller for this VideoGroup type
        vg = self.fc.getVideoGroup(channel, True)
        self.controller = controllers.get_controller(vg.group_type)
        if not self.controller:
            _debug_('Failed to find controller for device')
            return

        self.fc.chanSet(channel, True)

        self.buffer.reset()
        self.controller.start_filling(self.buffer, vg, channel, WAIT_FOR_DATA_TIMEOUT)
        self.device_in_use = vg
        self.last_channel = channel

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
        event_consumed = self.osd.handle_event(event)

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
        next_channel = self.fc.getManChannel(int(self.channel_number))
        self.channel_number = ''

        self.changing_channel = True
        self.player.stop()

        self.change_channel(next_channel)
        return True

    def __playing_tv_record(self, event, menuw):
        if self.recording:
            self.recording.cancel()
            self.recording = None
        else:
            self.recording = Recorder(self.reader.copy(), self.last_channel)

    def __playing_tv_record_start(self, event, menuw):
        self.osd.display_message(_('Recording started'))

    def __playing_tv_record_stop(self, event, menuw):
        self.osd.display_message(_('Recording stopped'))

    def __playing_reader_overtaken(self, event, menuw):
        if self.player.paused:
            self.player.resume()
        self.osd.display_message(_('Out of buffer space'))
        return True

    def __playing_button_pressed(self, event, menuw):
        consumed = False

        if event.arg == 'SUBTITLE':
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
                self.osd.display_message(_('Subtitles: %s') % subtitle_text)
            else:
                self.osd.display_message(_('Subtitles not supported'))
            consumed = True

        elif event.arg == 'ENTER' and self.channel_number:
            self.channel_number_timer.cancel()
            rc.post_event(TV_CHANNEL_NUMBER)
            consumed = True

        return consumed

    def __playing_osd_message(self, event, menuw):
        # Filter out the volume messages so the osd can do something nice with the level
        volume_string = _('Volume: %d%%') % 0
        colon_index = volume_string.find(':')
        volume_prefix = volume_string[:colon_index]

        if event.arg.startswith(volume_prefix):
            level = int(event.arg[colon_index + 1: -1])
            self.osd.display_volume(level)

        else:
            self.osd.display_message(event.arg)
        return True

    def __playing_display_info(self, event, menuw):
        info_dict = {}
        info_dict['channel'] = self.__get_display_channel()
        info_dict['current_time'] = self.reader.get_current_chunk_time()

        chunk_reader = self.buffer.get_reader()
        info_dict['start_time'] = chunk_reader.get_current_chunk_time()
        chunk_reader.seek(chunk_reader.available_forward() - 1)
        info_dict['end_time'] = chunk_reader.get_current_chunk_time()
        cf = self.reader.available_forward()
        cb = self.reader.available_backward()
        ct = cf + cb
        info_dict['percent_through_buffer'] = float(cb) / float(ct)
        chunk_reader.close()

        del chunk_reader

        self.osd.display_info(info_dict)
        return True

    def __playing_seek(self, event, menuw):
        steps = int(event.arg)
        if steps > 0:
            can_seek = self.reader.available_forward() > 0
        else:
            can_seek = self.reader.available_backward() > 0

        if can_seek:
            self.player.pause()
            self.reader.seek_seconds(steps)
            self.player.restart()
        return True

    def __playing_handle_number(self, event, menuw):
        self.channel_number += str(event.arg)
        if len(self.channel_number) > 3:
            self.channel_number = self.channel_number[1:]
        self.osd.display_message(self.channel_number)

        if self.channel_number_timer:
            self.channel_number_timer.cancel()
        _debug_('Starting channel number timer')
        self.channel_number_timer = threading.Timer(4.0, self.__fire_channel_number)
        self.channel_number_timer.start()
        return True

    ###########################################################################
    # State Managment
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
        self.state = new_state
        self.current_event_map = self.event_maps[new_state]

        # State Initialisation code

        if self.state == State.IDLE:
            rc.app(None)
            rc.post_event(PLAY_END)
            if self.controller:
                self.controller.enable_events(False)

        elif self.state == State.TUNING:
            self.slave_server.start_at_end = True

        elif self.state == State.BUFFERING:
            self.wait_for_data_count = WAIT_FOR_DATA_COUNT

        elif self.state == State.PLAYING:
            self.player.start(self.slave_server.port)

        # Display the current state on the OSD
        self.__draw_state_screen()


    def __draw_state_screen(self):
        osd_obj = osd.get_singleton()
        percent = 0.0

        channel = self.__get_display_channel()

        if self.state == State.IDLE:
            state_string = None

        elif self.state == State.TUNING:
            state_string = _('Tuning to %s') % channel

        elif self.state == State.BUFFERING:
            state_string = _('Buffering %s') % channel
            percent = float(WAIT_FOR_DATA_COUNT - self.wait_for_data_count) / float(WAIT_FOR_DATA_COUNT)

        elif self.state == State.PLAYING:
            state_string = _('Playing %s') % channel
            percent = 1.0

        osd_obj.clearscreen(color=osd_obj.COL_BLACK)
        if state_string:
            y = (config.CONF.height / 2) - config.OSD_DEFAULT_FONTSIZE
            h = -1
            font = osd_obj.getfont(config.OSD_DEFAULT_FONTNAME, config.OSD_DEFAULT_FONTSIZE)
            osd_obj.drawstringframed(state_string, 0, y, config.CONF.width, h, font,
                fgcolor=osd_obj.COL_ORANGE, align_h='center')
            x = config.CONF.width / 4
            w = x * 2
            y = (config.CONF.height / 2) + config.OSD_DEFAULT_FONTSIZE
            h = int(20.0 * ( float(config.CONF.height) /  600.0 ))
            osd_obj.drawbox(x - 4,y - 4,x + w + 4, y + h + 4 , color=osd_obj.COL_ORANGE, width=2)
            w = int(float(w) * percent)
            osd_obj.drawbox(x,y,x + w, y +h , color=osd_obj.COL_ORANGE, fill=1)

        osd_obj.update()


    def __get_display_channel(self):
        channel = self.last_channel

        for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
            if self.last_channel == tv_tuner_id:
                channel = tv_display_name

        return channel

    def __fire_channel_number(self):
        rc.post_event(TV_CHANNEL_NUMBER)
        self.channel_number_timer = None

    def __disable_buffering_timeout(self):
        self.disable_buffering()
        self.disable_buffering_timer = None

###############################################################################
# Live Buffer Emptier Class
###############################################################################
class SlaveServer:
    """
    Class to serve data from the ring buffer over HTTP (very simple no paths, 
    only 1 connection).
    """

    def __init__(self, reader, controller):
        """
        Initialise a server to provide data to player.
        """
        self.port = 50007
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(('', self.port))
        self.socket.listen(1)
        self.reader = reader
        self.controller = controller
        self.quit = False
        self.thread = None
        self.connection = None
        self.start_at_end = False
        self.send_events = False
        self.seek_offset_next_conn = 0

    def start(self, start_at_end = False):
        """
        Start the server.
        """
        if self.thread is None:
            self.quit = False
            self.start_at_end = start_at_end
            self.thread = threading.Thread(target=self.run, name='Slave Server')
            self.thread.setDaemon(True)
            self.thread.start()


    def stop(self):
        """
        Stop the server.
        """
        if self.thread is not None:
            self.quit = True
            self.socket.close()
            if self.connection:
                self.connection.close()



    def run(self):
        """
        Thread method to listen for connection from xine slave:// and serve data from the ring buffer.
        """
        self.reader.overtaken = self.__reader_overtaken

        while not self.quit:
            # When no client is connected we don't need to inform anyone about
            # being overtaken.
            self.send_events = False

            connection, addr = self.socket.accept()
            _debug_('Connection from %s:%d reader %d< >%d'  % ( addr[0], addr[1],
                            self.reader.available_backward(), self.reader.available_forward()))
            self.__handle_connection(connection)

        _debug_('Slave server exited')
        self.thread = None

    def __handle_connection(self, connection):
        """
        Handle a connection to the slave server.
        """
        self.connection = connection
        reader = self.reader
        
        connection.send('HTTP/1.0 200 OK\n')
        connection.send('Content-type: application/octet-stream\n')
        connection.send('Cache-Control: no-cache\n\n')
        
        if self.start_at_end:
            reader.seek( reader.available_forward())
            reader.seek_seconds(- WAIT_FOR_DATA_COUNT)
            self.start_at_end = False
        elif self.seek_offset_next_conn:
            reader.seek_seconds(self.seek_offset_next_conn)

        try:
            last_time = time.time()
            count = 0
            starved_count = 0
            self.send_events = True

            while not self.quit:
                if count == 0:
                    _debug_('In data loop')
                data = reader.read(188 * 7)

                if not data:
                    starved_count += 1
                    if starved_count >= STARVED_PAUSE_COUNT:
                        _debug_('Starved!!! count=%d starved_count=%d' % (count,starved_count))
                        self.controller.player.pause()
                        time.sleep(2.0)
                        self.controller.player.resume()
                    else:
                        time.sleep(0.2)
                else:
                    starved_count = 0
                    now = time.time()
                    if last_time - now > 1.0:
                        last_time = now
                        _debug_('Sent %d bytes' %  count)
                    count += len(data)
                    connection.send(data)

        except socket.error:
            pass
        except :
            traceback.print_exc()
        try:
            connection.close()
        except:
            pass

        self.connection = None

    def __reader_overtaken(self):
        """
        Callback to handle the situation where the reader has been overtaken
        by the buffer writer.
        """
        if self.send_events:
            rc.post_event(READER_OVERTAKEN)
