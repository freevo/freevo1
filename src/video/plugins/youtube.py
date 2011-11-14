# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for download and watch videos of youtube
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    You need to install:
#    youtube-dl from http://www.arrakis.es/~rggi3/youtube-dl/
#    and
#    gdata from http://code.google.com/p/gdata-python-client/
#
#    thanks to Sylvain Fabre (cinemovies_trailers.py)
#    and David Sotelo (universal_newlines=1)
#    thanks to Ryan Colp for streaming idea
#
#    To activate, put the following line in local_conf.py:
#       plugin.activate('video.youtube')
#       YOUTUBE_VIDEOS = [
#           ('user1', 'description'),
#           ('user2', 'description'),
#           ('standardfeed_1', 'description'),
#           ('standardfeed_2', 'description'),
#           ...
#       ]
#       Standard feeds as http://code.google.com/apis/youtube/reference.html#Standard_feeds
#       YOUTUBE_DIR = '/tmp/'
#       YOUTUBE_REGION_CODE as http://code.google.com/apis/youtube/reference.html#Region_specific_feeds
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
import logging
logger = logging.getLogger("freevo.video.plugins.youtube")

__author__           = 'Alberto Gonz�lez Rodr�guez'
__author_email__     = 'alberto@pesadilla.org'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '0.4'

import os
import plugin
import gdata.service
import urllib2, urllib
import re
import traceback
from item import Item
import menu
import video
import config
import string, os, subprocess, util
from stat import *

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import threading
import util.httpserver

from skin.widgets import TextEntryScreen
from video.videoitem import VideoItem
from subprocess import Popen
from item import Item
from gui.PopupBox import PopupBox
import osd

osd  = osd.get_singleton()
local_server = util.httpserver.get_local_server()

standardfeeds = [
    'top_rated', 'top_favorites', 'most_viewed', 'most_popular',
    'most_recent', 'most_discussed', 'most_linked', 'most_responded',
    'recently_featured', 'watch_on_mobile'
]

def decodeAcute(chain):
    return chain.replace('&aacute;', 'á') \
                .replace('&eacute;', 'é') \
                .replace('&iacute;', 'í') \
                .replace('&oacute;', 'ó') \
                .replace('&uacute;', 'ú') \
                .replace('&ordf;'  , 'º') \
                .replace('&ntilde;', 'ñ') \
                .replace('&iexcl;' , '¡') \
                .replace('&Aacute;', 'A') \
                .replace('&Eacute;', 'E') \
                .replace('&Iacute;', 'I') \
                .replace('&Oacute;', 'O') \
                .replace('&Uacute;', 'U') \
                .replace('&Ntilde;', 'ñ')

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    try:
        import cElementTree as ElementTree
    except ImportError:
        from elementtree import ElementTree

RE_VIDEO_ID=re.compile('.+watch\?v=([^&]+)')


