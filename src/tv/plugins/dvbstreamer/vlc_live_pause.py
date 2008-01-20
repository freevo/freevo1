# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo DVBStreamer module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# This only works with vlc,  try live_pause for xine
# Only supports DVBStreamer instance on localhost.
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
import os
import re
import copy
import sys
import traceback
import math

from threading import *
from socket import *

import config     # Configuration handler. reads config file.
import rc         # The RemoteControl class.
import util
import osd
import childapp
import kaa.notifier

from tv.channels import FreevoChannels

from event import *
import plugin

from tv.plugins.dvbstreamer.manager import DVBStreamerManager
from tv.plugins.dvbstreamer import ring_buffer

WAIT_FOR_DATA_COUNT   = 3
WAIT_FOR_DATA_TIMEOUT = 20 # Seconds

EVENT_DATA_STARTED     = Event('Data Started')
EVENT_DATA_ACQUIRED    = Event('Data Acquired')
EVENT_DATA_TIMEDOUT    = Event('Data Timed Out')
EVENT_READER_OVERTAKEN = Event('Reader Overtaken')

STATE_IDLE      = 'Idle'
STATE_TUNING    = 'Tuning'
STATE_BUFFERING = 'Buffering'
STATE_PLAYING   = 'Playing'

class PluginInterface(plugin.DaemonPlugin):
    """
    DVBStreamer plugin use the dvbstreamer application to minimise channel change time.
    """

    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        self.event_listener = True
        _debug_('dvbstreamer plugin starting')

        try:
            config.VLC_COMMAND
        except:
            print String(_( 'ERROR' )) + ': ' + \
                  String(_("'VLC_COMMAND' not defined, plugin 'DVBStreamer' deactivated.\n" \
                           'please check the vlc section in freevo_config.py' ))
            return

        # Create DVBStreamer objects
        username = 'dvbstreamer'
        password = 'control'

        try:
            username = config.DVBSTREAMER_USERNAME
            password = config.DVBSTREAMER_PASSWORD
        except:
            pass

        manager = DVBStreamerManager(username, password)

        # Determine size and location of the live buffer
        bitrate, duration = config.LIVE_PAUSE_BUFFER_SIZE
        size = int((((bitrate * 1000000 * duration) / (7* 188 * 8)) + 1) * (7 * 188))
        path = config.LIVE_PAUSE_BUFFER_PATH

        # register vlc as the object to play
        self.vlc = Vlc( manager, path, size)
        plugin.register(self.vlc, plugin.TV, False)

    def shutdown(self):
        """
        Shutdown callback.
        """
        self.vlc.shutdown()


    def eventhandler(self, event=None, menuw=None):
        if event == PLAY_START and self.vlc.state == STATE_IDLE:
            print 'Disabling buffering!'
            self.vlc.disable_buffering()
        return False


    def config(self):
        """
        Gets the required configuration variables
        """
        return [
            ('DVBSTREAMER_USERNAME', 'dvbstreamer', 'Username to use when connecting to a DVBStreamer server'),
            ('DVBSTREAMER_PASSWORD', 'control', 'Password to use when connecting to a DVBStreamer server'),
            ('LIVE_PAUSE_BUFFER_PATH','/tmp/freevo/live.buf', 'Location of the file to use for pausing live TV'),
            ('LIVE_PAUSE_BUFFER_SIZE', (6.25, 30*60), 'Size of the live buffer as a tuple of max Mbps of the TV and seconds'),
            ('LIVE_PAUSE_BUFFER_TIMEOUT', 5*60, 'Timeout to disable buffering after exiting watching tv'),
        ]

###############################################################################
# Vlc Control Class
###############################################################################




