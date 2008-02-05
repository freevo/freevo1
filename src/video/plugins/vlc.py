# -*- coding: iso-8859-1 -*-

# vlc.py - based on mplayer.py and xine.py

import os, re
import threading
import popen2
#import kaa.metadata as metadata

import config     # Configuration handler. reads config file.
import util       # Various utilities
import childapp   # Handle child applications
import rc         # The RemoteControl class.
import plugin

from event import *

class PluginInterface(plugin.Plugin):
    """
    VLC plugin for the video player, for RTSP streams
    """

    def __init__(self):
        plugin.Plugin.__init__(self)
        plugin.register(Vlc(), plugin.VIDEO_PLAYER, True)

    def config(self):
        return [ ('VLC_OPTIONS', 'None', 'Add your specific VLC options here'), ]


class Vlc:
    """
    the main class to control vlc
    """
    def __init__(self):
        """
        init the vlc object
        """
        self.name       = 'vlc'
        self.app_mode   = 'video'
        self.app        = None
        self.plugins    = []
        self.cmd        = config.VLC_CMD


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        try:
            _debug_('url=%r' % (item.url), 2)
            _debug_('mode=%r' % (item.mode), 2)
            _debug_('mimetype=%r' % (item.mimetype), 2)
            _debug_('network_play=%r' % (item.network_play), 2)
        except Exception, e:
            print e
        if item.url[:7] == 'rtsp://':
            _debug_('%r good' % (item.url))
            return 2
        _debug_('%r unplayable' % (item.url))
        return 0


    def play(self, options, item):
        """
        play a videoitem with vlc
        """
        self.options = options
        self.item    = item

        mode         = item.mode
        url          = item.url

        self.item_info    = None
        self.item_length  = -1
        self.item.elapsed = 0

        try:
            _debug_('Vlc.play(): url=%s' % url)
        except UnicodeError:
            _debug_('Vlc.play(): [non-ASCII data]')

        if config.VLC_OPTIONS:
            vlc_options=config.VLC_OPTIONS

        command = self.cmd + ' ' + vlc_options + ' --intf dummy -f --key-quit=esc "%s"' % url
        rc.app(self)

        self.app = childapp.ChildApp2(command)
        return None


    def stop(self):
        """
        Stop vlc
        """
        if not self.app:
            return
        self.app.kill(2)

        rc.app(None)
        self.app = None


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for vlc control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        #print "VLC::EventHendler : " + str(event)
        if not self.app:
            #print "VLC::Eventhandler : NNE"
            return self.item.eventhandler(event)

        if event == STOP:
            self.stop()
            return self.item.eventhandler(event)

        if event in ( PLAY_END, USER_END ):
            self.stop()
            return self.item.eventhandler(event)

        return self.item.eventhandler(event)
