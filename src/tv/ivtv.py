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
# -----------------------------------------------------------------------


import string, struct, fcntl, time

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
# changed in ivtv-0.8.0 and higher
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


    def streamTypeIvtvToV4l2(self, stream_type):
        map_ivtv_to_v4l2 = {
             0 : 0,  1 : 3,  2 : 2,  3 : 3,  5 : 3,  7 : 3,
            10 : 3, 11 : 4, 12 : 5, 13 : 3, 14 : 3
        }
        try:
            if DEBUG >= 1:
                print 'streamTypeIvtvToV4l2 %s -> %s' % (stream_type, map_ivtv_to_v4l2[stream_type])
            return map_ivtv_to_v4l2[stream_type]
        except:
            print 'streamTypeIvtvToV4l2 %s failed' % (stream_type)
        return 0


    def streamTypeV4l2ToIVTV(self, stream_type):
        map_v4l2_to_ivtv = {
            0 : 0, 2 : 2, 3 : 10, 4 : 11, 5 : 12,
        }
        try:
            if DEBUG >= 1:
                print 'streamTypeV4l2ToIVTV %s -> %s' % (stream_type, map_v4l2_to_ivtv[stream_type])
            return map_v4l2_to_ivtv[stream_type]
        except:
            print 'streamTypeV4l2ToIVTV %s failed' % (stream_type)
        return 0


    def getCodecInfo(self):
        if self.version >= 0x800:
            aspect = tv.v4l2.Videodev.getcontrol(self, 'Video Aspect')+1
            audio_bitmask = 0
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio Sampling Frequency') << 0)
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio Layer II Bitrate') << 2)
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio Encoding Layer') << 6)
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio Stereo Mode') << 8)
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio Stereo Mode Extension') << 10)
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio Emphasis') << 12)
            audio_bitmask |= (tv.v4l2.Videodev.getcontrol(self, 'Audio CRC') << 14)
            bframes = tv.v4l2.Videodev.getcontrol(self, 'Video B Frames')+1
            bitrate_mode = tv.v4l2.Videodev.getcontrol(self, 'Video Bitrate Mode')
            bitrate = tv.v4l2.Videodev.getcontrol(self, 'Video Bitrate')
            bitrate_peak = tv.v4l2.Videodev.getcontrol(self, 'Video Peak Bitrate')
            dnr_mode = 0
            dnr_mode |= tv.v4l2.Videodev.getcontrol(self, 'Spatial Filter Mode') << 0
            dnr_mode |= tv.v4l2.Videodev.getcontrol(self, 'Temporal Filter Mode') << 1
            dnr_spatial = tv.v4l2.Videodev.getcontrol(self, 'Spatial Filter')
            dnr_temporal = tv.v4l2.Videodev.getcontrol(self, 'Temporal Filter')
            dnr_type = tv.v4l2.Videodev.getcontrol(self, 'Median Filter Type')
            framerate = 0
            framespergop = tv.v4l2.Videodev.getcontrol(self, 'Video GOP Size')
            gop_closure = tv.v4l2.Videodev.getcontrol(self, 'Video GOP Closure')
            pulldown = tv.v4l2.Videodev.getcontrol(self, 'Video Pulldown')
            stream_type = self.streamTypeV4l2ToIVTV(tv.v4l2.Videodev.getcontrol(self, 'Stream Type'))
            codec_list = (aspect, audio_bitmask, bframes, bitrate_mode, bitrate, bitrate_peak,
                dnr_mode, dnr_spatial, dnr_temporal, dnr_type, framerate, framespergop, gop_closure,
                pulldown, stream_type)
            return IVTVCodec(codec_list)

        val = struct.pack( CODEC_ST, 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 )
        r = fcntl.ioctl(self.device, i32(IVTV_IOC_G_CODEC), val)
        codec_list = struct.unpack(CODEC_ST, r)
        if DEBUG >= 3: print "getCodecInfo: val=%r, r=%r, res=%r" % (val, r, struct.unpack(CODEC_ST, r))
        return IVTVCodec(codec_list)


    def setCodecInfo(self, codec):
        if self.version >= 0x800:
            '''
            'audio_bitmask' : 0xE9,
            NOTE: doesn't quite map to firmware api
            0:1 'Audio Sampling Frequency':
                '00' 44.1Khz
                '01' 48Khz
                '10' 32Khz
                '11' reserved
            2:3 'Audio Encoding Layer':
                '01'=Layer I
                '10'=Layer II
            4:7 'Audio Layer II Bitrate':
                     Index | Layer I     | Layer II
                     ------+-------------+------------
                    '0000' | free format | free format
                    '0001' |  32 kbit/s  |  32 kbit/s
                    '0010' |  64 kbit/s  |  48 kbit/s
                    '0011' |  96 kbit/s  |  56 kbit/s
                    '0100' | 128 kbit/s  |  64 kbit/s
                    '0101' | 160 kbit/s  |  80 kbit/s
                    '0110' | 192 kbit/s  |  96 kbit/s
                    '0111' | 224 kbit/s  | 112 kbit/s
                    '1000' | 256 kbit/s  | 128 kbit/s
                    '1001' | 288 kbit/s  | 160 kbit/s
                    '1010' | 320 kbit/s  | 192 kbit/s
                    '1011' | 352 kbit/s  | 224 kbit/s
                    '1100' | 384 kbit/s  | 256 kbit/s
                    '1101' | 416 kbit/s  | 320 kbit/s
                    '1110' | 448 kbit/s  | 384 kbit/s
                Note: For Layer II, not all combinations of total bitrate
                and mode are allowed. See ISO11172-3 3-Annex B, Table 3-B.2
            8:9 'Audio Stereo Mode':
                    '00'=Stereo
                    '01'=JointStereo
                    '10'=Dual
                    '11'=Mono
            10:11 'Audio Stereo Mode Extension' used in joint_stereo mode.
                In Layer I and II they indicate which subbands are in
                intensity_stereo. All other subbands are coded in stereo.
                    '00' subbands 4-31 in intensity_stereo, bound==4
                    '01' subbands 8-31 in intensity_stereo, bound==8
                    '10' subbands 12-31 in intensity_stereo, bound==12
                    '11' subbands 16-31 in intensity_stereo, bound==16
            12:13 'Audio Emphasis':
                    '00' None
                    '01' 50/15uS
                    '10' reserved
                    '11' CCITT J.17
            14 'Audio CRC':
                    '0' off
                    '1' on
            15 'Audio Copyright': not used
                    '0' off
                    '1' on
            16 'Audio Generation': not used
                    '0' copy
                    '1' original

            IVTV_STREAM_PS      0 -> 0: MPEG-2 Program Stream
            IVTV_STREAM_TS      1 -> 3:
            IVTV_STREAM_MPEG1   2 -> 2: MPEG-1 System Stream
            IVTV_STREAM_PES_AV  3 -> 3:
            IVTV_STREAM_PES_V   5 -> 3:
            IVTV_STREAM_PES_A   7 -> 3:
            IVTV_STREAM_DVD    10 -> 3: MPEG-2 DVD-compatible Stream
            IVTV_STREAM_VCD    11 -> 4: MPEG-1 VCD-compatible Stream
            IVTV_STREAM_SVCD   12 -> 5: MPEG-2 SVCD-compatible Stream
            IVTV_STREAM_DVD_S1 13 -> 3:
            IVTV_STREAM_DVD_S2 14 -> 3:


            VIDIOC_S_INPUT         'input'          : 4,
            VIDIOC_S_FMT           'resolution'     : '720x576',
            'Video Aspect'         'aspect'         : 2,
            'Video B Frames'       'bframes'        : 3,
            'Video Bitrate Mode'   'bitrate_mode'   : 0,
            'Video Bitrate'        'bitrate'        : 8000000,
            'Video Peak Bitrate'   'bitrate_peak'   : 9600000,
            'Spatial Filter Mode'  'dnr_mode, bit 0': 3,
            'Temporal Filter Mode' 'dnr_mode, bit 1': 3,
            'Median Filter Type'   'dnr_type'       : 0,
            'Spatial Filter'       'dnr_spatial     : 0,
            'Temporal Filter'      'dnr_temporal    : 0,
            VIDIOC_S_STD           'framerate'      : 0,
            'Video GOP Size'       'framespergop'   : 12,
            'Video GOP Closure'    'gop_closure'    : 1,
            'Video Pulldown'       'pulldown'       : 0,
            'Stream Type'          'stream_type'    : 14,
            '''
            tv.v4l2.Videodev.updatecontrol(self, 'Video Aspect', codec.aspect-1)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio Sampling Frequency', (codec.audio_bitmask >> 0) & 0x03)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio Layer II Bitrate', (codec.audio_bitmask >> 2) & 0x0F)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio Encoding Layer', (codec.audio_bitmask >> 6) & 0x01)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio Stereo Mode', (codec.audio_bitmask >> 8) & 0x03)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio Stereo Mode Extension', (codec.audio_bitmask >> 10) & 0x03)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio Emphasis', (codec.audio_bitmask >> 12) & 0x03)
            tv.v4l2.Videodev.updatecontrol(self, 'Audio CRC', (codec.audio_bitmask >> 14) & 0x01)
            tv.v4l2.Videodev.updatecontrol(self, 'Video B Frames', codec.bframes-1)
            tv.v4l2.Videodev.updatecontrol(self, 'Video Bitrate Mode', codec.bitrate_mode)
            tv.v4l2.Videodev.updatecontrol(self, 'Video Bitrate', codec.bitrate)
            tv.v4l2.Videodev.updatecontrol(self, 'Video Peak Bitrate', codec.bitrate_peak)
            tv.v4l2.Videodev.updatecontrol(self, 'Spatial Filter Mode', (codec.dnr_mode >> 0) & 0x01)
            tv.v4l2.Videodev.updatecontrol(self, 'Temporal Filter Mode', (codec.dnr_mode >> 1) & 0x01)
            tv.v4l2.Videodev.updatecontrol(self, 'Spatial Filter', codec.dnr_spatial)
            tv.v4l2.Videodev.updatecontrol(self, 'Temporal Filter', codec.dnr_temporal)
            tv.v4l2.Videodev.updatecontrol(self, 'Median Filter Type', codec.dnr_type)
            tv.v4l2.Videodev.updatecontrol(self, 'Video GOP Size', codec.framespergop)
            tv.v4l2.Videodev.updatecontrol(self, 'Video GOP Closure', codec.gop_closure)
            tv.v4l2.Videodev.updatecontrol(self, 'Video Pulldown', codec.pulldown)
            tv.v4l2.Videodev.updatecontrol(self, 'Stream Type', self.streamTypeIvtvToV4l2(codec.stream_type))
            return
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
                           codec.framerate,     #read only, ignored on write
                           codec.framespergop,  #read only, ignored on write
                           codec.gop_closure,
                           codec.pulldown,
                           codec.stream_type)
        r = fcntl.ioctl(self.device, i32(IVTV_IOC_S_CODEC), val)
        if DEBUG >= 3: print "setCodecInfo: val=%r, r=%r" % (val, r)


    def mspSetMatrix(self, input=None, output=None):
        if not input: input = 3
        if not output: output = 1

        val = struct.pack(MSP_MATRIX_ST, input, output)
        r = fcntl.ioctl(self.device, i32(MSP_SET_MATRIX), val)
        if DEBUG >= 3: print "mspSetMatrix: val=%r, r=%r" % (val, r)


    def getvbiembed(self):
        if self.version >= 0x800:
            return self.getcontrol('Stream VBI Format')
        try:
            r = fcntl.ioctl(self.device, i32(GETVBI_EMBED_NO), struct.pack(VBI_EMBED_ST,0))
            if DEBUG >= 3:
                print "getvbiembed: val=%r, r=%r, res=%r" % (struct.pack(VBI_EMBED_ST,0), r,
                    struct.unpack(VBI_EMBED_ST,r))
            return struct.unpack(VBI_EMBED_ST,r)[0]
        except IOError:
            print 'getvbiembed: failed'
            return 0


    def setvbiembed(self, value):
        if self.version >= 0x800:
            self.setcontrol('Stream VBI Format', value)
            return
        try:
            r = fcntl.ioctl(self.device, i32(SETVBI_EMBED_NO), struct.pack(VBI_EMBED_ST, value))
            if DEBUG >= 3: print "setvbiembed: val=%r, res=%r" % (struct.pack(VBI_EMBED_ST, value), r)
        except IOError:
            print 'setvbiembed: failed'


    def gopend(self, value):
        r = fcntl.ioctl(self.device, i32(GOP_END_NO), struct.pack(GOP_END_ST, value))
        if DEBUG: print "gopend: val=%r, res=%r" % (struct.pack(GOP_END_ST, value), r)


    def init_settings(self, opts=None):
        if not opts:
            opts = config.TV_IVTV_OPTIONS

        tv.v4l2.Videodev.init_settings(self)

        (width, height) = string.split(opts['resolution'], 'x')
        self.setfmt(int(width), int(height))

        if self.version >= 0x800:
            tv.v4l2.Videodev.getcontrols(self)

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
        # framerate is set by the std
        #codec.framerate     = opts['framerate']
        codec.framespergop  = opts['framespergop']
        codec.gop_closure   = opts['gop_closure']
        codec.pulldown      = opts['pulldown']
        codec.stream_type   = opts['stream_type']

        self.setCodecInfo(codec)


    def print_settings(self):
        tv.v4l2.Videodev.print_settings(self)

        codec = self.getCodecInfo()

        print 'CODEC::aspect: %s' % codec.aspect
        print 'CODEC::audio_bitmask: 0x%X' % codec.audio_bitmask
        print 'CODEC::bframes: %s' % codec.bframes
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


    def __str__(self):
        res =  'aspect=%d, ' % self.aspect
        res += 'audio_bitmask=0x%0X, ' % self.audio_bitmask
        res += 'bframes=%d, ' % self.bframes
        res += 'bitrate_mode=%d, ' % self.bitrate_mode
        res += 'bitrate=%d, ' % self.bitrate
        res += 'bitrate_peak=%d, ' % self.bitrate_peak
        res += 'dnr_mode=%d, ' % self.dnr_mode
        res += 'dnr_spatial=%d, ' % self.dnr_spatial
        res += 'dnr_temporal=%d, ' % self.dnr_temporal
        res += 'dnr_type=%d, ' % self.dnr_type
        res += 'framerate=%d, ' % self.framerate
        res += 'framespergop=%d, ' % self.framespergop
        res += 'gop_closure=%d, ' % self.gop_closure
        res += 'pulldown=%d, ' % self.pulldown
        res += 'stream_type=%d' % self.stream_type
        return res


