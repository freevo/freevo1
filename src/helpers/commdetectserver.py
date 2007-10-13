#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# CommDetectServer.py, part of Commercial Detection Server - for use with Freevo
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

from commdetectcore import CommDetectJob, CommDetectQueue

DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG

logfile = '%s/%s-%s.log' % (config.FREEVO_LOGDIR, appname, os.getuid())
log.startLogging(open(logfile, 'a'))

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            log.debug(String(text))
        except:
            print String(text)

tmppath = '/tmp/commdetectserver'

jam = jellyToXML
unjam = unjellyFromXML

class CommDetectServer(xmlrpc.XMLRPC):
    def __init__(self, debug=False):
        self.jobs = {}
        self.queue = CommDetectQueue(log, DEBUG)
        _debug_("CommDetectServer started...", config.DINFO)

    def xmlrpc_echotest(self, blah):
        _debug_("xmlrpc_echotest(self, blah)", 3)
        return (True, 'CommDetectServer::echotest: %s' % blah)

    def xmlrpc_initCommDetectJob(self, source):
        _debug_("xmlrpc_initCommDetectJob(self, %s)" % (source))
        #safety checks
        if not (source):
            return (False, 'CommDetectServer::initCommDetectJob:  no source given')
        idnr = int((time.time() / random.random()) / 100)
        _debug_("idnr=%s" % (idnr), 2)
        self.jobs[idnr] = CommDetectJob(source,idnr)
        _debug_("Initialized job %s (idnr : %s)" % (source,idnr), config.DINFO)
        return (True, idnr)

    def xmlrpc_queueIt(self, idnr, now=False):
        _debug_("xmlrpc_queueIt(self, idnr, now=False)", 3)
        self.queue.addCommDetectJob(self.jobs[idnr])
        del self.jobs[idnr]
        _debug_("Added job %s to the queue" % idnr, config.DINFO)
        if now:
            self.queue.startQueue()
        return (True, "CommDetectServer::queueIt: OK")

    def xmlrpc_startQueue(self):
        _debug_("xmlrpc_startQueue(self)", 3)
        self.queue.startQueue()
        return (True, "CommDetectServer::startqueue: OK")

    def xmlrpc_listJobs(self):
        _debug_("xmlrpc_listJobs(self)", 3)
        jlist = self.queue.listJobs()
        return (True, jam(jlist))

def main():
    global DEBUG
    if not (os.path.exists(tmppath) and os.path.isdir(tmppath)):
        os.mkdir(tmppath)
    os.chdir(tmppath)
    app = Application("CommDetectServer")
    if len(sys.argv) >= 2 and sys.argv[1] == "debug":
        es = CommDetectServer(True)
        import commdetectcore
        commdetectcore.DEBUG=True
    else:
        es = CommDetectServer()
    _debug_('main: DEBUG=%s' % DEBUG, config.DINFO)
    if (DEBUG == 0):
        app.listenTCP(config.COMMDETECTSERVER_PORT, server.Site(es, logPath='/dev/null'))
    else:
        app.listenTCP(config.COMMDETECTSERVER_PORT, server.Site(es))
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
                _debug_('server problem, sleeping 1 min', config.DINFO)
                time.sleep(60)
