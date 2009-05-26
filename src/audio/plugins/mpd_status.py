# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the status display.  Using this you can see the currently playing
# track, play, pause, stop, skip forward, skip back, toggle repeat, toggle
# shuffle, clear playlist, open external playlist editor, change volume
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# There are two parts to this plugin, an addition to the audio item menu to queue
# the item in mpd's playlist and a status display in the audio menu
#
# Advantages of this over the previous mpd plugin:
#   The code is a lot cleaner and more robust.
#   Faster (talks to mpd directly, rather than calling other programs).
#   Allows you to modify the playlist within freevo.
#
# Todo:
#
#   enable localisation
#   investigate having the mpd connection managed by another class
#   pretty GUI
#   have status/everything update periodicly
#   add a playlist browser
#   code to handle when the mpd server is down
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

import plugin
import config
from gui import PopupBox
import menu
import childapp

import os
import sys

import mpdclient2

class PluginInterface(plugin.MainMenuPlugin):
    """
    This creates a new item in the audio menu
    Which allows you to view and modify the MPD settings

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    | plugin.activate('audio.mpd_status')
    """
    __author__           = 'Graham Billiau (DrLizAu\'s code monkey)'
    __author_email__     = 'graham@geeksinthegong.net'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '2'

    def __init__(self):
        """Initilise the plugin"""
        if not config.MPD_MUSIC_BASE_PATH:
            self.reason = 'MPD_MUSIC_BASE_PATH not set in local_conf.py'
            return

        plugin.MainMenuPlugin.__init__(self)
        self.show_item = menu.MenuItem('MPD status', action=self.show_menu)
        #self.show_item.type = 'menu'
        plugin.register(self, 'audio.MPD_status')
        # connect to the server
        self.conn = mpdclient2.Thread_MPD_Connection(config.MPD_SERVER_HOST, config.MPD_SERVER_PORT, True,
                    config.MPD_SERVER_PASSWORD)

        # items to go in the mpd menu
        self.item_play = menu.MenuItem('play', self.mpd_play)#, parent=self)
        self.item_status = menu.MenuItem('status', self.mpd_status)#, parent=self)
        self.item_pause = menu.MenuItem('pause', self.mpd_pause)#, parent=self)
        self.item_stop = menu.MenuItem('stop', self.mpd_stop)#, parent=self)
        self.item_next = menu.MenuItem('next track', self.mpd_next)#, parent=self)
        self.item_previous = menu.MenuItem('previous track', self.mpd_previous)#, parent=self)
        self.item_clear = menu.MenuItem('clear playlist', self.mpd_clear)#, parent=self)
        self.item_shuffle = menu.MenuItem('shuffle playlist', self.mpd_shuffle)#, parent=self)
        self.item_random = menu.MenuItem('toggle random', self.mpd_toggle_random)#, parent=self)
        self.item_repeat = menu.MenuItem('toggle repeat', self.mpd_toggle_repeat)#, parent=self)
        self.item_extern = menu.MenuItem('open external mpd client', self.start_external)#, parent=self)


    def config(self):
        """returns the config variables used by this plugin"""
        return [
            ('MPD_SERVER_HOST', 'localhost', 'the host running the mpd server'),
            ('MPD_SERVER_PORT', 6600, 'the port the server is listening on'),
            ('MPD_SERVER_PASSWORD', None, 'the password to access the mpd server'),
            ('MPD_MUSIC_BASE_PATH', None, 'the local path to where the music is stored'),
            ('MPD_EXTERNAL_CLIENT', None,'the location of the external client you want to use'),
           #('MPD_EXTERNAL_CLIENT_ARGS', '','arguments to be passed to the external client'),
        ]


    def shutdown(self):
        """close the connection to the MPD server"""
        self.conn.join()
        try:
            self.conn.close()
        except EOFError:
            # this always happens
            pass


    def items(self, parent):
        """returns the options to add to the main menu"""
        return [ self.show_item ]


    def actions(self):
        """extra options for this menu"""
        return [ ]


    def create_menu(self):
        """this creates the menu"""

        menu_items = []
        stat = self.conn.status()

        # populate the menu
        menu_items.append(self.item_status)
        if (stat['state'] == 'play'):
            menu_items.append(self.item_pause)
            menu_items.append(self.item_stop)
        elif (stat['state'] == 'pause'):
            menu_items.append(self.item_play)
            menu_items.append(self.item_stop)
        else:
            menu_items.append(self.item_play)
        menu_items.append(self.item_next)
        menu_items.append(self.item_previous)
        menu_items.append(self.item_repeat)
        menu_items.append(self.item_random)
        menu_items.append(self.item_shuffle)
        menu_items.append(self.item_clear)
        if not (config.MPD_EXTERNAL_CLIENT is None or config.MPD_EXTERNAL_CLIENT == ''):
            menu_items.append(self.item_extern)

        return menu.Menu('MPD status', menu_items, reload_func=self.create_menu)


    def show_menu(self, arg=None, menuw=None):
        """this displays the menu"""
        mpd_menu = self.create_menu()
        menuw.pushmenu(mpd_menu)
        menuw.refresh()


    def mpd_play(self, arg=None, menuw=None):
        """send the play command to the mpd server"""
        self.conn.play()
        # force the menu to reload
        menuw.delete_menu()
        self.show_menu(arg, menuw)


    def mpd_next(self, arg=None, menuw=None):
        """send the play command to the mpd server"""
        self.conn.next()


    def mpd_previous(self, arg=None, menuw=None):
        """send the play command to the mpd server"""
        self.conn.previous()


    def mpd_stop(self, arg=None, menuw=None):
        """send the stop command to the mpd server"""
        self.conn.stop()
        # force the menu to reload
        menuw.delete_menu()
        self.show_menu(arg, menuw)


    def mpd_pause(self, arg=None, menuw=None):
        """send the pause command to the mpd server"""
        self.conn.pause(1)
        # force the menu to reload
        menuw.delete_menu()
        self.show_menu(arg, menuw)


    def mpd_shuffle(self, arg=None, menuw=None):
        """send the shuffle command to the mpd server"""
        self.conn.shuffle()


    def mpd_toggle_random(self, arg=None, menuw=None):
        """toggle random on/off to the mpd server"""
        stat = self.conn.status()
        if (stat['random'] == '0'):
            self.conn.random(1)
        else:
            self.conn.random(0)


    def mpd_toggle_repeat(self, arg=None, menuw=None):
        """toggle repeat on/off to the mpd server"""
        stat = self.conn.status()
        if (stat['repeat'] == '0'):
            self.conn.repeat(1)
        else:
            self.conn.repeat(0)


    def mpd_clear(self, arg=None, menuw=None):
        """send the clear command to the mpd server"""
        self.conn.clear()


    def start_external(self, arg=None, menuw=None):
        """start the external browser in the config file"""
        if (config.MPD_EXTERNAL_CLIENT is None or config.MPD_EXTERNAL_CLIENT == ''):
            return

        #if (config.MPD_EXTERNAL_CLIENT_ARGS is None or config.MPD_EXTERNAL_CLIENT_ARGS == ''):
            #args = None
        #else:
            #args = config.MPD_EXTERNAL_CLIENT_ARGS.split()

        try:
            #os,spawnv(os.P_NOWAIT, config.MPD_EXTERNAL_CLIENT, args)
            childapp.ChildApp(config.MPD_EXTERNAL_CLIENT)
        except:
            text = "Error starting external client\n%s\n%s" %sys.exc_info()[:2]
            pop = PopupBox(text)
            pop.show()


    def mpd_status(self, arg=None, menuw=None):
        """bring up a dialog showing mpd's current status"""
        stat = self.conn.status()
        track = self.conn.currentsong()

        text = "status:     %s\n" %(stat['state'])
        if (stat['state'] != 'stop'):
            text += "title:      %s\n" %(track['title'])
            text += "album:      %s\n" %(track['album'])
            text += "artist:     %s\n" %(track['artist'])
            text += "track:      %s\\%s\n" %(int(stat['song']) + 1, stat['playlistlength'])
            text += "time:       %s\n" %(stat['time'])
        if (stat['repeat'] == '1'):
            text += "repeat:     on\n"
        else:
            text += "repeat:     off\n"
        if (stat['random'] == '1'):
            text += "random:     on\n"
        else:
            text += "random:     off\n"
        text += "volume:    %s" %(stat['volume'])

        pop = PopupBox(text)
        pop.show()
