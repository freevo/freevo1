# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Interface to the encoding server
# -----------------------------------------------------------------------
# $Id$
#
# Author: den_RDC
# some parts taken or inspired by Quickrip (by T. Chance, GPL,
# http://quickrip.sf.net)
# Todo:
# niceness & pausing queue
# different containers (Matroska)
#
# -----------------------------------------------------------------------
# Copyright (C) 2004 den_RDC (RVDM)
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
# with this program; if not, write to the Free Software Foundation
#
# -----------------------------------------------------------------------

"""
Interface to the encoding server, to re-encode video to a different format.
"""

#Import statements
from threading import Thread, Lock
from time import sleep
import sys, os, re #, ConfigParser, copy
from subprocess import Popen, PIPE
from pprint import pprint, pformat
from copy import copy
from string import split, join
from util.misc import uniquify_filename

import config
import kaa.metadata

from childapp import ChildApp2


#precompiled regular expression to obtain mencoder progress
re_progress = re.compile('(\d+)\%\) .*Trem:\s*(\d+\w+)\s+')

#some temporary hardcoded programs

mencoder = config.CONF.mencoder
mplayer = config.CONF.mplayer

#some data
__author__ = 'den_RDC (rdc@kokosnoot.com)'
__revision__ = '$Rev$'
__copyright__ = 'Copyright (C) 2004 den_RDC'
__license__ = 'GPL'


mappings = {
    'lists' : {
        'containers'  : [ 'avi', 'mp4', 'mpeg' ], # add mkv back later
        'videocodecs' : [ 'MPEG 4 (lavc)','MPEG 4 (lavc fast)','MPEG 2 (lavc)', 'XviD', 'H.264', 'copy' ],
        'audiocodecs' : [ 'MPEG 1 Layer 3 (mp3)', 'MPEG 1 Layer 2 (mp2)', 'AAC (iPod)', 'AC3', 'Vorbis',
            'WMAv1',' WMAv2', 'copy' ],
    },
    'vcodec' : {
        'MPEG 4 (lavc)' : [ 'lavc', '-lavcopts', 'vcodec=mpeg4:mbd=2:trell:v4mv:last_pred=2:dia=-1:vmax_b_frames=2:'+
            'vb_strategy=1:cmp=3:subcmp=3:precmp=0:vqcomp=0.6:vbitrate=%s:threads=%s%s%s'],
        'MPEG 4 (lavc fast)' : [ 'lavc', '-lavcopts', 'vcodec=mpeg4:vbitrate=%s:threads=%s%s%s' ],
        'MPEG 2 (lavc)' : [ 'lavc', '-lavcopts', 'vcodec=mpeg2video:vhq:vqmin=2:trell:vrc_buf_size=1835:'+
            'vrc_maxrate=9800:keyint=18:vstrict=0:vbitrate=%s:threads=%s%s%s'],
        'XviD'          : [ 'xvid', '-xvidencopts', 'chroma_opt:vhq=4:bvhq=1:bitrate=%s:threads=%s%s%s' ],
        #'H.264'         : [ 'x264', '-x264encopts', 'subq=5:8x8dct:frameref=2:bframes=3:b_pyramid:weight_b:'+
        #    'bitrate=%s:threads=%s%s%s' ],
        #'H.264'         : [ 'x264', '-x264encopts', 'subq=7:global_header:trellis=2:partitions=all:no-fast-pskip:'+
        #    'me=umh:deblock:direct_pred=auto:level_idc=30:frameref=6:no8x8dct:me_range=32:bframes=0:nob_pyramid:'+
        #    'nobrdo:cabac:bitrate=%s:threads=%s%s%s' ],
        'H.264'         : [ 'x264', '-x264encopts', 'subq=5:8x8dct:frameref=2:bframes=3:b_pyramid:weight_b:' +
            'bitrate=%s:threads=%s%s%s' ],
        'copy'          : [ 'copy' ],
    },
    'container' : {
        'mpeg' : [ 'mpeg', '-mpegopts', 'format=dvd:tsaf' ],
        'mp4' : [ 'lavf' , '-lavfopts', 'format=mp4', '-ffourcc', 'mp4v' ],
        'mkv' : [ 'lavf',  '-lavfopts', 'format=avi' ],
        'avi' : [ 'lavf' , '-lavfopts', 'format=avi' ],
    },
    'acodec' : {
        'MPEG 1 Layer 3 (mp3)' : ['lavc', '-lavcopts', 'acodec=libmp3lame:abitrate=%s:aglobal=1'],
        'AAC (iPod)'           : ['lavc', '-lavcopts', 'acodec=libfaac:abitrate=%s:aglobal=1'],
        'AC3'                  : ['lavc', '-lavcopts', 'acodec=ac3:abitrate=%s:aglobal=1'],
        'MPEG 1 Layer 2 (mp2)' : ['lavc', '-lavcopts', 'acodec=mp2:abitrate=%s:aglobal=1'],
        'Vorbis'               : ['lavc', '-lavcopts', 'acodec=vorbis:abitrate=%s:aglobal=1'],
        'WMAv1'                : ['lavc', '-lavcopts', 'acodec=wmav1:abitrate=%s:aglobal=1'],
        'WMAv2'                : ['lavc', '-lavcopts', 'acodec=wmav2:abitrate=%s:aglobal=1'],
        'copy'                 : ['copy'],
    },
    'filter' : {
        'Linear blend' : 'pp=lb',
        'Lavc deinterlacer' : 'lavcdeint',
        'On (stateless filter)' : 'ivtc=1',
        'Normal denoise' : 'denoise3d',
        'HQ denoise' : 'hqdn3d',
        'iPod' : 'scale=320:240'
    },
    'filtertype' : {
        'None' : ['None'],
        'Deinterlacing' : ['None', 'Linear blend', 'Lavc deinterlacer'],
        'Inverse Telecine' : ['None', 'On (stateless filter)'],
        'Denoise' : ['None', 'Normal denoise', 'HQ denoise'],
        'iPod' : ['iPod']
    },
}



