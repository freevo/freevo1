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
import logging
logger = logging.getLogger("freevo.plugins.autostart")

from kaa import OneShotTimer
from kaa import EventHandler
import config
import plugin
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
        self.timer = OneShotTimer(self._timer_handler)
        self.event = EventHandler(self._event_handler)
        self.event.register()


    def config(self):
        return [
            ('AUTOSTART_EVENTS', [], 'list of events to send to freevo at start up'),
            ('AUTOSTART_TIMEOUT', 5, 'Numbers of seconds to time out if there is no action'),
        ]


    def _event_handler(self, event):
        if self.active:
            if event == FREEVO_READY:
                self.active = True
                self.timer.start(config.AUTOSTART_TIMEOUT)
            elif event == MENU_PROCESS_END:
                if not self.active:
                    self.timer.start(config.AUTOSTART_TIMEOUT)
            elif config.AUTOSTART_TIMEOUT:
                _debug_('Another event is closing the autostart plugin.', DINFO)
                self.event.unregister()
                self.timer.stop()
                self.active = False


    def _timer_handler(self):
        if self.active:
            _debug_('Timeout reached without an event, posting events now.', DINFO)
            for e in config.AUTOSTART_EVENTS:
                rc.post_event(Event(e))
            self.event.unregister()
            self.timer.stop()
            self.active = False
