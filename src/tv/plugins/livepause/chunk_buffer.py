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
"""
This module adds a layer on top of the standard ring buffer to add time data
and time based seeking.
"""

import struct
import time
import threading

from tv.plugins.livepause.ring_buffer import RingBuffer, Reader

__all__ = ['ChunkBuffer']

# Ringbuffer chunk size is based on the maximum amount of data that
# can be placed in a UDP packet sent over ethernet (1500 - 20 (IP) - 8 (UDP) = 1472)
# An 8 byte header of data length, number of chunks since last second and seconds
RB_CHUNK_HEADER_SIZE   =    8
RB_CHUNK_DATA_SIZE     = 1472
RB_CHUNK_SIZE          = RB_CHUNK_HEADER_SIZE + RB_CHUNK_DATA_SIZE

class ChunkBuffer(object):
    """
    Class to add time information inline into the ring buffer to allow for time based seeking.
    """

    def __init__(self, path, size):
        """
        @param path: Location to create the ring buffer file.
        @param size: Size of the ring buffer.
        """
        self.buffer = RingBuffer(path, (size / RB_CHUNK_SIZE) * RB_CHUNK_SIZE)
        self.last_time = 0
        self.since_last_second_chunk = 0


    def get_reader(self):
        """
        Retrieve a chunk reader for this buffer.
        @returns: A ChunkBufferReader instance.
        """
        return ChunkBufferReader(Reader(self.buffer))


    def reset(self):
        """
        Reset the ring buffer to be empty.
        """
        self.buffer.reset()
        self.last_time = 0
        self.since_last_second_chunk = 0


    def write(self, data):
        """
        Write data to the ringbuffer adding inline time information.
        @param data: String to write to the ring buffer.
        """
        pos = 0
        while len(data) > RB_CHUNK_DATA_SIZE:
            to_write = data[pos:pos + RB_CHUNK_DATA_SIZE]
            self.__write(to_write)

        if pos < len(data):
            self.__write(data[pos:])


    def __write(self, data):
        """
        Internal function to write a single chunk.
        @param data: String to write to the ring buffer.
        """
        now = time.time()
        header = struct.pack('=HHL', len(data), self.since_last_second_chunk, long(now))
        if now - self.last_time > 1.0:
            self.since_last_second_chunk = 0
            self.last_time = now
        else:
            self.since_last_second_chunk += 1

        chunk = header + data
        if len(chunk) < RB_CHUNK_SIZE:
            chunk += '\0' * (RB_CHUNK_SIZE - len(chunk))
        self.buffer.write(chunk)


class ChunkBufferReader(object):
    """
    Class to read data and time information from a ChunkBuffer.
    """

    def __init__(self, reader):
        """
        @param reader: RingBuffer.Reader() instance to use to read the ring buffer.
        """
        self.reader = reader
        self.current_chunk = None

        self.current_chunk_pos = 0
        self.current_chunk_len = 0
        self.current_chunk_slsc = 0
        self.current_chunk_secs = 0

        self.__lock = threading.Lock()


    def copy(self):
        """
        Create a copy of this reader.
        @return: A new ChunkBufferReader instance located at the same position in the ring buffer.
        """
        reader = self.reader.copy()
        return ChunkBufferReader(reader)


    def close(self):
        """
        Close the readers connection to the ring buffer.
        """
        self.reader.close()


    def lock(self):
        """
        Lock access to the reader.
        """
        self.__lock.acquire()


    def unlock(self):
        """
        Unlock access to the reader.
        """
        self.__lock.release()


    def seek(self, chunks):
        """
        Seek a number of chunks in the buffer.
        @param chunks: Number of chunks to seek.
        """
        self.current_chunk = None
        self.reader.seek(chunks * RB_CHUNK_SIZE)


    def seek_seconds(self, seconds):
        """
        Seek backward or forward seconds in the buffer.
        @param seconds: Number of seconds from the current chunk to seek.
        """
        self.lock()
        if not self.current_chunk:
            self.__read_chunk()
            if not self.current_chunk:
                if self.reader.at_end:
                    self.seek( - 1)
                else:
                    self.seek(1)
                self.__read_chunk()

        if self.current_chunk:
            if seconds < 0:
                while seconds < 0:
                    # + 1 For the chunk we have just read
                    # + 1 To move to the start of the top of the second chunk
                    self.seek(- (self.current_chunk_slsc + 2 ))
                    self.__read_chunk()
                    if self.current_chunk:
                        seconds += 1
                    else:
                        break
            else:
                start_seconds = self.current_chunk_secs
                while self.current_chunk_secs < seconds + start_seconds :
                    self.__read_chunk()
                    if not self.current_chunk:
                        break
        self.unlock()


    def read(self, length):
        """
        Read length bytes from the buffer or until there is no more data in the buffer.

        @param length: Number of bytes to read.
        @return: A string containing the bytes read.
        """
        self.lock()
        result = ''
        to_read = length
        while len(result) < length:

            if self.current_chunk:
                chunk_len = self.current_chunk_len + RB_CHUNK_HEADER_SIZE
                if to_read > (chunk_len - self.current_chunk_pos):
                    result += self.current_chunk[self.current_chunk_pos:chunk_len]
                    self.current_chunk = None
                else:
                    result += self.current_chunk[self.current_chunk_pos:self.current_chunk_pos+to_read]
                    self.current_chunk_pos += to_read
                to_read = length - len(result)
            else:
                self.__read_chunk()
                if not self.current_chunk:
                    break

        self.unlock()
        return result


    def __read_chunk(self):
        """
        Internal function to load the current chunk.
        """
        self.current_chunk = self.reader.read(RB_CHUNK_SIZE)
        if self.current_chunk:
            self.current_chunk_pos = RB_CHUNK_HEADER_SIZE
            header = struct.unpack('=HHL', self.current_chunk[:RB_CHUNK_HEADER_SIZE])
            self.current_chunk_len = header[0]
            self.current_chunk_slsc = header[1]
            self.current_chunk_secs = header[2]


    def get_current_chunk_time(self):
        """
        Retrieve the time the current chunk was written to the ring buffer.
        @return: An int describing time in seconds since the epoch.
        """
        if not self.current_chunk:
            self.__read_chunk()
        return self.current_chunk_secs


    def available_forward(self):
        """
        Determine the number of chunks that can be seeked forward.
        @return: Number of chunks.
        """
        return self.reader.available_forward() / RB_CHUNK_SIZE


    def available_backward(self):
        """
        Determine the number of chunks that can be seeked backward.
        @return: Number of chunks.
        """
        return self.reader.available_backward() / RB_CHUNK_SIZE


    def __set_overtaken(self, overtaken):
        """
        Internal property function to set the overtaken callback on the underlying reader object.
        """
        self.reader.overtaken = overtaken

    def __get_overtaken(self):
        """
        Internal property function to get the overtaken callback from the underlying reader object.
        """
        return self.reader.overtaken

    overtaken = property(__get_overtaken, __set_overtaken, None,
                            "Callback to be call when the reader is overtaken by the buffer writer")
