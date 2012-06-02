# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo TV Guide module.
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
import logging
logger = logging.getLogger("freevo.tv.tvguide")


import os, time
import pprint

import config, skin, util, rc

from event import *
from item import Item
from programitem import ProgramItem

import dialog

import tv.epg
from tv.epg_types import TvProgram
from tv.record_client import RecordClient

skin.get_singleton().register('tv', ('screen', 'title', 'subtitle', 'view', 'tvlisting', 'info', 'plugin'))

CHAN_NO_DATA = _('This channel has no data loaded')

class TVGuide(Item):
    """
    Class for TVGuide
    """
    def __init__(self, channels, start_time, player, menuw):
        logger.log( 9, 'TVGuide.__init__(start_time=%r, player=%r, menuw=%r)', start_time, player, menuw)
        Item.__init__(self)

        self.channels = channels
        self.start_channel_idx = 0
        self.selected_channel_idx = 0

        # get skin definitions of the TVGuide
        self.n_items, self.hours_per_page = skin.items_per_page(('tv', self))
        # end of visible guide
        stop_time = start_time + self.hours_per_page * 60 * 60

        self.selected = None
        self.col_time = 30      # each col represents 30 minutes
        self.n_cols  = (stop_time - start_time) / 60 / self.col_time
        self.player = player

        self.type = 'tv'
        self.menuw = menuw
        self.visible = True
        self.select_time = start_time
        self.last_update = 0

        self.lastinput_value = None
        self.lastinput_time = None

        self.event_context = 'tvmenu'
        self.transition = skin.TRANSITION_IN
        self.start_time = 0
        self.stop_time = 0

        # We select the first channel/program available an relie on
        # the rebuild method not calling the select function again
        # after a program has been selected.
        self.rebuild(start_time, stop_time, lambda  p: True)
        
        menuw.pushmenu(self)
        

    def eventhandler(self, event, menuw=None):
        """
        Handles events in the tv guide
        """
        logger.log( 9, 'eventhandler(event=%r, menuw=%r)', event.name, menuw)

        ## MENU_CHANGE_STYLE
        if event == MENU_CHANGE_STYLE:
            if skin.toggle_display_style('tv'):
                start_time    = self.start_time
                stop_time     = self.stop_time
                selected      = self.selected

                self.n_items, hours_per_page = skin.items_per_page(('tv', self))

                stop_time = start_time + hours_per_page * 60 * 60

                self.n_cols  = (stop_time - start_time) / 60 / self.col_time
                self.rebuild(start_time, stop_time, lambda p: p == selected)
            return True

        ## MENU_UP: Move one channel up in the guide
        elif event == MENU_UP:
            self.change_channel(-1)
            return True

        ## MENU_DOWN: Move one channel down in the guide
        elif event == MENU_DOWN:
            self.change_channel(1)
            return True

        ## MENU_LEFT: Move to the next program on this channel
        elif event == MENU_LEFT:
            self.change_program(-1)
            return True

        ## MENU_RIGHT: Move to previous program on this channel
        elif event == MENU_RIGHT:
            self.change_program(1)
            return True

        ## MENU_PAGEUP: Moves to the first of the currently displayed channels
        elif event == MENU_PAGEUP:
            self.change_channel(-self.n_items)
            return True

        ## MENU_PAGEDOWN: Move to the last of the currently displayed channels
        elif event == MENU_PAGEDOWN:
            self.change_channel(self.n_items)
            return True


        ## MENU_SUBMENU: Open a submenu for the selected program
        elif event == MENU_SUBMENU:
            # create a ProgramItem for the selected program
            pi = ProgramItem(self, prog=self.selected, context='guide')
            #and show its submenu
            pi.display_submenu(menuw=self.menuw)
            return True

        ## MENU_SELECT: Show the description
        elif event == MENU_SELECT:
            # create a ProgramItem for the selected program
            pi = ProgramItem(self, prog=self.selected, context='guide')
            #and show selecte the first action in the actions list
            pi.actions()[0][0](menuw=self.menuw)
            return True

        ## TV_START_RECORDING: add or remove this program from schedule
        elif event == TV_START_RECORDING:
            pi = ProgramItem(self, prog=self.selected, context='guide')
            pi.toggle_rec(menuw=self.menuw)
            return True

        ## PLAY: Start to watch the selected channel (if it is possible)
        elif event == PLAY:
            # create a ProgramItem for the selected program
            pi = ProgramItem(self, prog=self.selected, context='guide')
            #and show its submenu
            pi.play(menuw=self.menuw)
            return True

        ## PLAY_END: Show the guide again
        elif event == PLAY_END:
            self.show()
            self.jump_to_now(self.selected)
            return True

        # FIX or REMOVE:
        # the numerical INPUT events are not available in the tvmenu context
        ## numerical INPUT: Jump to a specific channel number
        elif event in INPUT_ALL_NUMBERS:
            newinput_time = time.time()
            if self.lastinput_value is not None:
                # allow 1.2 seconds delay for multiple digit channels
                if newinput_time - self.lastinput_time < 1.2:
                    # this enables multiple (max 3) digit channel selection
                    if self.lastinput_value >= 100:
                        self.lastinput_value = (self.lastinput_value % 100)
                    newinput_value = self.lastinput_value * 10 + int(event)
            self.lastinput_value = newinput_value
            self.lastinput_time = newinput_time

            channel_no = int(newinput_value)-1
            if channel_no < len(config.TV_CHANNELS):
                self.start_channel = config.TV_CHANNELS[channel_no][0]
            else:
                self.lastinput_value = None
            s = self.selected
            self.rebuild(self.start_time, self.stop_time, lambda p : p == s)
            return True

        return False


    ### gui functions

    def show(self):
        """ show the guide"""
        logger.log( 9, 'show')
        if not self.visible:
            self.visible = 1
            self.refresh()


    def hide(self):
        """ hide the guide"""
        logger.log( 9, 'hide')
        if self.visible:
            self.visible = 0
            skin.clear()


    def refresh(self, force_update=True):
        """refresh the guide

        This function is called automatically by freevo whenever this menu is
        opened or reopened.
        """
        logger.log( 9, 'refresh(force_update=True)')
        if self.menuw.children:
            return
        logger.log( 9, 'tvguide: setting context to %s', self.event_context)

        s = self.selected
        self.rebuild(self.start_time, self.stop_time, lambda p: p == s, force=True)

    def __advance(self, start_time, stop_time):
        # we need to determine the program,
        # that is running now at the selected channel
        programs = tv.epg.search(old_selected.channel_id, (start_time+1, stop_time-1))

        if len(programs) > 0:
            selected = lambda p: p == programs[0]
        else:
            selected = None

        self.rebuild(start_time, stop_time, selected)


    def jump_to_now(self, old_selected):
        """
        jump to now in the tv guide.
        """
        logger.log( 9, 'jump_to_now(old_selected=%r)', old_selected)
        (year, mon, mday, hour, min, sec, wday, yday, isdst) = time.localtime()
        min = min > 30 and 30 or 0
        start_time = time.mktime((year, mon, mday, hour, min, sec, wday, yday, isdst))
        stop_time = start_time + self.hours_per_page * 60 * 60
        self.__advance(start_time, stop_time)


    def advance_tv_guide(self, hours=0):
        """
        advance the tv guide by the number of hours that is passed in arg.
        """
        logger.log( 9, 'advance_tv_guide(hours=%r)', hours)
        new_start_time = self.start_time + (hours * 60 * 60)
        new_end_time =  self.stop_time + (hours * 60 * 60)

        self.__advance(new_start_time, new_end_time)


    def rebuild(self, start_time, stop_time, selected_fn, force=False):
        """ rebuild the guide

        This is neccessary we change the set of programs that have to be
        displayed, this is the case when the user moves around in the menu.
        """
        logger.log( 9, 'rebuild(start_time=%r, stop_time=%r, selected_fn=%r)', start_time, stop_time, selected_fn)
        start_channel_idx = self.start_channel_idx
        if self.selected_channel_idx > self.start_channel_idx + (self.n_items - 1):
            self.start_channel_idx = self.selected_channel_idx - (self.n_items - 1)

        elif self.selected_channel_idx < self.start_channel_idx:
            self.start_channel_idx = self.selected_channel_idx

        if force or self.start_time != start_time or self.start_channel_idx != start_channel_idx:

            end_idx = self.start_channel_idx + self.n_items

            channel_list = self.channels[self.start_channel_idx:end_idx]
            self.display_up_arrow = self.start_channel_idx > 0
            self.display_down_arrow = end_idx < len(self.channels)

            channels = tv.epg.get_grid(start_time+1, stop_time-1, channel_list)

            self.start_time    = start_time
            self.stop_time     = stop_time

            # table header
            header = ['Chan']
            for i in range(int(self.n_cols)):
                header.append( start_time + self.col_time * i * 60 )

            table = [header, self.selected]

            flag_selected = False

            for chan in channels:
                if not chan.programs:
                    prg = TvProgram(chan.id, 0, 0, 2147483647, CHAN_NO_DATA, desc='')
                    chan.programs = [ prg ]
                table.append(chan)

            self.table = table

        selected_channel_offset = (self.selected_channel_idx - self.start_channel_idx) + 2
        if selected_fn:
            for p in self.table[selected_channel_offset].programs:
                if selected_fn(p):
                    flag_selected = True
                    self.selected = p
                    self.table[1] = p
                    break

        if not flag_selected:
            p = self.table[selected_channel_offset].programs[0]
            self.table[1] = p
            self.selected = p

        skin.draw(self.type, self, transition=self.transition)
        self.transition = skin.TRANSITION_NONE



    def change_program(self, value, full_scan=False):
        """
        Move to the next program
        """
        logger.log( 9, 'change_program(value=%r, full_scan=%r)', value, full_scan)
        start_time    = self.start_time
        stop_time     = self.stop_time
        last_prg      = self.selected

        if full_scan:
            if value > 0:
                programs = tv.epg.search(last_prg.channel_id, (stop_time-1, stop_time+24*60*60))
            else:
                programs = tv.epg.search(last_prg.channel_id, (start_time-24*60*60, start_time+1))
        else:
            programs = self.table[2 + (self.selected_channel_idx - self.start_channel_idx)].programs

        # Current channel programs
        if programs:
            for i in range(len(programs)):
                if programs[i].title == last_prg.title and \
                   programs[i].start == last_prg.start and \
                   programs[i].stop == last_prg.stop and \
                   programs[i].channel_id == last_prg.channel_id:
                    break

            prg = None

            if value > 0:
                if i + value < len(programs):
                    prg = programs[i+value]
                elif full_scan:
                    prg = programs[-1]
                else:
                    return self.change_program(value, True)
            else:
                if i + value >= 0:
                    prg = programs[i+value]
                elif full_scan:
                    prg = programs[0]
                else:
                    return self.change_program(value, True)

            self.select_time = prg.start

            # set new (better) start / stop times
            extra_space = 0
            if prg.stop - prg.start > self.col_time * 60:
                extra_space = self.col_time * 60

            while prg.start + extra_space >= stop_time:
                start_time += (self.col_time * 60)
                stop_time += (self.col_time * 60)

            while prg.start + extra_space <= start_time:
                start_time -= (self.col_time * 60)
                stop_time -= (self.col_time * 60)
        else:
            prg = TvProgram(last_prg.channel_id, 0, 0, 2147483647, CHAN_NO_DATA, desc='')

        self.rebuild(start_time, stop_time, lambda p: p == prg)


    def change_channel(self, value):
        """
        Move to the next channel
        """
        logger.log( 9, 'change_channel(value=%r)', value)
        start_time    = self.start_time
        stop_time     = self.stop_time

        selected_channel_idx = min(len(self.channels) - 1, max(0, self.selected_channel_idx + value))
        if selected_channel_idx == self.selected_channel_idx:
            return
        self.selected_channel_idx = selected_channel_idx

        self.rebuild(start_time, stop_time, lambda p: p.stop > self.select_time and p.stop > start_time \
                        and p.channel_id == self.channels[self.selected_channel_idx].id)
