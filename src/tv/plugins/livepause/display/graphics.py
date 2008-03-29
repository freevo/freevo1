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
import threading

from tv.plugins.livepause.display.base import OSD
from tv.plugins.livepause.display import dialogs

class GraphicsOSD(OSD):
    def __init__(self, player):
        OSD.__init__(self, player)
        self.thread = threading.Thread(target=self.run)
        self.thread.setDaemon(True)
        self.thread.start()
        self.new_dialog_event = threading.Event()
        self.new_dialog_mutex = threading.Lock()
        self.new_dialog = None


    def display_volume(self, level):
        # TODO: Implement
        self.__send_dialog('volume', {'volume':level}, 3.0)

    def display_message(self, message):
        # TODO: Implement
        self.__send_dialog('message', {'text':message}, 3.0)

    def display_info(self, info_function):
        # TODO: Implement
        pass

    def hide(self):
        self.__send_dialog(None, None, 0.0)

    def __send_dialog(self, name, info, time):
        self.new_dialog_mutex.acquire()
        self.new_dialog = (name, info, time)
        self.new_dialog_event.set()
        self.new_dialog_mutex.release()

    def run(self):
        current_dialog_name = None
        current_dialog_info = None
        current_dialog_time = 0.0
        current_dialog_definition = None

        wait_time = None
        while True:
            self.new_dialog_event.wait(wait_time)
            if self.new_dialog_event.isSet():
                self.new_dialog_mutex.acquire()

                # Close any current dialog if not the same as the one to be displayed.
                if current_dialog_name and current_dialog_name != self.new_dialog[0]:
                    self.hide_surface()
                    current_dialog_definition.finish()

                if current_dialog_name != self.new_dialog[0]:
                    current_dialog_name = self.new_dialog[0]
                    current_dialog_definition = dialogs.get_definition(current_dialog_name)
                    current_dialog_definition.prepare()

                current_dialog_info = self.new_dialog[1]
                wait_time = self.new_dialog[2]

                if callable(current_dialog_info):
                    info = current_dialog_info()
                else:
                    info = current_dialog_info

                self.__render_dialog(current_dialog_definition, info)

                self.new_dialog = None
                self.new_dialog_event.clear()
                self.new_dialog_mutex.release()

            else:
                self.hide_surface()
                current_dialog_name = None
                current_dialog_definition.finish()
                current_dialog_definition = None
                wait_time = None

    def __render_dialog(self, dialog_def, info):
        surface = dialog_def.render(info)
        location = dialog_def.location

        os_l = config.OSD_OVERSCAN_LEFT
        os_r = config.OSD_OVERSCAN_RIGHT
        os_t = config.OSD_OVERSCAN_TOP
        os_b = config.OSD_OVERSCAN_BOTTOM

        if location and 1:
            x = os_l
        elif location and 2:
            x = config.CONF.width - (w + os_r)
        else:
            x = ((config.CONF.width - (w + os_l + os_r)) / 2) + os_l

        if location and 4:
            y = os_t
        elif location and 8:
            y = config.CONF.height - (h + os_b)
        else:
            y = ((config.CONF.height - (h + os_t + os_b)) / 2) + os_t

        self.show_surface(surface, x, y)

    def show_surface(self, surface, x, y):
        self.player.show_graphics(surface, x, y)

    def hide_surface(self):
        self.player.hide_graphics()
