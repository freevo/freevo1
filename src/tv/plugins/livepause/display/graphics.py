# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# base.py - base osd module for livepause osd
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
#
# Todo:
#
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
import config

import kaa

from tv.plugins.livepause.display.base import OSD
from tv.plugins.livepause.display import dialogs

class GraphicsOSD(OSD):
    def __init__(self, player):
        OSD.__init__(self, player)
        self.current_dialog = None
        self.hide_dialog_timer = kaa.OneShotTimer(self.hide_dialog)

    def handle_event(self, event):
        if self.current_dialog:
            return self.current_dialog.handle_event(event)
        return False

    def display_volume(self, level):
        dialog = dialogs.VolumeDialog(level)
        dialog.set_display(self)
        dialog.show()

    def display_message(self, message):
        dialog = dialogs.MessageDialog(message)
        dialog.set_display(self)
        dialog.show()

    def display_info(self, info_function):
        dialog = dialogs.InfoDialog(info_function)
        dialog.set_display(self)
        dialog.show()

    def hide_dialog(self):
        if self.current_dialog:
            self.hide_dialog_timer.stop()
            self.current_dialog.finish()
            self.current_dialog = None
            self.hide_image()

    #===============================================================================
    # Helper methods
    #===============================================================================

    def show_dialog(self, dialog, duration):
        #Stop any pending hide timers
        self.hide_dialog_timer.stop()

        if self.current_dialog and self.current_dialog != dialog:
            self.hide_dialog()

        if not self.current_dialog:
            self.current_dialog = dialog
            dialog.prepare()

        self.show_image(dialog.render(), dialog.skin.position)
        self.hide_dialog_timer.start(duration)

    #===============================================================================
    #  Methods that should be overriden by subclasses
    #===============================================================================
    def show_image(self, image, position):
        self.player.show_graphics(image, position)

    def hide_image(self):
        self.player.hide_graphics()
