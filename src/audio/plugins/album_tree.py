# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Represents audio items as different views
# -----------------------------------------------------------------------
# $Id$
# Author:      Martijn Voncken(2005)
# Todo:        need more(all) tags in the database(mmpython->extendedmeta)
#              gui:the bar on the left is gone?
#              couldn't figure out how to use playlist.Playlist() object.
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

"""
Represents audio items as different views
"""
import logging
logger = logging.getLogger("freevo.audio.plugins.album_tree")
from pprint import pprint

import config
import plugin
import menu
import rc
import skin, osd
#import audio.player

from event import *
from util.dbutil import *
db = MetaDatabase()

import playlist
from audio import audioitem
from gui import ProgressBox
from menu import MenuItem
from item import Item

#get the singletons so we get skin info and access the osd
skin = skin.get_singleton()
osd  = osd.get_singleton()

skin.register('album_tree', ('screen', 'title', 'info', 'plugin'))

class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to browse songs in a tree-like way.

    Requires: pysqlite U{http://oss.itsystementwicklung.de/trac/pysqlite/}

    B{Pre-Installation}

    The sqlite-meta-database should be available.

    The audio.rating and audio.logger plugin allso use this database,
    you can skip the rest of the pre-install if those plugins
    are already succesfully installed.

        - install pysqlite, sqlite
        - edit your local_config.py
          Configure AUDIO_ITEMS ('''AudioConfig''', don't leave it at the default!)
        - run freevo cache
        - wait.....
        - The meta database should be available now.

    B{Configuration}

    albumtree uses AUDIO_ALBUM_TREE_SPEC which is a list of selection criteria::

        - name is the name in the menu
        - spec is a list of selection criteria
        - alt_grouping is the grouping of the tracks (group by)

    Edit your local_config.py and add this:

    | plugin.activate('audio.album_tree')
    | AUDIO_ALBUM_TREE_SPEC = []
    |
    | #You could add all trees below:, but probably you only want 1 or 2 of them:
    | AUDIO_ALBUM_TREE_SPEC.append({'name':'Artist/Album/Track',
    |   'spec':["artist", "album", "track||'-'||title"],
    |   'alt_grouping':[None, None, 'track']
    | })
    |
    | #A case sensitive tree like above...
    | #Is easy to convert to a convert to a case insensitive tree like below:
    | AUDIO_ALBUM_TREE_SPEC.append({'name':'nocase:artist/album/Track',
    |   'spec':["lower(artist)", "lower(album)", "track||'-'||title"],
    |   'alt_grouping':[None, None, 'track']
    | })
    |
    | #my favorite layout:
    | AUDIO_ALBUM_TREE_SPEC.append({'name':'(A-Z)/Artist/Album-Year/Track',
    |   'spec':["upper(substr(artist, 0, 1))",
    |   "artist", "album||'-'||year",
    |   "track||'-'||title"],
    |   'alt_grouping':[None, None, 'year||album', 'track']
    | })
    |
    | #you can comment out a tree definition like this:
    | #AUDIO_ALBUM_TREE_SPEC.append({'name':'Artist-Album/Track',
    | #  'spec':["artist||'-'||album", "track||'-'||title"],
    | #  'alt_grouping':[None, 'track']
    | #})
    |
    | #More Examples:
    | AUDIO_ALBUM_TREE_SPEC.append({'name':'Year/Artist-Album/Track',
    |   'spec':["year", "artist||'-'||album", "track||'-'||title"],
    |   'alt_grouping':[None, None, None, 'track']
    | })
    |
    | AUDIO_ALBUM_TREE_SPEC.append({'name':'Dirtitle/Artist/Album/Track',
    |   'spec':["dirtitle", "artist", "album", "track||'-'||title"],
    |   'alt_grouping':[None, None, None, 'track']
    | })

    B{Post Installation}

    New plugins are not immediately visible on the freevo webserver.

    You might want to restart the  [wiki:Webserver freevo webserver] after the
    installation of a new plugin.

    Available columns for the selection are:
        - id INTEGER PRIMARY KEY
        - dirtitle VARCHAR(255) directory title
        - path VARCHAR(255)
        - filename VARCHAR(255)
        - type VARCHAR(5) (.mp3, .ogg, .flac)
        - artist VARCHAR(255)
        - title VARCHAR(255)
        - album VARCHAR(255)
        - genre VARCHAR(255)
        - year VARCHAR(255)
        - track NUMERIC(3)
        - track_total NUMERIC(3)
        - bpm NUMERIC(3)
        - last_play float
        - play_count NUMERIC
        - start_time NUMERIC
        - end_time NUMERIC
        - rating NUMERIC
        - eq VARCHAR
    """
    __version__ = "album_tree v0.60"

    def __init__(self):
        _debug_('PluginInterface.__init__()')
        plugin.MainMenuPlugin.__init__(self)
        if not config.AUDIO_ALBUM_TREE_SPEC:
            _debug_('AUDIO_ALBUM_TREE_SPEC is empty; demo-mode, using predefined trees', DWARNING)
            self.album_tree_list = self.load_demo()
        else:
            self.album_tree_list = self.load_spec(config.AUDIO_ALBUM_TREE_SPEC)

        #self.show_item = menu.MenuItem(_('Album Tree'), action=self.onchoose_main)
        #self.show_item.type = 'audio'
        plugin.register(self, 'audio.album_tree')


    def config(self):
        _debug_('PluginInterface.config()')
        return [
            ('AUDIO_ALBUM_TREE_SPEC', [], 'Specification for the album tree queries'),
        ]


    def shutdown(self):
        """
        shut down the sqlite database
        """
        _debug_('PluginInterface.shutdown()')
        db.close()


    def load_spec(self, spec_list):
        """
        Load definitions from config

        @returns: a list of trees
        """
        curs = db.cursor
        album_tree_list = []
        for specdef in spec_list:
            tree = TreeSpec(specdef['name'], curs, specdef['spec'])
            if specdef.has_key('alt_grouping'):
                tree.alt_grouping = specdef['alt_grouping']
            album_tree_list.append(tree)
        return album_tree_list


    def load_demo(self):
        """
        Load predefined testing layout

        @returns: a list of trees
        """
        curs = db.cursor
        album_tree_list = [
            TreeSpec('Artist/Album/Track', curs, ["artist", "album", "track||'-'||title"], [None, None, 'track']),
            TreeSpec('(A-Z)/Artist/Year-Album/Track', curs,
                ["upper(substr(artist, 0, 1))", "artist", "album||'-'||year", "track||'-'||title"],
                [None, None, 'year||album', 'track']),
            TreeSpec('Artist-Album/Track', curs, ["artist||'-'||album", "track||'-'||title"], [None, 'track']),
            TreeSpec('a-z/artist/title-album-track', curs,
                ["lower(substr(artist, 0, 1))", "lower(artist)", "title||'-'||album||'-'||track"]),
            TreeSpec('Year/Artist-Album/Track', curs,
                ["year", "artist||'-'||album", "track||'-'||title"], [None, None, None, 'track']),
            TreeSpec('Dirtitle/Artist/Album/Track', curs,
                ["dirtitle", "artist", "album", "track||'-'||title"], [None, None, None, 'track'])
        ]
        return album_tree_list

        #treespec below:
        #INSANE, but this is what i like about foobar2000.
        #NOT YET POSSIBLE, "album_artist" tag is not in sql database.
        #Surprisingly:sqlite can handle it pretty fast.
        #TreeSpec('a-z/album_artist/album/track-(artist)-title', curs,
        #   ["lower(substr(ifnull(album_artist, artist), 0, 1))",
        #       "ifnull(album_artist, artist)", "album",
        #       "track||'-'||nullif(artist, ifnull(album_artist, artist))||'-'||title"],
        #   [None, None, None, None, 'track'])


    def items(self, parent):
        _debug_('PluginInterface.items(parent=%r)' % (parent,))
        return [ AlbumTreeMainMenu(parent, self.album_tree_list) ]


    def actions(self):
        _debug_('PluginInterface.actions()')
        #todo: add random 10 etc..
        return []



class AlbumTreeMainMenu(MenuItem):
    """
    Create the menu item for Album Tree
    """
    def __init__(self, parent, tree):
        _debug_('AlbumTreeMainMenu.__init__(parent=%r)' % (parent,))
        MenuItem.__init__(self, name=_('Album Tree 2'), parent=parent, skin_type='album_tree', type='audio')
        self.parent = parent
        self.tree = tree
        #print 'AlbumTreeMainMenu:', pprint(self.__dict__)


    def actions(self):
        """
        return a list of actions for this item
        """
        _debug_('AlbumTreeMainMenu.actions()')
        items = [ (self.create_album_tree_menu, _('Album Tree Items')) ]
        return items


    def __call__(self, arg=None, menuw=None):
        """
        call first action in the actions list
        """
        _debug_('AlbumTreeMainMenu.__call__(arg=%r, menuw=%r)' % (arg, menuw))
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)


    def create_album_tree_menu(self, arg=None, menuw=None):
        """
        Create the menu of Album Tree items

        @param arg: will always be None as this is a method
        @param menuw: is a MenuWidget
        @returns: Nothing
        """
        _debug_('create_album_tree_menu(arg=%r, menuw=%r)' % (arg, menuw))
        branches = []
        for branch in self.tree:
            #print 'branch=%r' % branch,; pprint(branch.__dict__)
            branches.append(AlbumTreeBranchMenu(self, branch.name, (branch, [])))

        album_tree_menu = menu.Menu(_('Album Tree 2'), branches)
        menuw.pushmenu(album_tree_menu)
        menuw.refresh()



class AlbumTreeBranchMenu(MenuItem):
    """
    Item for the menu for one query
    """
    def __init__(self, parent, name, arg):
        _debug_('AlbumTreeBranchMenu.__init__(parent=%r, name=%r, arg=%r)' % (parent, name, arg))
        MenuItem.__init__(self, name, parent=parent)
        self.parent = parent
        self.branch = arg[0]
        self.data = arg[1]
        #print 'AlbumTreeBranchMenu:', pprint(self.__dict__)


    def actions(self):
        _debug_('AlbumTreeBranchMenu.actions()')
        return [ (self.branch_node, _('Album Tree Item')) ]


    def branch_node(self, arg=None, menuw=None):
        """
        browse through a tree specification
        """
        _debug_('branch_node(arg=%r, menuw=%r)' % (arg, menuw))
        title = '-'.join(self.data)

        mylistofitems =  []

        #print 'len(self.branch.spec)-1=%r, len(self.data)=%r' % (len(self.branch.spec)-1, len(self.data))
        if len(self.branch.spec) - 1 == len(self.data): #tracks
            self.leaf_node(self.branch, self.data, menuw)
            return
        else:
            for item, count in self.branch.execute(self.data):
                mylistofitems.append(AlbumTreeBranchMenu(self, "%s(%i)" % (item, count),
                    (self.branch, self.data + [item])))

        #should be impossible?
        if (len(mylistofitems) == 0):
            mylistofitems += [menu.MenuItem(_('No Objects found'), menuw.back_one_menu, 0)]

        myobjectmenu = menu.Menu(title, mylistofitems)
                                 #reload_func=menuw.back_one_menu )
        menuw.pushmenu(myobjectmenu)
        menuw.refresh()


    def leaf_node(self, branch, data, menuw):
        """
        last node in branch generates a playlist.
        """
        _debug_('leaf_node(branch=%r, data=%r, menuw=%r)' % (branch, data, menuw))
        title = '-'.join(data)
        #creating of audio items is slow.
        #need a progress-bar.
        pl = playlist.Playlist(name='-'.join(data), playlist=[], display_type='audiocd')

        tracks = branch.execute(data)  #returns list of (desc, path, filename)

        pop = ProgressBox(text=_('Generating playlist...'), full=len(tracks))
        pop.show()
        items = []
        i = 0
        for desc, path, filename in tracks:
            filepath = os.path.join(path, filename)
            item = audioitem.AudioItem(filepath, parent=pl)
            item.name = desc
            item.track = i
            items.append( item)
            pop.tick()
            i+=1
        pop.destroy()

        pl.playlist = items

        mymenu = menu.Menu(title, pl.playlist, item_types="audio")
        menuw.pushmenu(mymenu)



class TreeSpec(object):
    """
    see: PluginInterface() below for freevo plugin doc.
    this class contains no freevo specific code
    Inspired by foobar2000 albumlist (NOT playlist tree)
    (http://www.hydrogenaudio.org/forums/index.php?showforum=28)
    This is a tree/not a playlist generator.
    generates ugly sql(only as ugly as the spec), but sqlite is fast enough.
    operates directly on a sqlite cursor.
    see http://www.sqlite.org/lang_expr.html for "scripting" functions
    """
    def __init__(self, name='unnamed', cursor=None, spec=None, alt_grouping=None):
        self.spec = spec
        self.name = name
        self.alt_grouping = alt_grouping
        self.cursor = cursor


    def get_query(self, data):
        """
        builds query
        """

        where = []
        for i, item in enumerate(self.spec):
            if i < len(data):
                where.append('%s="%s"' % (item, data[i]))
            else:
                break
        if where:
            wheresql = ' where ' + ' and '.join(where)
        else:
            wheresql = ''

        #group by:
        grouping = self.spec[i]
        if self.alt_grouping and self.alt_grouping[i]:
            grouping = self.alt_grouping[i]

        #last level in tree-->, no-count ; use path, filename + order by instead of group by
        if len(self.spec) -1 == len(data):
            query = 'select %s, path, filename from music'% (self.spec[i], )
            query += wheresql
            query += ' order by ' + grouping
        #normal/not last level in tree
        else:
            query = 'select %s, count() from music'% (self.spec[i], )
            query += wheresql
            query += ' group by %s order by %s'  % (grouping, grouping)

        return query


    def execute(self, data):
        self.cursor.execute(self.get_query(data))
        return list(self.cursor)
        #should return an iterator/generator instead of a list?
        #dont confuse others/need count for progress -->return list
