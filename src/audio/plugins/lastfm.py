# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Last FM player
# -----------------------------------------------------------------------
# $Id$

########################################################################
#This file Copyright 2007, Krasimir Atanasov
# atanasov.krasimir@gmail.com
#Released under the GPL
#ver 0.1
# LastFM Client
########################################################################

import md5, urllib, urllib2, re, os
import config, menu, rc, plugin, util, time, socket
from event import *
from audio.player import PlayerGUI
from item import Item
from menu import MenuItem
from gui import AlertBox
import skin

DEBUG = config.LASTFM_DEBUG

_player_ = None

class PluginInterface(plugin.MainMenuPlugin):
    """
    Last FM player client

    To activate this plugin, put the following in your local_conf.py:

    | plugin.activate('audio.lastfm')
    | LASTFM_USER = '<last fm user name>'
    | LASTFM_PASS = '<last fm password>'
    | LASTFM_LOCATIONS = [
    |     ('Last Fm - Neighbours', 'lastfm://user/%s/neighbours' % LASTFM_USER),
    |     ('Last FM - Jazz', 'lastfm://globaltags/jazz'),
    |     ('Last FM - Rock', 'lastfm://globaltags/rock'),
    |     ('Last FM - Oldies', 'lastfm://globaltags/oldies'),
    |     ('Last FM - Pop', 'lastfm://globaltags/pop'),
    |     ('Last FM - Norah Jones', 'lastfm://artist/norah jones')
    | ]

    Events sent to lastfm:

    | RIGHT - skip song
    | 1     - send to lastfm LOVE song
    | 9     - send to lastfm BAN song
    """
    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        if not config.LASTFM_USER or not config.LASTFM_PASS:
            self.reason = 'LASTFM_USER or LASTFM_PASS not set'
            return
        plugin.MainMenuPlugin.__init__(self)
        self.plugin_name = 'lastfm'


    def config(self):
        """
        freevo plugins -i audio.freevo returns the info
        """
        _debug_('config()', 2)
        return [
            ('LASTFM_USER', None, 'User name for www.last.fm'),
            ('LASTFM_PASS', None, 'Password for www.last.fm'),
            ('LASTFM_LOCATIONS', [], 'LastFM locations')
        ]


    def items(self, parent):
        _debug_('items(parent=%r)' % (parent,), 2)
        return [ LastFMMainMenuItem(parent) ]



class LastFMMainMenuItem(MenuItem):
    """
    this is the item for the main menu and creates the list
    of commands in a submenu.
    """
    def __init__(self, parent):
        _debug_('LastFMMainMenuItem.__init__(parent)=%r' % (parent,), 2)
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Last FM')
        self.webservices = LastFMWebServices()


    def actions(self):
        """return a list of actions for this item"""
        _debug_('actions()', 2)
        return [ (self.create_stations_menu, 'stations') ]


    def create_stations_menu(self, arg=None, menuw=None):
        _debug_('create_stations_menu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        lfm_items = []
        self.webservices._login()
        for lfm_station in config.LASTFM_LOCATIONS:
            lfm_item = LastFMItem(self.webservices)
            lfm_item.name = lfm_station[0]
            lfm_item.station_url = urllib.quote_plus(lfm_station[1])
            lfm_item.url = self.webservices.stream_url
            lfm_item.type = 'audio'
            lfm_item.mplayer_options = ''
            lfm_item.filename = ''
            lfm_item.network_play = 1
            lfm_item.station_index = config.LASTFM_LOCATIONS.index(lfm_station)
            lfm_item.trackduration = 0
            lfm_item.elapsed = 0
            lfm_item.info = {'album': '', 'artist': '', 'trackno': '', 'title': ''}
            lfm_items += [ lfm_item ]

        if len(lfm_items) == 0:
            lfm_items += [menu.MenuItem(_('Invalid LastFM Session!'), menuw.goto_prev_page, 0)]
        lfm_menu = menu.Menu(_('Last FM'), lfm_items)
        rc.app(None)
        menuw.pushmenu(lfm_menu)
        menuw.refresh()



class LastFMItem(Item):
    """
    """
    def __init__(self, webservices):
        Item.__init__(self)
        self.title = None
        self.artist = None
        self.image = None
        self.length = 0
        self.webservices = webservices


    def actions(self):
        """return a list of actions for this item"""
        _debug_('actions()', 2)
        items = [ (self.play, _('Listen Last FM')) ]
        return items


    def play(self, arg=None, menuw=None):
        _debug_('play(arg=%r, menuw=%r)' % (arg, menu), 2)
        self.elapsed = 0
        if not self.menuw:
            self.menuw = menuw

        self.player = LastFMPlayerGUI(self, self.webservices, menuw)
        error = self.player.play()

        if error and menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)



