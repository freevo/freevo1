# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ivtv.py - Python interface to ivtv based capture cards.
# -----------------------------------------------------------------------
# $Id$
#
# Notes: http://ivtv.sf.net
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
# ----------------------------------------------------------------------- */


import string, struct, fcntl, time

#import tv.v4l2, config
import config
import tv.v4l2

DEBUG = config.DEBUG

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

# structs
CODEC_ST = '15I'
MSP_MATRIX_ST = '2i'
VBI_EMBED_ST = "I"
GOP_END_ST = "I"

# ioctls
IVTV_IOC_G_CODEC = 0xFFEE7703
IVTV_IOC_S_CODEC = 0xFFEE7704
MSP_SET_MATRIX =   0x40086D11

GETVBI_EMBED_NO  = _IOR('@', 55, VBI_EMBED_ST) #IVTV_IOC_G_VBI_EMBED
SETVBI_EMBED_NO  = _IOW('@', 54, VBI_EMBED_ST) #IVTV_IOC_S_VBI_EMBED

GOP_END_NO   = _IOWR('@', 50, GOP_END_ST) #IVTV_IOC_S_GOP_END used to wait for a GOP

# Stream types 
IVTV_STREAM_PS     = 0
IVTV_STREAM_TS     = 1
IVTV_STREAM_MPEG1  = 2
IVTV_STREAM_PES_AV = 3
IVTV_STREAM_PES_V  = 5
IVTV_STREAM_PES_A  = 7
IVTV_STREAM_DVD    = 10


class IVTV(tv.v4l2.Videodev):

    def __init__(self, device):
        tv.v4l2.Videodev.__init__(self, device)


    def setCodecInfo(self, codec):
        val = struct.pack( CODEC_ST, 
                           codec.aspect,
                           codec.audio_bitmask,
                           codec.bframes,
                           codec.bitrate_mode,
                           codec.bitrate,
                           codec.bitrate_peak,
                           codec.dnr_mode,
                           codec.dnr_spatial,
                           codec.dnr_temporal,
                           codec.dnr_type,
                           codec.framerate,
                           codec.framespergop,
                           codec.gop_closure,
                           codec.pulldown,
                           codec.stream_type)
        r = fcntl.ioctl(self.device, i32(IVTV_IOC_S_CODEC), val)
        if DEBUG >= 3: print "setCodecInfo: val=%r, r=%r" % (val, r)


    def getCodecInfo(self):
        val = struct.pack( CODEC_ST, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 )
        r = fcntl.ioctl(self.device, i32(IVTV_IOC_G_CODEC), val)
        codec_list = struct.unpack(CODEC_ST, r)
        if DEBUG >= 3: print "getCodecInfo: val=%r, r=%r, res=%r" % (val, r, struct.unpack(CODEC_ST, r))
        return IVTVCodec(codec_list)


    def mspSetMatrix(self, input=None, output=None):
        if not input: input = 3
        if not output: output = 1

        val = struct.pack(MSP_MATRIX_ST, input, output)
        r = fcntl.ioctl(self.device, i32(MSP_SET_MATRIX), val)
        if DEBUG >= 3: print "mspSetMatrix: val=%r, r=%r" % (val, r)


    def getvbiembed(self):
        r = fcntl.ioctl(self.device, i32(GETVBI_EMBED_NO), struct.pack(VBI_EMBED_ST,0))
        if DEBUG >= 3:
            print "getvbiembed: val=%r, r=%r, res=%r" % (struct.pack(VBI_EMBED_ST,0), r, struct.unpack(VBI_EMBED_ST,r))
        return struct.unpack(VBI_EMBED_ST,r)[0]
  

    def setvbiembed(self, value):
        r = fcntl.ioctl(self.device, i32(SETVBI_EMBED_NO), struct.pack(VBI_EMBED_ST, value))
        if DEBUG: print "setvbiembed: val=%r, res=%r" % (struct.pack(VBI_EMBED_ST, value), r)


    def gopend(self, value):
        r = fcntl.ioctl(self.device, i32(GOP_END_NO), struct.pack(GOP_END_ST, value))
        if DEBUG: print "gopend: val=%r, res=%r" % (struct.pack(GOP_END_ST, value), r)


    def init_settings(self, opts=None):
        if not opts:
            opts = config.TV_IVTV_OPTIONS

        tv.v4l2.Videodev.init_settings(self)

        (width, height) = string.split(opts['resolution'], 'x')
        self.setfmt(int(width), int(height))

        codec = self.getCodecInfo()

        codec.aspect        = opts['aspect']
        codec.audio_bitmask = opts['audio_bitmask']
        codec.bframes       = opts['bframes']
        codec.bitrate_mode  = opts['bitrate_mode']
        codec.bitrate       = opts['bitrate']
        codec.bitrate_peak  = opts['bitrate_peak']
        codec.dnr_mode      = opts['dnr_mode']
        codec.dnr_spatial   = opts['dnr_spatial']
        codec.dnr_temporal  = opts['dnr_temporal']
        codec.dnr_type      = opts['dnr_type']
        # XXX: Ignore framerate for now, use the card's initialized default.
        # codec.framerate     = opts['framerate']
        # XXX: Ignore framespergop for now, use the card's initialized default.
        # codec.framespergop  = opts['framespergop']
        codec.gop_closure   = opts['gop_closure']
        codec.pulldown      = opts['pulldown']
        codec.stream_type   = opts['stream_type']

        self.setCodecInfo(codec)


    def print_settings(self):
        tv.v4l2.Videodev.print_settings(self)

        codec = self.getCodecInfo()

        print 'CODEC::aspect: %s' % codec.aspect
        print 'CODEC::audio_bitmask: %s' % codec.audio_bitmask
        print 'CODEC::bfrmes: %s' % codec.bframes
        print 'CODEC::bitrate_mode: %s' % codec.bitrate_mode
        print 'CODEC::bitrate: %s' % codec.bitrate
        print 'CODEC::bitrate_peak: %s' % codec.bitrate_peak
        print 'CODEC::dnr_mode: %s' % codec.dnr_mode
        print 'CODEC::dnr_spatial: %s' % codec.dnr_spatial
        print 'CODEC::dnr_temporal: %s' % codec.dnr_temporal
        print 'CODEC::dnr_type: %s' % codec.dnr_type
        print 'CODEC::framerate: %s' % codec.framerate
        print 'CODEC::framespergop: %s' % codec.framespergop
        print 'CODEC::gop_closure: %s' % codec.gop_closure
        print 'CODEC::pulldown: %s' % codec.pulldown
        print 'CODEC::stream_type: %s' % codec.stream_type


