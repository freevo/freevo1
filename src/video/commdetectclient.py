#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# commdetectclient.py - A client interface to the commercial detecting server.
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

import xmlrpclib, sys
from util.marmalade import jellyToXML, unjellyFromXML
import config


server_string = 'http://%s:%s/' % \
                (config.COMMDETECTSERVER_IP, config.COMMDETECTSERVER_PORT)

server = xmlrpclib.Server(server_string, allow_none=1)
#server = object() - uncomment this and comment the previous line to enable pychecker testing

jam = jellyToXML
unjam = unjellyFromXML

def returnFromJelly(status, response):
    """Un-serialize CommDetectServer responses"""
    if status:
        return (status, unjam(response))
    else:
        return (status, response)

def connectionTest(teststr='testing'):
    """
    Test connectivity
    Returns false if the CommDetectServer cannot be reached
    """
    try:
        (status, response) = server.echotest(teststr)
    except:
        return (False, 'CommDetectClient: connection error')
    return (status, response)

def initCommDetectJob(source):
    """Initialize the commdetectjob."""
    _debug_('initCommDetectJob(%s)' % (source))
    if not (source):
        return (False, "CommDetectClient: no source")
    try:
        (status, response) = server.initCommDetectJob(source)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
        return (False, 'CommDetectClient: connection error')
    return (status, response)

def queueIt(idnr, now=False):
    """
    Insert the current job in the commdetectqueue
        If now is true, the commdetect queue is automatically started
    """
    if not idnr:
        return (False, "CommDetectClient: no idnr")
    try:
        (status, response) = server.queueIt(idnr, now)
    except:
        return (False, 'CommDetectClient: connection error')
    return (status, response)

def startQueue():
    """Start the commdetect queue"""
    try:
        (status, response) = server.startQueue()
    except:
        return (False, 'CommDetectClient: connection error')

    return (status, response)

def listJobs():
    """
    Get a list with all jobs in the commdetect queue and their current state
    """
    try:
        (status, response) = server.listJobs()
    except:
        return (False, 'CommDetectClient: connection error')
    return returnFromJelly(status, response)

if __name__ == '__main__':
    if len(sys.argv) >= 2:
        function = sys.argv[1]
    else:
        function = 'none'

    from time import sleep

    if function == "test":
        (result, response) = connectionTest('connection test')
        print 'result: %s, response: %s ' % (result, response)
        print listJobs()

    if function == "runtest":
        (status, idnr) = initCommDetectJob('/opt/media/tv/01-09_21_00_Dirty_Jobs_-_Bug_Breeder.mpeg')
        print "Job has idnr nr : %s" % idnr
        print idnr
        sleep(5)
        print queueIt(idnr, True)

'''
To run this as standalone use the following before running python v4l2.py
pythonversion=$(python -V 2>&1 | cut -d" " -f2 | cut -d"." -f1-2)
export PYTHONPATH=/usr/lib/python${pythonversion}/site-packages/freevo
export FREEVO_SHARE=/usr/share/freevo
export FREEVO_CONFIG=/usr/share/freevo/freevo_config.py
export FREEVO_CONTRIB=/usr/share/freevo/contrib
export RUNAPP=""

python encodingclient.py test
'''
