# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# favoriteItem - Favorite handling.
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
import time

import menu, config, osd

from item import Item

from gui.InputBox import InputBox
from gui.AlertBox import AlertBox
from gui.PopupBox import PopupBox

import tv.record_client as record_client

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
                self.mod = time.strftime(config.TV_TIMEFORMAT,
                                    time.gmtime(float(int(fav.mod) * 60)))
            except:
                print 'Cannot add "%s" to favorites' % fav.name

        # needed by the inputbox handler
        self.menuw = None

    def actions(self):
        return [( self.display_submenu , _('Display favorite'))]


    def display_submenu(self, arg=None, menuw=None):
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
        favorite_menu.is_submenu = True
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

        items.append(menu.MenuItem(_('ANY DAY'), action=self.alter_prop,
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

        items.append(menu.MenuItem(_('ANY TIME'), action=self.alter_prop,
                     arg=('mod', 'ANY')))

        for i in range(48):
            mod = i * 30
            items.append(menu.MenuItem(time.strftime(config.TV_TIMEFORMAT,
                                                time.gmtime(float(mod * 60))),
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
                self.mod = time.strftime(config.TV_TIMEFORMAT,
                                    time.gmtime(float(val * 60)))
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
        # this can take some time, as it means although to update the schedule
        msgtext = _('Saving the changes to this favorite.')
        msgtext+= _('This may take some time.')
        pop = PopupBox(text=msgtext)
        pop.show()


        if self.fav_action == 'edit':
            # first we remove the old favorite
            (result, msg) = record_client.removeFavorite(self.origname)
        elif self.fav_action =='add':
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
            if result:
                self.fav_action = 'edit'
                if menuw:
                    # and reload the menu that we return to
                    menuw.back_one_menu(arg='reload')
                pop.destroy()
            else:
                pop.destroy()
                # it is important to show the user this error,
                # because that means the favorite is removed,
                # and must be created again
                msgtext=_('Save failed, favorite was lost.')+(': %s' % msg)
                AlertBox(text=msgtext).show()


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
            msgtext = _('Remove failed')+(': %s' % msg)
            AlertBox(text=msgtext).show()
