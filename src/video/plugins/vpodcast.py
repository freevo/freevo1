# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Video Podcast Player Plug-in
# -----------------------------------------------------------------------
# $Id$
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

__author__ = 'Krasimir Atanasov'
__author_email__ = 'atanasov.krasimir@gmail.com'

import urllib2, os, threading, urllib, time, re, string
import config, menu, rc, plugin, util, skin
import util.feedparser
from item import Item
from audio.player import PlayerGUI
from video.videoitem import VideoItem
from menu import MenuItem
from gui import AlertBox, PopupBox, GUIObject
from event import *
import util.youtube_dl as youtube
from util.benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
from pprint import pformat, pprint

MAX_AGE = 3600 * 10

_player_ = None



class PodcastException: pass


class PluginInterface(plugin.MainMenuPlugin):

    """
    Video podcast plugin

    Add to local_conf.py
    | plugin.activate('video.vpodcast')
    | VPODCAST_LOCATIONS = [
    |     ('You Tube - Top Viewed', 'http://youtube.com/rss/global/top_viewed.rss'),
    |     ('You Tube - Norah Jones', 'http://www.referd.info/tag/norah_jones/rss.php'),
    |     ('You Tube - Top Rated', 'http://youtube.com/rss/global/top_rated.rss'),
    |     ('Metacafe - Top Videos', 'http://www.metacafe.com/tags/top_videos/rss.xml'),
    |     ('Metacafe - Music', 'http://www.metacafe.com/tags/music/rss.xml'),
    |     ('Metacafe - Today Videos ', 'http://www.metacafe.com/rss/today_videos/rss.xml'),
    |     ('Metacafe - New Videos', 'http://www.metacafe.com/rss/new_videos.rss'),
    |     ('CNN - Now in the news', 'http://rss.cnn.com/services/podcasting/nitn/rss.xml'),
    |     ('CNN - The Larry King', 'http://rss.cnn.com/services/podcasting/lkl/rss?format=xml'),
    |     ('Discovery Chanel', 'http://www.discovery.com/radio/xml/discovery_video.xml')
    | ]
    |
    | VPODCAST_DIR = '/path/to/vpodcasts'
    """
    @benchmark(benchmarking)
    def __init__(self):
        """ Initialise the Video postcast plug-in interface """
        if config.VPODCAST_DIR is None:
            self.reason = 'VPODCAST_DIR not set'
            return
        plugin.MainMenuPlugin.__init__(self)
        self.plugin_name = 'vpodcast'
        self.check_dir()


    @benchmark(benchmarking)
    def config(self):
        """ freevo plugins -i video.vpodcast returns the info """
        return [
            ('VPODCAST_LOCATIONS', None, 'List of podcast locations'),
            ('VPODCAST_DIR', os.path.join(config.FREEVO_CACHEDIR, 'vposcasts'), 'Directory for downloaded podcasts'),
            ('YOUTUBE_USERNAME', None, 'YouTube user name (optional)'),
            ('YOUTUBE_PASSWORD', None, 'YouTube password (optional)'),
            ('YOUTUBE_FORMAT', '18', 'YouTube format 18=high 17=mobile (optional)'),
            ('VPODCAST_BUFFERING_TIME', 20, 'Length of time to wait while buffering the poscast'),
            ('VPODCAST_BUFFERING_SIZE', 20*1024, 'size of downloaded file to start playing'),
        ]


    @benchmark(benchmarking)
    def items(self, parent):
        return [ VPodcastMainMenuItem(parent) ]


    @benchmark(benchmarking)
    def check_dir(self):
        """ Check that the VPODCAST_DIR directories exist, if not create them """
        if not os.path.isdir(config.VPODCAST_DIR):
            _debug_('%r does not exist, directory created' % (config.VPODCAST_DIR))
            os.makedirs(config.VPODCAST_DIR)

        for pcdir in config.VPODCAST_LOCATIONS:
            podcastdir = os.path.join(config.VPODCAST_DIR, pcdir[0].strip().replace(' ', '_').lower())
            if not os.path.isdir(podcastdir):
                os.makedirs(podcastdir)



