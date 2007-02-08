# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# v4l2.py - V4L2 python interface.
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
import freq
import os
import struct
import array
import fcntl
import sys

import config

DEBUG = config.DEBUG

# Different formats depending on word size
bit32 = struct.calcsize('L') == struct.calcsize('I')

def i32(x): return (x&0x80000000L and -2*0x40000000 or 0) + int(x&0x7fffffff)

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

def _IOC(dir,type,nr,size):
    return (((dir)  << _IOC_DIRSHIFT) | \
           (ord(type) << _IOC_TYPESHIFT) | \
           ((nr)   << _IOC_NRSHIFT) | \
           ((size) << _IOC_SIZESHIFT))

def _IO(type,nr): return _IOC(_IOC_NONE,(type),(nr),0)

def _IOR(type,nr,size): return _IOC(_IOC_READ,(type),(nr),struct.calcsize(size))

def _IOW(type,nr,size): return _IOC(_IOC_WRITE,(type),(nr),struct.calcsize(size))

def _IOWR(type,nr,size): return _IOC(_IOC_READ|_IOC_WRITE,(type),(nr),struct.calcsize(size))

# used to decode ioctl numbers..
def _IOC_DIR(nr): return (((nr) >> _IOC_DIRSHIFT) & _IOC_DIRMASK)
def _IOC_TYPE(nr): return (((nr) >> _IOC_TYPESHIFT) & _IOC_TYPEMASK)
def _IOC_NR(nr): return (((nr) >> _IOC_NRSHIFT) & _IOC_NRMASK)
def _IOC_SIZE(nr): return (((nr) >> _IOC_SIZESHIFT) & _IOC_SIZEMASK)

def _ID2CLASS(id): return ((id) & 0x0fff0000)


QUERYCAP_ST      = "<16s32s32sII16x"
QUERYCAP_NO      = _IOR('V',  0, QUERYCAP_ST)

FMT_ST           = bit32 and "<I7I4x168x" or "<Q7I4x168x"
GET_FMT_NO       = _IOWR('V',  4, FMT_ST)
SET_FMT_NO       = _IOWR('V',  5, FMT_ST)

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

EXT_CTRL_ST      = "@L2Lq"         # (id, res1, res2, s64)
EXT_CTRLS_ST     = "@LLL2LP"       # (class, count, error_idx, res1, res2, ptr)
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
    'NTSC'  : 0x3000,
    'PAL'   : 0xff,
    'SECAM' : 0x7f0000,
}


