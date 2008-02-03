#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# applelib.py - Module for parsing apple's trailer site
# -----------------------------------------------------------------------
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Copyright (C) 2006 Pierre Ossman
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

import sys
import os
import re
import urllib
import urlparse
import pickle

_DEFAULT_URL = 'http://www.apple.com/trailers/'

_FEEDS = (
        ( 'home/feeds/just_added.json', 'Just Added' ),
        ( 'home/feeds/exclusive.json', 'Exclusive' ),
        ( 'home/feeds/just_hd.json', 'HD' ),
        ( 'home/feeds/upcoming.json', 'Featured' ),
        ( 'home/feeds/most_pop.json', 'Most Popular' ),
        ( 'home/feeds/genres.json', None ),
        ( 'home/feeds/studios.json', None),
        )

# Date of trailer addition. Comes on a separate line.
_date_re = re.compile(r'''<dt>(?P<month>[0-9]+)\.(?P<day>[0-9]+)</dt>''', re.IGNORECASE)

# Trailer link
_trailer_link_re = re.compile(r'''<dd><a[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>[^<]+).*</a>.*</dd>''', re.IGNORECASE)

# Start of a studio section
_studio_name_re = re.compile(r'''<h4><a[^>]*>(?P<name>[^<]*).*</a>.*</h4>''', re.IGNORECASE)

# Start of a genre section
_genre_name_re = re.compile(r'''<h4>(?P<name>[^<]*).*</h4>''', re.IGNORECASE)

# Trailer link when in studio/genre list
_trailer_list_link_re = re.compile(r'''<li><a[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>[^<]+).*</a>.*</li>''', re.IGNORECASE)

# Trailer subpages
_subpage_link_res = (
        re.compile(r'''href="(?P<url>[^"]*(?P<size>sm|small|low|240|mid|medium|320|lg|large|high|480|fullscreen)[^"]*\.html[^"]*)"''', re.IGNORECASE),
        re.compile(r'''movieAddress[^=]*=[^"]*"(?P<url>[^"]*(?P<size>240|320|480|640)[^"]*\.mov[^"]*)"''', re.IGNORECASE),
        re.compile(r'''<li><a href="(?P<url>/trailers/[^"]*)">''', re.IGNORECASE)
        )

# Extra step before trailer page
_frontpage_link_re = re.compile(r'''<a[^>]+href="(?P<url>/trailers/[^"]*(?P<type>trailer|teaser)[^"]*)"[^>]*>''', re.IGNORECASE)

# Stream link regexps
_stream_link_res = (
        re.compile(r'''<param[^>]+name="href"[^>]+value="(?P<url>[^"]+)"[^>]*>''', re.IGNORECASE),
        re.compile(r'''<param[^>]*name="src"[^>]*value="(?P<url>[^"]*)"[^>]*>''', re.IGNORECASE),
        re.compile(r'''XHTML[(]([^)]*\'href\',)?\'(?P<url>[^\']*)\'''', re.IGNORECASE),
        re.compile(r'''\'(?P<url>http[^\']*mov)\'''', re.IGNORECASE)
        )
# Stream exclude regexps
_stream_excl_res = (
        re.compile(r'''trailers/images.*btn''', re.IGNORECASE),
        )

# Old regexps
#       re.compile(r'''XHTML[(]\'(?P<url>[^\']*)\'''', re.IGNORECASE)

# Stream URLs in script based pages
_scriptpage_stream_link_re = re.compile(r'''movieAddress[^=]*=[^"]*"(?P<url>[^"]*(?P<size>240|320|480|640)[^"]*\.mov[^"]*)"''', re.IGNORECASE)

# Mapping between size code and name
_sizemap = [
        (('sm', 'small', 'low', '240'), ('Small', 0)),
        (('mid', 'medium', '320'), ('Medium', 1)),
        (('lg', 'large', 'high', '480'), ('Large', 2)),
        (('extralarge',), ('Extra Large', 3)),
        (('fullscreen',), ('Fullscreen', 4)),
        (('teaser',), ('Teaser', -1)),
        (('trailer',), ('Trailer', -1)),
        (('480p',), ('Small [HD 480p]', 10)),
        (('720p',), ('Medium [HD 720p]', 11)),
        (('1080i',), ('Small [HD 1080i]', 12)),
        (('1080p',), ('Large [HD 1080p]', 13))
        ]

