#if 0 /*
# -----------------------------------------------------------------------
# cinemovies_trailers.py - Plugin for streaming trailers from cinemovies.fr
# -----------------------------------------------------------------------
#
# Revision 0.3  -  Author Sylvain Fabre
#
# Notes: This code is still beta
#
#        Add "plugin.activate('video.ccinemovies_trailers')" in local_conf.py
#        to activate it
#        No other config needed
#

import os

import config
import plugin
import menu
import stat
import time, datetime
import re
import urllib
import string
import util.fileops
import util.misc
import sys
import codecs
import os
import traceback
import urllib, urllib2, urlparse, commands

from util import htmlenties2txt
from util import fxdparser
from gui.PopupBox import PopupBox

from item import Item
from video.videoitem import VideoItem
from gui.ProgressBox import ProgressBox
from BeautifulSoup import BeautifulSoup, SoupStrainer

INTERNAL_VERSION = '040708_02'
CAC_URL = 'http://www.cinemovies.fr/'

class TrailerVideoItem(VideoItem):
    def __init__(self, name, url, parent):
        VideoItem.__init__(self, url, parent)
        self.name = name
        self.type = 'trailers'

class PluginInterface(plugin.MainMenuPlugin):
    """
    A freevo interface to http://www.cinemovies.fr

    plugin.activate('video.cinemovies')
    """
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)

    def items(self, parent):
        return [ MovieTrailers(parent), DVDTrailers(parent) ]

