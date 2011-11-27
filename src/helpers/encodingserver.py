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
import logging
logger = logging.getLogger("freevo.helpers.encodingserver")

import sys, string, random, time, os, re, pwd, stat, tempfile

import kaa
import kaa.rpc
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


    from optparse import IndentedHelpFormatter, OptionParser

    def parse_options():
        """
        Parse command line options
        """
        import version
        formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
        parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="freevo %prog [--daemon|--stop]",
            version='%prog ' + str(version.version))
        parser.prog = appname
        parser.description = "start or stop the video encoding server"
        parser.add_option('-d', '--debug', action='count', dest='debug', default=0,
            help='set the level of debugging')

        opts, args = parser.parse_args()
        return opts, args


    opts, args = parse_options()


import time, random, sys, os
import logging
import config

from encodingcore import EncodingJob, EncodingQueue, EncodingOptions

__author__ = 'den_RDC (rdc@kokosnoot.com)'
__revision__ = '$Rev$'
__copyright__ = 'Copyright (C) 2004 den_RDC'
__license__ = 'GPL'

DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG


class EncodingServer:
    def __init__(self, debug=False, allowNone=False):
        """ Initialise the EncodingServer class """
        logger.log( 9, 'EncodingServer.__init__(debug=%r, allowNone=%r)', debug, allowNone)
        self.debug = debug
        self.jobs = {}
        self.encodingopts = EncodingOptions()
        self.queue = EncodingQueue()
        logger.info('EncodingServer started...')


    @kaa.rpc.expose('ping')
    def _pingtest(self):
        logger.log( 9, 'pingtest()')
        return True

    @kaa.rpc.expose('getContainerCAP')
    def _getContainerCAP(self):
        """ get the container capabilities """
        return (True, EncodingOptions.getContainerList(self.encodingopts))


    @kaa.rpc.expose('getVideoCodecCAP')
    def _getVideoCodecCAP(self):
        """ get the video capabilities """
        return (True, EncodingOptions.getVideoCodecList(self.encodingopts))


    @kaa.rpc.expose('getAudioCodecCAP')
    def _getAudioCodecCAP(self):
        """ get the audio capabilities """
        return (True, EncodingOptions.getAudioCodecList(self.encodingopts))


    @kaa.rpc.expose('getVideoFiltersCAP')
    def _getVideoFiltersCAP(self):
        """ get the video filter capabilities """
        return (True, EncodingOptions.getVideoFiltersList(self.encodingopts))


    @kaa.rpc.expose('initEncodingJob')
    def _initEncodingJob(self, source, output, friendlyname='', chapter=None, rmsource=False):
        """
        Initialise an encoding job
        @param source: source file to encode
        @param output: output file to encode
        @param friendlyname: encoding job title
        @param chapter: chapter number to encode
        @param rmsource: remove the source after successful encoding
        @returns: tuple of success status and job identifier
        """
        #safety checks
        if not (source or output):
            return (False, '%s.initEncodingJob: no source or output given' % (self.__class__,))

        # generate a 'random' idnr based on the time in p2.3, int() can return long
        # int's, which is fine, except it makes XMLRPC fail somewhere along the way so we
        # devide or random number by 100 :)
        idnr = int((time.time() / random.random()) / 100)
        logger.log( 9, 'idnr=%s', idnr)
        self.jobs[idnr] = EncodingJob(source, output, friendlyname, idnr, chapter, rmsource)
        logger.info('Initialized job %s (idnr: %s)', friendlyname, idnr)
        if self.jobs[idnr].failed:
            return (False, 0)
        return (True, idnr)


    @kaa.rpc.expose('waitCropDetect')
    def _waitCropDetect(self, idnr):
        #wait for the analyzing to end
        status = self.jobs[idnr]._cropdetect()
        while not self.jobs[idnr].finishedanalyze:
            time.sleep(0.1)
        if self.jobs[idnr].finishedanalyze and self.jobs[idnr].failed:
            logger.debug('Crop detection failed')
            return (False, 'Crop detection failed')
        return (True, 'Ended successfully crop detection.')


    @kaa.rpc.expose('setContainer')
    def _setContainer(self, idnr, container):
        """ set the container """
        status = self.jobs[idnr].setContainer(container)
        if not status:
            return (True, 'EncodingServer::setContainer: OK')
        return (False, 'EncodingServer::setContainer: %s' % status)


    @kaa.rpc.expose('setVideoCodec')
    def _setVideoCodec(self, idnr, vcodec, tgtsize, multipass=False, vbitrate=0, altprofile=None):
        """ set the video codec """
        logger.debug('_setVideoCodec(idnr=%r, vcodec=%r, tgtsize=%r, multipass=%r, vbitrate==%r)', idnr, vcodec, tgtsize, multipass, vbitrate)

        if not (vcodec or (tgtsize and vbitrate)):
            return (False, 'EncodingServer::setVideoCodec: no codec or target size given')

        status = self.jobs[idnr].setVideoCodec(vcodec, tgtsize, multipass, vbitrate, altprofile)
        if not status:
            return (True, 'EncodingServer::setVideoCodec: OK')
        return (False, 'EncodingServer::setVideoCodec: %s' % status)


    @kaa.rpc.expose('setAudioCodec')
    def _setAudioCodec(self, idnr, acodec, abrate):
        """ set the audio codec """
        logger.log( 9, '_setAudioCodec(idnr=%r, acodec=%r, abrate=%r)', idnr, acodec, abrate)
        if not (acodec or abrate):
            return (False, 'EncodingServer::setAudioCodec: no codec or bit rate given')

        status = self.jobs[idnr].setAudioCodec(acodec, abrate)
        if not status:
            return (True, 'EncodingServer::setAudioCodec: OK')
        return (False, 'EncodingServer::setAudioCodec: %s' % status)


    @kaa.rpc.expose('setVideoFilters')
    def _setVideoFilters(self, idnr, filters):
        """ set the video filter list """
        if not filters:
            return (False, 'EncodingServer::setVideoFilters: no filter given')

        status = self.jobs[idnr].setVideoFilters(filters)
        if not status:
            return (True, 'EncodingServer::setVideoFilters: OK')
        return (False, 'EncodingServer::setVideoFilters: %s' % status)


    @kaa.rpc.expose('setTimeslice')
    def _setTimeslice(self,idnr,timeslice):
        logger.log( 8, '_setTimeslice(self, %s, %s)', idnr, timeslice)
        status = self.jobs[idnr].setTimeslice(timeslice)
        if not status:
            return (True, 'EncodingServer::setTimeslice: OK')
        return (False, 'EncodingServer::setTimeslice: %s' % status)


    @kaa.rpc.expose('setVideoRes')
    def _setVideoRes(self, idnr, videores ):
        """ set the video resolution """
        logger.log( 9, '_setAudioCodec(idnr=%r, videores=%r)', idnr, videores)
        if not (videores):
            return (False, 'EncodingServer::setVideoRes: no video resolution given')

        status = self.jobs[idnr].setVideoRes( videores)
        if not status:
            return (True, 'EncodingServer::setVideoRes: OK')
        return (False, 'EncodingServer::setVideoRes: %s' % status)


    @kaa.rpc.expose('setNumThreads')
    def _setNumThreads(self, idnr, numthreads ):
        """ set the number of threads """
        logger.log( 9, '_setAudioCodec(idnr=%r, numthreads=%r)', idnr, numthreads)
        #safety checks
        if not (numthreads):
            return (False, 'EncodingServer::setNumThreads: no number given')

        status = self.jobs[idnr].setNumThreads( numthreads)
        if not status:
            return (True, 'EncodingServer::setNumThreads: OK')
        return (False, 'EncodingServer::setNumThreads: %s' % status)


    @kaa.rpc.expose('listJobs')
    def _listJobs(self):
        """ List the current jobs """
        logger.log( 9, '_listJobs()')
        jlist = self.queue.listJobs()
        return (True, jlist)


    @kaa.rpc.expose('queueIt')
    def _queueIt(self, idnr, now=False):
        """ queue a job to run """
        logger.log( 9, '_queueIt(idnr=%r, now=%r)', idnr, now)
        self.queue.addEncodingJob(self.jobs[idnr])
        del self.jobs[idnr]
        logger.info('Added job %s to the queue', idnr)
        if now:
            self.queue.startQueue()
        return (True, 'EncodingServer::queueIt: OK')


    @kaa.rpc.expose('startQueue')
    def _startQueue(self):
        """ start the job queue """
        logger.log( 9, '_startQueue()')
        self.queue.startQueue()
        return (True, 'EncodingServer::startqueue: OK')


    @kaa.rpc.expose('getProgress')
    def _getProgress(self):
        """ get the progress status of the current job """
        logger.log( 9, '_getProgress()')
        prog = self.queue.getProgress()
        if type(prog) is str:
            return (False, 'EncodingServer::getProgress: %s' % prog)
        return (True, prog)


def main():
    """ The main entry point for the server """
    logger.log( 9, 'main()')
    global DEBUG
    tmppath = tempfile.mkdtemp(prefix = 'encodeserver-')
    os.chdir(tmppath)

    if opts.debug:
        import encodingcore
        encodingcore.DEBUG = opts.debug != 0
    logger.info('main: DEBUG=%s', DEBUG)
    socket = ('', config.ENCODINGSERVER_PORT)
    secret = config.ENCODINGSERVER_SECRET
    logger.debug('socket=%r, secret=%r', socket, secret)

    encodingserver = EncodingServer(debug=opts.debug, allowNone=True)
    try:
        rpc = kaa.rpc.Server(socket, secret)
    except Exception:
        raise

    rpc.register(encodingserver)

    logger.debug('kaa.main starting')
    kaa.main.run()
    logger.debug('kaa.main finished')


if __name__ == '__main__':
    try:
        logger.debug('main() starting')
        main()
        logger.debug('main() finished')
    except SystemExit:
        logger.debug('main() stopped')
        pass
    except Exception, why:
        import traceback
        traceback.print_exc()
        logger.warning(why)
