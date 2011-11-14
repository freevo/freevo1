# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A client interface to the Freevo encoding server.
# -----------------------------------------------------------------------
# $Id$
#
# Author: den_RDC
# Notes: parts taken from encodingclient
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

"""
A client interface to the Freevo encoding server.
"""
import logging
logger = logging.getLogger("freevo.video.encodingclient")

import sys

import kaa
import kaa.rpc

import config

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__revision__ = "$Rev$"
__copyright__ = "Copyright (C) 2004 den_RDC"
__license__ = "GPL"
__doc__="""EncodingClient, an interface to EncodingServer
            This document will try to provide the necessary instructions for developpers
            to use EncodingServer.

            Some information about EncodingServer(and EncodingClient):
            - It is an extensive front-end to mencoder (but extending it beyond mencoder is a
                future possibility.
            - It is geared towards user-friendliness by automatizing and auto-detecting obvious
                or trivial options and settings. Some assumptions are made and some settings are
                not changeable, but where encoding parameter choices are made, quality is preferred
                above speed.
            - Options and preferences are dynamically generated (this is not 100% true yet) in order
                to give users and front-end developers an easier job.
            - The encoding suite is fully network-capable, but not network-aware. This means you can run
                both client and server on different machines, but you have to make sure that the files/paths
                you pass to the server are available from the servers environment.
            - In order te preserve quality, no rescaling is currently done on the video, instead
                a flag is added by mencoder to indicate proper rescaling on playback. Rescaling
                will be introduced in a future version.
            - There is no specific order in which you have to call the functions to make and customize an
                encodingjob, except that it is necessary to call setContainer first if you want to
                use another container then "avi".
            - Once the job has been queued, it is impossible to change it's properties any more.

            The functions in this module have a behaviour similar to Freevo's RecordServer. Each function
            returns a tuple. The first element of this tuple is a boolean value.
            If this value is false, then the function failed to execute somewhere along the way.
            In this case the second tuple contains a string further specifying the error.
            IF the boolean value is true, the function succeeded, and the second carries the return value.
            Depending on the function itself, this can be an object holding specific values that where queried,
                or a simple string stating everything went OK (useful for debugging).


"""

