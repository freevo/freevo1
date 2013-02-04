# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Information and actions for TV Programmes.
# -----------------------------------------------------------------------
# $Id$
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
import logging
logger = logging.getLogger("freevo.tv.programitem")

import time
import os

import config
import menu
import rc
import skin

import dialog
from dialog.dialogs import ButtonDialog,ProgressDialog

from skin.widgets import ScrollableTextScreen
from event import *
from item import Item
from favoriteitem import FavoriteItem

import util.tv_util as tv_util
from tv.record_client import RecordClient
from tv.channels import FreevoChannels, CHANNEL_ID
from tv.record_types import Favorite

import plugin

class ProgramItem(Item):
    """
    Item class for program items

    This is used in the tv guide
    and in the list of schedules recordings.
    """
    def __init__(self, parent, prog, context='menu'):
        Item.__init__(self, parent, skin_type='video')
        logger.log( 9, '__init__(parent=%r, prog=%r, context=%r)', parent, prog, context)
        # prog is a TvProgram object as we get it from the recordserver
        self.prog = prog
        self.context= context

        if hasattr(prog, 'name'): self.name = self.title = prog.name
        if hasattr(prog, 'title'): self.title = self.name = Unicode(prog.title)
        if hasattr(prog, 'sub_title'): self.sub_title = prog.sub_title
        if hasattr(prog, 'desc'): self.description = prog.desc
        if hasattr(prog, 'categories'):self.categories = prog.categories
        if hasattr(prog, 'ratings'): self.ratings = prog.ratings
        if hasattr(prog, 'advisories'): self.advisories = prog.advisories

        self.channel = tv_util.get_chan_displayname(prog.channel_id)
        if hasattr(prog, 'scheduled'):
            self.scheduled = prog.scheduled
        else:
            self.scheduled = False

        self.favorite = False
        if hasattr(prog, 'allowDuplicates'):
            self.allowDuplicates = prog.allowDuplicates
        else:
            self.allowDuplicates = 1

        if hasattr(prog, 'onlyNew'):
            self.onlyNew = prog.onlyNew
        else:
            self.onlyNew = 0

        self.overlap = prog.overlap

        self.start = time.strftime(config.TV_DATETIME_FORMAT, time.localtime(prog.start))
        self.stop = time.strftime(config.TV_DATETIME_FORMAT, time.localtime(prog.stop))
        self.recordclient = RecordClient()


    def actions(self):
        """ List of actions """
        logger.log( 9, 'actions()')
        #list of entries for the menu
        items = []

        #'Play', if this programm is currently running or starts soon
        if self.context == 'guide':
            items.append((self.play, _('Play')))
            #now = time.time()
            #if self.prog.start <= now+(7*60) and self.prog.stop > now:
            #    items.append((self.play, _('Play')))

        # 'Show full description'
        items.append((self.show_description, _('Full Description')))

        if self.recordclient.pingNow():

            # 'Schedule for recording' OR 'Remove from schedule'
            (status, reason) = self.recordclient.isProgScheduledNow(self.prog)
            self.scheduled = status
            if self.scheduled:
                items.append((self.remove_program, _('Remove from schedule')))
            else:
                items.append((self.schedule_program, _('Schedule for recording')))

            # 'Add to favorites' OR 'Remove from favorites'
            (status, reason) = self.recordclient.isProgAFavoriteNow(self.prog)
            self.favorite = status
            if self.favorite:
                items.append((self.edit_favorite, _('Edit favorite')))
            else:
                items.append((self.add_favorite, _('Add to favorites')))

        plugins_list = plugin.get('tv_program')
        for p in plugins_list:
            items += p.items(self)

        return items


    ### Actions:

    def play(self, arg=None, menuw=None):
        """ Start watching TV """
        logger.log( 9, 'play(arg=%r, menuw=%r)', arg, menuw)
        # watching TV should only be possible from the guide
        if not self.context == 'guide':
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
                confirmbtn = _('Remove')
            else:
                msgtext = _('This Program is in the future. Do you want to record it?')
                confirmbtn = _('Record')
            dialog.show_confirmation(msgtext, lambda: self.toggle_rec(menuw=menuw), proceed_text=confirmbtn)
            return
        else:
            # check if the device is free
            fc = FreevoChannels()
            # for that we need the name of the lock file
            suffix = fc.getVideoGroup(self.prog.channel_id, True, CHANNEL_ID).vdev
            suffix = suffix.split('/')[-1]
            tvlockfile = config.FREEVO_CACHEDIR + '/record.'+suffix
            if os.path.exists(tvlockfile):
                if menuw: menuw.show()
                # XXX: In the future add the options to watch what we are
                #      recording or cancel it and watch TV.
                msgtext = _('Sorry, you cannot watch TV while recording. ')
                msgtext += _('If this is not true then remove ')
                msgtext += tvlockfile + '.'
                dialog.show_alert(msgtext)
            else:
                # everything is ok, we can start watching!
                self.parent.hide()
                self.parent.player('tv', self.prog.channel_id)


    def show_description(self, arg=None, menuw=None):
        """ View a full scrollable description of the program.  """
        logger.log( 9, 'show_description(arg=%r, menuw=%r)', arg, menuw)
        ShowProgramDetails(menuw, self)


    def toggle_rec(self, arg=None, menuw=None):
        """ Schedule or unschedule this program, depending on its current status """
        logger.log( 9, 'toggle_rec(arg=%r, menuw=%r)', arg, menuw)
        if self.scheduled:
            # remove this program from schedule it it is already scheduled
            self.remove_program(menuw=menuw)
        else:
            # otherwise add it to schedule without more questions
            self.schedule_program(menuw=menuw)


    def schedule_program(self, arg=None, menuw=None):
        """ Add a program to schedule """
        logger.log( 9, 'schedule_program(arg=%r, menuw=%r)', arg, menuw)
        # schedule the program
        (status, reason) = self.recordclient.scheduleRecordingNow(self.prog)
        if status == 'ok':
            self.scheduled = True
            menuw.delete_submenu(refresh=False)
            if hasattr(self.parent, 'update'):
                self.parent.update(force=True)
            else:
                menuw.refresh(reload=True)
            msgtext= _('"%s" has been scheduled for recording') % self.name
        elif status == 'conflict':
            msgtext=_('Conflict detected!')
            self.resolve_conflict(menuw, reason)
            return
        else:
            # something went wrong
            msgtext = _('Scheduling failed: ')+ _(reason)

        dialog.show_message(msgtext)


    def remove_program(self, arg=None, menuw=None):
        """ Remove a program from schedule """
        logger.log( 9, 'remove_program(arg=%r, menuw=%r)', arg, menuw)
        # remove the program
        (status, reason) = self.recordclient.removeScheduledRecordingNow(self.prog)
        if status:
            self.scheduled = False
            menuw.delete_submenu(refresh=False)
            if hasattr(self.parent, 'update'):
                self.parent.update(force=True)
            else:
                menuw.refresh(reload=True)
            msgtext = _('"%s" has been removed from schedule') % self.name
        else:
            # something went wrong
            msgtext = _('Remove failed')+(':\n%s' % reason)
        dialog.show_message(msgtext)


    def add_favorite(self, arg=None, menuw=None):
        """ Add a program to favorites """
        logger.log( 9, 'add_favorite(arg=%r, menuw=%r)', arg, menuw)
        if menuw:
            menuw.delete_submenu(refresh=False)
        # create a favorite
        fav = Favorite(self.title, self.prog, True, True, True, -1, True, False)
        logger.log( 9, 'self.title=%r, self.prog=%r, fav.__dict__=%r)', self.title, self.prog, fav.__dict__)
        # and a favorite item which represents the submen
        fav_item = FavoriteItem(self, fav, fav_action='add')
        # and open that submenu
        fav_item.display_submenu(menuw=menuw)


    def edit_favorite(self, arg=None, menuw=None):
        """
        Edit the settings of a favorite
        """
        logger.log( 9, 'edit_favorite(arg=%r, menuw=%r)', arg, menuw)
        if menuw:
            menuw.delete_submenu(refresh=False)

        # get the favorite from the record client
        (got_fav, fav) = self.recordclient.getFavoriteObjectNow(self.prog)
        if got_fav:
            # create a favorite item for the submenu
            fav_item = FavoriteItem(self, fav, fav_action='edit')
            # and open the submenu
            fav_item.display_submenu(menuw=menuw)
        else:
            dialog.show_alert(_('Cannot edit favorite %s') % self.name)


    def display_submenu(self, arg=None, menuw=None):
        """
        Open the submenu for this item
        """
        logger.log( 9, 'display_submenu(arg=%r, menuw=%r)', arg, menuw)
        if not menuw:
            return
        # this tries to imitated freevo's internal way of creating submenus
        menuw.make_submenu(_('Program Menu'), self.actions(), self)
        menuw.show()

    def resolve_conflict(self, menuw, conflictingProgs):
        prog_text = self.prog.getattr('time') + u' ' + self.prog.title
        other_prog_text = u''
        menu_items = []
        for progs in conflictingProgs:
            remove_text = ''
            for cprog in progs:
                if other_prog_text:
                    other_prog_text += u'\n'
                other_prog_text += cprog.getattr('time') + u' ' + cprog.title
                if not remove_text:
                    remove_text = cprog.title
                else:
                    remove_text += u', ' + cprog.title
            other_prog_text += u'\n\n'
            menu_items.append(menu.MenuItem(_('Remove ') + remove_text, self.remove_and_schedule, progs))
        self.conflict_info = _('How do you want to resolve the conflict?\n%s\nconflicts with\n%s') % (prog_text, other_prog_text)
        menu_items.append(menu.MenuItem(_('Cancel scheduling ') + self.prog.title, menuw.back_one_menu))

        conflict_menu = menu.Menu(_('Resovle Conflict'), menu_items, item_types='tv conflict menu')
        conflict_menu.infoitem = self
        menuw.delete_submenu(refresh = False)
        menuw.pushmenu(conflict_menu)
        menuw.refresh()


    def remove_and_schedule(self, arg=None, menuw=None):
        for prog in arg:
            self.recordclient.removeScheduledRecordingNow(prog)
        menuw.back_one_menu()
        self.schedule_program(menuw=menuw)


