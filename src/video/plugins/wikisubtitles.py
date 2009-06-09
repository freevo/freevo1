# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for download subtitles from web based on wikisubtitles project
# -----------------------------------------------------------------------
# $Id$
#
#    To activate, put the following line in local_conf.py:
#       plugin.activate('video.wikisubtitles')
#
#   This plugin search in www.wikitle.com for subtitles, if you want use
#   another url please edit self.wiki
#   please see http://www.wikisubtitles.net/blog/clones-y-codigo-fuente
#   there are another website with subtitles based on wikisubtitles
#   project.
#
#   Filename accepted:
#   - name.1x01.avi
#   - name.101.avi
#   - name.s01e01.avi
#   - not only tv shows! with films works too
#
# ToDo:
#
# -----------------------------------------------------------------------
#
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

__author__           = 'Alberto González Rodríguez'
__author_email__     = 'alberto@pesadilla.org'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '0.4'


import os,sys

import menu
import config
import plugin
import re
import time
import urllib2,urllib
import freevo.version as version
from gui.PopupBox import PopupBox
from util import htmlenties2txt

class PluginInterface(plugin.ItemPlugin):
    """
    You can search and download subtitles from web based on wikisubtitles project

    activate with:
    | plugin.activate('video.wikisubtitles')

    You can also set wikisubtitles_search on a key (e.g. 't') by setting
    | EVENTS['menu']['t'] = Event(MENU_CALL_ITEM_ACTION, arg='wikisubtitles_search_launch')
    """

    def __init__(self, license=None):
        if not config.USE_NETWORK:
            self.reason = 'USE_NETWORK not enabled'
            return
        self.season = None
        self.episode = None
        self.formats =  ('(.*)\.(\d+)x(\d+)', '(.*)\.s(\d+)e(\d+)', '(.*)\.(\d+)(\d{2})')
        self.txheaders = {
            'User-Agent': 'freevo %s (%s)' % (version, sys.platform),
            'Accept-Language': 'en-us',
        }
        self.txdata = ''
        self.wiki = 'http://www.wikitle.com'
        plugin.ItemPlugin.__init__(self)

    def wikisubtitles_download(self, arg=None, menuw=None):
        "Download subtitle .srt"
        import directory
        box = PopupBox(text=_('Downloading subtitle, please wait..'))
        box.show()
        urllib.urlretrieve(arg,self.srtdownload)
        box.destroy()
        box = PopupBox(text=_('Subtitle downloaded'))
        box.show()
        time.sleep(2)
        box.destroy()
        self.wikisubtitles_menu_back(menuw)

    def wikisubtitles_versions(self, arg=None, menuw=None):
        "Choose the correct version"
        box = PopupBox(text=_('Getting versions of subtitle...'))
        box.show()
        req = urllib2.Request(arg, self.txdata, self.txheaders)
        try:
            response = urllib2.urlopen(req)
        except:
            print 'wikisubtitles_search:', e
            box.destroy()
            box = PopupBox(text=_('Unknown error while connecting to ' + self.wiki))
            box.show()
            time.sleep(2)
            box.destroy()
            self.wikisubtitles_menu_back(menuw)
            return
        data = response.read()
        m=re.compile('<table width="90[^>]*>(.*?)</table>',re.DOTALL)
        r=m.findall(data)
        items = []
        if len(r) > 0:
            for type in r:
                m=re.compile('<td colspan="2" class="NewsTitle"><img[^<]*>([^<]*)</td>',re.DOTALL)
                s=m.search(type)
                m=re.compile('<td width="21%" class="language">([^<]*?)</td>\s*<td width="19%"><strong>\s*Completed.*?<a href="([^<]*)">',re.DOTALL)
                r=m.findall(type)
                for d in r:
                    items.append(menu.MenuItem('%s %s' % (s.group(1).replace(" \n",""),d[0].replace('\n','')),
                            self.wikisubtitles_download, self.wiki + d[1].replace('\n','')))

        box.destroy()
        if items:
            moviemenu = menu.Menu(_('Versions found'), items)
            menuw.pushmenu(moviemenu)
            return
        self.wikisubtitles_menu_back(menuw)

    def actions(self, item):
        "Only one action"
        self.item = item

        if item.type == 'video' and (not item.files or not item.files.fxd_file):
            if item.mode == 'file' or (item.mode in ('dvd', 'vcd') and \
                                       item.info.has_key('tracks') and not \
                                       item.media):
                self.disc_set = False
                return [ ( self.wikisubtitles_search , _('Search Subtitle for this file'),
                           'wikisubtitles_search_launch') ]

        return []


    def wikisubtitles_search(self, arg=None, menuw=None):
        """
        search subtitle for this item
        """

        box = PopupBox(text=_('searching Subtitle...'))
        box.show()

        items = []

        try:

            if self.disc_set:
                self.searchstring = self.item.media.label
            else:
                self.searchstring = os.path.basename(self.item.filename)
            self.srtdownload = self.item.filename
            m = re.compile('avi$', re.IGNORECASE)
            self.srtdownload = m.sub('srt',self.srtdownload)

            video = self.searchstring.replace("_",".").replace(" ",".")
            found = video.replace('_',' ').replace('.',' ').replace(' ','%20')
            for format in self.formats:
                m = re.compile(format, re.IGNORECASE)
                r = m.search(video)
                if r:
                    found = r.group(1).replace('_',' ').replace('.',' ').replace(' ','%20') + "%25" + r.group(2) + "%25"  + r.group(3)
                    break

            url = self.wiki + '/search.php?Submit=Search&search=' + found
            req = urllib2.Request(url, self.txdata, self.txheaders)
            try:
                response = urllib2.urlopen(req)
            except:
                print 'wikisubtitles_search:', e
                box.destroy()
                box = PopupBox(text=_('Unknown error while connecting to ' + self.wiki))
                box.show()
                time.sleep(2)
                box.destroy()
                return
            read = response.read()
            m=re.compile('((serie|film)/[^"]+)" >([^<]*)<')
            r=m.findall(read)
            if r:
                box.destroy()
                if len(r) == 1:
                    sub = self.wiki + "/" + r[0][0]
                    items.append(menu.MenuItem('%s' % (r[0][2]),
                            self.wikisubtitles_versions, sub))
                else:
                    for s in r:
                        sub = self.wiki + "/" + s[0]
                        items.append(menu.MenuItem('%s' % (s[2]),
                            self.wikisubtitles_versions, sub))
                if items:
                    moviemenu = menu.Menu(_('Subtitles found'), items)
                    menuw.pushmenu(moviemenu)
                    return


            else:
                box.destroy()
                box = PopupBox(text=_('No found subtitle'))
                box.show()
                time.sleep(2)
                box.destroy()
                return



        except Exception, e:
            print 'wikisubtitles_search:', e
            box.destroy()
            box = PopupBox(text=_('Unknown error while connecting to ' + self.wiki))
            box.show()
            time.sleep(2)
            box.destroy()
            return



    def wikisubtitles_menu_back(self, menuw):
        """
        check how many menus we have to go back to see the item
        """
        import directory

        # check if we have to go one menu back (called directly) or
        # two (called from the item menu)
        back = 1
        if menuw.menustack[-2].selected != self.item:
            back = 2

        # maybe we called the function directly because there was only one
        # entry and we called it with an event
        if menuw.menustack[-1].selected == self.item:
            back = 0

        # update the directory
        if directory.dirwatcher:
            directory.dirwatcher.scan()

        # go back in menustack
        for i in range(back):
            menuw.delete_menu()
