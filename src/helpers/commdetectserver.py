# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Commercial Detection Server - for use with Freevo
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

from twisted.web import xmlrpc, server, sux
from twisted.internet import reactor
from util.marmalade import jellyToXML, unjellyFromXML
import time, random, sys, os
import logging
import config

from commdetectcore import CommDetectJob, CommDetectQueue

DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG

tmppath = '/tmp/commdetectserver'

jam = jellyToXML
unjam = unjellyFromXML

class CommDetectServer(xmlrpc.XMLRPC):
    def __init__(self, debug=False):
        self.jobs = {}
        self.queue = CommDetectQueue()
        _debug_("CommDetectServer started...", DINFO)

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
        _debug_("Initialized job %s (idnr : %s)" % (source,idnr), DINFO)
        return (True, idnr)

    def xmlrpc_queueIt(self, idnr, now=False):
        _debug_("xmlrpc_queueIt(self, idnr, now=False)", 3)
        self.queue.addCommDetectJob(self.jobs[idnr])
        del self.jobs[idnr]
        _debug_("Added job %s to the queue" % idnr, DINFO)
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
    _debug_('DEBUG=%s' % DEBUG, DINFO)
    reactor.listenTCP(config.COMMDETECTSERVER_PORT, server.Site(es))
    reactor.run()

if __name__ == '__main__':
    main()
