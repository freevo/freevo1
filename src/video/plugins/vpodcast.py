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
import logging
logger = logging.getLogger("freevo.video.plugins.vpodcast")

__author__ = 'Krasimir Atanasov'
__author_email__ = 'atanasov.krasimir@gmail.com'

import urllib2, os, stat, threading, urllib, time, re, string, sys, pprint
import config, menu, rc, plugin, util, skin
import util.feedparser
from item import Item
from audio.player import PlayerGUI
from video.videoitem import VideoItem
from menu import MenuItem
from gui import AlertBox, PopupBox, GUIObject
from event import *
import util.youtube_dl as youtube

if sys.hexversion >= 0x2050000:
    from xml.etree.cElementTree import ElementTree, Element
else:
    try:
        from cElementTree import ElementTree, Element
    except ImportError:
        from elementtree.ElementTree import ElementTree, Element

import socket
socket.setdefaulttimeout(300)

_player_ = None



class PodcastException: pass


class PluginInterface(plugin.MainMenuPlugin):

    """
    Video podcast plugin

    Add to local_conf.py
    | plugin.activate('video.vpodcast')
    | VPODCAST_LOCATIONS = [
    |     ('You Tube - Top Viewed', 'http://youtube.com/rss/global/top_viewed.rss', 'mrss'),
    |     ('You Tube - Norah Jones', 'http://www.referd.info/tag/norah_jones/rss.php', 'mrss'),
    |     ('You Tube - Top Rated', 'http://youtube.com/rss/global/top_rated.rss'),
    |     ('Metacafe - Top Videos', 'http://www.metacafe.com/tags/top_videos/rss.xml'),
    |     ('Metacafe - Music', 'http://www.metacafe.com/tags/music/rss.xml', 'mrss'),
    |     ('Metacafe - Today Videos ', 'http://www.metacafe.com/rss/today_videos/rss.xml'),
    |     ('Metacafe - New Videos', 'http://www.metacafe.com/rss/new_videos.rss'),
    |     ('CNN - Now in the news', 'http://rss.cnn.com/services/podcasting/nitn/rss.xml'),
    |     ('CNN - The Larry King', 'http://rss.cnn.com/services/podcasting/lkl/rss?format=xml'),
    |     ('Discovery Channel', 'http://www.discovery.com/radio/xml/discovery_video.xml')
    |     (u'TV Markíza - Spravodajstvo', 'http://www.markiza.sk/xml/video/feed.rss?section=spravodajstvo', 'mrss'),
    | ]
    |
    | VPODCAST_DIR = '/path/to/vpodcasts'

    VPODCAST_LOCATIONS is a list of items, (<menu name>, <feed url>, <parser>)
    <parser> is optional can be 'mrss' or None. The mrss parser may not work in all cases

    other options type: "freevo plugins -i video.vpodcast"
    """
    def __init__(self):
        """ Initialise the Video postcast plug-in interface """
        plugin.MainMenuPlugin.__init__(self)
        self.plugin_name = 'vpodcast'
        self.check_dir()


    def config(self):
        """ freevo plugins -i video.vpodcast returns the info """
        return [
            ('VPODCAST_LOCATIONS', None, 'List of podcast locations'),
            ('VPODCAST_DIR', os.path.join(config.FREEVO_CACHEDIR, 'vposcasts'), 'Directory for downloaded podcasts'),
            ('YOUTUBE_USERNAME', None, 'YouTube user name (optional)'),
            ('YOUTUBE_PASSWORD', None, 'YouTube password (optional)'),
            ('YOUTUBE_FORMAT', '18', 'YouTube format 18=high 17=mobile (optional)'),
            ('VPODCAST_BUFFERING_TIME', 20, 'Length of time to wait while fetching the poscast'),
            ('VPODCAST_BUFFERING_SIZE', 512*1024, 'Size of fetched file before starting to play it'),
        ]


    def items(self, parent):
        return [ VPodcastMainMenuItem(parent) ]


    def check_dir(self):
        """ Check that the VPODCAST_DIR directories exist, if not create them """
        if not os.path.isdir(config.VPODCAST_DIR):
            logger.debug('%r does not exist, directory created', config.VPODCAST_DIR)
            os.makedirs(config.VPODCAST_DIR)

        for location in config.VPODCAST_LOCATIONS:
            if len(location) == 3:
                name, rss_url, feed_type = location
            elif len(location) == 2:
                name, rss_url = location
                feed_type = None
            else:
                logger.warning('Invalid VPODCAST_LOCATIONS %r', location)
                continue

            podcastdir = str(os.path.join(config.VPODCAST_DIR, _name_to_filename(name)))
            if not os.path.isdir(podcastdir):
                os.makedirs(podcastdir)



