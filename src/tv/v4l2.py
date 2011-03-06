# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# V4L2 python interface.
# -----------------------------------------------------------------------
# $Id$
#
# Notes: http://bytesex.org/v4l/spec/
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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


import string
import os
import struct
import array
import fcntl
import sys

import config
import freq


# Different formats depending on word size
bit32 = struct.calcsize('L') == struct.calcsize('I')

def i32(x):
    return (x&0x80000000L and -2*0x40000000 or 0) + int(x&0x7fffffff)

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = ((1 << _IOC_NRBITS)-1)
_IOC_TYPEMASK = ((1 << _IOC_TYPEBITS)-1)
_IOC_SIZEMASK = ((1 << _IOC_SIZEBITS)-1)
_IOC_DIRMASK = ((1 << _IOC_DIRBITS)-1)

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = (_IOC_NRSHIFT+_IOC_NRBITS)
_IOC_SIZESHIFT = (_IOC_TYPESHIFT+_IOC_TYPEBITS)
_IOC_DIRSHIFT = (_IOC_SIZESHIFT+_IOC_SIZEBITS)

# Direction bits.
_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2

def _IOC(dir, type, nr, size):
    return (((dir)  << _IOC_DIRSHIFT) | \
           (ord(type) << _IOC_TYPESHIFT) | \
           ((nr)   << _IOC_NRSHIFT) | \
           ((size) << _IOC_SIZESHIFT))

def _IO(type, nr):
    return _IOC(_IOC_NONE, (type), (nr), 0)

def _IOR(type, nr, size):
    return _IOC(_IOC_READ, (type), (nr), struct.calcsize(size))

def _IOW(type, nr, size):
    return _IOC(_IOC_WRITE, (type), (nr), struct.calcsize(size))

def _IOWR(type, nr, size):
    return _IOC(_IOC_READ|_IOC_WRITE, (type), (nr), struct.calcsize(size))

# used to decode ioctl numbers..
def _IOC_DIR(nr):
    return (((nr) >> _IOC_DIRSHIFT) & _IOC_DIRMASK)
def _IOC_TYPE(nr):
    return (((nr) >> _IOC_TYPESHIFT) & _IOC_TYPEMASK)
def _IOC_NR(nr):
    return (((nr) >> _IOC_NRSHIFT) & _IOC_NRMASK)
def _IOC_SIZE(nr):
    return (((nr) >> _IOC_SIZESHIFT) & _IOC_SIZEMASK)

def _ID2CLASS(id):
    return ((id) & 0x0fff0000)


QUERYCAP_ST      = "<16s32s32sII16x"
QUERYCAP_NO      = _IOR('V', 0, QUERYCAP_ST)

FMT_ST           = bit32 and "<I7I4x168x" or "<Q7I4x168x"
GET_FMT_NO       = _IOWR('V', 4, FMT_ST)
SET_FMT_NO       = _IOWR('V', 5, FMT_ST)

SETFREQ_NO_V4L   = _IOW('v', 15, "L")

STANDARD_ST      = "<Q"
GETSTD_NO        = _IOR('V', 23, STANDARD_ST)
SETSTD_NO        = _IOW('V', 24, STANDARD_ST)

ENUMSTD_ST       = bit32 and "<IQ24s2II16x" or "<QQ24s2II20x"
ENUMSTD_NO       = _IOWR('V', 25, ENUMSTD_ST)

ENUMINPUT_ST     = bit32 and "<I32sIIIQI16x" or "<I32sIIIQI20x"
ENUMINPUT_NO     = _IOWR('V', 26, ENUMINPUT_ST)

CTRL_ST          = "<Ll"
G_CTRL_NO        = _IOWR('V', 27, CTRL_ST)
S_CTRL_NO        = _IOWR('V', 28, CTRL_ST)

TUNER_ST         = "<L32sLLLLLLll16x"
GET_TUNER_NO     = _IOWR('V', 29, TUNER_ST)
SET_TUNER_NO     = _IOW ('V', 30, TUNER_ST)

AUDIO_ST         = "<L32sLL8x"
GET_AUDIO_NO     = _IOWR('V', 33, AUDIO_ST)
SET_AUDIO_NO     = _IOW ('V', 34, AUDIO_ST)

QUERYCTRL_ST     = "<LL32slllll2L"
QUERYCTRL_NO     = _IOWR('V', 36, QUERYCTRL_ST)

QUERYMENU_ST     = "<LL32sL"
QUERYMENU_NO     = _IOWR('V', 37, QUERYMENU_ST)

INPUT_ST         = "<I"
GETINPUT_NO      = _IOR ('V', 38, INPUT_ST)
SETINPUT_NO      = _IOWR('V', 39, INPUT_ST)

FREQUENCY_ST     = "<III32x"
GETFREQ_NO       = _IOWR('V', 56, FREQUENCY_ST)
SETFREQ_NO       = _IOW ('V', 57, FREQUENCY_ST)

