# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# An example of a DaemonPlugin using kaa notifier using EventHandler
# -----------------------------------------------------------------------
# $Id$
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


import time
from threading import Thread
import config
import plugin
from kaa import Timer
from kaa import EventHandler
import rc
from event import *


class PluginInterface(plugin.DaemonPlugin):
    """
    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    | plugin.activate('processevent')
    """
    __author__           = 'Your Name'
    __author_email__     = 'you@youremail.addr'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'

    def __init__(self):
        """
        init the events plug-in
        """
        plugin.DaemonPlugin.__init__(self)
        plugin.register(self, 'processevent')
        self.plugin_name = 'processevent'
        self.event = EventHandler(self.event_handler)
        self.event.register()

    def event_handler(self, event):
        """ The event handler """
        print '%s event_handler(%s) %s' % (time.strftime('%H:%M:%S'), event, event.__dict__)
        return True
