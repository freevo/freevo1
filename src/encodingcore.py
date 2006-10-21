#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# EncodingCore.py, part of EncodingServer - for use with Freevo
# -----------------------------------------------------------------------
# $Id: rc.py 8278 2006-09-30 07:22:11Z duncan $
#
# Author: den_RDC
# some parts taken or inspired by Quickrip (by T. Chance, GPL,
# http://quickrip.sf.net)
# TODO:
# niceness & pausing queue
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
import kaa.metadata as mmpython
from copy import copy
from string import split, join

#some temporary hardcoded programs

mencoder = "mencoder"
mplayer = "mplayer"

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__revision__ = "$Rev: 30 $"
__copyright__ = "Copyright (C) 2004 den_RDC"
__license__ = "GPL"

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            self.log.debug(String(text))
        except:
            print(String(text))

#"hardcoded capabilities" .. these might change or become dynamic in the future, when more capabilities are supported
#the "container format" will remain hardcoded

ContainerCapList = [ 'Avi' ]
VideoCodecList = [ 'MPEG 4 (lavc)', 'XViD']
AudioCodecList = [ 'MPEG 1 Layer 3 (mp3)' ]

VFDict = {
    'Deinterlacing' : ['None','Linear blend','Lavc deinterlacer'],
    'Inverse Telecine' : ['None','On (stateless filter)'],
    'Denoise' : ['None','Normal denoise','HQ denoise']
    }

MencoderFilters = {
    'Linear blend' : "pp=lb",
    'Lavc deinterlacer' : "lavcdeint",
    'On (stateless filter)' : "ivtc=1",
    'Normal denoise' : "denoise3d",
    'HQ denoise' : "hqdn3d"
    }

MencoderMapping = {
    'MPEG 4 (lavc)' : ["lavc",["-lavcopts","vcodec=mpeg4:vhq:vqmin=2:v4mv:trell:autoaspect:vbitrate=%s%s"]],
#to hard    'MPEG 4 (lavc)' : ["lavc",["-lavcopts","vcodec=mpeg4:vhq:vqmin=2:v4mv:vlelim=-4:vcelim=9:lumi_mask=0.05:dark_mask=0.01:autoaspect:vbitrate=%s%s"]],
#old one    'MPEG 4 (lavc)' : ["lavc",["-lavcopts","vcodec=mpeg4:vhq:autoaspect:vbitrate=%s%s"]],
    'XViD' : ["xvid",["-xvidencopts","bitrate=%s%s"]],
    'MPEG 1 Layer 3 (mp3)' : ["mp3lame",["-lameopts", "cbr:br=%s"]]
    }


#from pytvgrab enum.py, see http://pytvgrab.sourceforge.net
class Enum(dict):
    """Enum

    Enum(names, x=0)"""

    def __init__(self, names, x=0):
        for i in range(x, x+len(names)):
          self.__dict__[names[i-x]]=i
          self[i]=names[i-x]
    # __init__()


status = Enum(["notset","apass","vpass1","vpassfinal","postmerge"])

