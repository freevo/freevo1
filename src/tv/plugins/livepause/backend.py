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
import socket
import sys
import threading
import time
import traceback

import kaa
import kaa.rpc
import childapp
import config     # Configuration handler. reads config file.
import util


from tv.channels import FreevoChannels
from event import *

from tv.plugins.livepause.events import *
from tv.plugins.livepause import controllers


__all__ = ['get_backend', 'BACKEND_SERVER_PORT', 'BACKEND_SERVER_SECRET', 'LocalBackend']

MEDIA_SERVER_PORT = 7777
BACKEND_SERVER_PORT = 7776
BACKEND_SERVER_SECRET = 'livepause'

WAIT_FOR_DATA_TIMEOUT = 20 # Seconds

def get_backend():
    if config.LIVE_PAUSE2_BACKEND_SERVER_IP is None:
        return LocalBackend()
    return RemoteBackendClient()

class Backend(object):
    """
    Abstract class used to control tuning and the ringbuffer.
    """

    def get_server_address(self):
        """
        Return the IP address of the media server to connect to.
        """
        pass

    def set_mode(self, mode):
        """
        Set the mode of the media server to either raw or http.
        @param mode: Either 'raw' or 'http'.
        """
        pass

    def get_buffer_info(self):
        """
        Retrieve information on the state of the ring buffer.
        @return: A tuple of percentage full (0.0 - 1.0), time at the start of
        the buffer, time at the end of the buffer, time at the current reader
        position.
        """
        pass

    def set_events_enabled(self, enable):
        """
        Enable the sending of events todo with the ringbuffer.
        @param enable: Whether to enable or disable events.
        """
        pass

    def seekto(self, to_time):
        """
        Seek to the specified time.
        @param to_time: The time to seek to.
        """
        pass

    def seek(self, time_delta, now=False):
        """
        Seek specified number of seconds back or forward in the ring buffer.
        @param time_delta: Number of second to seek back (-ve) or forward (+ve).
        @param now: Whether the seek should be done immediately or on the next connection.
        """
        pass

    def disable_buffering(self):
        """
        Stop buffering the current channel.
        """
        pass

    def change_channel(self, channel):
        """
        Change to the specified channel and start filling the ring buffer.
        @param channel: Channel to change to.
        """
        pass

    def save(self, filename, time_start, time_end):
        """
        Save a portion of the ring buffer to the specified file.
        @param filename: Name of the file to store the ring buffer contents to.
        @param time_start: Time to start saving from.
        @param time_stop: Time to finish saving data to the file.
        """
        pass

