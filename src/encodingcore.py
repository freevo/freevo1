# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# encodingcore.py, part of EncodingServer - for use with Freevo
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

#Import statements
import threading
from time import sleep
import sys, os, re, popen2 #, ConfigParser, copy
import config
import kaa.metadata
from copy import copy
from string import split, join

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
        'videocodecs' : [ 'MPEG 4 (lavc)','MPEG 2 (lavc)', 'XviD', 'H.264' ],
        'audiocodecs' : [ 'MPEG 1 Layer 3 (mp3)', 'MPEG 1 Layer 2 (mp2)', 'AAC (iPod)', 'AC3', 'Vorbis', 'WMAv1',' WMAv2', 'copy' ]
    },
    'vcodec' : {
        'MPEG 4 (lavc)' : [ 'lavc', '-lavcopts', 'vcodec=mpeg4:mbd=2:trell:v4mv:last_pred=2:dia=-1:vmax_b_frames=2:vb_strategy=1:cmp=3:subcmp=3:precmp=0:vqcomp=0.6:vbitrate=%s:threads=%s%s%s'],
        'MPEG 2 (lavc)' : [ 'lavc', '-lavcopts', 'vcodec=mpeg2video:vhq:vqmin=2:trell:vrc_buf_size=1835:vrc_maxrate=9800:keyint=18:vstrict=0:vbitrate=%s:threads=%s%s%s'],
        'XviD'          : [ 'xvid', '-xvidencopts', 'chroma_opt:vhq=4:bvhq=1:bitrate=%s:threads=%s%s%s'],
        'H.264'         : [ 'x264', '-x264encopts', 'subq=5:8x8dct:frameref=2:bframes=3:b_pyramid:weight_b:bitrate=%s:threads=%s%s%s']
    },
    'container' : {
        'mpeg' : [ 'mpeg', '-mpegopts', 'format=dvd:tsaf'],
        'mp4' : [ 'lavf' , '-lavfopts', 'format=mp4', '-ffourcc', 'mp4v'    ],
        'mkv' : [ 'lavf',  '-lavfopts', 'format=avi'],
        'avi' : [ 'lavf' , '-lavfopts', 'format=avi']
    },
    'acodec' : {
        'MPEG 1 Layer 3 (mp3)' : ['lavc', '-lavcopts', 'acodec=libmp3lame:abitrate=%s:aglobal=1'],
        'AAC (iPod)'           : ['lavc', '-lavcopts', 'acodec=libfaac:abitrate=%s:aic=2:aglobal=1'],
        'AC3'                  : ['lavc', '-lavcopts', 'acodec=ac3:abitrate=%s:aglobal=1'],
        'MPEG 1 Layer 2 (mp2)' : ['lavc', '-lavcopts', 'acodec=mp2:abitrate=%s:aglobal=1'],
        'Vorbis'               : ['lavc', '-lavcopts', 'acodec=vorbis:abitrate=%s:aglobal=1'],
        'WMAv1'                : ['lavc', '-lavcopts', 'acodec=wmav1:abitrate=%s:aglobal=1'],
        'WMAv2'                : ['lavc', '-lavcopts', 'acodec=wmav2:abitrate=%s:aglobal=1'],
        'copy'                 : ['copy']
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
        for i in range(x, x+len(names)):
            self.__dict__[names[i-x]]=i
            self[i]=names[i-x]
    # __init__()

status = Enum(['notset', 'apass', 'vpass1', 'vpassfinal', 'postmerge'])



class EncodingOptions:
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
    """Class for creation & configuration of EncodingJobs. This generates the mencoder commands"""
    def __init__(self, source, output, friendlyname, idnr, chapter=None):
        """Initialize class instance"""
        _debug_('encodingcore.EncodingJob.__init__(%s, %s, %s, %s, %s)' % \
            (source, output, friendlyname, idnr, chapter), 2)
        #currently only MEncoder can be used, but who knows what will happen in the future :)
        self._generateCL = self._GenerateCLMencoder
        self.encodingopts = EncodingOptions()
        self.source = source
        self.output = output
        self.name = friendlyname
        self.idnr = idnr
        self.chapter = chapter

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

        # list of initial and end point of slice to encode
        self.timeslice = [ None , None ]
        # corresponding arguments for mencoder
        self.timeslice_mencoder = []

        self.acodec = mappings['lists']['audiocodecs'][0]
        self.abrate = 128
        self.afilters = {} # Not used atm, might be used in the future

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
        self.failed=False
        if self.source:
            try:
                self.info = kaa.metadata.parse(self.source)
                if self.info:
                    self._AnalyzeSource()
                else:
                    print 'Failed to analyse "%s" kaa.metadata.parse()'  % self.source
                    self.failed=True
                    self.finishedanalyze = True
            except Exception, e:
                print 'Failed to analyse "%s": %s' % (self.source, e)
                self.failed=True
                self.finishedanalyze = True


    def setTimeslice(self, timeslice):
        "Set the encoding timeslice"
        self.timeslice = timeslice
        assert(type(timeslice) == type([]))
        assert(len(timeslice) == 2)
        self.timeslice_mencoder = []
        start=0
        if timeslice[0]:
            self.timeslice_mencoder += [ '-ss', str(timeslice[0])]
            start = timeslice[0]
        if timeslice[1]:
            self.timeslice_mencoder += ['-endpos', str(timeslice[1]-start)]
            if timeslice[1] < start:
                self.timeslice_mencoder = []
                self.timeslice = [ None , None ]
                return 'Invalid slice of times: end is before start ??'


    def setContainer(self, container):
        """Set a container to hold the audio & video streams"""
        #safety checks
        if container not in self.encodingopts.getContainerList():
            return 'Unknown container format'

        self.container = container
        if hasattr(config, 'ENCODINGSERVER_SAVE_DIR') and config.ENCODINGSERVER_SAVE_DIR:
            if not os.path.exists(config.ENCODINGSERVER_SAVE_DIR):
                os.makedirs(self.ENCODINGSERVER_SAVE_DIR, stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))
            self.output = os.path.basename(self.output)
            self.output = ('%s/%s.%s' % (config.ENCODINGSERVER_SAVE_DIR, self.output, self.container))
        else:
            self.output = ('%s.%s' % (self.output, self.container))


    def setVideoCodec(self, vcodec, tgtsize, multipass=False, vbitrate=0, altprofile=None):
        """Set video codec and target filesize (in MB) or bit rate (in kbits/sec)"""
        _debug_('setVideoCodec(self, vcodec=%s, tgtsize=%s, multipass=%s, vbitrate=%s)' % \
            (vcodec, tgtsize, multipass, vbitrate))
        #safety checks first
        if vcodec not in self.encodingopts.getVideoCodecList():
            return 'Unknown video codec'

        self.vcodec = vcodec
        if vbitrate:
            self.tgtsize = 0
        else:
            self.tgtsize = (int(tgtsize) * 1024) #filesize is internally stored in kB
        self.multipass = multipass
        self.vbitrate = vbitrate
        self.altprofile = altprofile


    def setAudioCodec(self, acodec, abrate=128):
        """Set audio codec & bitrate"""
        #safety first
        if acodec not in self.encodingopts.getAudioCodecList():
            return 'Unknown audio codec'

        self.acodec = acodec
        self.abrate = abrate


    def setVideoFilters(self, videofilters):
        """Set video filters"""
        for vfilter, option in videofilters:
            if mappings['filter'].has_key(option):
                self.vfilters += [ mappings['filter'][option]]


    def setVideoRes(self, videores):
        if videores == 'Optimal':
            (self.resx, self.resy) = (0, 0)
        else:
            (self.resx, self.resy) = videores.split(':')


    def setNumThreads(self, numthreads):
        self.threads = numthreads


    def _CalcVideoBR(self):
        """Calculates the video bitrate"""

        _debug_('_CalcVideoBR: tgtsize=%s vbitrate=%s' % (self.tgtsize, self.vbitrate), 2)
        if self.vbitrate > 0:
            self.vbrate = self.vbitrate
        else:
            self.vbrate = int((((int(self.tgtsize)*8) / int(self.length)) - int(self.abrate)) / 0.98)
        #we got a very short file, very high bitrates are interpreted as bit/s instead of kbit/s, shitty qual
        if self.vbrate > 12000:
            self.vbrate = 6000
        _debug_('_CalcVideoBR: vbrate=%s' % (self.vbrate), 2)


    def _AnalyzeSource(self):
        """Find out some basic information about the source

        ATM we will blindly assume it's a dvdrom device or a disk dvd image,
        if a title (chapter) number is given.
        """
        _debug_('_AnalyzeSource(self)', 2)

        if self.chapter:
            #check some things, like length
            _debug_('source=\"%s\" chapter=%s' % (self.source, self.chapter))
            dvddata = self.info
            dvdtitle = dvddata.tracks[self.chapter - 1]
            self.length = dvdtitle['length']
            _debug_('Video length is %s' % self.length)
        else:
            data = self.info
            _debug_('source=\"%s\"' % (self.source))
            if config.DEBUG >= 2:
                for f in dir(data):
                    _debug_('%s: %s' % (f, eval('data["%s"]' % f)), 2)
            if data.has_key('length') and data['length'] is not None:
                self.length = data['length']
                _debug_('Video length is %s' % self.length)
            else:
                self.length = 600
                _debug_('Video length not found, using %s' % (self.length))
        self._CropDetect()


    def _CropDetect(self):
        """Detect cropping, contains pieces of QuickRip

        Function is always called because cropping is a good thing, and we can pass our ideal values
        back to the client wich can verify them visually if needed.""" #not true atm
        #build mplayer parameters
        start = 0
        if self.timeslice[0]:
            start = self.timeslice[0]
        if self.timeslice[1]:
            sstep = int( (self.timeslice[1] - start) / 27)
        elif hasattr(self, "length"):
            sstep = int( (self.length - start) / 27)
        else:
            sstep = 60

        arguments = self.timeslice_mencoder + [ "-vf", "cropdetect=30", "-nosound", "-vo", "null", "-fps", "540"]
        if sstep > 0:
            arguments +=  [ "-sstep", str(sstep)]

        if self.info.mime == 'video/dvd':
            arguments += [ '-dvd-device', self.source, 'dvd://%s' % self.chapter ]
        else:
            arguments += [ self.source ]

        _debug_('_run(mplayer, arguments, self._CropDetectParse, None, 0, None)', 2)
        _debug_(' '.join([mplayer]+arguments))
        #print (' '.join([mplayer]+arguments))
        self._run(mplayer, arguments, self._CropDetectParse, None, 0, None)


    def _GenerateCLMencoder(self):
        """Generate the command line(s) to be executed, using MEncoder for encoding"""
        #calculate the videobitrate
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
        if self.info.mime == 'video/dvd':
            if hasattr(config, 'DVD_LANG_PREF') and config.DVD_LANG_PREF:
                audio = ['-alang', config.DVD_LANG_PREF]
            else:
                audio = []
            return audio+[ '-dvd-device', self.source, 'dvd://%s' % self.chapter]
        else:
            return [ self.source ]


    def _GCLMVideopass(self, passnr):
        """Returns video pass specefic part of mencoder cl"""
        vf = copy(self.vfilters)
        vfilter = ''
        vpass = ''
        yscaled = None
        #deinterlacer test vf += ['pp=lb']
        #set appropriate videopass, codec independant (lavc is vpass, xvid is pass)
        if passnr > 0:
            if self.vcodec == 'XviD':
                passname = ':pass=%s'
            else:
                passname = ':vpass=%s'

            vpass = passname % passnr

            if self.vcodec == 'MPEG 4 (lavc)' and passnr == 1:
                vpass = vpass + ':turbo'

        #generate videofilters first, NI completly yet
        if self.crop != None:
            vf += [ 'crop=%s' % self.crop ]

        #in case of xvid and anamorphic dvd, add scaling to compensate AR..
        #if we didn't find cropping we have no res, so no tricks
        if self.vcodec == 'XviD' and self.crop:
            if self.ana:
                #calculate a decent resized picturesize, res must still be a multiple of 16
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
                self.resx=720
                self.resy=576
            else:
                self.resx=720
                self.resy=480

        if self.resx==0 and self.crop:
            (self.resx, self.resy) = self._OptimalRes(self.cropres[0], self.cropres[1])
        elif self.resx==0:
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

        output=self.output

        aspect= ''
        if self.vcodec=='MPEG 2 (lavc)' and self.cropres[0] != '720':
            if self.ana == True:
                aspect=':aspect=16/9'
            else:
                aspect=':aspect=4/3'
        elif self.vcodec!='H.264':
            aspect =  ':autoaspect'

        # set video encoder options
        if self.altprofile == None:
            args = [
                '-ovc', mappings['vcodec'][self.vcodec][0], mappings['vcodec'][self.vcodec][1],
                        mappings['vcodec'][self.vcodec][2] % (self.vbrate, self.threads, vpass, aspect ) ]
        else:  # Allow encoder options from client
            aprofile = '%s:vbitrate=%s:threads=%s%s%s' % (self.altprofile, self.vbrate, self.threads, vpass, aspect)
            args = ['-ovc', mappings['vcodec'][self.vcodec][0],mappings['vcodec'][self.vcodec][1], aprofile ]


        # set audio encoder options
        args += ['-oac' , mappings['acodec'][self.acodec][0] ]
        if self.acodec != 'copy':
            args += [ mappings['acodec'][self.acodec][1],
                      mappings['acodec'][self.acodec][2] % self.abrate ]
        args += [ '-o', output]

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

        if self.vcodec=='MPEG 2 (lavc)':
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


    def _CropDetectParse(self, lines, data): #seek to remove data
        """Parses Mplayer output to obtain ideal cropping parameters, and do PAL/NTSC detection
        from QuickRip, heavily adapted, new algo
        TODO give this another name, it does more then crop detection only
        """
        #print '_CropDetectParse(self, lines=%r, data=%r)' % (lines, data)

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
        crop_options = {}
        #common_crop = ''
        #cc_hits = 2

        foundrate = False

        try:
            if not self.info.video[0].has_key('width') or not self.info.video[0].has_key('height'):
                self.finishedanalyze = True
                return
            crop = str(self.info.video[0].width)+':'+str(self.info.video[0].height)+':0:0'
            crop_options[crop] = 1
        except Exception, e:
            pass
        for line in lines:
            line = line.strip('\n')
            if re_crop.search(line):
                crop = re_crop.search(line).group(1)
                try:
                    crop_options[crop] = crop_options[crop] + 1
                    #if crop_options[crop] > cc_hits:
                    #    common_crop = crop
                except:
                    crop_options[crop] = 1

            #try to see if this is a PAL DVD, an NTSC Progressive DVD, ar an NTSC DVD
            if not foundrate and self.info.mime == 'video/dvd':
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
                        if not (self.info.video[0].has_key('width') / self.info.video[0].has_key('height')) > 1.3334:
                            self.ana = False
                    except:
                        pass
                else:
                    self.ana = True

        if hasattr(self.info, 'aspect'):
            if int(self.info.aspect*100) == 1.33:
                self.ana = False
            else:
                self.ana =  True

        if not foundrate: # unknown frame rate setting to 29.970
            self.fps = 29.970

        #  unknown frame rate setting to 29.970
        if not foundrate: self.fps = 29.970

        _debug_('All collected cropopts: %s' % crop_options)

        #if we didn't find cropping options (seems to happen sometimes on VERY short dvd chapters)
        if crop_options == {}:
            #end analyzing
            self.finishedanalyze = True
            return

        #some homegrown sleezy alghorythm to pick the best crop options
        hcounter = 0
        possible_crop = []
        for crop, counter in crop_options.items():
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


        #make the final crop outputs a resolution wich is a multiple of 16, v and h ....
        crop = split(self.crop, ':')
        adjustedcrop = []
        for res in crop[0:2]:
            if res:
                over = int(res) % 16
                adjustedcrop.append(str(int(res) - over))
        adjustedcrop += crop[2:]
        #save cropped resolution for later
        self.cropres = ( int(adjustedcrop[0]), int(adjustedcrop[1]) )

        self.crop = join(adjustedcrop, ':')

        _debug_('Selected crop option: %s' % self.crop)

        #end analyzing
        self.finishedanalyze = True


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

        re_progress = re.compile('(\d+)\%\) .*Trem:\s*(\d+\w+)\s+')
        if re_progress.search(line):
            self.percentage = re_progress.search(line).group(1)
            self.trem = re_progress.search(line).group(2)
            #self.ui_updateProgress(perc, trem, passtype)


    def _run(self, program, arguments, finalfunc, updatefunc=None, flushbuffer=0, data=None, lock=None):
        """Runs a program; supply program name (string) and arguments (list)
        seek to remove data and/or crop (not really used)
        """
        command = [program]
        command += arguments

        self.thread = CommandThread(self, command, updatefunc, finalfunc, flushbuffer, data, None)
        self.thread.start()