class EncodingJob:
    """Class for creation & configuration of EncodingJobs. This generates the mencoder commands"""

    def __init__(self, source, output, friendlyname, idnr, chapter=None):
        """Initialize class instance"""
        _debug_('__init__(self, %s, %s, %s, %s, %s)' % (source, output, friendlyname, idnr, chapter), 2)
        #currently only MEncoder can be used, but who knows what will happen in the future :)
        self._generateCL = self._GenerateCLMencoder

        self.source = source
        self.output = output
        self.name = friendlyname
        self.idnr = idnr
        self.chapter = chapter

        self.sourcetype = None

        self.container = "Avi"

        self.tgtsize = None
        self.length = None

        self.vcodec = None
        self.vbrate = None
        self.multipass = False
        self.vfilters = []
        self.crop = None


        self.acodec = AudioCodecList[0]
        self.abrate = 128
        self.afilters = {} # Not used atm, might be used in the future

        self.cls = []

        self.percentage = 0
        self.trem = 0

        self.status = status.notset
        self.pid = 0

        self.pal = False
        self.ntsc = False
        self.ntscprog = False
        self.ana = False

        #Analyze our source
        self.finishedanalyze = False
        self._AnalyzeSource()


    def setContainer(self, container):
        """Set a container to hold the audio & video streams"""
        #safety checks
        if container not in ContainerCapList:
            return "Unknown container format"

        self.container = container

    def getContainerList(self):
        return ContainerCapList


    def getVideoCodecList(self):
        """Return a possible video codec list"""
        return VideoCodecList

    def setVideoCodec(self, vcodec, tgtsize, multipass=False):
        """Set video codec and target filesize (in MB)"""
        #safety checks first
        if vcodec not in self.getVideoCodecList():
            return "Unknown video codec"

        self.vcodec = vcodec
        self.tgtsize = (int(tgtsize) * 1024) #filesize is internally stored in kb
        self.multipass = multipass


    def getAudioCodecList(self):
        """Return a possible audio codec list"""
        return AudioCodecList


    def setAudioCodec(self, acodec, abrate=128):
        """Set audio codec & bitrate"""
        #safety first
        if acodec not in self.getAudioCodecList():
            return "Unknown audio codec"

        self.acodec = acodec
        self.abrate = abrate

    def getVideoFiltersList(self):
        """Return a list of possible video filters"""
        if self.ntsc:
            return VFDict
        else:
            non_ivtcdict = VFDict.copy()
            del non_ivtcdict['Inverse Telecine']
            return non_ivtcdict

    def setVideoFilters(self, videofilters):
        """Set video filters"""
        for vfilter, option in videofilters.items():
            if MencoderFilters.has_key(option):
                self.vfilters += [ MencoderFilters[option] ]

    def _CalcVideoBR(self):
        """Calculates the video bitrate"""

        self.vbrate = int((((int(self.tgtsize)*8) / int(self.length)) - int(self.abrate)) / 0.98)
        if self.vbrate > 12000: #we got a very short file, very high bitrates are interpreted as bit/s instead of kbit/s, shitty qual
            self.vbrate = 6000


    def _AnalyzeSource(self):
        """Find out some basic information about the source

        ATM we will blindly assume it's a dvdrom device or a disk dvd image, if a chapter is given"""
        _debug_('_AnalyzeSource(self)', 2)

        if self.chapter:
            self.sourcetype = "dvd"
            #check some things, like length
            mmpython.disc.ifoparser.open(self.source)
            data = mmpython.disc.ifoparser.title(self.chapter)
            self.length = data[2]
            _debug_("Video length: %s" % self.length)
            #NI : maybe implement procedure to get resolution, handy for scaling/manual cropping
            self._CropDetect()
        else:
            data = mmpython.parse(self.source)
            self.sourcetype = data['type'].encode('latin1')
            for f in dir(data):
                print '%s: %s' % (f, eval('data["%s"]' % f))
            self.length = data.get_length()
            _debug_("Video length: %s" % self.length)
            self._CropDetect()


    def _CropDetect(self): #contains pieces of QuickRip
        """Detect cropping

        Function is always called because cropping is a good thing, and we can pass our ideal values
        back to the client wich can verify them visually if needed.""" #not true atm
        #build mplayer parameters
        if hasattr(self,"length"):
            sstep = int(self.length / 27)
        else:
            sstep = 60

        arguments = [ "-vop", "cropdetect=30", "-nosound", "-vo", "null", "-frames", "10", "-sstep", str(sstep)]

        if self.sourcetype == "dvd":
            arguments += [ '-dvd-device', self.source, 'dvd://%s' % self.chapter ]
        else:
            arguments += [ self.source ]

        _debug_('arguments=%s' % arguments)
        _debug_('_run(mplayer, arguments, self._CropDetectParse, None, 0, None)', 2)
        self._run(mplayer, arguments, self._CropDetectParse, None, 0, None)

    def _GenerateCLMencoder(self):
        """Generate the command line(s) to be executed, using MEncoder for encoding"""
        #calculate the videobitrate
        self._CalcVideoBR()

        #generate the audio pass
        audiopass = []


        audiopass += self._GCLMAudiopass()
        audiopass += self._GCLMSource()

        #for single passes
        if not self.multipass:
            videopass = []
            videopass += self._GCLMVideopass(0)
            videopass += self._GCLMSource()

            self.cls = [ audiopass, videopass ]

        else:
            videopass1 = []
            videopass2 = []

            videopass1 += self._GCLMVideopass(1)
            videopass1 += self._GCLMSource()

            videopass2 += self._GCLMVideopass(2)
            videopass2 += self._GCLMSource()

            self.cls = [ audiopass, videopass1, videopass2 ]

    def _GCLMSource(self):
        """Returns source part of mencoder"""
        if self.sourcetype == "dvd":
            #return [ "-endpos", "10","-dvd-device", self.source , "dvd://%s" % self.chapter]
            return [ "-dvd-device", self.source , "dvd://%s" % self.chapter]
        else:
            return [ self.source ]

    def _GCLMAudiopass(self):
        """Returns audio pass specefic part of mencoder cl"""
        return ["-ovc", "frameno", "-oac", MencoderMapping[self.acodec][0], MencoderMapping[self.acodec][1][0],
                MencoderMapping[self.acodec][1][1] % self.abrate,
                "-o", "frameno.avi"]

    def _GCLMVideopass(self, passnr):
        """Returns video pass specefic part of mencoder cl"""
        vf = copy(self.vfilters)
        vfilter=""
        vpass = ""
        yscaled = None
        #deinterlacer test vf += ["pp=lb"]
        #set appropriate videopass , codec independant (lavc is vpass, xvid is pass)
        if passnr > 0 :
            if self.vcodec == "XViD":
                passname = ":pass=%s"
            else:
                passname = ":vpass=%s"

            vpass = passname % passnr

        #generate videofilters first, NI completly yet
        if self.crop != None:
            vf += [ "crop=%s" % self.crop ]

        #in case of xvid and anamorphic dvd, add scaling to compensate AR.. if we didn't find cropping we have no res, so no tricks
        if self.vcodec == "XViD" and (self.crop != None):
            if self.ana:
                #calculate a decent resized picturesize, res must still be a multiple of 16
                yscaled = (self.cropres[1] * 0.703125)
                rounded = yscaled % 16
                yscaled -= rounded
                if rounded > 7.5:
                    yscaled += 16
                _debug_("Rescaled, corrected for AR res is %sx%s" % (self.cropres[0], int(yscaled)))
            else: # no scaling, w ehave a 4/3
                yscaled = self.cropres[1]
            #new, calculate ideal res based on BPP
            idealres = self._OptimalRes(self.cropres[0], int(yscaled))
            _debug_("Rescaled, rounded yres is %sx%s" % (idealres[0], idealres[1]))
            vf += [ "scale=%s:%s" % (idealres[0], idealres[1])]

        _debug_("Video filters: %s" % vf)

        #join vf options
        if len(vf)> 1:
            for vfopt in vf[0:-1]:
                vfilter = vfilter + vfopt + ","
        if len(vf) >= 1:
            vfilter = vfilter + vf[-1]

        #if we have a dualpass, for the first pass, dump the output to /dev/null
        if passnr == 1:
            output="/dev/null"
        else:
            output=self.output

        args = ["-oac", "copy", "-ovc",MencoderMapping[self.vcodec][0], MencoderMapping[self.vcodec][1][0],
                MencoderMapping[self.vcodec][1][1] % (self.vbrate, vpass),
                "-vf", vfilter, "-o", output]

        #if we have a progressive ntsc file, lock the output fps (do this with ivtc too)
        if ("ivtc=1" in vf) or self.ntscprog:
            args = ["-ofps","23.976"].append(args)

        #if we scale, use the bilinear algorithm
        if yscaled:
            args += ["-sws","1"]

        return args

    #from QuickRip, heavily adapted, new algo
    #TODO give this another name, it does more then crop detection only
    def _CropDetectParse(self, lines, data): #seek to remove data
        """Parses Mplayer output to obtain ideal cropping parameters, and do PAL/NTSC detection"""

        re_crop = re.compile('.*-vf crop=(\d*:\d*:\d*:\d*).*')
        re_ntscprog = re.compile('24fps progressive NTSC content detected')
        re_pal = re.compile('25.000 fps')
        re_ana = re.compile('(aspect 3)')

        crop_options = {}
