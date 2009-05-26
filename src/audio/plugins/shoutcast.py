# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Browse and play shoutcast radio stations
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
#
# Description:
#   browse and play shoutcast radio station
#
# Usage: Simply add the following lines to your local_conf.py:
#    plugin.activate('audio.shoutcast')
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
import menu
import plugin
import time
import config
import rc
import util
import os
import sys
import socket
from stat import *

import urllib2

from event import *
from audio.player import PlayerGUI
from item import Item
from audio.audioitem import AudioItem
from gui.ProgressBox import ProgressBox

from xml.sax import make_parser, handler, saxutils
from xml.sax.handler import ContentHandler

class GenreParser(handler.ContentHandler):
    def __init__(self):
        handler.ContentHandler.__init__(self)
        self.genrelist = []


    def startElement(self, name, attrs):
        if name == 'genre':
            self.genrelist.append(attrs['name'])



class StationParser(handler.ContentHandler):
    def __init__(self):
        handler.ContentHandler.__init__(self)
        self.stationlist = []
        self.tunein = ''

    def startElement(self, name, attrs):
        if name == 'tunein':
            self.tunein = attrs['base']
        elif name == 'station':
            self.stationlist.append(attrs)



class ShoutcastAudioMenuItem(Item):
    """
    Creates the Audio Menu item
    """
    def __init__(self, parent):
        """
        Sets up the configuration variables
        """
        if not config.SYS_USE_NETWORK:
            self.reason = _('SYS_USE_NETWORK not enabled')
            return

        Item.__init__(self, parent, skin_type = 'audio')
        self.name = ( _('Shoutcast Radio') )
        self.min_bitrate = int(config.SHOUTCAST_MIN_BITRATE)
        self.cache_ttl = int(config.SHOUTCAST_TTL)
        self.max_bitrate = int(config.SHOUTCAST_MAX_BITRATE)

        self.cacheFolder = str(config.FREEVO_CACHEDIR) + '/shoutcast/'
        if not os.path.isdir(self.cacheFolder):
            os.mkdir(self.cacheFolder)


    def actions(self):
        """
        Actions for the Main Menu
        """
        return [ ( self.generate_genre_menu, _('Genres') ) ]


    def retrievexml(self, genre=None):
        socktimeout = socket.getdefaulttimeout()
        cachefile = self.cacheFolder
        url = 'http://www.shoutcast.com/sbin/newxml.phtml'
        if genre == None:
            cachefile += 'ShoutcastGenres.xml'
        else:
            cachefile += genre
            url += '?genre=%s' % urllib2.quote(genre)

        try:
            finfo = os.stat(cachefile)
            ftime = finfo[ST_MTIME]
        except:
            ftime = -1

        tries = 5
        if ftime > 0:
            delta = time.time() - ftime
        else:
            delta = self.cache_ttl + 5

        socket.setdefaulttimeout(20)
        if delta > self.cache_ttl:
            while tries > 0:
                try:
                    cache = open(cachefile, 'w')
                    f = urllib2.urlopen(url)
                    xmlt = "".join(f.readlines())
                    f.close()
                    cache.write(xmlt)
                    cache.close()
                    tries = 0
                except:
                    if tries > 0:
                        time.sleep(5)
                        tries -= 1
                    else:
                        socket.setdefaulttimeout(socktimeout)
                        return None

        socket.setdefaulttimeout(socktimeout)
        return cachefile


    def generate_genre_menu(self, arg=None, menuw=None):
        """
        Generates the genre list menu
        """
        genrelist = []
        pop = ProgressBox(text = _('Fetching Shoutcast Genres'), full = 2)
        pop.show()

        xmlfile = self.retrievexml()
        pop.tick()
        if xmlfile == None:
            genrelist =  [ menu.MenuItem( _('Error retrieving genres'), action = menuw.goto_prev_page, arg = None) ]
        else:
            parser = make_parser()
            parseGenreXML = GenreParser()
            parser.setContentHandler(parseGenreXML)
            parser.parse(xmlfile)
            try:
                for genre in parseGenreXML.genrelist:
                    genrelist.append( menu.MenuItem(genre, action = self.generate_station_list, arg = genre ) )
            except:
                genrelist =  [ menu.MenuItem( _('Error retrieving genres'), action = menuw.goto_prev_page, arg = None) ]

        genremenu = menu.Menu( _("Genres"), genrelist, item_types = 'audio' )
        rc.app(None)
        menuw.pushmenu(genremenu)
        menuw.refresh()
        pop.destroy()


    def stationsortkey(self, arg):
        return "%s - %03d" % ( arg.name.lower(), arg.bitrate )


    def generate_station_list(self, arg=None, menuw=None):
        """
        Generates the Station List
        """
        stationlist = []
        pop = ProgressBox(text = _('Fetching station list for %s') % arg, full = 2)
        pop.show()
        xmlfile = self.retrievexml(arg)
        pop.tick()

        if xmlfile == None:
            stationlist = [ menu.MenuItem( _('Error retrieving stations'), action = menuw.goto_prev_page, arg = None) ]
        else:
            try:
                parser = make_parser()
                parseStationXML = StationParser()
                parser.setContentHandler(parseStationXML)
                parser.parse(xmlfile)
                for station in parseStationXML.stationlist:
                    statid = urllib2.quote(station["id"])
                    statname = station["name"]
                    statbr = station["br"]
                    statct = station['ct']
                    if int(statbr) >= self.min_bitrate and (self.max_bitrate == 0 or int(statbr) <= self.max_bitrate):
                        stationitem = AudioItem('http://www.shoutcast.com%s?id=%s' % (parseStationXML.tunein, statid), self, statname, False)
                        stationitem.player = 'mplayer'
                        stationitem.reconect = True
                        stationitem.network_play = True
                        stationitem.is_playlist = True
                        stationitem.bitrate = int(statbr)
                        stationitem.length = 0
                        stationitem.remain = 0
                        stationitem.info = {'title':statname, 'description':'%s - %skbs' % (station['genre'], statbr) }
                        stationlist.append(stationitem)
                    stationlist.sort(key = self.stationsortkey)
            except:
                stationlist = [ menu.MenuItem( _('Error retrieving stationlist'), action = menuw.goto_prev_page, arg = None) ]

            stationmenu = menu.Menu( arg, stationlist, item_types = 'audio' )
            rc.app(None)
            menuw.pushmenu(stationmenu)
            menuw.refresh()
            pop.destroy()



class PluginInterface(plugin.MainMenuPlugin):
    """
    Browse and play Shoutcast Radio streams

    activation
    plugin.activate('audio.shoutcast')

    configuration variables:
    | SHOUTCAST_TTL = 600
    |   time in seconds before fetching from the web again
    | SHOUTCAST_MIN_BITRATE = 0
    |   the minimum bitrate a station must have to be displayed
    |   0 to disable
    | SHOUTCAST_MAX_BITRATE = 0
    |   the maximum bitrate a station must have to be displayed
    |   0 to disable
    """
    __author__        = 'Ian Denton'
    __author_email__  = 'Ian Denton <ian at mad-prof.co.uk>'
    __version__       = '0.2'

    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)


    def items(self, parent):
        return [ ShoutcastAudioMenuItem(parent) ]


    def config(self):
        return [
            ('SHOUTCAST_TTL', 600, _("Use the cache, TTL default is 10 mins, set to 0 to disable") ),
            ('SHOUTCAST_MIN_BITRATE', 0, _("Minimum bitrate of stations to display - 0 to disable") ),
            ('SHOUTCAST_MAX_BITRATE', 0, _("Maximum bitrate of stations to display - 0 to disable") ) ]