LOG_STATUS       = _IO  ('V', 70)

EXT_CTRL_ST      = "=I2Iq"         # (id, res1, res2, s64)
EXT_CTRLS_ST     = "@III2IP"       # (class, count, error_idx, res1, res2, ptr)
G_EXT_CTRLS_NO   = _IOWR('V', 71, EXT_CTRLS_ST)
S_EXT_CTRLS_NO   = _IOWR('V', 72, EXT_CTRLS_ST)
TRY_EXT_CTRLS_NO = _IOWR('V', 73, EXT_CTRLS_ST)

V4L2_CTRL_FLAG_NEXT_CTRL = 0x80000000

V4L2_CTRL_CLASS_USER  = 0x00980000 # Old-style 'user' controls
V4L2_CTRL_CLASS_MPEG  = 0x00990000 # MPEG-compression controls

V4L2_CID_USER_BASE    = (V4L2_CTRL_CLASS_USER | 0x900)
V4L2_CID_USER_CLASS   = (V4L2_CTRL_CLASS_USER | 1)
V4L2_CID_MPEG_BASE    = (V4L2_CTRL_CLASS_MPEG | 0x900)
V4L2_CID_MPEG_CLASS   = (V4L2_CTRL_CLASS_MPEG | 1)
V4L2_CID_PRIVATE_BASE = 0x08000000

V4L2_CID_FIRSTP1      = (V4L2_CID_USER_BASE+0)
V4L2_CID_LASTP1       = (V4L2_CID_USER_BASE+24)

V4L2_TUNER_CAP_NORM   = 0x0002
V4L2_TUNER_CAP_STEREO = 0x0010
V4L2_TUNER_CAP_LANG2  = 0x0020
V4L2_TUNER_CAP_SAP    = 0x0020
V4L2_TUNER_CAP_LANG1  = 0x0040

V4L2_CTRL_TYPE_INTEGER    = 1
V4L2_CTRL_TYPE_BOOLEAN    = 2
V4L2_CTRL_TYPE_MENU       = 3
V4L2_CTRL_TYPE_BUTTON     = 4
V4L2_CTRL_TYPE_INTEGER64  = 5
V4L2_CTRL_TYPE_CTRL_CLASS = 6
V4L2_CTRL_TYPES = {
    0 : 'DISABLED',
    1 : 'INTEGER',
    2 : 'BOOLEAN',
    3 : 'MENU',
    4 : 'BUTTON',
    5 : 'INTEGER64',
    6 : 'CTRL_CLASS',
}

V4L2_CTRL_FLAG_DISABLED   = 0x0001
V4L2_CTRL_FLAG_GRABBED    = 0x0002
V4L2_CTRL_FLAG_READ_ONLY  = 0x0004
V4L2_CTRL_FLAG_UPDATE     = 0x0008
V4L2_CTRL_FLAG_INACTIVE   = 0x0010
V4L2_CTRL_FLAG_SLIDER     = 0x0020
V4L2_CTRL_FLAGS = {
    0x0001 : 'DISABLED',
    0x0002 : 'GRABBED',
    0x0004 : 'READ_ONLY',
    0x0008 : 'UPDATE',
    0x0010 : 'INACTIVE',
    0x0020 : 'SLIDER',
}

NORMS = {
    'PAL_B'       : 0x00000001,
    'PAL_B1'      : 0x00000002,
    'PAL_G'       : 0x00000004,
    'PAL_H'       : 0x00000008,
    'PAL_I'       : 0x00000010,
    'PAL_D'       : 0x00000020,
    'PAL_D1'      : 0x00000040,
    'PAL_K'       : 0x00000080,
    'PAL_M'       : 0x00000100,
    'PAL_N'       : 0x00000200,
    'PAL_Nc'      : 0x00000400,
    'PAL_60'      : 0x00000800,
    'NTSC_M'      : 0x00001000,
    'NTSC_M_JP'   : 0x00002000,
    'NTSC_443'    : 0x00004000,
    'NTSC_M_KR'   : 0x00008000,
    'SECAM_B'     : 0x00010000,
    'SECAM_D'     : 0x00020000,
    'SECAM_G'     : 0x00040000,
    'SECAM_H'     : 0x00080000,
    'SECAM_K'     : 0x00100000,
    'SECAM_K1'    : 0x00200000,
    'SECAM_L'     : 0x00400000,
    'SECAM_LC'    : 0x00800000,
    'ATSC_8_VSB'  : 0x01000000,
    'ATSC_16_VSB' : 0x02000000,

    'PAL_BG'      : 0x00000007,
    'B'           : 0x00010003,
    'GH'          : 0x000C000C,
    'PAL_DK'      : 0x000000E0,
    'PAL'         : 0x000000FF,
    'NTSC'        : 0x0000B000,
    'MN'          : 0x0000B700,
    'SECAM_DK'    : 0x00320000,
    'DK'          : 0x003200E0,
    'SECAM'       : 0x00FF0000,
    '525_60'      : 0x0000F900,
    '625_50'      : 0x00FF06FF,
    'UNKNOWN'     : 0x00000000,
    'ALL'         : 0x00FFFFFF,
}