class EncodingClientActions:
    """
    encodingserver access class using kaa.rpc
    """
    encodingserverdown = _('Encoding server is not available')

    def __init__(self):
        """ """
        _debug_('%s.__init__()' % (self.__class__,), 2)
        socket = (config.ENCODINGSERVER_IP, config.ENCODINGSERVER_PORT)
        self.channel = kaa.rpc.connect(socket, config.ENCODINGSERVER_SECRET, retry=1)
        #kaa.inprogress(self.channel).wait()

    #--------------------------------------------------------------------------------
    # encoding server calls using a coroutine and the wait method
    #--------------------------------------------------------------------------------

    def _encodingserver_rpc(self, cmd, *args, **kwargs):
        """ call the encoding server command using kaa rpc """
        _debug_('_encodingserver_rpc(cmd=%r, args=%r, kwargs=%r)' % (cmd, args, kwargs), 2)
        if self.channel.status != kaa.rpc.CONNECTED:
            _debug_('encoding server is down', DINFO)
            return None
        return self.channel.rpc(cmd, *args, **kwargs)


    def _encodingserver_call(self, cmd, *args, **kwargs):
        _debug_('_encodingserver_call(cmd=%s)' % (cmd,), 2)
        inprogress = self._encodingserver_rpc(cmd, *args, **kwargs)
        if inprogress is None:
            return (None, EncodingClientActions.encodingserverdown)
        inprogress.wait()
        result = inprogress.result
        _debug_('%s.result=%r' % (cmd, result), 3)
        return result


    def ping(self):
        """ Ping the recordserver to see if it is running """
        _debug_('ping', 2)
        inprogress = self._encodingserver_rpc('ping')
        if inprogress is None:
            return False
        inprogress.wait()
        result = inprogress.result
        _debug_('ping.result=%r' % (result,), 3)
        return result


    def getContainerCAP(self):
        """
        Get the container capabilities
        """
        return self._encodingserver_call('getContainerCAP')


    def getVideoCodecCAP(self):
        """
        Get a list of possible video codecs (depending on the input and container format)

        This returns a list with plain strings, each identifying a video codec, like
        MPEG4(divx), Xvid etc. Currently only MPEG4 is available. The strings are user-readable.
        """
        return self._encodingserver_call('getVideoCodecCAP')


    def getAudioCodecCAP(self):
        """
        Get a list of possible audio codecs (depending on the input and container format)

        This returns a list with plain strings, each identifying a audio codec, like
        MP3, Ogg, etc. Currently only MP3 is available. The strings are user-readable.
        """
        return self._encodingserver_call('getAudioCodecCAP')


    def getVideoFiltersCAP(self):
        """
        Get a dict of possible video filters & processing operations

        This returns a dictionary, with the filter (human-readable string) as
        keyword, and a list of options (also human-readable strings) as
        possible settings for each filter.  The first option in the list is the
        default.
        """
        return self._encodingserver_call('getVideoFiltersCAP')


    def initEncodingJob(self, source, output, friendlyname="", title=None, rmsource=False):
        """Initialize the encodingjob.

        This function returns an idnr (integer).

        This call can take some time (10 seconds on average) before returning, because the
        encodingserver analyzes the video during this call.

        @param source: is the source video you want to have encoded
        @param output: is the name of the resulting encoded file you want
        @param friendlyname: is a "friendly name" to assign to this encoding job
        @param title: is obligatory if you have a dvd/dvd-on-disc, in which case you need
            to specify a title (integer)
        @param rmsource: sets whether to remove the source video on completion (boolean)
        """
        return self._encodingserver_call('initEncodingJob', source, output, friendlyname, title, rmsource)


    def setContainer(self, idnr, container):
        """Set a container format

        container is one of the possible container formats. It should be one of the strings
        returned by getContainerCAP.
        """
        if not (idnr or container):
            return (False, "EncodingClient: no idnr or container")
        return self._encodingserver_call('setContainer', idnr, container)


    def waitCropDetect(self, idnr):
        """Uses MPlayer to detect video cropping

        This call can take some time (10 seconds on average) before returning, because the
        encodingserver analyzes the video during this call.
        """
        if not idnr :
            return (False, "EncodingClient: no idnr or container")
        return self._encodingserver_call('waitCropDetect', idnr)


    def setVideoCodec(self, idnr, vcodec, tgtsize, multipass=False, vbitrate=0, altprofile=None):
        """Set a video codec

        @param vcodec: is one of the possible video codecs. It should be one of the strings
            returned by getVideoCodecCAP.
        @param tgtsize: is the target size of the encoded file, in megabytes (this includes
            audio data and container format overhead)
        @param multipass: is a boolean. Set this to True if you want multi-pass encoding
            (1 pass, 2 video passes). The default is no multi-pass (1 video)
        @param vbitrate: is the video bitrate, if it is not 0 then this value is used instead
            of using the tgtsize.
        """
        if not (idnr or vcodec or tgtsize or vbitrate):
            return (False, "EncodingClient: no idnr and/or videocodec and/or targetsize")
        return self._encodingserver_call('setVideoCodec', idnr, vcodec, tgtsize, multipass, vbitrate, altprofile)


    def setAudioCodec(self, idnr, acodec, abrate):
        """Set a audio codec

        @param acodec: is one of the possible audio codecs. It should be one of the strings
            returned byt getAudioCodecCAP.

        @param abrate: is the audio bitrate to be set, in kbit/s. Although any integer
            between 0 and 320 is valid, it is advisable to take standard encoding bitrates
            like 32, 64, 128, 160, 192, 256 and 320.
        """
        if not (idnr or acodec or abrate):
            return (False, "EncodingClient: no idnr or audiocodec or audiobitrate")
        return self._encodingserver_call('setAudioCodec', idnr, acodec, abrate)


    def setVideoRes(self, idnr, videores):
        """Set the video resolution

        @param vidoeres: is a string in the form of x:y
        """
        if not (idnr or videores):
            return (False, "EncodingClient: no idnr or videores")
        return self._encodingserver_call('setVideoRes', idnr, videores)


    def setVideoFilters(idnr, filters):
        """Set a number of possible video filters & processing operations

        filters - a dictionary with filters you want to have enabled and there settings.
        The structure of this dict is almost identical to the dict getVideoFiltersCAP returns,
        except you should replace the list of options with the options you need. The value assigned
        to each keyword is thus a string (which means you cannot choose more then 1 option/setting) per
        video filter.
        """
        if not (idnr or filters):
            return (False, "EncodingClient: no idnr or filter dictionary")

        try:
            (status, response) = server.setVideoFilters(idnr, filters)
        except:
            return (False, 'EncodingClient: connection error')

        return (status, response)


    def setNumThreads(self, idnr, numthreads):
        """Set the number of encoder threads

        @param idnr: job number
        @param numthreads: is a string value from 1-8
        """
        if not (idnr or numthreads):
            return (False, "EncodingClient: no idnr or no numthreads")
        return self._encodingserver_call('setNumThreads', idnr, numthreads)


    def setTimeslice(self, idnr, timeslice):
        """
        Set the start and end position of the encoding

        @param idnr: job number
        @param timeslice: tuple of the start and the end position
        """
        return self._encodingserver_call('setTimeslice', idnr, timeslice)


    def queueIt(self, idnr, now=False):
        """Insert the current job in the encodingqueue
            If now is true, the encoding queue is automatically started
        """
        if not idnr:
            return (False, "EncodingClient: no idnr")
        return self._encodingserver_call('queueIt', idnr, now)


    def getProgress(self):
        """Get the progress & pass information of the job currently encoding.

        This call returns False if no job is currently encoding (fx the queue is not active).

        friendlyname is the friendlyname you assigned to the encoding job
        status is the current status of the encoding job, represented by an integer
            - 0 Not set (this job hasn't started encoding). Never used in this context
            - 1 Audio pass in progress
            - 2 First (analyzing) video pass (only used in multi-pass encoding)
            - 3 Final video pass
            - 4 Postmerge (not used atm). Final merging or similar processing in progress

        perc is the percentage completed of the current pass, timerem is the estimated
        time remaining of the current pass, formatted as a human-readable string.

        @returns: When the queue is active, this call returns a tuple of 4 values:
            (friendlyname, status, perc, timerem)
        """
        return self._encodingserver_call('getProgress')


    def startQueue(self):
        """
        Start the encoding queue
        """
        return self._encodingserver_call('startQueue')


    def listJobs(self):
        """
        Get a list with all jobs in the encoding queue and their current state

        @returns: a list of tuples containing all the current queued jobs. When the
            queue is empty, an empty list is returned.  Each job in the list is a tuple
            containing 3 values (idnr, friendlyname, status) These values have the same
            meaning as the corresponding values returned by the getProgress call
        """
        return self._encodingserver_call('listJobs')