class PluginInterface(plugin.MainMenuPlugin):
    """
    Download and watch youtube video

    prerequisites are:
    U(youtube-dl <http://www.arrakis.es/~rggi3/youtube-dl/>
    U(gdata <http://code.google.com/p/gdata-python-client/>

    Activate:
    | plugin.activate('video.youtube')
    |
    | YOUTUBE_VIDEOS = [
    |     ('user1', 'description1'),
    |     ('user2', 'description2'),
    |     ('standardfeed_1', 'description'),
    |     ('standardfeed_2', 'description'),
    |     # standard feeds are:
    |     ("top_rated", "Top rated"),
    |     ("top_favorites", "Top favorites"),
    |     ("most_viewed", "Most viewed"),
    |     ("most_popular", "Most popular"),
    |     ("most_recent", "Most recent"),
    |     ("most_discussed", "Most discussed"),
    |     ("most_responded", "Most responded"),
    |     ("recently_featured", "Recently featured"),
    |     ...
    | ]
    | Standard feeds see http://code.google.com/apis/youtube/2.0/reference.html#Standard_feeds
    | YOUTUBE_DIR = '/tmp/'
    | YOUTUBE_REGION_CODE see http://code.google.com/apis/youtube/2.0/reference.html#Region_specific_feeds
    """
    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        plugin.MainMenuPlugin.__init__(self)

        if not os.path.isdir(config.YOUTUBE_DIR):
            os.mkdir(config.YOUTUBE_DIR, S_IMODE(os.stat(config.FREEVO_CACHEDIR)[ST_MODE]))

        local_server.register_handler(r'/youtube/(.+)$', get_youtube_handler)

    def config(self):
        """returns the config variables used by this plugin"""
        _debug_('config()', 2)
        return [
            ('YOUTUBE_VIDEOS', [("top_rated", "Top rated"),
                                ("top_favorites", "Top favorites"),
                                ("most_viewed", "Most viewed"),
                                ("most_popular", "Most popular"),
                                ("most_recent", "Most recent"),
                                ("most_discussed", "Most discussed"),
                                ("most_responded", "Most responded"),
                                ("recently_featured", "Recently featured")],
                                'id and description to get/watch videos of youtube'),
            ('YOUTUBE_DIR', config.FREEVO_CACHEDIR + '/youtube', 'directory to save youtube files'),
            ('YOUTUBE_DL', 'youtube-dl', 'The youtube downloader'),
            ('YOUTUBE_REGION_CODE', None, 'To retrieve region-specific standard feeds'),
            ('YOUTUBE_FORMAT', None, 'The video format to use.')
        ]


    def items(self, parent):
        _debug_('items(parent=%r)' % (parent), 2)
        return [ YoutubeVideo(parent) ]



class YoutubeVideoItem(VideoItem):
    """Create a VideoItem for play"""

    def __init__(self, video, id, parent):
        VideoItem.__init__(self, local_server.get_url('/youtube/%s' % id), parent)
        self.name = unicode(video.title.text)
        if video.content.type == "text" and video.content.text:
            self.description = unicode(video.content.text)
        elif video.content.type == "html":
            text = util.htmlenties2txt(unicode(video.content.text), 'unicode')
            match = re.search('<span>([^\<]*)<', text)
            if match:
                self.description = decodeAcute(match.group(1))
            else:
                self.description = text
            match = re.search('src="([^\"]*)"', text)
            if match:
                self.image = match.group(1)
        else:
            self.description = ""
        self.description += '\n' + _('User') + ': ' + video.author[0].name.text
        date = video.published.text.split('T')
        self.description += '. ' + date[0]
        self.plot = self.description


class YoutubeVideoMenu(menu.Menu):
    def __init__(self, service, feed, parent):
        menu.Menu.__init__(self, _('Videos available'), [])
        self.service = service
        self.feed = feed
        self.parent = parent
        self.append_items(feed)
        self.__add_more_items_mi(feed)


    def __add_more_items_mi(self, gfeed):
        nfeed = self.service.GetNext(gfeed)
        if nfeed:
            mi = menu.MenuItem(_('More videos...'), self.add_more_items, nfeed)
            self.choices.append(mi)


    def add_more_items(self, arg=None, menuw=None):
        del self.choices[-1]
        i = len(self.choices)
        self.append_items(arg)
        self.__add_more_items_mi(arg)
        self.selected = self.choices[i]
        if menuw:
            menuw.init_page()
            menuw.rebuild_page()
            menuw.refresh()


    def append_items(self, gfeed):
        for video in gfeed.entry:
            id = None
            for link in (video.link[1], video.link[0]):
                m = RE_VIDEO_ID.match(link.href)
                if  m is not None:
                    id = m.group(1)

            if id is None:
                continue
            mi = YoutubeVideoItem(video, id, self.parent)
            self.choices.append(mi)



