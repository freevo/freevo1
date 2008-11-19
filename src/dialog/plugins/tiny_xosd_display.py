# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo module to handle channel changing.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
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

import time
import re

import pyosd

import config
import plugin

import osd_display

class PluginInterface(plugin.Plugin):
    """
    Enables the use of the dialog layer in the menu screens to show dialogs and use
    PyOSD (XOsd) to display volume and messages.
    """
    def __init__(self):
        dialog.set_osd_display(TinyXOSDGraphicsDisplay())
        plugin.Plugin.__init__(self)

    def config(self):
        return [
                ('OSD_MESSAGE_FONT', '-*-helvetica-medium-r-normal-*-*-260-*-*-p-*-*-*', 'Font used for Xosd'),
                ('OSD_MESSAGE_COLOR','#D3D3D3', 'Color used to display Xosd (Default: LightGray)'),
                ('OSD_MESSAGE_TIMEOUT', 3, 'Time to display messages for in seconds'),
                ('OSD_MESSAGE_OFFSET', 20 + config.OSD_OVERSCAN_BOTTOM, 'Location to display messages')
                ]


class TinyXOSDGraphicsDisplay(osd_display.OSDGraphicsDisplay):
    """
    Display class that uses the osd.dialog_layer to display dialogs and uses
    PyOSD to display volume and messages.
    """
    def __init__(self):
        super(TinyXOSDGraphicsDisplay, self).__init__()

        self.xosd = pyosd.osd()
        self.xosd.set_font(OSD_MESSAGE_FONT)
        self.xosd.set_colour(OSD_MESSAGE_COLOR)
        self.xosd.set_timeout(OSD_MESSAGE_TIMEOUT)
        self.xosd.set_offset(OSD_MESSAGE_OFFSET)

    def show_message(self, message):
        # This is text, display it on top
        self.xosd.set_pos(pyosd.POS_TOP)
        lines = message.split('\n')
        self.xosd.display(lines[0], pyosd.TYPE_STRING, line=0)
        if lines > 1:
            self.xosd.display(lines[1], pyosd.TYPE_STRING, line=1)
        else:
            self.osd.display('', pyosd.TYPE_STRING, line=1)

    def show_volume(self, level, muted, channel=None):
        if not channel:
            channel = _('Volume')
        level = min(100, max(0, level))
        if muted:
            message = '%s (%s)' % (channel, _('Muted'))
        else:
            message = '%s (%d%%)' % (channel, level)
        self.osd.display(message, pyosd.TYPE_STRING, line=0)
        self.osd.display('%s (%d%%)' % (channel, level), pyosd.TYPE_STRING, line=0)
        self.osd.display(percent, pyosd.TYPE_PERCENT, line=1)