class Videodev:
    def __init__(self, device):
        _debug_('Videodev.__init__(device=%r)' % (device,), 2)
        self.chanlist = None
        self.device = -1
        try:
            self.device = os.open(device, os.O_TRUNC)
        except OSError, why:
            #self.device = os.open(device, os.O_RDONLY)
            _debug_('Cannot open video device %r: %s' % (device, why), DERROR)
            return

        _debug_('Video opened for %r' % device)
        results           = self.querycap()
        self.driver       = results[0][:results[0].find('\0')]
        self.card         = results[1][:results[1].find('\0')]
        self.bus_info     = results[2][:results[2].find('\0')]
        self.version      = results[3]
        self.capabilities = results[4]
        self.inputs       = self.enuminputs()
        self.standards    = self.enumstds()
        self.controls     = self.enumcontrols()


    def getdriver(self):
        _debug_('getdriver()', 2)
        return self.driver.strip('\0')


    def getversion(self):
        _debug_('getversion()', 2)
        return self.version


    def getdevice(self):
        _debug_('getdevice()', 2)
        return self.device


    def close(self):
        _debug_('close()', 2)
        os.close(self.device)


    def setchanlist(self, chanlist):
        _debug_('setchanlist(chanlist=%r)' % (chanlist,), 2)
        self.chanlist = freq.CHANLIST[chanlist]


    def querycap(self):
        _debug_('querycap()', 2)
        val = struct.pack(QUERYCAP_ST, "", "", "", 0, 0)
        r = fcntl.ioctl(self.device, i32(QUERYCAP_NO), val)
        res = struct.unpack(QUERYCAP_ST, r)
        _debug_('querycap: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res


    def getfreq(self):
        _debug_('getfreq()', 2)
        val = struct.pack(FREQUENCY_ST, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(GETFREQ_NO), val)
        res = struct.unpack(FREQUENCY_ST, r)
        _debug_('getfreq: val=%r, r=%r, res=%r' % (val, r, res), 3)
        (tuner, type, freq, ) = res
        return freq


    def getfreq2(self):
        _debug_('getfreq2()', 2)
        val = struct.pack(FREQUENCY_ST, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(GETFREQ_NO), val)
        res = struct.unpack(FREQUENCY_ST, r)
        _debug_('getfreq2: val=%r, r=%s, res=%r' % (val, r, res), 3)
        return res


    def setchannel(self, channel):
        _debug_('setchannel(channel=%r)' % (channel,), 2)
        freq = config.TV_FREQUENCY_TABLE.get(channel)
        if freq:
            _debug_('Using custom frequency: chan="%s", freq="%s"' % (channel, freq))
        else:
            freq = self.chanlist[str(channel)]
            _debug_('Using standard frequency: chan="%s", freq="%s"' % (channel, freq))

        freq *= 16

        # The folowing check for TUNER_LOW capabilities was not working for
        # me... needs further investigation.
        # if not (self.capabilities & V4L2_TUNER_CAP_LOW):
        #     # Tune in MHz.
        #     freq /= 1000
        freq /= 1000

        try:
            self.setfreq(freq)
        except:
            self.setfreq_old(freq)


    def setfreq_old(self, freq):
        _debug_('setfreq_old(freq=%r)' % (freq,), 2)
        val = struct.pack("L", freq)
        r = fcntl.ioctl(self.device, i32(SETFREQ_NO_V4L), val)
        _debug_('setfreq_old: val=%r, r=%r' % (val, r), 3)


    def setfreq(self, freq):
        _debug_('setfreq(freq=%r)' % (freq,), 2)
        val = struct.pack(FREQUENCY_ST, long(0), long(2), freq)
        r = fcntl.ioctl(self.device, i32(SETFREQ_NO), val)
        _debug_('setfreq: val=%r, r=%r' % (val, r), 3)


    def enuminput(self, num):
        """
        Enumerate a video device input
        @param num: is the input number
        """
        _debug_('enuminput(num=%r)' % (num), 2)
        val = struct.pack(ENUMINPUT_ST, num, "", 0, 0, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(ENUMINPUT_NO), val)
        res = struct.unpack(ENUMINPUT_ST, r)
        _debug_('enuminput: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res

    def enuminputs(self):
        """
        Enumerate all inputs
        @returns: a dict of the inputs index by name
        """
        _debug_('enuminputs()', 2)
        res = {}
        num = 0
        try:
            while 1:
                (index, name, type, audioset, tuner, std, status) = self.enuminput(num)
                name = name.rstrip('\0')
                res[name.lower()] = (index, name, type, audioset, tuner, std, status)
                num += 1
        except IOError, e:
            pass
        return res

    def getinput(self):
        _debug_('getinput()', 2)
        val = struct.pack(INPUT_ST, 0)
        r = fcntl.ioctl(self.device, i32(GETINPUT_NO), val)
        res = struct.unpack(INPUT_ST, r)
        _debug_('getinput: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res[0]


    def setinput(self, value):
        _debug_('setinput(value=%r)' % (value,), 2)
        try:
            r = fcntl.ioctl(self.device, i32(SETINPUT_NO), struct.pack(INPUT_ST, value))
            _debug_('setinput: val=%r, res=%r' % (struct.pack(INPUT_ST, value), r), 3)
        except IOError:
            self.print_settings
            raise


    def getinputbyname(self, name):
        """
        Get the TV input by name, eg: TELEVISION, s-video
        """
        _debug_('getinputbyname(name=%r)' % (name,), 2)
        v_input = name.lower()
        return self.inputs[v_input]


    def setinputbyname(self, name):
        """
        Set the TV input by name, eg: TELEVISION, s-video
        """
        _debug_('setinputbyname(name=%r)' % (name,), 2)
        v_input = name.lower()
        try:
            (index, name, type, audioset, tuner, std, status) = self.inputs[v_input]
            self.setinput(index)
        except KeyError, e:
            _debug_('setinputbyname failed: %s' % (e), DERROR)
            _debug_('possible are: %r' % (self.inputs.keys()), DINFO)
            raise
        _debug_('setinputbyname: %s->%s set' % (name, index))


    def enumstd(self, num):
        _debug_('enumstd(num=%r)' % (num,), 2)
        val = struct.pack(ENUMSTD_ST, num, 0, "", 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(ENUMSTD_NO), val)
        res = struct.unpack(ENUMSTD_ST, r)
        (index, id, name, numerator, denominator, framelines) = res
        _debug_('enumstd: index=%r, id=0x%08x, name=%r, numerator=%r, denominator=%r, framelines=%r' % \
            (index, id, name.strip('\0'), numerator, denominator, framelines), 2)
        _debug_('enumstd: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res


    def enumstds(self):
        """
        Enumerate the TV standards
        @returns: a dict of the standards index by name
        """
        _debug_('enumstds()', 2)
        res = {}
        num = 0
        try:
            while 1:
                (index, id, name, frameperiod, framelines, reserved) = self.enumstd(num)
                name = name.rstrip('\0')
                res[name.upper()] = (index, id, name, frameperiod, framelines)
                num += 1
        except IOError, e:
            pass
        return res


    def getstd(self):
        """
        Get the current TV standard
        """
        _debug_('getstd()', 2)
        val = struct.pack(STANDARD_ST, 0)
        r = fcntl.ioctl(self.device, i32(GETSTD_NO), val)
        res = struct.unpack(STANDARD_ST, r)
        _debug_('getstd: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res[0]


    def setstd(self, value):
        """
        Set the TV standard by number
        """
        _debug_('setstd(value=%r)' % (value,), 2)
        val = struct.pack(STANDARD_ST, value)
        r = fcntl.ioctl(self.device, i32(SETSTD_NO), val)
        _debug_('setstd: val=%r, r=%r' % (val, r), 3)


    def getstdbyname(self, name):
        """
        Get the TV standard by name, eg: PAL-BGH, secam-dk, etc
        """
        _debug_('getstdbyname(name=%r)' % (name,), 2)
        v_norm = name.upper()
        return self.standards[v_norm]


    def setstdbyname(self, name):
        """
        Set the TV standard by name, eg: PAL-BGH, secam-dk, etc
        """
        _debug_('setstdbyname(name=%r)' % (name,), 2)
        v_norm = name.upper()
        tmp = self.getstd()
        try:
            self.setstd(NORMS[v_norm])
            _debug_('setstdbyname: %s (0x%08X) set' % (name, NORMS[v_norm]), 3)
        except KeyError, e:
            _debug_('setstdbyname failed: %s' % (e), DERROR)
            _debug_('possible are: %r' % (NORMS.keys()), DINFO)


    def enuminput(self, num):
        _debug_('enuminput(num=%r)' % (num,), 2)
        val = struct.pack(ENUMINPUT_ST, num, "", 0, 0, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(ENUMINPUT_NO), val)
        res = struct.unpack(ENUMINPUT_ST, r)
        _debug_('enuminput: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res


    def getfmt(self):
        _debug_('getfmt()', 2)
        val = struct.pack(FMT_ST, 1, 0, 0, 0, 0, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(GET_FMT_NO), val)
        res = struct.unpack(FMT_ST, r)
        _debug_('getfmt: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res


    def setfmt(self, width, height):
        _debug_('setfmt(width=%r, height=%r)' % (width, height), 2)
        val = struct.pack(FMT_ST, 1L, width, height, 0L, 4L, 0L, 131072L, 0L)
        r = fcntl.ioctl(self.device, i32(SET_FMT_NO), val)
        _debug_('setfmt: val=%r, r=%r' % (val, r), 3)


    def gettuner(self, num):
        _debug_('gettuner(num=%r)' % (num,), 2)
        val = struct.pack(TUNER_ST, num, "", 0, 0, 0, 0, 0, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(GET_TUNER_NO), val)
        res = struct.unpack(TUNER_ST, r)
        _debug_('gettuner: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res


    def settuner(self, num, audmode):
        _debug_('settuner(num=%r, audmode=%r)' % (num, audmode), 2)
        val = struct.pack(TUNER_ST, num, "", 0, 0, 0, 0, 0, audmode, 0, 0)
        r = fcntl.ioctl(self.device, i32(SET_TUNER_NO), val)
        _debug_('settuner: val=%r, r=%r' % (val, r), 3)


    def getaudio(self, num):
        _debug_('getaudio(num=%r)' % (num,), 2)
        val = struct.pack(AUDIO_ST, num, "", 0, 0)
        r = fcntl.ioctl(self.device, i32(GET_AUDIO_NO), val)
        res = struct.unpack(AUDIO_ST, r)
        _debug_('getaudio: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res


    def setaudio(self, num, mode):
        _debug_('setaudio(num=%r, mode=%r)' % (num, mode), 2)
        val = struct.pack(AUDIO_ST, num, "", mode, 0)
        r = fcntl.ioctl(self.device, i32(SET_AUDIO_NO), val)
        _debug_('setaudio: val=%r, r=%r' % (val, r), 3)


    def getctrl(self, id):
        """
        Get the value of a control
        """
        _debug_('getctrl(id=0x%08x)' % (id,), 2)
        val = struct.pack(CTRL_ST, id, 0)
        r = fcntl.ioctl(self.device, i32(G_CTRL_NO), val)
        res = struct.unpack(CTRL_ST, r)
        _debug_('getctrl: val=%r, %d, res=%r' % (val, len(val), res), 3)
        return res[1]


    def setctrl(self, id, value):
        """
        Set the value of a control
        """
        _debug_('setctrl(id=0x%08x, value=%r)' % (id, value), 2)
        val = struct.pack(CTRL_ST, id, value)
        r = fcntl.ioctl(self.device, i32(S_CTRL_NO), val)
        res = struct.unpack(CTRL_ST, r)
        _debug_('setctrl: val=%r, %d, res=%r' % (val, len(val), res), 3)


    def getextctrl(self, id):
        """
        Get the value of an external control
        EXT_CTRL_type->id, res1, res2, value
        EXT_CTRLS_ST->class, count, error_idx, res1, res2, ptr
        """
        _debug_('getextctrl(id=0x%08x)' % (id,), 2)
        extctrl = array.array('B')
        extctrl.fromstring(struct.pack(EXT_CTRL_ST, id, 0, 0, 0))
        extctrl_p = extctrl.buffer_info()[0]
        val = struct.pack(EXT_CTRLS_ST, _ID2CLASS(id), 1, 0, 0, 0, extctrl_p)
        try:
            r = fcntl.ioctl(self.device, i32(G_EXT_CTRLS_NO), val)
            res = struct.unpack(EXT_CTRLS_ST, r)
            extres = struct.unpack(EXT_CTRL_ST, extctrl.tostring())
            _debug_('getextctrl: val=%r, %d, res=%r' % (val, len(val), res), 3)
            _debug_('getextctrl: extctrl=%r, %d, extres=%s' % (extctrl.tostring(), len(extctrl), extres), 3)
        except IOError, e:
            extres = struct.unpack(EXT_CTRL_ST, extctrl.tostring())
            _debug_('getextctrl(%s)=%s' % (id, e), DWARNING)
        return extres[3]


    def setextctrl(self, id, value):
        """
        Set the value of an external control
        """
        _debug_('setextctrl(id=0x%08x, value=%r)' % (id, value), 2)
        extctrl = array.array('B')
        extctrl.fromstring(struct.pack(EXT_CTRL_ST, id, 0, 0, value))
        extctrl_p = extctrl.buffer_info()[0]
        val = struct.pack(EXT_CTRLS_ST, _ID2CLASS(id), 1, 0, 0, 0, extctrl_p)
        try:
            r = fcntl.ioctl(self.device, i32(S_EXT_CTRLS_NO), val)
            res = struct.unpack(EXT_CTRLS_ST, r)
            extres = struct.unpack(EXT_CTRL_ST, extctrl.tostring())
            _debug_('setextctrl: val=%r, %d, res=%r' % (val, len(val), res), 3)
            _debug_('setextctrl: extctrl=%r, %d, extres=%s' % (extctrl.tostring(), len(extctrl), extres), 3)
        except IOError, e:
            _debug_('setextctrl(%s) %r: %s' % (id, self.findcontrol(id), e), DWARNING)


    def querymenu(self, id, num):
        _debug_('querymenu(id=0x%08x, num=%r)' % (id, num), 2)
        val = struct.pack(QUERYMENU_ST, id, num, "", 0)
        try:
            r = fcntl.ioctl(self.device, i32(QUERYMENU_NO), val)
            res = struct.unpack(QUERYMENU_ST, r)
            _debug_('querymenu: val=%r, %d, res=%r' % (val, len(val), res), 3)
        except IOError, e:
            res = struct.unpack(QUERYMENU_ST, val)
        return res


    def queryctrl(self, id):
        _debug_('queryctrl(id=0x%08x)' % (id,), 2)
        val = struct.pack(QUERYCTRL_ST, id, 0, "", 0, 0, 0, 0, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(QUERYCTRL_NO), val)
        res = struct.unpack(QUERYCTRL_ST, r)
        _debug_('queryctrl: val=%r, %d, res=%r' % (val, len(val), res), 3)
        (id, type, name, min, max, step, default, flags, res1, res2) = res
        name = name.strip('\0')
        if flags & 0x0001:
            return (id, type, name, min, max, step, default, flags, 0)
        if type == V4L2_CTRL_TYPE_CTRL_CLASS:
            return (id, type, name, min, max, step, default, flags, 0)
        if _ID2CLASS(id) != V4L2_CTRL_CLASS_USER and id < V4L2_CID_PRIVATE_BASE:
            value = self.getextctrl(id)
        else:
            value = self.getctrl(id)
        return (id, type, name, min, max, step, default, flags, value)


    def printcontrol(self, res):
        _debug_('printcontrol(res=%r)' % (res,), 2)
        (id, type, name, min, max, step, default, flags, value) = res
        if flags & 0x0001:
            return
        if type == V4L2_CTRL_TYPE_CTRL_CLASS:
            print
            print 'id=%08x, type=%s, name=\"%s\"' % (id, V4L2_CTRL_TYPES[type], name)
            return
        print 'id=%08x, type=%s, name=\"%s\", min=%d, max=%d, step=%d, default=%d, flags=%04x value=%d' % \
            (id, V4L2_CTRL_TYPES[type], name, min, max, step, default, flags, value)
        if type == V4L2_CTRL_TYPE_MENU:
            for i in range(min, max+1):
                (id, index, name, res1) = self.querymenu(id, i)
                print 'index=%d, name=\"%s\"' % (index, name)


    def ctrlname(self, name):
        """
        converts a control to lowercase and replaces spaces with underscore, like v4l2-ctl
        """
        _debug_('ctrlname(name=%r)' % (name,), 2)
        return name.replace(' ', '_').lower()


    def listcontrols(self):
        """
        prints all the controls
        """
        _debug_('listcontrols()', 2)
        id = V4L2_CTRL_FLAG_NEXT_CTRL
        while 1:
            try:
                res = self.queryctrl(id)
                self.printcontrol(res)
                id = res[0] | V4L2_CTRL_FLAG_NEXT_CTRL
            except IOError, e:
                break
        if id != V4L2_CTRL_FLAG_NEXT_CTRL:
            return

        print
        id = V4L2_CID_USER_BASE
        for id in range(V4L2_CID_FIRSTP1, V4L2_CID_LASTP1):
            try:
                res = self.queryctrl(id)
                self.printcontrol(res)
            except IOError, e:
                break


    def enumcontrols(self):
        _debug_('enumcontrols()', 2)
        res = {}
        id = V4L2_CTRL_FLAG_NEXT_CTRL
        while 1:
            try:
                ctrl = self.queryctrl(id)
                (id, type, name, min, max, step, default, flags, value) = ctrl
                if flags == V4L2_CTRL_FLAG_DISABLED:
                    id = ctrl[0] | V4L2_CTRL_FLAG_NEXT_CTRL
                    continue
                res[self.ctrlname(name)] = ctrl
                id = ctrl[0] | V4L2_CTRL_FLAG_NEXT_CTRL
            except IOError, e:
                break
        if id != V4L2_CTRL_FLAG_NEXT_CTRL:
            return res

        id = V4L2_CID_USER_BASE
        for id in range(V4L2_CID_FIRSTP1, V4L2_CID_LASTP1):
            try:
                ctrl = self.queryctrl(id)
                (id, type, name, min, max, step, default, flags, value) = ctrl
                if flags & V4L2_CTRL_FLAG_DISABLED:
                    continue
                res[self.ctrlname(name)] = ctrl
            except IOError, e:
                break
        return res


    def findcontrol(self, id):
        """
        find a control by id
        """
        _debug_('findcontrol(id=0x%08x)' % (id,), 2)
        for ctrl in self.controls.keys():
            if self.controls[ctrl][0] == id:
                return ctrl
        return None


    def getcontrol(self, name):
        """
        get the control record by name
        """
        _debug_('getcontrol(name=%r)' % (name,), 2)
        key = self.ctrlname(name)
        if not self.controls.has_key(key):
            raise AttributeError('Cannot getcontrol \"%s\" does not exist' % (name))
        (id, type, name, min, max, step, default, flags, value) = self.controls[key]
        return value


    def setcontrol(self, name, value):
        """
        get the control record by name
        """
        _debug_('setcontrol(name=%r, value=%r)' % (name, value), 2)
        key = self.ctrlname(name)
        if not self.controls.has_key(key):
            raise AttributeError('Cannot setcontrol \"%s\" does not exist' % (name))
        (id, type, name, min, max, step, default, flags, oldvalue) = self.controls[key]
        self.controls[key] = (id, type, name, min, max, step, default, flags, value)

        if _ID2CLASS(id) != V4L2_CTRL_CLASS_USER and id < V4L2_CID_PRIVATE_BASE:
            self.setextctrl(id, value)
        else:
            self.setctrl(id, value)
        return value


    def updatecontrol(self, name, value):
        """ set the control record by name
        """
        _debug_('updatecontrol(name=%r, value=%r)' % (name, value), 2)
        if self.getcontrol(name) == None:
            return

        oldvalue = self.getcontrol(name)
        _debug_('%-30s: value %d->%d' % ('"'+name+'"', oldvalue, value))
        if value == oldvalue:
            return

        self.setcontrol(name, value)
        return


    def init_settings(self):
        """ initialise the V4L2 setting """
        _debug_('init_settings()', 2)
        if self.device < 0:
            return False
        (v_norm, v_input, v_clist, v_dev) = config.TV_SETTINGS.split()
        self.inputs = self.enuminputs()
        self.standards = self.enumstds()
        self.controls = self.enumcontrols()
        self.setstdbyname(v_norm)
        self.setchanlist(v_clist)

        # TODO: make a good way of setting the input
        # self.setinput(...)
        return True


    def print_settings(self):
        _debug_('print_settings()', 2)
        print 'Driver: %s' % self.driver.strip('\0')
        print 'Card: %s' % self.card.strip('\0')
        print 'Version: %08x (%02u.%02u)' % (self.version, self.version / 256, self.version % 256)
        print 'Capabilities: 0x%08x' % int(self.capabilities)

        print "Enumerating supported Standards."
        try:
            for i in range(0, 255):
                (index, id, name, junk, junk, junk) = self.enumstd(i)
                print "  %i: 0x%x %s" % (index, id, name.strip('\0'))
        except:
            pass
        print "Current Standard is: 0x%x" % self.getstd()

        print "Enumerating supported Inputs."
        try:
            for i in range(0, 255):
                (index, name, type, audioset, tuner, std, status) = self.enuminput(i)
                print "  %i: %s" % (index, name.strip('\0'))
        except:
            pass
        print "Input: %i" % self.getinput()

        (buf_type, width, height, pixelformat, field, bytesperline,
         sizeimage, colorspace) = self.getfmt()
        print "Width: %i, Height: %i" % (width, height)

        try:
            print "Read Frequency: %i" % self.getfreq()
        except IOError, e:
            pass


class V4LGroup:
    def __init__(self):
        _debug_('V4LGroup.__init__()', 2)
        # Types:
        #   tv-v4l1 - video capture card with a tv tuner using v4l1
        #   tv-v4l2 - video capture card with a tv tuner using v4l2
        #   video   - video capture card (v4l1 or v4l2) using an external video
        #             source such as sattelite, digital cable box, video or
        #             security camera.
        #   webcam  - such as a USB webcam, these are handled a bit differently
        #             than most other v4l devices.

        self.type = type
        self.vdev = vdev
        self.vvbi = vvbi
        self.vinput = vinput
        self.adev = adev
        self.desc = desc
        self.inuse = False


if __name__ == '__main__':

    config.DEBUG = 3
    config.LOGGING = config.logging.DEBUG

    videodev = '/dev/video0'
    if len(sys.argv) > 1:
        videodev = sys.argv[1]
    viddev=Videodev(videodev)
    print 'Device = %r' % videodev
    print 'Driver = \"%s\"' % viddev.getdriver()
    print 'Driver Version = %02d.%02d' % (viddev.getversion() / 256, viddev.getversion() % 256)
    viddev.print_settings()
    viddev.enumcontrols()
    viddev.listcontrols()
    ctrlname = 'Median Luma Filter Minimum'
    ctrlkey = 'median_luma_filter_minimum'
    ctrlcode = 0x00991007
    mlfm = viddev.getcontrol(ctrlname)
    print 'by name:', mlfm
    mlfm = viddev.getcontrol(ctrlkey)
    print 'by key:', mlfm
    mlfm = viddev.getextctrl(ctrlcode)
    print 'by id:', mlfm
    viddev.setcontrol(ctrlname, mlfm+1)
    print '%s -> %s %s' % (mlfm, viddev.getcontrol(ctrlname), viddev.getextctrl(ctrlcode))

    NORMS['PAL_BG'] = (NORMS['PAL_B']+NORMS['PAL_B1']+NORMS['PAL_G'])
    NORMS['B'] = (NORMS['PAL_B']+NORMS['PAL_B1']+NORMS['SECAM_B'])
    NORMS['GH'] = (NORMS['PAL_G']+NORMS['PAL_H']+NORMS['SECAM_G']+NORMS['SECAM_H'])
    NORMS['PAL_DK'] = (NORMS['PAL_D']+NORMS['PAL_D1']+NORMS['PAL_K'])
    NORMS['PAL'] = (NORMS['PAL_BG']+NORMS['PAL_DK']+NORMS['PAL_H']+NORMS['PAL_I'])
    NORMS['NTSC'] = (NORMS['NTSC_M']+NORMS['NTSC_M_JP']+NORMS['NTSC_M_KR'])
    NORMS['MN'] = (NORMS['PAL_M']+NORMS['PAL_N']+NORMS['PAL_Nc']+NORMS['NTSC'])
    NORMS['SECAM_DK'] = (NORMS['SECAM_D']+NORMS['SECAM_K']+NORMS['SECAM_K1'])
    NORMS['DK'] = (NORMS['PAL_DK']+NORMS['SECAM_DK'])
    NORMS['SECAM'] = (NORMS['SECAM_B']+NORMS['SECAM_G']+NORMS['SECAM_H']+NORMS['SECAM_DK']+NORMS['SECAM_L']+NORMS['SECAM_LC'])
    NORMS['525_60'] = (NORMS['PAL_M']+NORMS['PAL_60']+NORMS['NTSC']+NORMS['NTSC_443'])
    NORMS['625_50'] = (NORMS['PAL']+NORMS['PAL_N']+NORMS['PAL_Nc']+NORMS['SECAM'])
    NORMS['UNKNOWN'] = 0
    NORMS['ALL'] = (NORMS['525_60']+NORMS['625_50'])

    print '\'%s\'      : 0x%08X, ' % ('PAL_BG', NORMS['PAL_BG'])
    print '\'%s\'           : 0x%08X, ' % ('B', NORMS['B'])
    print '\'%s\'          : 0x%08X, ' % ('GH', NORMS['GH'])
    print '\'%s\'      : 0x%08X, ' % ('PAL_DK', NORMS['PAL_DK'])
    print '\'%s\'         : 0x%08X, ' % ('PAL', NORMS['PAL'])
    print '\'%s\'        : 0x%08X, ' % ('NTSC', NORMS['NTSC'])
    print '\'%s\'          : 0x%08X, ' % ('MN', NORMS['MN'])
    print '\'%s\'    : 0x%08X, ' % ('SECAM_DK', NORMS['SECAM_DK'])
    print '\'%s\'          : 0x%08X, ' % ('DK', NORMS['DK'])
    print '\'%s\'       : 0x%08X, ' % ('SECAM', NORMS['SECAM'])
    print '\'%s\'      : 0x%08X, ' % ('525_60', NORMS['525_60'])
    print '\'%s\'      : 0x%08X, ' % ('625_50', NORMS['625_50'])
    print '\'%s\'     : 0x%08X, ' % ('UNKNOWN', NORMS['UNKNOWN'])
    print '\'%s\'         : 0x%08X, ' % ('ALL', NORMS['ALL'])

    inputs = viddev.enuminputs()
    print 'inputs = %r' % (inputs.keys())
    standards = viddev.enumstds()
    print 'standards = %r' % (standards.keys())
    try:
        viddev.setinputbyname('composite 1')
        print viddev.getinput()
    except KeyError:
        pass
    try:
        viddev.setstdbyname('PAL')
        print '0x%08X' % viddev.getstd()
    except (KeyError, IOError):
        pass
    try:
        viddev.setinputbyname('tuner 1')
        print viddev.getinput()
    except KeyError:
        pass

    viddev.close()

#"""
#To run this as standalone use the following before running python v4l2.py
#pythonversion=$(python -V 2>&1 | cut -d" " -f2 | cut -d"." -f1-2)
#export PYTHONPATH=/usr/lib/python${pythonversion}/site-packages/freevo
#export FREEVO_SHARE=/usr/share/freevo
#export FREEVO_CONFIG=/usr/share/freevo/freevo_config.py
#export FREEVO_CONTRIB=/usr/share/freevo/contrib
#export RUNAPP=""
#python v4l2.py
#OR
#freevo execute v4l2.py [<video device>]
#"""