class CommandThread(threading.Thread): # seek to remove data andor crop (not really used)
    """Handle threading of external commands
    command executing class - Taken from Quickrip & adapted.
    """
    def __init__(self, parent, command, updatefunc, finalfunc, flushbuffer, data, lock):
        threading.Thread.__init__(self)
        self.parent = parent
        self.updateFunc = updatefunc
        self.finalFunc = finalfunc
        self.flushbuffer = flushbuffer
        self.command = command
        self.data = data
        self.lock = lock
        _debug_('command=\"%s\"' % ' '.join(command))


    def run(self):
        #self.lock.acquire()
        self.pipe = popen2.Popen4(self.command)
        pid = self.pipe.pid
        self.parent.pid = copy(pid)
        totallines = []

        _debug_('Mencoder running at PID %s' % self.pipe.pid)

        while 1:
            if self.flushbuffer:
                line = self.pipe.fromchild.read(1000)
            else:
                line = self.pipe.fromchild.readline()

            _debug_(line)
            if not line:
                break
            else:
                #don't save up the output if flushbuffer is enabled
                if self.flushbuffer != 1:
                    totallines.append(line)
                if self.updateFunc != None:
                    self.updateFunc(line, self.data)


        # Clean up process table--you already handle exceptions in the function
        #self.kill_pipe()

        #give mplayer/mencoder some time to die before we try & kill it, or zombies will raise from their grave :)
        sleep(0.5)

        try:
            os.waitpid(pid, os.WNOHANG)
        except:
            pass

        self.kill_pipe()

        if self.finalFunc != None:
            self.finalFunc(totallines, self.data)

        #self.lock.release()

        sys.exit(2)


    def kill_pipe(self):
        """Kills current process (pipe)"""
        try:
            os.kill(self.pipe.pid, 9)
            os.waitpid(self.pipe.pid, os.WNOHANG)
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
            return (self.currentjob.name, int(self.currentjob.status),
                    int(self.currentjob.percentage), self.currentjob.trem)
        else:
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
        """Executes the jobs in the queue, and gets called after every mencoder run is completed"""
        if self.qlist == []:
            #empty queue, do nothing
            self.running = False
            if hasattr(self, 'currentjob'):
                del self.currentjob
            _debug_('queue empty, stopping processing...', DINFO)
            return

        _debug_('runQueue callback data: %s' % line)
        #get the first queued object
        self.currentjob = self.qlist[0]

        _debug_('PID %s' % self.currentjob.pid)

        if self.currentjob.status == status.vpassfinal:
            _debug_('Job %s finished' % self.currentjob.idnr, DINFO)
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
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue,
                            self.currentjob._MencoderParse, 1, None)

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
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue,
                            self.currentjob._MencoderParse, 1, None)

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
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue,
                            self.currentjob._MencoderParse, 1, None)

        _debug_('Started job %s, %s on PID %s' % (self.currentjob.idnr, \
            status[self.currentjob.status], self.currentjob.pid), DINFO)
        _debug_('Encoder Command is "%s"' % ' '.join(self.currentjob.cls[0]), DINFO)



# -----DEBUGGING STUFF BELOW---USE ONLY WHEN WEARING A BULLETPROOF VEST ;)


#def conc(list):
#str = ''
#for el in list:
#    str = str + el + ' '
#return str

#FOR TESTING ONLY
if __name__ == '__main__':
    encjob = EncodingJob('/storage/video/dvd/BRUCE_ALMIGHTY/', 'test.avi', 'lala', 456789, 17)
    #encjob._CropDetect()
    print 'THE KING RETURNED FROM INSPECTING THE CROPPING !'
    sleep(5)
    print encjob.crop
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
