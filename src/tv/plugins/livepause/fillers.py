# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# fillers.py - the Freevo Live Pause module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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
"""
This module contains the classes used to fill the live pause buffer.

UDPTSReceiver - Receives a MPEG-TS transported over UDP.

"""

import socket
import threading
import rc
import struct
import time
import traceback
import subprocess
import os
import select

from tv.plugins.livepause.events import DATA_STARTED, DATA_ACQUIRED, DATA_TIMEDOUT

__all__ = ['UDPTSReceiver']

class UDPTSReceiver:
    """
    Class to receive UDP packets containing MPEG-TS packets sent by DVBStreamer
    and write them into a ring buffer.
    """

    def __init__(self, port, timeout):
        """
        Create a UDP Receiver to write into the ring buffer specified in buffer.
        """
        # Create socket and bind to address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', port))
        self.socket.settimeout(0.2)

        self.quit = False
        self.thread = None
        self.buffer = None
        self.data_timeout_count = timeout * 5
        self.send_events = False


    def start(self, buffer):
        """
        Start a thread to receive UDP packets.
        """
        if self.thread is None:
            _debug_('Starting thread')
            self.quit = False
            self.buffer = buffer

            self.thread = threading.Thread(target=self.run, name='UDP Receiver')
            self.thread.setDaemon(True)
            self.thread.start()
        else:
            _debug_('Thread already running!')


    def stop(self):
        """
        Stop the thread receiving UDP packets.
        """
        if self.thread is not None:
            self.quit = True
            self.thread.join()
        else:
            _debug_('Thread not running!')

    def run(self):
        """
        Thread method to receive UDP packets.
        """
        buffer_size = 188*7
        buffer = self.buffer
        last_time = 0
        timeout_count = 0
        data_received = False
        no_pat_pmt = True
        pat = None
        pmt = None

        _debug_('UDPTSReceiver thread started')
        while not self.quit:
            try:
                data, addr = self.socket.recvfrom(buffer_size)
                if data:
                    timeout_count = 0


                    if not data_received:
                        # We've not had any data yet on the current channel so
                        # clear some state and send an event to say the data
                        # has started.

                        data_received = True
                        last_time = time.time()

                        if self.send_events:
                            _debug_('Sending data started')
                            rc.post_event(DATA_STARTED)

                    # Find the PAT
                    new_pat = find_pat(data)
                    if new_pat:
                        pat = new_pat

                    # Find the PMT
                    if pat:
                        new_pmt = find_pmt(data, pat)
                        if new_pmt:
                            pmt = new_pmt

                    # Make sure the first packets are a PAT and a PMT
                    if no_pat_pmt and pat and pmt:
                        no_pat_pmt = False
                        buffer.write(pat + pmt)

                    # Wait until we have a PAT and a PMT before starting to write to the buffer.
                    if pat and pmt:
                        buffer.write(data)

                        now = time.time()
                        time_diff = now - last_time
                        if time_diff > 1.0:
                            last_time = now
                            if self.send_events:
                                rc.post_event(DATA_ACQUIRED)

                            # For seeking write a new pat+pmt chunk every second.
                            if pat and pmt:
                                buffer.write(pat + pmt)

            except socket.timeout:
                if not self.quit:
                    timeout_count += 1
                    if (timeout_count > self.data_timeout_count) and self.send_events:
                        rc.post_event(DATA_TIMEDOUT)
            except:
                traceback.print_exc()
        _debug_('UDPTSReceiver thread finished')
        self.thread = None