class YoutubeVideo(Item):
    """Main Class"""

    def __init__(self, parent):
        _debug_('YoutubeVideo.__init__(parent=%r)' % (parent), 2)
        # look for a default player
        for p in plugin.getbyname(plugin.VIDEO_PLAYER, True):
            if config.VIDEO_PREFERED_PLAYER == p.name:
                self.player = p
        Item.__init__(self, parent)
        self.name = _('Youtube videos')
        self.type = 'youtube'
        self.image = config.IMAGE_DIR + '/youtube.png'


    def actions(self):
        """Only one action, return user list"""
        _debug_('actions()', 2)
        return [ (self.userlist, 'Video youtube') ]


    def userlist(self, arg=None, menuw=None):
        """Menu for choose user"""
        _debug_('userlist(arg=%r, menuw=%r)' % (arg, menuw), 2)
        users = []
        for item in config.YOUTUBE_VIDEOS:
            users.append(menu.MenuItem(item[1], self.videolist, item))
        users.append(menu.MenuItem('Search video', self.search_video, 0))
        menuw.pushmenu(menu.Menu(_('Choose please'), users))


    def search_video(self, arg=None, menuw=None):
        _debug_('search_video(arg=%r, menuw=%r)' % (arg, menuw), 2)
        txt = TextEntryScreen((_('Search'), self.search_list), _('Search'))
        txt.show(menuw)


    def videolist(self, arg=None, menuw=None):
        """Menu for video"""
        _debug_('videolist(arg=%r, menuw=%r)' % (arg, menuw), 2)
        video_type = "uploaded"
        if len(arg) > 2 and arg[2]:
            video_type = arg[2]
        menuw.pushmenu(self.get_user_menu(arg[0], video_type.lower()))


    def search_list(self, menuw, text=''):
        """Get the video list for a specific search"""
        _debug_('search_list(self=%r, menuw=%r, text=%r)' % (self, menuw, text), 2)
        text=text.replace(' ', '/')
        feed = 'http://gdata.youtube.com/feeds/videos/-/' + text
        menuw.pushmenu(self.get_feed_menu(feed))


    def get_user_menu(self, user, video_type):
        if user in standardfeeds:
            feed  = 'http://gdata.youtube.com/feeds/base/standardfeeds/'
            if config.YOUTUBE_REGION_CODE and user != 'watch_on_mobile':
                feed += config.YOUTUBE_REGION_CODE + '/'
            feed += user
            if user not in ('most_recent', 'recently_featured', 'watch_on_mobile'):
                feed += '?time=today'
        else:
            feed = 'http://gdata.youtube.com/feeds/users/' + user
            if video_type == "favorites":
                feed += '/favorites'
            else:
                feed += '/uploads?orderby=updated'
        return self.get_feed_menu(feed)


    def get_feed_menu(self, feed):
        service = gdata.service.GDataService(server='gdata.youtube.com')
        gfeed = service.GetFeed(feed)
        box = PopupBox(text=_('Loading video list'))
        box.show()
        menu =  YoutubeVideoMenu(service, gfeed, self)
        box.destroy()
        return menu


#-------------------------------------------------------------------------------
# HTTP Server
#-------------------------------------------------------------------------------
def get_youtube_handler(request, ytid):
    cmd = [config.YOUTUBE_DL, '-o', '-', "http://www.youtube.com/watch?v=%s" % ytid]
    if config.YOUTUBE_FORMAT:
        cmd += ['-f', config.YOUTUBE_FORMAT]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process:
        def output(out):
            buf = 'a'
            line = ''
            while buf:
                buf = out.read(1)
                if buf =='\n' or buf == '\r':
                    _debug_('DOWNLOAD: %r' % line)
                    line = ''
                else:
                    line += buf

        thread = threading.Thread(target=output, args=(process.stderr,))
        thread.setName('youtube-dl-stderr')
        thread.start()
        request.send_response(200)
        request.send_header('Content-type', 'application/octet-stream')
        request.end_headers()
        request.request.settimeout(None)
        more_data = True
        try:
            while more_data:
                data = process.stdout.read(2048)
                if data:
                    request.wfile.write(data)
                else:
                    more_data = False
        except:
            os.kill(process.pid, 15)
    else:
        request.send_error(500, 'Failed to start youtube-dl')



