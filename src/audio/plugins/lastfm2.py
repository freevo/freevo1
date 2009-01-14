# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# LastFM radio player plug-in (http://www.last.fm/listen)
# -----------------------------------------------------------------------
# $Id$
#
# Notes: For the API 1.2
# http://code.google.com/p/thelastripper/wiki/LastFM12UnofficialDocumentation
# Todo:
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

import sys, os, time, traceback
import md5, urllib, urllib2, httplib, re
from threading import Thread

# Freevo modules
import config
import plugin
import rc
import version, revision
from event import STOP, PLAY_END
from menu import MenuItem, Menu
from gui import AlertBox, PopupBox
from audio.audioitem import AudioItem
from audio.player import PlayerGUI
from util import feedparser
if sys.hexversion >= 0x2050000:
    from xml.etree.cElementTree import XML
else:
    try:
        from cElementTree import XML
    except ImportError:
        from elementtree.ElementTree import XML
from util.benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL

# Debugging modules
if config.DEBUG_DEBUGGER:
    import pdb, pprint


class LastFMError(Exception):
    """
    An exception class for last.fm
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, why, url=None):
        Exception.__init__(self)
        if url:
            self.why = str(why) + ': ' + url
        else:
            self.why = str(why)

    def __str__(self):
        return self.why



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

    | PLAYLIST_NEXT - skip song (Key v or DOWN)
    | SUBTITLE      - send to lastfm LOVE song (Key l)
    | LANG          - send to lastfm BAN song (Key a)
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        if not config.LASTFM_USER or not config.LASTFM_PASS:
            self.reason = 'LASTFM_USER or LASTFM_PASS not set'
            return
        plugin.MainMenuPlugin.__init__(self)
        self.menuitem = None


    @benchmark(benchmarking, benchmarkcall)
    def config(self):
        """
        freevo plugins -i audio.freevo returns the info
        """
        _debug_('config()', 2)
        return [
            ('LASTFM_USER', None, 'User name for www.last.fm'),
            ('LASTFM_PASS', None, 'Password for www.last.fm'),
            ('LASTFM_LANG', 'en', 'Language of last fm metadata (cn,de,en,es,fr,it,jp,pl,ru,sv,tr)'),
            ('LASTFM_DIR', os.path.join(config.FREEVO_CACHEDIR, 'lastfm'), 'Directory to save lastfm files'),
            ('LASTFM_LOCATIONS', [], 'LastFM locations')
        ]


    @benchmark(benchmarking, benchmarkcall)
    def items(self, parent):
        _debug_('items(parent=%r)' % (parent,), 2)
        self.menuitem = LastFMMainMenuItem(parent)
        return [ self.menuitem ]


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        if self.menuitem is not None:
            self.menuitem.shutdown()



class LastFMMainMenuItem(MenuItem):
    """
    This is the item for the main menu and creates the list of commands in a
    submenu.
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, parent):
        _debug_('LastFMMainMenuItem.__init__(parent=%r)' % (parent,), 2)
        MenuItem.__init__(self, parent, arg='audio', skin_type='radio')
        self.name = _('Last FM')
        self.webservices = LastFMWebServices()


    @benchmark(benchmarking, benchmarkcall)
    def actions(self):
        """return a list of actions for this item"""
        _debug_('actions()', 2)
        return [ (self.create_stations_menu, 'stations') ]


    @benchmark(benchmarking, benchmarkcall)
    def create_stations_menu(self, arg=None, menuw=None):
        _debug_('create_stations_menu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        lfm_items = []
        self.webservices._login()
        for lfm_station in config.LASTFM_LOCATIONS:
            name, station = lfm_station
            lfm_item = LastFMItem(self, name, station, self.webservices)
            lfm_items += [ lfm_item ]
        if not lfm_items:
            lfm_items += [MenuItem(_('Invalid LastFM Session!'), menuw.goto_prev_page, 0)]
        lfm_menu = Menu(_('Last FM'), lfm_items)
        #rc.app(None)
        menuw.pushmenu(lfm_menu)
        menuw.refresh()


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        if self.webservices is not None:
            self.webservices.shutdown()



class LastFMItem(AudioItem):
    """
    This is the class that actually runs the commands. Eventually
    hope to add actions for different ways of running commands
    and for displaying stdout and stderr of last command run.
    """
    poll_interval = 4
    poll_interval = 1
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, parent, name, station, webservices):
        _debug_('LastFMItem.__init__(parent=%r, name=%r, station=%r, webservices=%r)' % \
            (parent, name, station, webservices), 1)
        AudioItem.__init__(self, station, parent, name)
        self.station_url = urllib.quote_plus(station)
        self.station_name = name
        self.webservices = webservices
        self.xspf = None
        self.feed = None
        self.player = None
        self.arg = None
        self.menuw = None


    @benchmark(benchmarking, benchmarkcall)
    def actions(self):
        """
        return a list of actions for this item
        """
        _debug_('LastFMItem.actions()', 1)
        #self.genre = self.station_name
        self.stream_name = self.station_name
        self.webservices.adjust_station(self.station_url)
        self.xspf = LastFMXSPF()
        self.feed = None
        items = [ (self.play, _('Listen to LastFM Station')) ]
        return items


    @benchmark(benchmarking, benchmarkcall)
    def eventhandler(self, event, menuw=None):
        _debug_('LastFMItem.eventhandler(event=%s, menuw=%r)' % (event, menuw), 2)
        if event == 'STOP':
            self.stop(self.arg, self.menuw)
            return True
        if event == 'PLAY_START':
            pass
        elif event == 'PLAY_END':
            if self.feed is not None and len(self.feed.entries) > 0:
                entry = self.feed.entries.pop(0)
                if entry:
                    time.sleep(3)
                    from kaa.metadata.audio import eyeD3
                    try:
                        tag = eyeD3.Tag()
                        tag.link(entry.trackpath)
                        tag.header.setVersion(eyeD3.ID3_V2_3)
                        tag.setArtist(entry.artist)
                        tag.setAlbum(entry.album)
                        tag.setTitle(entry.title)
                        #tag.setGenre(entry.genre)
                        if entry.image:
                            tag.addImage(eyeD3.ImageFrame.FRONT_COVER, entry.image)
                        tag.update()
                    except Exception, why:
                        print why
            self.play()
            return False
        elif event == 'PLAYLIST_NEXT':
            self.skip()
            return True
        elif event == 'LANG': # bAn
            self.ban()
            return True
        elif event == 'SUBTITLE': # Love
            self.love()
            return True
        return False


    @benchmark(benchmarking, benchmarkcall)
    def play(self, arg=None, menuw=None):
        """
        Play the current playing
        """
        _debug_('LastFMItem.play(arg=%r, menuw=%r)' % (arg, menuw), 1)
        self.arg = arg
        if self.menuw is None:
            self.menuw = menuw

        try:
            if self.feed is None or len(self.feed.entries) <= 1:
                for i in range(3):
                    xspf = self.webservices.request_xspf()
                    if xspf != 'No recs :(':
                        break
                    time.sleep(2)
                else:
                    raise LastFMError('No recs :(')

                self.feed = self.xspf.parse(xspf)
                if self.feed is None:
                    raise LastFMError('Cannot get XSFP')

            entry = self.feed.entries[0]
            _debug_('entry "%s / %s / %s" of %s' % (entry.artist, entry.album, entry.title, len(self.feed.entries)))
            self.stream_name = urllib.unquote_plus(self.feed.title)
            self.album = entry.album
            self.artist = entry.artist
            self.title = entry.title
            self.location_url = entry.location_url
            self.length = entry.duration
            basename = os.path.join(config.LASTFM_DIR, entry.artist, entry.album, entry.title)
            self.basename = basename.lower().replace(' ', '_').\
                replace('.', '').replace('\'', '').replace(':', '').replace(',', '')
            if not os.path.exists(os.path.dirname(self.basename)):
                _debug_('make directory %r' % (os.path.dirname(self.basename),), DINFO)
                os.makedirs(os.path.dirname(self.basename), 0777)
            # url is changed, to include file://
            self.url = os.path.join(self.basename + os.path.splitext(entry.location_url)[1])
            entry.trackpath = os.path.join(self.basename + os.path.splitext(entry.location_url)[1])
            if entry.image_url:
                self.image = os.path.join(self.basename + os.path.splitext(entry.image_url)[1])
                self.image_downloader = self.webservices.download(entry.image_url, self.image)
                # Wait three seconds for the image to be downloaded
                for i in range(30):
                    if not self.image_downloader.isrunning():
                        break
                    time.sleep(0.1)
            else:
                self.image = None
            entry.image = self.image
            track_downloader = self.webservices.download(self.location_url, entry.trackpath, self)
            # Wait for a bit of the file to be downloaded
            while track_downloader.filesize() < 1024 * 20:
                if not track_downloader.isrunning():
                    raise LastFMError('Failed to download track', entry.location_url)
                time.sleep(0.1)
            if not self.player:
                self.player = PlayerGUI(self, self.menuw)
            error = self.player.play()
            if error:
                raise LastFMError('Play error=%r' % (error,))

        except LastFMError, why:
            _debug_('play error: %s' % (why,), DWARNING)
            if self.menuw:
                AlertBox(text=str(why)).show()
            rc.post_event(STOP)
            return


    @benchmark(benchmarking, benchmarkcall)
    def stop(self, arg=None, menuw=None):
        """
        Stop the current playing
        """
        _debug_('LastFMItem.stop(arg=%r, menuw=%r)' % (arg, menuw), 1)
        if self.player:
            self.player.stop()


    @benchmark(benchmarking, benchmarkcall)
    def skip(self):
        """Skip song"""
        _debug_('skip()', 1)
        self.feed.entries.pop(0)
        self.play(self.arg, self.menuw)


    @benchmark(benchmarking, benchmarkcall)
    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 1)
        self.webservices.love()


    @benchmark(benchmarking, benchmarkcall)
    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 1)
        self.webservices.ban()



