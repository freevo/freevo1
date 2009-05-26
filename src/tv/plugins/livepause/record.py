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

def start_recording(backend, channel_id):
    """
    Start recording the contents of the ring buffer to a file.
    @param reader: ChunkBufferReader instance used to read from the ring buffer.
    @param channel_id: The currently tuned channel.
    """
    buffer_info = backend.get_buffer_info()

    program = _get_program(buffer_info[3], channel_id)
    if program:
        filename_array = { 'progname': String(program.title),
                           'title'   : String(program.sub_title) }
        start_time = program.start
        end_time = program.stop
    else:
        filename_array = { 'progname': String('Manual Recording'),
                           'title'   : String('') }
        start_time = buffer_info[3]
        end_time = current_buffer_time + config.LIVE_PAUSE2_INSTANT_RECORD_LENGTH

    filemask = config.TV_RECORD_FILE_MASK % filename_array
    filemask = time.strftime(filemask, time.localtime(current_buffer_time))
    filename = os.path.join(config.TV_RECORD_DIR, progname2filename(filemask).rstrip(' -_:') + \
                            config.TV_RECORD_FILE_SUFFIX)

    _create_fxd(program, filename, start_time)
    backend.save(filename, start_time, end_time)

def _get_program(current_time, channel_id):
    """
    Get the program object from the EPG for channel_id at time current_time.
    """
    for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
        if tv_tuner_id == channel_id:
            channel_id = tv_channel_id

    channels = epg_xmltv.get_guide().get_programs(start=current_time,
                                                 stop=current_time,
                                                 channel_id=[channel_id])

    if channels and channels[0] and channels[0].programs:
        return channels[0].programs[0]
    return None

def _create_fxd(prog, filename, start_time):
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
