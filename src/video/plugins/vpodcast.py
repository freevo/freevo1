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

import urllib2, os, stat, threading, urllib, time, re, string
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
            ('VPODCAST_BUFFERING_TIME', 20, 'Length of time to wait while fetching the poscast'),
            ('VPODCAST_BUFFERING_SIZE', 512*1024, 'size of fetched file before starting to play it'),
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

        for name, rss_url in config.VPODCAST_LOCATIONS:
            podcastdir = os.path.join(config.VPODCAST_DIR, _name_to_filename(name))
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
    def create_podcast_menu(self, arg=None, menuw=None):
        """ Create the main menu item for the video podcasts """
        podcast_menu_items = []

        for name, rss_url in config.VPODCAST_LOCATIONS:
            podcastdir = _name_to_filename(name)
            image_path = os.path.join(config.VPODCAST_DIR, podcastdir, 'cover.jpg')

            podcast_menu_items += [ menu.MenuItem(name, action=self.create_podcast_submenu,
                arg=(name, rss_url), image=image_path) ]

        podcast_main_menu = menu.Menu(_('Video Podcasts'), podcast_menu_items)
        rc.app(None)
        menuw.pushmenu(podcast_main_menu)
        menuw.refresh()


    @benchmark(benchmarking)
    def create_podcast_submenu(self, arg=None, menuw=None, image=None):
        """ create the sub-menu for the podcast """
        name, rss_url = arg
        podcastdir = _name_to_filename(name)

        popup = PopupBox(text=_('Fetching podcast items...'))
        popup.show()
        try:
            p = Podcast(rss_url)
            feed = p.feed()
            rss_title = p.rss_title()
            rss_stitle = _name_to_filename(rss_title)
            rss_description = p.rss_description()
            rss_imageurl = p.rss_image()
            if rss_imageurl:
                image_path = os.path.join(config.VPODCAST_DIR, podcastdir, 'cover.jpg')
                if not os.path.exists(image_path):
                    self.download(rss_imageurl, image_path)
            else:
                image_path = None

            podcast_items = []
            for item in feed.entries:
                try:
                    item_link = p.rss_item_link(item)
                    if item_link is None:
                        raise PodcastException
                    item_title = p.rss_item_title(item)
                    item_stitle = _name_to_filename(item_title)
                    item_image_url = p.rss_item_image(item)
                    if item_image_url is None:
                        item_image_url = rss_imageurl
                    item_mimetype = p.rss_item_mimetype(item)
                    item_updated = p.rss_item_updated(item)
                    isYT = item_link.find('youtube.com')
                    isMC = item_link.find('metacafe.com')
                    item_ext = isYT >= 0 and config.YOUTUBE_FORMAT == '18' and 'mp4' \
                            or isYT >= 0 and config.YOUTUBE_FORMAT == '17' and '3gp' \
                            or isMC >= 0 and 'flv' \
                            or item_mimetype == 'video/mpeg' and 'mpeg' \
                            or item_mimetype == 'video/quicktime' and 'mov' \
                            or item_mimetype == 'video/x-la-asf' and 'asf' \
                            or item_mimetype == 'video/x-ms-asf' and 'asf' \
                            or item_mimetype == 'video/x-msvideo' and 'avi' \
                            or item_mimetype == 'video/x-m4v' and 'mp4' \
                            or item_mimetype == 'application/x-shockwave-flash' and 'flv' \
                            or ''
                    if not item_ext:
                        item_ext = 'avi'
                    results = [{
                        'id':       time.strftime('%s').decode('utf-8'),
                        'url':      item_link.decode('utf-8'),
                        'uploader': u'',
                        'title':    item_title.decode('utf-8'),
                        'stitle':   item_stitle.decode('utf-8'),
                        'ext':      item_ext.decode('utf-8'),
                        }]
                    item_path = os.path.join(config.VPODCAST_DIR, podcastdir, item_stitle+'.'+item_ext)
                    if item_image_url is not None:
                        image_path = os.path.join(config.VPODCAST_DIR, podcastdir, item_stitle+'.jpg')
                        if not os.path.exists(image_path):
                            self.download(item_image_url, image_path)
                    podcast_items += [ menu.MenuItem(item_title,
                        action=VPVideoItem(item_path, self, item_link, results), arg=None, image=image_path) ]
                    if os.path.exists(item_path):
                        if item_updated > os.stat(item_path)[stat.ST_MTIME]:
                            os.remove(item_path)
                            _debug_('%r removed updated %r > %r' % (item_path, item_updated,
                                os.stat(item_path)[stat.ST_MTIME]), DINFO)
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
    def download(self, url, filename):
        """ Download the url and save it """
        if url is not None:
            data = urllib2.urlopen(url).read()
            save = open(filename, 'w')
            print >>save, data
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
    Extract information from the rss item
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
        img_pattern = 'img src="(.*?)"'
        try:
            self.image = re.search(img_pattern, item.description).group(1)
        except Exception, why:
            #try:
            #    self.image = re.search(img_pattern, item.summary).group(1)
            #except Exception, why:
            #    self.image = None
            self.image = None
        return self.image


    @benchmark(benchmarking)
    def rss_item_mimetype(self, item):
        """ get the item's mime type """
        try:
            self.type = item.enclosures[0].type.encode(self.encoding)
        except Exception, why:
            self.type = 'video/x-msvideo'
        return self.type


    @benchmark(benchmarking)
    def rss_item_updated(self, item):
        """ get the item's mime type """
        try:
            self.updated = time.mktime(item.updated_parsed)
        except Exception, why:
            self.updated = None
        return self.updated