class VPodcastMainMenuItem(MenuItem):
    """
    this is the item for the main menu and creates the list
    of commands in a submenu.
    """
    def __init__(self, parent):
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Video Podcast')


    def actions(self):
        """ return a list of actions for this item """
        return [ (self.create_podcast_menu, 'stations') ]


    def create_podcast_menu(self, arg=None, menuw=None):
        """ Create the main menu item for the video podcasts """
        podcast_menu_items = []

        for location in config.VPODCAST_LOCATIONS:
            if len(location) == 3:
                name, rss_url, feed_type = location
            elif len(location) == 2:
                name, rss_url = location
                feed_type = None
            else:
                continue

            podcastdir = _name_to_filename(name)
            image_path = os.path.join(config.VPODCAST_DIR, podcastdir, 'cover.jpg')

            podcast_menu_items += [ menu.MenuItem(name, action=self.create_podcast_submenu,
                arg=(name, rss_url, feed_type), image=image_path) ]

        podcast_main_menu = menu.Menu(_('Video Podcasts'), podcast_menu_items)
        menuw.pushmenu(podcast_main_menu)
        menuw.refresh()


    def create_podcast_submenu(self, arg=None, menuw=None, image=None):
        """ create the sub-menu for the podcast """
        name, rss_url, feed_type = arg
        podcastdir = _name_to_filename(name)

        popup = PopupBox(text=_('Fetching podcast items...'))
        popup.show()
        try:
            p = Podcast(rss_url, feed_type)
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
                            or item_mimetype == 'video/x-flv' and 'flv' \
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
                            logger.info('%r removed updated %r > %r', item_path, item_updated, 
os.stat(item_path)[stat.ST_MTIME])

                except PodcastException:
                    pass
            if not podcast_items:
                podcast_items += [menu.MenuItem(_('No Podcast locations found'), menuw.back_one_menu, 0)]
        finally:
            popup.destroy()

        podcast_sub_menu = menu.Menu(_('Video Podcasts'), podcast_items)
        menuw.pushmenu(podcast_sub_menu)
        menuw.refresh()


    def download(self, url, filename):
        """ Download the url and save it """
        if url is not None:
            request = urllib2.Request(url, None, youtube.std_headers)
            data = urllib2.urlopen(request)
            #print 'DJW:Content-length', data.info().get('Content-length', None)
            #print 'DJW:Content-type', data.info().get('Content-type', None)
            try:
                save = open(filename, 'w')
                print >>save, data.read()
                save.close()
            finally:
                data.close()



