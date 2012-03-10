# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dialogs.py - Common dialogs for use by TV players
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
import os.path
import time

import config
from event import *
import dialog
from dialog.dialogs import Dialog, InputDialog
import tv.epg

_epg_info_dialog = None
_channel_banner_dialog = None

def show_epg_info(current_channel):
    global _epg_info_dialog
    if dialog.is_dialog_supported():
        if _epg_info_dialog is None:
            _epg_info_dialog = EPGInfoDialog()
        _epg_info_dialog.set_initial_channel(current_channel)
        _epg_info_dialog.show()

def show_channel_banner(channel=None, channel_number=None):
    global _channel_banner_dialog
    if dialog.is_dialog_supported():
        if channel is None and channel_number is None:
            raise RuntimeException('Either channel or channel_number must be specified!')
        if _channel_banner_dialog is None:
            _channel_banner_dialog = ChannelBannerDialog()
        _channel_banner_dialog.set_channel(channel, channel_number)
        _channel_banner_dialog.show()
    else:
        if channel:
            dialog.show_message(channel)
        else:
            dialog.show_message(channel_number)


def handle_channel_number_input(evt):
    """
    Handles the process of entering channel numbers to change channel.
    Should be called at the start of a players event handler so that
    only events that this function doesn't consume are processed.
    for example:

    | def eventhandler(self, event):
    |     if tv.channels.handle_channel_number_input(event):
    |         return True
    |
    |     if event == 'STOP':
    |         ...

    @param event: The event to process.
    @return: True if the event was consumed, False otherwise.
    """
    global _channel_number
    if evt in INPUT_ALL_NUMBERS:
        _channel_number_timer.stop()
        _channel_number += str(evt.arg)
        if len(_channel_number) > 3:
            _channel_number = _channel_number[1:]
        _channel_number_timer.start(2)
        show_channel_banner(channel_number=_channel_number)
        return True

    if evt == STOP and _channel_number:
        _channel_number = ''
        _channel_number_timer.stop()
        return True

    if evt == PLAY and _channel_number:
        _channel_number_timer.stop()
        _post_channel_number()
        return True
    return False

def _post_channel_number():
    global _channel_number
    number = int(_channel_number)
    _channel_number = ''
    if number > 1 and number < len(config.TV_CHANNELS):
        Event('TV_CHANNEL_NUMBER', number).post()


class EPGInfoDialog(InputDialog):
    def __init__(self):
        super(EPGInfoDialog, self).__init__('epg_info', 3.0)
        self.info_channel = None
        self.info_prog = None
        self.info_time = None
        self.current_channel = None
        self.update_interval = 1.0


    def eventhandler(self, evt):
        update_info = False
        if evt == 'INPUT_LEFT':
            if self.info_prog:
                self.info_time = self.info_prog.start - 1.0
            update_info = True

        if evt == 'INPUT_RIGHT':
            if self.info_prog:
                self.info_time = self.info_prog.stop + 1.0
            update_info = True

        if evt == 'INPUT_UP':
            channel = self.__get_previous_channel(self.info_channel)
            if channel:
                self.info_channel = channel
            update_info = True

        if evt == 'INPUT_DOWN':
            channel = self.__get_next_channel(self.info_channel)
            if channel:
                self.info_channel = channel
            update_info = True

        if update_info:
            self.show()
            return True

        return super(EPGInfoDialog, self).handle_event(evt)

    def set_initial_channel(self, channel):
        self.current_channel = channel
        self.info_channel = channel

    def get_info_dict(self):
        now = time.time()


        if now > self.info_time:
            self.info_time = now

        tv_channel_id = tv.epg.channels_by_display_name[self.info_channel].id
        channels = tv.epg.get_programs(self.info_time, self.info_time, tv_channel_id)
        if channels and channels[0].programs:
            self.info_prog = channels[0].programs[0]

            if self.info_prog.start <= now and \
                  self.info_prog.stop >= now:
                if self.current_channel == self.info_channel:
                    info_dict['guide_status'] = _('Watching')
                else:
                    info_dict['guide_status'] = _('On Now')
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
        info_dict['time'] = time.localtime()
        return info_dict


    def __find_channel(self, channel):
        for i,ch in enumerate(tv.epg.channels):
            if ch.displayname == channel:
                return i
        return -1


    def __get_previous_channel(self, channel):
        i = self.__find_channel(channel)

        return tv.epg.channels[ i - 1].displayname


    def __get_next_channel(self, channel):
        i = self.__find_channel(channel) + 1
        if i >= len(tv.epg.channels):
            i = 0
        return tv.epg.channels[i].displayname



class ChannelBannerDialog(Dialog):
    def __init__(self):
        super(ChannelBannerDialog, self).__init__('channel_banner', 4.0)
        self.channel_number = ''
        self.update_interval = 1.0

    def set_channel(self, channel=None, channel_number=None ):
        if channel:
            for pos in range(len(config.TV_CHANNELS)):
                chan_cfg = config.TV_CHANNELS[pos]
                if str(chan_cfg[2]) == str(channel):
                    channel_number = str(pos)
        self.channel_number = channel_number

    def get_info_dict(self):
        channel_number = int(self.channel_number) - 1
        if channel_number < 0 or channel_number > len(config.TV_CHANNELS):
            channel_name = _('No channel')
            channel_logo = ''
        else:
            channel_name = config.TV_CHANNELS[channel_number][1]
            channel_logo = config.TV_LOGOS + '/' + config.TV_CHANNELS[channel_number][0] + '.png'
            if not os.path.isfile(channel_logo):
                channel_logo = ''

        info_dict = {
                      'channel_number' : self.channel_number,
                      'channel_name'   : channel_name,
                      'channel_logo'   : channel_logo,
                      'time'           : time.localtime(),
                    }
        return info_dict



_channel_number = ''
_channel_number_timer = kaa.OneShotTimer(_post_channel_number)