##~         common_crop = ""
##~         cc_hits = 2

        foundtype = False

        for line in lines:
            if re_crop.search(line):
                crop = re_crop.search(line).group(1)
                try:
                    crop_options[crop] = crop_options[crop] + 1
##~                     if crop_options[crop] > cc_hits:
##~                         common_crop = crop
                except:
                    crop_options[crop] = 1

            #try to see if this is a PAL DVD, an NTSC Progressive DVD, ar an NTSC DVD
            if not foundtype and self.sourcetype == "dvd":
                if re_pal.search(line):
                    self.pal = True
                    foundtype = True
                else:
                    if re_ntscprog.search(line):
                        self.ntscprog = True
                        foundtype = True

            if re_ana.search(line):
                self.ana = True

        if not foundtype: self.ntsc = True

        if DEBUG:
            print "All collected cropopts: %s" % crop_options
            if self.pal: print "This is a PAL dvd"
            if self.ntsc: print "This is an NTSC dvd"
            if self.ntscprog: print "This is a progressive NTSC dvd"

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



        #make the final crop outputs a resolution wich is a multiple of 16 , v and h ....
        crop = split(self.crop, ":")
        adjustedcrop = []
        for res in crop[0:2]:
            over = int(res) % 16
            adjustedcrop.append(str(int(res) - over))
        adjustedcrop += crop[2:]
        #save cropped resolution for later
        self.cropres = ( int(adjustedcrop[0]), int(adjustedcrop[1]) )

        self.crop = join(adjustedcrop, ":")

        _debug_("Selected crop option: %s" % self.crop)

        #end analyzing
        self.finishedanalyze = True

    def _CalcBPP(self, x, y):
        """Perform a BPP (Bits per Pixel calculation)"""
        if self.pal: fps = 25.000
        if self.ntscprog: fps = 23.976
        if self.ntsc: fps = 29.970
        return (self.vbrate * 1000)/(x * y * fps)

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

    #from Quickrip, adapted
    def _MencoderParse(self, line, data): #seek to remove data
        """Parses mencoder stdout to get progress and trem"""
        #(passtype, title) = data

        re_progress = re.compile('(\d+)\%\) .*Trem:\s*(\d+\w+)\s+')
        if re_progress.search(line):
            self.percentage = re_progress.search(line).group(1)
            self.trem = re_progress.search(line).group(2)
            #self.ui_updateProgress(perc, trem, passtype)

    #from QuickRip, adapted
    def _run(self, program, arguments, finalfunc, updatefunc=None,
                flushbuffer=0, data=None, lock=None): # seek to remove data andor crop (not really used)
        """Runs a program; supply program name (string) and arguments (list)"""
        command = [program]
        command += arguments

        self.thread = CommandThread(self, command, updatefunc, finalfunc,
                                    flushbuffer, data, None) #self.lock)
        self.thread.start()





