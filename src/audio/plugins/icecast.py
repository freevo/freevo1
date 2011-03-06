# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Browse and play shoutcast radio stations
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
#
# Description:
#   browse and play icecast radio station
#
# Usage: Simply add the following lines to your local_conf.py:
#    plugin.activate('audio.icecast')
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
import cPickle
import urllib2

from event import *
from audio.player import PlayerGUI
from item import Item
from audio.audioitem import AudioItem
from gui.ProgressBox import ProgressBox

from xml.sax import make_parser, handler, saxutils
from xml.sax.handler import ContentHandler

from urlparse import urlparse

class StationParser(handler.ContentHandler):
    def __init__(self, genres, audiotypes=None, genremap=None, bitrates=None):
        self.inEntry = False
        self.element = ""
        self.station = { "name":"", "listen_url":"", "audiotype":"", "bitrate":"", "genres":{} }
        self.value = ""
        self.stations = []
        self.genres = genres

        if bitrates == None:
            self.bitrates = {}
        else:
            self.bitrates = bitrates

        if audiotypes == None:
            self.audiotypes = [ 'MP3', 'OGG', 'AAC', 'AAC+' ]
        else:
            self.audiotypes = audiotypes

        if genremap == None:
            self.genremap = {}
        else:
            self.genremap = genremap


    def startElement(self, name, attrs):
        self.value = ""


    def endElement(self, name):
        if name == 'entry':
            if self.station['audiotype'] in self.audiotypes:
                self.stations.append(self.station)
            self.station = { "name":"", "listen_url":"", "audiotype":"", "bitrate":"", "genres":{} }
        else:
            if name == 'server_name':
                self.station['name'] = self.value
            elif name == 'listen_url':
                self.station['listen_url'] = self.value
            elif name == 'server_type':
                if self.value == 'audio/mpeg':
                    self.station['audiotype'] = 'MP3'
                elif self.value == 'application/ogg':
                    if self.station['listen_url'][:-4] == '.ogv':
                        self.station['audiotype'] = 'OGG Theora'
                    else:
                        self.station['audiotype'] = 'OGG'
                elif self.value == 'audio/aacp':
                    self.station['audiotype'] = 'AAC+'
                elif self.value == 'audio/aac':
                    self.station['audiotype'] = 'AAC'
                elif self.value == 'video/nsv':
                    self.station['audiotype'] = 'NUPPLE'
                elif self.value == 'data':
                    self.station['audiotype'] = 'DATA'
            elif name == 'genre':
                if self.station['audiotype'] in self.audiotypes:
                    for g in self.value.split(' '):
                        g = g.lower()

                        ## genre remapping
                        if self.genremap.has_key(g):
                            g = self.genremap[g]

                        self.station['genres'][g] = g
                    for g in self.station['genres'].keys():
                        try:
                            self.genres[g] += 1
                        except:
                            self.genres[g] = 1
            elif name == 'bitrate':
                self.station['bitrate'] = self.value
                try:
                    self.bitrates[self.value] += 1
                except:
                    self.bitrates[self.value] = 1


    def characters(self, content):
        self.value = content



