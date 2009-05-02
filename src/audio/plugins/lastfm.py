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
from util import feedparser


"""
Last FM player

see U{http://code.google.com/p/thelastripper/wiki/LastFM12UnofficialDocumentation}
"""
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
            ('LASTFM_LANG', 'en', 'Language of last fm metadata (cn,de,en,es,fr,it,jp,pl,ru,sv,tr)'),
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
        _debug_('LastFMMainMenuItem.__init__(parent=%r)' % (parent,), 2)
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
        menuw.pushmenu(lfm_menu)
        menuw.refresh()



class LastFMItem(Item):
    """
    LastFM Item
    """
    def __init__(self, webservices):
        Item.__init__(self)
        self.title = None
        self.artist = None
        self.album = None
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
        self.start_time = time.time()
        if not self.menuw:
            self.menuw = menuw

        self.player = LastFMPlayerGUI(self, self.webservices, menuw)
        error = self.player.play()

        if error and menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)


    def eventhandler(self, event, menuw=None):
        """Event handler"""
        if event == 'PLAY_START':
            self.player.now_playing()



class LastFMPlayerGUI(PlayerGUI):
    """
    LastFM Player

    @ivar webservices: Instance of the a Audioscrobbler web-services interface
    @ivar visible: Is the player visible
    @ivar menuw: Menu window of the player
    @ivar wsitem: Instance of a LastFM item
    @ivar item: Instance of a Freevo item
    @ivar player: The player
    @ivar running: Is the player running
    @ivar info_time: Get the information from LastFM at this time
    @ivar pic_url: URL to the picture of the current song
    @ivar track_url: URL to the track of the current song
    @ivar start_time: Time the track started playing
    """
    class WSItem:
        """
        LastFM web-services item
        """
        def __init__(self):
            """
            Create an instance of LastFM web-services item
            """
            self.price = ''
            self.shopname = ''
            self.clickthrulink = ''
            self.streaming = False
            self.discovery = 0
            self.station =  ''
            self.artist = ''
            self.artist_url = ''
            self.track = ''
            self.track_url = ''
            self.album = ''
            self.album_url = ''
            self.albumcover_small = ''
            self.albumcover_medium = ''
            self.albumcover_large = ''
            self.trackduration = 0
            self.tracknumber = None
            self.radiomode = 0
            self.recordtoprofile = ''


    def __init__(self, item, webservices, menuw=None):
        """Initialize an instance of the LastFMPlayerGUI"""
        _debug_('LastFMPlayerGUI.__init__(item=%r, menuw=%r)' % (item, menu), 2)
        PlayerGUI.__init__(self, item, menuw)
        self.webservices = webservices
        self.webservices.adjust_station(item.station_url)
        self.visible = menuw is not None
        self.menuw = menuw
        self.wsitem = LastFMPlayerGUI.WSItem()
        self.item = item
        self.player  = None
        self.running = False
        self.info_index = 0  #XXX
        self.info_times = [] #XXX
        self.pic_url = None
        self.track_url = None
        self.start_time = time.time()
        #self.check_pts = ( 32, 16, 8, 4, 2, 0, -2, -4, -8, -16, -32 )
        self.check_pts = ( 32, 16, 8, 4, 0, -4, -8, -16, -32 )
        config.EVENTS['audio']['RIGHT'] = Event(FUNCTION_CALL, arg=self.skip)
        config.EVENTS['audio']['1'] = Event(FUNCTION_CALL, arg=self.love)
        config.EVENTS['audio']['9'] = Event(FUNCTION_CALL, arg=self.ban)
        config.EVENTS['audio']['SELECT'] = Event(FUNCTION_CALL, arg=self.now_playing)


    def skip(self):
        """Skip song"""
        _debug_('skip()', 2)
        self.webservices.skip()
        self.now_playing()


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

        elapsed = int(time.time() - self.start_time + 0.5)
        self.item.elapsed = '%d:%02d' % (elapsed / 60, elapsed % 60)

        if self.info_index >= len(self.info_times):
            info_time = self.start_time + (self.info_index + 1 - len(self.info_times)) * 64
        else:
            info_time = self.info_times[self.info_index]

        if time.time() > info_time:
            self.now_playing()

        skin.draw('player', self.item)


    def now_playing(self):
        """Song Information"""
        lines = self.webservices.now_playing()
        try:
            for line in lines:
                exec('self.wsitem.%s = "%s"' % tuple(line.split('=', 1)))
            # Adjust items to match freevo's
            self.item.title = self.wsitem.track
            self.item.artist = self.wsitem.artist
            self.item.album = self.wsitem.album
            self.item.trackno = self.wsitem.tracknumber
            self.item.length = int(self.wsitem.trackduration)

            if self.track_url != self.wsitem.track_url:
                if self.track_url is not None:
                    self.start_time = time.time()
                self.track_url = self.wsitem.track_url
                self.item.image = None

                # check song info at intervals, the idea way is to write a
                # mplayer plug-in that detects the squeek at the end of a
                # track, squelches it and writes to the output a message. The
                # message could then be detected and the url read.

                # the following code block is a bit complex, the idea is to
                # check at intervals if the track has changed, checking more
                # frequently near the end of the track.  Easier to explain with
                # an example, if a track is 200 seconds long then we check from
                # the start time at [72, 136, 168, 184, 192, 196, 198, 200,
                # 202, 204, 208, 216, 232] and every 64 seconds after the time.

                self.info_index = 0
                num_cpts = self.item.length / 64
                cpts = range(num_cpts-1, 0, -1)
                check_at = []
                for i in cpts:
                    check_at.append(self.item.length - (i * 64))
                for i in self.check_pts:
                    check_at.append(self.item.length - i)
                self.info_times = []
                for i in check_at:
                    self.info_times.append(self.start_time + i)
            else:
                self.info_index += 1

            if self.item.image is None:
                pic_url = None
                if self.wsitem.albumcover_large:
                    pic_url = self.wsitem.albumcover_large
                elif self.wsitem.albumcover_medium:
                    pic_url = self.wsitem.albumcover_medium
                elif self.wsitem.albumcover_small:
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
    _version = '1.1.2'

    def __init__(self):
        _debug_('LastFMWebServices.__init__()', 2)
        self.logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'lastfm.session')
        try:
            self.cachefd = open(self.logincachefilename, 'r')
            self.session = self.cachefd.readline().strip('\n')
            self.stream_url = self.cachefd.readline().strip('\n')
            self.base_url = self.cachefd.readline().strip('\n')
            self.base_path = self.cachefd.readline().strip('\n')
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
        login_url='http://ws.audioscrobbler.com/radio/handshake.php' + \
            '?version=%s&platform=linux' % (LastFMWebServices._version) + \
            '&username=%s&passwordmd5=%s' % (config.LASTFM_USER, password.hexdigest()) + \
            '&debug=0&language=%s' % (config.LASTFM_LANG)
        stream_url = ''

        try:
            lines = self._urlopen(login_url)
            for line in lines:
                print line
                # this is a bit dangerous if a variable clashes
                exec('self.%s = "%s"' % tuple(line.split('=', 1)))
            # Save the lastfm session information
            fd = open(self.logincachefilename, 'w')
            print >>fd, self.session
            print >>fd, self.stream_url
            print >>fd, self.base_url
            print >>fd, self.base_path
            fd.close()
        except IOError, why:
            self.session = ''
            self.stream_url = ''
            self.base_url = ''
            self.base_path = ''


    def adjust_station(self, station_url):
        """Change Last FM Station"""
        _debug_('adjust_station(station_url=%r)' % (station_url,), 2)
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


    def now_playing(self):
        """
        Return Song Info and album Cover
        """
        _debug_('now_playing()', 2)
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
