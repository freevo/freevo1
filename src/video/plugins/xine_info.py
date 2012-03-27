# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Use telnetlib to provide information about the videos played with xine
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('xine_info')
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
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.video.plugins.xine_info")

import os
import telnetlib
import time

import config
import plugin
from event import *
import rc

class PluginInterface(plugin.DaemonPlugin):
    """
    Provides information about videos played with xine

    Requirements:
        - xine started with option '--network' (XINE_ARGS_DEF)
        - xine passwd file '.xine/passwd' contains at least 'ALL:ALLOW'

    To activate this plugin, just put the following line in your local_conf.py
    file:

    | plugin.activate('video.xine_info')
    """
    __author__           = 'Andreas Dick'
    __author_email__     = 'andudi@gmx.ch'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'

    def __init__(self):
        """
        Setup the xine info plugin
        """
        # check if xine telnet access is possible:
        if config.XINE_COMMAND.find('--network') < 0 and config.XINE_ARGS_DEF.find('--network') < 0:
            self.reason = '"--network" is missing in xine args!'
            return
        else:
            passwd_file = '%s/.xine/passwd' % os.environ['HOME']
            if not os.path.exists(passwd_file):
                self.reason = 'xine passwd file is missing: %s it should at least contain ALL:ALLOW' % (passwd_file)
                return
        plugin.DaemonPlugin.__init__(self)

        self.playing = False
        self.timer = 0
        self.handle = None

        # plugin settings
        self.poll_interval = 4
        self.poll_menu_only = 0         # lcd even if player is on
        self.event_listener = 1         # listening to events

        # register this pluing
        plugin.register(self, 'xine_info')


    def get_time(self, arg):
        """
        get time info from running xine
        """
        try:
            self.handle.write('get %s\n' % arg)
            out = self.handle.read_until('\n', 0.05).split()
            if out[1] == ('%s:'%arg):
                time = int(int(out[2])/1000)
                return time
        except:
            self.handle = None
        return 0


    def poll(self):
        """
        plugin polling
        """
        if self.playing:
            self.timer += 1
            if self.timer >= 4:
                self.timer = 0

                # try to connect to xine and check answer
                if self.handle is None:
                    try:
                        self.handle = telnetlib.Telnet('127.0.0.1', 6789)
                        out = self.handle.read_until('\n', 0.1)
                        if out[-1] != '\n':
                            raise
                    except:
                        self.handle = None
                        logger.warning('Cannot telnet to xine at 127.0.0.1:6789')

                # try to get xine time info
                if self.handle is not None:
                    length = self.get_time('length')
                    elapsed = self.get_time('position')
                    if length and elapsed:
                        rc.post_event(Event('VIDEO_PLAY_INFO', arg=(elapsed, length)))


    def eventhandler(self, event, menuw=None):
        """
        called from plugin.py if an event occur
        """
        if event == VIDEO_START:
            self.timer = 0
            self.playing = True
        if event == VIDEO_END:
            self.playing = False

        return 0
