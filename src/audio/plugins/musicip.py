# -----------------------------------------------------------------------
# musicip.py - MusicIP Mixer plugin
# -----------------------------------------------------------------------
# $Id$
#
# Author:
#   Dobes Vandermeer <dobesv@gmail.com>
# Notes:
#   HACK - sadly there's no way to import from the playlist module
#   since there's another playlis module in this same package.
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


from audio.audioitem import AudioItem
from gui.PopupBox import PopupBox
from directory import Playlist
import plugin
import config
import time
import item
import menu
import socket

from urllib import urlencode
from httplib import HTTPConnection

class MusicIPException(Exception):
    pass



class MusicIPClient:

    def __init__(self, host):
        self.host = host
        self.connection = None


    def callApi(self, func, args=None):
        if not self.connection:
            self.connection = HTTPConnection(self.host)

        url = '/api/'+func
        if args:
            url += '?' + urlencode(args)
        #print '[MusicIP Mixer] Fetching', url, 'from', self.host
        try: self.connection.request("GET", url)
        except socket.error:
            self.connection = None
            raise MusicIPException("Failed to communicate with MusicIP service!")
        response = self.connection.getresponse()
        if response.status != 200:
            raise MusicIPException(response.read().rstrip())
        return response.read()


    def getArtists(self, filter=None, showCounts=False):
        """
        Returns a list of all the artists.

        Parameters are:

        filter=name Use the named filter when creating the list (default none)
        If there is no such filter the name may refer to a genre as an implicit filter. 1.5
        showCount Prefix each artist with the number of songs by that artist
        """
        args = {}
        if filter: args["filter"] = filter
        if showCounts: args["showCounts"] = 1
        return self.callApi("artists", args).split('\n')


    def getAlbums(self, artist=None, bysong=False, extended=False, filter=None, showCount=None):
        """
        Returns a list of all the albums.

        Parameters are:

        artist=name Only include albums with at least one song by the named artist
        bysong Return key song from each album (useful for other api calls) 1.5
        extended Return album in artist@@name format 1.5 filter=name Use the named
        filter when creating the list (default none) If there is no such filter the
        name may refer to a genre as an implicit filter. 1.5 showCount Prefix each
        album with the number of songs on that album
        """
        args = {}
        if artist: args["artist"] = artist
        if bysong: args["bysong"] = 1
        if extended: args["extended"] = 1
        if filter: args["filter"] = filter
        if showCount: args["showCount"] = 1
        return self.callApi("albums", args).split('\n')


    def getGenres(self, filter=None, showCount=False):
        """
        Returns a list of all the genres. Parameters are: filter=name Use the named
        filter when creating the list (default none) 1.6 showCount Prefix each genres
        with the number of songs in that genre
        """
        args = {}
        if filter: args["filter"] = filter
        if showCount: args["showCount"] = 1
        return self.callApi("genres", args).split('\n')


    def getMix(self, song=None, artist=None, album=None, mixgenre=None, mood=None, playlist=None, rejectsize=None,
        rejecttype=None, size=None, sizetype=None, style=None, variety=None, filter=None,
        content=None):
        """
        Return a dynamic playlist. Parameters are: song=fullpath Choose a seed song
        artist=name Choose a seed artist album=fullpath Choose a seed album. fullpath
        is any song from the album album=artistname@@albumname Choose a seed album.
        (example: "The Beatles@@The White Album") mixgenre=boolean Restrict mix to the
        genre of the seed 1.1.6 mood=name Make a mood mix based on the given mood 1.5
        playlist=name||fullpath Choose all songs in the playlist as seeds 1.1.5.1
        rejectsize=# Set the number of items to skip before repeating artists 1.1.6
        rejecttype=(tracks|min|mbytes) Set the units for rejectsize (default tracks)
        1.1.6 size=# Set the size of the list (default 12) sizetype=(tracks|min|mbytes)
        Set the units for size (default tracks) style=# Set the style slider (default
        20, range is 0..200) variety=# Set the variety slider (default 0, range is
        0..9)) filter=name Use the named filter when creating the playlist (default
        none) If there is no such filter, the name may refer to a genre as an implicit
        filter.  content=(json|m3u|text|xspf) Set the returned mime type (default text)
        json|xspf requires 1.5 short Return short-style names (Windows only) 1.1.4 You
        may specify any number of songs, artists or albums as seeds, but you may not
        mix different types in a single request. If no seeds are set, a random song
        will be chosen from within the current filter.

        As of version 1.1.4, the above default values are replaced with the
        current application settings from the mix preferences.

        """
        args = {}
        if song: args["song"] = song
        if album: args["album"] = album
        if artist: args["artist"] = artist
        if mixgenre: args["mixgenre"] = mixgenre
        if mood: args["mood"] = mood
        if playlist: args["playlist"] = playlist
        if rejectsize: args["rejectsize"] = rejectsize
        if rejecttype: args["rejecttype"] = rejecttype
        if size: args["size"] = size
        if sizetype: args["sizetype"] = sizetype
        if style: args["style"] = style
        if variety: args["variety"] = variety
        if filter: args["filter"] = filter
        if content: args["content"] = content
        data = self.callApi("mix", args)
        if content is None or content == "text":
            return data.split('\n')
        elif content == 'json':
            import simplejson
            return simplejson.loads(data)
        else:
            return data


    def getMoods(self):
        """
        Returns a list of all the moods. Call this without parameters. This will only
        return information on platforms supporting the Moods menu.
        """
        return self.callApi("moods").split()


    def getSongs(self, album=None, artist=None, content=None, filter=None, extended=None):
        """
        Returns a list of all the songs (as a playlist). As of version 1.5, if you pass
        no artists or albums, all songs are returned. Parameters are: album=fullpath
        Only include songs from the named album. fullpath is any song from the album
        album=artistname@@albumname Only include songs from the named album. (example:
        "Pink Floyd@@Dark Side of the Moon") artist=name Only include songs by the
        named artist content=(json|m3u|text|xspf) Set the returned mime type (default
        text) json|xspf requires 1.5 filter=name Use the named filter when creating the
        playlist (default none) If there is no such filter the name may refer to a
        genre as an implicit filter. 1.5 extended Return extended info for each song
        (as in the getSong command). This ignores the content and short options.1.5
        short Return short-style names (Windows only)
        """
        args = {}
        if album: args["album"] = album
        if artist: args["artist"] = artist
        if filter: args["filter"] = filter
        if content: args["content"] = content
        data = self.callApi("songs", args)
        if content is None or content == "text":
            return data.split('\n')
        elif content == 'json':
            import simplejson
            return simplejson.loads(data)
        else:
            return data


    def getSongInfo(self, index=None, file=None):
        """
        Returns information about the indicated song. Parameters are: index Choose a
        song by index file Choose a song by file Returned value is a list of
        attributes, 1 per line. The first word is the field name, and the rest of the
        line is the field value. Some fields may not be present if there is no
        associated value. Current fields are: name, artist, album, album-id, file,
        genre, track, active, seconds, bytes, year, bitrate, composer, conductor,
        orchestra, lyricist, rating, modified, lastplayed, playcount, added
        """
        assert index or file, 'Must specify a file or an index'
        args = {}
        if index: args["index"] = index
        if file: args["file"] = file
        info = {}
        for line in self.callApi("getSong", args).split('\n'):
            words = line.split(None,1)
            if len(words) < 2: continue
            k,v = words
            info[k] = v
        return info


