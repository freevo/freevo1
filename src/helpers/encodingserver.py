#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# EncodingServer.py, part of EncodingServer - for use with or without Freevo
# -----------------------------------------------------------------------
# $Id: rc.py 8278 2006-09-30 07:22:11Z duncan $
#
# Author: den_RDC
# some parts taken or inspired by Freevo's recordserver (by rshortt)
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
from twisted.web import xmlrpc, server
from twisted.internet.app import Application
from twisted.internet import reactor
from twisted.python import log
from util.marmalade import jellyToXML, unjellyFromXML
import logging
import time, random, sys, os

from encodingcore import EncodingJob, EncodingQueue

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__revision__ = "$Rev: 26 $"
__copyright__ = "Copyright (C) 2004 den_RDC"
__license__ = "GPL"

tmppath = '/tmp/encodingserver'

DEBUG=False

jam = jellyToXML
unjam = unjellyFromXML

class EncodingServer(xmlrpc.XMLRPC):

    def __init__(self, debug=False):
        self.jobs = {}
        
        #setup a logger
        if debug: #when debugging, output everything to stdout using the root logging class
            self.log = logging
        else: #normally, write nice formatted messages to a logfile)
            self.log = logging.getLogger("EncodingServer")
            self.log.setLevel(logging.INFO)
            FHandler = logging.FileHandler("encodingserver.log")
            FHandler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s %(message)s"))
            self.log.addHandler(FHandler)
        
        self.queue = EncodingQueue(self.log)
        
        self.log.info("EncodingServer started...")
        
    def xmlrpc_echotest(self, blah):
        return (True, 'EncodingServer::echotest: %s' % blah)

    def xmlrpc_initEncodeJob(self, source, output, friendlyname="", chapter=None):
        #safety checks
        if not (source or output):
            return (False, 'EncodingServer::initEncodeJob:  no source or output given')
        #generate a "random" idnr based on the time
        #in p2.3 , int() can return long int's, wich is fine, except it makes XMLRPC fail somwhere along the way
        # so we devide or random number by 100 :)
        idnr = int((time.time() / random.random()) / 100)
        self.jobs[idnr] = EncodingJob(source, output, friendlyname, idnr, chapter)
        
        #wait for the analyzing to end
        while not self.jobs[idnr].finishedanalyze:
            time.sleep(0.1)
        
        self.log.info("Initialized job %s (idnr : %s)" % (friendlyname,idnr))
        
        return (True, idnr)
        
    def xmlrpc_getContainerCAP(self, idnr):
        return (True, jam(self.jobs[idnr].getContainerList()))
       
    def xmlrpc_setContainer(self, idnr, container):
        status = self.jobs[idnr].setContainer(container)
        
        if not status:
            return (True, "EncodingServer::setContainer: OK")
        else:
            return (False, "EncodingServer::setContainer: %s" % status)
            
    def xmlrpc_getVideoCodecCAP(self, idnr):
        return (True, jam(self.jobs[idnr].getVideoCodecList()))
        
    def xmlrpc_setVideoCodec(self, idnr, vcodec, tgtsize, multipass=False):
        #safety checks
        if not (vcodec or tgtsize):
            return (False, 'EncodingServer::setVideoCodec:  no codec or target size given')
            
        status = self.jobs[idnr].setVideoCodec(vcodec, tgtsize, multipass)
        
        if not status:
            return (True, "EncodingServer::setVideoCodec: OK")
        else:
            return (False, "EncodingServer::setVideoCodec: %s" % status)   
           
    def xmlrpc_getAudioCodecCAP(self, idnr):
        return (True, jam(self.jobs[idnr].getAudioCodecList()))
        
    def xmlrpc_setAudioCodec(self, idnr, acodec, abrate):
        #safety checks
        if not (acodec or abrate):
            return (False, 'EncodingServer::setAudioCodec:  no codec or bitrate given')
            
        status = self.jobs[idnr].setAudioCodec(acodec, abrate)
        
        if not status:
            return (True, "EncodingServer::setAudioCodec: OK")
        else:
            return (False, "EncodingServer::setAudioCodec: %s" % status)
            
    def xmlrpc_getVideoFiltersCAP(self, idnr):
        return (True, jam(self.jobs[idnr].getVideoFiltersList()))
        

    def xmlrpc_setVideoFilters(self, idnr, filters):
        #safety checks
        if not filters:
            return (False, 'EncodingServer::setAudioCodec:  no codec or bitrate given')
            
        status = self.jobs[idnr].setVideoFilters(unjam(filters))
        
        if not status:
            return (True, "EncodingServer::setVideoFilters: OK")
        else:
            return (False, "EncodingServer::setVideoFilters: %s" % status)
        
    def xmlrpc_queueIt(self, idnr, now=False):
        self.queue.addEncodingJob(self.jobs[idnr])
        del self.jobs[idnr]
        self.log.info("Added job %s to the queue" % idnr)
        if now:
            self.queue.startQueue()
        return (True, "EncodingServer::queueIt: OK")
        
    def xmlrpc_getProgress(self):
        prog = self.queue.getProgress()
        if type(prog) is str:
            return (False, "EncodingServer::getProgress: %s" % prog)
        return (True, jam(prog))
        
    def xmlrpc_startQueue(self):
        self.queue.startQueue()
        
        return (True, "EncodingServer::startqueue: OK")
        
    def xmlrpc_listJobs(self):
        jlist = self.queue.listJobs()
        
        return (True, jam(jlist))

        
        

def main():
    #check for /tmp/encodingserver and if it doesn't exist make it
    if not (os.path.exists(tmppath) and os.path.isdir(tmppath)):
        os.mkdir(tmppath)
    #chdir to /tmp/encodingserver
    os.chdir(tmppath)
    
    app = Application("EncodingServer")
    if len(sys.argv) >= 2 and sys.argv[1] == "debug":
        es = EncodingServer(True)
        DEBUG=True
        import encodingcore
        encodingcore.DEBUG=True
    else:
        es = EncodingServer()
    app.listenTCP(6666, server.Site(es))
    app.run(save=0)
    

if __name__ == '__main__':
    import traceback
    while 1:
        try:
            start = time.time()
            main()
            break
        except:
            traceback.print_exc()
            if start + 10 > time.time():
                print 'server problem, sleeping 1 min'
                time.sleep(60)