class Enum(dict):
    """Enum
    from pytvgrab enum.py, see http://pytvgrab.sourceforge.net

    Enum(names, x=0)"""
    def __init__(self, names, x=0):
        """ Initialize an Enum """
        for i in range(x, x+len(names)):
            self.__dict__[names[i-x]] = i
            self[i] = names[i-x]
    # __init__()

status = Enum(['notset', 'apass', 'vpass1', 'vpassfinal', 'postmerge'])



class EncodingError(Exception):
    """
    An exception class for last.fm
    """
    def __init__(self, why):
        Exception.__init__(self)
        self.why = str(why)

    def __str__(self):
        return self.why



class EncodingOptions:
    """
    Encoding options
    """
    def getContainerList(self):
        """Return a list of possible containers"""
        return mappings['lists']['containers']


    def getVideoCodecList(self):
        """Return a list of possible video codecs"""
        return mappings['lists']['videocodecs']


    def getAudioCodecList(self):
        """Return a possible audio codec list"""
        return mappings['lists']['audiocodecs']


    def getVideoFiltersList(self):
        """Return a list of possible video filters"""
        return mappings['filtertype']



class EncodingJob:
    """
    Class for creation & configuration of EncodingJobs. This generates the mencoder commands

    @ivar _generateCL: function to generate the command line
    @ivar encodingopts: options for the different encoding steps
    @ivar source: source file to encode
    @ivar output: output file after encoding
    @ivar name: friendly name of the job
    @ivar idnr: job id number
    @ivar titlenum: titlenum number to re-encode
    @ivar rmsource: remove the source when done
    @type rmsource: boolean
    @ivar container: type of video container
    @ivar tgtsize: target size for video
    @ivar length: length of source video in seconds
    @ivar vcodec: video codec to use
    @ivar altprofile: user defined encoding profile
    @ivar vbrate: video bit rate
    @ivar multipass: number of encoding passes
    @ivar vfilters: list of video filters to apply
    @ivar crop: crop settings
    @ivar cropres: crop settings
    @ivar timeslice: start and end positions to encode
    @ivar timeslice_mencoder: mencoder options for start and end
    @ivar acodec: audio codec to use
    @ivar abrate: audio bit rate
    @ivar afilters: list of audio filters
    @ivar cls: codec job list
    @ivar percentage: mencoders current percentage
    @ivar trem: mencoders current time remaining
    @ivar status: current job status
    @ivar pid: job process id
    @ivar ana: is the source anamorphic?
    @ivar fps: frames per second of the source
    @ivar finishedanalyze: has the analysis finished?
    @ivar info: Meta data of the source
    @ivar resx: target video width
    @ivar resy: target video height
    @ivar threads: number of threads
    @ivar failed: has the job failed?
    """
    def __init__(self, source, output, friendlyname, idnr, titlenum=None, rmsource=False):
        """
        Initialize an instance of an EncodingJob
        @param source: input source name
        @param output: output file name
        @param friendlyname: name of the job
        @param idnr: job id number
        @param titlenum: titlenum number to re-encode
        @param rmsource: remove the source
        """
        _debug_('encodingcore.EncodingJob.__init__(%s, %s, %s, %s, %s, %s)' % \
            (source, output, friendlyname, idnr, titlenum, rmsource), 2)
        #currently only MEncoder can be used, but who knows what will happen in the future :)
        self._generateCL = self._GenerateCLMencoder
        self.encodingopts = EncodingOptions()
        self.source = source
        #note that we strip the extension from the self.output file name
        self.output = output
        self.temp_output = None #temporary output file for mencoder job
        self.name = friendlyname
        self.idnr = idnr
        self.titlenum = titlenum
        self.rmsource = rmsource

        self.container = 'avi'
        self.tgtsize = None
        self.length = None

        self.vcodec = None
        self.altprofile = None
        self.vbrate = None
        self.multipass = False
        self.vfilters = []
        self.crop = None
        self.cropres = None
        self.id_info = None

        # list of initial and end point of slice to encode
        self.timeslice = [ None , None ]
        # corresponding arguments for mencoder
        self.timeslice_mencoder = []

        self.acodec = mappings['lists']['audiocodecs'][0]
        self.abrate = 128
        self.afilters = {} # Not used ATM, might be used in the future

        self.cls = []

        self.percentage = 0
        self.trem = 0

        self.status = status.notset
        self.pid = 0

        self.ana = False
        self.fps = 0

        self.finishedanalyze = False
        self.info = {}

        self.resx = None
        self.resy = None

        self.threads = 1 # How many threads to use during encoding (multi core systems)
        self.failed = False
        if self.source:
            try:
                self.info = kaa.metadata.parse(self.source)
                if self.info:
                    self._analyze_source()
                else:
                    _debug_('Failed to analyse "%s" kaa.metadata.parse()'  % self.source, DERROR)
                    self.failed = True
                    self.finishedanalyze = True
            except Exception, e:
                _debug_('Failed to analyse "%s": %s' % (self.source, e), DERROR)
                self.failed = True
                self.finishedanalyze = True


    def setTimeslice(self, timeslice):
        "Set the encoding time-slice"
        self.timeslice = timeslice
        assert(type(timeslice) == type([]))
        assert(len(timeslice) == 2)
        self.timeslice_mencoder = []
        start = 0
        if timeslice[0]:
            self.timeslice_mencoder += ['-ss', str(timeslice[0])]
            start = timeslice[0]
        if timeslice[1]:
            self.timeslice_mencoder += ['-endpos', str(timeslice[1]-start)]
            if timeslice[1] < start:
                self.timeslice_mencoder = []
                self.timeslice = [ None , None ]
                return 'Invalid slice of times: end is before start ??'


    def setContainer(self, container):
        """Set a container to hold the audio & video streams"""
        #safety checks, should raise an exception
        if container not in self.encodingopts.getContainerList():
            return 'Unknown container format %r' % (container,)
        self.container = container


    def full_output_file_name(self):
        #note that we strip the extension from the self.output file name
        return '%s.%s' % (self.output, self.container)


    def setVideoCodec(self, vcodec, tgtsize, multipass=False, vbitrate=0, altprofile=None):
        """Set video codec and target filesize (in MB) or bit rate (in kbits/sec)"""
        _debug_('setVideoCodec(self, vcodec=%s, tgtsize=%s, multipass=%s, vbitrate=%s)' % \
            (vcodec, tgtsize, multipass, vbitrate))
        if vcodec not in self.encodingopts.getVideoCodecList():
            return 'Unknown video codec %r' % vcodec

        self.vcodec = vcodec
        if vbitrate:
            self.tgtsize = 0
        else:
            self.tgtsize = (int(tgtsize) * 1024) #file size is internally stored in kB
        self.multipass = multipass
        self.vbitrate = vbitrate
        self.altprofile = altprofile


    def setAudioCodec(self, acodec, abrate=128):
        """Set audio codec & bit rate"""
        if acodec not in self.encodingopts.getAudioCodecList():
            return 'Unknown audio codec %r' % acodec

        self.acodec = acodec
        self.abrate = abrate


    def setVideoFilters(self, videofilters):
        """Set video filters"""
        for vfilter, option in videofilters:
            if mappings['filter'].has_key(option):
                self.vfilters += [ mappings['filter'][option] ]


    def setVideoRes(self, videores):
        """Set video resolution"""
        if videores == 'Optimal':
            (self.resx, self.resy) = (0, 0)
        else:
            (self.resx, self.resy) = videores.split(':')


    def setNumThreads(self, numthreads):
        """Set the number of threads to use"""
        self.threads = numthreads


    def _CalcVideoBR(self):
        """Calculates the video bit rate"""

        _debug_('_CalcVideoBR: tgtsize=%s vbitrate=%s' % (self.tgtsize, self.vbitrate), 2)
        if self.vbitrate > 0:
            self.vbrate = self.vbitrate
        else:
            self.vbrate = int((((int(self.tgtsize)*8) / int(self.length)) - int(self.abrate)) / 0.98)
        #we got a very short file, very high bitrates are interpreted as bit/s instead of kbit/s, shitty qual
        if self.vbrate > 12000:
            self.vbrate = 6000
        _debug_('_CalcVideoBR: vbrate=%s' % (self.vbrate), 2)


    def _analyze_source(self):
        """Find out some basic information about the source

        ATM we will blindly assume it's a dvdrom device or a disk dvd image,
        if a title (titlenum) number is given.
        """
        _debug_('_analyze_source(self)', 2)

        if self.titlenum:
            #check some things, like length
            _debug_('source=%r" titlenum=%s' % (self.source, self.titlenum))
            dvddata = self.info
            dvdtitle = dvddata.tracks[self.titlenum - 1]
            self.length = dvdtitle['length']
            _debug_('Video length is %s' % self.length)
        else:
            data = self.info
            _debug_('source=%r' % (self.source))
            if config.DEBUG >= 2:
                for f in dir(data):
                    _debug_('%s: %s' % (f, eval('data["%s"]' % f)), 2)
            if data.has_key('length') and data['length'] is not None:
                self.length = data['length']
                _debug_('Video length is %s' % self.length)
            else:
                self.length = 600
                _debug_('Video length not found, using %s' % (self.length))


    def _identify(self):
        """
        Identify the media file

        @returns: a dictionary of items
        """
        arguments = [ '-vo', 'null', '-ao', 'null', '-frames', '0', '-identify' ]
        if self.titlenum:
            arguments += [ '-dvd-device', self.source, 'dvd://%s' % self.titlenum ]
        else:
            arguments += [ self.source ]

        self._run(mplayer, arguments, self._identify_parse, None, 0, None)


    def _identify_parse(self, lines, data):
        """
        Parses Mplayer output to obtain ideal cropping parameters, and do
        PAL/NTSC detection from QuickRip, heavily adapted, new algo.

        TODO: give this another name, it does more then crop detection only
        """
        id_pattern = re.compile('^(ID_.*)=(.*)')
        id_info = {}

        for line in [l.rstrip() for l in lines]:
            id_match = id_pattern.match(line)
            if id_match:
                id_info[id_match.groups()[0]] = id_match.groups()[1]

        if config.DEBUG_CONSOLE:
            print 'id_info: '+ pformat(id_info)

        self.id_info = id_info


    def _videothumb(self):
        """
        Generate a video thumbnail of the video
        """
        if self.length is None:
            self._identify()
            self._wait()
            if self.id_info.has_key('ID_LENGTH'):
                self.length = float(self.id_info['ID_LENGTH'])
            else:
                self.length = 0

        position = str(int(self.length / 2.0))
        arguments = [ '-vo', 'png:z=1', '-ao', 'null', '-frames', '8', '-ss', position, '-zoom' ]
        if self.titlenum:
            arguments += [ '-dvd-device', self.source, 'dvd://%s' % self.titlenum ]
        else:
            arguments += [ self.source ]

        # chdir to tmp so we have write access
        os.chdir(config.FREEVO_TEMPDIR)
        self._run(mplayer, arguments, self._videothumb_parse, None, 0, 'data.png')


    def _videothumb_parse(self, lines, data):
        from util import vfs
        for line in lines:
            if line:
                _debug_(line)
        import glob
        import shutil
        captures = glob.glob('000000??.png')
        if captures:
            _debug_('%r' % (captures,))
            capture = captures[-1]
            try:
                vfsdir = os.path.dirname(self.output)
                if not os.path.isdir(vfsdir):
                    os.makedirs(vfsdir)
                _debug_('copying %r->%r' % (capture, self.output))
                shutil.copy(capture, self.output)
            except OSError, why:
                _debug_('%s' % why, DINFO)
                try:
                    shutil.copy(capture, vfs.getoverlay(self.output))
                    _debug_('copied %r to %r' % (capture, vfs.getoverlay(self.output)))
                except Exception, why:
                    _debug_('unable to write file %r: %s' % (self.output, why), DWARNING)
        else:
            _debug_('error creating capture for "%s"' % self.source, DWARNING)

        for capture in captures:
            try:
                os.remove(capture)
            except:
                _debug_('error removing temporary captures for "%s"' % Unicode(filename), 1)



    def _cropdetect(self):
        """
        Detect cropping, contains pieces of QuickRip

        Function is always called because cropping is a good thing, and we can
        pass our ideal values back to the client which can verify them visually
        if needed.
        """
        self.crop_results = {}
        if self.length is None:
            self._identify()
            self._wait()
            if self.id_info.has_key('ID_LENGTH'):
                self.length = float(self.id_info['ID_LENGTH'])
            else:
                self.length = 0

        start = 0
        if self.timeslice[0]:
            start = self.timeslice[0]
        if self.timeslice[1]:
            sstep = int((self.timeslice[1] - start) / 27)
        elif hasattr(self, 'length') and self.length:
            sstep = int((self.length - start) / 27)
        else:
            sstep = 60

        arguments = self.timeslice_mencoder + [ '-vf', 'cropdetect=30', '-nosound', '-vo', 'null', '-fps', '540' ]
        if sstep > 0:
            arguments += [ '-demuxer', 'lavf', '-sstep', str(sstep) ]

        mid_length = int(self.length) / 2
        if self.length > 90:
            positions = [mid_length - 35, mid_length, mid_length + 35]
        else:
            positions = [mid_length]
        for pos in positions:
            arguments = self.timeslice_mencoder + [ '-ss', '%s' % pos, '-identify', '-frames', '20', '-vo', 'md5sum',
                '-ao', 'null', '-nocache', '-speed', '100', '-noframedrop', '-vf', 'cropdetect=20:16' ]
            if self.titlenum:
                arguments += [ '-dvd-device', self.source, 'dvd://%s' % self.titlenum ]
            else:
                arguments += [ self.source ]

            self._run(mplayer, arguments, self._cropdetect_parse, None, 0, None)
            self._wait()


    def _cropdetect_parse(self, lines, data): #seek to remove data
        """
        Parses Mplayer output to obtain ideal cropping parameters, and do
        PAL/NTSC detection from QuickRip, heavily adapted, new algo.
        """
        #_debug_('_cropdetect_parse(self, lines=%r, data=%r)' % (lines, data))

        re_crop = re.compile('.*-vf crop=(\d*:\d*:\d*:\d*).*')
        re_ntscprog = re.compile('24fps progressive NTSC content detected')
        re_fps_23 = re.compile('23.876 fps')
        re_fps_25 = re.compile('25.000 fps')
        re_fps_29 = re.compile('29.970 fps')
        re_fps_50 = re.compile('50.000 fps')
        re_fps_59 = re.compile('59.940 fps')

        re_ana1 = re.compile('ASPECT', re.IGNORECASE)
        re_ana2 = re.compile('1.33')
        re_ana3 = re.compile('0.00')

        foundrate = False

        try:
            if not self.info.video[0].has_key('width') or not self.info.video[0].has_key('height'):
                self.finishedanalyze = True
                return
            crop = str(self.info.video[0].width)+':'+str(self.info.video[0].height)+':0:0'
            self.crop_results[crop] = 1
        except Exception, why:
            pass
        for line in [l.rstrip() for l in lines]:
            if re_crop.search(line):
                crop = re_crop.search(line).group(1)
                if crop in self.crop_results:
                    self.crop_results[crop] += 1
                else:
                    self.crop_results[crop] = 1

            #try to see if this is a PAL DVD, a NTSC Progressive DVD, or a NTSC DVD
            if not foundrate: # and self.info.mime == 'video/dvd':
                if re_fps_23.search(line):
                    self.fps = 23.976
                    foundrate = True
                if re_fps_25.search(line):
                    self.fps = 25.000
                    foundrate = True
                if re_fps_29.search(line):
                    self.fps = 29.970
                    foundrate = True
                if re_fps_50.search(line):
                    self.fps = 50.000
                    foundrate = True
                if re_fps_59.search(line):
                    self.fps = 59.940
                    foundrate = True
                else:
                    if re_ntscprog.search(line):
                        self.fps = 24.000
                        foundrate = True

            if re_ana1.search(line):
                if re_ana2.search(line):
                    self.ana = False
                elif re_ana3.search(line):
                    try:
                        # what a odd line of code
                        if not (self.info.video[0].has_key('width')/self.info.video[0].has_key('height')) > 1.3334:
                            self.ana = False
                    except:
                        pass
                else:
                    self.ana = True

        if hasattr(self.info, 'aspect'):
            if int(self.info.aspect*100) == 1.33:
                self.ana = False
            else:
                self.ana = True

        if not foundrate: # unknown frame rate setting to 29.970
            self.fps = 29.970

        _debug_('All collected crop results: %s' % self.crop_results)

        #if we didn't find cropping options (seems to happen sometimes on VERY short DVD titles)
        if self.crop_results == {}:
            #end analysing
            self.finishedanalyze = True
            return

        #some home-grown sleazy algorithm to pick the best crop options
        hcounter = 0
        possible_crop = []
        for crop, counter in self.crop_results.items():
            if counter == hcounter:
                possible_crop += [crop]
            if counter > hcounter:
                hcounter = counter
                possible_crop = [crop]

        self.crop = possible_crop[0]

        if len(possible_crop) > 1:
            for crop in possible_crop:
                if crop < self.crop:
                    self.crop = crop

        #make the final crop outputs a resolution which is a multiple of 16, v and h ....
        crop = split(self.crop, ':')
        adjustedcrop = []
        for res in crop[0:2]:
            if res != 'None':
                over = int(res) % 16
                adjustedcrop.append(str(int(res) - over))
        adjustedcrop += crop[2:]
        #save cropped resolution for later
        self.cropres = ( int(adjustedcrop[0]), int(adjustedcrop[1]) )

        self.crop = join(adjustedcrop, ':')

        _debug_('Selected crop setting: %s' % self.crop)

        #end analysing
        self.finishedanalyze = True


    def _GenerateCLMencoder(self):
        """Generate the command line(s) to be executed, using Mencoder for encoding"""
        #calculate the video bit rate
        self._CalcVideoBR()

        #for single passes
        if not self.multipass:
            videopass = []
            videopass += self._GCLMVideopass(0)
            videopass += self._GCLMSource()

            self.cls = [ videopass ]

        else:
            videopass1 = []
            videopass2 = []

            videopass1 += self._GCLMVideopass(1)
            videopass1 += self._GCLMSource()

            videopass2 += self._GCLMVideopass(2)
            videopass2 += self._GCLMSource()

            self.cls = [ videopass1, videopass2 ]


    def _GCLMSource(self):
        """Returns source part of mencoder"""
        if self.titlenum:
            if hasattr(config, 'DVD_LANG_PREF') and config.DVD_LANG_PREF:
                audio = ['-alang', config.DVD_LANG_PREF]
            else:
                audio = []
            return audio+[ '-dvd-device', self.source, 'dvd://%s' % self.titlenum]
        else:
            return [ self.source ]


    def _GCLMVideopass(self, passnr):
        """Returns video pass specific part of mencoder cl"""
        vf = copy(self.vfilters)
        vfilter = ''
        vpass = ''
        yscaled = None
        #deinterlacer test vf += ['pp=lb']
        #set appropriate videopass, codec independant (lavc is vpass, xvid is pass)
        if passnr > 0:
            if self.vcodec == 'XviD' or self.vcodec == 'H.264':
                passname = ':pass=%s'
            else:
                passname = ':vpass=%s'

            vpass = passname % passnr

            if self.vcodec == 'MPEG 4 (lavc)' and passnr == 1:
                vpass = vpass + ':turbo'

        #generate videofilters first, NI completely yet
        if self.crop != None:
            vf += [ 'crop=%s' % self.crop ]

        #in case of xvid and anamorphic dvd, add scaling to compensate AR..
        #if we didn't find cropping we have no res, so no tricks
        if self.vcodec == 'XviD' and self.crop:
            if self.ana:
                #calculate a decent resized picture size, res must still be a multiple of 16
                yscaled = (self.cropres[1] * 0.703125)
                rounded = yscaled % 16
                yscaled -= rounded
                if rounded > 7.5:
                    yscaled += 16
                _debug_('Rescaled, corrected for AR res is %sx%s' % (self.cropres[0], int(yscaled)))
            else: # no scaling, we have a 4/3
                yscaled = self.cropres[1]
            #new, calculate ideal res based on BPP
            idealres = self._OptimalRes(self.cropres[0], int(yscaled))
            _debug_('Rescaled, rounded yres is %sx%s' % (idealres[0], idealres[1]))
            (self.resx, self.resy) = (idealres[0], idealres[1])
        # Check to see if generating a dvd complient mpeg
        elif self.vcodec == 'MPEG 2 (lavc)' and self.resx == '720':
            if self.fps == 25.000 or self.fps == 50:
                self.resx = 720
                self.resy = 576
            else:
                self.resx = 720
                self.resy = 480

        if self.resx == 0 and self.crop:
            (self.resx, self.resy) = self._OptimalRes(self.cropres[0], self.cropres[1])
        elif self.resx == 0:
            (self.resx, self.resy) = self._OptimalRes(self.info.video[0].width, self.info.video[0].height )

        if self.resx != None:
            vf += [ 'scale=%s:-3'  % self.resx ]
            vf += [ 'expand=%s:%s'  % (self.resx, self.resy) ]


        _debug_('Video filters: %s' % vf)

        #join vf options
        if len(vf) > 1:
            for vfopt in vf[0:-1]:
                vfilter += vfopt + ','
        if len(vf) >= 1:
            vfilter += vf[-1]

        output = self.output

        aspect = ''
        if self.vcodec == 'MPEG 2 (lavc)' and self.cropres[0] != '720':
            if self.ana:
                aspect = ':aspect=16/9'
            else:
                aspect = ':aspect=4/3'
        elif self.vcodec != 'H.264':
            aspect =  ':autoaspect'

        # set video encoder options
        if self.altprofile is None:
            args = [ '-ovc', mappings['vcodec'][self.vcodec][0] ,]
            if self.vcodec != 'copy':
                args += [ mappings['vcodec'][self.vcodec][1],
                        mappings['vcodec'][self.vcodec][2] % (self.vbrate, self.threads, vpass, aspect ) ]
        else:  # Allow encoder options from client
            aprofile = '%s:vbitrate=%s:threads=%s%s%s' % (self.altprofile, self.vbrate, self.threads, vpass, aspect)
            args = ['-ovc', mappings['vcodec'][self.vcodec][0],mappings['vcodec'][self.vcodec][1], aprofile ]


        # set audio encoder options
        args += ['-oac' , mappings['acodec'][self.acodec][0] ]
        if self.acodec != 'copy':
            args += [ mappings['acodec'][self.acodec][1],
                      mappings['acodec'][self.acodec][2] % self.abrate ]
        self.temp_output = uniquify_filename(output + '~incomplete~')
        args += [ '-o', self.temp_output ]

        # don't pass video filter in we have none
        if len(vfilter) != 0:
            args += ['-vf', vfilter ]

        if passnr > 0:  # Remove when/if mencoder uses the same file name for all codecs
            args += [ '-passlogfile', 'x264_2pass.log' ]

        #if we have a progressive ntsc file, lock the output fps (do this with ivtc too)
        if 'ivtc=1' in vf or self.fps == 23.976:
            args = ['-ofps', '24000/1001'].append(args) # mencoder don't like 23.976

        if hasattr(config, 'DVD_LANG_PREF') and config.DVD_LANG_PREF:
            args += ['-alang', config.DVD_LANG_PREF ]

        if self.vcodec == 'MPEG 2 (lavc)':
            if self.fps == 25.000 or self.fps == 50.000:
                args += ['-ofps', '25.000']
            else:
                args += ['-ofps', '30000/1001'] # mencoder don't like 29.97

        # Set output file container
        args += ['-of'] + mappings['container'][self.container]

        #if we scale, use the bilinear algorithm
        if yscaled:
            args += ['-sws', '1']

        args = self.timeslice_mencoder + args

        return args


    def _CalcBPP(self, x, y):
        """Perform a BPP (Bits per Pixel calculation)"""
        bpp = (self.vbrate * 1000) / (x * y * self.fps)
        _debug_('_CalcBPP() = %s, fps=%s' % (bpp, self.fps))
        return bpp


    def _OptimalRes(self, x, y):
        """Using BPP calculations, try to find out the ideal resolution for this movie"""
        nonoptimal = True
        optx = x

        #scale down until or ideal size is met
        while nonoptimal:
            #scale down x with 16 pix, calc y with the same AR as original x & y
            optx -= 16
            opty = (optx * y)/x
            #round opty to a multiple of 16
            rounded = opty % 16
            opty -= rounded
            if rounded > 7.5:
                opty += 16
            if self._CalcBPP( optx, opty ) >= 0.22:
                nonoptimal = False

        return ( int(optx), int (opty) )


    def _MencoderParse(self, line, data):
        """Parses mencoder stdout to get progress and them
        from Quickrip, adapted
        seek to remove data
        """
        #(passtype, title) = data
        # re_progress is pre-compiled at the beginning of this file, to speed up
        s = re_progress.search(line)
        if s:
            self.percentage = s.group(1)
            self.trem = s.group(2)
            #self.ui_updateProgress(perc, trem, passtype)


    def _run(self, program, arguments, finalfunc=None, updatefunc=None, flushbuffer=0, data=None, lock=None):
        """
        Runs a program; supply program name (string) and arguments (list)
        """
        command = [program]
        command += arguments

        self.thread = CommandThread(self, command, updatefunc, finalfunc, flushbuffer, data, lock)
        self.thread.start()


    def _wait(self, timeout=10):
        """
        Wait for the thread to finish in time-out seconds.
        If the thread has not finished the kill it
        """
        self.thread.join(timeout)
        if self.thread.isAlive():
            self.thread.kill_process()
            self.thread.join(timeout)
            if self.thread.isAlive():
                raise EncodingError('thread still running')