def getAudioItemsLazily(parent, callable, *args, **kwargs):
    for filename in callable(*args, **kwargs):
        yield AudioItem(filename, parent)



class ArtistItem(item.Item):

    def __init__(self, name, parent, service):
        item.Item.__init__(self, parent)
        self.name = name
        self.type = 'musicip_album'
        self.service = service


    def actions(self):
        return [ (self.make_menu, 'Browse') ]


    def make_menu(self, arg=None, menuw=None):
        try:
            menuw.pushmenu(menu.Menu('Genres',
            [ Playlist('All', getAudioItemsLazily(self, self.service.getSongs, artist=self.name), self)] +
            [ AlbumItem(x, self, self.service) for x in self.service.getAlbums(artist=self.name, extended=True)]))
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return



class AlbumItem(Playlist):

    def __init__(self, name, parent, service):
        Playlist.__init__(self, name.replace("@@", " - "), \
            getAudioItemsLazily(self, service.getSongs, album=name), parent)
        self.name = name.replace("@@", " - ")



class GenreItem(item.Item):

    def __init__(self, name, parent, service):
        item.Item.__init__(self, parent)
        self.name = name
        self.type = 'musicip_genre'
        self.service = service


    def actions(self):
        return [ (self.make_menu, 'Browse') ]


    def make_menu(self, arg=None, menuw=None):
        try:
            menuw.pushmenu(menu.Menu(self.name,
            [ Playlist('All', getAudioItemsLazily(self, self.service.getSongs, filter=self.name), self)] +
            [ AlbumItem(x, self, self.service) for x in self.service.getAlbums(filter=self.name, extended=True)]))
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return



class GenresItem(item.Item):

    def __init__(self, parent, service):
        item.Item.__init__(self, parent)
        self.name = 'Genres'
        self.type = 'musicip_genre_browser'
        self.service = service


    def actions(self):
        return [ (self.make_menu, 'Browse') ]


    def make_menu(self, arg=None, menuw=None):
        try:
            menuw.pushmenu(menu.Menu('Genres',
            [ GenreItem(x, self, self.service) for x in self.service.getGenres()]))
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return