class VPodcastMainMenuItem(MenuItem):
    """
    this is the item for the main menu and creates the list
    of commands in a submenu.
    """
    @benchmark(benchmarking)
    def __init__(self, parent):
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Video Podcast')


    @benchmark(benchmarking)
    def actions(self):
        """ return a list of actions for this item """
        return [ (self.create_podcast_menu, 'stations') ]


    @benchmark(benchmarking)
    def create_podcast_submenu(self, arg=None, menuw=None, image=None):
        """ create the sub-menu for the podcast """
        dir, url = arg
        podcastdir = dir.strip().replace(' ', '_').lower()

        popup = PopupBox(text=_('Fetching podcast...'))
        popup.show()
        try:
            p = Podcast(url)
            feed = p.feed()
            rss_title = p.rss_title()
            rss_description = p.rss_description()
            rss_imageurl = p.rss_image()
            if rss_imageurl:
                filename = rss_title.strip().replace(' ', '_').lower()
                image = os.path.join(config.VPODCAST_DIR, podcastdir, filename+'.jpg')
                self.download(rss_imageurl, image)
            else:
                image = None

            podcast_items = []
            for item in feed.entries:
                #pprint(item) #DJW
                try:
                    item_title = p.rss_item_title(item)
                    item_image = p.rss_item_image(item)
                    item_link = p.rss_item_link(item)
                    isYT = item_link.find('youtube.com')
                    isMC = item_link.find('metacafe.com')
                    name = item_title.strip().replace(' ', '_').lower()
                    file_ext = isYT >= 0 and config.YOUTUBE_FORMAT == '18' and '.mp4' \
                            or isYT >= 0 and config.YOUTUBE_FORMAT == '17' and '.3gp' \
                            or isMC >= 0 and '.flv' \
                            or '.avi'
                    filename = os.path.join(config.VPODCAST_DIR, podcastdir, name+file_ext)
                    podcast_items += [ menu.MenuItem(item_title, action=VPVideoItem(filename, item_link, self),
                        arg=None, image=image) ]
                except PodcastException:
                    pass
            if not podcast_items:
                podcast_items += [menu.MenuItem(_('No Podcast locations found'), menuw.goto_prev_page, 0)]
        finally:
            popup.destroy()

        podcast_sub_menu = menu.Menu(_('Video Podcasts'), podcast_items)
        menuw.pushmenu(podcast_sub_menu)
        menuw.refresh()
        rc.app(None)


    @benchmark(benchmarking)
    def create_podcast_menu(self, arg=None, menuw=None):
        """ Create the main menu item for the video podcasts """
        popup = PopupBox(text=_('Fetching podcast list...'))
        popup.show()
        podcast_menu_items = []

        for dir, url in config.VPODCAST_LOCATIONS:
            podcastdir = dir.strip().replace(' ', '_').lower()
            image_path = os.path.join(config.VPODCAST_DIR, podcastdir, 'cover.jpg')
            #XXX here we are only downloading the images, but this slows down the plug-in lots
            #if self.check_logo(image_path):
            #    p = Podcast()
            #    p.open_rss(url)
            #    p.rss_title()
            #    #XXX name = p.rss_title
            #    if p.rss_imageurl:
            #        try:
            #            image_url = p.rss_imageurl
            #            self.download(image_url, image_path)
            #        except Exception, why:
            #            _debug_(why, DWARNING)

            podcast_menu_items += [ menu.MenuItem(dir, action=self.create_podcast_submenu,
                arg=(dir, url), image=image_path) ]

        popup.destroy()
        podcast_main_menu = menu.Menu(_('Video Podcasts'), podcast_menu_items)
        rc.app(None)
        menuw.pushmenu(podcast_main_menu)
        menuw.refresh()


    @benchmark(benchmarking)
    def download(self, url, savefile):
        """ Download the url and save it """
        file = urllib2.urlopen(url).read()
        save = open(savefile, 'w')
        print >> save, file
        save.close()


    @benchmark(benchmarking)
    def check_logo(self, logo_file):
        """
        Check if the logo has changed
        @returns: True if the logo does not exist or is too old
        """
        return not os.path.exists(logo_file) or (time.time() - os.path.getmtime(logo_file)) > MAX_AGE



