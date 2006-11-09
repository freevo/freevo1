#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# EncodingServer.py, part of EncodingServer - for use with Freevo
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

import sys, string, random, time, os, re, pwd, stat
import config
from util import vfs

appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
appconf = appname.upper()

# change uid
if __name__ == '__main__':
    uid='config.'+appconf+'_UID'
    gid='config.'+appconf+'_GID'
    try:
        if eval(uid) and os.getuid() == 0:
            os.setgid(eval(gid))
            os.setuid(eval(uid))
            os.environ['USER'] = pwd.getpwuid(os.getuid())[0]
            os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
    except Exception, e:
        print e

from twisted.web import xmlrpc, server
from twisted.internet.app import Application
from twisted.internet import reactor
from twisted.python import log
from util.marmalade import jellyToXML, unjellyFromXML
import time, random, sys, os
import logging
import config

from encodingcore import EncodingJob, EncodingQueue

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__revision__ = "$Rev: 26 $"
__copyright__ = "Copyright (C) 2004 den_RDC"
__license__ = "GPL"

DEBUG = hasattr(config, appconf+'_DEBUG') and eval('config.'+appconf+'_DEBUG') or config.DEBUG

logfile = '%s/%s-%s.log' % (config.LOGDIR, appname, os.getuid())
log.startLogging(open(logfile, 'a'))

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            log.debug(String(text))
        except:
            print String(text)

tmppath = '/tmp/encodingserver'

jam = jellyToXML
unjam = unjellyFromXML