class ArtistsItem(item.Item):

    def __init__(self, parent, service):
        item.Item.__init__(self, parent)
        self.name = 'Artists'
        self.type = 'musicip_artist_browser'
        self.service = service


    def actions(self):
        return [ (self.make_menu, 'Browse') ]


    def make_menu(self, arg=None, menuw=None):
        try:
            menuw.pushmenu(menu.Menu('Artists',
            [ ArtistItem(x, self, self.service) for x in self.service.getArtists()]))
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return



class AlbumsItem(item.Item):

    def __init__(self, parent, service):
        item.Item.__init__(self, parent)
        self.name = 'Albums'
        self.type = 'musicip_album_browser'
        self.service = service


    def actions(self):
        return [ (self.make_menu, 'Browse') ]


    def make_menu(self, arg=None, menuw=None):
        try:
            menuw.pushmenu(menu.Menu('Albums',
            [ AlbumItem(x, self, self.service) for x in self.service.getAlbums()]))
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return



class PluginInterface(plugin.ItemPlugin,plugin.MainMenuPlugin):
    """
    This plugin allows you to create a new mix based on MusicIP's automatic mixing
    feature.  It also allows browsing by Genre, Album, or Artist.

    You may set config.MUSICIP_SERVER to the host:port of the MusicIP service;
    127.0.0.1:10002 is the default.
    """

    def __init__(self):
        try: server = config.MUSICIP_SERVER
        except AttributeError: server = "127.0.0.1:10002"
        self.service = MusicIPClient(server)
        #config.
        plugin.ItemPlugin.__init__(self)
        plugin.MainMenuPlugin.__init__(self)

    #plugin.activate(self, type="audio")
    #self._type = 'mainmenu_audio'


    def items(self, parent):
        return [GenresItem(parent, self.service),
        ArtistsItem(parent, self.service),
        AlbumsItem(parent, self.service)]


    def actions(self, item):
        self.item = item
        #print 'actions called for item', item
        items = []
        if item.type in ('audio', 'playlist'):
            items.append((self.file_mix, _('MusicIP Mix'), 'musicip_file_mix'))
        if item.type == 'audio':
            items.append((self.file_play_album, _('Songs From Same Album'), 'musicip_file_play_album'))
            items.append((self.file_play_all_by_artist, _('Songs From Same Artist'), 'musicip_file_play_all_by_artist'))

        return items


    def file_mix(self, arg=None, menuw=None):
        kwargs = {}
        try:
            if self.item.type == 'playlist':
                filenames = self.service.getMix(playlist=self.item.filename)
            elif self.item.type == 'audio':
                filenames = self.service.getMix(song=self.item.filename)
            else:
                print 'Bad file type', self.item.type, self.item.filename, 'for MusicIP mix'
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return

        #file = NamedTemporaryFile(prefix="freevo-musicip-playlist", suffix=".tmp")
        #file.write(m3u)
        #print '\n'.join(filenames)
        #items = [kaa.beacon.query(filename=f) for f in filenames]
        playlist = Playlist('MusicIP Mix', playlist=filenames, display_type="audio", autoplay=True)
        playlist.browse(arg=arg, menuw=menuw)


    def file_play_album(self, arg=None, menuw=None):
        kwargs = {}
        try:
            if self.item.type == 'audio':
                songInfo = self.service.getSongInfo(file=self.item.filename)
                filenames = self.service.getSongs(album=songInfo['artist']+'@@'+songInfo['album'])
            else:
                print 'Bad file type', self.item.type, self.item.filename, 'for MusicIP mix'
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return

        #file = NamedTemporaryFile(prefix="freevo-musicip-playlist", suffix=".tmp")
        #file.write(m3u)
        #print '\n'.join(filenames)
        #items = [kaa.beacon.query(filename=f) for f in filenames]
        playlist = Playlist('%s - %s'%(songInfo['artist'], songInfo['album']), playlist=filenames, display_type="audio", autoplay=True)
        playlist.browse(arg=arg, menuw=menuw)


    def file_play_all_by_artist(self, arg=None, menuw=None):
        kwargs = {}
        try:
            if self.item.type == 'audio':
                songInfo = self.service.getSongInfo(file=self.item.filename)
                filenames = self.service.getSongs(artist=songInfo['artist'])
            else:
                print 'Bad file type', self.item.type, self.item.filename, 'for MusicIP mix'
        except MusicIPException, x:
            pop = PopupBox(text=_(str(x)))
            pop.show()
            time.sleep(2)
            pop.destroy()
            return

        #file = NamedTemporaryFile(prefix="freevo-musicip-playlist", suffix=".tmp")
        #file.write(m3u)
        #print '\n'.join(filenames)
        #items = [kaa.beacon.query(filename=f) for f in filenames]
        playlist = Playlist(songInfo['artist'], playlist=filenames, display_type="audio", autoplay=True)
        playlist.browse(arg=arg, menuw=menuw)
