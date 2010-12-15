#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# vi:et:sw=4
# -----------------------------------------------------------------------
# applelib.py - Module for parsing apple's trailer site
# -----------------------------------------------------------------------
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Copyright (C) 2006-2008 Pierre Ossman
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
import traceback
try:
    import xml.etree.cElementTree as ET
except:
    import xml.etree.ElementTree as ET

import time
import datetime
import urllib

class Trailer:
    def __init__(self, element):
        self.cast = []
        self.genres = []
        self.poster = ''
        self.poster_large = ''
        self.title = ''
        self.runtime = 0
        self.rating = ''
        self.studio = ''
        self.release_date = None
        self.post_date = None
        self.director = ''
        self.description = ''
        self.preview_url = ''
        self.preview_size = 0

        for ch_element in element:
            if ch_element.tag == 'info':
                self.__parse_info(ch_element)
            elif ch_element.tag == 'cast':
                self.__parse_cast(ch_element)
            elif ch_element.tag == 'genre':
                self.__parse_genre(ch_element)
            elif ch_element.tag == 'poster':
                self.__parse_poster(ch_element)
            elif ch_element.tag == 'preview':
                self.__parse_preview(ch_element)

    def __parse_info(self, element):

        for ch in element:
            if ch.tag in ['title', 'rating', 'studio', 'director', 'description']:
                setattr(self, ch.tag, ch.text)

            elif ch.tag == 'runtime':
                rt = ch.text
                if rt is not None:
                    colon_pos = rt.find(':')
                    try:
                        if colon_pos != -1:
                            self.runtime = (int(rt[:colon_pos]) * 60 ) + int(rt[colon_pos+1:])
                        else:
                            self.runtime = int(colon_pos)
                    except:
                        traceback.print_exc()

            elif ch.tag == 'releasedate':
                if ch.text is not None:
                    t = time.strptime(ch.text, '%Y-%m-%d')
                    self.release_date = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)

            elif ch.tag == 'postdate':
                if ch.text is not None:
                    t = time.strptime(ch.text, '%Y-%m-%d')
                    self.post_date = datetime.date(t.tm_year, t.tm_mon, t.tm_mday)

    def __parse_cast(self, element):
        for ch in element.findall('name'):
            self.cast.append(ch.text)


    def __parse_genre(self, element):
        for ch in element.findall('name'):
            self.genres.append(ch.text)

    def __parse_poster(self, element):
        location = element.find('location')
        if location is not None:
            self.poster = location.text
        xlarge = element.find('xlarge')
        if xlarge is not None:
            self.poster_large = xlarge.text

    def __parse_preview(self, element):
        large = element.find('large')
        if large is not None:
            self.preview_url = large.text
            self.preview_size = int(large.get('filesize'))


class Trailers:
    """
    Class containing a list of trailers and cross-references to those trailers.

    The trailers are available as a simple list in attribute 'trailers' and
    are available via the cross-reference attributes 'genres', 'actors',
    'directors' and 'ratings'. Each of these is a dictionary containing the
    available genres/actors/directors or ratings and the trailer objects that
    match.
    """

    def __init__(self, resolution=None):
        """
        Create an object containing a list of trailers of the specified resolution
        (one of '480p', '720p' or None to get the standard resolution).
        """
        if resolution:
            self.feed_url = 'http://trailers.apple.com/trailers/home/xml/current_%s.xml' % resolution
        else:
            self.feed_url = 'http://trailers.apple.com/trailers/home/xml/current.xml'
        self.resolution = resolution
        self.feed_date = ''
        self.trailers = []
        self.genres = {}
        self.actors = {}
        self.directors = {}
        self.ratings = {}
        self.release_dates = {}
        self.update_feed()


    def update_feed(self):
        """
        Update the list trailers.
        Returns True if the list was updated, or False if not.
        """
        try:
            tree = ET.ElementTree()
            feed = urllib.urlopen(self.feed_url)
            tree.parse(feed)
            feed.close()
            root = tree.getroot()
            feed_date = root.get('date')
            if self.feed_date != feed_date:
                self.feed_date = feed_date
                self.trailers = []
                for record in root.findall('movieinfo'):
                    self.trailers.append(Trailer(record))
                self.trailers.sort(lambda x,y: cmp(x.title, y.title))
                
                self.genres = {}
                self.actors = {}
                self.directors = {}
                self.ratings = {}
                self.studios = {}
                self.release_dates = {}
                def add_to_hash(table, key, trailer):
                    if key in table:
                        table[key].append(trailer)
                    else:
                        table[key] = [trailer]

                for trailer in self.trailers:
                    for actor in trailer.cast:
                        add_to_hash(self.actors, actor, trailer)
                    for genre in trailer.genres:
                        add_to_hash(self.genres, genre, trailer)
                    add_to_hash(self.ratings, trailer.rating, trailer)
                    add_to_hash(self.directors, trailer.director, trailer)
                    add_to_hash(self.studios, trailer.studio, trailer)
                    add_to_hash(self.release_dates, trailer.release_date, trailer)

                return True
        except:
            traceback.print_exc()
        return False

if __name__ == '__main__':
    a = Trailers('720p')
    for studio,trailers in a.studios.items():
        print '[Studio] %s' % studio
        for t in trailers:
            print '\t%s' % t.title

    for genre,trailers in a.genres.items():
        print '[Genre] %s' % genre
        for t in trailers:
            print '\t%s' % t.title

    for actor,trailers in a.actors.items():
        print '[Actor] %s' % actor
        for t in trailers:
            print '\t%s' % t.title

    for director,trailers in a.directors.items():
        print '[Director] %s' % director
        for t in trailers:
            print '\t%s' % t.title

    for rating,trailers in a.ratings.items():
        print '[Rating] %s' % rating
        for t in trailers:
            print '\t%s' % t.title

    for date,trailers in a.release_dates.items():
        print '[Date] %s' % date.isoformat()
        for t in trailers:
            print '\t%s' % t.title