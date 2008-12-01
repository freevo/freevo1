# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ring_buffer.py - implementation of a Ring Buffer for PVR
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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

import os
import threading
import rwlock

class RingBuffer(object):
    """
    Ring Buffer backed by a file that can be written to by a single writer but
    read by many readers.
    """
    def __init__(self, path,  size):
        """
        Initialise the ring buffer with size of the buffer and the path to the
        file to use. If path is None then a temporary file will be created.
        """
        self.readers = []
        self.rwlock = rwlock.RWLock()
        self.write_event = threading.Condition()

        self.size = size
        self.path = path
        # Try opening with read + write and then write + read as w+ truncates the file.
        try:
            self.buffer_fd = open(path, 'r+b', 0)
        except:
            self.buffer_fd = open(path, 'w+b', 0)

        # Check to see if we need to increase the size of the file.
        stat = os.fstat(self.buffer_fd.fileno())
        if stat.st_size < size:
            self.buffer_fd.truncate(size)

        self.start = 0
        self.end = 0
        self.full = False

    def close(self):
        """
        Close the ring buffer.
        """
        self.buffer_fd.close()

    def reset(self):
        """
        Reset the ring buffer back to having no contents.
        """
        #self.rwlock.acquire_write()
        self.start = 0
        self.end = 0
        self.full = False
        self.buffer_fd.seek(0)

        for reader in self.readers:
            reader.pos = self.start
            reader.at_end = False
        #self.rwlock.release()


    def add_reader(self, reader):
        """
        Add a reader to this ring buffer.
        """
        self.readers.append(reader)
        reader.pos = self.start
        reader.file = open(self.path, 'rb', 0)
        reader.file.seek(self.start)


    def remove_reader(self, reader):
        """
        Remove a reader from this ring buffer.
        """
        self.readers.remove(reader)


    def write(self, buffer):
        """
        Write the contents of buffer to the ring buffer.
        """
        self.rwlock.acquire_write()

        buf_len = len(buffer)
        pos = self.end

        if (buf_len + pos) < self.size:
            self.buffer_fd.write(buffer)
            self.end += buf_len
        else:
            to_end_len = self.size - pos
            from_start_len = buf_len - to_end_len
            self.buffer_fd.write(buffer[:to_end_len])
            self.buffer_fd.seek(0)
            self.buffer_fd.write(buffer[to_end_len:])
            self.end = from_start_len
            self.full = True

        self.buffer_fd.flush()
        self.buffer_fd.seek(self.end)
        if self.full:
            old_start = self.start
            self.start = self.end

            # Update any readers that we have now passed over
            for reader in self.readers:
                if not reader.at_end:
                    overtaken = False
                    if (old_start < self.start) and (reader.pos >= old_start) and (reader.pos < self.start):
                        overtaken = True
                    elif (old_start > self.start) and (reader.pos >= old_start) and (reader.pos > self.start):
                        overtaken = True

                    if overtaken:
                        reader.file.seek(self.start)
                        reader.pos = self.start
                        if reader.overtaken is not None:
                            reader.overtaken(reader)
                else:
                    # We've added data to the buffer so no reader can now be at
                    # the end of the buffer.
                    reader.at_end = False
        else:
            for reader in self.readers:
                reader.at_end = False

        self.rwlock.release()
        self.__notify_data__()



    def read(self, reader, max_len):
        """
        Read upto max_len bytes from the ring buffer using the specified reader.
        """
        self.rwlock.acquire_read()

        pos = reader.pos
        result = ''

        if not reader.at_end:
            if pos < self.end:
                len_from_pos = self.end - pos
                if len_from_pos >= max_len:
                    result = reader.file.read(max_len)
                else:
                    result = reader.file.read(len_from_pos)
            elif self.full:
                to_end_len = self.size - pos
                if to_end_len >= max_len:
                    result = reader.file.read(max_len)
                else:
                    from_start_len = max_len - to_end_len
                    if from_start_len > self.end:
                        from_start_len = self.end
                    result = reader.file.read(to_end_len)
                    reader.file.seek(0)
                    result += reader.file.read(from_start_len)

        reader.pos += len(result)
        if reader.pos >= self.size:
            reader.pos -= self.size
            reader.file.seek(reader.pos)

        reader.at_end = (reader.pos == self.end)

        self.rwlock.release()
        return result


    def __notify_data__(self):
        """
        Notify waiting readers that there is data available.
        """
        self.write_event.acquire()
        self.write_event.notifyAll()
        self.write_event.release()


    def wait_for_data(self, delay):
        """
        Wait for data to be written to the ring buffer.
        """
        self.write_event.acquire()
        self.write_event.wait(delay)
        self.write_event.release()

    def __len__(self):
        if self.full:
            return self.size
        return self.end