class Podcast:
    """
    Extract information from the rss item
    """
    def __init__(self, rss_url, feed_type):
        self.rss = None
        self.rss_url = rss_url
        self.feed_type = feed_type
        self.encoding = 'utf-8'
        self.link = None


    def feed(self):
        try:
            request = urllib2.Request(self.rss_url, None, youtube.std_headers)
            data = urllib2.urlopen(request)
            try:
                #print 'DJW:Content-length', data.info().get('Content-length', None)
                #print 'DJW:Content-type', data.info().get('Content-type', None)
                if self.feed_type is None:
                    self.rss = util.feedparser.parse(data)
                    self.encoding = self.rss.encoding
                    return self.rss
                if self.feed_type == 'mrss':
                    feed = FeedTypeMRSS()
                    self.rss = feed.parse(data)
                    self.encoding = 'utf-8'
                    return self.rss
            finally:
                data.close()
        except Exception, why:
            logger.warning('Cannot parse feed "%s": %s', self.rss_url, why)
            raise
            self.rss = None
            return self.rss


    def rss_title(self):
        if self.rss.feed.has_key('title'):
            return self.rss.feed.title.encode(self.encoding)
        return None


    def rss_description(self):
        if self.rss.feed.has_key('description'):
            return self.rss.feed.description.encode(self.encoding)
        return None


    def rss_image(self):
        if self.rss.feed.has_key('image') and self.rss.feed.image.has_key('url'):
            return self.rss.feed.image.url
        return None


    def rss_item_title(self, item):
        """ get the item's title """
        title = item.title.encode(self.encoding)
        self.title = re.sub('(/)', '_', title)
        return self.title


    def rss_item_link(self, item):
        """ get the item's link """
        if 'links' in item:
            for link in item.links:
                if link.type.startswith('video'):
                    self.link = link.href.encode(self.encoding)
                    break
        if self.link is None:
            self.link = item.link.encode(self.encoding)
        if 'links' in item:
            for link in item['links']:
                if link['type'].startswith('video'):
                    self.link = link['href']
                    break
        return self.link


    def rss_item_image(self, item):
        """ get the item's image """
        if item.has_key('image') and item.image.has_key('url'):
            return item.image.url
        img_pattern = 'img src="(.*?)"'
        try:
            self.image = re.search(img_pattern, item.description).group(1)
        except Exception, why:
            self.image = None
        return self.image


    def rss_item_mimetype(self, item):
        """ get the item's mime type """
        if item.has_key('mimetype'):
            return item.mimetype
        try:
            self.type = item.enclosures[0].type
        except Exception, why:
            self.type = 'video/x-msvideo'
        return self.type


    def rss_item_updated(self, item):
        """ get the item's updated time """
        try:
            self.updated = time.mktime(item.updated_parsed)
        except Exception, why:
            self.updated = None
        return self.updated



class FeedTypeMRSS:
    """
    Analyse the media RSS feed using ElementTree

    FeedParser is a great bit of code but does not seem to be able to handle all feeds
    This feed type extracts the media information using elementtree XML parser.

    Media RSS is documented at http://search.yahoo.com/mrss/
    """
    _MEDIA_NS = 'http://search.yahoo.com/mrss/'
    _CONTENT_NS = 'http://purl.org/rss/1.0/modules/content/'

    def __init__(self):
        self.feed = util.feedparser.FeedParserDict()
        self.entries = []


    def parse(self, feed):
        """
        Parse the feed
        """
        et = ElementTree()
        tree = et.parse(feed)
        channel = tree.find('channel')
        if channel:
            title = channel.find('title')
            self.feed.title = title is not None and title.text or u''
            description = channel.find('description')
            self.feed.description = description is not None and description.text or u''
            image = channel.find('image')
            if image:
                self.feed.image = util.feedparser.FeedParserDict()
                image_url = image.find('url')
                self.feed.image.url = image_url is not None and image_url.text or None
            for item_elem in channel.findall('item'):
                item = util.feedparser.FeedParserDict()
                item.image = util.feedparser.FeedParserDict()
                title = item_elem.find('title')
                item.title = title is not None and title.text or u''
                description = item_elem.find('description')
                item.description = description is not None and description.text or u''
                pub_date = item_elem.find('pubDate')
                item.updated = pub_date is not None and pub_date.text or None
                item.updated_parsed = None
                if pub_date is not None:
                    from time import strptime
                    try: # used by
                        item.updated_parsed = strptime(pub_date.text, '%a, %d %b %Y %H:%M: %Z')
                    except ValueError:
                        try: # used by referd
                            item.updated_parsed = strptime(pub_date.text, '%a, %d %b %Y %H:%M:%S')
                        except ValueError:
                            try: # used by metacafe
                                item.updated_parsed = strptime(pub_date.text, '%d-%b-%y')
                            except ValueError:
                                pass
                image_url = item_elem.find('image/url')
                item.image.url = image_url is not None and image_url.text or None
                content = item_elem.find('.//{%s}content' % FeedTypeMRSS._MEDIA_NS)
                if content is None:
                    content = item
                item.link = content.get('url')
                item.mimetype = content.get('type')
                title_tag = '{%s}title' % FeedTypeMRSS._MEDIA_NS
                title = item_elem.find(title_tag)
                if title is not None:
                    item.title = title.text
                description_tag = '{%s}description' % FeedTypeMRSS._MEDIA_NS
                description = item_elem.find(description_tag)
                if description is not None:
                    item.description = description.text
                player_tag = '{%s}player' % FeedTypeMRSS._MEDIA_NS
                player = item_elem.find(player_tag)
                if player is not None:
                    item.link = player.get('url')
                thumbnail_tag = '{%s}thumbnail' % FeedTypeMRSS._MEDIA_NS
                thumbnail = item_elem.find(thumbnail_tag)
                if thumbnail is not None:
                    image_url = thumbnail.get('url')
                    if image_url is not None:
                        item.image.url = image_url
                if item.link is not None:
                    self.entries.append(item)
        return self