class MPEGProgamStreamReceiver:
    """
    Class to read a MPEG ProgramStream and convert it to a MPEG SPTS for the ring buffer.
    """
    def __init__(self):
        self.path = None
        self.quit = False
        self.thread = None
        self.buffer = None
        self.data_timeout_count = timeout * 5
        self.send_events = False


    def start(self, path, buffer):
        """
        Start a thread to receive TS packets and the mpegpstots program.
        """
        if self.thread is None:
            _debug_('Starting thread')
            self.quit = False
            self.path = path
            self.buffer = buffer

            self.thread = threading.Thread(target=self.run, name='PS to TS Receiver')
            self.thread.setDaemon(True)
            self.thread.start()
        else:
            _debug_('Thread already running!')


    def stop(self):
        """
        Stop the thread receiving TS packets and the mpegpstots program.
        """
        if self.thread is not None:
            self.quit = True
            self.thread.join()
        else:
            _debug_('Thread not running!')

    def run(self):
        """
        Thread method to receive UDP packets.
        """
        buffer_size = 188*7
        buffer = self.buffer
        last_time = 0
        timeout_count = 0
        data_received = False
        no_pat_pmt = True
        pat = None
        pmt = None
        process = subprocess.Popen('mpegpstots %s -' % self.path, shell=True, bufsize=buffer_size, stdout=subprocess.PIPE)
        tsin = process.stdout
        _debug_('MPEGProgamStreamReceiver thread started')
        while not self.quit:
            try:
                fds = select.select([tsin],[],[], 0.2)
                if len(fds[0]) == 0:
                    if not self.quit:
                        timeout_count += 1
                        if (timeout_count > self.data_timeout_count) and self.send_events:
                            rc.post_event(DATA_TIMEDOUT)
                else:
                    data = tsin.read(buffer_size)
                    if data:
                        timeout_count = 0


                        if not data_received:
                            # We've not had any data yet on the current channel so
                            # clear some state and send an event to say the data
                            # has started.

                            data_received = True
                            last_time = time.time()

                            if self.send_events:
                                _debug_('Sending data started')
                                rc.post_event(DATA_STARTED)

                        # Find the PAT
                        new_pat = find_pat(data)
                        if new_pat:
                            pat = new_pat

                        # Find the PMT
                        if pat:
                            new_pmt = find_pmt(data, pat)
                            if new_pmt:
                                pmt = new_pmt

                        # Make sure the first packets are a PAT and a PMT
                        if no_pat_pmt and pat and pmt:
                            no_pat_pmt = False
                            buffer.write(pat + pmt)

                        # Wait until we have a PAT and a PMT before starting to write to the buffer.
                        if pat and pmt:
                            buffer.write(data)

                            now = time.time()
                            time_diff = now - last_time
                            if time_diff > 1.0:
                                last_time = now
                                if self.send_events:
                                    rc.post_event(DATA_ACQUIRED)

                                # For seeking write a new pat+pmt chunk every second.
                                if pat and pmt:
                                    buffer.write(pat + pmt)

            except:
                traceback.print_exc()

        os.kill(process.pid, 15)
        process.wait()
        _debug_('MPEGProgamStreamReceiver thread finished')
        self.thread = None

def find_pat(data):
    """
    Attempt to find the PAT in the supplied buffer.
    Returns the PAT packet or None if not found.
    """
    offset = 0
    pat = None
    while offset < len(data):
        ts_header = data[offset:offset + 4]
        pid,  = struct.unpack('>xHx', ts_header)
        pid = pid & 0x1fff
        if pid == 0:
            pat = data[offset:offset + 188]
            break
        offset += 188
    return pat

def find_pmt(data, pat):
    """
    Based on the PAT passed in attempt to find the PMT in the supplied buffer.
    Returns the PMT packet or None if not found.
    """
    pmt_pid = get_pmt_pid(pat)
    offset = 0
    pmt = None
    while offset < len(data):
        ts_header = data[offset:offset + 4]
        pid,  = struct.unpack('>xHx', ts_header)
        pid = pid & 0x1fff
        if pmt_pid == pid:
            # Only add the pmt to the start of the file if the first packet isn't the pmt.
            if offset > 0:
                pmt = data[offset:offset + 188]
            break
        offset += 188
    return pmt

def get_pmt_pid(pat):
    """
    Extract the PMT PID from the supplied PAT
    """
    programs = pat[4 + 1 + 8:]
    program, pmt_pid = struct.unpack('>HH', programs[:4])
    pmt_pid = pmt_pid & 0x1fff
    return pmt_pid
