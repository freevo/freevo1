# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# the Freevo livepause osd module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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
# ----------------------------------------------------------------------- */
import time

import dialog

from tv.plugins.livepause.display.base import OSD

class TextOSD(OSD):
    def display_info(self, info_function):
        info_dict = info_function()

        info_message = '%s ' % info_dict['channel']
        info_message += time.strftime('%H:%M', time.localtime(info_dict['start_time']))
        info_message += '<-'
        info_message += time.strftime('%H:%M', time.localtime(info_dict['current_time']))
        info_message += '->'
        info_message += time.strftime('%H:%M', time.localtime(info_dict['end_time']))
        dialog.show_message(info_message)

    def display_buffer_pos(self, info_function):
        self.display_info(info_function)

    def display_channel_number(self, channel):
        dialog.show_message(_('Channel #: %s') % channel)
