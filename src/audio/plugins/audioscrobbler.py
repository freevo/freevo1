# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Audio scrobbler plug-in
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

import string
import copy
import os, re, sys, re, urllib, md5, time, locale, math

# From Freevo
import config, plugin, rc
from event import *
from util.audioscrobbler import Audioscrobbler, AudioscrobblerException
import util.audioscrobbler


#
# Some parts here are from the LCD plugin.
#
# The rest is the creation of Erik Pettersson
# irc: ikea/ieka on irc.freenode.org
# lastfm: ieka
# mail: tankdriverikea AT gmail DOT com
# mail: petterson.erik AT gmail DOT com
#
# This code is under the GPL License
#


# TODO Re-login code sleeps, is that allowed?
# TODO Add support for batch-sending (This will be there for Freevo 2.0 - maybe)


class PluginInterface(plugin.DaemonPlugin):
    """
    Submit information to the AudioScrobbler project about tracks played
    Written by Erik Pettersson, petterson.erik@gmail.com, activation::

        plugin.activate('audioscrobbler')
        LASTFM_USER = 'username'
        LASTFM_PASS = 'password'
    """

    def __init__(self):
        """
        Set up the basics, register with Freevo and connect
        """
        _debug_('PluginInterface.__init__()', 2)
        if not config.LASTFM_USER or not config.LASTFM_PASS:
            self.reason = 'LASTFM_USER or LASTFM_PASS have not been set'
            return

        plugin.DaemonPlugin.__init__(self)

        # DeamonPlugin internal settings.
        self.poll_interval = 3000
        self.poll_menu_only = False
        self.event_listener = 1

        # Register ourselves
        plugin.register(self, "audioscrobbler")

        # Internal Plugin Setting
        self.playitem = False
        self.failed_retries = 0
        self.logged_in = False
        self.lastsong = ''
        self.sleep_timeout = 0
        self.starttime = time.time()
        self.elapsed = 0

        util.audioscrobbler.DEBUG = config.LASTFM_DEBUG
        logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'audioscrobbler.session')
        self.lastfm = Audioscrobbler(config.LASTFM_USER, config.LASTFM_PASS, logincachefilename)


    def config(self):
        _debug_('config()', 2)
        return [
            ('LASTFM_USER', None, 'User name for last FM'),
            ('LASTFM_PASS', None, 'Password for Last FM'),
            ('LASTFM_DEBUG', False, 'Enable debugging information'),
        ]


    def poll(self):
        """
        Run this code every self.poll_interval seconds
        """
        _debug_('poll()', 2)
        if self.sleep_timeout:
            if math.ceil(time.time() - self.sleep_timeout) > 30*60:
                self.sleep_timeout = False
                return

        if self.playitem and self.logged_in:
            self.draw(('player', self.playitem), None)


    def draw(self, (ttype, object), osd):
        """
        This is from the LCD plugin. With some modification.
        I don't know what this does, or how it does it so I'll just let it be for now.
        Original docstring:
        'Draw' the information on the LCD display.
        """
        _debug_('draw((ttype=%r, object=%r), osd=%r)' % (ttype, object, osd), 2)
        if ttype != 'player':
            return
        player = object
        title  = player.getattr('title')
        album = None
        if not title:
            title = player.getattr('name')

        if player.type == 'audio':
            playing = '__audio'
            if player.getattr('trackno'):
                starttime = self.starttime
                song    = player.getattr('trackno')
                artist  = player.getattr('artist')
                length  = player.getattr('length')
                album   = player.getattr('album')
                elapsed = int(player.elapsed)
                length = str(int(length.split(":")[0])*60 + int(length.split(":")[1]))
                self.elapsed = time.time() - self.starttime

                # We do not send unless the song is longer than 30 seconds
                if length > 30:
                    # We send only when 240 seconds or 50% have elapsed. Adhering to Audioscrobbler rules
                    if self.elapsed > 240 or self.elapsed > int(length)/2:
                        try:
                            self.lastfm.submit(artist, title, starttime, 'P', 'L', length, album, song)
                        except AudioscrobblerException, why:
                            _debug_('%s' % why, DERROR)


    def eventhandler(self, event, menuw=None):
        """
        Get events from Freevo
        """
        _debug_('eventhandler(event=%r, menuw=%r)' % (event.name, menuw), 2)
        if event == PLAY_START:
            self.playitem = event.arg
            self.starttime = time.time()

        if event == PLAY_END:
            self.playitem = False

        if event == STOP:
            self.playitem =  False
            self.elapsed = 0

        if event == PLAYLIST_NEXT:
            self.starttime = time.time()

        if event == SEEK:
            self.elapsed = 0

        return 0