class CommandThread2(ChildApp2):
    def __init__():
        pass


    def stdout_cb(self, line):
        """
        parse the stdout of the mplayer process
        """
        pass


    def stderr_cb(self, line):
        """
        parse the stderr of the mplayer process
        """
        pass



class CommandThread(Thread):
    """
    Handle threading of external commands

    command executing class - Taken from Quickrip & adapted.
    """
    def __init__(self, parent, command, updatefunc, finalfunc, flushbuffer, data, lock):
        _debug_('CommandThread.__init__(parent=%r, command=%r, updatefunc=%r, finalfunc=%r, flushbuffer=%r, data=%r, lock=%r)' % (parent, command, updatefunc, finalfunc, flushbuffer, data, lock))
        Thread.__init__(self)
        self.parent = parent
        self.command = command
        self.updateFunc = updatefunc
        self.finalFunc = finalfunc
        self.flushbuffer = flushbuffer
        self.data = data
        self.lock = lock
        self.returncode = None


    def run(self):
        _debug_(' '.join(self.command))
        self.process = Popen(['nice']+self.command, stdout=PIPE, stderr=PIPE, close_fds=True, universal_newlines=True)
        _debug_('%s thread running with PID %s' % (self.command[0], self.process.pid))

        output = self.process.stdout
        totallines = []
        while self.process.poll() is None:
            line = output.readline().strip()
            _debug_('line=%r' % (line,), 2)
            totallines.append(line)
            if self.updateFunc is not None:
                self.updateFunc(line, self.data)
        self.returncode = self.process.returncode

        _debug_('%s thread finished with %s, %s lines' % (self.command[0], self.process.returncode, len(totallines)))

        if self.finalFunc is not None:
            self.finalFunc(totallines, self.data)
        self.process.stdout.close()
        self.process.stderr.close()
        self.process = None


    def kill_process(self):
        """
        Kills current process
        """
        try:
            os.kill(self.process.pid, 9)
            os.waitpid(self.process.pid, os.WNOHANG)
        except:
            pass