if __name__ == '__main__':
    if len(sys.argv) >= 2:
        function = sys.argv[1]
    else:
        function = 'none'

    from time import sleep

    idnr = None
    startclock = time.clock()
    es = EncodingClientActions()
    print time.clock() - startclock
    kaa.inprogress(es.channel).wait()
    print time.clock() - startclock
    if function == 'test2':
        result = es.ping()
        print 'ping:', result
        if not result:
            raise EncodingClientActions.encodingserverdown
        result = es.getContainerCAP()
        print 'getContainerCAP:', result
        container = result[1][1]
        result = es.getVideoCodecCAP()
        print 'getVideoCodecCAP:', result
        video_codec = result[1][3]
        result = es.getAudioCodecCAP()
        print 'getAudioCodecCAP:', result
        audio_codec = result[1][3]
        result = es.getVideoFiltersCAP()
        print 'getVideoFiltersCAP:', result
        source = '/freevo/video/movies/04_S\'_Häsli_goht_velore.mpg'
        result = es.initEncodingJob(source, 'movie.avi', 'MyMovie')
        print 'initEncodingJob:', result
        if not result[0]:
            raise result[1]
        idnr = result[1]
        print 'video_codec:', video_codec, 'audio_codec:', audio_codec
        result = es.setVideoCodec(idnr, video_codec, 1400, True, 0)
        print 'setVideoCodec:', result
        result = es.queueIt(idnr, True)
        print 'queueIt:', result
        sleep(5)
        print es.getProgress()

    elif function == "jobs":
        print es.listJobs()

    elif function == "progress":
        print es.getProgress()

    elif function == "start":
        print es.startQueue()

    elif function == "test":
        result = es.ping()
        print 'result: %s' % (result)
        print es.getProgress()

    elif function == "runtest":
        source = '/freevo/video/movies/04_S\'_Häsli_goht_velore.mpg'
        result = es.initEncodingJob(source, 'movie.avi', 'MyMovie')
        print 'initEncodingJob:', result
        if not result[0]:
            raise result[1]
        idnr = result[1]
        print "Job has idnr num: %s" % idnr
        #sleep(5)
        (status, codec) = es.getVideoCodecCAP()
        print codec[0]
        print codec[1]
        print es.setVideoCodec(idnr, codec[1], 1400, True, 0)
        #print setVideoFilters(idnr, {'Denoise': 'HQ denoise'})
        #sleep(5)
        print es.queueIt(idnr, True)
        sleep(5)
        print es.getProgress()
        sleep(5)
        print es.getProgress()
        sleep(5)
        print es.getProgress()

    else:
        print 'function %s not defined' % (function,)

"""
To run this as standalone use the following before running python v4l2.py
pythonversion=$(python -V 2>&1 | cut -d" " -f2 | cut -d"." -f1-2)
export PYTHONPATH=/usr/lib/python${pythonversion}/site-packages/freevo
export FREEVO_SHARE=/usr/share/freevo
export FREEVO_CONFIG=/usr/share/freevo/freevo_config.py
export FREEVO_CONTRIB=/usr/share/freevo/contrib
export RUNAPP=""

python encodingclient.py test
"""
