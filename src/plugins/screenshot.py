# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screenshot.py - a simple plugin to listen for screenshot events
# -----------------------------------------------------------------------
# $Id: headlines.py 11461 2009-05-02 07:59:05Z duncan $
#
# Notes:
# Todo:
# activate:
# plugin.activate('screenshot')
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
import os.path

import config
import dialog
from event import SCREENSHOT
import osd
import plugin

osd  = osd.get_singleton()

class PluginInterface(plugin.DaemonPlugin):
    """
    Event handler plugin to take a screenshot when a SCREENSHOT event
    is received.

    To activate, put the following lines in local_conf.py:
    | plugin.activate('screenshot')
    | SCREENSHOT_DIR = '/home/freevo/screenshots'
    """
    def config(self):
        return [('SCREENSHOT_DIR', '/tmp', 'Where to save screenshots to.')]

    
    def eventhandler(self, event=None, menuw=None):
        if event == SCREENSHOT:
            self.screenshot()
            return True


    def screenshot(self):
        filename = time.strftime('freevo-screenshot-%Y-%m-%d_%H_%M_%S.bmp')
        try:
            osd.screenshot(os.path.join(config.SCREENSHOT_DIR, filename))
            dialog.show_alert('Screenshot saved as %s' % filename)
        except:
            dialog.show_alert('Failed to save screenshot!')
            import traceback
            traceback.print_exc()