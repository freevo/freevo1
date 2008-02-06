# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# tvguide.py - This is the Freevo TV Guide module.
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


import os, time


import config, skin, util, rc

from gui.PopupBox import PopupBox
from gui.AlertBox import AlertBox

from item import Item
from programitem import ProgramItem
from event import *

import epg_xmltv, epg_types
import record_client as ri

skin = skin.get_singleton()
skin.register('tv', ('screen', 'title', 'subtitle', 'view',
                     'tvlisting', 'info', 'plugin'))

CHAN_NO_DATA = _('This channel has no data loaded')

class TVGuide(Item):
    """
    Class for TVGuide
    """
    def __init__(self, start_time, player, menuw):
        Item.__init__(self)

        # get skin definitions of the TVGuide
        self.n_items, self.hours_per_page = skin.items_per_page(('tv', self))
        # end of visible guide
        stop_time = start_time + self.hours_per_page * 60 * 60

        # constructing the guide takes some time
        msgtext = _('Preparing the program guide')
        guide = epg_xmltv.get_guide(PopupBox(text=msgtext))
        # getting channels
        channels = guide.GetPrograms(start=start_time+1, stop=stop_time-1)
        if not channels:
            AlertBox(text=_('TV Guide is corrupt!')).show()
            return

        # select the first available program
        selected = None
        for chan in channels:
            if chan.programs:
                self.selected = chan.programs[0]
                break


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
        self.rebuild(start_time, stop_time, guide.chan_list[0].id, selected)
        menuw.pushmenu(self)


    def update_schedules(self, force=False):
        """
        update schedule

        reload the list of scheduled programs and check for overlapping
        """
        if not force and self.last_update + 60 > time.time():
            return

        # less than one second? Do not belive the force update
        #if self.last_update + 1 > time.time():
        #    return

        upsoon = '%s/upsoon' % (config.FREEVO_CACHEDIR)
        if os.path.isfile(upsoon):
            os.unlink(upsoon)

        _debug_('update schedule',2)
        self.last_update = time.time()
        self.scheduled_programs = []
        self.overlap_programs = []
        self.favorite_programs = []
        (got_schedule, schedule) = ri.getScheduledRecordings()

        util.misc.comingup(None, (got_schedule, schedule))

        if got_schedule:
            progs = schedule.getProgramList()

            for k in progs:
                prog = progs[k]
                self.scheduled_programs.append(prog.str2utf())
                if prog.overlap:
                    self.overlap_programs.append(prog.str2utf())
                if hasattr(prog, 'isFavorite' ) and prog.isFavorite:
                    self.favorite_programs.append(prog.str2utf())

