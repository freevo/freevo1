# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# help.py - a simple plugin to listen for help events
# -----------------------------------------------------------------------
# $Id: headlines.py 11461 2009-05-02 07:59:05Z duncan $
#
# Notes:
# Todo:
# activate:
# plugin.activate('help')
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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

from event import HELP_TOGGLE
import osd
import plugin

osd  = osd.get_singleton()

class PluginInterface(plugin.DaemonPlugin):
    """
    Event handler plugin to toggle the help overlay when the HELP_TOGGLE event
    is received.

    To activate, put the following lines in local_conf.py:
    | plugin.activate('help')
    """
    def eventhandler(self, event=None, menuw=None):
        if event == HELP_TOGGLE:
            osd.toggle_helpscreen()
            return True


