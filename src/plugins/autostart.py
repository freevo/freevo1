# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in to sent events at the end of start up
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('autostart')
#           AUTOSTART_TIMEOUT = 5
#           AUTOSTART_EVENTS = ( <event1>, <event2>, ... )
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
# -----------------------------------------------------------------------

import config
import plugin
import time
import rc
from event import *

class PluginInterface(plugin.DaemonPlugin):
    """
    The autostart plugin allows you to define an action that will be called when
    the user do not interact in the first few seconds.  With this it is possible to
    define a default action e.g. starting radio if there is no other activity.

    To activate the autostart plugin add to local_conf.py::

        plugin.activate('autostart')
        AUTOSTART_EVENTS = (
            'MENU_DOWN', 'MENU_DOWN', 'MENU_SELECT', 'MENU_SELECT',
        )
    """
    __author__           = 'Andreas Dick'
    __author_email__     = 'andudi@gmx.ch'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'.split()[1]

    def __init__(self):
        """
        Init the autostart timeout and the plugin variables
        """
        plugin.DaemonPlugin.__init__(self)

        self.active = True
        self.event_listener = True
        self.poll_interval = config.AUTOSTART_POLL_INTERVAL
        self.timeout = time.time() + config.AUTOSTART_TIMEOUT

        plugin.register(self, 'autostart')
        self.plug = plugin.getbyname('autostart')


    def config(self):
        return [
            ('AUTOSTART_EVENTS', [], 'list of events to send to freevo at start up'),
            ('AUTOSTART_TIMEOUT', 5, 'Numbers of seconds to time out if there is no action'),
            ('AUTOSTART_POLL_INTERVAL', 100, 'Frequency that poll is called'),
        ]


    def poll(self):
        """
        plugin polling
        """
        #print "POLL(%.1f): polling" % (self.timeout - time.time())
        if not self.active:
            return
        if (self.timeout - time.time()) < 0:
            _debug_('Timeout (%ss) reached without an event, posting events now.' %
                self.timeout, DINFO)
            for e in config.AUTOSTART_EVENTS:
                rc.post_event(Event(e))

            self.poll_interval = 0
            self.event_listener = False
            self.active = False


    def eventhandler(self, event, menuw=None):
        """
        called when an event occurs
        """
        #print "EVENT(%.1f): %s" % ((self.timeout - time.time()), event.name)
        if not self.active:
            return 0
        if event == MENU_PROCESS_END:
            return 0
        if config.AUTOSTART_TIMEOUT:
            _debug_('Another event is closing the autostart plugin.', DINFO)
            self.poll_interval = 0
            self.event_listener = False
            self.active = False
        return 0