class EncodingQueue:
    """Class for generating an encoding queue"""
    def __init__(self):
        #we keep a list and a dict because a dict doesn't store an order
        self.qlist = []
        self.qdict = {}
        self.running = False

        #remove old files
        self._removeTmp()


    def addEncodingJob(self, encjob):
        """Adds an encodingjob to the queue"""
        self.qlist += [encjob]
        self.qdict[encjob.idnr] = encjob


    def getProgress(self):
        """Gets progress on the current job"""
        if hasattr(self, 'currentjob'):
            return (self.currentjob.name, int(self.currentjob.status), int(self.currentjob.percentage),
                self.currentjob.trem)
        return 'No job currently running'


    def startQueue(self):
        """Start the queue"""
        if not self.running:
            self.running = True
            _debug_('queue started', DINFO)
            self._runQueue()


    def listJobs(self):
        """Returns a list of queue'ed jobs"""
        if self.qdict == {}:
            return []
        else:
            jlist = []
            for idnr, job in self.qdict.items():
                jlist += [ (idnr, job.name, job.status) ]
            return jlist


    def _removeTmp(self):
        """Removes possible temporary files created during encoding"""
        tmpfiles = ['frameno.avi', 'divx2pass.log', 'xvid-twopass.stats', 'x264_2pass.log' ]

        for tmpfile in tmpfiles:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)


    def _runQueue(self, line='', data=''):
        """
        Executes the jobs in the queue; when running each job, registers itself
        as a finalfunc callback for the new thread for the job run is completed.
        """
        if self.qlist == []:
            #empty queue, do nothing
            self.running = False
            if hasattr(self, 'currentjob'):
                del self.currentjob
            _debug_('queue empty, stopping processing...', DINFO)
            return

        #get the first queued object
        self.currentjob = self.qlist[0]
        if config.DEBUG_CONSOLE:
            #print 'self.currentjob:',; pprint(self.currentjob.__dict__)
            #print 'self.currentjob.thread:',; pprint(self.currentjob.thread.__dict__)
            print 'self.currentjob.idnr: ' + repr(self.currentjob.idnr)
            print 'self.currentjob.status: ' + repr(self.currentjob.status)
            if hasattr(self.currentjob, 'thread'):
                print 'self.currentjob.thread.returncode: ' + repr(self.currentjob.thread.returncode)

        _debug_('PID %s' % self.currentjob.pid)

        output = self.currentjob.full_output_file_name()
        # check eventually that there is no file by the same name
        unique_output = uniquify_filename(output)

        if hasattr(self.currentjob,'thread'):
            if self.currentjob.thread.returncode:
                _debug_('Failed job:'+ ' '.join(self.currentjob.thread.command), DWARNING)
                #we are done with this job, remove it
                del self.qlist[0]
                del self.qdict[self.currentjob.idnr]
                #currently, keep running  until the queue is empty
                self._runQueue()
                return

        if self.currentjob.status == status.vpassfinal:
            _debug_('Job %s finished' % self.currentjob.idnr, DINFO)
            if self.currentjob.rmsource:
                _debug_('Removing source: %s' % self.currentjob.source)
                try:
                    os.remove(self.currentjob.source)
                except OSError :
                    _debug_('Cannot remove file '+self.currentjob.source, DWARNING)
            #
            try:
                os.rename(self.currentjob.temp_output, unique_output)
            except OSError :
                _debug_('Cannot rename file to remove ~incomplete~ suffix '+self.currentjob.temp_output, DWARNING)

            #we are done with this job, remove it
            del self.qlist[0]
            del self.qdict[self.currentjob.idnr]
            #currently, keep running  until the queue is empty
            self._runQueue()
            return

        if self.currentjob.status == status.vpass1:
            #start final video encoding pass
            self.currentjob.cls.pop(0)
            self.currentjob.status = status.vpassfinal
            #start video encoding
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue, self.currentjob._MencoderParse,
                1, None)

        if self.currentjob.status == status.apass:
            #in case audio encoding started before auto-crop detection returned, we are gonna
            #rebuild the clis... audio encoding doesn't need cropping
            self.currentjob._generateCL()
            #remove audioencoding cli
            self.currentjob.cls.pop(0)
            #start video encoding
            if not self.currentjob.multipass:
                self.currentjob.status = status.vpassfinal
            else:
                self.currentjob.status = status.vpass1
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue, self.currentjob._MencoderParse,
                1, None)

        if self.currentjob.status == status.notset:
            #generate cli's
            self.currentjob._generateCL()
            _debug_('CLIs: %s' % self.currentjob.cls)

            #clean out temporary files
            self._removeTmp()

            if not self.currentjob.multipass:
                self.currentjob.status = status.vpassfinal
            else:
                self.currentjob.status = status.vpass1
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue, self.currentjob._MencoderParse,
                1, None)

        _debug_('Started job %s, %s on PID %s' % (self.currentjob.idnr, \
            status[self.currentjob.status], self.currentjob.pid), DINFO)



