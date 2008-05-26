# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# wwitv.py - Plugin for streaming tv on wwitv.com
# based on appletrailers.py by  Pierre Ossman
# -----------------------------------------------------------------------
#
# 04/21/08
# Notes:
#   this is my very first time I play with python, then be careful! (no warranty) ;-)
#   you can copy this plugin in the main freevo plugins directory
#   and add "plugin.activate('wwitv') in local_conf.py
#   to activate
#   OR
#   you can copy this plugin in the video/plugins directory
#   and add "plugin.activate('video.wwitv')" in local_conf.py
#   to activate
# Todo:
#   verify HTML2ENTITY utf-8
#   routine for progress box
# Bugs:
#   if you stop while caching you get bad redrawing of freevo window
#   problems with quicktime playlists (not play)
#
# -----------------------------------------------------------------------
# Copyright (C) 2008 Fabrizio Regondi (fabrintosh@gmail.com)
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


__author__           = 'Fabrizio Regondi'
__author_email__     = 'fabrintosh@gmail.com'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '0.1'


import os
import urllib2
import re
import config
import plugin
import menu
import stat
import time
import string
import util.fileops
import util.misc

from item import Item
from video.videoitem import VideoItem
from gui.ProgressBox import ProgressBox
from gui.AlertBox import AlertBox
from gui.PopupBox import PopupBox

categories = (
             ("new_tv/index.html", "New channels"),
             ("business_tv/index.html", "TV: Business news"),
             ("educational_tv/index.html", "TV: Educational"),
             ("entertainment_tv/index.html", "TV: Entertainment"),
             ("government_tv/index.html", "TV: Government"),
             ("children_tv/index.html", "TV: Kids"),
             ("lifestyle_tv/index.html", "TV: Lifestyle"),
             ("movie_tv/index.html", "TV: Movies"),
             ("music_tv/index.html", "TV: Music"),
             ("news_tv_live/index.html", "TV: News (live)"),
             ("news_tv_on_demand/index.html", "TV: News (vod)"),
             ("religious_tv/index.html", "TV: Religious"),
             ("shopping_tv/index.html", "TV: Shopping"),
             ("sports_tv/index.html", "TV: Sports"),
             ("weather_tv/index.html", "TV: Weather"),
             ("teletext_tv/index.html", "Teletext / Videotext"),
             ("webcam_tv/index.html", "Webcam streams")
)

MAX_CACHE_AGE = (60 * 60) * 8 # 8 hours

cachedir = os.path.join(config.FREEVO_CACHEDIR, 'wwitv')
if not os.path.isdir(cachedir):
    os.mkdir(cachedir,
            stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))
# only for test
#url_nations = "http://localhost/television/tvbar.htm"
#url_base = "http://localhost/television/"
#url_= "http://localhost/television/"

url_nations = "http://wwitv.com/television/tvbar.htm"
url_base = "http://wwitv.com/television/"
url_ = "http://wwitv.com/"
_nations = re.compile(r'''<a class="rb" href="([^"]*)" target="r">(.*)$''', re.IGNORECASE)
txdata = None
txheaders = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.1) Gecko/20060601 Firefox/2.0',
    'Accept-Language': 'en-us',
    }


class PluginInterface(plugin.MainMenuPlugin):
    """
    A freevo interface to http://wwitv.com

    plugin.activate('video.wwitv')
    """
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)

    def items(self, parent):
        return [ BrowseBy(parent) ]