class VPVideoItem(VideoItem):
    """
    Video podcast video item
    """
    def __init__(self, filename, parent, item_url, results):
        """ Initialise the VPVideoItem class """
        logger.log( 9, 'VPVideoItem.__init__(filename=%r, parent=%r, item_url=%r, results=%r)', filename, parent, item_url, results)

        VideoItem.__init__(self, filename, parent)
        self.item_url = item_url
        self.results = results


    def play(self, arg=None, menuw=None):
        """
        Play this Podcast
        """
        download_failed = False
        self.download_url = self.item_url
        if not os.path.exists(self.filename) or os.path.getsize(self.filename) < 1024:
            try:
                background = BGDownload(self.download_url, self.filename, self.results)
                background.start()
                popup = PopupBox(text=_('Fetching "%s"...' % self.name))
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
                    AlertBox(text=_('Fetching "%s" failed\nNo data') % self.filename).show()
                    return
            except youtube.DownloadError, why:
                AlertBox(text=_('Fetching "%(filename)s" failed:\n%(why)s') % ({
                    'filename': self.filename, 'why': why})).show()
                return

        # call the play funuction of VideoItem
        VideoItem.play(self, menuw=menuw, arg=arg)



class OtherIE(youtube.InfoExtractor):
    """
    Information extractor for other feeds, where the results are extracted from
    feedparser and passed directly it.
    """

    def __init__(self, downloader=None, results=None):
        youtube.InfoExtractor.__init__(self, downloader)
        self.results = results


    def suitable(self, url):
        """Receives a URL and returns True if suitable for this IE."""
        return self.results is not None


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
    def __init__(self, url, filename, results):
        threading.Thread.__init__(self)
        self.url = url
        self.filename = filename
        self.youtube_ie = youtube.YoutubeIE()
        self.metacafe_ie = youtube.MetacafeIE(self.youtube_ie)
        self.youtube_pl_ie = youtube.YoutubePlaylistIE(self.youtube_ie)
        self.other_ie = OtherIE(self.youtube_ie, results)


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
            logger.log(retcode and logging.WARNING or logging.INFO, 'youtube download "%s": %s', self.url, retcode)
        except youtube.DownloadError, why:
            logger.warning('Cannot download "%s": %s', self.url, why)


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

    if name is None:
        return None
    #newname = name.translate(translation_table).strip().replace(' ', '_').lower()
    newname = name.replace(':', '').strip().replace(' ', '_').lower()
    return re.sub('__+', '_', newname)


if __name__ == '__main__':
    pass
