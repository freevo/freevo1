import threading
import time
import ring_buffer
import struct

# Ringbuffer chunk size is based on the maximum amount of data that
# can be placed in a UDP packet sent over ethernet (1500 - 20 (IP) - 8 (UDP) = 1472)
# An 6 byte header of data length, number of chunks since last second and seconds
RB_CHUNK_HEADER_SIZE   =    8
RB_CHUNK_DATA_SIZE     = 1472
RB_CHUNK_SIZE          = RB_CHUNK_HEADER_SIZE + RB_CHUNK_DATA_SIZE
class ChunkBufferWriter:
    def __init__(self, buffer):
        self.buffer = buffer
        self.reset()

    def reset(self):
        self.last_time = 0
        self.since_last_second_chunk = 0

    def write(self, data):
        pos = 0
        while len(data) > RB_CHUNK_DATA_SIZE:
            to_write = data[pos:pos + RB_CHUNK_DATA_SIZE]
            self.__write(to_write)

        if pos < len(data):
            self.__write(data[pos:])


    def __write(self, data):
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

class ChunkBufferReader:
    def __init__(self, reader):
        self.reader = reader
        self.current_chunk = None

        self.current_chunk_pos = 0
        self.current_chunk_len = 0
        self.current_chunk_slsc = 0
        self.current_chunk_secs = 0

        self.__lock = threading.Lock()

    def close(self):
        self.reader.close()

    def lock(self):
        self.__lock.acquire()

    def unlock(self):
        self.__lock.release()

    def seek(self, chunks):
        print 'Seeking %d chunks pos %d start %d end %d at_end %r' % (chunks, self.reader.pos, self.reader.ringbuffer.start, self.reader.ringbuffer.end, self.reader.at_end)
        self.current_chunk = None
        self.reader.seek(chunks * RB_CHUNK_SIZE)
        print 'After seeking pos %d start %d end %d at_end %r' % (self.reader.pos, self.reader.ringbuffer.start, self.reader.ringbuffer.end, self.reader.at_end)

    def seek_seconds(self, seconds):
        self.lock()
        print 'Seeking %d seconds' % seconds
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
                    print 'Since last second = %d seconds = %d' % (self.current_chunk_slsc, seconds)
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
                chunk_time = start_seconds
                while self.current_chunk_secs < seconds + start_seconds :
                    self.__read_chunk()
                    if not self.current_chunk:
                        break
        print 'Finished seeking seconds'
        self.unlock()

    def read(self, max):
        self.lock()
        result = ''
        #print 'Reading upto %d bytes' % max
        to_read = max
        while len(result) < max:

            if self.current_chunk:
                chunk_len = self.current_chunk_len + RB_CHUNK_HEADER_SIZE
                #print 'len(result) = %d to_read = %d chunk len = %d pos = %d' % (len(result), to_read, chunk_len, self.current_chunk_pos)
                if to_read > (chunk_len - self.current_chunk_pos):
                    result += self.current_chunk[self.current_chunk_pos:chunk_len]
                    self.current_chunk = None
                else:
                    result += self.current_chunk[self.current_chunk_pos:self.current_chunk_pos+to_read]
                    self.current_chunk_pos += to_read
                to_read = max - len(result)
            else:
                self.__read_chunk()
                if not self.current_chunk:
                    break

        self.unlock()
        #print 'returning : len(result) = %d' % len(result)
        return result

    def __read_chunk(self):
        self.current_chunk = self.reader.read(RB_CHUNK_SIZE)
        if self.current_chunk:
            print 'Reading chunk'
            self.current_chunk_pos = RB_CHUNK_HEADER_SIZE
            header = struct.unpack('=HHL', self.current_chunk[:RB_CHUNK_HEADER_SIZE])
            self.current_chunk_len = header[0]
            self.current_chunk_slsc = header[1]
            self.current_chunk_secs = header[2]

    def available_forward(self):
        return self.reader.available_forward() / RB_CHUNK_SIZE

    def available_backward(self):
        return self.reader.available_backward() / RB_CHUNK_SIZE

def fill_buffer():
    global buffer_writer, buffer
    count = 0
    while True:
        packet = '%d %s' % (count + 1,time.ctime())
        packet += ' ' * (187 - len(packet))
        packet += '\n'
        buffer_writer.write(packet)
        count += 1
        time.sleep(0.2)
        if (count % 10 == 0):
            print 'Written %d packets (len buffer %d) start %d end %d' % (count, len(buffer), buffer.start, buffer.end)

def empty_buffer():
    global buffer_reader, buffer
    count = 0
    done = False
    while True:
        packets = buffer_reader.read(188*10)
        print packets[:-1]
        if packets:
            count += 1
            print 'Read %d packets (len packets %d buffer %d) chunks f %d b %d bytes f %d b %d' % (count, len(packets), len(buffer),
                                                                  buffer_reader.available_forward(),
                                                                  buffer_reader.available_backward(),
                                                                  buffer_reader.reader.available_forward(),
                                                                  buffer_reader.reader.available_backward())
        else:
            print 'No data sleeping (len buffer %d) chunks f %d b %d bytes f %d b %d' % (len(buffer),
                                                              buffer_reader.available_forward(),
                                                              buffer_reader.available_backward(),
                                                              buffer_reader.reader.available_forward(),
                                                              buffer_reader.reader.available_backward())
            time.sleep(0.2)
        if count == 100:
            buffer_reader.seek(-2)
        if not done and count == 102:
            buffer_reader.seek(2)
            done = True

        if count == 104:
            buffer_reader.seek_seconds(-1)


buffer = ring_buffer.RingBuffer('testbuffer', (100*RB_CHUNK_SIZE))
buffer_reader = ChunkBufferReader(ring_buffer.Reader(buffer))
buffer_writer = ChunkBufferWriter(buffer)

filler_thread = threading.Thread(target=fill_buffer)
filler_thread.setDaemon(True)
filler_thread.start()

empty_buffer()