# Create the skin_object object
skin_object = skin.get_singleton()
skin_object.register('tvguideinfo', ('screen', 'info', 'scrollabletext', 'plugin'))



class ShowProgramDetails(ScrollableTextScreen):
    """
    Screen to show the details of the TV programme
    """
    def __init__(self, menuw, prg):
        logger.log( 9, 'ShowProgramDetails.__init__(menuw=%r, prg=%r)', menuw, prg)
        if prg is None:
            name = _('No Information Available')
        else:
            self.program = prg
            name = prg.title
            # gather the info and construct the description text
            if hasattr(prg, 'sub_title') and  prg.sub_title:
            # subtitle + newline + description
                description = u'"' + Unicode(prg.sub_title) + u'"\n' + Unicode(prg.description)
            else:
                # or just the description, if there is no subtitle
                description = Unicode(prg.description)

            if prg.prog.date:
                description += u'\n\n' + _('Date : ') + prg.prog.date
            
            # maybe there is more info to add (categories, advisories, ratings)
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
        """ get programme attributes """
        logger.log( 9, 'getattr(name=%r)', name)
        if name == 'title':
            return self.name

        if name == 'datetime':
            return self.program.prog.getattr('date') + u' ' + self.program.prog.getattr('time')

        if self.program:
            result = self.program.getattr(name)
            if not result:
                result = self.program.self.program.prog.getattr(name)
            return result
        return u''


    def eventhandler(self, event, menuw=None):
        """ event handler for the programme description display """
        logger.log( 9, 'eventhandler(event=%r, menuw=%r)', event, menuw)
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
