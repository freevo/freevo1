# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A plugin to manually record TV programs
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


import calendar
import time, traceback, sys
from time import gmtime, strftime

import plugin, config, menu

import util.tv_util as tv_util
from tv.record_client import RecordClient
import event as em

from item import Item
from gui.AlertBox import AlertBox
from gui.InputBox import InputBox
from tv.record_types import Favorite
from tv.epg_types import TvProgram

# Use the alternate strptime module which seems to handle time zones
#
# XXX Remove when we are ready to require Python 2.3
if float(sys.version[0:3]) < 2.3:
    import tv.strptime as strptime
else:
    import _strptime as strptime


class ManualRecordItem(Item):

    def __init__(self, parent):
        _debug_('manual_record.ManualRecordItem.__init__(parent)', 2)
        Item.__init__(self, parent, skin_type='video')

        self.name = _("Manual Record")

        self.recordclient = RecordClient()

        # maxinum number of days we can record
        self.MAXDAYS = 7

        # minimum amount of time it would take record_server.py
        # to pick us up in seconds by default it is one minute plus
        # a few seconds just in case
        self.MINPICKUP = 70

        self.months = [
            _('Jan'), _('Feb'), _('Mar'), _('Apr'), _('May'), _('Jun'),
            _('Jul'), _('Aug'), _('Sep'), _('Oct'), _('Nov'), _('Dec')
        ]

        now = time.time()
        now += 300
        self.startnow = now
        self.starttime = time.localtime(now)
        now += 1900
        self.stopnow = now
        self.stoptime = time.localtime(now)


    def make_newprog(self):
        _debug_('make_newprog(self)', 2)
        self.prog = TvProgram()

        self.disp_title = self.prog.title = self.name

        self.description = ''
        self.prog.desc = ''

        self.prog.channel_id = config.TV_CHANNELS[0][0]
        self.disp_channel = config.TV_CHANNELS[0][1]

        #self.start_year = self.starttime[0]
        self.start_month = self.starttime[1]
        self.disp_start_month = self.months[self.start_month - 1]
        self.start_day   = self.starttime[2]
        self.start_time  = time.strftime(config.TV_TIME_FORMAT, self.starttime)
        self.prog.start  = self.startnow
        self.disp_starttime = '%s %s %s' % (self.disp_start_month, self.start_day, self.start_time)

        #self.stop_year = self.stoptime[0]
        self.stop_month = self.stoptime[1]
        self.disp_stop_month = self.months[self.stop_month - 1]
        self.stop_day   = self.stoptime[2]
        self.stop_time  = time.strftime(config.TV_TIME_FORMAT, self.stoptime)
        self.prog.stop  = self.stopnow
        self.disp_stoptime = '%s %s %s' % (self.disp_stop_month, self.stop_day, self.stop_time)


    def actions(self):
        _debug_('actions(self)', 2)
        return [( self.display_recitem , _('Display record item') )]


    def display_recitem(self, arg=None, menuw=None):
        _debug_('display_recitem(self, arg=None, menuw=None)', 2)
        self.make_newprog()

        items = []

        items.append(menu.MenuItem(_('Modify name'), action=self.mod_name))
        items.append(menu.MenuItem(_('Modify channel'), action=self.mod_channel))
        items.append(menu.MenuItem(_('Modify start month'), action=self.mod_start_month))
        items.append(menu.MenuItem(_('Modify start day'), action=self.mod_start_day))
        items.append(menu.MenuItem(_('Modify start time'), action=self.mod_start_time))
        items.append(menu.MenuItem(_('Modify stop month'), action=self.mod_stop_month))
        items.append(menu.MenuItem(_('Modify stop day'), action=self.mod_stop_day))
        items.append(menu.MenuItem(_('Modify stop time'), action=self.mod_stop_time))
        items.append(menu.MenuItem(_('Save'), action=self.save_changes))

        manualrecord_menu = menu.Menu(_('Record Item Menu'), items, item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_name(self, arg=None, menuw=None):
        _debug_('mod_name(self, arg=None, menuw=None)', 2)
        self.menuw = menuw
        InputBox(text=_('Alter Name'), handler=self.alter_name).show()


    def mod_channel(self, arg=None, menuw=None):
        _debug_('mod_channel(self, arg=None, menuw=None)', 2)
        items = []

        for chanline in config.TV_CHANNELS:
            items.append(menu.MenuItem(chanline[1], action=self.alter_prop,
                         arg=('channel', (chanline[1],chanline[0]))))

        manualrecord_menu = menu.Menu(_('Modify Channel'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_start_month(self, arg=None, menuw=None):
        _debug_('mod_start_month(self, arg=None, menuw=None)', 2)
        items = []

        iter=0
        while iter < 12:
            month_name = self.months[(iter + self.starttime[1] - 1) % 12];
            month_num  = self.months.index(month_name) + 1;
            items.append(menu.MenuItem(month_name, action=self.alter_prop, arg=('startmonth', (month_name, month_num))))
            iter = iter + 1

        manualrecord_menu = menu.Menu(_('Modify Day'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_start_day(self, arg=None, menuw=None):
        _debug_('mod_start_day(self, arg=None, menuw=None)', 2)
        items = []

        numdays = calendar.monthrange(self.starttime[0], self.start_month)[1]
        daylimit = numdays + 1
        iter=1
        while iter < daylimit:
            newday = (iter + self.starttime[2] - 1)
            currday = newday % daylimit
            if newday >= daylimit:
                currday += 1
            items.append(menu.MenuItem(str(currday), action=self.alter_prop,
                         arg=('startday', currday)))
            iter = iter + 1

        manualrecord_menu = menu.Menu(_('Modify Day'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_start_time(self, arg=None, menuw=None):
        _debug_('mod_start_time(self, arg=None, menuw=None)', 2)
        items = []

        currminutes = self.starttime[3]*60 + self.starttime[4]
        minpadding = 5 - (currminutes % 5)
        if minpadding == 5:
            minpadding = 0
        for i in range(288):
            mod = (i * 5 + currminutes + minpadding) % 1440
            showtime = strftime(config.TV_TIME_FORMAT, gmtime(float(mod * 60)))
            items.append(menu.MenuItem(showtime,
                                       action=self.alter_prop,
                                       arg=('starttime', showtime)))

        manualrecord_menu = menu.Menu(_('Modify Time'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_stop_month(self, arg=None, menuw=None):
        _debug_('mod_stop_month(self, arg=None, menuw=None)', 2)
        items = []

        iter=0
        while iter < 12:
            month_name = self.months[(iter + self.stoptime[1] - 1) % 12];
            month_num  = self.months.index(month_name) + 1;
            items.append(menu.MenuItem(month_name, action=self.alter_prop, arg=('stopmonth', (month_name, month_num))))
            iter = iter + 1

        manualrecord_menu = menu.Menu(_('Modify Day'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_stop_day(self, arg=None, menuw=None):
        _debug_('mod_stop_day(self, arg=None, menuw=None)', 2)
        items = []

        numdays = calendar.monthrange(self.stoptime[0], self.stop_month)[1]
        daylimit = numdays + 1
        iter=1
        while iter < daylimit:
            newday = (iter + self.starttime[2] - 1)
            currday = newday % daylimit
            if newday >= daylimit:
                currday += 1
            items.append(menu.MenuItem(str(currday), action=self.alter_prop,
                         arg=('stopday', currday)))
            iter = iter + 1

        manualrecord_menu = menu.Menu(_('Modify Day'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def mod_stop_time(self, arg=None, menuw=None):
        _debug_('mod_stop_time(self, arg=None, menuw=None)', 2)
        items = []

        currminutes = self.starttime[3]*60 + self.starttime[4]
        minpadding = 5 - (currminutes % 5)
        if minpadding == 5:
            minpadding = 0
        for i in range(288):
            mod = (i * 5 + currminutes + minpadding) % 1440
            showtime = strftime(config.TV_TIME_FORMAT, gmtime(float(mod * 60)))
            items.append(menu.MenuItem(showtime,
                                       action=self.alter_prop,
                                       arg=('stoptime', showtime)))

        manualrecord_menu = menu.Menu(_('Modify Time'), items,
                                  item_types = 'tv manual record menu')
        manualrecord_menu.infoitem = self
        menuw.pushmenu(manualrecord_menu)
        menuw.refresh()


    def alter_name(self, name):
        _debug_('alter_name(self, name)', 2)
        if name:
            self.disp_title = self.prog.title = name

        self.menuw.refresh()


    def alter_prop(self, arg=(None,None), menuw=None):
        _debug_('alter_prop(self, arg=(None,None), menuw=None)', 2)
        (prop, val) = arg

        if prop == 'channel':
            self.prog.channel_id = val[1]
            self.disp_channel = val[0]

        if prop == 'startday':
            self.start_day = val
            self.disp_starttime = '%s %s %s' % (self.disp_start_month, self.start_day, self.start_time)

        if prop == 'startmonth':
            self.start_month = val[1]
            self.disp_start_month = val[0]
            self.disp_starttime = '%s %s %s' % (self.disp_start_month, self.start_day, self.start_time)

        if prop == 'starttime':
            self.start_time = val
            self.disp_starttime = '%s %s %s' % (self.disp_start_month, self.start_day, self.start_time)

        if prop == 'stopday':
            self.stop_day = val
            self.disp_stoptime = '%s %s %s' % (self.disp_stop_month, self.stop_day, self.stop_time)

        if prop == 'stopmonth':
            self.stop_month = val[1]
            self.disp_stop_month = val[0]
            self.disp_stoptime = '%s %s %s' % (self.disp_stop_month, self.stop_day, self.stop_time)

        if prop == 'stoptime':
            self.stop_time = val
            self.disp_stoptime = '%s %s %s' % (self.disp_stop_month, self.stop_day, self.stop_time)

        if menuw:
            menuw.back_one_menu(arg='reload')


    def save_changes(self, arg=None, menuw=None):
        _debug_('save_changes(self, arg=None, menuw=None)', 2)
        result = self.check_prog()
        if result:
            (result, reason) = self.recordclient.scheduleRecordingNow(self.prog)

            if not result:
                AlertBox(text=_('Save Failed, recording was lost')+(':\n%s' % reason)).show()
            else:
                if menuw:
                    menuw.back_one_menu(arg='reload')


    def check_prog(self):
        _debug_('check_prog(self)', 2)
        isgood = True
        curtime_epoch = time.time()
        curtime = time.localtime(curtime_epoch)
        startyear = curtime[0]
        stopyear = curtime[0]
        currentmonth = curtime[1]

        # handle the year wraparound
        if int(self.stop_month) < currentmonth:
            stopyear = str(int(stopyear) + 1)
        if int(self.start_month) < currentmonth:
            startyear = str(int(startyear) + 1)
        # create utc second start time
        starttime = time.mktime(strptime.strptime(str(self.start_month)+" "+str(self.start_day)+" "+str(startyear)+" "+str(self.start_time)+":00",'%m %d %Y '+config.TV_TIME_FORMAT+':%S'))
        # create utc stop time
        stoptime = time.mktime(strptime.strptime(str(self.stop_month)+" "+str(self.stop_day)+" "+str(stopyear)+" "+str(self.stop_time)+":00",'%m %d %Y '+config.TV_TIME_FORMAT+':%S'))

        # so we don't record for more then maxdays (maxdays day * 24hr/day * 60 min/hr * 60 sec/min)
        if not abs(stoptime - starttime) < (self.MAXDAYS * 86400):
            if self.MAXDAYS > 1:
                isgood = False
                msg = _("Program would record for more than %d days!") % self.MAXDAYS
                AlertBox(text=_('Save Failed, recording was lost')+(':\n%s' % msg)).show()
            else:
                isgood = False
                msg = _("Program would record for more than 1 day!") % self.MAXDAYS
                AlertBox(text=_('Save Failed, recording was lost')+(':\n%s' % msg)).show()

        elif not starttime < stoptime:
            isgood = False
            msg = _("start time is not before stop time." )
            AlertBox(text=_('Save Failed, recording was lost')+(':\n%s' % msg)).show()
        elif stoptime < curtime_epoch + self.MINPICKUP:
            isgood = False
            msg = _("Sorry, the stop time does not give enough time for scheduler to pickup the change.  Please set it to record for a few minutes longer.")
            AlertBox(text=_('Save Failed, recording was lost')+(':\n%s' % msg)).show()
        else:
            self.prog.start = starttime
            self.prog.stop = stoptime

        return isgood


class PluginInterface(plugin.MainMenuPlugin):
    """
    This plugin is used to display your list of favorites.

    | plugin.activate('tv.view_favorites')
    """
    def __init__(self):
        _debug_('manual_record.PluginInterface.__init__()', 2)
        plugin.MainMenuPlugin.__init__(self)


    def items(self, parent):
        _debug_('items(self, parent)', 2)
        if config.TV_CHANNELS:
            return [ ManualRecordItem(parent) ]
        return []
