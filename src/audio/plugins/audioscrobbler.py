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
try:
    import cPickle as pickle
except ImportError:
    import pickle

# From Freevo
import config, plugin, rc
from event import *
from util.audioscrobbler import Audioscrobbler, AudioscrobblerException
import util.audioscrobbler

from benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL


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

    @benchmark(benchmarking & 0x4, benchmarkcall)
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
        self.playitem = None
        self.starttime = time.time()
        self.failed = []
        self.logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'audioscrobbler.session')
        self.failedcachefilename = os.path.join(config.FREEVO_CACHEDIR, 'audioscrobbler.pickle')
        self.nowplaying = False
        self.submitted = None

        util.audioscrobbler.DEBUG = config.LASTFM_DEBUG
        self.lastfm = Audioscrobbler(config.LASTFM_USER, config.LASTFM_PASS, self.logincachefilename)
        try:
            f = open(self.failedcachefilename, 'r')
            self.failed = pickle.load(f)
            f.close()
        except IOError:
            pass


    @benchmark(benchmarking & 0x4, benchmarkcall)
    def shutdown(self):
        _debug_('shutdown()', 2)
        try:
            f = open(self.failedcachefilename, 'w')
            pickle.dump(self.failed, f, 1)
            f.close()
        except IOError:
            pass


    @benchmark(benchmarking & 0x4, benchmarkcall)
    def config(self):
        _debug_('config()', 2)
        return [
            ('LASTFM_USER', None, 'User name for last FM'),
            ('LASTFM_PASS', None, 'Password for Last FM'),
            ('LASTFM_DEBUG', False, 'Enable debugging information'),
        ]


    @benchmark(benchmarking & 0x4, benchmarkcall)
    def poll(self):
        """
        Run this code every self.poll_interval seconds
        """
        _debug_('poll()', 2)
        if self.playitem is not None:
            self.draw(('player', self.playitem), None)


    @benchmark(benchmarking & 0x4, benchmarkcall)
    def draw(self, (ttype, object), osd):
        """
        'draw' is called about once a second when playing audio
        call submit a song if the track has a track number
        """
        _debug_('draw((ttype=%r, object=%r), osd=%r)' % (ttype, object, osd), 2)
        if ttype != 'player':
            return

        player = object
        if player.type == 'audio':
            playing = '__audio'
            if player.getattr('trackno'):
                self.submit_song(player)


    @benchmark(benchmarking & 0x4, benchmarkcall)
    def eventhandler(self, event, menuw=None):
        """
        Get events from Freevo
        """
        _debug_('eventhandler(event=%r:%r, menuw=%r)' % (event.name, event.arg, menuw), 2)
        print event
        if event == PLAY_START:
            self.playitem = event.arg
            self.starttime = time.time()
            self.nowplaying = True

        if event == PLAY_END:
            self.playitem = None

        if event == STOP:
            self.playitem = None

        if event == PLAYLIST_NEXT:
            self.starttime = time.time()

        if event == SEEK:
            self.starttime = time.time()

        return 0


    @benchmark(benchmarking & 0x4, benchmarkcall)
    def submit_song(self, player):
        artist    = player.getattr('artist')
        track     = player.getattr('title') or player.getattr('name')
        starttime = self.starttime
        length    = player.getattr('length')
        secs      = length and int(length.split(":")[0])*60 + int(length.split(":")[1]) or 0
        album     = player.getattr('album')
        trackno   = player.getattr('trackno')
        elapsed   = time.time() - self.starttime
        keystr = track+'|'+artist+'|'+str(int(starttime))+'|'+length+'|'+album+'|'+trackno
        key = md5.new(keystr).hexdigest()

        if self.nowplaying:
            self.nowplaying = False
            try:
                self.lastfm.nowplaying(artist, track, album)
            except:
                pass

        # We don't submit the same song instance more than once
        if self.submitted == key:
            return
        # We do not send unless the song is longer than 30 seconds
        if secs <= 30:
            return
        # We send only when 240 seconds or 50% have elapsed. Adhering to Audioscrobbler rules
        if elapsed <= 240 and elapsed <= secs/2:
            return

        self.submitted = key
        try:
            self.lastfm.submit(artist, track, starttime, 'P', 'L', secs, album, trackno)
        except AudioscrobblerException, why:
            self.failed.append(('AE', artist, track, starttime, 'P', 'L', secs, album, trackno, why))
            _debug_('%s' % why, DERROR)
        except IOError, why:
            self.failed.append(('IO', artist, track, starttime, 'P', 'L', secs, album, trackno, why))
            _debug_('%s' % why, DWARNING)