if __name__ == '__main__':

    DEBUG = 0

    ivtv_dev = IVTV('/dev/video0')
    ivtv_dev.init_settings()
    #ivtv_dev.print_settings()

    #print 'driver="%s"' % ivtv_dev.driver
    #print 'version=%x' % ivtv_dev.version
    #print config.TV_IVTV_OPTIONS

    #print ivtv_dev.print_settings()
    ##embed = ivtv_dev.getvbiembed()
    ##print "current vbi embed=%s" % embed
    ##ivtv_dev.setvbiembed(1)
    ##print "set vbi embed=%s (%s)" % (ivtv_dev.getvbiembed(), 1)
    ##ivtv_dev.setvbiembed(embed)
    ##print "reset vbi embed=%s (%s)" % (ivtv_dev.getvbiembed(), embed)

    ##print ivtv_dev.getCodecInfo()
    #codec = IVTVCodec((2, 0x00e9, 3, 0, 8000000, 9600000, 0, 0, 8, 0, 0, 15, 1, 0, 10))
    #print 'codec:', codec
    #ivtv_dev.setCodecInfo(codec)
    #print ivtv_dev.getCodecInfo()

'''
To run this as standalone use the following before running python ivtv.py
pythonversion=$(python -V 2>&1 | cut -d" " -f2 | cut -d"." -f1-2)
export PYTHONPATH=/usr/lib/python${pythonversion}/site-packages/freevo
export FREEVO_SHARE=/usr/share/freevo
export FREEVO_CONFIG=/usr/share/freevo/freevo_config.py
export FREEVO_CONTRIB=/usr/share/freevo/contrib
export RUNAPP=""
python ivtv.py
'''
