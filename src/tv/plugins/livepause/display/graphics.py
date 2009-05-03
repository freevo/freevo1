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

import os.path

import kaa
import time
import tv.epg_xmltv
from tv.plugins.livepause.display.base import OSD
import dialog
from dialog.dialogs import Dialog, InputDialog

class GraphicsOSD(OSD):
    """
    Graphical OSD that uses the dialogs to display information
    """
    def __init__(self):
        super(OSD, self).__init__()
        self.info_dialog = InfoDialog()
        self.buffer_pos_dialog = BufferPositionDialog()
        self.last_dialog = None

    def display_info(self, info_function):
        self.info_dialog.info_function = info_function
        self.info_dialog.info_channel = None
        self.info_dialog.show()
        self.last_dialog = self.info_dialog

    def display_buffer_pos(self, info_function):
        self.buffer_pos_dialog.info_function = info_function
        self.buffer_pos_dialog.show()
        self.last_dialog = self.buffer_pos_dialog

    def hide(self):
        if self.last_dialog:
            self.last_dialog.hide()
            self.last_dialog = None

class InfoDialog(InputDialog):
    def __init__(self):
        super(InfoDialog, self).__init__('livepause_info', 3.0)
        self.info_function = None
        self.info_channel = None
        self.info_prog = None
        self.info_time = None
        self.current_channel = None
        self.current_prog = None
        self.update_interval = 1.0


    def eventhandler(self, event):
        update_info = False
        if event == 'INPUT_LEFT':
            if self.info_prog:
                self.info_time = self.info_prog.start - 1.0
            update_info = True

        if event == 'INPUT_RIGHT':
            if self.info_prog:
                self.info_time = self.info_prog.stop + 1.0
            update_info = True

        if event == 'INPUT_UP':
            channel = self.__get_previous_channel(self.info_channel)
            if channel:
                self.info_channel = channel
            update_info = True

        if event == 'INPUT_DOWN':
            channel = self.__get_next_channel(self.info_channel)
            if channel:
                self.info_channel = channel
            update_info = True

        if event == 'INPUT_EXIT':
            self.hide()

        if update_info:
            self.show()
            return True

        return super(InfoDialog, self).handle_event(event)

    def get_info_dict(self):
        info_dict = self.info_function()
        now = time.time()

        if self.info_channel == None:
            self.info_channel = info_dict['channel']
            self.info_time = info_dict['current_time']
            self.info_prog = 'current'
            self.current_channel = self.info_channel
            self.current_time = info_dict['current_time']

        if self.current_channel == self.info_channel:
            start_time = info_dict['start_time']
            if self.info_time < start_time:
                self.info_time = start_time
        else:
            if now > self.info_time:
                self.info_time = now

        guide = tv.epg_xmltv.get_guide()
        tv_channel_id = self.__get_guide_channel(self.info_channel)
        channels = guide.get_programs(self.info_time, self.info_time, tv_channel_id)
        if channels and channels[0].programs:
            self.info_prog = channels[0].programs[0]

            if self.info_prog.start <= self.current_time and \
                self.info_prog.stop >= self.current_time and \
                self.current_channel == self.info_channel:
                info_dict['guide_status'] = _('Current')
            elif self.info_prog.start <= now and \
                  self.info_prog.stop >= now:
                info_dict['guide_status'] = _('Now')
            else:
                info_dict['guide_status'] = ''

            info_dict['guide_program_title'] = self.info_prog.title
            info_dict['guide_program_desc'] = self.info_prog.desc
            info_dict['guide_program_start'] = self.info_prog.getattr('start')
            info_dict['guide_program_stop'] = self.info_prog.getattr('stop')

        else:
            self.info_prog = None
            info_dict['guide_program_title'] = ''
            info_dict['guide_program_desc'] = ''
            info_dict['guide_program_start'] = ''
            info_dict['guide_program_stop'] = ''

        info_dict['guide_channel'] = self.info_channel

        # Convert time entries to localtime to allow use of strftime
        info_dict['start_time'] = time.localtime(info_dict['start_time'])
        info_dict['end_time'] = time.localtime(info_dict['end_time'])
        info_dict['current_time'] = time.localtime(info_dict['current_time'])
        return info_dict

    def __get_guide_channel(self, channel):
        result = ''

        for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
            if channel == tv_display_name:
                result = tv_channel_id
                break

        return result

    def __get_previous_channel(self, channel):
        result = ''
        prev_channel = ''

        for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
            if channel == tv_display_name:
                result = prev_channel
                break
            prev_channel = tv_display_name

        return result

    def __get_next_channel(self, channel):
        result = ''
        return_next_channel = False

        for tv_channel_id, tv_display_name, tv_tuner_id in config.TV_CHANNELS:
            if return_next_channel:
                result = tv_display_name
                break

            if channel == tv_display_name:
                return_next_channel = True

        return result

class BufferPositionDialog(Dialog):
    def __init__(self):
        super(BufferPositionDialog, self).__init__('livepause_bufferpos', 3.0)
        self.info_function = None
        self.update_interval = 1.0

    def get_info_dict(self):
        info_dict = self.info_function()

        # Convert time entries to localtime to allow use of strftime
        info_dict['start_time'] = time.localtime(info_dict['start_time'])
        info_dict['end_time'] = time.localtime(info_dict['end_time'])
        info_dict['current_time'] = time.localtime(info_dict['current_time'])
        return info_dict
