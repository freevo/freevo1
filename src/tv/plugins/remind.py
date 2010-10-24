# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to view your list of favorites.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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

import config
import dialog
from item import Item
import kaa
import menu
import plugin
import time
import tv.channels
from tv.programitem import ProgramItem
from util.tv_util import getKey as get_prog_key

class ReminderItem(ProgramItem):
    """
    ProgramItem subclass used as a menu item in 'View Reminders' menu,
    """
    def __init__(self, parent, prog):
        ProgramItem.__init__(self, parent, prog)

    def actions(self):
        return ((self.remove_reminder ,_('Remove reminder')),)

    def remove_reminder(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Do you want to remove the reminder for %s') % self.prog.title,
                                proceed_handler=self.__remove_reminder, proceed_text=_('Remove'))

    def __remove_reminder(self):
        self.parent.reminders.remove_reminder(self.prog)
        self.menuw.refresh(reload=True)

class ViewRemindersItem(Item):
    """
    Menu showing all programs that have reminders set.
    """
    def __init__(self, parent, reminders):
        _debug_('ViewRemindersItem.__init__(parent=%r)' % (parent,), 2)
        Item.__init__(self, parent, skin_type='tv')
        self.name = _('View Reminders')
        self.menuw = None
        self.reminders = reminders


    def actions(self):
        _debug_('actions()', 2)
        return [ ( self.view_reminders , _('View Reminders') ) ]


    def view_reminders(self, arg=None, menuw=None):
        _debug_('view_reminders(arg=%r, menuw=%r)' % (arg, menuw), 2)

        items = self.get_items()
        if not len(items):
            dialog.show_alert(_('No reminders set!'))
            return

        reminders_menu = menu.Menu(_( 'View Reminders'), items,  reload_func=self.reload,
                                    item_types='tv program menu')
        self.menuw = menuw
        menuw.pushmenu(reminders_menu)
        menuw.refresh()

    
    def reload(self):
        _debug_('reload()', 2)
        menuw = self.menuw

        menu = menuw.menustack[-1]

        new_choices = self.get_items()
        if not menu.selected in new_choices and len(new_choices):
            sel = menu.choices.index(menu.selected)
            if len(new_choices) <= sel:
                menu.selected = new_choices[-1]
            else:
                menu.selected = new_choices[sel]

        menu.choices = new_choices

        return menu


    def get_items(self):
        _debug_('get_items()', 2)
        items = []
        for prog in self.reminders.get_reminders():
            items.append(ReminderItem(self, prog))

        return items



class PluginInterface(plugin.MainMenuPlugin):
    """
    This plugin is used to remind you when a program you are interested in is
    about to start.

    | plugin.activate('tv.reminders')
    """

    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        plugin.MainMenuPlugin.__init__(self)
        self.reminders = Reminders()
        plugin.register(self.reminders, "TVReminders")
        plugin.activate(self.reminders)


    def config(self):
        return [('REMIND_MINUTES_BEFORE', 3, 'Number of minutes before a program to remind the user')]
    
    def items(self, parent):
        _debug_('items(parent=%r)' % (parent,), 2)
        return [ ViewRemindersItem(parent, self.reminders) ]


class Reminders(plugin.Plugin):
    """
    Class to add action to add add/remove reminder to program action menu.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)
        self._type = 'tv_program'
        self.progs = {}
        self.current_prog = None
        self.timer = kaa.AtTimer(self.check_reminders)
        self.timer.start()


    def update(self, prog):
        if self.is_reminder_set(prog):
            prog.reminder = True
        else:
            prog.reminder = False
            

    def items(self, prog):
        """
        Get actions for prog.
        """
        self.current_prog = prog
        if self.is_reminder_set(prog):
            return ((self.__remove_reminder ,_('Remove reminder')),)
        else:
            return ((self.__add_reminder ,_('Add reminder')),)


    def __add_reminder(self, arg=None, menuw=None):
        self.add_reminder(self.current_prog)
        menuw.back_one_menu()


    def __remove_reminder(self, arg=None, menuw=None):
        self.remove_reminder(self.current_prog)
        menuw.back_one_menu()


    def add_reminder(self, prog):
        """
        Add a reminder for the specified program.
        """
        self.progs[get_prog_key(prog)] = prog


    def remove_reminder(self, prog):
        """
        Remove the reminder for the specified program.
        """
        key = get_prog_key(prog)
        if key in self.progs:
            del self.progs[key]


    def is_reminder_set(self, prog):
        """
        Check to see if a reminder has been set for the specified program,
        """
        return get_prog_key(prog) in self.progs

    def get_reminders(self):
        """
        Get a list of programs that have reminders set.
        """
        return self.progs.values()

    def check_reminders(self):
        """
        Check to see if we should show a dialog if a program is about to start.
        """
        now = time.time()
        for prog in self.progs.values():
            if prog.start <= now:
                channel_name = tv.channels.map_channel_id_to_name(prog.channel_id)
                if prog.start == now:
                    dialog.show_message(_('%s is starting now on %s') % (prog.name, channel_name))
                elif prog.start >= now + config.REMIND_MINUTES_BEFORE:
                    minutes = (prog.start - now) / 60
                    dialog.show_message(_('%s is about to start in %d minutes on %s') % (prog.name, minutes,channel_name))
            if now > prog.start:
                del self.progs[get_prog_key(prog)]