class IcecastAudioMenuItem(Item):
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
        self.name = ( _('Icecast Radio') )

        self.min_bitrate = int(config.ICECAST_MIN_BITRATE)
        self.cache_ttl = int(config.ICECAST_TTL)
        self.max_bitrate = int(config.ICECAST_MAX_BITRATE)
        self.max_bitrate = 0
        self.yellowpages = config.ICECAST_YPS
        self.audiotypes = config.ICECAST_AUDIOTYPES
        self.genremapping = config.ICECAST_GENRE_MAP

        self.cacheFolder = str(config.FREEVO_CACHEDIR) + '/icecast/'
        if not os.path.isdir(self.cacheFolder):
            os.mkdir(self.cacheFolder)

        self.stations = {}
        self.genres = {}
        self.bitrates = {}


    def actions(self):
        """
        Actions for the Main Menu
        """
        return [ ( self.generate_main_menu, _('Filter By') ) ]


    def generate_main_menu(self, arg=None, menuw=None):
        self.retrievexml()
        gm = []
        gm.append(menu.MenuItem('Genre', action = self.generate_sub_menu, arg = {'genre':''}))
        gm.append(menu.MenuItem('Format', action = self.generate_sub_menu, arg = {'audiotype':''}))
        gm.append(menu.MenuItem('Bitrate', action = self.generate_sub_menu, arg = {'bitrate':''}))

        gms = menu.Menu( _('Filter By'), gm, item_types = 'audio')
        menuw.pushmenu(gms)


    def retrievexml(self):
        socktimeout = socket.getdefaulttimeout()
        self.genres = {}
        self.stations = {}
        try:
            finfo = os.stat(self.cacheFolder + 'built.pickle')
            ftime = finfo[ST_MTIME]
        except:
            ftime = -1

        if ftime > 0:
            delta = time.time() - ftime
        else:
            delta = self.cache_ttl + 5

        if delta < self.cache_ttl:
            fd = open(self.cacheFolder + 'built.pickle', "rb")
            self.stations = cPickle.load(fd)
            self.genres = cPickle.load(fd)
            self.bitrates = cPickle.load(fd)
            fd.close()
            return

        genrelist = []
        stationlist = []
        socket.setdefaulttimeout(20)
        for url in self.yellowpages:
            cachefile = self.cacheFolder
            xmlfile = self.cacheFolder
            glist = []
            slist = []

            purl = urlparse(url)
            cachefile += '%s.pickle' % purl.netloc
            xmlfile += '%s.xml' % purl.netloc

            pop = ProgressBox(text = _('Fetching Feed %s') % url, full = 2)
            pop.show()
            try:
                finfo = os.stat(xmlfile)
                ftime = finfo[ST_MTIME]
            except:
                ftime = -1

            if ftime > 0:
                delta = time.time() - ftime
            else:
                delta = self.cache_ttl + 5
            if delta > self.cache_ttl:
                tries = 5
                while tries > 0:
                    try:
                        cache = open(xmlfile, 'w')
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
                            pop.destroy()
                            return None
            pop.tick()

            pop.destroy()
            socket.setdefaulttimeout(socktimeout)
            pop2 = ProgressBox(text = _('Parsing Feed %s') % url, full = 1)
            pop2.show()

            parser = make_parser()
            parseXML = StationParser(self.genres, self.audiotypes, self.genremapping, self.bitrates)
            parser.setContentHandler(parseXML)
            parser.parse(xmlfile)
            stationlist += parseXML.stations
            self.genres = parseXML.genres
            self.bitrates = parseXML.bitrates
            pop2.destroy()

        pop = ProgressBox(text = _('Building Station List'), full = len(stationlist))
        pop.show()
        for station in stationlist:
            key = "%s%s%s" % (  station["name"], station["bitrate"], station["listen_url"] )
            self.stations[key] = station

        pop.destroy()
        fd = open(self.cacheFolder + 'built.pickle',"wb")
        cPickle.dump(self.stations, fd)
        cPickle.dump(self.genres, fd)
        cPickle.dump(self.bitrates, fd)
        fd.close()


    def __builditem(self, station):
        statbr = station['bitrate']
        try:
            statbr_int = int(statbr)
        except:
            statbr = "0"

        stationitem = AudioItem(station['listen_url'], self, station['name'], False)
        stationitem.player = 'mplayer'
        stationitem.reconect = True
        stationitem.network_play = True
        if station['listen_url'].find('.',-6) == -1 and station['audiotype'] == 'MP3':
            stationitem.is_playlist = True
        else:
            stationitem.is_playlist = False

        stationitem.is_playlist = False
        if station['audiotype'][:3] == 'AAC':
            stationitem.mplayer_options = '-demuxer aac'
        elif station['audiotype'] == 'OGG':
            stationitem.mplayer_options = '-demuxer ogg'
        #else:
            #stationitem.mplayer_options = '-demuxer audio'

        stationitem.bitrate = int(statbr)
        stationitem.length = 0
        stationitem.remain = 0
        stationitem.info = {
            'title':station['name'],
            'description':'%s - %skbs - %s' % (station['audiotype'], statbr, " ".join(station['genres'].keys()))
        }
        return stationitem


    def generate_sub_menu(self, arg=None, menuw=None):
        """
        Generates the genre list menu
        """
        gm = []
        if arg.has_key('genre'):
            if arg['genre'] == '':
                for genre in self.genres.keys():
                    gm.append(menu.MenuItem('[%s] (%d)' % (genre, self.genres[genre]), action = self.generate_sub_menu, arg = {'genre':genre}))

                gm.sort(key = self.genresortkey)
                gms = menu.Menu( _('Genre'), gm, item_types = 'audio')
                rc.app(None)
                menuw.pushmenu(gms)
                menuw.refresh()
                return
        if arg.has_key('audiotype'):
            if arg['audiotype'] == '':
                gm = []
                for atype in self.audiotypes:
                    gm.append(menu.MenuItem('[%s]' % atype, action = self.generate_sub_menu, arg = {'audiotype':atype} ))

                gms = menu.Menu( _('Format'), gm, item_types = 'audio')
                rc.app(None)
                menuw.pushmenu(gms)
                menuw.refresh()
                return

        if arg.has_key('bitrate'):
            if arg['bitrate'] == '':
                gm = []
                for br in self.bitrates.keys():
                    gm.append(menu.MenuItem('[%s] (%d)' % (br, self.bitrates[br]), action = self.generate_sub_menu, arg = {'bitrate':br}))
                gm.sort(key = self.genresortkey)
                gms = menu.Menu( _('Bitrate'), gm, item_types = 'audio')
                rc.app(None)
                menuw.pushmenu(gms)
                menuw.refresh()
                return

        stationlist = []
        for stationk in self.stations.keys():
            add = False
            station = self.stations[stationk]
            for stfilter in arg.keys():
            ##genre
                if stfilter == 'genre':
                    if station['genres'].has_key(arg[stfilter]):
                        add = True
                else:
                    if station[stfilter] == arg[stfilter]:
                        add = True
            if add:
                stationlist.append(self.__builditem(station))
        stationlist.sort(key = self.stationsortkey)

        stationmenu = menu.Menu( arg, stationlist, item_types = 'audio' )
        rc.app(None)
        menuw.pushmenu(stationmenu)
        menuw.refresh()
        return


    def stationsortkey(self, arg):
        return "%s - %03d" % ( arg.name.lower(), int(arg.bitrate) )


    def genresortkey(self, arg):
        return arg.name