class TvItem(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.skin_display_type = 'video'
        self.mainArray = {}
        self.nation_list = []
        self.nation_tv = {}
        self.categories_tv = {}
        self.__load()

    def __load(self):
        pfile = os.path.join(cachedir, 'data')
        if (os.path.isfile(pfile) == 0):
            popup = PopupBox(text=_('Downloading stream links'))
            popup.show()
            self.getNations()
            self.getCategories()
            popup.destroy()
            util.fileops.save_pickle(self.mainArray, pfile)
        else:
            if abs(time.time() - os.path.getmtime(pfile)) > MAX_CACHE_AGE:
                popup = PopupBox(text=_('Downloading stream links'))
                popup.show()
                self.getNations()
                self.getCategories()
                popup.destroy()
                util.fileops.save_pickle(self.mainArray, pfile)
        self.mainArray = util.fileops.read_pickle(pfile)
        self.nation_tv = self.mainArray['nation_tv']
        self.nation_list = self.mainArray['nation_list']
        self.categories_tv = self.mainArray['categories_tv']

    def getNations(self):
        try:
            req = urllib2.Request( url_nations, txdata, txheaders )
            response = urllib2.urlopen( req )
        except:
            print "errore url\n";
            popup.destroy()
            box = AlertBox( text=_( 'Failed to download channel list' ) )
            box.show()
            return
        all = ''
        for line in response.read().split( '\n' ):
            all += line + ' '
        myDict = []
        all = all.replace( '\r', '' ).replace( '\t', '' ).replace( '\n', '' )
        m = re.compile( r'''<a class="rb" href="([^"]*)" target="r">([^<]*)\s+(\d+)\s+</a>''', re.IGNORECASE ).findall( all )
        if m:
            for url, title, channels in m:
                myDict = [title.strip(), url_base + url, channels]
                self.nation_list.append( myDict )
            self.mainArray['nation_list'] = self.nation_list
            for i in self.nation_list:
                print "Scarico gli stream di: " + i[0]
                try:
                    req = urllib2.Request(i[1], txdata, txheaders)
                    response = urllib2.urlopen(req)
                except:
                    print "errore url\n";
                all = ''
                for line in response.read().split('\n'):
                    all += line
                myChannel = []
                all = all.replace('\r', '').replace('\t', '').replace('\n', '')
                # uncomment for qtl playlist (quicktime)
                #m = re.compile(r'''target="TV">([^<]*)</a></td><td class="(?:qm|qt|qr|wa)"><a class="(r|m|qu|w)" href="javascript:listen([^>]*)">([^<]*)</a> </td><td class="q"><center>(?:.*?)<font class="hd2">([^>]*)</td></tr>''', re.IGNORECASE).findall(all)
                # without qtl playlists
                m = re.compile(r'''target="TV">([^<]*)</a></td><td class="(?:qm|qr|wa)"><a class="(r|m|w)" href="javascript:listen([^>]*)">([^<]*)</a> </td><td class="q"><center>(?:.*?)<font class="hd2">([^>]*)</td></tr>''', re.IGNORECASE).findall(all)
                if m:
                    nation_channels = []
                    for  tv, gen, url, stream, desc in m:
                        #print tv + " " + gen + " " + url + " " + stream + " " + desc
                        myChannel = eval(url)
                        myDict = [util.htmlenties2txt(tv), myChannel[1], stream, util.htmlenties2txt(desc)]
            #          myDict = [myChannel[1], stream]
                        nation_channels.append(myDict)
                    self.nation_tv[i[0]] = nation_channels
                else:
                    print "non trovo corrispondenze!"
                self.mainArray['nation_tv'] = self.nation_tv
#                print len(nation_tv)
#                keylist = nation_tv.keys()
#                keylist.sort()
#                for key in keylist:
#                    print key
#                    print len(nation_tv[key])
#                    print nation_tv[key]




    def getCategories(self):
        for i in categories:
            try:
                print "download " + i[1] + " url: " + url_ + i[0]
                req = urllib2.Request( url_ + i[0], txdata, txheaders )
                response = urllib2.urlopen( req )
            except:
                print "errore url\n";
                #popup.destroy()
                box = AlertBox( text=_( 'Failed to download categories list' ) )
                box.show()
                return
            all = ''
            myDict = []
            for line in response.read().split('\n'):
                all += line
            myChannel = []
            all = all.replace('\r', '').replace('\t', '').replace('\n', '')
            # uncomment for qtl playlist (quicktime)
            #m = re.compile(r'''<tr><td class="q"><font class="hd2">([^<]*)</font></td><td class="name" width="120"><font class="new">(?:(?:[^<]*)|(?:\d\d\d\d-\d\d-\d\d<BR>))</font><a class="travel" href="(?:[^"]*)" target="TV">([^<]*)</a></td><td class="(?:qm|qt|qr|wa)"><a class="(r|m|qu|w)" href="javascript:listen([^>]*)">([^<]*)</a> </td><td class="q"><center>(?:.*?)></td><td class="qe"><font class="hd2">([^>]*)</td></tr>''', re.IGNORECASE).findall(all)
            # without qtl playlists
            m = re.compile(r'''<tr><td class="q"><font class="hd2">([^<]*)</font></td><td class="name" width="120"><font class="new">(?:(?:[^<]*)|(?:\d\d\d\d-\d\d-\d\d<BR>))</font><a class="travel" href="(?:[^"]*)" target="TV">([^<]*)</a></td><td class="(?:qm|qr|wa)"><a class="(r|m|w)" href="javascript:listen([^>]*)">([^<]*)</a> </td><td class="q"><center>(?:.*?)></td><td class="qe"><font class="hd2">([^>]*)</td></tr>''', re.IGNORECASE).findall(all)
            #m = re.compile(r'''<font class="hd2">([^<]*)</font>(?:.*?)target="TV">([^<]*)</a></td><td class="qm"><a class="(r|m|qu)" href="javascript:listen([^>]*)">([^<]*)</a> </td><td class="q"><center>(?:.*?)<font class="hd2">([^>]*)</td></tr>''', re.IGNORECASE).findall(all)
            if m:
                categories_channels = []
                for  state, tv, gen, url, stream, desc in m:
                #print state + " " + tv + " " + gen + " " + url + " " + stream + " " + desc
                    myChannel = eval(url)
                    mydesc = util.htmlenties2txt(desc) + "\n"  + util.htmlenties2txt(state)
                    myDict = [util.htmlenties2txt(tv), myChannel[1], stream, mydesc]
                    categories_channels.append(myDict)
                self.categories_tv[i[1]] = categories_channels
            else:
                print "non trovo corrispondenze!"
        self.mainArray['categories_tv'] = self.categories_tv


class Nation(Item):
    def __init__(self, nation, tv, parent):
        Item.__init__(self, parent)
        self.name = nation

        self.description = "Channels available: %d" % len(tv)

        self._tv = tv

    def actions(self):
        return [ (self.make_menu, 'Nation') ]

    def make_menu(self, arg=None, menuw=None):
        entries = []
        self._tv.sort()
        for i in self._tv:
            name = i[0]
            #entries.append(Tv(name, i, self))
            entries.append(TvVideoItem(name, i, self))
        menuw.pushmenu(menu.Menu(self.name, entries))

class TvVideoItem(VideoItem):
    #def __init__(self, name, url, parent):
    def __init__(self, name, tv, parent):
        #VideoItem.__init__(self, url, parent)
        VideoItem.__init__(self, tv[1], parent)
        self.name = name
        self.description = 'Stream: ' + tv[2]
        self.description += '\nInformation: ' + tv[3]
        self.description += "\nURL: "  + tv[1]
        self.is_playlist = True

class Tv(Item):
    def __init__(self, name, tv, parent):
        Item.__init__(self, parent)
        self.name = name
        self.type = 'video'
        self._tv = tv
        self.url = self._tv[1]
        self.mode = ''
        self.files = ''
        self.description = 'Stream: ' + self._tv[2]
        self.description += '\nInformation: ' + self._tv[3]


    def actions(self):
        return [ (self.make_menu, 'Tv') ]

    def make_menu(self, arg=None, menuw=None):
        entries = []
        #for s in self._tv:
        #    name = s[0]
        #    url = s[1]
        #    print url
        entries.append(TvVideoItem(self.name, self.url, self))
        menuw.pushmenu(menu.Menu(self.name, entries))



class BrowseByNations(TvItem):
    def __init__(self, parent):
        TvItem.__init__(self, parent)
        self.name = _('Browse by Nations')
        self.title = _('Nations')

    def actions(self):
        return [ (self.make_menu, 'Nations') ]

    def make_menu(self, arg=None, menuw=None):
        nations = []
        keylist = self.nation_tv.keys()
        keylist.sort()
        for key in keylist:
#            print key
#            print len(nation_tv[key])
#            print nation_tv[key]
            nations.append(Nation(key,self.nation_tv[key],self))
#        for i in nation_list:
#            nations.append(Nation(i,self))
        menuw.pushmenu(menu.Menu(_('Choose a Nation'), nations))

class BrowseByCategories(TvItem):
    def __init__(self, parent):
        TvItem.__init__(self, parent)
        self.name = _('Browse by Category')
        self.title = _('Categories')

    def actions(self):
        return [ (self.make_menu, 'Categories') ]

    def make_menu(self, arg=None, menuw=None):
        category = []
        keylist = self.categories_tv.keys()
        keylist.sort()
        for key in keylist:
            category.append(Nation(key,self.categories_tv[key],self))
        menuw.pushmenu(menu.Menu(_('Choose a Category'), category))



class BrowseBy(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.name = 'World Wide Internet TV'
        self.type = 'wwitv'

    def actions(self):
        return [ (self.make_menu, 'Browse by') ]

    def make_menu(self, arg=None, menuw=None):
        menuw.pushmenu(menu.Menu('World Wide Internet TV',
                [ BrowseByNations(self),
                 BrowseByCategories(self)]))
