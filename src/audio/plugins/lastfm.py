# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# LastFM radio player plug-in (http://www.last.fm/listen)
# -----------------------------------------------------------------------
# $Id$
#
# Notes: For the API 1.2
# http://code.google.com/p/thelastripper/wiki/LastFM12UnofficialDocumentation
# Todo: I hate to say it but this needs fixing
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

import os
import sys
import re
import time
import urllib, urllib2
import traceback
from stat import *
from threading import Thread
from collections import deque
from pprint import pprint, pformat
from xml.etree.cElementTree import XML
from hashlib import md5

# freevo modules, config is always first
import config
import version
from util import feedparser
from util.mediainfo import Info
from plugin import MainMenuPlugin
from menu import Menu, MenuItem
from audio.audioitem import AudioItem
from item import Item

GUI = True
if __name__ == '__main__':
    GUI = False
else:
    #Freevo modules
    import skin, osd, rc
    from audio.player import PlayerGUI
    from gui.AlertBox import AlertBox
    from event import *

    #get the singletons so we get skin info and access the osd
    skin = skin.get_singleton()
    osd  = osd.get_singleton()

    skin.register('lastfm', ('screen', 'title', 'info', 'plugin'))



class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        result.status = code
        return result

    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
        result.status = code
        return result



class LastFMError(Exception):
    """
    An exception class for last.fm
    """
    def __init__(self, why, url=None, code=0):
        Exception.__init__(self)
        self.why = why
        self.url = url
        self.code = code

    def __str__(self):
        return '%s' % (self.why,)
        return '%s' % (self.why,) if self.url is None else '%s: %s' % (self.why, self.url)



class LastFMXSPF:
    """
    Analyse the XSPF (spiff) XML Sharable Playlist File feed using ElementTree

    XSPF is documented at U{http://www.xspf.org/quickstart/}
    """
    _LASTFM_NS = 'http://www.audioscrobbler.net/dtd/xspf-lastfm'

    def __init__(self):
        self.feed = feedparser.FeedParserDict()
        self.feed.entries = []


    def parse(self, xml):
        """
        Parse the XML feed
        """
        #print('xml=%s' % (xml,))
        if xml == 'No recs :(':
            raise LastFMError('No records in XSPF')

        try:
            tree = XML(xml)
        except SyntaxError, why:
            traceback.print_exc()
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



class LastFMFetcher(Thread):
    """
    Download the stream to a file

    There is a bad bug im mplayer that corrupts the url passed, so we have to
    download it to a file and then play it
    """
    def __init__(self, url, filename, headers=None):
        Thread.__init__(self)
        self.url = url
        self.filename = filename
        self.headers = headers
        self.size = 0
        self.result = False
        self.reason = None


    def run(self):
        """
        Execute a download operation. Stop when finished downloading or
        requested to stop.
        """
        _debug_('%s.run(%s)' % (self.__class__, self.name))
        if not self.url:
            _debug_('%s _not_ downloaded' % (self.filename,))
            return
        request = urllib2.Request(self.url, headers=self.headers)
        opener = urllib2.build_opener(SmartRedirectHandler())
        try:
            f = opener.open(request)
            fd = open(self.filename, 'wb')
            while not self.result:
                reply = f.read(config.LASTFM_BLOCK_SIZE)
                fd.write(reply)
                if len(reply) == 0:
                    self.result = True
                    break
                self.size += len(reply)
            else:
                _debug_('%s download aborted' % (self.filename,))
                os.remove(self.filename)
            fd.close()
            f.close()
        except urllib2.HTTPError, why:
            if why.code not in (404,):
                self.reason = '%r: %s' % (self.filename, why)
            _debug_('%s: %s' % (self.url, why))
            print('%s: %s' % (self.url, why))
            print('%r: %s/%s' % (self.filename, why.code, why.message))
        except ValueError, why:
            self.reason = '%r: %s' % (self.filename, why)
            traceback.print_exc()
            _debug_('%s: %s' % (self.url, why))
        except Exception, why:
            self.reason = '%r: %s' % (self.filename, why)
            traceback.print_exc()
        _debug_('%s.run(%s) finished' % (self.__class__, self.name))


    def stop(self):
        """
        Stop the download thead running
        """
        _debug_('%s.stop()' % (self.__class__,))
        self.running = False


    def filesize(self):
        """
        Get the downloaded file size
        """
        return self.size