class Vlc:
    """
    the main class to control vlc
    """
    def __init__(self, manager, path, size):
        self.name      = 'vlc'
        self.app_mode  = 'tv'
        self.app       = None
        self.adapter_in_use = -1
        self.fc = FreevoChannels()
        self.path = path
        self.size = size
        self.buffer = ring_buffer.RingBuffer(size, path)
        self.last_channel = None
        self.subtitles = False
        self.paused = False
        self.stop_time = 0
        self.state = STATE_IDLE
        self.manager = manager
        self.udp_receiver = UDPReceiver(self.buffer, WAIT_FOR_DATA_TIMEOUT)
        self.slave_server = SlaveServer(self.buffer, self)
        self.fill = 0
        self.cur_audio      = None
        self.cur_sub        = None
        self.cur_audiodev   = None
        self.lastchan       = None

        self.timer = kaa.notifier.Timer(self.__update_data_from_vlc)
        self.timer_start = kaa.notifier.OneShotTimer( self.__update_data_from_vlc)
        self.timer_disablebuffering = kaa.notifier.OneShotTimer( self.disable_buffering)

        if hasattr(config, 'LIVE_PAUSE_BUFFER_TIMEOUT'):
            self. buffering_timeout=config.LIVE_PAUSE_BUFFER_TIMEOUT
        else: # Disable after 5min if not LIVE_PAUSE_BUFFERING_TIMEOUT
            self.buffering_timeout= 5 * 60

        # Create the command used to start vlc.
        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset vlc rendering pipeline and
        # make it possible to seek quickly.
        self.command = [ '--prio=%s' % config.MPLAYER_NICE ] + \
                       config.VLC_COMMAND.split(' ')  + \
                       [ '--intf', 'rc' ] + \
                       ['--no-interact','--rc-fake-tty'] + \
                       [ '--sub-filter' ,'marq' ] + \
                       [ '--marq-marquee' ,'Playing' ] + \
                       [ '--marq-position','4'] + \
                       [ '--fullscreen', self.slave_server.get_vlc_mrl(),
                                         self.slave_server.get_vlc_mrl()]

        if not rc.PYLIRC and '--no-lirc' in self.command:
            self.command.remove('--no-lirc')

        self.udp_receiver.start()
        self.slave_server.start()


    def Play(self, mode, tuner_channel=None):
        """
        play with vlc
        """
        if not tuner_channel:
            tuner_channel = self.fc.getChannel()

        rc.app(self)

        same_channel = self.last_channel == tuner_channel

        # If it's the same channel as last time and we have come back to it after
        # more than 2 minutes start at the end of the buffer, otherwise jump
        # straight back in where we left off.
        if same_channel:
            if (time.time() - self.stop_time) > 120.0:
                start_at_end = True
            else:
                start_at_end = False
        else:
            self.fc.chanSet(tuner_channel, True, app=self.app)
            self.change_channel(tuner_channel)
            start_at_end = True

        if start_at_end:
            self.start_slave_server_at_end = True
            if same_channel:

                self.__change_state(STATE_PLAYING)
        else:
            self.__change_state(STATE_PLAYING)

        return None


    def stop(self, channel_change=False):
        """
        Stop vlc
        """
        if self.app:
            self.app.stop('quit\n')
            self.app = None

            if not channel_change:
                self.stop_time = time.time()
                _debug_('Shutting Down Buffering in %d secs' % self.buffering_timeout )
                self.timer_disablebuffering.start(self.buffering_timeout)
                self.__change_state(STATE_IDLE)

    def disable_buffering(self):
        """
        Stop buffering the current channel.
        """
        if self.adapter_in_use != -1:
            self.time = 0
            self.last_channel = None
            try:
                self.manager.disable_output(self.adapter_in_use)
            except:
                _debug_('Failed to disable output! ' + traceback.format_exc())
            self.adapter_in_use = -1

    def pause(self):
        """
        Pause Playback.
        """
        if self.app and not self.paused:
            _debug_('Pausing')
            self.app.write('pause\n')
            self.__osd_write('PAUSED')
            self.paused = True


    def resume(self):
        """
        Resume Playback.
        """
        if self.app and self.paused:
            _debug_('Resuming')
            self.app.write('pause\n')
            self.paused = False


    def shutdown(self):
        """
        Stop the UDP receiver and slave server.
        """
        if self.udp_receiver:
            self.udp_receiver.stop()
            self.udp_receiver = None

        if self.slave_server:
            self.slave_server.stop()
            self.slave_server = None

    def change_channel(self, channel):
        """
        Select the correct dvbstreamer instance, change the channel
        and set the primary mrl.
        """

        if self.last_channel == channel:
            # Already tune to this channel so nothing to do!
            return

        adapter = eval(self.fc.getVideoGroup(channel, True).vdev)

        if (self.adapter_in_use != -1) and (self.adapter_in_use != adapter):
            try:
                self.manager.disable_output(self.adapter_in_use)
            except:
                _debug_('Failed to disable output! ' + traceback.format_exc())

        # We are tuning to a different channel so stop receiving packets and
        # reset the ring buffer
        self.udp_receiver.pause = True
        self.buffer.rwlock.acquire_write()
        self.buffer.reset()

        self.manager.select(adapter, channel)

        if self.adapter_in_use != adapter:
            self.adapter_in_use = adapter
            try:
                self.manager.enable_udp_output(self.adapter_in_use)
            except:
                _debug_('Failed to enable output! ' + traceback.format_exc())

        # Start receiving packets and remember the channel we've just tuned to.
        self.udp_receiver.reset()
        self.udp_receiver.send_events = True
        self.udp_receiver.pause = False
        self.buffer.rwlock.release()
        self.last_channel = channel

        self.__change_state(STATE_TUNING)


    def eventhandler(self, event, menuw=None):
        """
        Eventhandler for vlc control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        event_consumed = False

        if self.state == STATE_IDLE:
            event_consumed = self.__eventhandler_idle(event, menuw)
        elif self.state == STATE_TUNING:
            event_consumed = self.__eventhandler_tuning(event, menuw)
        elif self.state == STATE_BUFFERING:
            event_consumed = self.__eventhandler_buffering(event, menuw)
        elif self.state == STATE_PLAYING:
            event_consumed = self.__eventhandler_playing(event, menuw)

        if not event_consumed:
            _debug_('Unused event %s in state %s' % (event.name, self.state))

        return event_consumed


    def __eventhandler_idle(self, event, menuw):
        """
        Internal event handler when in Idle state.
        """
        return False


    def __eventhandler_tuning(self, event, menuw):
        """
        Internal event handler when in Tuning state.
        """
        if event == EVENT_DATA_STARTED:
            self.__change_state(STATE_BUFFERING)
            return True

        if event == EVENT_DATA_TIMEDOUT:
            # Timeout while waiting for data!
            # We could display a searching for signal graphic or something here
            self.__change_state(STATE_IDLE)
            return True

        return False

    def __eventhandler_buffering(self, event, menuw):
        """
        Internal event handler when in Buffering state.
        """
        if event == EVENT_DATA_ACQUIRED:
            self.wait_for_data_count -= 1
            self.__draw_state_screen()
            if self.wait_for_data_count <= 0:
                self.__change_state(STATE_PLAYING)
            return True

        if event == EVENT_DATA_TIMEDOUT:
            # Timeout while waiting for data!
            # We could display a searching for signal graphic or something here
            self.__change_state(STATE_IDLE)
            return True

        return False


    def __eventhandler_playing(self, event, menuw):
        """
        Internal event handler when in Playing state.
        """
        if event == PAUSE or event == PLAY:
            if self.paused:
                self.resume()
            else:
                self.pause()
            return True

        if event in ( PLAY_END, USER_END, STOP ):
            self.timer.stop()
            self.stop()
            return True

        if event in [ TV_CHANNEL_UP, TV_CHANNEL_DOWN, TV_CHANNEL_LAST ] or (str(event).startswith('INPUT_') and str(event)[6:].isdigit()):
            _debug_('Event: %s' % str(event))
            if event == TV_CHANNEL_UP:
                self.lastchan = self.fc.getChannel()
                nextchan = self.fc.getNextChannel()
            elif event == TV_CHANNEL_DOWN:
                self.lastchan = self.fc.getChannel()
                nextchan = self.fc.getPrevChannel()
            elif event == TV_CHANNEL_LAST:
                if not self.lastchan:
                    return True
                nextchan = self.lastchan
                self.lastchan = self.fc.getChannel()
            else:
                self.lastchan = self.fc.getChannel()
                nextchan = self.fc.getManChannel(int(event.arg))

            self.fc.chanSet(nextchan, True, app=self.app)

            self.stop(True)

            self.change_channel(nextchan) # Moves to the Tuning state
            return True

        if event == OSD_MESSAGE:
            self.__osd_write( event.arg)
            return True

        if event == TOGGLE_OSD:
            # Write percent through ringbuffer to OSD
            channel = self.__get_display_channel()
            percent = self.slave_server.get_percent()
            now = time.strftime(config.TV_TIME_FORMAT)
            self.__osd_write('%s - %d%% - %s' % (channel, percent, now) )
            return True

        if event == SEEK:
            steps = int(event.arg)
            self.buffer.rwlock.acquire_write()
            bytes_per_sec =  self.udp_receiver.average_pps * 188
            if steps > 0:
                can_seek = self.slave_server.reader.available_forward() >= ((steps + 1) * bytes_per_sec)
            else:
                can_seek = self.slave_server.reader.available_backward() > 0

            if can_seek:
                self.slave_server.reader.seek(steps * bytes_per_sec)
                if self.mrl_index == 0:
                    self.mrl_index = 1
                    self.app.write('next\n')
                else:
                    self.mrl_index = 0
                    self.app.write('prev\n')

            self.buffer.rwlock.release()
            return True

        if event == TV_GOTO_LIVE_PLAY:
            self.buffer.rwlock.acquire_write()
            self.slave_server.reader.seek(self.slave_server.reader.available_forward())
            if self.mrl_index == 0:
                self.mrl_index = 1
                self.app.write('next\n')
            else:
                self.mrl_index = 0
                self.app.write('prev\n')
            self.buffer.rwlock.release()
            return True

        if event == EVENT_READER_OVERTAKEN:
            if self.paused:
                self.resume()
            return True

        if event == VIDEO_NEXT_FILLMODE:
            self.__set_next_fill()
            return True

        if event == VIDEO_NEXT_AUDIOLANG:
            self.__set_next_audio_track()
            return True

        if event == VIDEO_NEXT_SUBTITLE:
            self.__set_next_sub_track()
            return True

        if event == VIDEO_NEXT_AUDIOMODE:
            self.__set_next_audio_mode()
            return True

        # Consume UDP Receiver events.
        if event in (EVENT_DATA_ACQUIRED, EVENT_DATA_TIMEDOUT):
            return True

        return False


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

        # State Initialisation code

        if self.state == STATE_IDLE:
            rc.app(None)
            rc.post_event(PLAY_END)
            self.udp_receiver.send_events = False

        elif self.state == STATE_TUNING:
            self.start_slave_server_at_end = True

        elif self.state == STATE_BUFFERING:
            self.wait_for_data_count = WAIT_FOR_DATA_COUNT

        elif self.state == STATE_PLAYING:
            self.slave_server.reader_at_end = self.start_slave_server_at_end
            self.slave_server.end_offset = self.udp_receiver.average_pps * WAIT_FOR_DATA_COUNT * 188
            self.mrl_index = 0
            self.app = VlcApp(self.command, self)

            self.timer.start(60)      # Call every 60 seconds and
            self.timer_start.start(3) # at startup
            _debug_('self.timer_disablebuffering.get_interval %s' % self.timer_disablebuffering.get_interval())
            if self.timer_disablebuffering.get_interval() != None:
                self.timer_disablebuffering.stop()
            self.start_slave_server_at_end = False

        self.__draw_state_screen()


    def __osd_write(self, text):
        if self.app:
            self.app.write('marq-marquee %s\n' % text)

    def __draw_state_screen(self):
        osd_obj = osd.get_singleton()
        percent = 0.0

        channel = self.__get_display_channel()

        if self.state == STATE_IDLE:
            state_string = None

        elif self.state == STATE_TUNING:
            state_string = _('Tuning to %s' % self.__get_display_channel())

        elif self.state == STATE_BUFFERING:
            state_string = _('Buffering %s' % self.__get_display_channel())
            percent = float(WAIT_FOR_DATA_COUNT - self.wait_for_data_count) / float(WAIT_FOR_DATA_COUNT)

        elif self.state == STATE_PLAYING:
            state_string = _('Playing %s' % self.__get_display_channel())
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
            osd_obj.drawbox(x - 2,y - 2,x + w + 2, y + h + 2 , color=osd_obj.COL_ORANGE)
            w = int(float(w) * percent)
            osd_obj.drawbox(x,y,x + w, y +h , color=osd_obj.COL_ORANGE, fill=1)

        osd_obj.update()

    def __update_data_from_vlc(self):
        if self.app != None:
            self.app.write('atrack\n')
            self.app.write('adev\n')
            self.app.write('strack\n')

    def __set_next_audio_track(self):
        list = self.app.audio_tracks
        if len(list) > 0:
            if self.cur_audio == None:
                if len(list) > 1:
                    self.cur_audio = 1
                else:
                    self.cur_audio = 0

            self.cur_audio = self.__get_next_list(self.cur_audio,list)
            self.app.write('atrack %s\n' % list[self.cur_audio])
            if list[self.cur_audio] == '-1':
                self.__osd_write('Audio Track Disabled')
            else:
                self.__osd_write('Audio Track %d' % (self.cur_audio ) )
        else:
            self.__osd_write('audio track none')
        return True

    def __set_next_audio_mode(self):
        list = self.app.audio_chans
        if len(list) > 0:
            if self.cur_audiodev == None:
                if len(list) > 1: # STEREO
                    self.cur_audiodev = 2
                else:   # MONO
                    self.cur_audiodev = 1

            self.cur_audiodev = self.__get_next_list(self.cur_audiodev,list)
            self.app.write('adev %s\n' % list[self.cur_audiodev ])

            if list[self.cur_audiodev ] == '1':
                self.__osd_write('Audio Out: Mono' )
            if list[self.cur_audiodev ] == '2':
                self.__osd_write('Audio Out: Stereo' )
            if list[self.cur_audiodev ] == '4':
                self.__osd_write('Audio Out: 2 Front 2 Rear' )
            if list[self.cur_audiodev ] == '6':
                self.__osd_write('Audio Out: 5.1 channel' )
            if list[self.cur_audiodev ]  == '10':
                self.__osd_write('Audio Out: A/52 over S/PDIF' )
        else:
            self.__osd_write('Audio Out: unknown')
        return True

    def __get_next_list(self,current,list):
        for i in range (len(list)):
            if i == current:
                if i+1 < len(list):
                    return i+1
                else:
                    return 0
                break

    def __set_next_sub_track(self):
        # should work but untested , Maybe vlc doesn't understand mpeg-ts subs
        list = self.app.sub_tracks
        if len(list) > 0 :
            if self.cur_sub == None:
                if len(list) >1:
                    self.cur_sub = 1
                elif self.cur_sub == None:
                    self.cur_sub = 0

            self.cur_sub = self.__get_next_list(self.cur_sub,list)
            self.app.write('strack %s\n' % list[self.cur_sub])
            if list[self.cur_audio] == '-1':
                self.__osd_write('Subtitle Track Off' )
            else:
                self.__osd_write('Subtitle Track %d' % self.cur_sub )
        else:
            self.__osd_write('Subtitle Track none')
        return True

    def __set_next_fill(self):
        cmdlist = ['Default','vcrop 16:10','vcrop 16:9','vcrop 4:3','vratio 16:10','vratio 16:9','vratio 4:3']
        textlist = ['Default','Crop 16:10','Crop 16:9','Crop 4:3','Ratio 16:10','Ratio 16:9','Ratio 4:3']
        self.fill=self.__get_next_list(self.fill,cmdlist)
        self.app.write('vcrop Default\n')
        self.app.write('vratio Default\n')
        self.app.write('%s\n' % cmdlist[self.fill])
        self.__osd_write('Video Fill %s' % textlist[self.fill] )

    def __get_display_channel(self):
        channel = self.last_channel

        for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
            if self.last_channel == tv_tuner_id:
                channel = tv_display_name

        return channel

###############################################################################
# Live Buffer Filler/Emptier Classes
###############################################################################

class UDPReceiver:
    """
    Class to receive UDP packets sent by DVBStreamer and write them into
    a ring buffer.
    """

    def __init__(self, buffer, timeout_count):
        """
        Create a UDP Receiver to write into the ring buffer specified in buffer.
        """
        # Create socket and bind to address
        self.socket = socket(AF_INET,SOCK_DGRAM)
        self.socket.bind(('', 1234))
        self.socket.settimeout(1.0)
        self.buffer = buffer
        self.quit = False
        self.thread = None
        self.send_events = False
        self.data_timeout_count = timeout_count
        self.pause = False
        self.average_pps = 0 # Average packets per second


    def start(self):
        """
        Start a thread to receive UDP packets.
        """
        if self.thread is None:
            self.quit = False

            self.thread = Thread(target=self.run, name='UDP Receiver')
            self.thread.setDaemon(True)
            self.thread.start()


    def stop(self):
        """
        Stop the thread receiving UDP packets.
        """
        if self.thread is not None:
            self.quit = True
            self.socket.close()

    def reset(self):
        self.average_pps = 0
        self.data_received = False

    def run(self):
        """
        Thread method to receive UDP packets.
        """
        buffer_size = 188*7
        ringbuffer = self.buffer
        last_time = 0
        self.data_received = False
        byte_count = 0
        timeout_count = 0

        while not self.quit:
            try:
                data,addr = self.socket.recvfrom(buffer_size)
                if data and not self.pause:
                    timeout_count = 0


                    if not self.data_received:
                        # We've not had any data yet on the current channel so
                        # clear some state and send an event to say the data
                        # has started.

                        self.data_received = True
                        last_time = time.time()
                        byte_count = 0

                        if self.send_events:
                            _debug_('Sending data started')
                            rc.post_event(EVENT_DATA_STARTED)

                    ringbuffer.write(data)

                    # Keep track of how much data we've received to determine
                    # the average number of packets per second.
                    byte_count += len(data)

                    now = time.time()
                    time_diff = now - last_time
                    if time_diff >= 1.0:
                        last_time = now
                        if self.average_pps == 0:
                            self.average_pps = int(byte_count / 188)
                        else:
                            self.average_pps = int((((self.average_pps * 188) + byte_count) / 2) / 188)
                        byte_count = 0

                        if self.send_events:
                            rc.post_event(EVENT_DATA_ACQUIRED)

            except timeout:
                if not self.pause:
                    timeout_count += 1
                    if (timeout_count > self.data_timeout_count) and self.send_events:
                        rc.post_event(EVENT_DATA_TIMEDOUT)
            except:
                traceback.print_exc()
        self.thread = None


class SlaveServer:
    """
    Class to serve data to vlc http://
    """

    def __init__(self, buffer, controller):
        """
        Initialise a server to provide data to vlc.
        """
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.bind(('', 50007))
        self.socket.listen(1)
        self.buffer = buffer
        self.controller = controller
        self.quit = False
        self.thread = None
        self.connection = None
        self.reader_at_end = False
        self.end_offset = 0


    def get_vlc_mrl(self):
        # using http:// rather than tcp://
        # Playback is smoother
        return 'http://@127.0.0.1:50007'


    def start(self, reader_at_end = False):
        """
        Start a server to serve VLC http://
        """
        if self.thread is None:
            self.quit = False
            self.reader_at_end = reader_at_end
            self.thread = Thread(target=self.run, name='Slave Server')
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

    def get_percent(self):
        """
        Return the percentage the slave server has read through the buffer.
        """
        rb_len = len(self.buffer)
        pos = self.reader.available_backward()
        return int(math.ceil(float(pos) / float(rb_len) * 100.0))


    def run(self):
        """
        Thread method to listen for connection from vlc http:// and serve data from the ring buffer.
        """
        reader = ring_buffer.Reader(self.buffer)
        reader.overtaken = self.overtaken
        self.reader = reader

        if self.reader_at_end:
            reader.pos = self.buffer.end
            reader.seek( - self.end_offset)

        while not self.quit:
            conn, addr = self.socket.accept()
            self.connection = conn

            conn.send('HTTP/1.0 200 OK\n')
            conn.send('Content-type: application/octet-stream\n')
            conn.send('Cache-Control: no-cache\n\n')

            if self.reader_at_end:
                reader.pos = self.buffer.end
                reader.seek( - self.end_offset)
                self.reader_at_end = False

            try:
                last_time = time.time()
                count = 0
                starved_count = 0
                while not self.quit:
                    if count == 0:
                        _debug_('In data loop')
                    data = reader.read(188 * 7)

                    if not data:
                        _debug_('Starved!!! count=%d starved_count=%d' % (count,starved_count))
                        starved_count += 1
                        if starved_count >= 5:
                            self.controller.pause()
                            time.sleep(3.0)
                            self.controller.resume()
                        else:
                            time.sleep(0.25)
                    else:
                        starved_count = 0
                        now = time.time()
                        if last_time - now > 1.0:
                            last_time = now
                            _debug_('Sent %d bytes' %  count)
                        count += len(data)
                        conn.send(data)

            except error:
                pass
            except :
                traceback.print_exc()
            try:
                conn.close()
            except:
                pass
        _debug_('Slave server exited')
        reader.close()
        self.thread = None


    def overtaken(self, reader):
        # Todo: would be nice to warn the user somehow that they've missed some of the program.
        # print 'Reader was overtaken new position = %d' % reader.pos
        rc.post_event(EVENT_READER_OVERTAKEN)


class VlcApp(childapp.ChildApp2):
    def __init__ (self, command, vlc):
        self.vlc = vlc
        self.RE_EXIT              = re.compile("status change: \( quit \)")
        self.RE_PARSE_HEAD_AUDIO  = re.compile("^\+----\[ Audio Track \]")
        self.RE_PARSE_HEAD_SUB    = re.compile("^\+----\[ Subtitles Track \]")
        self.RE_PARSE_HEAD_ACHAN  = re.compile("^\+----\[ Audio Device \]")
        self.RE_PARSE_FOOT        = re.compile("^\+----\[ end of")
        self.RE_PARSE_DATA        = re.compile("^\|")
        self.exit_type = None
        self.audio_tracks = []
        self.sub_tracks   = []
        self.audio_chans  = []
        self.stat= {
            'none'  : '0',
            'audio' : '1',
            'subs'  : '2',
            'achan' : '3',
        }
        self.parsecur     = None
        childapp.ChildApp2.__init__(self, command)



    def stdout_cb(self, line):
        '''Override this method to receive stdout from the child app
           The function receives complete lines
        '''
        if self.RE_EXIT.search(line):
            self.exit_type = 'Quit'

        elif self.RE_PARSE_HEAD_AUDIO.search(line):
            self.parsecur = self.stat['audio']
            self.audio_tracks = []

        elif self.RE_PARSE_HEAD_SUB.search(line):
            self.parsecur = self.stat['subs']
            self.sub_tracks = []

        elif self.RE_PARSE_HEAD_ACHAN.search(line):
            self.parsecur = self.stat['achan']
            self.audio_chans = []

        elif self.RE_PARSE_FOOT.search(line):
            self.parsecur = self.stat['none']

        elif self.RE_PARSE_DATA.search(line):
            if self.parsecur == self.stat['audio']:
                self.audio_tracks.append(  line.split(" ")[1] )
                self.audio_tracks = util.misc.unique( self.audio_tracks )

            elif self.parsecur == self.stat['achan']:
                self.audio_chans.append( line.split(" ")[1])
                self.audio_chans = util.misc.unique( self.audio_chans )

            elif self.parsecur == self.stat['subs']:
                self.sub_tracks.append(line.split(" ")[1])
                self.sub_tracks = util.misc.unique(self.sub_tracks)




    def stop_event(self):
        """
        return the stop event send through the eventhandler
        """
        if self.exit_type == 'Quit':
            return PLAY_END
