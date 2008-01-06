# This is a replacement for the previous mpd plugin
# By Graham Billiau <graham@geeksinthegong.net> (DrLizAu's code monkey)
# This code is released under the GPL

# There are two parts to this plugin, an addition to the audio item menu to queue the item in mpd's playlist and a
# status display in the audio menu

# TODO:
#   add code to cope if the mpd server crashes
#   add code to enqueue an entire directory & sub-directories
#   add code to enqueue an existing playlist
#   modify code to support localisation
#   investigate having the mpd connection managed by another class

# Advantages of this over the previous mpd plugin:
#   The code is a lot cleaner and more robust.
#   Faster (talks to mpd directly, rather than calling other programs).
#   Allows you to modify the playlist within freevo.

# This only works if the music to be played is part of the filesystem avalible to mpd and also avalible to freevo
# so both on the same computer, or exported using samba or nfs

# This code uses the following options in local_conf.py:
#   MPD_SERVER_HOST='localhost'     # the host running the mpd server
#   MPD_SERVER_PORT='6600'          # the port the server is listening on
#   MPD_SERVER_PASSWORD=None        # the password to access the mpd server
#   MPD_MUSIC_BASE_PATH='/mnt/music/'    # the local path to where the music is stored, must have trailing slash
#   MPD_EXTERNAL_CLIENT='/usr/bin/pympd'    # the location of the external client you want to use, or None
#   MPD_EXTERNAL_CLIENT_ARGS=''     # arguments to be passed to the external client, or None, obsolete

# This is the mpd playlist plugin.
# using this you can add the currently selected song to the mpd playlist

import plugin
import config

import mpdclient2

class PluginInterface (plugin.ItemPlugin):
    """This plugin adds a 'enqueue in MPD' option to audio files"""


    def __init__(self):
        """open the connection to the mpd server and keep it alive
        assume that the plugin is loaded once, then kept in memory"""
        plugin.ItemPlugin.__init__(self)
        self.conn = mpdclient2.Thread_MPD_Connection(config.MPD_SERVER_HOST, config.MPD_SERVER_PORT, True,
                    config.MPD_SERVER_PASSWORD)
        
        # ensure there is a trailing slash on config.MPD_MUSIC_BASE_PATH
        if not config.MPD_MUSIC_BASE_PATH.endswith('/'):
            config.MPD_MUSIC_BASE_PATH = config.MPD_MUSIC_BASE_PATH + '/'


    def config(self):
        return [ ('MPD_SERVER_HOST', 'localhost', 'the host running the mpd server'),
                 ('MPD_SERVER_PORT', 6600, 'the port the server is listening on'),
                 ('MPD_SERVER_PASSWORD', None, 'the password to access the mpd server'),
                 ('MPD_MUSIC_BASE_PATH', '/mnt/music/', 'the local path to where the music is stored') ]


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