class LastFMWebServices:
    """
    Interface to LastFM web-services
    """
    _version = '1.1.3'
    headers = {
        'User-agent': 'Freevo-%s)' % (version.version,)
    }

    def __init__(self):
        _debug_('%s.__init__()' % (self.__class__,))
        self.logincachefilename = os.path.join(config.FREEVO_CACHEDIR, 'lastfm.session')
        try:
            self.cachefd = open(self.logincachefilename, 'r')
            self.session = self.cachefd.readline().strip('\n')
            self.stream_url = self.cachefd.readline().strip('\n')
            self.base_url = self.cachefd.readline().strip('\n')
            self.base_path = self.cachefd.readline().strip('\n')
            self.downloader = None
            self.reason = None
        except IOError, why:
            self._login()


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
        #print('url=%r, lines=%r' % (url, lines))
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
                #print('reply=%r' % (reply,))
            else:
                reply = ''
                f = opener.open(request)
                reply = f.read()
                #print('len(reply)=%r' % (len(reply),))
            return reply
        except urllib2.HTTPError, why:
            _debug_('%s: %s' % (url, why))
            raise LastFMError(why, url, why.code)
        except Exception, why:
            _debug_('%s: %s' % (url, why))
            raise LastFMError(why, url)


    def _login(self, arg=None):
        """Read session and stream url from ws.audioscrobbler.com"""
        #print('login(arg=%r)' % (arg,))
        username = config.LASTFM_USER
        password_txt = config.LASTFM_PASS
        password = md5(config.LASTFM_PASS)
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


    def request_xspf(self):
        """Request a XSPF (XML Shareable Playlist File)"""
        #print('%s.request_xspf()' % (self.__class__,))
        if not self.session:
            self._login()
        request_url = 'http://%s%s/xspf.php?sk=%s&discovery=0&desktop=%s' % \
            (self.base_url, self.base_path, self.session, LastFMWebServices._version)
        return self._urlopen(request_url, lines=False)


    def adjust_station(self, station_url):
        """Change Last FM Station"""
        _debug_('%s.adjust_station(station_url=%r)' % (self.__class__, station_url))
        if GUI:
            osd.busyicon.wait(config.OSD_BUSYICON_TIMER[0])
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
                print('LastFMError(0)=%s' % why)
                self.reason = str(why)
                return None
            except AttributeError, why:
                self.reason = str(why)
                return None
            except IOError, why:
                self.reason = str(why)
                return None
        finally:
            if GUI:
                osd.busyicon.stop()


    def now_playing(self):
        """
        Return Song Info and album Cover
        """
        #print('%s.now_playing()' % (self.__class__,))
        if not self.session:
            self._login()
        info_url = 'http://ws.audioscrobbler.com/radio/np.php?session=%s&debug=0' % (self.session,)
        reply = self._urlopen(info_url)
        if not reply or reply[0] == 'streaming=false':
            return None
        return reply


    def fetch(self, url, filename, headers, entry=None):
        """
        Download album cover or track to last.fm directory.

        Add the session as a cookie to the request

        @param url: location of item to download
        @param filename: path to downloaded file
        @param headers: http request headers
        @param entry: metadata for the entry
        """
        _debug_('%s.fetch(url=%r, filename=%r, headers=%r, entry=%r)' % (self.__class__, url, filename, headers, entry))
        if filename is None:
            self.reason = 'No file name'
            return None

        if not self.session:
            self._login()
        self.downloader = LastFMFetcher(url, filename, headers)
        self.downloader.name = os.path.basename(filename) if filename is not None else 'fetch'
        self.downloader.setDaemon(1)
        self.downloader.start()
        return self.downloader


    def skip(self):
        """Skip song"""
        _debug_('%s.skip()' % (self.__class__,))
        if not self.session:
            self._login
        skip_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=skip&debug=0' % \
            (self.session)
        return self._urlopen(skip_url)


    def love(self):
        """Send "Love" message to audioscrobbler"""
        _debug_('%s.love()' % (self.__class__,))
        if not self.session:
            self._login
        love_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=love&debug=0' % \
            (self.session)
        return self._urlopen(love_url)


    def ban(self):
        """Send "Ban" message to audioscrobbler"""
        _debug_('%s.ban()' % (self.__class__,))
        if not self.session:
            self._login
        ban_url = 'http://ws.audioscrobbler.com/radio/control.php?session=%s&command=ban&debug=0' % \
            (self.session)
        return self._urlopen(ban_url)


    def test_user_pass(self):
        """
        Validate a User name and Password combination::

            http://ws.audioscrobbler.com/ass/pwcheck.php?time=[TS]&username=[USER]&auth=[AUTH1]&auth2=[AUTH2]&defaultplayer=[PLAYER]}

        Variables:
            - TS: Unix time-stamp of the current time.
            - USER: Username.
            - AUTH1: md5(md5(password) + Timestamp), An md5 sum of an md5 sum
              of the password, plus the timestamp as salt.
            - AUTH2: Second possible Password. The client uses md5(
              md5(toLower(password)) + Timestamp)
            - PLAYER: See Appendix
        """
        timestamp = time.strftime('%s', time.gmtime(time.time()))
        username = config.LASTFM_USER
        password = config.LASTFM_PASS
        auth = md5(md5(password).hexdigest()+timestamp).hexdigest()
        auth2 = md5(md5(password.lower()).hexdigest()+timestamp).hexdigest()
        url = 'http://ws.audioscrobbler.com//ass/pwcheck.php?' + \
            'time=%s&' % timestamp + \
            'username=%s&' % username + \
            'auth=%s&' % auth + \
            'auth2=%s&' % auth2 + \
            'defaultplayer=fvo'
        return self._urlopen(url)



