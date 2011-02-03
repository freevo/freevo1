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

import dialog

from tv.record_types import Favorite, ScheduledRecordings
from tv.epg_types import TvProgram
from tv.record_client import RecordClient

class FavoriteItem(Item):
    """
    Item class for favorite items
    """
    def __init__(self, parent, fav, fav_action='edit'):
        """ """
        Item.__init__(self, parent, skin_type='video')
        _debug_('FavoriteItem.__init__(parent=%r, fav=%r, fav_action=%r)' % (parent, fav, fav_action), 2)
        self.recordclient = RecordClient()
        self.fav   = fav
        self.name  = self.origname = fav.name
        self.title = fav.title
        self.fav_action = fav_action
        if hasattr(fav, 'allowDuplicates'):
            self.allowDuplicates = int(fav.allowDuplicates)

        if hasattr(self.fav, 'onlyNew'):
            self.onlyNew = int(fav.onlyNew)

        self.week_days = (_('Monday'), _('Tuesday'), _('Wednesday'), _('Thursday'), _('Friday'), _('Saturday'), _('Sunday'))


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
                self.mod = time.strftime(config.TV_TIME_FORMAT, time.gmtime(float(int(fav.mod) * 60)))
            except:
                print 'Cannot add "%s" to favorites' % fav.name

        # needed by the inputbox handler
        self.menuw = None


    def actions(self):
        _debug_('actions()', 2)
        return [( self.display_submenu, _('Edit favorite')), \
                ( self.rem_favorite, _('Remove favorite'))]


    def display_submenu(self, arg=None, menuw=None):
        """ Display menu for a favorite

        With this menu the user can made a program a favorite.
        All attributes of a favorite can be edited here and in the end
        the user must select 'save changes' to finally create the favorite.
        """
        _debug_('display_submenu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        ### create menu items for editing the favorites attributes
        items = []

        items.append(menu.MenuItem(_('Name') + u'\t' + _(self.name), action=self.mod_name))
        items.append(menu.MenuItem(_('Channel') + u'\t' + _(self.channel), action=self.mod_channel))
        items.append(menu.MenuItem(_('Day of the Week') + u'\t' + _(self.dow), action=self.mod_day))
        items.append(menu.MenuItem(_('Time of Day') + u'\t' + _(self.mod), action=self.mod_time))

        if config.TV_RECORD_DUPLICATE_DETECTION:
            if self.allowDuplicates:
                value = _('Allow duplicates')
            else:
                value = _('Prevent duplicates')
            items.append(menu.MenuItem(_('Duplicate Recordings') + u'\t' + _(value),
                                        action=self.alter_prop,
                                        arg=('dup', not self.allowDuplicates)))


        if config.TV_RECORD_ONLY_NEW_DETECTION:
            if self.onlyNew:
                value = _('Only new episodes')
            else:
                value = _('All episodes')
            items.append(menu.MenuItem(_('Episode Filter') + u'\t' + _(value),
                                        action=self.alter_prop,
                                        arg=('new', not self.onlyNew)))

        # XXX: priorities aren't quite supported yet
        if 0:
            (status, favorites) = self.recordclient.getFavoritesNow()
            if status and len(favorites) > 1:
                items.append(menu.MenuItem(_('Modify priority'), action=self.mod_priority))


        ### save favorite
        items.append(menu.MenuItem(_('Save changes') + u'\t', action=self.save_changes))

        ### remove this program from favorites
        if not self.fav_action == 'add':
            items.append(menu.MenuItem(_('Remove favorite') + u'\t', action=self.rem_favorite))

        ### put the whole menu together
        favorite_menu = menu.Menu(_('Favorite Menu'), items, item_types='tv favorite menu')
        favorite_menu.infoitem = self
        favorite_menu.is_submenu = True
        favorite_menu.table = (50, 50)
        menuw.pushmenu(favorite_menu)
        menuw.refresh()



    ### Actions:

    def mod_name(self, arg=None, menuw=None):
        """ Modify name

        This opens a input box to ask the user for a new name for this favorite.
        The default name of a favorite is the name of the program.
        """
        _debug_('mod_name(arg=%r, menuw=%r)' % (arg, menuw), 2)
        self.menuw = menuw
        InputBox(text=_('Alter Name'), handler=self.alter_name, \
            width=osd.get_singleton().width - config.OSD_OVERSCAN_LEFT - 20, input_text=self.name).show()


    def alter_name(self, name):
        """ set the new name"""
        _debug_('alter_name(name=%r)' % (name,), 2)
        if name:
            self.name = self.fav.name = name.strip()
        menustack = self.menuw.menustack[-1]
        menustack.selected.dirty = True
        self.menuw.refresh()


    def mod_channel(self, arg=None, menuw=None):
        """Modify channel"""
        _debug_('mod_channel(arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []

        items.append(menu.MenuItem('ANY CHANNEL', action=self.alter_prop, arg=('channel', 'ANY')))

        for chanline in config.TV_CHANNELS:
            items.append(menu.MenuItem(chanline[1], action=self.alter_prop, arg=('channel', chanline[1])))

        favorite_menu = menu.Menu(_('Modify Channel'), items, item_types='tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def mod_day(self, arg=None, menuw=None):
        """ Modify day

        Opens a submenu where the day of the week of a favorite can be configured.
        """
        _debug_('mod_day(arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []

        items.append(menu.MenuItem(_('ANY DAY'), action=self.alter_prop, arg=('dow', 'ANY')))

        for i in range(len(self.week_days)):
            items.append(menu.MenuItem(self.week_days[i], action=self.alter_prop, arg=('dow', i)))

        favorite_menu = menu.Menu(_('Modify Day'), items, item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def mod_time(self, arg=None, menuw=None):
        """ Modify time

        Opens a submenu where the time of a favorite can be configured.
        """
        _debug_('mod_time(arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []

        items.append(menu.MenuItem(_('ANY TIME'), action=self.alter_prop, arg=('mod', 'ANY')))

        for i in range(48):
            mod = i * 30
            items.append(menu.MenuItem(time.strftime(config.TV_TIME_FORMAT, time.gmtime(float(mod * 60))), \
                action=self.alter_prop, arg=('mod', mod)))

        favorite_menu = menu.Menu(_('Modify Time'), items, item_types = 'tv favorite menu')
        favorite_menu.infoitem = self
        menuw.pushmenu(favorite_menu)
        menuw.refresh()


    def alter_prop(self, arg=(None, None), menuw=None):
        """ Alter a favorites property

        This function is where the properties of a favorite really are changed.
        """
        _debug_('alter_prop(arg=%r, menuw=%r)' % (arg, menuw), 2)
        (prop, val) = arg
        new_text = None
        new_arg = None
        back = True

        if prop == 'channel':
            if val == 'ANY':
                self.channel = 'ANY CHANNEL'
                self.fav.channel = 'ANY'
            else:
                self.channel = val
                self.fav.channel = val
            new_text = _('Channel') + u'\t' + _(self.channel)

        elif prop == 'dow':
            if val == 'ANY':
                self.dow = 'ANY DAY'
                self.fav.dow = 'ANY'
            else:
                self.dow = self.week_days[val]
                self.fav.dow = val
            new_text = _('Day of the Week') + u'\t' + _(self.dow)

        elif prop == 'mod':
            if val == 'ANY':
                self.mod = 'ANY TIME'
                self.fav.mod = 'ANY'
            else:
                # self.mod = tv_util.minToTOD(val)
                self.mod = time.strftime(config.TV_TIME_FORMAT, time.gmtime(float(val * 60)))
                self.fav.mod = val
            new_text = _('Time of Day') + u'\t' + _(self.mod)

        elif prop == 'dup':
            self.allowDuplicates= self.fav.allowDuplicates= val
            if val:
                value = _('Allow Duplicates')
            else:
                value = _('Prevent Duplicates')

            new_text =  _('Duplicate Recordings') + u'\t' + value
            new_arg = ('dup', not val)
            back = False

        elif prop == 'new':
            self.onlyNew= self.fav.onlyNew = val
            if val:
                value = _('Only New Episodes')
            else:
                value = _('All New Episodes')
            new_text = _('Episode Filter') + u'\t' + value
            new_arg = ('new', not val)
            back = False

        if menuw and new_text:
            menu = menuw.menustack[back and -2 or -1]
            menu.selected.name = new_text
            if new_arg:
                menu.selected.arg = new_arg
            menu.selected.dirty = True
            if back:
                menuw.back_one_menu(arg='reload')
            else:
                menuw.refresh()

    def save_changes(self, arg=None, menuw=None):
        """
        Save favorite
        """
        _debug_('save_changes(arg=%r, menuw=%r)' % (arg, menuw), 2)
        # this can take some time, as it means although to update the schedule
        msgtext = _('Saving the changes to this favorite.')+'\n'+_('This may take some time.')
        pop = dialog.show_working_indicator(msgtext)

        if self.fav_action == 'edit':
            # first we remove the old favorite
            (result, msg) = self.recordclient.removeFavoriteNow(self.origname)
        elif self.fav_action =='add':
            result = True

        if result:
            # create a new edited favorite
            (result, msg) = self.recordclient.addEditedFavoriteNow(self.fav.name,
                self.fav.title, self.fav.channel, self.fav.dow, self.fav.mod,
                self.fav.priority, self.fav.allowDuplicates, self.fav.onlyNew)
            if result:
                if menuw:
                    menuw.delete_submenu()
                    if self.fav_action == 'add':
                        menuw.refresh(reload=1)
                self.fav_action = 'edit'
                pop.hide()
            else:
                pop.hide()
                # it is important to show the user this error,
                # because that means the favorite is removed,
                # and must be created again
                msgtext=_('Save failed, favorite was lost')+(':\n%s' % msg)
                dialog.show_alert(msgtext)


    def rem_favorite(self, arg=None, menuw=None):
        """
        Remove favorite
        """
        _debug_('rem_favorite(arg=%r, menuw=%r)' % (arg, menuw), 2)
        name = self.origname
        (result, msg) = self.recordclient.removeFavoriteNow(name)
        if result:
            # if this is successfull
            if menuw:
                menuw.delete_submenu()
                menuw.refresh(reload=1)
            # and show a short message of success
            msgtext = text=_('"%s" has been removed from favorites') % name
            dialog.show_alert(msgtext)
        else:
            # if all fails then we should show an error
            msgtext = _('Remove failed')+(':\n%s' % msg)
            dialog.show_alert(msgtext)