class PluginInterface(plugin.MainMenuPlugin):
    """
    Browse and play Icecast Radio streams

    activation
    plugin.activate('audio.icecast')

    configuration variables:
    | ICECAST_TTL = 3600
    |   time in seconds before fetching from the web again
    | ICECAST_MIN_BITRATE = 0
    |   the minimum bitrate a station must have to be displayed
    |   0 to disable
    | ICECAST_MAX_BITRATE = 0
    |   the maximum bitrate a station must have to be displayed
    |   0 to disable
    | ICECAST_YPS = [ 'http://dir.xiph.org/yp.xml' ]
    |   the icecast yellow pages to retrieve
    | ICECAST_AUDIOTYPES = [ 'MP3', 'OGG', 'AAC', 'AAC+' ]
    |   a list of the types to display - full list [ 'MP3', 'OGG', 'AAC', 'AAC+', 'NUPPEL', 'OGG Theora', 'DATA' ]
    """
    __author__        = 'Ian Denton'
    __author_email__  = 'Ian Denton <ian at mad-prof.co.uk>'
    __version__       = '0.2'


    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)


    def items(self, parent):
        return [ IcecastAudioMenuItem(parent) ]


    def config(self):
        return [
            ('ICECAST_TTL', 3600, _("Use the cache, TTL default is 1 minute, set to 0 to disable") ),
            ('ICECAST_MIN_BITRATE', 0, _("Minimum bitrate of stations to display - 0 to disable") ),
            ('ICECAST_MAX_BITRATE', 0, _("Maximum bitrate of stations to display - 0 to disable") ),
            ('ICECAST_YPS', [ 'http://dir.xiph.org/yp.xml' ], _("Icecast yellowpages xml urls") ),
            ('ICECAST_AUDIOTYPES', [ 'MP3', 'OGG', 'AAC', 'AAC+' ], _("a list of the types to display - full list [ 'MP3', 'OGG', 'AAC', 'AAC+', 'NUPPEL', 'OGG Theora', 'DATA' ]") ),
            ('ICECAST_GENRE_MAP', None, '')
       ]