class LastFMAudioItem(AudioItem):
    """
    This is the class that actually runs the commands. Eventually
    hope to add actions for different ways of running commands
    and for displaying stdout and stderr of last command run.
    """
    def __init__(self, parent, entry, track, image):
        _debug_('%s.__init__(parent=%r, entry=%s, track=%r, image=%r)' % (self.__class__, parent, entry, track, image))
        AudioItem.__init__(self, track, parent, entry.title, scan=False)
        metadata = {
            'artist': entry.artist,
            'album': entry.album,
            'length': entry.duration,
            'title': entry.title,
        }
        self.info = Info(track, discinfo=None, metadata=metadata)
        self.title = entry.title
        self.artist = entry.artist
        self.album = entry.album
        self.length = entry.duration
        self.image = image
        self.menuw = None
        #print('%s.__dict__=%s' % (self.__class__, pformat(self.__dict__)))
        #print('%s.info.__dict__=%s' % (self.__class__, pformat(self.info.__dict__)))


    def __str__(self):
        return '<%r %r: %s>' % (self.title, self.url, self.__class__)


    def __repr__(self):
        return '<%r: %s>' % (self.title, self.__class__)


    def eventhandler(self, event, menuw=None):
        """
        Event handler for play events and commands
        """
        _debug_('%s.eventhandler(event=%s, menuw=%r)' % (self.__class__, event, menuw))
        if event == PLAY_END:
            self.add_metadata()
            self.parent.playnext(menuw=self.menuw)
        elif event == STOP:
            self.stop(menuw=self.menuw)


    def play(self, arg=None, menuw=None):
        _debug_('%s.play(arg=%r, menuw=%r)' % (self.__class__, arg, menuw))
        self.elapsed = 0

        if not self.menuw:
            self.menuw = menuw

        self.player = PlayerGUI(self, self.menuw)
        error = self.player.play()

        if error and self.menuw:
            AlertBox(text=error).show()
            rc.post_event(rc.PLAY_END)


    def stop(self, arg=None, menuw=None):
        """
        Stop the current playing
        """
        _debug_('%s.stop(arg=%r, menuw=%r)' % (self.__class__, arg, menuw))
        self.player.stop()
        self.parent.stop()


    def add_metadata(self):
        """
        Add metadata to the current item
        """
        _debug_('%s.add_metadata()' % (self.__class__,))
        #print('%s.__dict__=%s' % (self.__class__, pformat(self.__dict__)))
        if self.filename and os.path.exists(self.filename):
            from kaa.metadata.audio import eyeD3
            try:
                _debug_('artist=%r album=%r title=%r' % (self.artist, self.album, self.title))
                tag = eyeD3.Tag()
                tag.link(self.filename)
                tag.header.setVersion(eyeD3.ID3_V2_4)
                tag.setTextEncoding(eyeD3.UTF_8_ENCODING)
                tag.setArtist(Unicode(self.artist))
                tag.setAlbum(Unicode(self.album))
                tag.setTitle(Unicode(self.title))
                #tag.setGenre(self.genre)
                if self.image and os.path.exists(self.image):
                    tag.addImage(eyeD3.ImageFrame.FRONT_COVER, self.image)
                tag.update()
            except Exception, why:
                traceback.print_exc()
        _debug_('%s.add_metadata() finished' % (self.__class__,))