class EncodingServer(xmlrpc.XMLRPC):

    def __init__(self, debug=False):
        self.jobs = {}
        
        #setup a logger
        #if debug: #when debugging, output everything to stdout using the root logging class
        #    self.log = logging
        #else: #normally, write nice formatted messages to a logfile)
        #    self.log = logging.getLogger("EncodingServer")
        #    self.log.setLevel(logging.INFO)
        #    FHandler = logging.FileHandler("encodingserver.log")
        #    FHandler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s %(message)s"))
        #    self.log.addHandler(FHandler)
        
        self.queue = EncodingQueue(log, DEBUG)
        
        _debug_("EncodingServer started...", 0)
        
    def xmlrpc_echotest(self, blah):
        _debug_("xmlrpc_echotest(self, blah)", 2)
        return (True, 'EncodingServer::echotest: %s' % blah)

    def xmlrpc_initEncodeJob(self, source, output, friendlyname="", chapter=None):
        _debug_("xmlrpc_initEncodeJob(self, %s, %s, %s, %s)" % (source, output, friendlyname, chapter), 2)
        #safety checks
        if not (source or output):
            return (False, 'EncodingServer::initEncodeJob:  no source or output given')
        #generate a "random" idnr based on the time
        #in p2.3 , int() can return long int's, wich is fine, except it makes XMLRPC fail somwhere along the way
        # so we devide or random number by 100 :)
        idnr = int((time.time() / random.random()) / 100)
        _debug_("idnr=%s" % (idnr), 2)
        self.jobs[idnr] = EncodingJob(source, output, friendlyname, idnr, chapter)
        
        #wait for the analyzing to end
        while not self.jobs[idnr].finishedanalyze:
            time.sleep(0.1)
        
        _debug_("Initialized job %s (idnr : %s)" % (friendlyname,idnr), 0)
        
        return (True, idnr)
        
    def xmlrpc_getContainerCAP(self, idnr):
        _debug_("xmlrpc_getContainerCAP(self, idnr)", 2)
        return (True, jam(self.jobs[idnr].getContainerList()))
       
    def xmlrpc_setContainer(self, idnr, container):
        _debug_("xmlrpc_setContainer(self, idnr, container)", 2)
        status = self.jobs[idnr].setContainer(container)
        
        if not status:
            return (True, "EncodingServer::setContainer: OK")
        else:
            return (False, "EncodingServer::setContainer: %s" % status)
            
    def xmlrpc_getVideoCodecCAP(self, idnr):
        _debug_("xmlrpc_getVideoCodecCAP(self, idnr)", 2)
        return (True, jam(self.jobs[idnr].getVideoCodecList()))
        
    def xmlrpc_setVideoCodec(self, idnr, vcodec, tgtsize, multipass=False, vbitrate=0):
        _debug_("xmlrpc_setVideoCodec(self, %s, %s, %s, %s %s)" % \
            (idnr, vcodec, tgtsize, multipass, vbitrate), 2)
        #safety checks
        if not (vcodec or (tgtsize and vbitrate)):
            return (False, 'EncodingServer::setVideoCodec:  no codec or target size given')
            
        status = self.jobs[idnr].setVideoCodec(vcodec, tgtsize, multipass, vbitrate)
        
        if not status:
            return (True, "EncodingServer::setVideoCodec: OK")
        else:
            return (False, "EncodingServer::setVideoCodec: %s" % status)   
           
    def xmlrpc_getAudioCodecCAP(self, idnr):
        _debug_("xmlrpc_getAudioCodecCAP(self, idnr)", 2)
        return (True, jam(self.jobs[idnr].getAudioCodecList()))
        
    def xmlrpc_setAudioCodec(self, idnr, acodec, abrate):
        _debug_("xmlrpc_setAudioCodec(self, idnr, acodec, abrate)", 2)
        #safety checks
        if not (acodec or abrate):
            return (False, 'EncodingServer::setAudioCodec:  no codec or bitrate given')
            
        status = self.jobs[idnr].setAudioCodec(acodec, abrate)
        
        if not status:
            return (True, "EncodingServer::setAudioCodec: OK")
        else:
            return (False, "EncodingServer::setAudioCodec: %s" % status)
            
    def xmlrpc_getVideoFiltersCAP(self, idnr):
        _debug_("xmlrpc_getVideoFiltersCAP(self, idnr)", 2)
        return (True, jam(self.jobs[idnr].getVideoFiltersList()))
        

    def xmlrpc_setVideoFilters(self, idnr, filters):
        _debug_("xmlrpc_setVideoFilters(self, idnr, filters)", 2)
        #safety checks
        if not filters:
            return (False, 'EncodingServer::setAudioCodec:  no codec or bitrate given')
            
        status = self.jobs[idnr].setVideoFilters(unjam(filters))
        
        if not status:
            return (True, "EncodingServer::setVideoFilters: OK")
        else:
            return (False, "EncodingServer::setVideoFilters: %s" % status)
        
    def xmlrpc_queueIt(self, idnr, now=False):
        _debug_("xmlrpc_queueIt(self, idnr, now=False)", 2)
        self.queue.addEncodingJob(self.jobs[idnr])
        del self.jobs[idnr]
        _debug_("Added job %s to the queue" % idnr, 0)
        if now:
            self.queue.startQueue()
        return (True, "EncodingServer::queueIt: OK")
        
    def xmlrpc_getProgress(self):
        _debug_("xmlrpc_getProgress(self)", 2)
        prog = self.queue.getProgress()
        if type(prog) is str:
            return (False, "EncodingServer::getProgress: %s" % prog)
        return (True, jam(prog))
        
    def xmlrpc_startQueue(self):
        _debug_("xmlrpc_startQueue(self)", 2)
        self.queue.startQueue()
        return (True, "EncodingServer::startqueue: OK")
        
    def xmlrpc_listJobs(self):
        _debug_("xmlrpc_listJobs(self)", 2)
        jlist = self.queue.listJobs()
        return (True, jam(jlist))

        
def main():
    global DEBUG
    #check for /tmp/encodingserver and if it doesn't exist make it
    if not (os.path.exists(tmppath) and os.path.isdir(tmppath)):
        os.mkdir(tmppath)
    #chdir to /tmp/encodingserver
    os.chdir(tmppath)
    
    app = Application("EncodingServer")
    if len(sys.argv) >= 2 and sys.argv[1] == "debug":
        es = EncodingServer(True)
        import encodingcore
        encodingcore.DEBUG=True
    else:
        es = EncodingServer()
    _debug_('main: DEBUG=%s' % DEBUG, 0)
    if (DEBUG == 0):
        app.listenTCP(config.ENCODINGSERVER_PORT, server.Site(es, logPath='/dev/null'))
    else:
        app.listenTCP(config.ENCODINGSERVER_PORT, server.Site(es))
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
                _debug_('server problem, sleeping 1 min', 0)
                time.sleep(60)
