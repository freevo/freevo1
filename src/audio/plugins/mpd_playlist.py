# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the mpd playlist plugin.  Using this you can add the currently
# selected song to the mpd playlist
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# There are two parts to this plugin, an addition to the audio item menu to queue
# the item in mpd's playlist and a status display in the audio menu
#
# This only works if the music to be played is part of the filesystem avalible to
# mpd and also avalible to freevo so both on the same computer, or exported using
# samba or nfs
#
# Advantages of this over the previous mpd plugin:
#   The code is a lot cleaner and more robust.
#   Faster (talks to mpd directly, rather than calling other programs).
#   Allows you to modify the playlist within freevo.
#
# Todo:
#
#   add code to cope if the mpd server crashes
#   add code to enqueue an entire directory & sub-directories
#   add code to enqueue an existing playlist
#   modify code to support localisation
#   investigate having the mpd connection managed by another class
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

import plugin
import config
import mpdclient2

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin adds a 'enqueue in MPD' option to audio files

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:
    | plugin.activate('audio.mpd_playlist')
    """
    __author__           = 'Graham Billiau (DrLizAu\'s code monkey)'
    __author_email__     = 'graham@geeksinthegong.net'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'
    """open the connection to the mpd server and keep it alive
    assume that the plugin is loaded once, then kept in memory"""


    def __init__(self):
        if not config.MPD_MUSIC_BASE_PATH:
            self.reason = 'MPD_MUSIC_BASE_PATH not set in local_conf.py'
            return

        plugin.ItemPlugin.__init__(self)
        self.conn = mpdclient2.Thread_MPD_Connection(config.MPD_SERVER_HOST, config.MPD_SERVER_PORT, True,
                    config.MPD_SERVER_PASSWORD)

        # ensure there is a trailing slash on config.MPD_MUSIC_BASE_PATH
        if not config.MPD_MUSIC_BASE_PATH.endswith('/'):
            config.MPD_MUSIC_BASE_PATH = config.MPD_MUSIC_BASE_PATH + '/'


    def config(self):
        """returns the config variables used by this plugin"""
        return [
            ('MPD_SERVER_HOST', 'localhost', 'the host running the mpd server'),
            ('MPD_SERVER_PORT', 6600, 'the port the server is listening on'),
            ('MPD_SERVER_PASSWORD', None, 'the password to access the mpd server'),
            ('MPD_MUSIC_BASE_PATH', None, 'the local path to where the music is stored'),
            ('MPD_EXTERNAL_CLIENT', None,'the location of the external client you want to use'),
           #('MPD_EXTERNAL_CLIENT_ARGS', '','arguments to be passed to the external client'),
        ]


    def shutdown(self):
        """close the connection to the mpd server"""
        try:
            # this always throws EOFError, even though there isn't really an error
            self.conn.close()
        except EOFError:
            pass
        return


    def actions (self, item):
        """add the option for all music that is in the mpd library"""
        self.item = item
        # check to see if item is a FileItem
        if (item.type == 'file'):
            # check to see if item is in mpd's library
            if (item.filename.startswith(config.MPD_MUSIC_BASE_PATH)):
                # can query mpd to see if the file is in it's ibrary
                return [ (self.enqueue_file, 'Add to MPD playlist') ]
        #elif (item.type == 'dir'):
        #elif (item.type == 'playlist'):
        return []


    def enqueue_file(self, arg=None, menuw=None):
        self.conn.add(self.item.filename[len(config.MPD_MUSIC_BASE_PATH):])
        if menuw is not None:
            menuw.delete_menu(arg, menuw)
        return


    #def enqueue_dir(self, arg=None, menuw=None):


    #def enqueue_playlist(self, arg=None, menuw=None):