class LastFMTuner(Thread):
    """
    The interface between the player and last.fm.

    This class is responsible for getting the play list and the tracks
    """
    def __init__(self, station, station_url, parent=None, menuw=None):
        Thread.__init__(self)
        self.name = parent.station if parent is not None else 'LastFMTuner'
        self.station = station
        self.station_url = station_url
        self.parent = parent
        self.menuw = menuw
        self.running = True
        self.webservices = LastFMWebServices()
        self.xspf = LastFMXSPF()
        self.playlist = deque()
        self.reason = None


    def retrieve_entry(self, entry):
        """
        Retrieve the image and the track
        """
        #print('%s.retrieve_entry(entry=%r)' % (self.__class__, entry))
        image_hdrs = {
            'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10'
        }
        track_hdrs = {
            'User-Agent': 'Freevo-%s' % (version.version),
            'Cookie': 'Session=%s' % self.webservices.session,
        }
        try:
            basename = os.path.join(config.LASTFM_DIR, entry.artist, entry.album, entry.title)
            basename = str(basename.lower().replace(' ', '_').replace('.', '').replace('\'', '').
                replace(':', '').replace(',', ''))
            if not os.path.isdir(os.path.dirname(basename)):
                #print('make directory %r' % (os.path.dirname(basename),))
                os.makedirs(os.path.dirname(basename), 0777)


            imagepath = basename + os.path.splitext(entry.image_url)[1].lower() if entry.image_url else None
            print('imagepath=%r' % (imagepath,))
            image_fetcher = self.webservices.fetch(entry.image_url, imagepath, image_hdrs)

            trackpath = basename + os.path.splitext(entry.location_url)[1].lower()
            print('trackpath=%r' % (trackpath,))
            track_fetcher = self.webservices.fetch(entry.location_url, trackpath, track_hdrs, entry)

            self.playlist.append(LastFMAudioItem(self.parent, entry, trackpath, imagepath))
            #print('%s.playlist=%s' % (self.__class__, pformat(list(self.playlist))))
        except LastFMError, why:
            print('LastFMError(1)=%s' % why)
            image_fetcher.stop()
            track_fetcher.stop()
            return

        try:
            while (image_fetcher and image_fetcher.isAlive()) or (track_fetcher and track_fetcher.isAlive()):
                if not self.running:
                    break
                time.sleep(0.5)

            if image_fetcher:
                print('image_fetcher.result=%r, track_fetcher.result=%r' % (image_fetcher.result, track_fetcher.result))
                if image_fetcher.reason is None:
                    _debug_('image %r downloaded' % (os.path.basename(imagepath),))
                elif imagepath and os.path.exists(imagepath):
                    _debug_('image %r removed' % (os.path.basename(imagepath),))
                    os.remove(imagepath)

            if track_fetcher:
                if track_fetcher.reason is None:
                    _debug_('track %r downloaded' % (os.path.basename(trackpath),))
                elif trackpath and os.path.exists(trackpath):
                    _debug_('track %r removed' % (os.path.basename(trackpath),))
                    os.remove(trackpath)
                #print('%s.playlist=%s' % (self.__class__, pformat(list(self.playlist))))
        except LastFMError, why:
            print('LastFMError(2)=%s' % why)
            image_fetcher.stop()
            track_fetcher.stop()
            if hasattr(why, 'code'):
                print(why.code)
            if hasattr(why, 'message'):
                print(why.message)
            print(self.playing())
            self.playlist.pop()
            print(self.playing())


    def run(self):
        """
        Execute the lastFM worker

        Tune to the station
        Fetch the XSPF play list
        Retrieve each entry in the XSPF play list
        """
        _debug_('%s.run(%s)' % (self.__class__, self.name))
        counter = 0
        if self.webservices.adjust_station(self.station_url) is None:
            self.reason = '%s' % (self.webservices.reason,)
            _debug_('cannot tune station %r: %s' % (self.station, self.reason), DWARNING)
            return

        while self.running:
            try:
                counter += 1
                xspf = self.webservices.request_xspf()
                feed = self.xspf.parse(xspf)
                for entry in feed.entries[:]:
                    if not self.running:
                        break
                    e = feed.entries.pop(0)
                    #print('e=%s' % (e,))
                    self.retrieve_entry(entry)
                # would need to append entries to the feed for this to work
                #if len(feed.entries) <= 2:
                #    break

            except LastFMError, why:
                traceback.print_exc()
                self.reason = '%s: %s' % (self.station, why)
                break
            except Exception, why:
                self.reason = '%s: %s' % (self.station, why)
                traceback.print_exc()
                break
            _debug_('counter=%r' % (counter,))
        self.running = False
        _debug_('%s.run(%s) finished' % (self.__class__, self.name))


    def stop(self):
        """
        Stop the tuner
        """
        _debug_('%s.stop()' % (self.__class__,))
        self.running = False


    def playing(self):
        #print('%s.playing()' % (self.__class__,))
        try:
            return self.playlist[0]
        except IndexError:
            return None

    def played(self):
        #print('%s.played()' % (self.__class__,))
        try:
            return self.playlist.popleft()
        except IndexError:
            return None

    def current(self):
        _debug_('%s.current()' % (self.__class__,))
        pass

    def skip(self):
        print('%s.skip()' % (self.__class__,))
        pass

    def ban(self):
        print('%s.ban()' % (self.__class__,))
        self.webservices.ban()

    def love(self):
        print('%s.love()' % (self.__class__,))
        self.webservices.love()



