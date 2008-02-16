# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# guide_ProgramItem - Information and actions for TvPrograms.
# -----------------------------------------------------------------------
# $Id:
#
# Todo:
# Notes:
#
# -----------------------------------------------------------------------
#
# Freevo - A Home Theater PC framework
#
# Copyright (C) 2002 Krister Lagerstrom, et al.
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
# ----------------------------------------------------------------------

import time, os

import config, menu, rc, skin

from skin.widgets import ScrollableTextScreen
from event import *
from item import Item
from favoriteitem import FavoriteItem

import util.tv_util as tv_util
from tv.record_client import RecordClient
from tv.channels import FreevoChannels
from tv.record_types import Favorite


from gui.PopupBox import PopupBox
from gui.AlertBox import AlertBox
from gui.ConfirmBox import ConfirmBox

class ProgramItem(Item):
    """
    Item class for program items

    This is used in the tv guide
    and in the list of schedules recordings.
    """
    def __init__(self, parent, prog, context='menu'):
        Item.__init__(self, parent, skin_type='video')
        _debug_('__init__(parent=%r, prog=%r, context=%r)' % (parent, prog, context), 2)
        # prog is a TvProgram object as we get it from the recordserver
        self.prog = prog
        self.context= context

        if hasattr(prog, 'name'): self.name = self.title = prog.name
        if hasattr(prog, 'title'): self.title = self.name = prog.title
        if hasattr(prog, 'sub_title'): self.sub_title = prog.sub_title
        if hasattr(prog, 'desc'): self.description = prog.desc

        # categories
        if hasattr(prog, 'categories'):self.categories = prog.categories
        # ratings
        if hasattr(prog, 'ratings'): self.ratings = prog.ratings
        # advisories
        if hasattr(prog, 'advisories'): self.advisories = prog.advisories

        # channel where this program is running
        self.channel = tv_util.get_chan_displayname(prog.channel_id)

        # check if the prog is scheduled for recording
        if hasattr(prog, 'scheduled'):
            self.scheduled = prog.scheduled
        else:
            self.scheduled = False

        # more infos from the TvProgam object
        self.allowDuplicates = prog.allowDuplicates
        self.onlyNew = prog.onlyNew
        self.overlap = prog.overlap

        # defaults to not favorite
        self.favorite = False

        self.start = time.strftime(config.TV_DATETIME_FORMAT, time.localtime(prog.start))
        self.stop = time.strftime(config.TV_DATETIME_FORMAT, time.localtime(prog.stop))
        self.recordclient = RecordClient()

    def actions(self):
        """ List of actions """
        _debug_('actions()', 2)
        #list of entries for the menu
        items = []

        ##'Play', if this programm is currently running or starts soon
        # check the time
        if self.context=='guide':
            now = time.time()
            if self.prog.start <= now+(7*60) and self.prog.stop > now:
                items.append((self.play, _('Play')))

        ## 'Show full description'
        items.append((self.show_description, _('Full Description')))

        ## 'Schedule for recording' OR 'Remove from schedule'
        # check if this program is scheduled
        schedule = self.recordclient.getScheduledRecordingsNow()
        if schedule:
            (result, message) = self.recordclient.isProgScheduledNow(self.prog, schedule.getProgramList())
            if result:
                self.scheduled = True
            else:
                self.scheduled = False

        if self.scheduled:
            items.append((self.remove_program, _('Remove from schedule')))
        else:
            items.append((self.schedule_program, _('Schedule for recording')))

        ## 'Add to favorites' OR 'Remove from favorites'
        # check if this program is a favorite
        (result, message) = self.recordclient.isProgAFavoriteNow(self.prog)
        if result:
            self.favorite = True

        if self.favorite:
            items.append((self.edit_favorite, _('Edit favorite')))
        else:
            items.append((self.add_favorite, _('Add to favorites')))

        ## 'Seach for more of this'
        if not self.context == 'search':
            items.append((self.find_more, _('Search for more of this program')))

        return items


    ### Actions:

    def play(self, arg=None, menuw=None):
        """
        Start watching TV
        """
        _debug_('play(arg=%r, menuw=%r)' % (arg, menuw), 2)
        # watching TV should only be possible from the guide
        if not self.context=='guide':
            rc.post_event(MENU_SELECT)
            return
        now = time.time()
        if menuw: menuw.delete_submenu()
        # Check if the selected program is >7 min in the future
        if self.prog.start > now + (7*60):
            if menuw: menuw.show()
            # this program is in the future
            if self.scheduled:
                msgtext= _('Do you want to remove the Program from the record schedule?')
            else:
                msgtext = _('This Program is in the future. Do you want to record it?')

            ConfirmBox(text=msgtext, handler=lambda: self.toggle_rec(menuw=menuw), default_choice=1).show()
            return
        else:
            # check if the device is free
            fc = FreevoChannels()
            # for that we need the name of the lock file
            suffix = fc.getVideoGroup(self.prog.channel_id, True).vdev
            suffix = suffix.split('/')[-1]
            tvlockfile = config.FREEVO_CACHEDIR + '/record.'+suffix
            if os.path.exists(tvlockfile):
                if menuw: menuw.show()
                # XXX: In the future add the options to watch what we are
                #      recording or cancel it and watch TV.
                msgtext = _('Sorry, you cannot watch TV while recording. ')
                msgtext+= _('If this is not true then remove ')
                msgtext+= tvlockfile + '.'
                AlertBox(text=msgtext, height=200).show()
            else:
                # everything is ok, we can start watching!
                self.parent.hide()
                self.parent.player('tv', self.prog.channel_id)


    def show_description(self, arg=None, menuw=None):
        """
        View a full scrollable description of the program.
        """
        _debug_('show_description(arg=%r, menuw=%r)' % (arg, menuw), 2)
        ShowProgramDetails(menuw, self)


    def toggle_rec(self, arg=None, menuw=None):
        """
        schedule or unschedule this program, depending on its current status
        """
        _debug_('toggle_rec(arg=%r, menuw=%r)' % (arg, menuw), 2)
        if self.scheduled:
            # remove this program from schedule it it is already scheduled
            self.remove_program(menuw=menuw)
            self.scheduled = False
        else:
            # otherwise add it to schedule without more questions
            self.schedule_program(menuw=menuw)
            self.scheduled = True


    def schedule_program(self, arg=None, menuw=None):
        """
        Add a program to schedule
        """
        _debug_('schedule_program(arg=%r, menuw=%r)' % (arg, menuw), 2)
        # schedule the program
        (result, msg) = self.recordclient.scheduleRecordingNow(self.prog)
        if result:
            menuw.delete_submenu(refresh=False)
            if hasattr(self.parent, 'update'):
                self.parent.update(force=True)
            else:
                menuw.refresh(reload=True)
            msgtext= _('"%s" has been scheduled for recording') % self.name
            pop = AlertBox(text=msgtext).show()
        else:
            # something went wrong
            msgtext = _('Scheduling failed')+(': %s' % msg)
            AlertBox(text=msgtext).show()


    def remove_program(self, arg=None, menuw=None):
        """
        Remove a program from schedule
        """
        _debug_('remove_program(arg=%r, menuw=%r)' % (arg, menuw), 2)
        # remove the program
        (result, msg) = self.recordclient.removeScheduledRecordingNow(self.prog)
        if result:
            menuw.delete_submenu(refresh=False)
            if hasattr(self.parent, 'update'):
                self.parent.update(force=True)
            else:
                menuw.refresh(reload=True)
            msgtext = _('"%s" has been removed from schedule') % self.name
            AlertBox(text=msgtext).show()
        else:
            # something went wrong
            msgtext = _('Remove failed')+(': %s' % msg)
            AlertBox(text=msgtext).show()


    def add_favorite(self, arg=None, menuw=None):
        """
        Add a program to favorites
        """
        _debug_('add_favorite(arg=%r, menuw=%r)' % (arg, menuw), 2)
        if menuw:
            menuw.delete_submenu(refresh=False)
        # create a favorite
        fav = Favorite(self.title, self.prog, True, True, True, -1, True, False)
        _debug_('self.title=%r, self.prog=%r, fav.__dict__=%r)' % (self.title, self.prog, fav.__dict__), 2)
        # and a favorite item which represents the submen
        fav_item = FavoriteItem(self, fav, fav_action='add')
        # and open that submenu
        fav_item.display_submenu(menuw=menuw)


    def edit_favorite(self, arg=None, menuw=None):
        """
        Edit the settings of a favorite
        """
        _debug_('edit_favorite(arg=%r, menuw=%r)' % (arg, menuw), 2)
        if menuw:
            menuw.delete_submenu(refresh=False)

        # get the favorite from the record_client
        (got_fav, fav) = self.recordclient.getFavoriteObjectNow(self.prog)
        if got_fav:
            # create a favorite item for the submenu
            fav_item = FavoriteItem(self, fav, fav_action='edit')
            # and open the submenu
            fav_item.display_submenu(menuw=menuw)
        else:
            msgtext=_('getFavorites failed')+(':%s' % self.name)
            AlertBox(text=msgtext).show()


    def find_more(self, arg=None, menuw=None):
        """
        Find more of this program
        """
        _debug_('find_more(arg=%r, menuw=%r)' % (arg, menuw), 2)

        # this might take some time, thus we open a popup messages
        _debug_(String('searching for: %s' % self.title), 2)
        pop = PopupBox(text=_('Searching, please wait...'))
        pop.show()
        # do the search
        (result, matches) = self.recordclient.findMatchesNow(self.title)
        # we are ready -> kill the popup message
        pop.destroy()
        if result:
            # we have been successful!
            items = []
            _debug_('search found %s matches' % len(matches), 2)
            # sort by start times
            f = lambda a, b: cmp(a.start, b.start)
            matches.sort(f)
            for prog in matches:
                items.append(ProgramItem(self.parent, prog, context='search'))
        elif matches == 'no matches':
                # there have been no matches
            msgtext = _('No matches found for %s') % self.title
            AlertBox(text=msgtext).show()
            return
        else:
            # something else went wrong
            msgtext = _('findMatches failed') +(': %s' % matches)
            AlertBox(text=msgtext).show()
            return

        # create a menu from the search result
        search_menu = menu.Menu(_('Search Results'), items, item_types='tv program menu')
        # do not return from the search list to the submenu
        # where the search was initiated
        menuw.delete_submenu(refresh = False)
        menuw.pushmenu(search_menu)
        menuw.refresh()


    def display_submenu(self, arg=None, menuw=None):
        """
        Open the submenu for this item
        """
        _debug_('display_submenu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        if not menuw:
            return
        # this tries to imitated freevo's internal way of creating submenus
        menuw.make_submenu(_('Program Menu'), self.actions(), self)
        menuw.show()


# Create the skin_object object
skin_object = skin.get_singleton()
skin_object.register('tvguideinfo', ('screen', 'info', 'scrollabletext', 'plugin'))

# Program Info screen
class ShowProgramDetails(ScrollableTextScreen):
    """
    Screen to show the details of the TV program
    """
    def __init__(self, menuw, prg):
        _debug_('ShowProgramDetails.__init__(menuw=%r, prg=%r)' % (menuw, prg), 2)
        if prg is None:
            name = _('No Information Available')
            sub_title = ''
            time = ''
            description = ''
        else:
            self.program = prg
            name = prg.name
            sub_title = prg.sub_title
            # gather the infos and construct the description text
            if sub_title:
            # subtitle + newline + description
                description = u'"' + sub_title + u'"\n' + prg.description
            else:
                # or just the description, if there is no subtitle
                description = prg.description

            # maybe there is more infos to add (categories, advisories, ratings)
            if prg.categories:
                description += u'\n'
                for category in prg.categories:
                    description += u'\n' + _('Category : ') + category

            if prg.advisories:
                description += u'\n'
                for advisory in prg.advisories:
                    description += u'\n' + _('Advisory : ') + advisory

            if prg.ratings:
                description += u'\n'
                for system, value in prg.ratings.items():
                    description += u'\n' + _('Rating') + u'(' + system + u') : ' + value

        # that's all, we can show this to the user
        ScrollableTextScreen.__init__(self, 'tvguideinfo', description)
        self.name = name
        self.event_context = 'tvmenu'
        self.show(menuw)



    def getattr(self, name):
        """
        """
        _debug_('getattr(name=%r)' % (name,), 2)
        if name == 'title':
            return self.name

        if self.program:
            return self.program.getattr(name)

        return u''


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for the programm description display
        """
        _debug_('eventhandler(event=%r, menuw=%r)' % (event, menuw), 2)
        menuw = self.menuw
        event_consumed = ScrollableTextScreen.eventhandler(self, event, menuw)
        if not event_consumed:
            if event == PLAY:
                menuw.delete_menu()
                # try to watch this program
                self.program.play(menuw=menuw)
                event_consumed = True
            elif event == TV_START_RECORDING:
                menuw.delete_menu()
                # short cut to change the schedule status of this program
                self.program.toggle_rec(menuw=menuw)
                event_consumed = True

        return event_consumed