class IVTVCodec:
    def __init__(self, args):
        self.aspect        = args[0]
        self.audio_bitmask = args[1]
        self.bframes       = args[2]
        self.bitrate_mode  = args[3]
        self.bitrate       = args[4]
        self.bitrate_peak  = args[5]
        self.dnr_mode      = args[6]
        self.dnr_spatial   = args[7]
        self.dnr_temporal  = args[8]
        self.dnr_type      = args[9]
        self.framerate     = args[10]
        self.framespergop  = args[11]
        self.gop_closure   = args[12]
        self.pulldown      = args[13]
        self.stream_type   = args[14]


'''
To run this as standalone use the following before running python v4l2.py
pythonversion=$(python -V 2>&1 | cut -d" " -f2 | cut -d"." -f1-2)
export PYTHONPATH=/usr/lib/python${pythonversion}/site-packages/freevo
export FREEVO_SHARE=/usr/share/freevo
export FREEVO_CONFIG=/usr/share/freevo/freevo_config.py
export FREEVO_CONTRIB=/usr/share/freevo/contrib
export RUNAPP=""
'''

if __name__ == '__main__':

    ivtv_dev = IVTV('/dev/video0')
    print config.TV_IVTV_OPTIONS
    print ivtv_dev.print_settings()
    print ivtv_dev.init_settings()
    embed = ivtv_dev.getvbiembed()
    print "embed=%s" % embed
    ivtv_dev.setvbiembed(1)
    print "embed=%s (%s)" % (ivtv_dev.getvbiembed(), 1)
    ivtv_dev.setvbiembed(embed)
    print "embed=%s (%s)" % (ivtv_dev.getvbiembed(), embed)