class LastFMPlayerGUI(PlayerGUI):
    """
    """
    def __init__(self, item, webservices, menuw=None):
        _debug_('LastFMPlayerGUI.__init__(item=%r, menuw=%r)' % (item, menu), 2)
        PlayerGUI.__init__(self, item, menuw)
        self.webservices = webservices
        self.webservices.tune_lastfm(item.station_url)
        self.visible = menuw is not None
        self.menuw = menuw
        self.item = item
        self.player  = None
        self.running = False
        self.info_time = 2
        self.pic_url = None
        self.track_url = None
        config.EVENTS['audio']['RIGHT'] = Event(FUNCTION_CALL, arg=self.skip)
        config.EVENTS['audio']['1'] = Event(FUNCTION_CALL, arg=self.love)
        config.EVENTS['audio']['9'] = Event(FUNCTION_CALL, arg=self.ban)


    def skip(self):
        """Skip song"""
        _debug_('skip()', 2)
        self.webservices.skip()
        self.info_time = time.time() + 8
        self.song_info()


    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 2)
        self.webservices.love()


    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 2)
        self.webservices.ban()


    def refresh(self):
        """Give information to the skin."""
        _debug_('refresh()', 2)
        if not self.visible:
            return
        if not self.running:
            return

        if time.time() > self.info_time:
            self.song_info()

        skin.draw('player', self.item)


    def song_info(self):
        """Song Information"""
        lines = self.webservices.song_info()
        try:
            for line in lines:
                exec('self.item.%s = "%s"' % tuple(line.split('=', 1)))
            # Adjust items to match freevo's
            if hasattr(self.item, 'track'):
                self.item.title = self.item.track
            if hasattr(self.item, 'tracknumber'):
                self.item.trackno = self.item.tracknumber
            if hasattr(self.item, 'trackduration'):
                self.item.length = int(self.item.trackduration)
            else:
                self.item.length = 0

            if hasattr(self.item, 'track_url'):
                if self.track_url != self.item.track_url:
                    self.track_url = self.item.track_url
                    # check song info again 12 seconds before the end of the track
                    self.info_time = time.time() + self.item.length - 12
                    self.item.image = None
                else:
                    self.info_time = time.time() + 2

            if self.item.image is None:
                pic_url = None
                if hasattr(self.item, 'albumcover_large'):
                    pic_url = self.item.albumcover_large
                elif hasattr(self.item, 'albumcover_medium'):
                    pic_url = self.item.albumcover_medium
                elif hasattr(self.item, 'albumcover_small'):
                    pic_url = self.item.albumcover_small
                if self.pic_url != pic_url:
                    self.pic_url = pic_url
                    if pic_url is not None:
                        self.item.image = self.webservices.download_cover(pic_url)
        except Exception, why:
            import traceback
            traceback.print_exc()