#command executing class - Taken from Quickrip & adapted.
class CommandThread(threading.Thread): # seek to remove data andor crop (not really used)
    """Handle threading of external commands"""
    def __init__(self, parent, command, updatefunc, finalfunc, flushbuffer, data, lock):
        threading.Thread.__init__(self)
        self.parent = parent
        self.updateFunc = updatefunc
        self.finalFunc = finalfunc
        self.flushbuffer = flushbuffer
        self.command = command
        self.data = data
        self.lock = lock

    def run(self):
        #self.lock.acquire()
        self.pipe = popen2.Popen4(self.command)
        pid = self.pipe.pid
        self.parent.pid = copy(pid)
        totallines = []

        _debug_("Mencoder running at PID %s" % self.pipe.pid)

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

    def __init__(self, logger, debug=0):
        #we keep a list and a dict because a dict doesn't store an order
        global DEBUG
        DEBUG = debug
        self.qlist = []
        self.qdict = {}
        self.running = False
        self.log = logger

        #remove old files
        self._removeTmp()

    def addEncodingJob(self, encjob):
        """Adds an encodingjob to the queue"""

        self.qlist += [encjob]
        self.qdict[encjob.idnr] = encjob

    def getProgress(self):
        """Gets progress on the current job"""
        if hasattr(self,"currentjob"):
            return (self.currentjob.name, int(self.currentjob.status),
                    int(self.currentjob.percentage), self.currentjob.trem)
        else:
            return "No job currently running"

    def startQueue(self):
        """Start the queue"""
        if not self.running:
            self.running = True
            _debug_("queue started", 0)
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
        tmpfiles = ['frameno.avi', 'divx2pass.log', 'xvid-twopass.stats' ]

        for tmpfile in tmpfiles:
            if os.path.exists(tmpfile):
                os.remove(tmpfile)

    def _runQueue(self, line="", data=""):
        """Executes the jobs in the queue, and gets called after every mencoder run is completed"""
        if self.qlist == []:
            #empty queue, do nothing
            self.running = False
            if hasattr(self,"currentjob"):
                del self.currentjob
            _debug_("queue empty, stopping processing...", 0)
            return

        _debug_("runQueue callback data : %s" % line)
        #get the first queued object
        self.currentjob = self.qlist[0]

        _debug_("PID %s" % self.currentjob.pid)

        if self.currentjob.status == status.vpassfinal:
            _debug_("Job %s finished" % self.currentjob.idnr, 0)
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
            _debug_("CLIs : %s" % self.currentjob.cls)

            #clean out temporary files
            self._removeTmp()

            #start audio encoding
            self.currentjob.status = status.apass
            self.currentjob._run(mencoder, self.currentjob.cls[0], self._runQueue,
                            self.currentjob._MencoderParse, 1, None)

        _debug_("Started job %s, %s on PID %s" % (self.currentjob.idnr, \
            status[self.currentjob.status], self.currentjob.pid), 0)
        _debug_("Encoder Command is %s" % self.currentjob.cls[0], 0)



# -----DEBUGGING STUFF BELOW---USE ONLY WHEN WEARING A BULLETPROOF VEST ;)


##~ def conc(list):
##~     str = ""
##~     for el in list:
##~         str = str + el + " "
##~     return str

#FOR TESTING ONLY
if __name__ == '__main__':
    encjob = EncodingJob('/storage/video/dvd/BRUCE_ALMIGHTY/', 'test.avi','lala', 456789, 17)
    #encjob._CropDetect()
    print "THE KING RETURNED FROM INSPECTING THE CROPPING !"
    sleep(5)
    print encjob.crop
    encjob.setVideoCodec('MPEG 4 (lavc)',"700", False)
    encjob.setAudioCodec("MPEG 1 Layer 3 (mp3)",'160')
    encjob.setVideoFilters({"Deinterlacing": "Linear blend"})
    encjob._CalcVideoBR()
    print encjob.vbrate
##~     encjob._generateCL()
##~     cl = encjob.cls
##~     print cl
##~     print conc(cl[0])
##~     print conc(cl[1])
    import logging
    log = logging.getLogger("EncodingCore")
    log.setLevel(logging.DEBUG)

    queue = encodingqueue(log, 2)
    queue.addEncodingJob(encjob)
    queue.startqueue()
