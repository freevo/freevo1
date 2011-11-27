# -*- coding: iso-8859-1 -*-
# ------------------
# apodcast.py - Audio Podcast Player
# ----------------------------------------------
# $id: apodcast.py 2007-10-04 $
#  -Krasimir Atanasov-
#
import logging
logger = logging.getLogger("freevo.audio.plugins.apodcast")

import urllib2, os, threading
import config, menu, rc, plugin, util, time, os.path, re
from audio.player import PlayerGUI
from item import Item
from menu import MenuItem
from gui import AlertBox
from gui.GUIObject import GUIObject
from gui.PopupBox import PopupBox
import skin
import util.feedparser


MAX_AGE = 3600 * 10

_player_ = None



class PluginInterface(plugin.MainMenuPlugin):
    """
    Audio podcast plugin

    Add to local_conf.py
    | plugin.activate('audio.apodcast')
    | APODCAST_LOCATIONS = [
    |     ('TWIT', 'http://leo.am/podcasts/twit'),
    |     ('NPR: Science Friday', 'http://www.sciencefriday.com/audio/scifriaudio.xml'),
    |     ('NPR: Story of the Day', 'http://www.npr.org/rss/podcast.php?id=1090'),
    |     ('PodTech.net: Technology and Entertainment Video Network', 'http://www.podtech.net/?feed=rss2'),
    |     ('60 Minutes - Selected Segments', 'http://www.cbsnews.com/common/includes/podcast/podcast_60min_1.rss'),
    |     ('English as a Second Language Podcast', 'http://feeds.feedburner.com/EnglishAsASecondLanguagePodcast')
    | ]
    |
    | APODCAST_DIR = '/home/user_name/apodcast'
    """
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
        self.plugin_name = 'apodcast'
        self.check_dir()


    def items(self, parent):
        return [ ApodcastMainMenuItem(parent) ]


    def config(self):
        """
        freevo plugins -i audio.apodcast returns the info
        """
        return [
            ('APODCAST_LOCATIONS', None, 'List of podcast locations'),
            ('APODCAST_DIR', None, 'Dir for downloaded podcasts')
        ]


    def check_dir(self):
        if os.path.exists(config.APODCAST_DIR) and os.path.isdir(config.APODCAST_DIR):
            #print 'APODCAST DIR EXIST !'
            pass
        else:
            os.mkdir(config.APODCAST_DIR)

        for pcdir in config.APODCAST_LOCATIONS:
            pc_dir = os.path.join(config.APODCAST_DIR, pcdir[0])
            if os.path.exists(pc_dir) and os.path.isdir(pc_dir):
                #print 'Podcast dir ' + pc_dir + ' exist !'
                pass
            else:
                os.mkdir(pc_dir)



class PodCastPlayerGUI(PlayerGUI):
    """
    """
    def __init__(self, item, menuw=None):
        PlayerGUI.__init__(self, item, menuw)
        self.visible = menuw and True or False
        self.menuw = menuw
        self.item = item
        self.player  = None
        self.running = False
        self.item.title = None
        self.item.artist = None
        self.box = None
        self.downl_time = 30
        if not os.path.exists(self.item.filename):
            background = BGDownload(self.item.url, self.item.filename)
            background.start()
            popup = PopupBox(text=_('Buffering podcast...'))
            popup.show()
            time.sleep(10) # 10s. buffering time
            popup.destroy()



class ApodcastItem(Item):
    """
    """
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ (self.play, _('Listen Audio Podcast')) ]
        return items


    def play(self, arg=None, menuw=None):
        logger.debug('%s.play(arg=%r, menuw=%r)', self.__module__, arg, menuw)
        self.elapsed = 0
        if not self.menuw:
            self.menuw = menuw

        self.player = PodCastPlayerGUI(self, menuw) #LastFM
        error = self.player.play()

        if error and menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)


    def confirm (self, arg=None, menuw=None):
        logger.debug('confirm (self, arg=%r, menuw=%r)', arg, menuw)
        if menuw:
            menuw.menu_back()


    def stop(self, arg=None, menuw=None):
        """
        Stop the current playing
        """
        self.player.stop()




