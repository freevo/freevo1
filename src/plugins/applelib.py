#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# applelib.py - Module for parsing apple's trailer site
# -----------------------------------------------------------------------
#
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
_subpage_link_re = re.compile(r'''href="(?P<url>[^"]*(?P<size>sm|small|low|240|mid|medium|320|lg|large|high|480|fullscreen)[^"]*\.html[^"]*)"''', re.IGNORECASE)

# Extra step before trailer page
_frontpage_link_re = re.compile(r'''<a[^>]+href="(?P<url>/trailers/[^"]*(?P<type>trailer|teaser)[^"]*)"[^>]*>''', re.IGNORECASE)

# Stream link regexps
_stream_link_res = (
	re.compile(r'''<param[^>]+name="href"[^>]+value="(?P<url>[^"]+)"[^>]*>''', re.IGNORECASE),
	re.compile(r'''<param[^>]*name="src"[^>]*value="(?P<url>[^"]*)"[^>]*>''', re.IGNORECASE),
	re.compile(r'''XHTML[(]([^)]*\'href\',)?\'(?P<url>[^\']*)\'''', re.IGNORECASE)
	)

# Old regexps
#	re.compile(r'''XHTML[(]\'(?P<url>[^\']*)\'''', re.IGNORECASE)

# New script based pages
_scriptpage_link_re = re.compile(r'''href="(?P<url>[^"]*video.html\?[^"]*)"''', re.IGNORECASE)

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

_last_date = None
_last_studio = None
_last_genre = None

def _parse_hidef(line, t):
	global _last_date

	m = _date_re.search(line)
	if m:
		_last_date = "%s/%s" % (m.group("day"), m.group("month"))
		return

	m = _trailer_link_re.search(line)
	if m:
		t.add_trailer(m.group("title"), url = m.group("url"), date = _last_date, category = "HD")
		_last_date = None

def _parse_exclusive(line, t):
	global _last_date

	m = _date_re.search(line)
	if m:
		_last_date = "%s/%s" % (m.group("day"), m.group("month"))
		return

	m = _trailer_link_re.search(line)
	if m:
		t.add_trailer(m.group("title"), url = m.group("url"), date = _last_date, category = "Exclusive")
		_last_date = None

def _parse_newest(line, t):
	global _last_date

	m = _date_re.search(line)
	if m:
		_last_date = "%s/%s" % (m.group("day"), m.group("month"))
		return

	m = _trailer_link_re.search(line)
	if m:
		t.add_trailer(m.group("title"), url = m.group("url"), date = _last_date, category = "Newest")
		_last_date = None

def _parse_studios(line, t):
	global _last_studio

	m = _studio_name_re.search(line)
	if m:
		_last_studio = m.group("name")
		return

	m = _trailer_list_link_re.search(line)
	if m:
		t.add_trailer(m.group("title"), url = m.group("url"), studio = _last_studio)

def _parse_genres(line, t):
	global _last_genre

	m = _genre_name_re.search(line)
	if m:
		_last_genre = m.group("name")
		return

	m = _trailer_list_link_re.search(line)
	if m:
		t.add_trailer(m.group("title"), url = m.group("url"), genre = _last_genre)

# Stages of parsing the page. Each stage consists of a start regexp, a stop
# regexp and a line parser.
_stages = [
	('<h3>Featured High Definition Trailers</h3>', '<!-- .* High Definition Trailers -->', _parse_hidef),
	('<h3>Trailers Exclusive</h3>', '<!-- .* Trailer Exclusives-->', _parse_exclusive),
	('<h3>Newest Trailers</h3>', '<!-- .* Newest Trailers -->', _parse_newest),
	('<div id="trailers-studio">', '</div>', _parse_studios),
	('<div id="trailers-genre">', '</div>', _parse_genres) ]

class Trailers:
	def __init__(self):
		self.titles = {}

	def parse(self, callback = None, url = _DEFAULT_URL):
		self._mark_old()

		self._url = url

		lines = self._dl(url).split("\n")

		count = 0
		in_stage = False
		stage = 0
		start = re.compile(_stages[0][0], re.IGNORECASE)
		for line in lines:
			count += 1
			if callback is not None:
				callback(100 * count / len(lines))

			if in_stage:
				_stages[stage][2](line, self)
				if stop.search(line):
					in_stage = False
					stage += 1
					if stage >= len(_stages):
						break
					start = re.compile(_stages[stage][0], re.IGNORECASE)

			if not in_stage and start.search(line):
				in_stage = True
				stop = re.compile(_stages[stage][1], re.IGNORECASE)
				_stages[stage][2](line, self)

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

	def add_trailer(self, title, date = None, url = None, category = None, studio = None, genre = None):
		title = title.strip()
		if not self.titles.has_key(title):
			self.titles[title] = {"studio":None, "genres":[], "trailers":[]}

		t = self.titles[title]

		if t.has_key("_old"):
			del t["_old"]

		if url is not None:
				url = urlparse.urljoin(self._url, url)
				self._parse_trailer_page(t, url, date, category)

		if studio is not None:
			t["studio"] = studio

		if genre is not None and genre not in t["genres"]:
			t["genres"].append(genre)

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
			iterator = _subpage_link_re.finditer(line)
			for m in iterator:
				page_size, page_key = self._map_size(m.group("size"))
						
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

			iterator = _scriptpage_link_re.finditer(line)
			for m in iterator:						
				suburl = urlparse.urljoin(url, m.group("url"))
				substreams = self._parse_stream_page(suburl)

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

				streams.append({"url":stream_url, "size":size})

		m = _scriptpage_stream_link_re.search(line)
		if m:
			stream_url = urlparse.urljoin(baseurl, m.group("url"))
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

if __name__ == '__main__':
	# Use this to test loading subpages
	t = Trailers()
	title = {"trailers":[]}
	t._parse_trailer_page(title, "http://www.apple.com/trailers/wb/blooddiamond/hd/", None, None)
	print title
	print ""
	title = {"trailers":[]}
	t._parse_trailer_page(title, "http://www.apple.com/trailers/touchstone/apocalypto/", None, None)
	print title
	sys.exit(0)

	try:
		t = pickle.load(file("trailers.dump"))
	except:
		t = Trailers()
	l = t.parse()
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