class MovieTrailers(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.name = _('Voir les bandes annonces de film')
        self.type = 'trailers'

    def actions(self):
        return [ (self.make_menu_week, 'Titres de films') ]

    def make_menu_week(self, arg=None, menuw=None):
        items = generate_common_menu(self, "Recuperation des bandes annonces", "calendrier_fr-1-")
        menuw.pushmenu(menu.Menu(_('Bandes annonces disponibles'), items))

    def play_video(self, arg=None, menuw=None):
        items = generate_common_stream_list(self, arg[1] )
        menuw.pushmenu(menu.Menu(arg[0], items))

class DVDTrailers(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.name = _('Voir les sorties DVD')
        self.type = 'trailers'

    def actions(self):
        return [ (self.make_menu_week, 'Titres DVD') ]

    def make_menu_week(self, arg=None, menuw=None):
        items = generate_common_menu(self, "Recuperation des bandes annonces DVD", "calendrier_dvd-8-")
        menuw.pushmenu(menu.Menu(_('Bandes annonces DVD disponibles'), items))

    def play_video(self, arg=None, menuw=None):
        items = generate_common_stream_list(self, arg[1] )
        menuw.pushmenu(menu.Menu(arg[0], items))

# headers for urllib2
txdata = None
txheaders = {
    'User-Agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.51',
    'Accept-Language': 'fr-fr',
}

#Generate a menu, whatever we are searching for DVD or movies
def generate_common_menu(parent, title_box, page_prefix):
    items = []

    #Start grabbing from DVD/Movies of last week
    current = datetime.date.today() - datetime.timedelta(days=7)
    for week in [0, 1, 2, 3, 4, 5, 6]:
    # Compute a new date for the week
        newdate = current + datetime.timedelta(days=(week*7))
        # Show some progress
        box = PopupBox(text=_(title_box+'\nSemaine du '+newdate.strftime("%d/%m/%Y")))
        box.show()

        filehtml = page_prefix + newdate.strftime("%Y") + \
                  newdate.strftime("%m") + newdate.strftime("%d") + ".html"
        #print "URL to fetch : %s" % filehtml
        trailers = get_movie_list_week(CAC_URL + filehtml)
        for title, idfilm in trailers:
            items.append(menu.MenuItem('%s' % (title + " (" + newdate.strftime("%d/%m/%Y") + ")"),
                                             parent.play_video, (title, idfilm) ) )
        box.destroy()

    return items

# Generate the list of streams of a specific movie
def generate_common_stream_list( object, idfilm ):
    items = []

    box = PopupBox(text=_('Recuperation des types de bande annonces disponibles'))
    box.show()

    streamlist = get_movie_sheet( idfilm )
    if streamlist:
        for title, streamurl in streamlist:
            items.append(TrailerVideoItem(title, streamurl, object))
    else:
        items.append( menu.MenuItem('Pas de bande annonce dispo', None, None) )

    box.destroy()
    return items

# Parse the 'player.php' file to get the stream URL
def get_stream_url(idfilm, idba):
    # Get the URL
    url = CAC_URL + "players/video.php?IDfilm=" + idfilm + "&IDBA=" + idba
    req = urllib2.Request(url, txdata, txheaders)
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError, error:
        exit

    # Build the soup tree
    links = SoupStrainer('script')
    soup  = BeautifulSoup( response.read(), parseOnlyThese=links )
    re_QT = re.compile('^QT_WriteOBJECT_XHTML\(\'(.*?)\',.*')
    re_RM = re.compile('.*AC_RunRealContentX\(.*, \"SRC\", \"(.*?)\"\);')
    re_WM = re.compile('.*name=\"filename\" value=\"(.*?)\".*')

    # Get the list of javascript tags to the streams
    scriptlist = soup.findAll("script")
    for script in scriptlist:
        if script.string:
            httpstr = re_QT.search(script.string)
            if httpstr:
                return httpstr.group(1)
            else:
                httpstr = re_RM.search(script.string)
                if httpstr:
                    return httpstr.group(1)
                else:
                    httpstr = re_WM.search(script.string)
                    if httpstr:
                        return  httpstr.group(1)

    return None

# Parse the 'fiche_multimedia' file to get the player URL
def get_movie_sheet(idfilm):
    # Get the URL
    url = CAC_URL + 'fiche_multimedia.php?IDfilm=' + idfilm
    req = urllib2.Request(url, txdata, txheaders)
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError, error:
        exit

    # Build the soup tree
    links = SoupStrainer('td')
    soup  = BeautifulSoup(response.read(), parseOnlyThese=links )
    re_idba = re.compile('.*IDBA=([0-9]*).*', re.I)
    re_res  = re.compile('haute r.*', re.I)
    streams = []

    # Find the kind of trailer that are listed below
    tdlist = soup.findAll("td", {"class" : ['arial8black', 'tail_disclaimer_grey8point', 'arial9black3'] } )
    title_part1 = "Bande annonce"
    title_type  = "(Type de video inconnu)"
    for td in tdlist:
        # We have found the type of BA and the type of streams
        if td['class'] == 'arial8black':
            if td.a:
                if td.a.string:
                    if re_res.search(td.a.string):
                        idba = re_idba.search(td.a['href'])
                        if idba:
                            streamurl = get_stream_url( idfilm, idba.group(1) )
                            streams += [ (title_part1 + " " + title_type, streamurl) ]
                            #print title_part1 + " " + title_type
        # We have found the type of BA, search for the type of streams
        if td['class'] == 'tail_disclaimer_grey8point':
            if td.p:
                if td.p.img:
                    if td.p.img['src'] == "images/data/ba/quicktime_ico.gif":
                        title_type = "(Quicktime)"
                    if td.p.img['src'] == "images/v2/div/player/real2.gif":
                        title_type = "(Real Media)"
                    if td.p.img['src'] == "images/data/ba/wmp_ico.gif":
                        title_type = "(Windows Media)"
        # We are searching eventually a new type of BA
        if td['class'] == 'arial9black3':
            if td.b:
                if td.b.string == "Bande annonce vf":
                    title_part1 = "Bande annonce VF"
                if td.b.string == "Bande annonce vost":
                    title_part1 = "Bande annonce VOST"
                if td.b.string == "Teaser vf":
                    title_part1 = "Teaser VF"
                if td.b.string == "Teaser vost":
                    title_part1 = "Teaser VOST"

    return streams


# Return the list of tupple movie title and URL to the stream
def get_movie_list_week(url):
    trailers = []

    req = urllib2.Request(url, txdata, txheaders)
    try:
        response = urllib2.urlopen(req)
    except urllib2.HTTPError, error:
        exit

    # Build the soup tree
    links = SoupStrainer('a')
    soup  = BeautifulSoup( response.read(), parseOnlyThese=links )
    re_id = re.compile('.*IDfilm=([0-9]*)', re.I)

    # Search all the movie title in the page
    titletag = soup.findAll("a", {"class" : "style6"} )
    for title in titletag:
        idfilm = re_id.search(title['href'])
        # If the ID is found, then check if a trailer is available
        if idfilm:
                # If some trailers are available (because the like is present, then we push it in the list
            fiche_tag = soup.find("a", {"href" : "fiche_multimedia.php?IDfilm="+idfilm.group(1)} )
            if fiche_tag:
                fiche_tag.extract()
                trailers += [ (title.next.string, idfilm.group(1)) ]

    return trailers