class Reader(object):
    def __init__(self, ringbuffer):
        """
        Create a new reader linked to the specified ring buffer.
        """
        self.ringbuffer = ringbuffer
        self.overtaken = None
        self.at_end = False
        self.file = None
        self.pos = 0
        # Opens the file and sets self.pos
        ringbuffer.add_reader(self)

    def copy(self):
        """
        Return a new instance of reader that is located at the same position as this reader.
        """
        result = Reader(self.ringbuffer)
        result.pos = self.pos
        result.file.seek(self.pos)
        result.at_end = self.at_end
        return result

    def close(self):
        """
        Close this reader and break its connection to the ring buffer.
        """
        self.ringbuffer.remove_reader(self)
        self.file.close()


    def read(self, max_len):
        """
        Read up to max_len bytes from the ring buffer.
        Returns '' if no bytes are available.
        """
        if self.at_end:
            return ''

        return self.ringbuffer.read(self, max_len)


    def available_forward(self):
        """
        Number of bytes available to read forward.
        """
        if self.at_end:
            return 0

        if self.pos < self.ringbuffer.end:
            return self.ringbuffer.end - self.pos

        return (self.ringbuffer.size - self.pos) + self.ringbuffer.end


    def available_backward(self):
        """
        Number of bytes that can be seeked backward.
        """
        if (self.pos == self.ringbuffer.start) and not self.at_end:
            return 0

        if self.pos > self.ringbuffer.start:
            return self.pos - self.ringbuffer.start

        return (self.ringbuffer.size - self.ringbuffer.start) + self.pos

    def seek(self, offset):
        """
        Seek offset bytes backward or forward in the ring buffer.
        """
        avail_forward = self.available_forward()
        if offset > avail_forward:
            offset = avail_forward

        avail_backward = self.available_backward()
        if (offset < 0) and (abs(offset) > avail_backward):
            offset = avail_backward * -1

        pos = self.pos + offset

        if pos > self.ringbuffer.size:
            pos = pos - self.ringbuffer.size

        elif pos < 0:
            pos = self.ringbuffer.size + pos

        self.pos = pos
        self.file.seek(pos)

        if offset >= 0:
            self.at_end = (self.pos == self.ringbuffer.end)
        else:
            self.at_end = False


def test_overtaken(reader):
    print 'Reader was overtaken  new position = %d' % reader.pos

if __name__ == '__main__':
    buffer = RingBuffer('c:\\temp\\ringbuffer', 10)
    test_reader = Reader(buffer)
    test_reader.overtaken = test_overtaken

    for i in range(0, 21):
        buffer.write(str(i%10))
        print 'Ring Buffer Length = %d (Start = %d End = %d Full=%s pos=%d)' % (len(buffer), buffer.start, buffer.end, str(buffer.full), buffer.buffer_fd.tell())

    print 'Sequential read test'
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
    for i in range(0, 10):
        data = test_reader.read(1)
        print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())

    print 'Seek test'
    test_reader = Reader(buffer)
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
    data = test_reader.read(1)
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
    test_reader.seek(-1)
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
    test_reader.seek(5)
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
    test_reader.seek(-10)
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
    test_reader.seek(11)
    print 'Reader pos = %d available_forward = %d available_backward = %d  pos=%d' % (test_reader.pos, test_reader.available_forward(), test_reader.available_backward(),  test_reader.file.tell())