class Trailers:
    def __init__(self):
        self.titles = {}

    def parse(self, callback = None, url = _DEFAULT_URL):
        self._mark_old()

        self._url = url

        feed_count = 0
        for feed in _FEEDS:
            data = self._dl(url + feed[0])
            try:
                false = False
                true = True
                data = eval(data)
            except:
                continue

            title_count = 0
            for title in data:
                self.parse_title(title, feed[1])

                title_count += 1
                callback(100 * feed_count / len(_FEEDS) + 100 * title_count / len(data) / len(_FEEDS))

            feed_count += 1
            callback(100 * feed_count / len(_FEEDS))

        if callback is not None:
            callback(100)

        self._prune()

        self.categories = []
        self.genres = []
        self.studios = []

        for title in self.titles.keys():
            if self.titles[title]["studio"] not in self.studios:
                self.studios.append(self.titles[title]["studio"])
            for g in self.titles[title]["genres"]:
                if g not in self.genres:
                    self.genres.append(g)
            for t in self.titles[title]["trailers"]:
                for c in t["categories"]:
                    if c not in self.categories:
                        self.categories.append(c)

        return self.titles

    def parse_title(self, title, category):
        name = title["title"]
        name = name.strip()

        if not self.titles.has_key(name):
            self.titles[name] = {"studio":title["studio"], "image":title["poster"], "genres":[], "trailers":[]}

        t = self.titles[name]

        if t.has_key("_old"):
            del t["_old"]

        for genre in title["genre"]:
            if genre is not None and genre not in t["genres"]:
                t["genres"].append(genre)

        for trailer in title["trailers"]:
            self.add_trailer(t, trailer["postdate"], trailer["url"], category)

    def add_trailer(self, t, date = None, url = None, category = None):
        if url is not None:
            url = urlparse.urljoin(self._url, url)
            self._parse_trailer_page(t, url, date, category)

    def _parse_trailer_page(self, title, url, date, category):
        for t in title["trailers"]:
            if t["url"] == url:
                if t.has_key("_old"):
                    del t["_old"]
                if date is not None:
                    t["date"] = date
                if category is not None and category not in t["categories"]:
                    t["categories"].append(category)
                return

        if category is None:
            categories = []
        else:
            categories = [category]

        t = {"url":url, "date":date, "categories":categories, "streams":[]}
        title["trailers"].append(t)

        lines = self._dl(url).split("\n")

        streams = []
        for line in lines:
            for expr in _subpage_link_res:
                iterator = expr.finditer(line)
                for m in iterator:
                    try:
                        page_size, page_key = self._map_size(m.group("size"))
                    except (IndexError):
                        page_size = None
                        page_key = None

                    suburl = urlparse.urljoin(url, m.group("url"))
                    substreams = self._parse_stream_page(suburl)

                    for ss in substreams:
                        for s in streams:
                            if s["url"] == ss["url"]:
                                break
                        else:
                            if ss["size"] is None:
                                size = page_size
                                key = page_key
                            else:
                                size, key = self._map_size(ss["size"])
                            self._add_stream(streams,
                                             {"url":ss["url"],
                                              "size":size,
                                              "sort_key":key})

            iterator = _frontpage_link_re.finditer(line)
            for m in iterator:
                page_size, page_key = self._map_size(m.group("type"))

                suburl = urlparse.urljoin(url, m.group("url"))
                substreams = self._parse_stream_page(suburl)
                if substreams:
                    for ss in substreams:
                        for s in streams:
                            if s["url"] == ss["url"]:
                                break
                        else:
                            if ss["size"] is None:
                                size = page_size
                                key = page_key
                            else:
                                size, key = self._map_size(ss["size"])
                            self._add_stream(streams,
                                             {"url":ss["url"],
                                              "size":size,
                                              "sort_key":key})
                else:
                    self._parse_trailer_page(title, suburl, date, category)

            substreams = self._extract_streams(url, line)
            if substreams:
                for ss in substreams:
                    for s in streams:
                        if s["url"] == ss["url"]:
                            break
                    else:
                        size, key = self._map_size(ss["size"])
                        self._add_stream(streams,
                                         {"url":ss["url"],
                                          "size":size,
                                          "sort_key":key})

        t["streams"] = streams

    def _parse_stream_page(self, url):
        lines = self._dl(url).split("\n")

        streams = []
        for line in lines:
            streams = streams + self._extract_streams(url, line)

        return streams

    def _extract_streams(self, baseurl, line):
        streams = []

        for expr in _stream_link_res:
            m = expr.search(line)
            if m:
                stream_url = urlparse.urljoin(baseurl, m.group("url"))

                size = None
                if stream_url.find("480p") != -1:
                    size = "480p"
                elif stream_url.find("720p") != -1:
                    size = "720p"
                elif stream_url.find("1080p") != -1:
                    size = "1080p"
                elif stream_url.find("1080i") != -1:
                    size = "1080i"

                for excl in _stream_excl_res:
                    if excl.search(stream_url):
                        break
                else:
                    streams.append({"url":stream_url, "size":size})

        m = _scriptpage_stream_link_re.search(line)
        if m:
            stream_url = urlparse.urljoin(baseurl, m.group("url"))
            for excl in _stream_excl_res:
                if excl.search(stream_url):
                    break
            else:
                streams.append({"url":stream_url, "size":m.group("size")})

        return streams

    def _map_size(self, size):
        for sm in _sizemap:
            if size in sm[0]:
                return sm[1]
        return ("Unknown (%s)" % str(size), -10)

    def _dl(self, url):
        f = urllib.urlopen(url)
        return f.read()

    def _add_stream(self, list, stream):
        for s in list:
            if s['sort_key'] < stream['sort_key']:
                list.insert(list.index(s), stream)
                break
        else:
            list.append(stream)

    def _mark_old(self):
        for title in self.titles.keys():
            self.titles[title]["_old"] = True
            for trailer in self.titles[title]["trailers"]:
                trailer["_old"] = True

    def _prune(self):
        keys = self.titles.keys()
        for title in keys:
            if self.titles[title].has_key("_old"):
                del self.titles[title]
            else:
                trailers = []
                for trailer in self.titles[title]["trailers"]:
                    if not trailer.has_key("_old"):
                        trailers.append(trailer)
                if trailers:
                    self.titles[title]["trailers"] = trailers
                else:
                    del self.titles[title]

    def only_studio(self, studio):
        keys = self.titles.keys()
        for title in keys:
            if studio != self.titles[title]["studio"]:
                del self.titles[title]

    def only_genre(self, genre):
        keys = self.titles.keys()
        for title in keys:
            if genre not in self.titles[title]["genres"]:
                del self.titles[title]

    def only_category(self, category):
        keys = self.titles.keys()
        for title in keys:
            trailers = []
            for trailer in self.titles[title]["trailers"]:
                if category in trailer["categories"]:
                    trailers.append(trailer)
            if trailers:
                self.titles[title]["trailers"] = trailers
            else:
                del self.titles[title]

    def sort_by_title(self):
        keys = self.titles.keys()
        keys.sort()
        return keys

def progress(perc):
    print "\rProgress: %d %%" % perc,

if __name__ == '__main__':
    # Use this to test loading subpages
    if 1:
        t = Trailers()
        title = {"trailers":[]}
        t._parse_trailer_page(title, "http://www.apple.com/trailers/weinstein/doadeadoralive/", None, None)
        print title
        sys.exit(0)

    try:
        t = pickle.load(file("trailers.dump"))
    except:
        t = Trailers()
    l = t.parse(progress)
    pickle.dump(t, file("trailers.dump", "w"))
    keys = l.keys()
    keys.sort()
    for title in keys:
        print title
        if l[title]["studio"] is not None:
            print "\tStudio:\t", l[title]["studio"]
        if l[title]["genres"]:
            print "\tGenres:\t", l[title]["genres"]
        print ""
        for t in l[title]["trailers"]:
            print "\t", t
        print ""