class LastFMWebServices:
    """
    Interface to LastFM web-services
    """
    def __init__(self):
        _debug_('LastFMWebServices.__init__()', 2)
        self.logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'lastfm.session')
        try:
            self.cachefd = open(self.logincachefilename, 'r')
            self.session = self.cachefd.readline().strip('\n')
            self.stream_url = self.cachefd.readline().strip('\n')
        except IOError, why:
            self._login()


    def _urlopen(self, url, data=None, lines=True):
        """
        Wrapper to see what is sent and received
        When lines is true then the reply is returned as a list of lines,
        otherwise it is returned as a block.

        @param url: Is the URL to read.
        @param data: Is the POST data.
        @param lines: return a list of lines, otherwise data block.
        @returns: reply from request
        """
        _debug_('url=%r, data=%r' % (url, data), 1)
        if lines:
            reply = []
            try:
                lines = urllib.urlopen(url, data).readlines()
                if lines is None:
                    return []
                for line in lines:
                    reply.append(line.strip('\n'))
            except Exception, why:
                _debug_('%s: %s' % (url, why), DWARNING)
                raise
            _debug_('reply=%r' % (reply,), 1)
            return reply
        else:
            reply = ''
            try:
                reply = urllib.urlopen(url, data).read()
            except Exception, why:
                _debug_('%s: %s' % (url, why), DWARNING)
                raise
            _debug_('reply=%r' % (reply,), 1)
            return reply


    def _login(self, arg=None):
        """Read session and stream url from ws.audioscrobbler.com"""
        _debug_('login(arg=%r)' % (arg,), 2)
        username = config.LASTFM_USER
        password_txt = config.LASTFM_PASS
        password = md5.new(config.LASTFM_PASS)
        login_url='http://ws.audioscrobbler.com/radio/handshake.php?version=1.1.1&platform=linux' + \
            '&username=%s&passwordmd5=%s&debug=0&partner=' % (config.LASTFM_USER, password.hexdigest())
        stream_url = ''

        try:
            lines = self._urlopen(login_url)
            for line in lines:
                # this is a bit dangerous if a variable clashes
                exec('self.%s = "%s"' % tuple(line.split('=', 1)))
            # Save the lastfm session information
            fd = open(self.logincachefilename, 'w')
            print >>fd, self.session
            print >>fd, self.stream_url
            fd.close()
        except IOError, why:
            self.session = ''
            self.stream_url = ''


    def tune_lastfm(self, station_url):
        """Change Last FM Station"""
        _debug_('tune_lastfm(station_url=%r)' % (station_url,), 2)
        if not self.session:
            self._login()
        tune_url = 'http://ws.audioscrobbler.com/radio/adjust.php?session=%s&url=%s&debug=0' % \
            (self.session, station_url)
        try:
            for x in self._urlopen(tune_url):
                if re.search('response=OK', x):
                    return True
            return False
        except IOError, why:
            return None


    def song_info(self):
        """
        Return Song Info and album Cover

        'price'=''
        'shopname'=''
        'clickthrulink'=''
        'streaming'='true'
        'discovery'='0'
        'station'=' oldies Tag Radio'
        'artist'='The Foundations'
        'artist_url'='http://www.last.fm/music/The+Foundations'
        'track'='Build Me Up Buttercup'
        'track_url'='http://www.last.fm/music/The+Foundations/_/Build+Me+Up+Buttercup'
        'album'='Sitting on the Dock of the Bay'
        'album_url'='http://www.last.fm/music/The+Foundations/Sitting+on+the+Dock+of+the+Bay'
        'albumcover_small'='http://cdn.last.fm/coverart/50x50/20997.jpg'
        'albumcover_medium'='http://cdn.last.fm/coverart/50x50/20997.jpg'
        'albumcover_large'='http://cdn.last.fm/coverart/50x50/20997.jpg'
        'trackduration'='172'
        'radiomode'='1'
        'recordtoprofile'=''
        """
        _debug_('song_info()', 2)
        if not self.session:
            self._login()
        info_url = 'http://ws.audioscrobbler.com/radio/np.php?session=%s&debug=0' % (self.session,)
        return self._urlopen(info_url)


    def download_cover(self, pic_url):
        """Download album Cover to freevo cache directory"""
        _debug_('download_cover(pic_url=%r)' % (pic_url,), 2)

        os.system('rm -f %s/lfmcover_*.jpg' % config.FREEVO_CACHEDIR)
        if not self.session:
            self._login()
        pic_file = self._urlopen(pic_url, lines=False)
        try:
            savefile = os.path.join(config.FREEVO_CACHEDIR, 'lfmcover_'+str(time.time())+'.jpg')
            save = open(savefile, 'w')
            try:
                print >>save, pic_file
                return savefile
            finally:
                save.close()
        except IOError:
            return None


    def skip(self):
        """Skip song"""
        _debug_('skip()', 2)
        if not self.session:
            self._login
        skip_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=skip&debug=0' % \
            (self.session)
        return self._urlopen(skip_url)


    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 2)
        if not self.session:
            self._login
        love_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=love&debug=0' % \
            (self.session)
        return self._urlopen(love_url)


    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 2)
        if not self.session:
            self._login
        ban_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=ban&debug=0' % \
            (self.session)
        return self._urlopen(ban_url)