class LastFMStation(Item):
    """
    Item for the menu one for station
    """
    def __init__(self, parent, name, station, url=None):
        """
        This constructed for each station
        """
        #print('%s.__init__(parent=%r, name=%r, station=%r, url=%r)' % (self.__class__, parent, name, station, url))
        Item.__init__(self, parent=parent, info=None, skin_type=None)
        # Item objects have some fixed attributes
        self.name = name
        # Item objects can have some extra attributes
        self.station = station
        self.station_url = urllib.quote_plus(station)
        self.nowplaying = None
        self.menuw = None
        #print('%s.__dict__=%s' % (self.__class__, pformat(self.__dict__),))


    def actions(self):
        """
        return a list of actions for this item
        """
        #print('%s.actions()' % (self.__class__,))
        items = [ (self.play, _('Listen to %s' % Unicode(self.name))) ]
        return items


    def play(self, arg=None, menuw=None):
        """
        Play the station
        """
        _debug_('%s.play(arg=%r, menuw=%r)' % (self.__class__, arg, menuw))
        #print('%s.play=%s' % (self.__class__, pformat(self.__dict__),))
        #print('%s.play.info=%s' % (self.__class__, pformat(self.info.__dict__),))

        if not self.menuw:
            self.menuw = menuw
            _debug_('self.menuw=%r' % (self.menuw,))

        self.lastfm_tuner = LastFMTuner(self.station, self.station_url, self, self.menuw)
        self.lastfm_tuner.setDaemon(1)
        self.lastfm_tuner.start()

        self.nowplaying = None

        error = self.playnext(arg, self.menuw)
        if error and self.menuw:
            # could make this a cancel/retry box
            AlertBox(text=error).show()
            rc.post_event(PLAY_END)


    def playnext(self, arg=None, menuw=None):
        """
        Play the next item
        """
        _debug_('%s.playnext(arg=%r, menuw=%r)' % (self.__class__, arg, menuw))
        #print('%s.playlist=%s' % (self.__class__, pformat(list(self.lastfm_tuner.playlist))))
        if self.nowplaying is not None:
            played = self.lastfm_tuner.played()
            #print('%s.played=%s' % (self.__class__, played))
            #print('%s.playlist=%s' % (self.__class__, pformat(list(self.lastfm_tuner.playlist))))
        # may need to do this differently
        for i in range(100):
            if self.lastfm_tuner.reason is not None:
                return '%s' % (self.lastfm_tuner.reason,)
            self.nowplaying = self.lastfm_tuner.playing()
            if self.nowplaying is not None and os.path.exists(self.nowplaying.filename):
                if os.stat(self.nowplaying.filename)[ST_SIZE] >= config.LASTFM_CACHE_SIZE:
                    break
            time.sleep(0.2)
        else:
            return '%s' % (self.lastfm_tuner.reason,)

        #print('%s.nowplaying=%s' % (self.__class__, self.nowplaying))
        if self.lastfm_tuner.isAlive():
            print('lastfm_tuner is alive')
            if self.nowplaying is not None:
                self.nowplaying.play(arg, menuw)
        else:
            print('lastfm_tuner has died: %s' % (self.lastfm_tuner.reason,))
            return self.lastfm_tuner.reason
        return None


    def stop(self, arg=None, menuw=None):
        """
        Stop the current playing
        """
        _debug_('%s.stop()' % (self.__class__,))
        self.lastfm_tuner.stop()


    def eventhandler(self, event, menuw=None):
        """
        Event handler for play events and commands
        """
        _debug_('%s.eventhandler(event=%s, menuw=%r)' % (self.__class__, event, menuw))




