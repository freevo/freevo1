# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Interface to CommDetectServer
# -----------------------------------------------------------------------
#
# Author: Justin Wetherell
# some parts taken or inspired by Freevo's encodingserver
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
Interface to Commercial Detection Server
"""

#Import statements
import threading
from time import sleep
import sys, os, re, popen2 #, ConfigParser, copy
import config
import kaa.metadata as mmpython
from copy import copy
from string import split, join

from benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL


class CommDetectJob:
    """Class for creation & configuration of CommDetectJobs. This generates the mencoder commands"""

    def __init__(self, source, idnr):
        """Initialize class instance"""
        _debug_('commdetectcore.CommDetectJob.__init__(%s)' % (source))
        self.source = source
        self.name = source
        self.idnr = idnr
        self.pid = 0

        self.busy = 0
        """0==NEW, 1==BUSY 2==DONE"""

        self.blackframes=[]
        self.edlList=[]
        videoCodec='-ovc lavc'
        nosound='-nosound'
        videoFilter='-vf blackframe'
        output='-o /dev/null'
        grep='| grep vf_blackframe'
        outfile='> /tmp/blackframes.txt'
        string=" "+videoCodec+\
               " "+nosound+\
               " "+videoFilter+\
               " "+self.source+\
               " "+output+\
               " "+grep+\
               " "+outfile
        self.cls = [string]

    def _run(self, program, arguments, source, flushbuffer, finalfunc):
        """Runs a program; supply program name (string) and arguments (list)"""
        command = program
        command += arguments
        self.thread = CommandThread(self, command, flushbuffer, finalfunc)
        self.thread.start()

    class blackframe:
        frame=0.0
        seconds=0.0
        time=0.0

    class edl:
        startSkipTime=0.0
        endSkipTime=0.0
        action=0.0

    def grabBlackFrames(self):
        #Grab all possible blackframes
        fileHandle = open('/tmp/blackframes.txt','r')
        for line in fileHandle.readlines():
            splitln = line.split("\r")
            line=splitln[-2]+splitln[-1]
            #output with blackframe
            newBlackFrame = self.blackframe()
            splitframe = line.split("vf_blackframe:")
            matchSeconds = re.compile('\d+\.\d+s')
            match = matchSeconds.search(splitframe[0])
            if match:
                seconds=re.sub('s','',match.group())
                newBlackFrame.seconds=float(seconds)
            matchFrame = re.compile('\d+f')
            match = matchFrame.search(splitframe[0])
            if match:
                frame=re.sub('f','',match.group())
                newBlackFrame.frame=float(frame)
            matchTime = re.compile('\d+min')
            match = matchTime.search(splitframe[0])
            if match:
                time=re.sub('min','',match.group())
                newBlackFrame.time=int(time)
            self.blackframes.append(newBlackFrame)
        fileHandle.close()

    def findCommercials(self):
        startFrame=None
        startFrameTime=0
        endFrame=None
        for bframe in self.blackframes:
            if (startFrameTime==0):
                #Commerical break
                startFrame=bframe
                startFrameTime=bframe.time
            else:
                if ((bframe.time==startFrameTime)or(bframe.time==(startFrameTime-1))):
                    #Same commercial break
                    startFrameTime=bframe.time
                    endFrame=bframe
                else:
                    #New commercial break
                    if not endFrame:
                        #Sometimes a blackframe is thrown in the beginning
                        endFrame=startFrame
                    if ((endFrame.seconds-startFrame.seconds)>0):
                        newEdl = self.edl()
                        newEdl.startSkipTime=startFrame.seconds
                        newEdl.endSkipTime=endFrame.seconds
                        self.edlList.append(newEdl)
                    startFrame=None
                    startFrameTime=0
                    endFrame=None
        if ((len(self.edlList)==0)and(startFrame and endFrame)):
            #Only one commercial
            newEdl = self.edl()
            newEdl.startSkipTime=startFrame.seconds
            newEdl.endSkipTime=endFrame.seconds
            self.edlList.append(newEdl)

    def writeEdl(self):
        if (len(self.edlList)>0):
            outputFile=self.source.split(".")
            output=outputFile[0]+".edl"
            fileHandle = open(output,'w')
            for skipSegment in self.edlList:
                fileHandle.write("%d %d %d\n" % (skipSegment.startSkipTime, \
                                                skipSegment.endSkipTime, \
                                                skipSegment.action))
            fileHandle.close()

class CommandThread(threading.Thread):
    """Handle threading of external commands"""
    def __init__(self, parent, command, flushbuffer, finalfunc):
        threading.Thread.__init__(self)
        self.parent = parent
        self.command = command
        self.flushbuffer = 0
        self.finalfunc = finalfunc
        _debug_('command=\"%s\"' % command)

    @benchmark(benchmarking & 0x1, benchmarkcall)
    def run(self):
        self.pipe = popen2.Popen4(self.command)
        pid = self.pipe.pid
        self.parent.pid = copy(pid)
        totallines = []
        _debug_("Mencoder running at PID %s" % self.pipe.pid)
        self.parent.busy = 1
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
        sleep(0.5)
        try:
            os.waitpid(pid, os.WNOHANG)
        except:
            pass
        self.kill_pipe()
        _debug_("Grabbing Blackframes from file")
        self.parent.grabBlackFrames()
        _debug_("Finding Commercials")
        self.parent.findCommercials()
        _debug_("Writing edl file")
        self.parent.writeEdl()
        self.parent.busy = 2
        self.finalfunc()
        sys.exit(2)

    def kill_pipe(self):
        """Kills current process (pipe)"""
        try:
            os.kill(self.pipe.pid, 9)
            os.waitpid(self.pipe.pid, os.WNOHANG)
        except:
            pass

class CommDetectQueue:
    """Class for generating an commdetect queue"""
    def __init__(self):
        #we keep a list and a dict because a dict doesn't store an order
        self.qlist = []
        self.qdict = {}
        self.running = False

    def addCommDetectJob(self, encjob):
        """Adds an commdetectjob to the queue"""
        self.qlist += [encjob]
        self.qdict[encjob.idnr] = encjob

    def startQueue(self):
        """Start the queue"""
        if not self.running:
            self.running = True
            _debug_("queue started", DINFO)
            self._runQueue()

    def listJobs(self):
        """Returns a list of queue'ed jobs"""
        if self.qdict == {}:
            return []
        else:
            jlist = []
            for idnr, job in self.qdict.items():
                jlist += [ (idnr, job.name) ]
            return jlist

    def _runQueue(self, line="", data=""):
        """Executes the jobs in the queue, and gets called after every mencoder run is completed"""
        if self.qlist == []:
            #empty queue, do nothing
            self.running = False
            if hasattr(self,"currentjob"):
                del self.currentjob
            _debug_("queue empty, stopping processing...", DINFO)
            return
        _debug_("runQueue callback data : %s" % line)

        #get the first queued object
        self.currentjob = self.qlist[0]
        _debug_("PID %s" % self.currentjob.pid)

        if self.currentjob.busy == 0:
            #NEW
            _debug_("Running Mencoder, to write the blackframes to a file")
            self.currentjob.busy = True
            self.currentjob._run(config.CONF.mencoder, \
                                self.currentjob.cls[0], \
                                self.currentjob.source, \
                                0, \
                                self._runQueue)
            _debug_("Started job %s, PID %s" % (self.currentjob.idnr, self.currentjob.pid))

        if self.currentjob.busy == 2:
            #DONE
            del self.qlist[0]
            del self.qdict[self.currentjob.idnr]
            self.currentjob.busy = 0
            self.running = False
            self._runQueue()
