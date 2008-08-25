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

import config
import plugin
import menu
import rc
#import audio.player

from event import *
from util.dbutil import *
db = MetaDatabase()

import playlist
from audio import audioitem
from gui import ProgressBox


class treeSpec(object):
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
    """
    __version__ = "album_tree v0.51"

    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
        #config.EVENTS['audio']['DISPLAY'] = Event(FUNCTION_CALL, arg=self.detach)
        self.show_item = menu.MenuItem(_('Album Tree'), action=self.onchoose_main)
        self.show_item.type = 'audio'
        plugin.register(self, 'audio.album_tree')

        if (not config.__dict__.has_key('AUDIO_ALBUM_TREE_SPEC') ) or  (not config.AUDIO_ALBUM_TREE_SPEC):
            print '*ALBUM_TREE:"config.AUDIO_ALBUM_TREE_SPEC" is empty:DEMO-MODE:USING PREDEFINED TREES'
            self.load_demo()
        else:
            self.load_spec(config.AUDIO_ALBUM_TREE_SPEC)


    def shutdown(self):
        """
        shut down the sqlite database
        """
        _debug_('shutdown', 2)
        db.close()


    def load_spec(self, spec_list):
        """
        load definitions from config
        """
        curs = db.cursor
        self.album_tree_list = []
        for specdef in spec_list:
            tree = treeSpec(specdef['name'], curs, specdef['spec'])
            if specdef.has_key('alt_grouping'):
                tree.alt_grouping = specdef['alt_grouping']
            self.album_tree_list.append(tree)


    def load_demo(self):
        """
        load predefined testing layout
        """
        curs = db.cursor
        self.album_tree_list = [
        treeSpec('Artist/Album/Track', curs, ["artist", "album", "track||'-'||title"], [None, None, 'track']),
        treeSpec('(A-Z)/Artist/Year-Album/Track', curs,
            ["upper(substr(artist, 0, 1))", "artist", "album||'-'||year", "track||'-'||title"],
            [None, None, 'year||album', 'track']),
        treeSpec('Artist-Album/Track', curs, ["artist||'-'||album", "track||'-'||title"], [None, 'track']),
        treeSpec('a-z/artist/title-album-track', curs,
            ["lower(substr(artist, 0, 1))", "lower(artist)", "title||'-'||album||'-'||track"]),
        treeSpec('Year/Artist-Album/Track', curs,
            ["year", "artist||'-'||album", "track||'-'||title"], [None, None, None, 'track']),
        #demo:
        treeSpec('Dirtitle/Artist/Album/Track', curs,
            ["dirtitle", "artist", "album", "track||'-'||title"], [None, None, None, 'track'])
        ]

        #treespec below:
        #INSANE, but this is what i like about foobar2000.
        #NOT YET POSSIBLE, "album_artist" tag is not in sql database.
        #Surprisingly:sqlite can handle it pretty fast.
        #treeSpec('a-z/album_artist/album/track-(artist)-title', curs,
        #   ["lower(substr(ifnull(album_artist, artist), 0, 1))",
        #       "ifnull(album_artist, artist)", "album",
        #       "track||'-'||nullif(artist, ifnull(album_artist, artist))||'-'||title"],
        #   [None, None, None, None, 'track'])


    def items(self, parent):
        return [ self.show_item ]


    def actions(self):
        #todo: add random 10 etc..
        return []


    def onchoose_main(self, arg=None, menuw=None):
        """
        main menu
        """
        items = []
        for tree in self.album_tree_list:
            items.append(menu.MenuItem(tree.name, action=self.onchoose_node, arg=[tree, []]))

        #myobjectmenu = menu.Menu(_('Album Tree'), items, reload_func=menuw.back_one_menu )
        myobjectmenu = menu.Menu(_('Album Tree'), items)
        rc.app(None)
        menuw.pushmenu(myobjectmenu)
        menuw.refresh()


    def onchoose_node(self, arg=None, menuw=None):
        """
        browse through a tree specification
        """
        tree = arg[0]
        data = arg[1]
        title = '-'.join(data)

        mylistofitems =  []

        if len(tree.spec) -1 <> len(data): #non-tracks
            for tree_item, count in tree.execute(data):
                mylistofitems.append(
                    menu.MenuItem("%s(%i)" % \
                        (tree_item, count), action=self.onchoose_node, arg=[tree, data + [tree_item]]))
        else: #tracks
            self.onchoose_last_node(tree, data, menuw)
            return

        #should be impossible?
        if (len(mylistofitems) == 0):
            mylistofitems += [menu.MenuItem(_('No Objects found'),
                              menuw.back_one_menu, 0)]

        myobjectmenu = menu.Menu(title, mylistofitems)
                                 #reload_func=menuw.back_one_menu )
        rc.app(None)
        menuw.pushmenu(myobjectmenu)
        menuw.refresh()


    def onchoose_last_node(self, tree, data, menuw):
        """
        last node in tree generates a playlist.
        """
        title = '-'.join(data)
        #creating of audio items is slow.
        #need a progress-bar.
        pl = playlist.Playlist(name='-'.join(data), playlist=[], display_type='audiocd')

        tracks = tree.execute(data)  #returns list of (desc, path, filename)

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

        #note/question for core developers:
        #command below causes strange errors?
        #plugin.__plugin_type_list__ is empty??? but it's Not?
        #pl.browse(arg=None, menuw=menuw)
        #print 'LIST=', plugin.__plugin_type_list__['mimetype']
        #workaround: not all features of a real playlist :(

        mymenu = menu.Menu(title, pl.playlist, item_types="audio")
        menuw.pushmenu(mymenu)
