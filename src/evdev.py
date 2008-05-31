# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Linux /dev/input/event interface library
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

"""
Linux /dev/input/event interface library
"""

import sys
import os
import re
from fcntl import ioctl
import struct

_types = {}
_events = {}

_ids = {}
_buses = {}

# Copied from asm-generic/ioctl.h

_IOC_NRBITS     = 8
_IOC_TYPEBITS   = 8
_IOC_SIZEBITS   = 14
_IOC_DIRBITS    = 2

_IOC_NRMASK     = ((1 << _IOC_NRBITS)-1)
_IOC_TYPEMASK   = ((1 << _IOC_TYPEBITS)-1)
_IOC_SIZEMASK   = ((1 << _IOC_SIZEBITS)-1)
_IOC_DIRMASK    = ((1 << _IOC_DIRBITS)-1)

_IOC_NRSHIFT    = 0
_IOC_TYPESHIFT  = (_IOC_NRSHIFT+_IOC_NRBITS)
_IOC_SIZESHIFT  = (_IOC_TYPESHIFT+_IOC_TYPEBITS)
_IOC_DIRSHIFT   = (_IOC_SIZESHIFT+_IOC_SIZEBITS)

_IOC_NONE       = 0
_IOC_WRITE      = 1
_IOC_READ       = 2

def _IOC(dir,type,nr,size):
    ioc = (((dir)  << _IOC_DIRSHIFT) | \
        (ord(type) << _IOC_TYPESHIFT) | \
        ((nr)   << _IOC_NRSHIFT) | \
        ((size) << _IOC_SIZESHIFT))
    if ioc >= 2**31:
        ioc = int(ioc - 2**32)
    return ioc

def _IO(type,nr):
    return _IOC(_IOC_NONE,(type),(nr),0)

def _IOR(type,nr,size):
    return _IOC(_IOC_READ,(type),(nr),(size))

def _IOW(type,nr,size):
    return _IOC(_IOC_WRITE,(type),(nr),(size))

def _IOWR(type,nr,size):
    return _IOC(_IOC_READ|_IOC_WRITE,(type),(nr),(size))


EVIOCGVERSION              = _IOR('E', 0x01, 4) # get driver version
EVIOCGID                   = _IOR('E', 0x02, 8) # get device ID

def EVIOCGNAME(len):
    return _IOR('E', 0x06, len) # get device name
def EVIOCGPHYS(len):
    return _IOR('E', 0x07, len) # get physical location
def EVIOCGUNIQ(len):
    return _IOR('E', 0x08, len) # get unique identifier

def EVIOCGBIT(ev,len):
    return _IOR('E', 0x20 + ev, len) # get event bits
def EVIOCGABS(abs):
    return _IOR('E', 0x40 + abs, 20) # get abs value/limits
def EVIOCSABS(abs):
    return _IOW('E', 0xc0 + abs, 20) # set abs value/limits

class evdev:
    """
    Interface to the Linux event device
    @ivar _fd: file descriptor of the event device
    @type _fd: open file descriptor
    """
    def __init__(self, dev, blocking=False):
        """
        Initialize an instance of evdev.
        """
        #print 'evdev.__init__(dev, blocking=False)'
        self._fd = None
        if blocking:
            self._fd = os.open(dev, os.O_RDONLY)
        else:
            self._fd = os.open(dev, os.O_RDONLY | os.O_NDELAY)
        self.get_events()


    def __del__(self):
        """
        Delete an instance of evdev.
        """
        #print '__del__(self=%r)' % (self.__dict__)
        try:
            self.close()
        except Exception, why:
            pass


    def close(self):
        """
        Close the open resouces of an instance of evdev.
        """
        #print 'close(self=%r)' % (self,)
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None


    def print_info(self):
        """
        Print the information about an event device
        """
        #print 'print_info()'
        print 'Input driver version %d.%d.%d' % self.get_version()

        devid = self.get_id()
        print 'Device ID: bus %(bus)s vendor 0x%(vendor)04x product 0x%(product)04x version 0x%(version)04x' % devid
        print 'Device name: "' + self.get_name() + '"'
        print 'Device location: "' + self.get_location() + '"'


    def print_events(self):
        """
        """
        #print 'print_events()'
        print 'Supported events:'

        keys = self._events.keys()
        keys.sort()
        for key in keys:
            print '    Event type %s (%d):' % (_types[key], key)

            self._events[key].sort()
            for event in self._events[key]:
                try:
                    print '        Event %s (%d)' % (_events[key][event], event)
                except KeyError:
                    print '        Event ??? (%d)' % event


    def get_version(self):
        """
        """
        #print 'get_version()'
        buf = ioctl(self._fd, EVIOCGVERSION, '    ')
        l, =  struct.unpack('I', buf)
        return (l >> 16, (l >> 8) & 0xff, l & 0xff)


    def get_id(self):
        """
        """
        #print 'get_id()'
        buf = ioctl(self._fd, EVIOCGID, ' ' * 8)
        bus, vendor, product, version = struct.unpack('HHHH', buf)
        return { 'bus':_buses[bus], 'vendor':vendor, 'product':product, 'version':version }


    def get_name(self):
        """
        """
        #print 'get_name()'
        buf = ioctl(self._fd, EVIOCGNAME(1024), ' ' * 1024)
        null = buf.find('\0')
        return buf[:null]


    def get_location(self):
        """
        """
        #print 'get_location()'
        buf = ioctl(self._fd, EVIOCGPHYS(1024), ' ' * 1024)
        null = buf.find('\0')
        return buf[:null]


    def get_events(self):
        """
        """
        #print 'get_events()'
        keys = _types.keys()
        keys.sort()

        # We need one bit per type, rounded up to even 4 bytes
        l = ((keys[-1] + 7) / 8 + 3) & ~0x3

        buf = ioctl(self._fd, EVIOCGBIT(0, l), ' ' * l)
        array = struct.unpack('I' * (l/4), buf)

        self._events = {}

        for i in xrange(l * 8):
            if not array[i / 32] & (1 << i % 32):
                continue

            self._events[i] = []

            subkeys = _events[i].keys()
            subkeys.sort()

            # We need one bit per type, rounded up to even 4 bytes
            sl = ((subkeys[-1] + 7) / 8 + 3) & ~0x3

            try:
                buf = ioctl(self._fd, EVIOCGBIT(i, sl), ' ' * sl)
            except IOError:
                # No events for a type results in Errno 22 (EINVAL)
                break
            subarray = struct.unpack('I' * (sl/4), buf)

            for j in xrange(sl * 8):
                if not subarray[j / 32] & (1 << j % 32):
                    continue

                self._events[i].append(j)


    def has_event(self, test_event):
        """
        """
        #print 'has_event(test_event)'
        for type in self._events.keys():
            for event in self._events[type]:
                if _events[type][event] == test_event:
                    return True
        return False


    def read(self):
        """
        """
        #print 'read()'
        try:
            buf = os.read(self._fd, struct.calcsize('LLHHi'))
        except OSError, (errno, str):
            if errno == 11:
                return None
            raise

        sec, usec, type, code, value = struct.unpack('LLHHi', buf)

        return (float(sec) + float(usec)/1000000.0, _types[type], _events[type][code], value)