class LastFMXSPF:
    """
    Analyse the XSPF (spiff) XML Sharable Playlist File feed using ElementTree

    XSPF is documented at U{http://www.xspf.org/quickstart/}
    """
    _LASTFM_NS = 'http://www.audioscrobbler.net/dtd/xspf-lastfm'

    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        self.feed = feedparser.FeedParserDict()
        self.feed.entries = []


    @benchmark(benchmarking, benchmarkcall)
    def parse(self, xml):
        """
        Parse the XML feed
        """
        try:
            tree = XML(xml)
        except SyntaxError:
            raise LastFMError(xml)
        title = tree.find('title')
        self.feed.title = title is not None and title.text or u''
        for link_elem in tree.findall('link'):
            for k, v in link_elem.items():
                if k == 'rel' and v == 'http://www.last.fm/skipsLeft':
                    self.feed.skips_left = int(link_elem.text)
        tracklist = tree.find('trackList')
        if tracklist:
            for track_elem in tracklist.findall('track'):
                track = feedparser.FeedParserDict()
                track_map = dict((c, p) for p in track_elem.getiterator() for c in p)
                title = track_elem.find('title')
                track.title = title is not None and title.text or u''
                album = track_elem.find('album')
                track.album = album is not None and album.text or u''
                artist = track_elem.find('creator')
                track.artist = artist is not None and artist.text or u''
                location_url = track_elem.find('location')
                track.location_url = location_url is not None and location_url.text or u''
                image_url = track_elem.find('image')
                track.image_url = image_url is not None and image_url.text or u''
                duration_ms = track_elem.find('duration')
                track.duration = duration_ms is not None and int(float(duration_ms.text)/1000.0+0.5) or 0
                trackauth = track_elem.find('{%s}trackauth' % LastFMXSPF._LASTFM_NS)
                track.trackauth = trackauth is not None and trackauth.text or u''
                self.feed.entries.append(track)
        return self.feed



