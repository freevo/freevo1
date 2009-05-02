# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Simple plug-in to listen to radio
# -----------------------------------------------------------------------
# $Id$
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

"""
Simple plugin to listen to radio

You need to have radio installed before using this plugin to activate put the
following in your local_conf.py::

    plugin.activate('audio.radioplayer')
    plugin.activate('audio.radio')
    RADIO_CMD='/usr/bin/radio'
    RADIO_STATIONS = [
        ('Sea FM', '90.9'),
        ('Kiss 108', '108'),
        ('Mix 98.5', '98.5'),
        ('Magic 106', '106.7')
    ]
"""

#python modules
import os, popen2, fcntl, select, time
import glob

import kaa.imlib2 as imlib2

#freevo modules
import config, menu, rc, plugin, util
from audio.player import PlayerGUI
from item import Item
from menu import MenuItem
from gui import AlertBox, ConfirmBox
import skin


class PluginInterface(plugin.MainMenuPlugin):
    """
    This plugin uses the command line program radio to tune a
    bttv card with a radio tuner to a radio station to listen
    to. You need to also use the RadioPlayer plugin to actually
    listen to the station.

    need to have radio installed before using this plugin.
    radio is availble in binary form for most linux distros.

    to activate put the following in your local_conf.py:
    | plugin.activate('audio.radioplayer')
    | plugin.activate('audio.radio')
    | RADIO_CMD='/usr/bin/radio'
    | RADIO_STATIONS = [
    |     ('Sea FM', '90.9'),
    |     ('Kiss 108', '108'),
    |     ('Mix 98.5', '98.5'),
    |     ('Magic 106', '106.7')
    | ]
    """
    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        if not config.RADIO_CMD or not config.RADIO_STATIONS:
            self.reason = 'RADIO_CMD or RADIO_STATIONS not set'
            return
        plugin.MainMenuPlugin.__init__(self)
        self.plugin_name = 'radio'


    def config(self):
        return [
            ('RADIO_CMD', None, 'Command to play the radio'),
            ('RADIO_STATIONS', None, 'List of radio stations'),
        ]


    def items(self, parent):
        return [ RadioMainMenuItem(parent) ]



class RadioMainMenuItem(MenuItem):
    """
    this is the item for the main menu and creates the list
    of commands in a submenu.
    """
    def __init__(self, parent):
        _debug_('RadioMainMenuItem.__init__(parent=%r)' % (parent,), 2)
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Radio')


    def actions(self):
        """
        Get a list of actions for this menu item
        """
        return [ (self.create_stations_menu, 'stations') ]


    def create_stations_menu(self, arg=None, menuw=None):
        station_items = []
        for rstation in config.RADIO_STATIONS:
            radio_item = RadioItem()
            radio_item.name = rstation[0]
            radio_item.station = rstation[1]
            radio_item.url = 'radio://' + str(rstation[1])
            radio_item.type = 'audio'
            radio_item.station_index = config.RADIO_STATIONS.index(rstation)
            radio_item.length = 0
            radio_item.remain = 0
            #radio_item.elapsed = 0
            radio_item.info = {'album':'', 'artist':'', 'trackno': '', 'title':''}
            station_items += [ radio_item ]
        if (len(station_items) == 0):
            station_items += [menu.MenuItem(_('No Radio Stations found'), menwu.goto_prev_page, 0)]
        station_menu = menu.Menu(_('Radio Stations'), station_items)
        menuw.pushmenu(station_menu)
        menuw.refresh()



class RadioItem(Item):
    """
    This is the class that actually runs the commands. Eventually hope to add
    actions for different ways of running commands and for displaying stdout
    and stderr of last command run.
    """
    def __init__(self):
        Item.__init__(self)
        self.title = None
        self.artist = None
        self.album = None
        self.image = None
        self.length = 0


    def actions(self):
        """ Get a list of actions for this item """
        items = [ (self.play, _('Listen to Radio Station')) ]
        return items


    def checktv(self):
        """ Check if something is recording """
        self.tvlockfile = config.FREEVO_CACHEDIR + '/record.*'
        return len(glob.glob(self.tvlockfile)) > 0


    def play(self, arg=None, menuw=None):
        _debug_('station=%r station_index=%r name=%r' % (self.station, self.station_index, self.name))
        # self.parent.current_item = self
        #self.elapsed = 0

        if not self.menuw:
            self.menuw = menuw

        if self.checktv():
            AlertBox(text=_('Cannot play - recording in progress'), handler=self.confirm).show()
            return 'Cannot play with RadioPlayer - recording in progress'

        self.player = RadioPlayerGUI(self, menuw)
        error = self.player.play()

        if error and menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)


    def confirm (self, arg=None, menuw=None):
        """ Confirm that the player should be stopped """
        _debug_('confirm (self, arg=%r, menuw=%r)' % (arg, menuw))
        if menuw:
            menuw.menu_back()
            #menuw.refresh()


    def stop(self, arg=None, menuw=None):
        """ Stop the current playing """
        _debug_('stop')
        self.player.stop()



class RadioPlayerGUI(PlayerGUI):
    """
    Radio Player user interface
    """
    def __init__(self, item, menuw=None):
        """ Create an instance of a RadioPlayerGUI """
        _debug_('RadioPlayerGUI.__init__(item=%r, menuw=%r)' % (item, menu), 2)
        PlayerGUI.__init__(self, item, menuw)
        self.start_time = time.time()
        self.item = item
        self.image = skin.get_icon('misc/radio')
        #self.item.image = imlib2.open(self.image)
        self.item.image = self.image


    def refresh(self):
        """ Give information to the skin """
        _debug_('refresh()', 2)
        if not self.visible:
            return
        if not self.running:
            return

        elapsed = int(time.time() - self.start_time + 0.5)
        hr = elapsed / (60 * 60)
        mn = elapsed % (60 * 60) / 60
        sc = elapsed % (60 * 60) % 60
        # Is there any point is having elapsed?
        #if hr > 0:
        #    self.item.elapsed = '%d:%02d:%02d' % (hr, mn, sc)
        #else:
        #    self.item.elapsed = '%d:%02d' % (mn, sc)

        skin.draw('player', self.item)