class Videodev:
    def __init__(self, device):
        self.chanlist = None
        self.device = os.open (device, os.O_TRUNC)
        if self.device < 0:
            sys.exit("Error: %d\n" %self.device)
        else:
            if DEBUG: print "Video Opened at %s" % device

        results           = self.querycap()
        self.driver       = results[0]
        self.card         = results[1]
        self.bus_info     = results[2]
        self.version      = results[3]
        self.capabilities = results[4]
        self.controls     = {}
    

    def getdriver(self):
        return self.driver


    def getversion(self):
        return self.version


    def getdevice(self):
        return self.device


    def close(self):
        os.close(self.device)


    def setchanlist(self, chanlist):
        self.chanlist = freq.CHANLIST[chanlist]


    def getfreq(self):
        val = struct.pack(FREQUENCY_ST, 0,0,0)
        r = fcntl.ioctl(self.device, i32(GETFREQ_NO), val)
        res = struct.unpack(FREQUENCY_ST, r)
        if DEBUG >= 3: print "getfreq: val=%r, r=%r, res=%r" % (val, r, res)
        (tuner, type, freq,) = res
        return freq


    def getfreq2(self):
        val = struct.pack(FREQUENCY_ST, 0,0,0)
        r = fcntl.ioctl(self.device, i32(GETFREQ_NO), val)
        res = struct.unpack(FREQUENCY_ST, r)
        if DEBUG >= 3: print "getfreq2: val=%r, r=%s, res=%r" % (val, r, res)
        return res


    def setchannel(self, channel):
        freq = config.FREQUENCY_TABLE.get(channel)
        if freq:
            if DEBUG: 
                print 'USING CUSTOM FREQUENCY: chan="%s", freq="%s"' % \
                      (channel, freq)
        else:
            freq = self.chanlist[str(channel)]
            if DEBUG: 
                print 'USING STANDARD FREQUENCY: chan="%s", freq="%s"' % \
                      (channel, freq)

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
        val = struct.pack("L", freq)
        r = fcntl.ioctl(self.device, i32(SETFREQ_NO_V4L), val)        
        if DEBUG >= 3: print "setfreq_old: val=%r, r=%r" % (val, r)


    def setfreq(self, freq):
        val = struct.pack(FREQUENCY_ST, long(0), long(2), freq)
        r = fcntl.ioctl(self.device, i32(SETFREQ_NO), val)
        if DEBUG >= 3: print "setfreq: val=%r, r=%r" % (val, r)


    def getinput(self):
        val = struct.pack(INPUT_ST,0)
        r = fcntl.ioctl(self.device, i32(GETINPUT_NO), val)
        res = struct.unpack(INPUT_ST,r)
        if DEBUG >= 3: print "getinput: val=%r, %d, res=%r" % (val, len(val), res)
        return res[0]
  

    def setinput(self, value):
        try:
            r = fcntl.ioctl(self.device, i32(SETINPUT_NO), struct.pack(INPUT_ST, value))
            if DEBUG: print "setinput: val=%r, res=%r" % (struct.pack(INPUT_ST, value), r)
        except IOError:
            self.print_settings
            raise


    def querycap(self):
        val = struct.pack(QUERYCAP_ST, "", "", "", 0, 0)
        r = fcntl.ioctl(self.device, i32(QUERYCAP_NO), val)
        res = struct.unpack(QUERYCAP_ST, r)
        if DEBUG >= 3: print "querycap: val=%r, %d, res=%r" % (val, len(val), res)
        return res


    def enumstd(self, no):
        val = struct.pack(ENUMSTD_ST, no, 0, "", 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(ENUMSTD_NO), val)
        res = struct.unpack(ENUMSTD_ST, r)
        if DEBUG >= 3: print "enumstd: val=%r, %d, res=%r" % (val, len(val), res)
        return res


    def getstd(self):
        val = struct.pack(STANDARD_ST, 0)
        r = fcntl.ioctl(self.device, i32(GETSTD_NO), val)
        res = struct.unpack(STANDARD_ST, r)
        if DEBUG >= 3: print "getstd: val=%r, %d, res=%r" % (val, len(val), res)
        return res[0]


    def setstd(self, value):
        val = struct.pack(STANDARD_ST, value)
        r = fcntl.ioctl(self.device, i32(SETSTD_NO), val)
        if DEBUG >= 3: print "setstd: val=%r, r=%r" % (val, r)


    def enuminput(self,index):
        val = struct.pack(ENUMINPUT_ST, index, "", 0,0,0,0,0)
        r = fcntl.ioctl(self.device, i32(ENUMINPUT_NO), val)
        res = struct.unpack(ENUMINPUT_ST, r)
        if DEBUG >= 3: print "enuminput: val=%r, %d, res=%r" % (val, len(val), res)
        return res


    def getfmt(self):  
        val = struct.pack(FMT_ST, 1,0,0,0,0,0,0,0)
        r = fcntl.ioctl(self.device, i32(GET_FMT_NO), val)
        res = struct.unpack(FMT_ST, r)
        if DEBUG >= 3: print "getfmt: val=%r, %d, res=%r" % (val, len(val), res)
        return res


    def setfmt(self, width, height):
        val = struct.pack(FMT_ST, 1L, width, height, 0L, 4L, 0L, 131072L, 0L)
        r = fcntl.ioctl(self.device, i32(SET_FMT_NO), val)
        if DEBUG >= 3: print "setfmt: val=%r, r=%r" % (val, r)


    def gettuner(self,index):
        val = struct.pack(TUNER_ST, index, "", 0,0,0,0,0,0,0,0)
        r = fcntl.ioctl(self.device, i32(GET_TUNER_NO), val)
        res = struct.unpack(TUNER_ST, r)
        if DEBUG >= 3: print "gettuner: val=%r, %d, res=%r" % (val, len(val), res)
        return res


    def settuner(self,index,audmode):
        val = struct.pack(TUNER_ST, index, "", 0,0,0,0,0,audmode,0,0)
        r = fcntl.ioctl(self.device, i32(SET_TUNER_NO), val)
        if DEBUG >= 3: print "settuner: val=%r, r=%r" % (val, r)


    def getaudio(self,index):
        val = struct.pack(AUDIO_ST, index, "", 0,0)
        r = fcntl.ioctl(self.device, i32(GET_AUDIO_NO), val)
        res = struct.unpack(AUDIO_ST, r)
        if DEBUG >= 3: print "getaudio: val=%r, %d, res=%r" % (val, len(val), res)
        return res


    def setaudio(self,index,mode):
        val = struct.pack(AUDIO_ST, index, "", mode, 0)
        r = fcntl.ioctl(self.device, i32(SET_AUDIO_NO), val)
        if DEBUG >= 3: print "setaudio: val=%r, r=%r" % (val, r)


    def getctrl(self, id):
        '''
        Get the value of a control
        '''
        val = struct.pack(CTRL_ST, id, 0)
        r = fcntl.ioctl(self.device, i32(G_CTRL_NO), val)
        res = struct.unpack(CTRL_ST, r)
        if DEBUG >= 3: print "getctrl: val=%r, %d, res=%r" % (val, len(val), res)
        return res[1]


    def setctrl(self, id, value):
        '''
        Set the value of a control
        '''
        val = struct.pack(CTRL_ST, id, value)
        r = fcntl.ioctl(self.device, i32(S_CTRL_NO), val)
        res = struct.unpack(CTRL_ST, r)
        if DEBUG >= 3: print "setctrl: val=%r, %d, res=%r" % (val, len(val), res)


    def getextctrl(self, id):
        '''
        Get the value of an external control
        EXT_CTRL_type->id, res1, res2, value
        EXT_CTRLS_ST->class, count, error_idx, res1, res2, ptr
        '''
        extctrl = array.array('B')
        extctrl.fromstring(struct.pack(EXT_CTRL_ST, id, 0, 0, 0))
        extctrl_p = extctrl.buffer_info()[0]
        val = struct.pack(EXT_CTRLS_ST, _ID2CLASS(id), 1, 0, 0, 0, extctrl_p)
        try:
            r = fcntl.ioctl(self.device, i32(G_EXT_CTRLS_NO), val)
            res = struct.unpack(EXT_CTRLS_ST, r)
            extres = struct.unpack(EXT_CTRL_ST, extctrl.tostring())
            if DEBUG >= 3: print "getextctrl: val=%r, %d, res=%r" % (val, len(val), res)
            if DEBUG >= 3: print "getextctrl: extctrl=%r, %d, extres=%s" % (extctrl.tostring(), len(extctrl), extres)
        except IOError, e:
            extres = struct.unpack(EXT_CTRL_ST, extctrl.tostring())
            print 'getextctrl:', e
        return extres[3]


    def setextctrl(self, id, value):
        '''
        Set the value of an external control
        '''
        extctrl = array.array('B')
        extctrl.fromstring(struct.pack(EXT_CTRL_ST, id, 0, 0, value))
        extctrl_p = extctrl.buffer_info()[0]
        val = struct.pack(EXT_CTRLS_ST, _ID2CLASS(id), 1, 0, 0, 0, extctrl_p)
        try:
            r = fcntl.ioctl(self.device, i32(S_EXT_CTRLS_NO), val)
            res = struct.unpack(EXT_CTRLS_ST, r)
            extres = struct.unpack(EXT_CTRL_ST, extctrl.tostring())
            if DEBUG >= 3: print "setextctrl: val=%r, %d, res=%r" % (val, len(val), res)
            if DEBUG >= 3: print "setextctrl: extctrl=%r, %d, extres=%s" % (extctrl.tostring(), len(extctrl), extres)
        except IOError, e:
            print 'setextctrl:', id, self.findcontrol(id), e


    def querymenu(self, id, index):
        val = struct.pack(QUERYMENU_ST, id, index, "", 0)
        try:
            r = fcntl.ioctl(self.device, i32(QUERYMENU_NO), val)
            res = struct.unpack(QUERYMENU_ST, r)
            if DEBUG >= 3: print "querymenu: val=%r, %d, res=%r" % (val, len(val), res)
        except IOError, e:
            res = struct.unpack(QUERYMENU_ST, val)
        return res


    def queryctrl(self, id):
        val = struct.pack(QUERYCTRL_ST, id, 0, "", 0, 0, 0, 0, 0, 0, 0)
        r = fcntl.ioctl(self.device, i32(QUERYCTRL_NO), val)
        res = struct.unpack(QUERYCTRL_ST, r)
        if DEBUG >= 3: print "queryctrl: val=%r, %d, res=%r" % (val, len(val), res)
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
            for i in range(min,max+1):
                (id, index, name, res1) = self.querymenu(id, i)
                print 'index=%d, name=\"%s\"' % (index, name)


    def listcontrols(self):
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


    def getcontrols(self):
        self.controls = {}
        id = V4L2_CTRL_FLAG_NEXT_CTRL
        while 1:
            try:
                res = self.queryctrl(id)
                (id, type, name, min, max, step, default, flags, value) = res
                if flags == V4L2_CTRL_FLAG_DISABLED:
                    id = res[0] | V4L2_CTRL_FLAG_NEXT_CTRL
                    continue
                self.controls[name] = res
                id = res[0] | V4L2_CTRL_FLAG_NEXT_CTRL
            except IOError, e:
                break
        if id != V4L2_CTRL_FLAG_NEXT_CTRL:
            return self.controls

        id = V4L2_CID_USER_BASE
        for id in range(V4L2_CID_FIRSTP1, V4L2_CID_LASTP1):
            try:
                res = self.queryctrl(id)
                (id, type, name, min, max, step, default, flags, value) = res
                if flags & V4L2_CTRL_FLAG_DISABLED:
                    continue
            except IOError, e:
                break
        return self.controls


    def findcontrol(self, id):
        '''
        find a control by id
        '''
        for ctrl in self.controls.keys():
            if self.controls[ctrl][0] == id:
                return ctrl
        return None


    def getcontrol(self, name):
        '''
        get the control record by name
        '''
        if not self.controls.has_key(name):
            print 'control \"%s\" does not exists' % (name)
            return None
        (id, type, name, min, max, step, default, flags, value) = self.controls[name]
        return value


    def setcontrol(self, name, value):
        '''
        get the control record by name
        '''
        if not self.controls.has_key(name):
            print 'control \"%s\" does not exists' % (name)
            return None
        (id, type, name, min, max, step, default, flags, oldvalue) = self.controls[name]
        self.controls[name] = (id, type, name, min, max, step, default, flags, value)

        if _ID2CLASS(id) != V4L2_CTRL_CLASS_USER and id < V4L2_CID_PRIVATE_BASE:
            self.setextctrl(id, value)
        else:
            self.setctrl(id, value)
        return value


    def updatecontrol(self, name, value):
        '''
        set the control record by name
        '''
        if DEBUG >= 1: print 'name=\"%s\", value=%d' % (name, value)
        if not self.getcontrol(name):
            return

        oldvalue = self.getcontrol(name)
        if value == oldvalue:
            return

        self.setcontrol(name, value)
        return


    def init_settings(self):
        (v_norm, v_input, v_clist, v_dev) = config.TV_SETTINGS.split()
        v_norm = string.upper(v_norm)
        self.setstd(NORMS.get(v_norm))
        self.setchanlist(v_clist)
        self.getcontrols()

        # XXX TODO: make a good way of setting the input
        # self.setinput(....)


    def print_settings(self):
        print 'Driver: %s' % self.driver
        print 'Card: %s' % self.card
        print 'Version: %x' % self.version
        print 'Capabilities: %s' % self.capabilities

        print "Enumerating supported Standards."
        try:
            for i in range(0,255):
                (index,id,name,junk,junk,junk) = self.enumstd(i)
                print "  %i: 0x%x %s" % (index, id, name)
        except:
            pass
        print "Current Standard is: 0x%x" % self.getstd()

        print "Enumerating supported Inputs."
        try:
            for i in range(0,255):
                (index,name,type,audioset,tuner,std,status) = self.enuminput(i)
                print "  %i: %s" % (index, name)
        except:
            pass
        print "Input: %i" % self.getinput()

        (buf_type, width, height, pixelformat, field, bytesperline,
         sizeimage, colorspace) = self.getfmt()
        print "Width: %i, Height: %i" % (width,height)

        print "Read Frequency: %i" % self.getfreq()