class LastFMWebServices:
    """
    Interface to LastFM web-services
    """
    _version = '1.1.2'
    headers = {
        'User-agent': 'Freevo-%s (r%s)' % (version.__version__, revision.__revision__)
    }

    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        _debug_('LastFMWebServices.__init__()', 2)
        self.logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'lastfm.session')
        try:
            self.cachefd = open(self.logincachefilename, 'r')
            self.session = self.cachefd.readline().strip('\n')
            self.stream_url = self.cachefd.readline().strip('\n')
            self.base_url = self.cachefd.readline().strip('\n')
            self.base_path = self.cachefd.readline().strip('\n')
            self.downloader = None
        except IOError, why:
            self._login()


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        """
        Shutdown the lasf.fm webservices
        """
        # XXX this does not always work if there are multiple instance of the
        # thread running, need to get the item to shutdown the thread
        if hasattr(self, 'downloader') and self.downloader is not None:
            self.downloader.stop()


    @benchmark(benchmarking, benchmarkcall)
    def _urlopen(self, url, lines=True):
        """
        Wrapper to see what is sent and received
        When lines is true then the reply is returned as a list of lines,
        otherwise it is returned as a block.

        @param url: Is the URL to read.
        @param data: Is the POST data.
        @param lines: return a list of lines, otherwise data block.
        @returns: reply from request
        """
        _debug_('url=%r, lines=%r' % (url, lines), 1)
        request = urllib2.Request(url, headers=LastFMWebServices.headers)
        opener = urllib2.build_opener(SmartRedirectHandler())
        try:
            if lines:
                reply = []
                f = opener.open(request)
                lines = f.readlines()
                if lines is None:
                    return []
                for line in lines:
                    reply.append(line.strip('\n'))
                _debug_('reply=%r' % (reply,), 1)
            else:
                reply = ''
                f = opener.open(request)
                reply = f.read()
                _debug_('len(reply)=%r' % (len(reply),), 1)
            return reply
        except urllib2.HTTPError, why:
            raise LastFMError(why, url)
        except Exception, why:
            _debug_('%s' % (why,), DWARNING)
            raise LastFMError(why)


    @benchmark(benchmarking, benchmarkcall)
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
                # this is a bit dangerous if a variable clashes
                exec('self.%s = "%s"' % tuple(line.split('=', 1)))
            # Save the lastfm session information
            fd = open(self.logincachefilename, 'w')
            print >>fd, self.session
            print >>fd, self.stream_url
            print >>fd, self.base_url
            print >>fd, self.base_path
            fd.close()
        except LastFMError, why:
            self.session = ''
            self.stream_url = ''
            self.base_url = ''
            self.base_path = ''
        except IOError, why:
            self.session = ''
            self.stream_url = ''
            self.base_url = ''
            self.base_path = ''


    @benchmark(benchmarking, benchmarkcall)
    def request_xspf(self):
        """Request a XSPF (XML Shareable Playlist File)"""
        _debug_('LastFMWebServices.request_xspf()', 1)
        if not self.session:
            self._login()
        request_url = 'http://%s%s/xspf.php?sk=%s&discovery=0&desktop=%s' % \
            (self.base_url, self.base_path, self.session, LastFMWebServices._version)
        return self._urlopen(request_url, lines=False)


    @benchmark(benchmarking, benchmarkcall)
    def adjust_station(self, station_url):
        """Change Last FM Station"""
        _debug_('adjust_station(station_url=%r)' % (station_url,), 2)
        pop = PopupBox(text=_('Tuning radio station, please wait...'))
        pop.show()
        try:
            if not self.session:
                self._login()
            tune_url = 'http://ws.audioscrobbler.com/radio/adjust.php?session=%s&url=%s&lang=%s&debug=0' % \
                (self.session, station_url, config.LASTFM_LANG)
            try:
                for line in self._urlopen(tune_url):
                    if re.search('response=OK', line):
                        return True
                return False
            except LastFMError, why:
                return None
            except AttributeError, why:
                return None
            except IOError, why:
                return None
        finally:
            pop.destroy()


    @benchmark(benchmarking, benchmarkcall)
    def now_playing(self):
        """
        Return Song Info and album Cover
        """
        _debug_('now_playing()', 2)
        if not self.session:
            self._login()
        info_url = 'http://ws.audioscrobbler.com/radio/np.php?session=%s&debug=0' % (self.session,)
        reply = self._urlopen(info_url)
        if not reply or reply[0] == 'streaming=false':
            return None
        return reply


    @benchmark(benchmarking, benchmarkcall)
    def download(self, url, filename, entry=None):
        """
        Download album cover or track to last.fm directory.

        Add the session as a cookie to the request

        @param url: location of item to download
        @param filename: path to downloaded file
        @param entry: metadata for the entry
        """
        _debug_('download(url=%r, filename=%r)' % (url, filename), 1)
        if not self.session:
            self._login()
        headers = {
            'Cookie': 'Session=%s' % self.session,
            'User-agent': 'Freevo-%s (r%s)' % (version.__version__, revision.__revision__)
        }
        self.downloader = LastFMDownloader(url, filename, headers, entry)
        self.downloader.start()
        return self.downloader


    @benchmark(benchmarking, benchmarkcall)
    def skip(self):
        """Skip song"""
        _debug_('skip()', 2)
        if not self.session:
            self._login
        skip_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=skip&debug=0' % \
            (self.session)
        return self._urlopen(skip_url)


    @benchmark(benchmarking, benchmarkcall)
    def love(self):
        """Send "Love" information to audioscrobbler"""
        _debug_('love()', 2)
        if not self.session:
            self._login
        love_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=love&debug=0' % \
            (self.session)
        return self._urlopen(love_url)


    @benchmark(benchmarking, benchmarkcall)
    def ban(self):
        """Send "Ban" information to audioscrobbler"""
        _debug_('ban()', 2)
        if not self.session:
            self._login
        ban_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=ban&debug=0' % \
            (self.session)
        return self._urlopen(ban_url)


    @benchmark(benchmarking, benchmarkcall)
    def test_user_pass(self):
        """
        Test User/Pass

        This way you can check, whether a user/pass is valid.

        http://ws.audioscrobbler.com/ass/pwcheck.php?
            time=[TS]&username=[USER]&auth=[AUTH1]&auth2=[AUTH2]&defaultplayer=[PLAYER]

        Variables:

        * TS: Unix timestamp of the current time.
        * USER: Username.
        * AUTH1: md5( md5(password) + Timestamp), An md5 sum of an md5 sum of the password, plus the timestamp as salt.
        * AUTH2: Second possible Password. The client uses md5( md5(toLower(password)) + Timestamp)
        * PLAYER: See Appendix
        """
        timestamp = time.strftime('%s', time.gmtime(time.time()))
        username = config.LASTFM_USER
        password = config.LASTFM_PASS
        auth = md5.new(md5.new(password).hexdigest()+timestamp).hexdigest()
        auth2 = md5.new(md5.new(password.lower()).hexdigest()+timestamp).hexdigest()
        url = 'http://ws.audioscrobbler.com//ass/pwcheck.php?' + \
            'time=%s&' % timestamp + \
            'username=%s&' % username + \
            'auth=%s&' % auth + \
            'auth2=%s&' % auth2 + \
            'defaultplayer=fvo'
        return self._urlopen(url)