if __name__ == '__main__':
    command = None
    source = '/freevo/video/dvd/BRUCE_ALMIGHTY/'
    titlenum = 0
    if len(sys.argv) >= 2:
        command = sys.argv[1]
        if len(sys.argv) >= 3:
            source = sys.argv[2]
            if len(sys.argv) >= 4:
                title = sys.argv[3]

    encjob = EncodingJob(None, 'test.avi', 'lala', 456789)
    encjob.source = source
    encjob.titlenum = titlenum
    if command == '--identify':
        encjob._identify()
        encjob._wait()
        print encjob.id_info
    elif command == '--videothumb':
        encjob._videothumb()
        encjob._wait()
    elif command == '--cropdetect':
        encjob.info = kaa.metadata.parse(encjob.source)
        encjob._cropdetect()
        encjob._wait()
        print encjob.crop
    elif command == '--analyze':
        encjob.info = kaa.metadata.parse(encjob.source)
        encjob._analyze_source()
        pprint(encjob.__dict__)
    else:
        encjob.setVideoCodec('MPEG 4 (lavc)', '700', False, 0)
        encjob.setAudioCodec('MPEG 1 Layer 3 (mp3)', '160')
        encjob.setVideoFilters({'Deinterlacing': 'Linear blend'})
        encjob._CalcVideoBR()
        print encjob.vbrate
        #encjob._generateCL()
        #cl = encjob.cls
        #print cl
        #print conc(cl[0])
        #print conc(cl[1])

        queue = encodingqueue()
        queue.addEncodingJob(encjob)
        queue.startqueue()