class V4LGroup:
    def __init__(self):
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

    DEBUG = 4
    viddev=Videodev('/dev/video0')
    print 'Driver = \"%s\"' % viddev.getdriver()
    print 'Driver Version = %x' % viddev.getversion()
    #print viddev.querycap()
    inp = viddev.getinput()
    viddev.setinput(inp)
    print 'querycap:', viddev.querycap()
    fmt = viddev.getstd()
    print 'fmt:', fmt
    std = viddev.getfmt()
    print 'std:', std
    viddev.setfmt(720, 576)
    std = viddev.getfmt()
    print 'std:', std
    
    print 'QUERYCAP_ST=%s %s' % (QUERYCAP_ST, struct.calcsize(QUERYCAP_ST))
    print 'FREQUENCY_ST=%s %s' % (FREQUENCY_ST, struct.calcsize(FREQUENCY_ST))
    print 'ENUMSTD_ST=%s %s' % (ENUMSTD_ST, struct.calcsize(ENUMSTD_ST))
    print 'STANDARD_ST=%s %s' % (STANDARD_ST, struct.calcsize(STANDARD_ST))
    print 'ENUMINPUT_ST=%s %s' % (ENUMINPUT_ST, struct.calcsize(ENUMINPUT_ST))
    print 'INPUT_ST=%s %s' % (INPUT_ST, struct.calcsize(INPUT_ST))
    print 'FMT_ST=%s %s' % (FMT_ST, struct.calcsize(FMT_ST))
    print 'TUNER_ST=%s %s' % (TUNER_ST, struct.calcsize(TUNER_ST))
    print 'AUDIO_ST=%s %s' % (AUDIO_ST, struct.calcsize(AUDIO_ST))

    viddev=Videodev('/dev/video0')
    '''
    viddev.print_settings()
    print 
    print viddev.querycap()
    inp = viddev.getinput()
    print 'viddev.getinput=%s' % (inp)
    viddev.setinput(inp)
    print 'viddev.setinput okay'
    fmt = viddev.getfmt()
    (buf_type, width, height, pixelformat, field, bytesperline,
         sizeimage, colorspace) = fmt
    print 'viddev.getfmt=%s' % (buf_type)
    print viddev.enuminput(inp)
    for i in range(0,99):
        try:
            print viddev.gettuner(i)
        except IOError:
            break
    print viddev.getaudio(0)
    print viddev.setfreq(2132)
    print viddev.getfreq()
    print viddev.setfreq(8948)
    print viddev.getfreq()
    print viddev.getfreq2()
    '''
    DEBUG=0
    viddev.listcontrols()
    dict = viddev.getcontrols()
    keys = list(dict)
    keys.sort()
    print keys
    for ctrl in keys:
        print dict[ctrl]
    viddev.setextctrl(0x009909c9, 2)
    print '0x009909c9 = %d' % viddev.getextctrl(0x009909c9)
    viddev.setextctrl(0x009909cf, 7000000)
    print '0x009909cf = %d' % viddev.getextctrl(0x009909cf)
    bitrate = viddev.getcontrol('Video Bitrate')
    viddev.updatecontrol('Video Bitrate', bitrate+1)
    print 'Video Bitrate = %d' % viddev.getcontrol('Video Bitrate')
    print '0x009909cf = %d' % viddev.getextctrl(0x009909cf)

    stream_type = 4
    viddev.updatecontrol('Stream Type', stream_type)
    #viddev.setcontrol('Stream Type', stream_type)
    #viddev.setextctrl(0x00990900, stream_type)
    print 'Stream Type = %d' % viddev.getcontrol('Stream Type')
    print '0x00990900 = %d' % viddev.getextctrl(0x00990900)
    DEBUG=4
    print 'getfreq:', viddev.getfreq()

    viddev.close()

'''
To run this as standalone use the following before running python v4l2.py
pythonversion=$(python -V 2>&1 | cut -d" " -f2 | cut -d"." -f1-2)
export PYTHONPATH=/usr/lib/python${pythonversion}/site-packages/freevo
export FREEVO_SHARE=/usr/share/freevo
export FREEVO_CONFIG=/usr/share/freevo/freevo_config.py
export FREEVO_CONTRIB=/usr/share/freevo/contrib
export RUNAPP=""
python v4l2.py
OR
freevo execute v4l2.py
'''
