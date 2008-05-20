# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Audio scrobbler plug-in
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#   replace prints with _debug_s
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

#From Python
import os, re, sys, re, urllib, md5, time, locale, math

# From Freevo
import plugin, config, rc
from event import *


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
# TODO Change from 'tst' to 'frv' or whatever Russ finds appropiate
# TODO Add support for batch-sending (This will be there for Freevo 2.0 - maybe)


class PluginInterface(plugin.DaemonPlugin):
    """
    Submit information to the AudioScrobbler project about tracks played
    Written by Erik Pettersson, petterson.erik@gmail.com, activation::

        plugin.activate('audioscrobbler')
        AS_USER = 'username'
        AS_PASSWORD = 'password'
    """

    def __init__(self):
        """
        Set up the basics, register with Freevo and connect
        """
        if not config.AS_USER or not AS_PASSWORD:
            self.reason = 'AS_USER or AS_PASSWORD have not been set'
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
        self.elapsed = 0

        self.USER = self.utf8(config.AS_USER)
        self.PASSWORD = config.AS_PASSWORD
        self.debug = config.AS_DEBUG

        # Login
        self.login()


    def config(self):
        return [
            ('AS_USER', None, 'User name for last FM'),
            ('AS_PASSWORD', None, 'Password for Last FM'),
            ('AS_DEBUG', 0, 'Enable debugging information'),
        ]


    def login(self):
        """
        Login, each session is ok for 30 mins or something like that

        @todo: If we fail we shouldn't not retry right away, but can we really sleep like this?
        """
        if self.failed_retries > 15:
            print "AudioScrobbler plugin: Tried to login 15 times and failed on 15 occasions: Exiting"
            self.shutdown()

        login_string = 'http://post.audioscrobbler.com/?hs=true&p=1.1&c=fvo&v=1.0&u=' + self.USER

        try:
            lo = urllib.urlopen(login_string)
            lo = lo.read()
        except:
            print "AudioScrobbler plugin: Fail to receive data from server, sleeping and retrying later"
            self.failed_retries += 1
            self.sleep_timeout = time.time()
            return

        match = re.match(u'.*?BADUSER.*', lo)
        if match:
            print "AudioScrobbler plugin: Bad username: Exiting"
            self.shutdown()

        match = re.search(u'INTERVAL\s(\d+)\n', lo)
        if match:
            self.interval = match.groups(1)[0]

        match = re.match(u'(\.*?)\n.*', lo)
        if match:
            if match.groups(1)[0] != 'UPTODATE':
                print "AudioScrobbler plugin: I'm old, I'm old! Please update me!"
                print "AudioScrobbler plugin: ", match.groups(1)[0]

        match = re.match(u'.*?\n(.*?)\n.*', lo)
        if match:
            self.challenge = match.groups(1)[0]
        else:
            print "AudioScrobbler plugin: Didn't find challenge string, retrying"
            self.failed_retries += 1
            return

        match = re.match(u'.*?\n.*?\n(.*?)\n.*', lo)
        if match:
            self.submiturl = match.groups(1)[0]
        else:
            print "AudioScrobbler plugin: Didn't find submit url, retrying"
            self.failed_retries += 1
            return # If we didn't get this we assume that their server is down and try to re-login

        self.challenge_reply = md5.md5(md5.md5(self.PASSWORD).hexdigest() + self.challenge).hexdigest()
        self.challenge_reply = self.utf8(self.challenge_reply)
        self.logged_in = True
        self.failed_reties = 0


    def poll(self):
        """
        Run this code every self.poll_interval seconds
        """
        if self.sleep_timeout:
            if math.ceil(time.time() - self.sleep_timeout) > 30*60:
                self.sleep_timeout = False
                return

        if not self.logged_in:
            self.login()

        if self.playitem and self.logged_in:
            self.draw(('player', self.playitem), None)


    def shutdown(self):
        """
        Kill ourselves
        """
        print 'AudioScrobbler plugin: I have shut down'
        plugin.shutdown(plugin_name='audioscrobbler')
        #sys.exit() # Ugly hack to shut down the plugin


    def draw(self, (ttype, object), osd):
        """
        This is from the LCD plugin. With some modification.
        I don't know what this does, or how it does it so I'll just let it be for now.
        Original docstring:
        'Draw' the information on the LCD display.
        """
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
                song    = player.getattr('trackno')
                artist  = player.getattr('artist')
                length  = player.getattr('length')
                album   = player.getattr('album')
                elapsed = int(player.elapsed)
                length = str(int(length.split(":")[0])*60 + int(length.split(":")[1]))
                # Erm. This function gets called every second altho' it shouldn't be. Let's build on a bug :>
                self.elapsed += 1

                # We do not send unless the song is longer than 30 seconds
                if length > 30:
                    # We send only when 240 seconds or 50% have elapsed. Adhering to Audioscrobbler rules
                    if self.elapsed > 240 or self.elapsed > int(length)/2:
                        self.submit_song(artist, title, length, album)


    def submit_song(self, artist, track, length, album=''):
        """
        Send song information to AudioScrobbler. I'm ashamed of this part, it's butt ugly...
        """
        if self.debug:
            print "AudioScrobbler Debug: Got song:", str(artist), str(track), str(length), str(album)

        if self.lastsong == artist + track:
            return
        if album == None:
            album = ''

        # Doing weak filtering
        filter = [None, '', 'track', 'artist', 'group', 'band', 'song']
        if artist.lower() not in filter and track.lower() not in filter:
            if album == None:
                album = ''

            params = {
                'u': self.urlenc(self.USER),
                's': self.urlenc(self.challenge_reply),
                'a[0]': self.urlenc(artist),
                't[0]': self.urlenc(track),
                'b[0]': self.urlenc(album),
                'm[0]': '', #TODO Who got this for their mp3's? Add support some day
                'l[0]': length,
                'i[0]': self.urlenc(time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))
            }
            cparams = ''
            for n in params:
                cparams += n + '=' + params[n] + '&'
            cparams = cparams.rstrip('&').replace('+', '%20')
            cparams = self.utf8(cparams)
            try:
                dl = urllib.urlopen(self.submiturl, cparams)
                dl = dl.read()
            except:
                self.logged_in = False
                return

            match = re.search(u'BADAUTH', dl)
            if match:
                print "AudioScrobbler plugin: Failed to submit info: Bad password or username: Exiting"
                self.shutdown()

            match = re.match(u'FAILED.*', dl)
            if match:
                print "AudioScrobbler plugin: Failed to submit info (unknown reason): Printing debug info and exiting"
                print "AudioScrobbler plugin: Debug info:" + dl
                self.shutdown()

            if self.debug:
                match = re.search(u'OK', dl)
                if match and self.debug:
                    print "AudioScrobbler DEBUG: INFORMATION SENT, I REPEAT, INFORMATION SENT!"
                    print str(dl)

            match = re.search(u'INTERVAL (\d+)', dl)
            if match:
                self.interval = int(match.group(1))

                if self.interval > self.poll_interval: # Can we really sleep here?
                    print 'AudioScrobbler plugin: SORRY, ugly hack, have to sleep here.'
                    print 'Locks up Freevo but adheres the Last FM rules. Again, Im sorry.'
                    time.sleep(self.interval-self.poll_interval)

            self.lastsong = artist + track


    def urlenc(self, s):
        return urllib.urlencode({'':s}).lstrip('=')


    def eventhandler(self, event, menuw=None):
        """
        Get events from Freevo
        """
        if event == PLAY_START:
            self.playitem = event.arg
            self.elapsed = 0

        if event == PLAY_END:
            self.playitem = False
            self.elapsed = 0

        if event == STOP:
            self.playitem =  False
            self.elapsed = 0

        if event == PLAYLIST_NEXT:
            self.elapsed = 0

        if event == SEEK:
            self.elapsed = 0

        return 0


    def utf8(self, s):
        """
        From kaa.base:
        Returns a UTF-8 string, converting from other character sets if
        necessary.
        """
        return self.str_to_unicode(s).encode("utf-8")


    def str_to_unicode(self, s):
        """
        From kaa.base:
        Attempts to convert a string of unknown character set to a unicode
        string.  First it tries to decode the string based on the locale's
        preferred encoding, and if that fails, fall back to UTF-8 and then
        latin-1.  If all fails, it will force encoding to the preferred
        charset, replacing unknown characters.
        """
        if type(s) == unicode or s == None:
            return s

        for c in (locale.getpreferredencoding(), "utf-8", "latin-1"):
            try:
                return s.decode(c)
            except UnicodeDecodeError:
                pass

        return s.decode(local.getpreferredencoding(), "replace")
