# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# view_recordings.py - View the TV recordings directory
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

import config
import plugin
from directory import DirItem

class PluginInterface(plugin.Plugin):
    """
    """
    def __init__(self):
        """
        normal plugin init, but sets _type to 'mainmenu_tv'
        """
        plugin.Plugin.__init__(self)
        self._type = 'mainmenu_tv'

    def items(self, parent):
        return [DirItem(config.TV_RECORD_DIR, None, name = _('Recorded Shows'),
                             display_type='tv')]
