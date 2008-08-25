# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------------
# Audioscrobbler Realtime Submission Protocol v1.2 interface
# http://www.audioscrobbler.net/development/protocol/
# -----------------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------------
# Copyright (C) 2008 Krister Lagerstrom, et al.
#
# First Edition: Duncan Webb <duncan@freevo.org>
# Maintainer:    Duncan Webb <duncan@freevo.org>
#
# Please see the file AUTHORS for a complete list of authors.
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version
# 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
#
# -----------------------------------------------------------------------------

__all__ = ['Audioscrobbler', 'AudioscrobblerException', 'DEBUG' ]

import time, md5
import urllib

DEBUG = False


class AudioscrobblerException(Exception):
    """ AudioscrobblerException class """
    def __init__(self, why, url=None):
        self.why = why
        self.url = url

    def __str__(self):
        if self.url:
            return repr(self.url+': '+self.why)
        else:
            return repr(self.why)



class Audioscrobbler(object):
    """
    Audioscrobbler Realtime Submission Protocol class
    """
    sessionid = None
    nowplayingurl = None
    submissionurl = None

    def __init__(self, user, password, cachefilename):
        """
        Initialise an instance of Audioscrobbler

        @ivar handshake: Indicates that a handshake is requested. Hits to
          post.audioscrobbler.com without this variable set will return a
          human-readable informational message, default true
        @ivar clientid: Is an identifier for the client, default tst
        @ivar clientver: Is the version of the client being used, default 1.0
        @ivar user: Is the name of the user.
        @ivar timestamp: Is the current UNIX Timestamp, in seconds.
        @ivar auth: md5(md5(password) + timestamp)
        """
        if DEBUG:
            print 'Audioscrobbler.__init__(user=%r, password=%r, cachefilename=%r' % \
                (user, '*' * len(password), cachefilename)

        #self.handshake = 'true'
        #self.clientid = 'tst'
        self.clientid = 'fvo'
        self.clientver = '1.1'
        self.user = user
        self.password = password
        self.timestamp = None
        self.auth = None
        self.cachefilename = cachefilename
        self.cachedlines = []
        try:
            self.cachefd = open(self.cachefilename, 'r')
            Audioscrobbler.sessionid = self.cachefd.readline().strip('\n')
            Audioscrobbler.nowplayingurl = self.cachefd.readline().strip('\n')
            Audioscrobbler.submissionurl = self.cachefd.readline().strip('\n')
            for line in self.cachefd.readlines():
                self.cachedlines += line.strip()
        except IOError, why:
            self._login()


    def _urlopen(self, url, data=None, lines=True):
        """
        Wrapper to see what is sent and received

        @param url: Is the URL to read.
        @param data: Is the POST data.
        @param lines: return a list of lines, otherwise data block.
        @returns: reply from request
        @raise AudioscrobblerException: when a problem has been detected.
        """
        if DEBUG:
            print 'url=%r, data=%r' % (url, data)
        if lines:
            reply = []
            try:
                f = urllib.urlopen(url, data)
                if f is None:
                    raise AudioscrobblerException('Cannot open url', url)
                lines = f.readlines()
                f.close()
                if lines is None:
                    return []
                for line in lines:
                    reply.append(line.strip('\n'))
            except Exception, why:
                if DEBUG:
                    print '%s: %s' % (url, why)
                raise
            if DEBUG:
                print 'reply=%r' % (reply,)
            return reply
        else:
            reply = ''
            try:
                reply = urllib.urlopen(url, data).read()
            except Exception, why:
                if DEBUG:
                    print why
                raise
            if DEBUG:
                print 'reply=%r' % (reply,)
            return reply


    def _login(self):
        """
        Login to audioscrobbler.com, this is called when needed.

        @raise AudioscrobblerException: when a problem has been detected.
        """
        #self.timestamp = time.strftime('%s')
        now = time.time()
        if DEBUG:
            print 'login: lt=%r gm=%s' % (
                time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(now)),
                time.strftime('%d.%m.%Y %H:%M:%S', time.gmtime(now)))
        self.timestamp = time.strftime('%s', time.gmtime(now))
        #self.timestamp = time.strftime('%s', time.localtime(now))
        self.auth = md5.new(md5.new(self.password).hexdigest()+self.timestamp).hexdigest()
        url = 'http://post.audioscrobbler.com/?hs=true&p=1.2&c=%(clientid)s&v=%(clientver)s' % self.__dict__ + \
            '&u=%(user)s&t=%(timestamp)s&a=%(auth)s' % self.__dict__
        reply = self._urlopen(url)
        if reply[0] != 'OK':
            raise AudioscrobblerException(reply[0], url)
        Audioscrobbler.sessionid = reply[1]
        Audioscrobbler.nowplayingurl = reply[2]
        Audioscrobbler.submissionurl = reply[3]
        # Save the Audioscrobbler session information
        fd = open(self.cachefilename, 'w')
        print >>fd, Audioscrobbler.sessionid
        print >>fd, Audioscrobbler.nowplayingurl
        print >>fd, Audioscrobbler.submissionurl
        fd.close()


    def nowplaying(self, artist, track, album=None, secs=None, tracknumber=None, mbtrackid=None):
        """
        Send what is now playing to audioscrobbler.com

        @raise AudioscrobblerException: when a problem has been detected.

        @param artist: The artist name, required.
        @param track: The track name, required.
        @param album: The album title, or None if not known.
        @param secs: The length of the track in seconds, or None if not known.
        @param tracknumber: The position of the track on the album, or None if not known.
        @param mbtrackid: The MusicBrainz Track ID, or None if not known.
        """
        if Audioscrobbler.sessionid is None:
            self._login()
        data = {}
        data['s'] = Audioscrobbler.sessionid
        data['a'] = artist
        data['t'] = track
        data['b'] = album or ''
        data['l'] = secs or ''
        data['n'] = tracknumber or ''
        data['m'] = mbtrackid or ''

        url = Audioscrobbler.nowplayingurl
        reply = self._urlopen(url, urllib.urlencode(data))
        if reply[0] == 'BADSESSION':
            self._login()
            data['s'] = Audioscrobbler.sessionid
            reply = self._urlopen(url, urllib.urlencode(data))
        if reply[0] != 'OK':
            raise AudioscrobblerException(reply[0], url)


    def _prepare(self, num, artist, track, starttime, source, rating=None, secs=None,
        album=None, tracknumber=None, mbtrackid=None):
        """
        Prepares the track information to Audioscrobbler Realtime.

        @raise AudioscrobblerException: when a problem has been detected.

        @param num: Item number to submit.
        @param artist: The artist name, required.
        @param track: The track title, required.
        @param starttime: The time the track started playing.
        @param source: The source of the track, required.
        @param rating: A single character denoting the rating of the track.
        @param secs: The length of the track in seconds, required.
        @param album: The album title, or None if not known.
        @param tracknumber: The position of the track on the album, or None.
        @param mbtrackid: The MusicBrainz Track ID, or None if not known.

        @returns: dict of items for submission
        """
        if DEBUG:
            print '_prepare: num=%r, artist=%r, track=%r, starttime=%r, source=%r, rating=%r, secs=%r, album=%r, tracknumber=%r, mbtrackid=%r' % (num, artist, track, starttime, source, rating, secs, album, tracknumber, mbtrackid)

        if source == 'P' and secs < 30:
            raise AudioscrobblerException('FAILED track too short')
        played = int(time.time() - starttime)
        if played < 240 and played < int(secs) / 2:
            raise AudioscrobblerException('FAILED too early to submit')
        data = {}
        data['a[%d]' % num] = artist
        data['t[%d]' % num] = track
        data['i[%d]' % num] = time.strftime('%s', time.gmtime(starttime))
        data['o[%d]' % num] = source
        data['r[%d]' % num] = rating or 'L'
        data['l[%d]' % num] = int(secs) or ''
        data['b[%d]' % num] = album or ''
        data['n[%d]' % num] = tracknumber or ''
        data['m[%d]' % num] = mbtrackid or ''
        if DEBUG:
            print '%s: lt=%r gm=%s' % (track,
                time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(float(starttime))),
                time.strftime('%d.%m.%Y %H:%M:%S', time.gmtime(float(starttime))))
        return data


    def submit(self, artist, track, starttime, source, rating, secs=None,
        album=None, tracknumber=None, mbtrackid=None):
        """
        Submit one or more tracks to Audioscrobbler Realtime.

        The parameters may be either a single item or a list, when a list then
        each list must have the same number of items.

        The submission takes place as a HTTP/1.1 POST transaction with the
        server, using the URL provided during the handshake phase of the
        protocol. The submission body may contain the details for up to 50
        tracks which are being submitted. Under normal circumstances only a
        single track will be submitted, however, clients should cache
        submissions in case of failure.

        The request takes the form of a group of form encoded key-value pairs
        which are submitted to the server as the body of the HTTP POST request,
        using the URL provided in the handshake. All specified parameters must
        be present; they should be left empty if not known.

        @raise AudioscrobblerException: when a problem has been detected.

        @param artist: The artist name, required.

        @param track: The track title, required.

        @param starttime: The time the track started playing, in UNIX timestamp
          format (integer number of seconds since 00:00:00, January 1st 1970
          UTC). This must be in the UTC time zone, required.

        @param source: The source of the track, required, must be one of the
          following codes:
            - P Chosen by the user
            - R Non-personalised broadcast (e.g. Shoutcast, BBC Radio 1)
            - E Personalised recommendation except Last.fm (e.g. Pandora,
              Launchcast)
            - L Last.fm (any mode). In this case, the 5-digit Last.fm
              recommendation key must be appended to this source ID to prove
              the validity of the submission (for example, "o[0]=L1b48a").
            - U Source unknown
          Please note, for the time being, sources other than P and L are not
          supported.

        @param rating: A single character denoting the rating of the track.
          Empty if not applicable.
            - L Love (on any mode if the user has manually loved the track).
              This implies a listen.
            - B Ban (only if source=L). This implies a skip, and the client
              should skip to the next track when a ban happens.
            - S Skip (only if source=L)

          Note: Currently, a web-service must also be called to set love/ban
          status. We anticipate that this will be phased out soon, and the
          submission service will handle the whole process.

        @param secs: The length of the track in seconds, required when the
          source is P, optional otherwise.

        @param album: The album title, or None if not known.

        @param tracknumber: The position of the track on the album, or None if
          not known.

        @param mbtrackid: The MusicBrainz Track ID, or None if not known.
        """
        if DEBUG:
            print 'submit: artist=%r, track=%r, starttime=%r, source=%r, rating=%r, secs=%r, album=%r, tracknumber=%r, mbtrackid=%r' % (artist, track, starttime, source, rating, secs, album, tracknumber, mbtrackid)

        if Audioscrobbler.sessionid is None:
            self._login()
        data = {}
        data['s'] = Audioscrobbler.sessionid
        if isinstance(artist, (list, tuple)):
            for i in range(len(artist)):
                s_artist = artist[i]
                s_track = track[i]
                s_starttime = starttime[i]
                s_source = source[i]
                s_rating = rating is not None and rating[i] or 'L'
                s_secs = secs is not None and secs[i] or 0
                s_album = album is not None and album[i] or ''
                s_tracknumber = tracknumber is not None and tracknumber[i] or ''
                s_mbtrackid = mbtrackid is not None and mbtrackid[i] or ''
                data.update(self._prepare(i, s_artist, s_track, s_starttime, s_source, s_rating, s_secs,
                    s_album, s_tracknumber, s_mbtrackid))
        else:
            data.update(self._prepare(0, artist, track, starttime, source, rating, secs, album, tracknumber, mbtrackid))

        url = Audioscrobbler.submissionurl
        reply = self._urlopen(url, urllib.urlencode(data))
        if reply[0] == 'BADSESSION':
            self._login()
            data['s'] = Audioscrobbler.sessionid
            reply = self._urlopen(url, urllib.urlencode(data))
        if reply[0] != 'OK':
            raise AudioscrobblerException(reply[0], url)