### event handler

    def eventhandler(self, event, menuw=None):
        """
        Handles events in the tv guide
        """
        _debug_('TVGUIDE EVENT is %s' % event)
        event_consumed = False

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
            event_consumed = True

        ## MENU_UP: Move one channel up in the guide
        if event == MENU_UP:
            self.change_channel(-1)
            event_consumed = True

        ## MENU_DOWN: Move one channel down in the guide
        elif event == MENU_DOWN:
            self.change_channel(1)
            event_consumed = True

        ## MENU_LEFT: Move to the next program on this channel
        elif event == MENU_LEFT:
            self.change_program(-1)
            event_consumed = True

        ## MENU_RIGHT: Move to previous programm on this channel
        elif event == MENU_RIGHT:
            self.change_program(1)
            event_consumed = True

        ## MENU_PAGEUP: Moves to the first of the currently displayed channels
        elif event == MENU_PAGEUP:
            self.change_channel(-self.n_items)
            event_consumed = True

        ## MENU_PAGEDOWN: Move to the last of the currently displayed channels
        elif event == MENU_PAGEDOWN:
            self.change_channel(self.n_items)
            event_consumed = True


        ## MENU_SUBMENU: Open a submenu for the selected program
        elif event == MENU_SUBMENU:
            # create a ProgramItem for the selected program
            pi = ProgramItem(self, prog=self.selected, context='guide')
            #and show its submenu
            pi.display_submenu(menuw=self.menuw)
            event_consumed = True

        ## MENU_SELECT: Show the description
        elif event == MENU_SELECT:
            # create a ProgramItem for the selected program
            pi = ProgramItem(self, prog=self.selected, context='guide')
            #and show selecte the first action in the actions list
            pi.actions()[0][0](menuw=self.menuw)
            event_consumed = True

        ## TV_START_RECORDING: add or remove this program from schedule
        elif event == TV_START_RECORDING:
            pi = ProgramItem(self, prog=self.selected, context='guide')
            pi.toggle_rec(menuw=self.menuw)
            event_consumed = True

        ## PLAY: Start to watch the selected channel (if it is possible)
        elif event == PLAY:
            # create a ProgramItem for the selected program
            pi = ProgramItem(self, prog=self.selected, context='guide')
            #and show its submenu
            pi.play(menuw=self.menuw)
            event_consumed = True

        ## PLAY_END: Show the guide again
        elif event == PLAY_END:
            self.show()
            event_consumed = True

        # FIX or REMOVE:
        # the numerical INPUT events are not available in the tvmenu context
        ## numerical INPUT: Jump to a specific channel number
        if str(event).startswith("INPUT_"):
            # tune explicit channel
            eventInput=str(event)[6]
            isNumeric=TRUE
            try:
                newinput_value = int(eventInput)
            except:
                #Protected against INPUT_UP, INPUT_DOWN, etc
                isNumeric=FALSE
            if isNumeric:
                newinput_time = int(time.time())
                if (self.lastinput_value != None):
                    # allow 1 seconds delay for multiple digit channels
                    if (newinput_time - self.lastinput_time < 1):
                        # this enables multiple (max 3) digit channel selection
                        if (self.lastinput_value >= 100):
                            self.lastinput_value = (self.lastinput_value % 100)
                        newinput_value += self.lastinput_value * 10
                self.lastinput_value = newinput_value
                self.lastinput_time = newinput_time

                channel_no = int(newinput_value)-1
                if channel_no < len(self.guide.chan_list):
                    self.start_channel = self.guide.chan_list[channel_no].id
                else:
                    self.lastinput_value = None

                self.rebuild(self.start_time, self.stop_time,
                             self.start_channel, self.selected)
                event_consumed = True

        return event_consumed


    ### gui functions

    def show(self):
        """ show the guide"""
        _debug_('show',2)
        if not self.visible:
            self.visible = 1
            self.refresh()


    def hide(self):
        """ hide the guide"""
        _debug_('hide',2)
        if self.visible:
            self.visible = 0
            skin.clear()


    def refresh(self, force_update=True):
        """refresh the guide

        This function is called automatically by freevo whenever this menu is
        opened or reopened.
        """
        _debug_('refresh',2)
        if self.menuw.children:
            return
        _debug_('tvguide: setting context to %s' % self.event_context, 2)
        rc.set_context(self.event_context)
        self.update(force_update)
        skin.draw(self.type, self)


    def update(self, force=False):
        """ update the guide

        This function updates the scheduled and overlap flags for
        all currently displayed programs.
        """
        _debug_('update',2)
        self.update_schedules(force)
        if self.table:
            for t in self.table:
                try:
                    for p in t.programs:
                        if p in self.scheduled_programs:
                            p.scheduled = TRUE
                            # DO NOT change this to 'True' Twisted
                            # does not support boolean objects and
                            # it will break under Python 2.3
                        else:
                            p.scheduled = FALSE
                            # Same as above; leave as 'FALSE' until
                            # Twisted includes Boolean
                        if p in self.overlap_programs:
                            p.overlap = TRUE
                        else:
                            p.overlap = FALSE

                        if p in self.favorite_programs:
                            p.favorite = TRUE
                        else:
                            p.favorite = FALSE
                except:
                    pass

        #self.refresh()


    def jump_to_now(self, old_selected):
        """
        jump to now in the tv guide.
        """
        start_time = time.time()
        stop_time = start_time + self.hours_per_page * 60 * 60
        start_channel = self.start_channel

        # we need to determine the program,
        # that is running now at the selected channel
        programs = self.guide.GetPrograms(start = start_time+1,
                                          stop = stop_time-1,
                                          chanids = old_selected.channel_id)

        if (len(programs) > 0) and (len(programs[0].programs) > 0):
            selected = programs[0].programs[0]
        else:
            selected = None

        self.rebuild(start_time, stop_time, start_channel, selected)


    def advance_tv_guide(self, hours=0):
        """
        advance the tv guide by the number of hours that is passed in arg.
        """
        new_start_time = self.start_time + (hours * 60 * 60)
        new_end_time =  self.stop_time + (hours * 60 * 60)
        start_channel = self.start_channel

        # we need to determine the new selected program
        programs = self.guide.GetPrograms(start = new_start_time+1,
                                          stop = new_end_time-1,
                                          chanids = self.start_channel)

        if (len(programs) > 0) and (len(programs[0].programs) > 0):
            selected = programs[0].programs[0]
        else:
            selected = None

        self.rebuild(new_start_time,new_end_time, start_channel, selected)


    def rebuild(self, start_time, stop_time, start_channel, selected):
        """ rebuild the guide

        This is neccessary we change the set of programs that have to be
        displayed, this is the case when the user moves around in the menu.
        """
        _debug_('reload',2)
        self.guide = epg_xmltv.get_guide()
        channels = self.guide.GetPrograms(start=start_time+1, stop=stop_time-1)

        table = [ ]

        self.start_time    = start_time
        self.stop_time     = stop_time
        self.start_channel = start_channel
        self.selected      = selected

        self.display_up_arrow   = FALSE
        self.display_down_arrow = FALSE

        # table header
        table += [ ['Chan'] ]
        for i in range(int(self.n_cols)):
            table[0] += [ start_time + self.col_time * i* 60 ]

        table += [ self.selected ] # the selected program

        found_1stchannel = 0
        if stop_time == None:
            found_1stchannel = 1

        flag_selected = 0

        n = 0
        for chan in channels:
            if n >= self.n_items:
                self.display_down_arrow = TRUE
                break

            if start_channel != None and chan.id == start_channel:
                found_1stchannel = 1

            if not found_1stchannel:
                self.display_up_arrow = TRUE

            if found_1stchannel:
                if not chan.programs:
                    prg = epg_types.TvProgram()
                    prg.channel_id = chan.id
                    prg.start = 0
                    prg.stop = 2147483647   # Year 2038
                    prg.title = CHAN_NO_DATA
                    prg.desc = ''
                    chan.programs = [ prg ]


                for i in range(len(chan.programs)):
                    if selected:
                        if chan.programs[i] == selected:
                            flag_selected = 1

                table += [  chan  ]
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
        start_time    = self.start_time
        stop_time     = self.stop_time
        start_channel = self.start_channel
        last_prg      = self.selected

        channel = self.guide.chan_dict[last_prg.channel_id]
        if full_scan:
            all_programs = self.guide.GetPrograms(start_time-24*60*60,
                                                  stop_time+24*60*60,
                                                  [ channel.id ])
        else:
            all_programs = self.guide.GetPrograms(start_time+1,
                                                  stop_time-1,
                                                  [ channel.id ])

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
                if i+value >= 0:
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
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)


    def change_channel(self, value):
        """
        Move to the next channel
        """
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


        programs = self.guide.GetPrograms(start_time+1, stop_time-1, [ channel.id ])
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
            prg = epg_types.TvProgram()
            prg.channel_id = channel.id
            prg.start = 0
            prg.stop = 2147483647   # Year 2038
            prg.title = CHAN_NO_DATA
            prg.desc = ''
            to_info = CHAN_NO_DATA

        self.rebuild(start_time, stop_time, start_channel, prg)
