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

import tv.epg_xmltv
from tv.epg_types import TvProgram
from tv.record_client import RecordClient

skin.get_singleton().register('tv', ('screen', 'title', 'subtitle', 'view', 'tvlisting', 'info', 'plugin'))

CHAN_NO_DATA = _('This channel has no data loaded')

class TVGuide(Item):
    """
    Class for TVGuide
    """
    def __init__(self, start_time, player, menuw):
        _debug_('TVGuide.__init__(start_time=%r, player=%r, menuw=%r)' % (start_time, player, menuw), 2)
        Item.__init__(self)

        # get skin definitions of the TVGuide
        self.n_items, self.hours_per_page = skin.items_per_page(('tv', self))
        # end of visible guide
        stop_time = start_time + self.hours_per_page * 60 * 60

        # constructing the guide takes some time
        guide = tv.epg_xmltv.get_guide(popup=True)
        # getting channels
        channels = guide.get_programs(start_time+1, stop_time-1)
        if not channels:
            dialog.show_alert(_('TV Guide is corrupt!'), type='error')
            return

        # select the first available program
        selected = None
        for chan in channels:
            if chan.programs:
                self.selected = chan.programs[0]
                break


        self.recordclient = RecordClient()
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

        self.update_schedules(force=True)

        self.event_context = 'tvmenu'
        self.transition = skin.TRANSITION_IN
        self.rebuild(start_time, stop_time, guide.chan_list[0].id, selected)
        
        menuw.pushmenu(self)
        


    def update_schedules_cb(self, scheduledRecordings):
        """ """
        _debug_('update_schedules_cb(scheduledRecordings=%r)' % (scheduledRecordings,), 2)
        #upsoon = '%s/upsoon' % (config.FREEVO_CACHEDIR)
        #if os.path.isfile(upsoon):
        #    os.unlink(upsoon)

    def update_schedules(self, force=False):
        """
        update schedule

        reload the list of scheduled programs and check for overlapping
        """
        _debug_('update_schedules(force=%r)' % (force,), 2)
        if not force and self.last_update + 60 > time.time():
            return

        _debug_('update schedule', 2)
        self.last_update = time.time()
        self.scheduled_programs = []
        self.overlap_programs = []
        self.favorite_programs = []
        (status, scheduledRecordings) = self.recordclient.getScheduledRecordingsNow()
        if status:
            util.misc.comingup(scheduledRecordings, True)
            progs = scheduledRecordings.getProgramList()

            for k in progs:
                prog = progs[k]
                self.scheduled_programs.append(prog.str2utf())
                if prog.overlap:
                    self.overlap_programs.append(prog.str2utf())
                if hasattr(prog, 'isFavorite') and prog.isFavorite:
                    self.favorite_programs.append(prog.str2utf())


    def eventhandler(self, event, menuw=None):
        """
        Handles events in the tv guide
        """
        _debug_('eventhandler(event=%r, menuw=%r)' % (event.name, menuw), 2)

        ## MENU_CHANGE_STYLE
        if event == MENU_CHANGE_STYLE:
            if skin.toggle_display_style('tv'):
                start_time    = self.start_time
                stop_time     = self.stop_time
                start_channel = self.start_channel
                selected      = self.selected

                self.n_items, hours_per_page = skin.items_per_page(('tv', self))

                before = -1
                after  = -1
                for c in self.guide.chan_list:
                    if before >= 0 and after == -1:
                        before += 1
                    if after >= 0:
                        after += 1
                    if c.id == start_channel:
                        before = 0
                    if c.id == selected.channel_id:
                        after = 0

                if self.n_items <= before:
                    start_channel = selected.channel_id

                if after < self.n_items:
                    up = min(self.n_items -after, len(self.guide.chan_list)) - 1
                    for i in range(len(self.guide.chan_list) - up):
                        if self.guide.chan_list[i+up].id == start_channel:
                            start_channel = self.guide.chan_list[i].id
                            break

                stop_time = start_time + hours_per_page * 60 * 60

                self.n_cols  = (stop_time - start_time) / 60 / self.col_time
                self.rebuild(start_time, stop_time, start_channel, selected)
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

        ## MENU_RIGHT: Move to previous programm on this channel
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
            if channel_no < len(self.guide.chan_list):
                self.start_channel = self.guide.chan_list[channel_no].id
            else:
                self.lastinput_value = None

            self.rebuild(self.start_time, self.stop_time, self.start_channel, self.selected)
            return True

        return False


    ### gui functions

    def show(self):
        """ show the guide"""
        _debug_('show', 2)
        if not self.visible:
            self.visible = 1
            self.refresh()


    def hide(self):
        """ hide the guide"""
        _debug_('hide', 2)
        if self.visible:
            self.visible = 0
            skin.clear()


    def refresh(self, force_update=True):
        """refresh the guide

        This function is called automatically by freevo whenever this menu is
        opened or reopened.
        """
        _debug_('refresh(force_update=True)', 2)
        if self.menuw.children:
            return
        _debug_('tvguide: setting context to %s' % self.event_context, 2)
        self.update(force_update)
        skin.draw(self.type, self, transition=self.transition)
        self.transition = skin.TRANSITION_NONE


    def update(self, force=False):
        """ update the guide

        This function updates the scheduled and overlap flags for
        all currently displayed programs.
        """
        _debug_('update(force=False)', 2)
        self.update_schedules(force)
        if self.table:
            for t in self.table:
                try:
                    for p in t.programs:
                        if p in self.scheduled_programs:
                            p.scheduled = True
                            # DO NOT change this to 'True' Twisted
                            # does not support boolean objects and
                            # it will break under Python 2.3
                        else:
                            p.scheduled = False
                            # Same as above; leave as 'False' until
                            # Twisted includes Boolean
                        if p in self.overlap_programs:
                            p.overlap = True
                        else:
                            p.overlap = False

                        if p in self.favorite_programs:
                            p.favorite = True
                        else:
                            p.favorite = False
                except:
                    pass

        #self.refresh()


    def jump_to_now(self, old_selected):
        """
        jump to now in the tv guide.
        """
        _debug_('jump_to_now(old_selected=%r)' % (old_selected,), 2)
        (year, mon, mday, hour, min, sec, wday, yday, isdst) = time.localtime()
        min = min > 30 and 30 or 0
        start_time = time.mktime((year, mon, mday, hour, min, sec, wday, yday, isdst))
        stop_time = start_time + self.hours_per_page * 60 * 60
        start_channel = self.start_channel

        # we need to determine the program,
        # that is running now at the selected channel
        programs = self.guide.get_programs(start_time+1, stop_time-1, old_selected.channel_id)

        if len(programs) > 0 and len(programs[0].programs) > 0:
            selected = programs[0].programs[0]
        else:
            selected = None

        self.rebuild(start_time, stop_time, start_channel, selected)


    def advance_tv_guide(self, hours=0):
        """
        advance the tv guide by the number of hours that is passed in arg.
        """
        _debug_('advance_tv_guide(hours=%r)' % (hours,), 2)
        new_start_time = self.start_time + (hours * 60 * 60)
        new_end_time =  self.stop_time + (hours * 60 * 60)
        start_channel = self.start_channel

        # we need to determine the new selected program
        programs = self.guide.get_programs(new_start_time+1, new_end_time-1, self.start_channel)

        if len(programs) > 0 and len(programs[0].programs) > 0:
            selected = programs[0].programs[0]
        else:
            selected = None

        self.rebuild(new_start_time, new_end_time, start_channel, selected)


    def rebuild(self, start_time, stop_time, start_channel, selected):
        """ rebuild the guide

        This is neccessary we change the set of programs that have to be
        displayed, this is the case when the user moves around in the menu.
        """
        _debug_('rebuild(start_time=%r, stop_time=%r, start_channel=%r, selected=%r)' % (start_time, stop_time, start_channel, selected), 2)
        self.guide = tv.epg_xmltv.get_guide(popup=True)
        channels = self.guide.get_programs(start_time+1, stop_time-1)

        table = [ ]

        self.start_time    = start_time
        self.stop_time     = stop_time
        self.start_channel = start_channel
        self.selected      = selected

        self.display_up_arrow   = False
        self.display_down_arrow = False

        # table header
        table += [ ['Chan'] ]
        for i in range(int(self.n_cols)):
            table[0] += [ start_time + self.col_time * i * 60 ]

        table += [ self.selected ] # the selected program

        found_1stchannel = 0
        if stop_time == None:
            found_1stchannel = 1

        flag_selected = 0

        n = 0
        for chan in channels:
            if n >= self.n_items:
                self.display_down_arrow = True
                break

            if start_channel != None and chan.id == start_channel:
                found_1stchannel = 1

            if not found_1stchannel:
                self.display_up_arrow = True

            if found_1stchannel:
                if not chan.programs:
                    prg = TvProgram(chan.id, 0, 0, 2147483647, CHAN_NO_DATA, desc='')
                    chan.programs = [ prg ]

                for i in range(len(chan.programs)):
                    if selected:
                        if chan.programs[i] == selected:
                            flag_selected = 1

                table += [ chan ]
                n += 1

        if flag_selected == 0:
            for i in range(2, len(table)):
                if flag_selected == 1:
                    break
                else:
                    if table[i].programs:
                        for j in range(len(table[i].programs)):
                            if table[i].programs[j].stop > start_time:
                                self.selected = table[i].programs[j]
                                table[1] = table[i].programs[j]
                                flag_selected = 1
                                break

        self.table = table
        # then we can refresh the display with this programs
        #self.update()
        self.refresh(force_update=False)


    def change_program(self, value, full_scan=False):
        """
        Move to the next program
        """
        _debug_('change_program(value=%r, full_scan=%r)' % (value, full_scan), 2)
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        channel = self.guide.chan_dict[last_prg.channel_id]
        if full_scan:
            all_programs = self.guide.get_programs(start_time-24*60*60, stop_time+24*60*60, channel.id)
        else:
            all_programs = self.guide.get_programs(start_time+1, stop_time-1, channel.id)

        # Current channel programs
        programs = all_programs[0].programs
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

            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc
            to_info = (prg.title, procdesc)
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
            prg = TvProgram(channel.id, 0, 0, 2147483647, CHAN_NO_DATA, desc='')
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)


    def change_channel(self, value):
        """
        Move to the next channel
        """
        _debug_('change_channel(value=%r)' % (value,), 2)
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        for i in range(len(self.guide.chan_list)):
            if self.guide.chan_list[i].id == start_channel:
                start_pos = i
                end_pos   = i + self.n_items
            if self.guide.chan_list[i].id == last_prg.channel_id:
                break

        channel_pos = min(len(self.guide.chan_list)-1, max(0, i+value))

        if value < 0 and channel_pos >= 0 and channel_pos < start_pos:
            start_channel = self.guide.chan_list[start_pos + value].id

        if value > 0 and channel_pos < len(self.guide.chan_list)-1 and channel_pos+1 >= end_pos:
            start_channel = self.guide.chan_list[start_pos + value].id

        channel = self.guide.chan_list[channel_pos]


        programs = self.guide.get_programs(start_time+1, stop_time-1, channel.id)
        programs = programs[0].programs

        prg = None
        if programs and len(programs) > 0:
            for i in range(len(programs)):
                if programs[i].stop > self.select_time and programs[i].stop > start_time:
                    break

            prg = programs[i]
            if prg.sub_title:
                procdesc = '"' + prg.sub_title + '"\n' + prg.desc
            else:
                procdesc = prg.desc

            to_info = (prg.title, procdesc)
        else:
            prg = TvProgram(channel.id, 0, 0, 2147483647, CHAN_NO_DATA, desc='')
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)
