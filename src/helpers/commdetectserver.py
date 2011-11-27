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
import logging
logger = logging.getLogger("freevo.helpers.commdetectserver")

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
    """ Commercial detect server class """

    def __init__(self, debug=False, allowNone=False):
        """ Initialise the Commercial Detection Server class """
        logger.log( 9, 'CommDetectServer.__init__(debug=%r, allowNone=%r)', debug, allowNone)
        try:
            xmlrpc.XMLRPC.__init__(self, allowNone)
        except TypeError:
            xmlrpc.XMLRPC.__init__(self)
        self.debug = debug
        self.jobs = {}
        self.queue = CommDetectQueue()
        logger.info("CommDetectServer started...")

    def xmlrpc_echotest(self, blah):
        logger.log( 8, "xmlrpc_echotest(self, blah)")
        return (True, 'CommDetectServer::echotest: %s' % blah)

    def xmlrpc_initCommDetectJob(self, source):
        logger.debug("xmlrpc_initCommDetectJob(self, %s)", source)
        #safety checks
        if not (source):
            return (False, 'CommDetectServer::initCommDetectJob:  no source given')
        idnr = int((time.time() / random.random()) / 100)
        logger.log( 9, "idnr=%s", idnr)
        self.jobs[idnr] = CommDetectJob(source,idnr)
        logger.info("Initialized job %s (idnr : %s)", source, idnr)
        return (True, idnr)

    def xmlrpc_queueIt(self, idnr, now=False):
        logger.log( 8, "xmlrpc_queueIt(self, idnr, now=False)")
        self.queue.addCommDetectJob(self.jobs[idnr])
        del self.jobs[idnr]
        logger.info("Added job %s to the queue", idnr)
        if now:
            self.queue.startQueue()
        return (True, "CommDetectServer::queueIt: OK")

    def xmlrpc_startQueue(self):
        logger.log( 8, "xmlrpc_startQueue(self)")
        self.queue.startQueue()
        return (True, "CommDetectServer::startqueue: OK")

    def xmlrpc_listJobs(self):
        logger.log( 8, "xmlrpc_listJobs(self)")
        jlist = self.queue.listJobs()
        return (True, jam(jlist))


def main(opts, args):
    from twisted.internet import reactor
    global DEBUG
    if not (os.path.exists(tmppath) and os.path.isdir(tmppath)):
        os.mkdir(tmppath)
    os.chdir(tmppath)

    if opts.debug:
        import commdetectcore
        commdetectcore.DEBUG = opts.debug != 0

    logger.info('DEBUG=%s', DEBUG)
    cds = CommDetectServer(debug=opts.debug, allowNone=True)
    reactor.listenTCP(config.COMMDETECTSERVER_PORT, server.Site(cds))
    reactor.run()


if __name__ == '__main__':
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
        parser.description = "start or stop the commercial detection server"
        parser.add_option('-d', '--debug', action='store_true', dest='debug', default=False,
            help='enable debugging')

        opts, args = parser.parse_args()
        return opts, args


    opts, args = parse_options()

    try:
        logger.debug('main() starting')
        main(opts, args)
        logger.debug('main() finished')
    except SystemExit:
        logger.debug('main() stopped')
        pass
    except Exception, why:
        import traceback
        traceback.print_exc()
        logger.warning(why)
