# -*- coding: iso-8859-15 -*-
# -----------------------------------------------------------------------
# youtube.py - Plugin for download and watch videos of youtube
# -----------------------------------------------------------------------
#
# Revision 0.1  -  Author Alberto González (alberto@pesadilla.org)
#                  thanks to Sylvain Fabre (cinemovies_trailers.py)
#                  and David Sotelo (universal_newlines=1)
#
#        Please install python-gdata and put youtube-dl in your PATH
#        Add "plugin.activate('video.youtube')" in local_conf.py
#        to activate it
#        In local_conf.py
#        YOUTUBE_VIDEOS = [
#                ("user1", "description1"),
#                ("user2", "description2"),
#               ...
#        ]
#        YOUTUBE_DIR = "/tmp/"
#

import os
import plugin
import gdata.service
import urllib2
import re
import traceback
import menu
import video
import config
import string, os, subprocess

from video.videoitem import VideoItem
from subprocess import Popen
from item import Item
from gui.PopupBox import PopupBox

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    try:
        import cElementTree as ElementTree
    except ImportError:
        from elementtree import ElementTree


class PluginInterface(plugin.MainMenuPlugin):
    """
    Download and watch youtube video

    Activate:
    plugin.activate('video.youtube')

    Config:

    YOUTUBE_VIDEOS = [
        ("user1", "description1"),
        ("user2", "description2"),
        ...
    ]
    YOUTUBE_DIR = "/tmp/"
    """
    def __init__(self):
        if not config.USE_NETWORK:
            self.reason = 'USE_NETWORK not enabled'
            return
        if not config.YOUTUBE_VIDEOS:
            self.reason = 'YOUTUBE_VIDEOS not defined'
            return
        if not config.YOUTUBE_DIR:
            config.YOUTUBE_DIR = "/tmp/"

        plugin.MainMenuPlugin.__init__(self)
    def items(self, parent):
        return [ YoutubeVideo(parent) ]

# Create a VideoItem for play
class YoutubeVideoItem(VideoItem):
    def __init__(self, name, url, parent):
        VideoItem.__init__(self, url, parent)
        self.name = name
        self.type = 'youtube'

# Main Class
class YoutubeVideo(Item):
    def __init__(self, parent):
        # look for a default player
        for p in plugin.getbyname(plugin.VIDEO_PLAYER, True):
            if config.VIDEO_PREFERED_PLAYER == p.name:
                self.player = p
        Item.__init__(self, parent)
        self.name = _('Youtube videos')
        self.type = 'youtube'

    # Only one action, return user list
    def actions(self):
        return [ (self.userlist, 'Video youtube') ]

    # Menu for choose user
    def userlist(self, arg=None, menuw=None):
        users = []
        for user,description in config.YOUTUBE_VIDEOS:
            users.append(menu.MenuItem(description, self.videolist, (user, description)))
        menuw.pushmenu(menu.Menu(_("Choose please"), users))

    # Menu for video
    def videolist(self, arg=None, menuw=None):
        items = video_list(self, _("Retrieving video list"), arg[0])
        menuw.pushmenu(menu.Menu(_('Videos available'), items))

    # Download video (if necessary) and watch it
    def downloadvideo(self, arg=None, menuw=None):
        filename =  config.YOUTUBE_DIR + '/' + arg[1].replace("-","_") + ".flv"
        if not os.path.exists(filename):
            box = PopupBox(text=_("Downloading video"), width=950)
            cmd = 'youtube-dl -o ' + config.YOUTUBE_DIR + '/' + arg[1].replace("-","_")
            cmd = cmd + '.flv "http://www.youtube.com/watch?v=' + arg[1] + '"'
            proceso = Popen(cmd, shell=True, bufsize=1024, stdout=subprocess.PIPE,universal_newlines=1)
            follow = proceso.stdout
            while proceso.poll() == None:
                mess = follow.readline()
                if mess:
                    if len(mess.strip()) > 0:
                        box.label.text=mess.strip()
                        box.show()
            box.destroy()

        # Create a fake VideoItem
        playvideo2 = YoutubeVideoItem(_("bla"), filename, self)
        playvideo2.player = self.player
        playvideo2.player_rating = 10
        playvideo2.menuw = menuw
        playvideo2.play()

# Get the video list for a specific user
def video_list(parent, title, user):
    items = []
    feed = "http://gdata.youtube.com/feeds/users/" + user + "/uploads?orderby=updated"

    service = gdata.service.GDataService(server="gdata.youtube.com")
    for video in service.GetFeed(feed).entry:
        date = video.published.text.split("T")
        id = video.link[1].href.split("watch?v=");
        items.append(menu.MenuItem(date[0] + " " + video.title.text, parent.downloadvideo, (video.title.text, id[1])))
    return items
