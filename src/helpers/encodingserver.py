# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# EncodingServer daemon, manages the encoding queue
# -----------------------------------------------------------------------
# $Id$
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

import sys, string, random, time, os, re, pwd, stat, tempfile
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
from twisted.internet import reactor
from util.marmalade import jellyToXML, unjellyFromXML
import time, random, sys, os
import logging
import config

from encodingcore import EncodingJob, EncodingQueue, EncodingOptions

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__revision__ = "$Rev$"
__copyright__ = "Copyright (C) 2004 den_RDC"
__license__ = "GPL"

DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG

jam = jellyToXML
unjam = unjellyFromXML


class EncodingServer(xmlrpc.XMLRPC):

    def __init__(self, debug=False, allowNone=False):
        """ Initialise the EncodingServer class """
        _debug_('EncodingServer.__init__(debug=%r, allowNone=%r)' % (debug, allowNone), 2)
        try:
            xmlrpc.XMLRPC.__init__(self, allowNone)
        except TypeError:
            xmlrpc.XMLRPC.__init__(self)
        self.debug = debug
        self.jobs = {}
        self.encodingopts = EncodingOptions()
        self.queue = EncodingQueue()
        _debug_("EncodingServer started...", DINFO)

    def xmlrpc_echotest(self, blah):
        """ Using Twisted check the connection """
        _debug_('xmlrpc_echotest(blah=%r)' % (blah), 2)
        return (True, 'EncodingServer::echotest: %s' % blah)

    def xmlrpc_initEncodeJob(self, source, output, friendlyname="", chapter=None):
        """ Using Twisted initialise an encoding job """
        _debug_('xmlrpc_initEncodeJob(source=%r, output=%r, friendlyname=%r, chapter=%r)' % \
            (source, output, friendlyname, chapter), 1)
        #safety checks
        if not (source or output):
            return (False, 'EncodingServer::initEncodeJob:  no source or output given')

        # generate a "random" idnr based on the time in p2.3, int() can return long
        # int's, which is fine, except it makes XMLRPC fail somewhere along the way so we
        # devide or random number by 100 :)
        idnr = int((time.time() / random.random()) / 100)
        _debug_("idnr=%s" % (idnr), 2)
        self.jobs[idnr] = EncodingJob(source, output, friendlyname, idnr, chapter)

        #wait for the analyzing to end
        while not self.jobs[idnr].finishedanalyze:
            time.sleep(0.1)
        if self.jobs[idnr].finishedanalyze and self.jobs[idnr].failed:
            _debug_('Analysis failed')
            return (False,10)

        _debug_("Initialized job %s (idnr : %s)" % (friendlyname, idnr), DINFO)

        return (True, idnr)

    def xmlrpc_getContainerCAP(self):
        """ Using Twisted get the container capabilities """
        _debug_('xmlrpc_getContainerCAP()' , 2)
        return EncodingOptions.getContainerList( self.encodingopts)

    def xmlrpc_setContainer(self, idnr, container):
        """ Using Twisted set the container """
        _debug_('xmlrpc_setContainer(idnr=%r, container=%r)' % (idnr, container), 2)
        status = self.jobs[idnr].setContainer(container)

        if not status:
            return (True, "EncodingServer::setContainer: OK")
        else:
            return (False, "EncodingServer::setContainer: %s" % status)

    def xmlrpc_getVideoCodecCAP(self):
        """ Using Twisted get the video capabilities """
        _debug_('xmlrpc_getVideoCodecCAP()', 2)
        return EncodingOptions.getVideoCodecList(self.encodingopts)

    def xmlrpc_setVideoCodec(self, idnr, vcodec, tgtsize, multipass=False, vbitrate=0, altprofile=None):
        """ Using Twisted set the video codec """
        _debug_('xmlrpc_setVideoCodec(idnr=%r, vcodec=%r, tgtsize=%r, multipass=%r, vbitrate==%r)' % \
            (idnr, vcodec, tgtsize, multipass, vbitrate), 1)
        #safety checks
        if not (vcodec or (tgtsize and vbitrate)):
            return (False, 'EncodingServer::setVideoCodec:  no codec or target size given')

        status = self.jobs[idnr].setVideoCodec(vcodec, tgtsize, multipass, vbitrate, altprofile)

        if not status:
            return (True, "EncodingServer::setVideoCodec: OK")
        else:
            return (False, "EncodingServer::setVideoCodec: %s" % status)

    def xmlrpc_getAudioCodecCAP(self):
        """ Using Twisted get the audio capabilities """
        _debug_('xmlrpc_getAudioCodecCAP()', 2)
        return EncodingOptions.getAudioCodecList(self.encodingopts)

    def xmlrpc_setAudioCodec(self, idnr, acodec, abrate):
        """ Using Twisted set the audio codec """
        _debug_('xmlrpc_setAudioCodec(idnr=%r, acodec=%r, abrate=%r)' % (idnr, acodec, abrate), 2)
        #safety checks
        if not (acodec or abrate):
            return (False, 'EncodingServer::setAudioCodec:  no codec or bitrate given')

        status = self.jobs[idnr].setAudioCodec(acodec, abrate)

        if not status:
            return (True, "EncodingServer::setAudioCodec: OK")
        else:
            return (False, "EncodingServer::setAudioCodec: %s" % status)


    def xmlrpc_setVideoRes(self, idnr, videores ):
        """ Using Twisted set the video resolution """
        _debug_('xmlrpc_setAudioCodec(idnr=%r, videores=%r)' % (idnr, videores ), 2)
        #safety checks
        if not (videores):
            return (False, 'EncodingServer::setVideoRes:  no video resolution given')

        status = self.jobs[idnr].setVideoRes( videores)

        if not status:
            return (True, "EncodingServer::setVideoRes: OK")
        else:
            return (False, "EncodingServer::setVideoRes: %s" % status)


    def xmlrpc_setNumThreads(self, idnr, numthreads ):
        """ Using Twisted set the number of threads """
        _debug_('xmlrpc_setAudioCodec(idnr=%r, numthreads=%r)' % (idnr, numthreads ), 2)
        #safety checks
        if not (numthreads):
            return (False, 'EncodingServer::setNumThreads:  no number given')

        status = self.jobs[idnr].setNumThreads( numthreads)

        if not status:
            return (True, "EncodingServer::setNumThreads: OK")
        else:
            return (False, "EncodingServer::setNumThreads: %s" % status)


    def xmlrpc_getVideoFiltersCAP(self):
        """ Using Twisted get the video filter capabilities """
        _debug_('xmlrpc_getVideoFiltersCAP()', 2)
        return EncodingOptions.getVideoFiltersList(self.encodingopts)


    def xmlrpc_setVideoFilters(self, idnr, filters):
        """ Using Twisted set the video filter list """
        _debug_('xmlrpc_setVideoFilters(idnr, filters)', 2)
        #safety checks
        if not filters:
            return (False, 'EncodingServer::setAudioCodec:  no codec or bitrate given')

        status = self.jobs[idnr].setVideoFilters(unjam(filters))

        if not status:
            return (True, "EncodingServer::setVideoFilters: OK")
        else:
            return (False, "EncodingServer::setVideoFilters: %s" % status)

    def xmlrpc_queueIt(self, idnr, now=False):
        """ Using Twisted queue a job to run """
        _debug_('xmlrpc_queueIt(idnr=%r, now=%r)' % (idnr, now), 2)
        self.queue.addEncodingJob(self.jobs[idnr])
        del self.jobs[idnr]
        _debug_("Added job %s to the queue" % idnr, DINFO)
        if now:
            self.queue.startQueue()
        return (True, "EncodingServer::queueIt: OK")

    def xmlrpc_getProgress(self):
        """ Using Twisted get the progress status of the current job """
        _debug_('xmlrpc_getProgress()', 2)
        prog = self.queue.getProgress()
        if type(prog) is str:
            return (False, "EncodingServer::getProgress: %s" % prog)
        return (True, jam(prog))

    def xmlrpc_startQueue(self):
        """ Using Twisted start the job queue """
        _debug_('xmlrpc_startQueue()', 2)
        self.queue.startQueue()
        return (True, "EncodingServer::startqueue: OK")

    def xmlrpc_listJobs(self):
        """ List the current jobs """
        _debug_('xmlrpc_listJobs()', 2)
        jlist = self.queue.listJobs()
        return (True, jam(jlist))


def main():
    """ The main entry point for the server """
    _debug_('main()', 2)
    global DEBUG
    tmppath = tempfile.mkdtemp(prefix = 'encodeserver')
    os.chdir(tmppath)

    debug = False
    if len(sys.argv) >= 2 and sys.argv[1] == "debug":
        debug = True
        import encodingcore
        encodingcore.DEBUG = debug
    _debug_('main: DEBUG=%s' % DEBUG, DINFO)
    es = EncodingServer(debug=debug, allowNone=True)
    reactor.listenTCP(config.ENCODINGSERVER_PORT, server.Site(es))
    reactor.run()


if __name__ == '__main__':
    main()
