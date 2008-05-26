# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# record.py - The Freevo Live Pause recording module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:
#
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
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
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# ----------------------------------------------------------------------- */
"""
This modules contains the code to save the contents of the ringbuffer to disk,
for the instant recording feature.
"""
import os.path
import time
import threading
import traceback
import plugin

import event
import rc
from tv import epg_xmltv
from util.tv_util import progname2filename
import config

__all__ = ['Recorder']

class Recorder(object):
    """
    Class to store the contents of the ring buffer to a file.
    """

    def __init__(self, reader, channel_id):
        """
        Create a new Recorder instance
        @param reader: ChunkBufferReader instance used to read from the ring buffer.
        @param channel_id: The currently tuned channel.
        """
        self.reader = reader
        self.channel_id = channel_id
        self.canceled = False
        self.recording = True
        self.thread = threading.Thread(target=self.__run)
        self.thread.start()

    def cancel(self):
        """
        Cancel the copy of the contents of the ring buffer to a file.
        """
        self.canceled = True

    def __run(self):
        """
        Thread method that does the actual recording.
        """
        rc.post_event(event.RECORD_START)
        reader = self.reader
        # Get the show that is currently being viewed
        current_buffer_time = reader.get_current_chunk_time()

        program = self.__get_program(current_buffer_time, self.channel_id)
        if program:
            filename_array = { 'progname': String(program.title),
                               'title'   : String(program.sub_title) }
            end_time = program.stop
        else:
            filename_array = { 'progname': String('Manual Recording'),
                               'title'   : String('') }
            end_time = current_buffer_time + config.LIVE_PAUSE2_INSTANT_RECORD_LENGTH

        filemask = config.TV_RECORD_FILE_MASK % filename_array
        filemask = time.strftime(filemask, time.localtime(current_buffer_time))
        filename = os.path.join(config.TV_RECORD_DIR, progname2filename(filemask).rstrip(' -_:') + \
                                config.TV_RECORD_FILE_SUFFIX)

        self.__create_fxd(program, filename, current_buffer_time)
        output = None
        try:
            output = open(filename, 'wb')

            while not self.canceled:
                current_buffer_time = reader.get_current_chunk_time()
                if current_buffer_time >= end_time:
                    break
                data = reader.read(188 * 7)
                if not data:
                    time.sleep(0.5)
                else:
                    output.write(data)
        except:
            _debug_('Caught exception while recording! %s' % traceback.format_exc())

        # Make sure the file gets closed.
        if output:
            try:
                output.close()
            except:
                pass

        self.recording = False
        rc.post_event(event.RECORD_STOP)
        reader.close()

    def __get_program(self, current_time, channel_id):
        """
        Get the program object from the EPG for channel_id at time current_time.
        """
        for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
            if tv_tuner_id == channel_id:
                channel_id = tv_channel_id

        channels = epg_xmltv.get_guide().GetPrograms(start=current_time,
                                                     stop=current_time,
                                                     chanids=[channel_id])

        if channels and channels[0] and channels[0].programs:
            return channels[0].programs[0]
        return None

    def __create_fxd(self, prog, filename, start_time):
        """
        Create a .fxd file with the specified program information in.
        """
        from util.fxdimdb import FxdImdb, makeVideo
        fxd = FxdImdb()

        (filebase, fileext) = os.path.splitext(filename)
        fxd.setFxdFile(filebase, overwrite=True)

        video = makeVideo('file', 'f1', os.path.basename(filename))
        fxd.setVideo(video)
        if prog:
            fxd.title = prog.title
            fxd.info['tagline'] = fxd.str2XML(prog.sub_title)
            desc = prog.desc.replace('\n\n','\n').replace('\n','&#10;')
            fxd.info['plot'] = fxd.str2XML(desc)
        else:
            fxd.title = _('Manual Recording')
        fxd.info['recording_timestamp'] = str(start_time)
        fxd.info['runtime'] = None
        # bad use of the movie year field :)
        try:
            fxd.info['year'] = time.strftime(config.TV_RECORD_YEAR_FORMAT, time.localtime(start_time))
        except:
            fxd.info['year'] = '2007'

        if plugin.is_active('tv.recordings_manager'):
            fxd.info['watched'] = 'False'
            fxd.info['keep'] = 'False'
        fxd.writeFxd()
