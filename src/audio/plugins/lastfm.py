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
from util.audioscrobbler import *
from event import *
from audio.player import PlayerGUI
from item import Item
from menu import MenuItem
from gui import AlertBox
from gui.GUIObject import GUIObject
import skin

_player_ = None

logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'audioscrobbler.session')
audioscrobbler = Audioscrobbler(config.LASTFM_USER, config.LASTFM_PASS, logincachefilename)
DEBUG = config.DEBUG

class PluginInterface(plugin.MainMenuPlugin):
    """
    Last FM player client

    To activate this plugin, put the following in your local_conf.py::

        plugin.activate('audio.lastfm')
        LASTFM_USER = '<last fm user name>'
        LASTFM_PASS = '<last fm password>'
        LASTFM_LOCATIONS = [
            ('Last Fm - Neighbours', 'lastfm://user/<lastfm user name>/neighbours'),
            ('Last FM - Jazz', 'lastfm://globaltags/jazz'),
            ('Last FM - Rock', 'lastfm://globaltags/rock'),
            ('Last FM - Oldies', 'lastfm://globaltags/oldies'),
            ('Last FM - Pop', 'lastfm://globaltags/pop'),
            ('Last FM - Norah Jones', 'lastfm://artist/norah jones')
        ]

    RIGHT - skip song
    1     - send to last.fm LOVE song
    9     - send to last.fm BAN song
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



class LastFMPlayerGUI(PlayerGUI):
    """
    """
    def __init__(self, item, menuw=None):
        _debug_('LastFMPlayerGUI.__init__(item=%r, menuw=%r)' % (item, menu), 2)
        self.tune_lastfm(item.station)
        GUIObject.__init__(self)
        self.visible = menuw is not None
        self.menuw = menuw
        self.item = item
        self.player  = None
        self.running = False
        self.info_time = 2
        self.info_uppdated = False
        self.item.title = None
        self.item.artist = None
        self.covercount = 0
        config.EVENTS['audio']['RIGHT'] = Event(FUNCTION_CALL, arg=self.skip)
        config.EVENTS['audio']['1'] = Event(FUNCTION_CALL, arg=self.love)
        config.EVENTS['audio']['9'] = Event(FUNCTION_CALL, arg=self.ban)


    def tune_lastfm(self, station):
        """Change Last FM Station"""
        _debug_('tune_lastfm(station=%r)' % (station,), 2)
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        tune_url = 'http://ws.audioscrobbler.com/radio/adjust.php?session=%s&url=%s&debug=0' % \
            (Audioscrobbler.sessionid, station)
        try:
            for x in audioscrobbler._urlopen(tune_url):
                if re.search('response=OK', x):
                    print 'Station is OK'
        except IOError, why:
            print 'tune_url=%r failed: %s' % (tune_url, why)


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
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        info_url = 'http://ws.audioscrobbler.com/radio/np.php?session=%s&debug=0' % (Audioscrobbler.sessionid,)
        lines = audioscrobbler._urlopen(info_url)
        if not lines:
            return
        try:
            for line in lines:
                k, v = line.split("=")
                print '%r=%r' % (k, v)
                if v:
                    exec('self.item.%s = %r' % (k, v))
            #self.info_time += self.item.length - 10
            # Adjust items to match freevo's
            if hasattr(self.item, 'track'):
                self.item.title = self.item.track
            if hasattr(self.item, 'tracknumber'):
                self.item.trackno = self.item.tracknumber
            pic_url = None
            if hasattr(self.item, 'albumcover_large'):
                pic_url = self.item.albumcover_large
            elif hasattr(self.item, 'albumcover_medium'):
                pic_url = self.item.albumcover_medium
            elif hasattr(self.item, 'albumcover_small'):
                pic_url = self.item.albumcover_small
            if pic_url is not None:
                self.download_cover(pic_url)
            #else:
            #    self.info_time += 2
            #else:
            #    print 'Stream Error'
            #    print lines[0].split("=")[1]
            #    return
        except Exception, why:
            import traceback
            traceback.print_exc()


    def download_cover(self, pic_url):
        """Download album Cover to freevo cache directory"""
        _debug_('download_cover(pic_url=%r)' % (pic_url,), 2)
        os.system('rm -f %s/lfmcover_*.jpg' % config.FREEVO_CACHEDIR)
        self.covercount += 1
        savefile = config.FREEVO_CACHEDIR + '/lfmcover_' + str(time.time()) + '.jpg'
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        pic_file = audioscrobbler._urlopen(pic_url, lines=False)
        save = open(savefile, 'w')
        print >>save, pic_file
        save.close()
        self.item.image = savefile


    def skip(self):
        """Skip song"""
        _debug_('skip()', 2)
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        skip_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=skip&debug=0' % \
            (Audioscrobbler.sessionid)
        audioscrobbler._urlopen(skip_url)
        self.info_time = self.item.elapsed + 8
        self.song_info()


    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 2)
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        love_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=love&debug=0' % \
            (Audioscrobbler.sessionid)
        audioscrobbler._urlopen(love_url)


    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 2)
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        ban_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=ban&debug=0' % \
            (Audioscrobbler.sessionid)
        audioscrobbler._urlopen(ban_url)


    def refresh(self):
        """Give information to the skin."""
        _debug_('refresh()', 2)
        if not self.visible:
            return

        if not self.running:
            return

        if self.info_time <= self.item.elapsed:
            self.song_info()

        # Calculate some new values
        if not self.item.length:
            self.item.remain = 0
        else:
            self.item.remain = self.item.length - self.item.elapsed

        skin.draw('player', self.item)
        return



class LastFMItem(Item):
    """
    """
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

        self.player = LastFMPlayerGUI(self, menuw)
        error = self.player.play()

        if error and menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)



class LastFMMainMenuItem(MenuItem):
    """
    this is the item for the main menu and creates the list
    of commands in a submenu.
    """
    def __init__(self, parent):
        _debug_('LastFMMainMenuItem.__init__(parent)=%r' % (parent,), 2)
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Last FM')

        self.login()


    def login(self, arg=None):
        """Read session and stream url from ws.audioscrobbler.com"""
        _debug_('login(arg=%r)' % (arg,), 2)
        username = config.LASTFM_USER
        password_txt = config.LASTFM_PASS
        password = md5.new(config.LASTFM_PASS)
        login_url='http://ws.audioscrobbler.com/radio/handshake.php?version=1.1.1&platform=linux' + \
            '&username=%s&passwordmd5=%s&debug=0&partner=' % (config.LASTFM_USER, password.hexdigest())
        stream_url = ' '
    
        page = audioscrobbler._urlopen(login_url)
        for x in page:
            if re.search('session', x):
                Audioscrobbler.sessionid = x[8:40]
    
            if re.search('stream_url', x):
                self.stream_url = x[11:]
                print self.stream_url


    def actions(self):
        """return a list of actions for this item"""
        _debug_('actions()', 2)
        return [ (self.create_stations_menu, 'stations') ]


    def create_stations_menu(self, arg=None, menuw=None):
        _debug_('create_stations_menu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        lfm_items = []
        if not Audioscrobbler.sessionid:
            audioscrobbler._login()
        for lfm_station in config.LASTFM_LOCATIONS:
            lfm_item = LastFMItem()
            lfm_item.name = lfm_station[0]
            lfm_item.station = urllib.quote_plus(lfm_station[1])
            lfm_item.url = self.stream_url
            lfm_item.type = 'audio'
            lfm_item.mplayer_options = ''
            lfm_item.filename = ''
            lfm_item.network_play = 1
            lfm_item.station_index = config.LASTFM_LOCATIONS.index(lfm_station)
            lfm_item.length = 0
            lfm_item.remain = 0
            lfm_item.elapsed = 0
            lfm_item.info = {'album': '', 'artist': '', 'trackno': '', 'title': ''}
            lfm_items += [ lfm_item ]

        if len(lfm_items) == 0:
            lfm_items += [menu.MenuItem(_('Invalid LastFM Session!'), menuw.goto_prev_page, 0)]
        lfm_menu = menu.Menu(_('Last FM'), lfm_items)
        rc.app(None)
        menuw.pushmenu(lfm_menu)
        menuw.refresh()
