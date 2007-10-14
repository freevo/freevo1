# -*- coding: iso-8859-1 -*-
# ------------------
# lastfm.py - Last FM player
# ----------------------------------------------
########################################################################
#This file Copyright 2007, Krasimir Atanasov
# atanasov.krasimir@gmail.com
#Released under the GPL
#ver 0.1
# LastFM Client
########################################################################
#
import md5, urllib, urllib2, re, os
import config, menu, rc, plugin, util, time, socket
from event import *
from audio.player import PlayerGUI
from item import Item
from menu import MenuItem
from gui import AlertBox
from gui.GUIObject import GUIObject
import skin

_player_ = None

class PluginInterface(plugin.MainMenuPlugin):
    """
    Last FM player client

    To activate this plugin, put the following in your local_conf.py:

    plugin.activate('audio.lastfm')
    LASTFM_USER = '<last fm user name>'
    LASTFM_PASS = '<last fm password>'
    LASTFM_SESSION = ' '

    LASTFM_LOCATIONS = [
          ('Last Fm - Neighbours','lastfm://user/<lastfm user name>/neighbours'),
          ('Last FM - Jazz', 'lastfm://globaltags/jazz'),
          ('Last FM - Rock', 'lastfm://globaltags/rock'),
          ('Last FM - Oldies', 'lastfm://globaltags/oldies'),
          ('Las FM - Pop', 'lastfm://globaltags/pop'),
          ('Las FM - Norah Jones', 'lastfm://artist/norah jones')
          ]
    ------------------------------------------------------------------------
    RIGHT - skip song
    1     - send to last.fm LOVE song
    9     - send to last.fm BAN song
    """

    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
        self.plugin_name = 'lastfm'

    def items(self, parent):
        return [ LastFMMainMenuItem(parent) ]

    def config(self):
        '''
        freevo plugins -i audio.freevo returns the info
        '''
        return [
            ('LASTFM_USER', '<last fm user name', 'User name from www.last.fm'),
            ('LASTFM_PASS', '<last fm password', 'Password from www.last.fm'),
            ('LASTFM_SESSION', '', 'Last fm session')
        ]

class LastFMPlayerGUI(PlayerGUI):
    def __init__(self, item, menuw=None):

        self.tune_lastfm(item.station)
        GUIObject.__init__(self)
        if menuw:
            self.visible = True
        else:
            self.visible = False

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

    def tune_lastfm(self,station):
        #Change Last FM Station
        tune_url = 'http://ws.audioscrobbler.com/radio/adjust.php?session=' + config.LASTFM_SESSION + '&url=' + station + '&debug=0'
        f = urllib.urlopen(tune_url)
        page = f.readlines()
        for x in page:
            if re.search('response=OK',x):
                print 'Station is OK'

    def song_info(self):
        #Return Song Info and album Cover
        info_url = 'http://ws.audioscrobbler.com/radio/np.php?session=' + config.LASTFM_SESSION + '&debug=0'
        try:
            f = urllib2.urlopen(info_url)
            lines = f.read().rstrip().split("\n")
        except:
            print 'Last FM Info site not responding !'
            return
        try:
            if lines[0].split("=")[1] != 'false':
                if self.item.title != lines[8].split("=")[1] and self.item.artist != lines[6].split("=")[1]:
                    self.item.artist = lines[6].split("=")[1]
                    self.item.title = lines[8].split("=")[1]
                    self.item.album = lines[10].split("=")[1]
                    self.item.length = int(lines[15].split("=")[1])
                    self.info_time += self.item.length - 10
                    pic_url = lines[14].split("=")[1]
                    self.download_cover(pic_url)
                    return
                else:
                    self.info_time += 2
            else:
                print 'Stream Error'
                print lines[0].split("=")[1]
                return
        except:
            print 'Error parsing Info page !'

    def download_cover(self,pic_url):
        # Download album Cover to /tmp/freevo
        os.system("rm /tmp/freevo/cover*.jpg")
        self.covercount +=1
        savefile = '/tmp/freevo/cover_' + str(time.time()) + '.jpg'
        pic_file = urllib.urlopen(pic_url).read()
        save = open(savefile, 'w')
        print >> save, pic_file
        save.close()
        self.item.image = savefile

    def skip(self):
        # Skip song
        print "Skip " + self.item.title
        skip_url = 'http://ws.audioscrobbler.com/radio/control.php?session=' + config.LASTFM_SESSION +'&command=skip&debug=0'
        urllib.urlopen(skip_url).read()
        self.info_time = self.item.elapsed + 8
        self.song_info()

    def love(self):
        # Send "Love" information to audioscrobbler
        print 'Love ' + self.item.title
        love_url = 'http://ws.audioscrobbler.com/radio/control.php?session=' + config.LASTFM_SESSION +'&command=love&debug=0'
        urllib.urlopen(love_url).read()

    def ban(self):
        # Send "Ban" information to audioscrobbler
        print 'Ban'
        ban_url = 'http://ws.audioscrobbler.com/radio/control.php?session=' + config.LASTFM_SESSION +'&command=ban&debug=0'
        urllib.urlopen(ban_url).read()
        print 'Ban!'

    def refresh(self):
        """
        Give information to the skin..
        """
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


    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.play , _( 'Listen Last FM' ) ) ]
        return items


    def play(self, arg=None, menuw=None):
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
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _( 'Last FM' )
        self.login()


    def actions(self):
        """
        return a list of actions for this item
        """
        return [ ( self.create_stations_menu , 'stations' ) ]


    def create_stations_menu(self, arg=None, menuw=None):
        lfm_items = []
        if len(config.LASTFM_SESSION) > 5:
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
                lfm_item.info = {'album':'', 'artist':'', 'trackno': '', 'title': ''}
                lfm_items += [ lfm_item ]

        if (len(lfm_items) == 0):
            lfm_items += [menu.MenuItem( _( 'Invalid LastFM Session!' ),
                                             menuw.goto_prev_page, 0)]
        lfm_menu = menu.Menu( _( 'Last FM' ), lfm_items)
        rc.app(None)
        menuw.pushmenu(lfm_menu)
        menuw.refresh()

    def login(self , arg=None):
        # Read session and stream url from ws.audioscrobbler.com
        username = config.LASTFM_USER
        password_txt = config.LASTFM_PASS
        password = md5.new(config.LASTFM_PASS)
        login_url='http://ws.audioscrobbler.com/radio/handshake.php?version=1.1.1&platform=linux&username=' + config.LASTFM_USER + '&passwordmd5=' + password.hexdigest() + '&debug=0&partner='
        stream_url = ' '

        try:
            f = urllib.urlopen(login_url)
            page = f.readlines()
            for x in page:
                if re.search('session',x):
                    config.LASTFM_SESSION = x[8:40]

                if re.search('stream_url',x):
                    self.stream_url = x[11:]
                    print self.stream_url
        except:
            print "Socket Error"