class RemoteBackendClient(Backend):
    """
    Stub class used to communicate with a remote backend.
    """

    def __init__(self):
        super(RemoteBackendClient, self).__init__()
        _debug_('RecordClient.__init__()', 2)
        self.socket = (config.LIVE_PAUSE2_BACKEND_SERVER_IP, config.LIVE_PAUSE2_BACKEND_SERVER_PORT)
        self.secret = config.LIVE_PAUSE2_BACKEND_SERVER_SECRET
        self.server = None


    def _rpc(self, cmd, *args, **kwargs):
        """ call the record server command using kaa rpc """
        def closed_handler():
            _debug_('%r has closed' % (self.socket,), DINFO)
            self.server = None

        _debug_('RemoteBackendClient._rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs), 2)
        try:
            if self.server is None:
                try:
                    self.server = kaa.rpc.Client(self.socket, self.secret)
                    self.server.connect(self)
                    self.server.signals['closed'].connect(closed_handler)
                    _debug_('%r is up' % (self.socket,), DINFO)
                except kaa.rpc.ConnectError:
                    _debug_('%r is down' % (self.socket,), DINFO)
                    self.server = None
                    return None
            return self.server.rpc(cmd, *args, **kwargs)
        except kaa.rpc.ConnectError, e:
            _debug_('%r is down' % (self.socket,), DINFO)
            self.server = None
            return None
        except IOError, e:
            _debug_('%r is down' % (self.socket,), DINFO)
            self.server = None
            return None

    @kaa.rpc.expose('send_event')
    def _send_event(self, to_send):
        to_send.post()

    def get_server_address(self):
        return config.LIVE_PAUSE2_BACKEND_SERVER_IP

    def set_mode(self, mode):
        inprogress = self._rpc('set_mode', mode)
        if inprogress is None:
            return False
        inprogress.wait()

    def get_buffer_info(self):
        inprogress = self._rpc('get_buffer_info')
        if inprogress is None:
            return False
        return inprogress.wait()

    def set_events_enabled(self, enable):
        inprogress = self._rpc('set_events_enabled', enable)
        if inprogress is None:
            return False
        inprogress.wait()

    def seekto(self, to_time):
        inprogress = self._rpc('seekto', to_time)
        if inprogress is None:
            return False
        inprogress.wait()

    def seek(self, time_delta, now=False):
        inprogress = self._rpc('seek', time_delta, now)
        if inprogress is None:
            return False
        inprogress.wait()

    def disable_buffering(self):
        inprogress = self._rpc('disable_buffering')
        if inprogress is None:
            return False
        inprogress.wait()

    def change_channel(self, channel):
        inprogress = self._rpc('change_channel', channel)
        if inprogress is None:
            return False
        inprogress.wait()

    def save(self, filename, time_start, time_end):
        inprogress = self._rpc('save', filename, time_start, time_end)
        if inprogress is None:
            return False
        inprogress.wait()

    def cancelsave(self):
        inprogress = self._rpc('cancelsave')
        if inprogress is None:
            return False
        inprogress.wait()


class LocalBackend(Backend):
    """
    Class used to control tuning and the ringbuffer locally.
    """
    def __init__(self):
        super(LocalBackend, self).__init__()
        self.fc = FreevoChannels()

        self.livepause_app = None

        self.controller = None
        self.device_in_use = None
        self.last_channel = None

        self.mode = 'raw'
        self.events_enabled = False

    def get_server_address(self):
        return 'localhost'

    def set_mode(self, mode):
        if self.livepause_app:
            self.livepause_app.set_mode(mode)
        self.mode = mode

    def get_buffer_info(self):
        if self.livepause_app:
            return self.livepause_app.info()
        return (0.0,0,0,0)

    def set_events_enabled(self, enable):
        if self.livepause_app:
            self.livepause_app.events_enabled = enable
        self.events_enabled = enable

    def seekto(self, to_time):
        if self.livepause_app:
            self.livepause_app.seekto(to_time)

    def seek(self, time_delta, now=False):
        if self.livepause_app:
            self.livepause_app.seek(time_delta, now)

    def disable_buffering(self):
        if self.device_in_use:
            self.last_channel = None
            self.controller.stop_filling()
            self.controller = None
            self.device_in_use = None
            self.livepause_app.quit()
            self.livepause_app = None
            _debug_('Buffering disabled.')


    def change_channel(self, channel):
        if self.last_channel == channel:
            # Already tune to this channel so nothing to do!
            return

        if self.device_in_use:
            self.controller.stop_filling()
            self.controller = None
            self.device_in_use = None

        if self.livepause_app is None:
            self.livepause_app = LivePauseApp(config.CONF.livepause,
                                              config.LIVE_PAUSE2_BUFFER_PATH,
                                              config.LIVE_PAUSE2_BUFFER_SIZE,
                                              config.LIVE_PAUSE2_PORT,
                                              self.send_event)
            self.livepause_app.set_mode(self.mode)
            self.livepause_app.events_enabled = self.events_enabled

        # Find the controller for this VideoGroup type
        vg = self.fc.getVideoGroup(channel, True)
        self.controller = controllers.get_controller(vg.group_type)
        if not self.controller:
            _debug_('Failed to find controller for device')
            return

        self.fc.chanSet(channel, True)

        self.livepause_app.reset()
        self.livepause_app.events_enabled = True
        self.controller.start_filling(self.livepause_app, vg, channel, WAIT_FOR_DATA_TIMEOUT)
        self.device_in_use = vg
        self.last_channel = channel

    def save(self, filename, time_start, time_end):
        if self.livepause_app:
            self.livepause_app.save(filename, time_start, time_end)

    def cancelsave(self):
        if self.livepause_app:
            self.livepause_app.cancel_save()

    def send_event(self, to_send):
        to_send.post()


###############################################################################
# Live Pause App Class
###############################################################################
class LivePauseApp(childapp.ChildApp):
    """
    Class used to control and process output from the livepause app.
    """

    def __init__ (self, command, buffer_file, size, port, send_event):
        """
        Start a new livepause server using the specified buffer file and TCP port.
        @param command: Name of the livepause executable.
        @param buffer_file: Name of the file to use as the ring buffer.
        @param size: Size in Megabytes of the ring buffer.
        @param port: TCP port to serve the data from.
        @param send_event: Callback function used to forward events to the frontend.
        """
        self.exit_type = None
        self.output_event = threading.Event()
        self.lines = ''
        self.code = 0
        self.message = ''
        self.events_enabled = True
        self.overtaken_last_sent = 0
        self.send_event = send_event
        childapp.ChildApp.__init__(self, [command, '-f', buffer_file, '-s', str(size)], callback_use_rc=False)


    def fill(self, filler, arg):
        """
        Start filling the ring buffer, using the specified filler.
        @param filler: The method to use to fill the ring buffer.
        @param arg: Parameter to pass to the filler.
        """
        self.send_command_wait_for_output('fill %s %s' % (filler, arg))

    def reset(self):
        """
        Stop filling the ring buffer.
        """
        self.send_command_wait_for_output('stop')

    def info(self):
        """
        Retrieve information on the state of the ring buffer.
        @return: A tuple of percentage full (0.0 - 1.0), time at the start of
        the buffer, time at the end of the buffer, time at the current reader
        position.
        """
        results = self.send_command_wait_for_output('info')
        if results[1] == 0:
            data = results[0].strip().split()
            if data >= 4:
                percent = float(data[0])
                buffer_start = int(data[1])
                buffer_end = int(data[2])
                reader_pos = int(data[3])
                return (percent, buffer_start, buffer_end, reader_pos)
        return None

    def set_mode(self, mode):
        """
        Set the mode of the media server.
        @param mode: Either http to enabled HTTP mode or raw for raw data.
        """
        self.send_command_wait_for_output('mode ' + mode)

    def seekto(self, time_pos):
        """
        Seek the read position to an absolute time or as close as possible.
        @param time_pos: Time to seek to.
        """
        self.send_command_wait_for_output('seektoonc %d' % time_pos )

    def seek(self, time_delta, now=False):
        """
        Seek relative to the current read position.
        @param time_delta: Number of seconds to seek, backwards or forwards.
        @param now: Whether the seek should be done immediately or on the next connection.
        """
        if now:
            cmd = 'seek %d' % time_delta
        else:
            cmd = 'seekonc %d' % time_delta
        self.send_command_wait_for_output(cmd)

    def save(self, filename, time_start, time_end):
        """
        Save a portion of the ring buffer to the specified file.
        @param filename: Name of the file to store the ring buffer contents to.
        @param time_start: Time to start saving from.
        @param time_stop: Time to finish saving data to the file.
        """
        self.send_command_wait_for_output('save "%s" %d %d' % (filename, time_start, time_end))

    def cancel_save(self):
        """
        Cancel any current save operation.
        """
        self.send_command_wait_for_output('cancelsave')


    def quit(self):
        """
        Request that livepause exits.
        """
        self.send_command_wait_for_output('quit')

    def send_command_wait_for_output(self, cmd):
        """
        Send a command to livepause and then wait until output has been received.
        @param cmd: The command to send to livepause
        @return: Tuple of 3 items, lines received, error code and message.
        """
        self.lines = ''
        self.code = 0
        self.message = ''

        self.output_event.clear()
        self.write('%s\n' % cmd)
        self.output_event.wait(0.5)
        if not self.output_event.isSet():
            if self.isAlive():
                self.output_event.wait()
            else:
                raise Exception('Livepause died!')


        return (self.lines, self.code, self.message)

    def stdout_cb(self, line):
        """
        Process output from livepause sent to stdout.
        """
        if line.startswith('!!'):
            unused, code, self.message = line.split(' ', 2)
            self.code = int(code)
            self.output_event.set()
        else:
            self.lines += line

    def stderr_cb(self, line):
        if not self.events_enabled:
            return
        to_send = None
        line = line.strip()
        if line == '!Data Started':
            to_send = DATA_STARTED

        elif line == '!Data Acquired':
            to_send = DATA_ACQUIRED

        elif line == '!Overtaken':
            now = time.time()
            # To prevent swamping the event queue with overflow messages
            # only send an event if we haven't sent one for at least 1.0 second.
            if now - self.overtaken_last_sent >= 1.0:
                to_send = READER_OVERTAKEN
                self.overtaken_last_sent = now

        elif line == '!Starved':
            to_send = READER_STARVED

        elif line == '!Save Finished':
            to_send = SAVE_FINISHED

        elif line == '!Save Failed':
            to_send = SAVE_FAILED

        elif line == '!Save Started':
            to_send = SAVE_STARTED

        elif line[0] == '!':
            if line.endswith('seconds left'):
                to_send = Event('SECONDS_LEFT', int(line[1]))


        if to_send and self.send_event:
            self.send_event(to_send)