class LastFMMainMenuItem(MenuItem):
    """
    This is the item for the main menu and creates the list of examples in a
    sub-menu.
    """
    def __init__(self, parent, arg):
        """
        Construct an instance of the menu item

        Initialise the item instance for the skin

        @param parent: the parent menu
        """
        _debug_('%s.__init__(parent=%r, arg=%r)' % (self.__class__, parent, arg))
        MenuItem.__init__(self, parent=parent, skin_type='lastfm')
        # Here we overwrite the text of the skins menu item so it can be translated
        self.name = _('LastFM Radio')
        self.event_context = 'audio'


    def actions(self):
        """
        Generate a list of actions for this menu item

        @returns: list of menu items
        """
        _debug_('%s.actions()' % (self.__class__,))
        items = [ (self.create_stations_menu,) ]
        return items


    def create_stations_menu(self, arg=None, menuw=None):
        """
        Create the menu of example items

        @param arg: will always be None as this is a method
        @param menuw: is a MenuWidget
        """
        _debug_('%s.create_stations_menu(arg=%r, menuw=%r)' % (self.__class__, arg, menuw))
        #print('create_stations_menu=%s' % pformat(self.__dict__))

        lfm_stations = []
        for lfm_location in config.LASTFM_LOCATIONS:
            name, station = lfm_location
            lfm_stations += [ LastFMStation(self, name, station) ]
        if not lfm_stations:
            lfm_stations += [MenuItem(_('No LastFM Stations'), menuw.goto_prev_page, 0)]
        lfm_menu = Menu(_('Last FM'), lfm_stations)
        menuw.pushmenu(lfm_menu)
        menuw.refresh()



