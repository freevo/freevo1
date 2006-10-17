# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# appletrailers.py - Plugin for streaming trailers from apple.com
# -----------------------------------------------------------------------
#
# Add "plugin.activate('video.appletrailers')" in local_conf.py
# to activate
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

import os

import config
import plugin
import menu
import stat
import time
import string
import util.fileops
import util.misc

from item import Item
from video.videoitem import VideoItem
from gui.ProgressBox import ProgressBox

import applelib

MAX_CACHE_AGE = (60 * 60) * 8 # 8 hours

cachedir = os.path.join(config.FREEVO_CACHEDIR, 'appletrailers')
if not os.path.isdir(cachedir):
        os.mkdir(cachedir,
                stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))

class PluginInterface(plugin.MainMenuPlugin):
	"""
	A freevo interface to http://www.apple.com/trailers

	plugin.activate('video.appletrailers')
	"""
	def __init__(self):
		plugin.MainMenuPlugin.__init__(self)

	def items(self, parent):
		return [ BrowseBy(parent) ]

class AppleItem(Item):
	def __init__(self, parent):
		Item.__init__(self, parent)
		self.type = 'trailers'
		self.__load()

	def __progress(self, percent):
		if percent > self.__last_perc:
			for i in xrange(percent - self.__last_perc):
				self.__pop.tick()
			self.__last_perc = percent

	def __load(self):
		pfile = os.path.join(cachedir, 'data')
		if (os.path.isfile(pfile) == 0):
			self.trailers = applelib.Trailers()
			self.__pop = ProgressBox(text=_('Scanning Apple for trailers...'), full=100)
			self.__pop.show()
			self.__last_perc = -1
			self.trailers.parse(self.__progress)
			self.__pop.destroy()
			util.fileops.save_pickle(self.trailers, pfile)
		else:
			self.trailers = util.fileops.read_pickle(pfile)
			if abs(time.time() - os.path.getmtime(pfile)) > MAX_CACHE_AGE:
				self.__pop = ProgressBox(text=_('Scanning Apple for trailers...'), full=100)
				self.__pop.show()
				self.__last_perc = -1
				self.trailers.parse(self.__progress)
				self.__pop.destroy()
				util.fileops.save_pickle(self.trailers, pfile)

class TrailerVideoItem(VideoItem):
	def __init__(self, name, url, parent):
		VideoItem.__init__(self, url, parent)
		self.name = name
		self.type = 'trailers'

class Trailer(Item):
	def __init__(self, name, title, trailer, parent):
		Item.__init__(self, parent)
		self.name = name
		self.type = 'trailers'
		self.title = title
		self._trailer = trailer

	def actions(self):
		return [ (self.make_menu, 'Streams') ]

	def make_menu(self, arg=None, menuw=None):
		entries = []
		for s in self._trailer["streams"]:
			if s["size"] is None:
				name = "Unknown"
			else:
				name = s["size"]
			entries.append(TrailerVideoItem(name, s["url"], self))
		menuw.pushmenu(menu.Menu(self.title, entries))

class TrailerMenu(Item):
	def __init__(self, name, title, trailer, parent):
		Item.__init__(self, parent)
		self.name = name
		self.type = 'trailers'
		self.title = title
		self._trailer = trailer

	def actions(self):
		return [ (self.make_menu, 'Trailers') ]

	def make_menu(self, arg=None, menuw=None):
		entries = []
		i = 1
		for t in self._trailer["trailers"]:
			name = "Trailer %d" % i
			if t["categories"] is not None:
				name += " [" + ",".join(t["categories"]) + "]"
			if t["date"] is not None:
				name += " (" + t["date"] + ")"
			entries.append(Trailer(name, self.title, t, self))
			i += 1
		menuw.pushmenu(menu.Menu(self.title, entries))

class BrowseByTitle(AppleItem):
	def __init__(self, parent):
		AppleItem.__init__(self, parent)
		self.name = _('Browse by Title')
		self.title = _('Trailers')

	def actions(self):
		return [ (self.make_menu, 'Titles') ]

	def _gen_name(self, title, trailer):
		name = title
		dates = []
		categories = []
		for t in trailer["trailers"]:
			if t["date"] is not None and t["date"] not in dates:
				dates.append(t["date"])
			if t["categories"] is not None and t["categories"] not in categories:
				categories += t["categories"]
		if categories:
			name += " [" + ",".join(categories) + "]"
		if dates:
			name += " (" + ",".join(dates) + ")"
		return name

	def make_menu(self, arg=None, menuw=None):
		entries = []
		for t in self.trailers.sort_by_title():
			title = self.trailers.titles[t]
			name = self._gen_name(t, title)
			if len(title["trailers"]) == 1:
				entries.append(Trailer(name, t, title["trailers"][0], self))
			else:
				entries.append(TrailerMenu(name, t, title, self))
		menuw.pushmenu(menu.Menu(self.title, entries))

class Genre(BrowseByTitle):
	def __init__(self, genre, parent):
		BrowseByTitle.__init__(self, parent)
		self.name = genre
		self.title = genre
		self.trailers.only_genre(genre)

class Category(BrowseByTitle):
	def __init__(self, category, parent):
		BrowseByTitle.__init__(self, parent)
		self.name = category
		self.title = category
		self.trailers.only_category(category)

class Studio(BrowseByTitle):
	def __init__(self, studio, parent):
		BrowseByTitle.__init__(self, parent)
		self.name = studio
		self.title = studio
		self.trailers.only_category(studio)

class BrowseByGenre(AppleItem):
	def __init__(self, parent):
		AppleItem.__init__(self, parent)
		self.name = _('Browse by Genre')

	def actions(self):
		return [ (self.make_menu, 'Genres') ]

	def make_menu(self, arg=None, menuw=None):
		genres = []
		for g in self.trailers.genres:
			genres.append(Genre(g, self))
		menuw.pushmenu(menu.Menu(_('Choose a genre'), genres))

class BrowseByCategory(AppleItem):
	def __init__(self, parent):
		AppleItem.__init__(self, parent)
		self.name = _('Browse by Category')

	def actions(self):
		return [ (self.make_menu, 'Categories') ]

	def make_menu(self, arg=None, menuw=None):
		categories = []
		for c in self.trailers.categories:
			categories.append(Category(c, self))
		menuw.pushmenu(menu.Menu(_('Choose a category'), categories))

class BrowseByStudio(AppleItem):
	def __init__(self, parent):
		AppleItem.__init__(self, parent)
		self.name = _('Browse by Studio')

	def actions(self):
		return [ (self.make_menu, 'Studios') ]

	def make_menu(self, arg=None, menuw=None):
		studios = []
		for s in self.trailers.studios:
			studios.append(Studio(s, self))
		menuw.pushmenu(menu.Menu(_('Choose a studio'), studios))

class BrowseBy(Item):
	def __init__(self, parent):
		Item.__init__(self, parent)
		self.name = 'Apple Trailers'
		self.type = 'trailers'

	def actions(self):
		return [ (self.make_menu, 'Browse by') ]

	def make_menu(self, arg=None, menuw=None):
		menuw.pushmenu(menu.Menu('Apple Trailers',
			[ BrowseByGenre(self),
			  BrowseByCategory(self),
			  BrowseByStudio(self),
			  BrowseByTitle(self) ]))
