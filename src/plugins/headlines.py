# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# headlines.py - a simple plugin to listen to headlines
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
# activate:
# plugin.activate('headlines', level=45)
# HEADLINES_LOCATIONS = [ ("Advogato", "http://advogato.org/rss/articles.xml"),
#  ("Dictionary.com Word of the Day", "http://www.dictionary.com/wordoftheday/wotd.rss"),
#  ("DVD Review", "http://www.dvdreview.com/rss/newschannel.rss") ]
#
# for a full list of tested sites see Docs/plugins/headlines.txt
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
import logging
logger = logging.getLogger("freevo.plugins.headlines")


#python modules
import os, time, stat, re, copy

# rdf modules
import util.feedparser
import urllib

#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui.PopupBox import PopupBox
from item import Item
from skin.widgets import ScrollableTextScreen

# to decode html entities
from BeautifulSoup import BeautifulStoneSoup

#get the singletons so we get skin info and access the osd
skin_object = skin.get_singleton()
osd  = osd.get_singleton()

skin_object.register('headlines', ('screen', 'title', 'scrollabletext', 'plugin'))

#check every 30 minutes
MAX_HEADLINE_AGE = 1800


class PluginInterface(plugin.MainMenuPlugin):
    """
    A plugin to list headlines from an XML (RSS) feed.

    To activate, put the following lines in local_conf.py:

    | plugin.activate('headlines', level=45)
    | HEADLINES_LOCATIONS = [
    |       ('Advogato', 'http://advogato.org/rss/articles.xml'),
    |       ('DVD Review', 'http://www.dvdreview.com/rss/newschannel.rss') ]

    For a full list of tested sites, see 'Docs/plugins/headlines.txt'.
    """

    def __init__(self):
        """
        make an init func that creates the cache dir if it don't exist
        """
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        if not config.HEADLINES_LOCATIONS:
            self.reason = 'HEADLINES_LOCATIONS not defined'
            return
        plugin.MainMenuPlugin.__init__(self)

    def config(self):
        return [('HEADLINES_LOCATIONS',
                 [ ("DVD Review", "http://www.dvdreview.com/rss/newschannel.rss"),
                   ("Freshmeat", "http://freshmeat.net/backend/fm.rdf") ],
                 'where to get the news')]

    def items(self, parent):
        return [ HeadlinesMainMenuItem(parent) ]


class HeadlinesSiteItem(Item):
    """
    Item for the menu for one rss feed
    """
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.url = ''
        self.cachedir = '%s/headlines' % config.FREEVO_CACHEDIR
        if not os.path.isdir(self.cachedir):
            os.mkdir(self.cachedir,
                     stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))
        self.location_index = None


    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ (self.getheadlines, _('Show Sites Headlines')) ]
        return items


    def getsiteheadlines(self):
        headlines = []
        pfile = os.path.join(self.cachedir, 'headlines-%i' % self.location_index)
        if (os.path.isfile(pfile) == 0 or \
            (abs(time.time() - os.path.getmtime(pfile)) > MAX_HEADLINE_AGE)):
            #print 'Fresh Headlines'
            headlines = self.fetchheadlinesfromurl()
        else:
            #print 'Cache Headlines'
            headlines = util.read_pickle(pfile)
        return headlines


    def fetchheadlinesfromurl(self):
        headlines = []

        popup = PopupBox(text=_('Fetching headlines...'))
        popup.show()
        try:
            # parse the document
            doc = util.feedparser.parse(self.url)
            if doc.status < 400:
                for entry in doc['entries']:
                    try:
                        title = Unicode(entry.title)
                        link  = Unicode(entry.link)
                        if entry.has_key('content') and len(entry['content']) >= 1:
                            description = Unicode(entry['content'][0].value)
                        else:
                            description = Unicode(entry['summary_detail'].value)
                        headlines.append((title, link, description))
                    except AttributeError:
                        pass
            else:
                _debug_('Error %s, getting %r' % (doc.status, self.url))

            #write the file
            if len(headlines) > 0:
                pfile = os.path.join(self.cachedir, 'headlines-%i' % self.location_index)
                util.save_pickle(headlines, pfile)
        finally:
            popup.destroy()

        return headlines


    def show_details(self, arg=None, menuw=None):
        screen = ScrollableTextScreen('headlines', arg.description)
        screen.show(menuw)


    def getheadlines(self, arg=None, menuw=None):
        headlines = []
        rawheadlines = []
        rawheadlines = self.getsiteheadlines()
        for title, link, description in rawheadlines:
            mi = menu.MenuItem('%s' % title, self.show_details, 0)
            mi.arg = mi
            mi.link = link

            description = description.replace('\n\n', '&#xxx;').replace('\n', ' ').\
                          replace('&#xxx;', '\n')
            description = description.replace('<p>', '\n').replace('<br>', '\n')
            description = description.replace('<p>', '\n').replace('<br/>', '\n')
            description = description + '\n \n \nLink: ' + link
            description = unicode(BeautifulStoneSoup(description, convertEntities=BeautifulStoneSoup.HTML_ENTITIES))
            description = util.htmlenties2txt(description, 'unicode')

            mi.description = re.sub('<.*?>', '', description)

            headlines.append(mi)


        if (len(headlines) == 0):
            headlines += [menu.MenuItem(_('No Headlines found'), menuw.back_one_menu, 0)]

        headlines_menu = menu.Menu(_('Headlines'), headlines)
        menuw.pushmenu(headlines_menu)
        menuw.refresh()


class HeadlinesMainMenuItem(Item):
    """
    this is the item for the main menu and creates the list
    of Headlines Sites in a submenu.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='headlines')
        self.name = _('Headlines')

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ (self.create_locations_menu, _('Headlines Sites')) ]
        return items

    def create_locations_menu(self, arg=None, menuw=None):
        headlines_sites = []
        for location in config.HEADLINES_LOCATIONS:
            headlines_site_item = HeadlinesSiteItem(self)
            headlines_site_item.name = location[0]
            headlines_site_item.url = location[1]
            headlines_site_item.location_index = config.HEADLINES_LOCATIONS.index(location)
            headlines_sites += [ headlines_site_item ]
        if (len(headlines_sites) == 0):
            headlines_sites += [menu.MenuItem(_('No Headlines Sites found'),
                                              menuw.back_one_menu, 0)]
        headlines_site_menu = menu.Menu(_('Headlines Sites'), headlines_sites)
        menuw.pushmenu(headlines_site_menu)
        menuw.refresh()