if __name__ == '__main__':
    DEBUG = True
    # import username and password
    from astestdata import *

    # now playing test data
    np_artist='Nora Jones'
    np_track='Seven Years'
    np_album='Come Away With Me'

    # single track submission
    one_artist = 'Nora Jones'
    one_track = 'Humble Me'
    one_album = None
    one_starttime = time.time() - 30*60
    one_source = 'P'
    one_rating = 'L'
    one_secs = 276
    one_tracknumber = 9

    # mulitple track submission
    artist = ('Nora Jones', 'Nora Jones')
    track = ('Seven Years', 'In The Morning')
    album = ('come away with me', 'feels like home')
    starttime = (time.time() - 20*60, time.time() - 6*60)
    source = ('P', 'P')
    rating = ('L', 'L')
    secs = (145.319183673, 247.379591837)
    tracknumber = (None, 5)

    as = Audioscrobbler(user, password, '/tmp/as.cache')
    as.nowplaying(np_artist, np_track, np_album)
    try:
        #as.submit(one_artist, one_track, one_starttime, one_source, one_rating, one_secs, one_album, one_tracknumber)
        pass
    except AudioscrobblerException, why:
        print why
    try:
        #as.submit(artist, track, starttime, source, rating, secs, album, tracknumber)
        pass
    except AudioscrobblerException, why:
        print why

    artisttrackurl = "http://ws.audioscrobbler.com/1.0/artist/%s/toptracks.xml"
    url = artisttrackurl % (urllib.quote(np_artist))
    #print as._urlopen(url)