class LastFMDownloader(Thread):
    """
    Download the stream to a file

    There is a bad bug im mplayer that corrupts the url passed, so we have to
    download it to a file and then play it
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, url, filename, headers=None, entry=None):
        Thread.__init__(self)
        self.url = url
        self.filename = filename
        self.headers = headers
        self.entry = entry
        self.size = 0
        self.running = True


    @benchmark(benchmarking, benchmarkcall)
    def run(self):
        """
        Execute a download operation. Stop when finished downloading or
        requested to stop.
        """
        request = urllib2.Request(self.url, headers=self.headers)
        opener = urllib2.build_opener(SmartRedirectHandler())
        try:
            f = opener.open(request)
            fd = open(self.filename, 'wb')
            while self.running:
                reply = f.read(1024 * 100)
                fd.write(reply)
                if len(reply) == 0:
                    self.running = False
                    if config.DEBUG >= 2:
                        print '%s downloaded' % self.filename
                    # debugs fail during shutdown
                    #_debug_('%s downloaded' % self.filename)
                    # XXX this may upset mplayer, stopping playback before the end of the track
                    break
                self.size += len(reply)
            else:
                print '%s download aborted' % self.filename
                #_debug_('%s download aborted' % self.filename)
                os.remove(self.filename)
            fd.close()
            f.close()
        except ValueError, why:
            _debug_('%s: %s' % (self.url, why), DWARNING)
        except urllib2.HTTPError, why:
            _debug_('%s: %s' % (self.url, why), DWARNING)


    #@benchmark(benchmarking, benchmarkcall)
    def filesize(self):
        """
        Get the downloaded file size
        """
        return self.size


    @benchmark(benchmarking, benchmarkcall)
    def stop(self):
        """
        Stop the download thead running
        """
        # this does not stop the download thread
        self.running = False


    #@benchmark(benchmarking, benchmarkcall)
    def isrunning(self):
        """
        See if the thread running
        """
        return self.running



class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        return result



if __name__ == '__main__':
    """
    To run this test harness need to have defined in local_conf.py:

        - LASTFM_USER
        - LASTFM_PASS
        - LASTFM_LANG
    """

    station = 'lastfm://globaltags/jazz'
    station_url = urllib.quote_plus(station)
    webservices = LastFMWebServices()
    print webservices.test_user_pass()
    print webservices._login()
    print webservices.adjust_station(station_url)
    print webservices.request_xspf()
    print 'sleep(10)'
    time.sleep(10)
    for i in range(3):
        xspf = self.webservices.request_xspf()
        print xspf
        if xspf != 'No recs :(':
            break
        time.sleep(2)
    else:
        print 'Failed to get second playlist'
