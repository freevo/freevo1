#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# encodingclient.py - A client interface to the Freevo encoding server.
# -----------------------------------------------------------------------
# $Id$
#
# Author: den_RDC
# Notes: parts taken from recordclient
# Todo:
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
                (config.ENCODINGSERVER_IP, config.ENCODINGSERVER_PORT)

server = xmlrpclib.Server(server_string, allow_none=1)
#server = object() - uncomment this and comment the previous line to enable pychecker testing

jam = jellyToXML
unjam = unjellyFromXML

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__revision__ = "$Rev$"
__copyright__ = "Copyright (C) 2004 den_RDC"
__license__ = "GPL"
__doc__="""EncodingClient, an interface to EncodingServer
            This document will try to provide the necessary instructions for developpers
            to use EncodingServer.

            Some information about EncodingServer(and EncodingClient):
            - It is an extensive frontend to mencoder (but extending it beyond mencoder is a
                future possibility.
            - It is geared towards user-friendlyness by automizing and auto-detecting odvious
                or trivial options and settings. Some assuptions are made and some settings are
                not changeable, but where encoding parameter choices are made, quality is preferred
                above speed.
            - It currently only supports DVD/DVD-on-Disc as input formats. This wil change soon.
            - Options and preferences are dynamically generated (this is not 100% true yet) in order
                to give users and frontend developpers an easier job.
            - The encodingsuite is fully network-capable, but not network-aware. This means you can run
                both client and server on different machines, but you have to make sure that the files/paths
                you pass to the server are available from the servers environment.
            - In order te preserve quality, no rescaling is currently done on the video, instead
                a flag is added by mencoder to indicate proper rescaling on playback. Rescaling
                will be introduced in a future version.
            - There is no specefic order in wich you have to call the functions to make and customize an
                encodingjob, except that it is necessary to call setContainer first if you want to
                use another container then "avi".
            - Once the job has been queued, it is impossible to change it's properties anymore.

            The functions in this module have a behaviour similar to Freevo's RecordServer. Each function
            returns a tuple. The first element of this tuple is a boolean value.
            If this value is false, then the function failed to execute somewhere along the way.
            In this case the second tuple contains a string further specifying the error.
            IF the boolean value is true, the function succeeded, and the second carries the return value.
            Depending on the function itself, this can be an object holding specefic values that where queried,
                or a simple string stating everything went OK (usefull for debugging).


"""



def returnFromJelly(status, response):
    """Un-serialize EncodingServer responses"""
    if status:
        return (status, unjam(response))
    else:
        return (status, response)

def connectionTest(teststr='testing'):
    """Test connectivity

    Returns false if the EncodingServer cannot be reached"""

    try:
        (status, response) = server.echotest(teststr)
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def initEncodeJob(source, output, friendlyname="", title=None):
    """Initialize the encodingjob.

    source is the source video you want to have encoded
    output is the name of the resulting encoded file you want
    friendlyname is a "friendly name" to assign to this encoding job
    title is obligatory if you have a dvd/dvd-on-disc, in wich case you need
        to specify a title (integer)

    This function returns an idnr (integer) if succesful

    This call can take some time (10 seconds on average) before returning, because the
    encodingserver analyzes the video during this call."""

    _debug_('initEncodeJob(%s, %s, %s, %s)' % (source, output, friendlyname, title), 0)
    if not (source or output):
        return (False, "EncodingClient: no source and/or output")

    try:
        (status, response) = server.initEncodeJob(source, output, friendlyname, title)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
        return (False, 'EncodingClient: connection error')

    return (status, response)

def getContainerCAP(idnr):
    """Get a list of possible container formats

    This returns a list with plain strings, each identifiyng a container format, like
    Avi, MPEG or OGG. Currently only Avi is available. The strings are user-readable.
    """

    if not idnr:
        return (False, "EncodingClient: no idnr")

    try:
        (status, response) = server.getContainerCAP(idnr)
    except:
        return (False, 'EncodingClient: connection error')

    return returnFromJelly(status, response)

def setContainer(idnr, container):
    """Set a container format

    container is one of the possible container formats. It should be one of the strings
    returned by getContainerCAP.
    """

    if not (idnr or container):
        return (False, "EncodingClient: no idnr and/or container")

    try:
        (status, response) = server.setContainer(idnr, container)
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def getVideoCodecCAP(idnr):
    """Get a list of possible video codecs (depending on the input and container format)

    This returns a list with plain strings, each identifiyng a video codec, like
    MPEG4(divx), Xvid etc. Currently only MPEG4 is available. The strings are user-readable.
    """

    if not idnr:
        return (False, "EncodingClient: no idnr")

    try:
        (status, response) = server.getVideoCodecCAP(idnr)
    except:
        return (False, 'EncodingClient: connection error')

    return returnFromJelly(status, response)