if __name__ == '__main__':

    def _convert_value(s):
        #print '_convert_value(s)'
        if s.startswith('0x'):
            return int(s, 16)
        return int(s, 10)


    def parse_input_h(path):
        #print 'parse_input_h(path)'
        global _types, _events, _ids, _buses

        f = file(path)

        types = {}
        events = {}

        ids = {}
        buses = {}

        for line in f.readlines():
            m = re.search('#define (?P<name>EV_[A-Za-z0-9_]+)\s+(?P<value>(0x)?[0-9A-Fa-f]+)', line)
            if m:
                if m.group('name') != 'EV_VERSION':
                    types[_convert_value(m.group('value'))] = m.group('name')
                continue

            m = re.search('#define (?P<name>ID_[A-Za-z0-9_]+)\s+(?P<value>(0x)?[0-9A-Fa-f]+)', line)
            if m:
                ids[_convert_value(m.group('value'))] = m.group('name')
                continue

            m = re.search('#define (?P<name>BUS_[A-Za-z0-9_]+)\s+(?P<value>(0x)?[0-9A-Fa-f]+)', line)
            if m:
                buses[_convert_value(m.group('value'))] = m.group('name')
                continue

            m = re.search('#define (?P<name>(?P<type>[A-Za-z0-9]+)_[A-Za-z0-9_]+)\s+(?P<value>(0x)?[0-9A-Fa-f]+)', line)
            if m:
                t = m.group('type')

                # The naming is a bit off in input.h
                if t == 'BTN':
                    t = 'KEY'

                for k in types.keys():
                    if types[k] == 'EV_' + t:
                        break
                else:
                    raise Exception('Invalid type: %s' % m.group('type'))

                if not events.has_key(k):
                    events[k] = {}

                events[k][_convert_value(m.group('value'))] = m.group('name')

        _types = types
        _events = events

        _ids = ids
        _buses = buses


    def _print_tables():
        #print '_print_tables()'
        print '_types = {'

        keys = _types.keys()
        keys.sort()
        for key in keys:
            print '    %2d:%s,' % (key, repr(_types[key]))

        print '    }'

        print ''

        print '_events = {'

        keys = _events.keys()
        keys.sort()
        for key in keys:
            print '    %2d:{ # %s' % (key, _types[key])

            subkeys = _events[key].keys()
            for subkey in subkeys:
                print '        %3d:%s,' % (subkey, repr(_events[key][subkey]))

            print '        },'

        print '    }'

        print ''

        print '_ids = {'

        keys = _ids.keys()
        keys.sort()
        for key in keys:
            print '    %2d:%s,' % (key, repr(_ids[key]))

        print '    }'

        print ''

        print '_buses = {'

        keys = _buses.keys()
        keys.sort()
        for key in keys:
            print '    %2d:%s,' % (key, repr(_buses[key]))

        print '    }'

    # Main starts here
    e = evdev(sys.argv[1], True)
    e.print_info()
    e.print_events()

    try:
        while True:
            print e.read()
    except KeyboardInterrupt:
        pass

try:
    from linuxevent import _types, _events, _ids, _buses
except ImportError:
    from evfallback import _types, _events, _ids, _buses
except StandardError, e:
    print 'evfallback:', e