class Podcast:
    """
    This bit of code really needs fixing, it's really bad
    """
    @benchmark(benchmarking)
    def __init__(self, url):
        self.url = url
        self.encoding = 'latin-1'


    @benchmark(benchmarking)
    def feed(self):
        try:
            self.rss = util.feedparser.parse(self.url)
            self.encoding = self.rss.encoding
            return self.rss
        except Exception, why:
            _debug_('Cannot parse feed "%s": %s' % (self.url, why), DWARNING)
            return None


    @benchmark(benchmarking)
    def rss_title(self):
        if self.rss.feed.has_key('title'):
            return self.rss.feed.title.encode(self.encoding)
        return None


    @benchmark(benchmarking)
    def rss_description(self):
        if self.rss.feed.has_key('description'):
            return self.rss.feed.description.encode(self.encoding)
        return None


    @benchmark(benchmarking)
    def rss_image(self):
        if self.rss.feed.has_key('image') and self.rss.feed.image.has_key('url'):
            return self.rss.feed.image.url
        return None


    @benchmark(benchmarking)
    def rss_item_title(self, item):
        """ get the item's title """
        self.title = item.title.encode(self.encoding)
        self.title = re.sub('(/)', '_', self.title)
        return self.title


    @benchmark(benchmarking)
    def rss_item_link(self, item):
        """ get the item's link """
        self.link = item.link.encode(self.encoding)
        return self.link


    @benchmark(benchmarking)
    def rss_item_image(self, item):
        """ get the item's image """
        # Search for image
        #img_pattern = '<img src="(.*?)" align='
        img_pattern = 'img src="(.*?)"'
        try:
            self.image = re.search(img_pattern, item.description).group(1)
        except Exception, why:
            self.image = None
        return self.image



class VPVideoItem(VideoItem):
    """
    Video podcast video item
    """
    @benchmark(benchmarking)
    def __init__(self, name, url, parent):
        """ Initialise the VPVideoItem class """
        _debug_('VPVideoItem.__init__(name=%r, url=%r, parent=%r)' % (name, url, parent), 2)
        VideoItem.__init__(self, name, parent)
        self.vp_url = url


    @benchmark(benchmarking)
    def play(self, arg=None, menuw=None):
        """
        Play this Podcast
        """
        self.download_url = self.vp_url
        if not os.path.exists(self.filename):
            background = BGDownload(self.download_url, self.filename)
            background.start()
            popup = PopupBox(text=_('Buffering podcast...'))
            popup.show()
            size = 0
            for i in range(int(config.VPODCAST_BUFFERING_TIME)):
                if os.path.exists(self.filename):
                    mode, ino, dev, nlink, uid, gui, size, atime, mtime, ctime = os.stat(self.filename)
                    if size > config.VPODCAST_BUFFERING_SIZE:
                        break
                time.sleep(0.5)
            else:
                if size < 120 * 1024: # a bit arbitary, needs to be bigger than a web page
                    popup.destroy()
                    AlertBox(text=_('Cannot download %s') % self.filename).show()
                    return
            popup.destroy()

        # call the play funuction of VideoItem
        VideoItem.play(self, menuw=menuw, arg=arg)



class BGDownload(threading.Thread):
    """
    Download file in background
    """
    @benchmark(benchmarking)
    def __init__(self, url, savefile):
        threading.Thread.__init__(self)
        self.url = url
        self.savefile = savefile
        self.youtube_ie = youtube.YoutubeIE()
        self.metacafe_ie = youtube.MetacafeIE(self.youtube_ie)
        self.youtube_pl_ie = youtube.YoutubePlaylistIE(self.youtube_ie)


    @benchmark(benchmarking)
    def run(self):
        try:
            fd = youtube.FileDownloader({
                'usenetrc': False,
                'username': config.YOUTUBE_USERNAME,
                'password': config.YOUTUBE_PASSWORD,
                'quiet': True,
                'forceurl': False,
                'forcetitle': False,
                'simulate': False,
                'format': config.YOUTUBE_FORMAT,
                #'outtmpl': u'%(stitle)s-%(id)s.%(ext)s',
                'outtmpl': self.savefile,
                'ignoreerrors': False,
                'ratelimit': None,
                })
            fd.add_info_extractor(self.youtube_pl_ie)
            fd.add_info_extractor(self.metacafe_ie)
            fd.add_info_extractor(self.youtube_ie)
            retcode = fd.download([self.url])
            _debug_('youtube download "%s": %s' % (self.url, retcode), DINFO)
        except youtube.DownloadError:
            # Not sure about this code
            try:
                file = urllib2.urlopen(self.url)
                info = file.info()
                save = open(self.savefile, 'wb')
                chunkSize = 25
                totalBytes = int(info['Content-Length'])
                downloadBytes = 0
                bytesLeft = totalBytes
                while bytesLeft > 0:
                    chunk = file.read(chunkSize)
                    readBytes = len(chunk)
                    downloadBytes += readBytes
                    bytesLeft -= readBytes
                    save.write(chunk)
            except Exception, why:
                _debug_('Cannot download "%s": %s' % (self.url, why), DWARNING)