class PluginInterface(MainMenuPlugin):
    """
    A plug-in to list examples, but can be used to
    show the output of a user command.

    To activate, put the following lines in local_conf.py::

        plugin.activate('audio.lastfm', level=45)
    """
    def __init__(self):
        """
        Construct an instance of the LastFM audio plug-in
        """
        self.name = 'LastFM Radio'
        _debug_('%s.__init__()' % (self.__class__,))
        MainMenuPlugin.__init__(self)
        #print('%s.__dict__=%s' % (self.__class__, self.__dict__,))
        #print('dir(self)=%s' % (dir(self),))
        lastfm_session = os.path.join(config.FREEVO_CACHEDIR, 'lastfm.session')
        if os.path.exists(lastfm_session):
            print('%r removed' % (lastfm_session,))
            os.remove(lastfm_session)


    def config(self):
        """
        Configuration method for lastfm items
        """
        _debug_('%s.config()' % (self.__class__,))
        return [
            ('LASTFM_USER', None, 'User name for www.last.fm'),
            ('LASTFM_PASS', None, 'Password for www.last.fm'),
            ('LASTFM_LANG', 'en', 'Language of last fm metadata (cn,de,en,es,fr,it,jp,pl,ru,sv,tr)'),
            ('LASTFM_DIR', os.path.join(config.FREEVO_CACHEDIR, 'lastfm'), 'Directory to save lastfm files'),
            ('LASTFM_LOCATIONS', [], 'LastFM locations'),
            ('LASTFM_CACHE_SIZE', 150 * 1024, 'Cache size of the buffer before playing'),
            ('LASTFM_BLOCK_SIZE', 100 * 1024, 'Block size of the buffer to retrieve'),
        ]


    def items(self, parent):
        """
        Set the main menu item

        @returns: MenuItem
        """
        _debug_('%s.items(parent=%r)' % (self.__class__, parent))
        return [ LastFMMainMenuItem(parent, self) ]



if __name__ == '__main__':
    # Test harness
    """
    To run this test harness need to have defined in local_conf.py:

        - LASTFM_USER
        - LASTFM_PASS
        - LASTFM_LANG
        - LASTFM_DIR
    """
    GUI = False

    station = 'lastfm://globaltags/jazz'
    station_url = urllib.quote_plus(station)
    lastfm_tuner = LastFMTuner('Jazz', station_url)
    lastfm_tuner.setDaemon(1)
    lastfm_tuner.start()

    playlist = 0
    while lastfm_tuner.isAlive():
        try:
            if len(lastfm_tuner.playlist) > playlist:
                played = lastfm_tuner.played()
                print('*** TRACK=%r ***' % (played,))
                playlist = len(lastfm_tuner.playlist)
            sys.stderr.write('.'); sys.stderr.flush()
            time.sleep(30)
        except KeyboardInterrupt:
            print >>sys.stderr, 'KeyboardInterrupt'
            lastfm_tuner.stop()
            lastfm_tuner.join()

    print('goodbye')
    raise SystemExit