def setVideoCodec(idnr, vcodec, tgtsize, multipass=False, vbitrate=0):
    """Set a video codec

    vcodec is one of the possible video codecs. It should be one of the strings
        returned by getVideoCodecCAP.
    tgtsize is the target size of the encoded file, in megabytes (this includes
        audio data and container format overhead)
    multipass is a boolean. Set this to True if you want multipass encoding (1 audio
        pass, 2 video passes). The default is no multipass (1 audio, 1 video)
    vbitrate is the video bitrate, if it is not 0 then this value is used instead
        of using the tgtsize.
    """

    if not (idnr or vcodec or tgtsize or vbitrate):
        return (False, "EncodingClient: no idnr and/or videocodec and/or targetsize")

    try:
        (status, response) = server.setVideoCodec(idnr, vcodec, tgtsize, multipass, vbitrate)
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def getAudioCodecCAP(idnr):
    """Get a list of possible audio codecs (depending on the input and container format)

    This returns a list with plain strings, each identifiyng a audio codec, like
    MP3, Ogg,  etc. Currently only MP3 is available. The strings are user-readable.
    """

    if not idnr:
        return (False, "EncodingClient: no idnr")

    try:
        (status, response) = server.getAudioCodecCAP(idnr)
    except:
        return (False, 'EncodingClient: connection error')

    return returnFromJelly(status, response)

def setAudioCodec(idnr, acodec, abrate):
    """Set a audio codec

    acodec is one of the possible audio codecs. It should be one of the strings
        returned byt getAudioCodecCAP.
    abrate is the audio bitrate to be set, in kbit/s. Although any integer between 0
        and 320 is valid, it is advisable to take standard encoding bitrates like
        32,64,128,160,192,256 and 320.
    """

    if not (idnr or acodec or abrate):
        return (False, "EncodingClient: no idnr and/or audiocodec and/or audiobitrate")

    try:
        (status, response) = server.setAudioCodec(idnr, acodec, abrate)
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def getVideoFiltersCAP(idnr):
    """Get a dict of possible video filters & processing operations

    This returns a dictionary, with the filter (human-readable string) as keyword, and
    a list of options (also human-readable strings) as possible settings for each filter.
    The first option in the list is the default.
    """

    if not idnr:
        return (False, "EncodingClient: no idnr")

    try:
        (status, response) = server.getVideoFiltersCAP(idnr)
    except:
        return (False, 'EncodingClient: connection error')

    return returnFromJelly(status, response)

def setVideoFilters(idnr, filters):
    """Set a number of possible video filters & processing operations

    filters - a dictionary with filters you want to have enabled and there settings.
    The structure of this dict is almost identical to the dict getVideoFiltersCAP returns,
    except you should replace the list of options with the options you need. The value assigned
    to each keyword is thus a string (wich means you cannot choose more then 1 option/setting) per
    video filter.
    """

    if not (idnr or filters):
        return (False, "EncodingClient: no idnr or filter dictionary")

    try:
        (status, response) = server.setVideoFilters(idnr, jam(filters))
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def queueIt(idnr, now=False):
    """Insert the current job in the encodingqueue
        If now is true, the encoding queue is automatically started
    """

    if not idnr:
        return (False, "EncodingClient: no idnr")

    try:
        (status, response) = server.queueIt(idnr, now)
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def getProgress():
    """Get the progress & pass information of the job currently encoding.

    This call returns False if no job is currently encoding (fx the queue is not active).
    When the queue is active, this call returns a tuple of 4 values:
        (friendlyname, status, perc, timerem)

    friendlyname is the friendlyname you assigned to the encoding job
    status is the current status of the encoding job, represented by an integer
        0 - Not set (this job hasn't started encoding). Never used in this context
        1 - Audio pass in progress
        2 - First (analyzing) video pass (only used in multipass encoding)
        3 - Final video pass
        4 - Postmerge (not used atm). Final merging or similar processing in progress
    perc is the percentage completed of the current pass
    timerem is the estimated time remaining of the current pass, formatted as a
        human-readable string.
    """

    try:
        (status, response) = server.getProgress()
    except:
        return (False, 'EncodingClient: connection error')

    return returnFromJelly(status, response)

def startQueue():
    """Start the encoding queue"""

    try:
        (status, response) = server.startQueue()
    except:
        return (False, 'EncodingClient: connection error')

    return (status, response)

def listJobs():
    """Get a list with all jobs in the encoding queue and their current state

    Returns a list of tuples containing all the current queued jobs. When the queue is
    empty, an empty list is returned.
    Each job in the list is a tuple containing 3 values
        (idnr, friendlyname, status)
    These values have the same meaning as the corresponding values returned by the
        getProgress call"""

    try:
        (status, response) = server.listJobs()
    except:
        return (False, 'EncodingClient: connection error')

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
        print getProgress()

    if function == "runtest":
        #(status, idnr) = initEncodeJob('/storage/video/dvd/BRUCE_ALMIGHTY/', 'bam.avi','lala', 17)
        (status, idnr) = initEncodeJob('/dev/cdrom', '/home/rdc/fogu.avi','lala', 1)
        print "Job has idnr nr : %s" % idnr
        print idnr
        #sleep(5)
        (status, codec) = getVideoCodecCAP(idnr)
        print codec[0]
        print codec[1]
        print setVideoCodec(idnr, codec[1], 1400, True, 0)
        #print setVideoFilters(idnr, {'Denoise' : 'HQ denoise'})
        #sleep(5)
        print queueIt(idnr, True)
        sleep(5)
        print getProgress()
        sleep(5)
        print getProgress()
        sleep(5)
        print getProgress()

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
