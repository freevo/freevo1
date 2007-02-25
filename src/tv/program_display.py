# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ProgramDisplay - Information and actions for TvPrograms.
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


import time, traceback
from time import gmtime, strftime

import rc
import plugin, config, menu, string
import osd

import util.tv_util as tv_util
import tv.record_client as record_client
import event as em

from item import Item
from gui.AlertBox import AlertBox
from gui.InputBox import InputBox
from tv.record_types import Favorite

DEBUG = config.DEBUG


class ProgramItem(Item):
    """
    Item class for program items in the tv guide
    """
    def __init__(self, parent, prog, context='guide'):
        Item.__init__(self, parent, skin_type='video')
        self.prog = prog
        self.context = context

        self.name = self.title = prog.title
        if hasattr(prog,'sub_title'): self.sub_title = prog.sub_title
        if hasattr(prog,'desc'): self.desc = prog.desc
        self.channel = tv_util.get_chan_displayname(prog.channel_id)

        if hasattr(prog, 'scheduled'):
            self.scheduled = prog.scheduled
        else:
            self.scheduled = False

        self.allowDuplicates = prog.allowDuplicates

        self.onlyNew = prog.onlyNew

        self.overlap = prog.overlap

        self.favorite = False

        self.start = time.strftime(config.TV_DATETIMEFORMAT,
                                   time.localtime(prog.start))
        self.stop = time.strftime(config.TV_DATETIMEFORMAT,
                                       time.localtime(prog.stop))

        self.categories = ''
        try:
            for cat in prog.categories:
                if prog.categories.index(cat) > 0:
                    self.categories += ', %s' % cat
                else:
                    self.categories += '%s' % cat
        except AttributeError:
            pass

        self.ratings = ''
        try:
            for rat in prog.ratings.keys():
                self.ratings += '%s ' % rat
        except:
            pass


    def actions(self):
        return [( self.display_program , _('Display program') )]


    ### action menu
    def display_program(self, arg=None, menuw=None):
        """ creates the submenu for a programm

        Entries of this menu:
            0.) 'Play, if this programm is currently running'
            1.) 'Schedule for recording' OR 'Remove from schedule'
            2.) 'Search for more of this program'
            3.) 'Add to favorites' OR 'Remove from favorites'
        This function checks if the program is already scheduled or a favorite
        and chooses the appropriate menu entries.
        """

        #list of entries for the menu
        items = []

        ## 0.) 'Play', if this programm is currently running
        # check the time
        now = time.time() + (7*60)
        if self.prog.start <= now:
            items.append(menu.MenuItem(_('Play'), action= self.play_program))


        ## 1.) 'Schedule for recording' OR 'Remove from schedule'
        # check if this program is scheduled
        (got_schedule, schedule) = record_client.getScheduledRecordings()
        if got_schedule:
            (result, message) = record_client.isProgScheduled(self.prog,
                                               schedule.getProgramList())
            if result:
                self.scheduled = True
            else:
                self.scheduled = False

        if self.scheduled:
            items.append(menu.MenuItem(_('Remove from schedule'),
                                       action=self.remove_program))
        else:
            items.append(menu.MenuItem(_('Schedule for recording'),
                                       action=self.schedule_program))

        ## 2.) 'Seach for more of this menu
        if not self.context == 'search':
            items.append(menu.MenuItem(_('Search for more of this program'),
                                       action=self.find_more))

        ##3.) 'Add to favorites' OR 'Remove from favorites'
        # check if this program is a favorite
        (got_favs, favs) = record_client.getFavorites()
        if got_favs:
            (result, junk) = record_client.isProgAFavorite(self.prog, favs)
            if result:
                self.favorite = True

        if self.favorite:
            items.append(menu.MenuItem(_('Edit favorite'),
                                       action=self.edit_favorite))
        else:
            items.append(menu.MenuItem(_('Add to favorites'),
                                       action=self.add_favorite))

        ## Create the resulting menu
        program_menu = menu.Menu(_('Program Menu'), items,
                                 item_types = 'tv program menu')
        program_menu.infoitem = self
        menuw.pushmenu(program_menu)
        menuw.refresh()


    ### Actions:
    def play_program(self, arg=None, menuw=None):
        """ Play """
        menuw.delete_menu()
        rc.post_event('PLAY')


    def schedule_program(self, arg=None, menuw=None):
        """
        add a program to schedule
        """
        (result, msg) = record_client.scheduleRecording(self.prog)
        if result:
            if menuw:
                if self.context=='search':
                    menuw.delete_menu()
                    menuw.delete_menu()
                menuw.back_one_menu(arg='reload')
            msgtext= _('"%s" has been scheduled for recording') %self.prog.title
            AlertBox(text=msgtext).show()
        else:
            AlertBox(text=_('Scheduling Failed')+(': %s' % msg)).show()


    def remove_program(self, arg=None, menuw=None):
        """
        remove a program from schedule
        """
        (result, msg) = record_client.removeScheduledRecording(self.prog)
        if result:
            if menuw:
                menuw.back_one_menu(arg='reload')
            msgtext = _('"%s" has been removed from schedule') % self.prog.title
            AlertBox(text=msgtext).show()
        else:
            AlertBox(text=_('Remove Failed')+(': %s' % msg)).show()


    def find_more(self, arg=None, menuw=None):
        """
        Find more of this program
        """

        _debug_(String('searching for: %s' % self.prog.title))

        pop = AlertBox(text=_('Searching, please wait...'))
        pop.show()

        items = []
        (result, matches) = record_client.findMatches(self.prog.title)

        pop.destroy()
        if result:
            _debug_('search found %s matches' % len(matches))

            f = lambda a, b: cmp(a.start, b.start)
            matches.sort(f)
            for prog in matches:
                items.append(ProgramItem(self, prog, context='search'))
        else:
            if matches == 'no matches':
                msgtext = _('No matches found for %s') % self.prog.title
                AlertBox(text=msgtext).show()
                return
            AlertBox(text=_('findMatches failed: %s') % matches).show()
            return

        search_menu = menu.Menu(_( 'Search Results' ), items,
                                item_types = 'tv program menu')

        menuw.pushmenu(search_menu)
        menuw.refresh()


    def add_favorite(self, arg=None, menuw=None):
        """
        Add a program to favorites
        """
        if menuw:
            # we do not want to return to this menu,
            # if we delete it here, then later back_one_menu
            # brings us back to the tvguide
            menuw.delete_menu()
        # create a favorite
        fav = Favorite(self.prog.title, self.prog,
                       True, True, True, -1, True, False)
        # and a favorite item which represents the submen
        fav_item = FavoriteItem(self, fav, fav_action='add')
        # and open that submenu
        fav_item.display_favorite(menuw=menuw)


    def edit_favorite(self, arg=None, menuw=None):
        """
        Edit the settings of a favorite
        """
        if menuw:
            # we do not want to return to this menu,
            # if we delete it here, then later back_one_menu
            # brings us back to the tvguide
            menuw.delete_menu()
        # fist we have to construct the favorite name
        # (get rid of strange characters like german umlauts)
        name = tv_util.progname2favname(self.name)
        # get the favorite from the record_client
        (got_fav, fav) = record_client.getFavorite(name)
        if got_fav:
            # create a favorite item for the submenu
            fav_item = FavoriteItem(self, fav, fav_action='edit')
            # and open the submenu
            fav_item.display_favorite(menuw=menuw)
        else:
            AlertBox(text=_('getFavorites failed: %s') % self.name).show()