class VPVideoItem(VideoItem):
    """
    Video podcast video item
    """
    @benchmark(benchmarking)
    def __init__(self, filename, parent, item_url, results):
        """ Initialise the VPVideoItem class """
        _debug_('VPVideoItem.__init__(filename=%r, parent=%r, item_url=%r, results=%r)' % \
            (filename, parent, item_url, results), 2)
        VideoItem.__init__(self, filename, parent)
        self.item_url = item_url
        self.results = results


    @benchmark(benchmarking)
    def play(self, arg=None, menuw=None):
        """
        Play this Podcast
        """
        download_failed = False
        self.download_url = self.item_url
        if not os.path.exists(self.filename):
            background = BGDownload(self.download_url, self.filename, self.results)
            background.start()
            popup = PopupBox(text=_('Fetching "%s" podcast...' % self.name))
            popup.show()
            try:
                size = 0
                for i in range(int(config.VPODCAST_BUFFERING_TIME)):
                    if os.path.exists(self.filename):
                        size = os.stat(self.filename)[stat.ST_SIZE]
                        if size > config.VPODCAST_BUFFERING_SIZE:
                            break
                    time.sleep(1.0)
                else:
                    if size < config.VPODCAST_BUFFERING_SIZE:
                        download_failed = True
            finally:
                popup.destroy()
            if download_failed:
                AlertBox(text=_('Fetching "%s" failed') % self.filename).show()
                return

        # call the play funuction of VideoItem
        VideoItem.play(self, menuw=menuw, arg=arg)



class OtherIE(youtube.InfoExtractor):
    """Information extractor for cnn.com."""
    _VALID_URL = r'(?:http://)?(?:\w+\.)?cnn\.com/'

    def __init__(self, downloader=None, results=None):
        youtube.InfoExtractor.__init__(self, downloader)
        self.results = results


    @staticmethod
    def suitable(url):
        """Receives a URL and returns True if suitable for this IE."""
        #return (re.match(OtherIE._VALID_URL, url) is not None)
        return True


    def _real_initialize(self):
        """Real initialization process. Already done."""
        pass


    def _real_extract(self, url):
        """Real extraction process. Return the results."""
        return self.results



class BGDownload(threading.Thread):
    """
    Download file in background
    """
    @benchmark(benchmarking)
    def __init__(self, url, filename, results):
        threading.Thread.__init__(self)
        self.url = url
        self.filename = filename
        self.youtube_ie = youtube.YoutubeIE()
        self.metacafe_ie = youtube.MetacafeIE(self.youtube_ie)
        self.youtube_pl_ie = youtube.YoutubePlaylistIE(self.youtube_ie)
        self.other_ie = OtherIE(self.youtube_ie, results)


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
                'outtmpl': self.filename,
                'ignoreerrors': False,
                'ratelimit': None,
                })
            fd.add_info_extractor(self.youtube_pl_ie)
            fd.add_info_extractor(self.metacafe_ie)
            fd.add_info_extractor(self.youtube_ie)
            fd.add_info_extractor(self.other_ie)
            retcode = fd.download([self.url])
            _debug_('youtube download "%s": %s' % (self.url, retcode), retcode and DWARNING or DINFO)
        except youtube.DownloadError, why:
            _debug_('Cannot download "%s": %s' % (self.url, why), DWARNING)


def _name_to_filename(name):
    """ Convert a name to a file system name """
    translation_table \
        = '                ' \
        + '                ' \
        + '   # %     + -. ' \
        + '0123456789:;<=>?' \
        + '@ABCDEFGHIJKLMNO' \
        + 'PQRSTUVWXYZ[\]^_' \
        + '`abcdefghijklmno' \
        + 'pqrstuvwxyz{|}~ ' \
        + '                ' \
        + '                ' \
        + '                ' \
        + '                ' \
        + 'AAAAAAACEEEEIIII' \
        + 'DNOOOOOxOUUUUYPS' \
        + 'aaaaaaaceeeeiiii' \
        + 'dnooooo/ouuuuypy'

    #newname = name.translate(translation_table).strip().replace(' ', '_').lower()
    newname = name.replace(':', '').strip().replace(' ', '_').lower()
    return re.sub('__+', '_', newname)