class ApodcastMainMenuItem(MenuItem):
    """
    this is the item for the main menu and creates the list
    of commands in a submenu.
    """
    def __init__(self, parent):
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Audio Podcast')


    def actions(self):
        """
        return a list of actions for this item
        """
        return [ (self.create_podcast_menu, 'stations') ]


    def create_podcast_submenu(self, arg=None, menuw=None, image=None):
        popup = PopupBox(text=_('Fetching podcasts...'))
        popup.show()
        url = arg[1]
        p = podcast()
        p.open_rss(url)
        p.rss_title()
        p.rss_count()
        image = os.path.join(config.APODCAST_DIR, arg[0], 'cover.jpg')

        podcast_items = []
        for pc_location in range(p.rss.count):
            p.rss_item(pc_location)
            podcast_item = ApodcastItem()
            podcast_item.name = p.title
            podcast_item.url = p.enclosure
            podcast_item.type = 'audio'
            podcast_item.description = p.description
            podcast_item.image = image
            podcast_item.mplayer_options = ''
            podcast_item.filename = os.path.join(config.APODCAST_DIR, arg[0], os.path.split(p.enclosure)[1])
            podcast_item.network_play = 1
            podcast_item.length = 0
            podcast_item.remain = 0
            podcast_item.elapsed = 0
            podcast_item.info = {'album':'', 'artist':'', 'trackno': '', 'title': ''}
            podcast_items += [ podcast_item ]

        popup.destroy()
        if (len(podcast_items) == 0):
            podcast_items += [ menu.MenuItem(_('No Podcast locations found'), menwu.back_one_menu, 0) ]
        podcast_sub_menu = menu.Menu(_('AUDIO PODCAST'), podcast_items)
        menuw.pushmenu(podcast_sub_menu)
        menuw.refresh()


    def create_podcast_menu(self, arg=None, menuw=None):
        popup = PopupBox(text=_('Fetching podcast...'))
        popup.show()
        podcast_menu_items = []

        for location in config.APODCAST_LOCATIONS:
            url = location[1]
            image_path = os.path.join(config.APODCAST_DIR, location[0], 'cover.jpg')
            if self.check_logo(image_path):
                p = podcast()
                p.open_rss(url)
                p.rss_title()
                name = p.rss_title
                image_url = p.rss_image
                self.download(image_url, image_path)

            if (len(config.APODCAST_DIR) == 0):
                podcast_items += [ menu.MenuItem(_('Set APODCAST_DIR in local_conf.py'), menwu.back_one_menu, 0) ]
            podcast_menu_items += [ menu.MenuItem(_(location[0]), action=self.create_podcast_submenu, arg=location,
                image=image_path) ]

        popup.destroy()
        podcast_main_menu = menu.Menu(_('AUDIO PODCAST'), podcast_menu_items)
        menuw.pushmenu(podcast_main_menu)
        menuw.refresh()


    def download(self, url, savefile):
        try:
            file = urllib2.urlopen(url).read()
            save = open(savefile, 'w')
            print >> save, file
            save.close()
        except Exception, why:
            logger.warning('Cannot read url %r: %s', url, why)


    def check_logo(self, logo_file):
        if os.path.exists(logo_file) == 0 or (abs(time.time() - os.path.getmtime(logo_file)) > MAX_AGE):
            return True
        else:
            return False




class podcast:
    """
    extract info from RSS
    """
    def __init__(self):
        pass


    def open_rss(self, url):
        self.rss = util.feedparser.parse(url)
        self.encoding = self.rss.encoding


    def rss_title(self):
        self.rss_title = self.rss.feed.title.encode(self.encoding)
        self.rss_description = self.rss.feed.description.encode(self.encoding)
        if self.rss.feed.image.url:
            self.rss_image = self.rss.feed.image.url
        else:
            self.rss_image = None


    def rss_count(self):
        self.rss.count =  len(self.rss.entries)


    def rss_item(self, item=0):
        try:
            self.title = self.rss.entries[item].title.encode(self.encoding)
            self.description = self.rss.entries[item].description.encode(self.encoding)
            self.link  = self.rss.entries[item].link.encode(self.encoding)
            self.enclosure = self.rss.entries[item].enclosures[0]['href']
        except:
            pass



class BGDownload(threading.Thread):
    """
    Download podcast file
    """
    def __init__(self, url, savefile):
        threading.Thread.__init__(self)
        self.url = url
        self.savefile = savefile


    def run(self):
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
        except:
            print 'Download Error !'