class FavoriteItem(Item):
    """
    Item class for favorite items
    """
    def __init__(self, parent, fav, fav_action='edit'):
        Item.__init__(self, parent, skin_type='video')
        self.fav   = fav
        self.name  = self.origname = fav.name
        self.title = fav.title
        self.fav_action = fav_action
        if hasattr(fav,'allowDuplicates'):
           self.allowDuplicates = fav.allowDuplicates
        else:
           self.allowDuplicates = 1
        if hasattr(fav,'onlyNew'):
           self.onlyNew = fav.onlyNew
        else:
           self.onlyNew = 0

        self.week_days = (_('Mon'), _('Tue'), _('Wed'), _('Thu'),
                          _('Fri'), _('Sat'), _('Sun'))

        if fav.channel == 'ANY':
            self.channel = _('ANY CHANNEL')
        else:
            self.channel = fav.channel
        if fav.dow == 'ANY':
            self.dow = _('ANY DAY')
        else:
            self.dow = self.week_days[int(fav.dow)]
        if fav.mod == 'ANY':
            self.mod = _('ANY TIME')
        else:
            try:
                self.mod = strftime(config.TV_TIMEFORMAT,
                                    gmtime(float(int(fav.mod) * 60)))
            except:
                print 'Cannot add "%s" to favorites' % fav.name

        # needed by the inputbox handler
        self.menuw = None


    def actions(self):
        return [( self.display_favorite , _('Display favorite') )]


    def display_favorite(self, arg=None, menuw=None):
        """ Display menu for a favorite

        With this menu the user can made a program a favorite.
        All attributes of a favorite can be edited here and in the end
        the user must select 'save changes' to finally create the favorite.
        """

        ### create menu items for editing the favorites attributes
        items = []

        items.append(menu.MenuItem(_('Modify name'),
                                    action=self.mod_name))
        items.append(menu.MenuItem(_('Modify channel'),
                                    action=self.mod_channel))
        items.append(menu.MenuItem(_('Modify day of week'),
                                    action=self.mod_day))
        items.append(menu.MenuItem(_('Modify time of day'),
                                    action=self.mod_time))

        if config.DUPLICATE_DETECTION:
           items.append(menu.MenuItem(_('Modify duplicate flag'),
                                       action=self.mod_dup))

        if config.ONLY_NEW_DETECTION:
           items.append(menu.MenuItem(_('Modify episodes flag'),
                                        action=self.mod_new))

        # XXX: priorities aren't quite supported yet
        if 0:
            (got_favs, favs) = record_client.getFavorites()
            if got_favs and len(favs) > 1:
                items.append(menu.MenuItem(_('Modify priority'),
                                           action=self.mod_priority))


        ### save favorite
        items.append(menu.MenuItem(_('Save changes'),
                                    action=self.save_changes))

        ### remove this program from favorites
        if not self.fav_action == 'add':
            items.append(menu.MenuItem(_('Remove favorite'),
                                       action=self.rem_favorite))

        ### put the whole menu together
        favorite_menu = menu.Menu(_('Favorite Menu'), items,
                                  item_types = 'tv favorite menu')

        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    ### Actions:

    def mod_name(self, arg=None, menuw=None):
        """ Modify name

        This opens a input box to ask the user for a new name for this favorite.
        The default name of a favorite is the name of the program.
        """
        self.menuw = menuw
        InputBox(text=_('Alter Name'), handler=self.alter_name,
                 width = osd.get_singleton().width - config.OSD_OVERSCAN_X - 20,
                 input_text=self.name).show()


    def alter_name(self, name):
        """ set the new name"""
        if name:
            self.name = self.fav.name = name.strip()

        self.menuw.refresh()

    def mod_dup(self, arg=None, menuw=None):
        """ Modify duplication flag

        This opens a submenu where the user can change the settings for the
        duplication detection.
        """
        items = []
        items.append(menu.MenuItem('Allow Duplicates', action=self.alter_prop,
                                   arg=('dup', 'True')))
        items.append(menu.MenuItem('Prevent Duplicates', action=self.alter_prop,
                                   arg=('dup', 'False')))
        favorite_menu = menu.Menu(_('Modify Duplicate Flag'), items,
                                   item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def mod_new(self, arg=None, menuw=None):
        """ Modify new flag

        This opens a submenu where the user can choose if all episodes of
        a program should be recorded or only new ones.
        """
        items = []
        items.append(menu.MenuItem('All Episodes', action=self.alter_prop,
                                   arg=('new', 'False')))
        items.append(menu.MenuItem('Only New Episodes', action=self.alter_prop,
                                   arg=('new', 'True')))
        favorite_menu = menu.Menu(_('Modify Only New Flag'), items,
                                   item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def mod_channel(self, arg=None, menuw=None):
        """Modify channel"""
        items = []

        items.append(menu.MenuItem('ANY CHANNEL', action=self.alter_prop,
                     arg=('channel', 'ANY')))

        for chanline in config.TV_CHANNELS:
            items.append(menu.MenuItem(chanline[1], action=self.alter_prop,
                         arg=('channel', chanline[1])))

        favorite_menu = menu.Menu(_('Modify Channel'), items,
                                  item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()



    def mod_day(self, arg=None, menuw=None):
        """ Modify day

        Opens a submenu where the day of the week of a favorite can be configured.
        """
        items = []

        items.append(menu.MenuItem('ANY DAY', action=self.alter_prop,
                     arg=('dow', 'ANY')))

        for i in range(len(self.week_days)):
            items.append(menu.MenuItem(self.week_days[i], action=self.alter_prop,
                         arg=('dow', i)))

        favorite_menu = menu.Menu(_('Modify Day'), items,
                                  item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def mod_time(self, arg=None, menuw=None):
        """ Modify time

        Opens a submenu where the time of a favorite can be configured.
        """
        items = []

        items.append(menu.MenuItem('ANY TIME', action=self.alter_prop,
                     arg=('mod', 'ANY')))

        for i in range(48):
            mod = i * 30
            items.append(menu.MenuItem(strftime(config.TV_TIMEFORMAT,
                                                gmtime(float(mod * 60))),
                                       action=self.alter_prop,
                                       arg=('mod', mod)))

        favorite_menu = menu.Menu(_('Modify Time'), items,
                                  item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()



    def alter_prop(self, arg=(None,None), menuw=None):
        """ Alter a favorites property

        This function is where the properties of a favorite really are changed.
        """
        (prop, val) = arg

        if prop == 'channel':
            if val == 'ANY':
                self.channel = 'ANY CHANNEL'
                self.fav.channel = 'ANY'
            else:
                self.channel = val
                self.fav.channel = val

        elif prop == 'dow':
            if val == 'ANY':
                self.dow = 'ANY DAY'
                self.fav.dow = 'ANY'
            else:
                self.dow = self.week_days[val]
                self.fav.dow = val

        elif prop == 'mod':
            if val == 'ANY':
                self.mod = 'ANY TIME'
                self.fav.mod = 'ANY'
            else:
                # self.mod = tv_util.minToTOD(val)
                self.mod = strftime(config.TV_TIMEFORMAT,
                                    gmtime(float(val * 60)))
                self.fav.mod = val

        elif prop == 'dup':
             if val == 'True':
                self.allowDuplicates=TRUE
                self.fav.allowDuplicates=TRUE
             else:
                self.allowDuplicates=FALSE
                self.fav.allowDuplicates=FALSE

        elif prop == 'new':
             if val == 'True':
                self.onlyNew=TRUE
                self.fav.onlyNew=TRUE
             else:
                self.onlyNew=FALSE
                self.fav.onlyNew=FALSE

        if menuw:
            menuw.back_one_menu(arg='reload')


    def save_changes(self, arg=None, menuw=None):
        """
        Save favorite
        """
        if self.fav_action == 'edit':
            # first we remove the old favorite
            (result, msg) = record_client.removeFavorite(self.origname)
        else:
            result = True

        if result:
            # create a new edited favorite
            if not config.DUPLICATE_DETECTION or not hasattr(self.fav,
                                                             'allowDuplicates'):
                self.fav.allowDuplicates = 1

            if not config.ONLY_NEW_DETECTION or not hasattr(self.fav,
                                                           'onlyNew'):
                self.fav.onlyNew = 0

            (result, msg) = record_client.addEditedFavorite(self.fav.name,
                                                           self.fav.title,
                                                           self.fav.channel,
                                                           self.fav.dow,
                                                           self.fav.mod,
                                                           self.fav.priority,
                                                           self.fav.allowDuplicates,
                                                           self.fav.onlyNew)
            if not result:
                # it is important to show the user this error,
                # because that means the favorite is removed,
                # and must be created again
                msgtext=_('Save Failed, favorite was lost')+(': %s' % msg)
                AlertBox(text=msgtext).show()
            else:
                self.fav_action = 'edit'
                if menuw:
                    # and reload the menu that we return to
                    menuw.back_one_menu(arg='reload')
        else:
            # show an error messages when all failed
            AlertBox(text=_('Save Failed')+(': %s' % msg)).show()


    def rem_favorite(self, arg=None, menuw=None):
        """
        Remove favorite
        """
        name = self.origname
        (result, msg) = record_client.removeFavorite(name)
        if result:
            # if this is successfull
            if menuw:
                # reload the menu that we return to
                menuw.back_one_menu(arg='reload')
            # and show a short message of success
            msgtext = text=_('"%s" has been removed from favorites') % name
            AlertBox(text=msgtext).show()
        else:
            # if all fails then we should show an error
            AlertBox(text=_('Remove Failed')+(': %s' % msg)).show()
