# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for creating new events
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
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


from os import system

import config
import plugin
import rc
from event import *


class PluginInterface(plugin.DaemonPlugin):
    """
    A plugin to create and control new events, specially events associated to a
    script. The events are configured like this:
    (<EVENT>, <command>, [<OSD message>])

    To activate it, put the following in local_conf.py:

    | plugin.activate('newevents')
    | NEW_EVENTS = [
    |     ('MON_SWITCH_OFF', 'xset dpms force off', 'DPMS turned off'),
    |     ('XTERM', 'xterm -fa terminal -fs 14 -bg black -fg grey &'),
    |     ('WWW', 'firefox www.google.es/ig &')
    | ]
    | EVENTS['global']['q'] = Event('MON_SWITCH_OFF')
    | EVENTS['global']['t'] = Event('XTERM')

    # To map a key already in use:
    | GLOBAL_EVENTS['WWW'] = Event('WWW')
    | KEYMAP[key.K_w] = 'WWW'
    """

    def __init__(self):
        plugin.DaemonPlugin.__init__(self)


    def config(self):
        """
        The config information
        """
        return [
            ('NEW_EVENTS', [], 'A list of events and command tuples'),
        ]


    def eventhandler(self, event=None, menuw=None, arg=None):
        """
        eventhandler to handle the new events
        """
        for r in config.NEW_EVENTS:
            if event == r[0]:
                system(r[1])
                if len(r) > 2:
                    rc.post_event(Event(OSD_MESSAGE, arg=r[2]))
                return True
