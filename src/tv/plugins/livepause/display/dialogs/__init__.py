# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dialogs module for livepause osd
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

import time

import config
import rc
import tv.epg_xmltv

import skin
import xml

class Dialog(object):
    def __init__(self, name, duration):
        self.name = name
        self.skin = skin.get_definition(name)
        self.display = None
        self.duration = duration


    def handle_event(self, event):
        if event == 'STOP':
            self.display.hide_dialog()
            return True
        return False

    def set_display(self, display):
        self.display = display

    def show(self, duration=None):
        if duration is None:
            duration = self.duration
        self.display.show_dialog(self, duration)

    def prepare(self):
        if self.skin:
            self.skin.prepare()

    def render(self):
        if self.skin:
            return self.skin.render(self.get_info_dict())
        return None

    def finish(self):
        if self.skin:
            self.skin.finish()

    def get_info_dict(self):
        return {}

class InputDialog(Dialog):
    def prepare(self):
        self.context = rc.get_singleton().context
        rc.set_context('input')
        super(InputDialog,self).prepare()
    
    def finish(self):
        rc.set_context(self.context)
        super(InputDialog, self).finish()
        
class MessageDialog(Dialog):
    def __init__(self, message):
        super(MessageDialog, self).__init__('message', 3.0)
        self.message = message

    def get_info_dict(self):
        return {'message': self.message}


class VolumeDialog(Dialog):
    def __init__(self, level):
        super(VolumeDialog, self).__init__('volume', 3.0)
        self.level = level

    def get_info_dict(self):
        return {'volume': self.level,
                'volume_text': _('Volume')
                }


class InfoDialog(InputDialog):
    def __init__(self, info_function):
        super(InfoDialog, self).__init__('info', 3.0)
        self.info_function = info_function
        info_dict = info_function()
        self.info_channel = info_dict['channel']
        self.info_prog = 'current'
        self.current_channel = self.info_channel

    def handle_event(self, event):
        update_info = False
        print 'Event', event.name , 'Arg', event.arg
        if event == 'INPUT_LEFT':
            if self.info_prog == 'next':
                self.info_prog = 'now'
            elif self.info_channel == self.current_channel and self.info_prog == 'now':
                self.info_prog = 'current'
            update_info = True

        if event == 'INPUT_RIGHT':
            if self.info_prog == 'current':
                self.info_prog = 'now'
            elif self.info_prog == 'now':
                self.info_prog = 'next'
            update_info = True

        if event == 'INPUT_UP':
            channel = self.__get_previous_channel(self.info_channel)
            if channel:
                if self.info_prog == 'current':
                    self.info_prog = 'now'
                self.info_channel = channel
            update_info = True

        if event == 'INPUT_DOWN':
            channel = self.__get_next_channel(self.info_channel)
            if channel:
                if self.info_prog == 'current':
                    self.info_prog = 'now'
                self.info_channel = channel
            update_info = True

        if update_info:
            self.show()
            return True

        return super(InfoDialog, self).handle_event(event)

    def get_info_dict(self):
        info_dict = self.info_function()

        guide = tv.epg_xmltv.get_guide()
        tv_channel_id = self.__get_guide_channel(self.info_channel)
        program = None

        if self.info_prog == 'current':
            info_dict['guide_status'] = _('Current')
            prog_time = info_dict['current_time']
            channels = guide.get_programs(prog_time, prog_time, tv_channel_id)
            if channels and channels[0].programs:
                program = channels[0].programs[0]

        elif self.info_prog == 'now':
            info_dict['guide_status'] = _('Now')
            prog_time = time.time()
            channels = guide.get_programs(prog_time, prog_time, tv_channel_id)
            if channels and channels[0].programs:
                program = channels[0].programs[0]

        elif self.info_prog == 'next':
            info_dict['guide_status'] = _('Next')
            prog_time = time.time()
            channels = guide.get_programs(prog_time, prog_time, tv_channel_id)
            if channels and channels[0].programs:
                now = channels[0].programs[0]
                next_start_time = now.stop + 1.0
                channels = guide.get_programs(next_start_time, next_start_time, tv_channel_id)
                if channels[0].programs:
                    program = channels[0].programs[0]

        info_dict['guide_channel'] = self.info_channel

        if program:
            info_dict['guide_program_title'] = program.title
            info_dict['guide_program_desc'] = program.desc
            info_dict['guide_program_start'] = program.getattr('start')
            info_dict['guide_program_stop'] = program.getattr('stop')
        else:
            info_dict['guide_program_title'] = ''
            info_dict['guide_program_desc'] = ''
            info_dict['guide_program_start'] = ''
            info_dict['guide_program_stop'] = ''

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

