# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for watching youtube videos
# -----------------------------------------------------------------------
# $Id: youtube.py 11862 2011-08-07 11:56:13Z adam $
#
# -----------------------------------------------------------------------
#
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
import logging
logger = logging.getLogger("freevo.video.plugins.ytflashplayer")
import os
import re
import socket
import urllib2

from BeautifulSoup import BeautifulSoup
import urlparse

import childapp
import config     # Configuration handler. reads config file.
import util       # Various utilities
import rc         # The RemoteControl class.
import plugin
import dialog

import util.httpserver
import util.webbrowser as webbrowser

from event import *

local_server = None

RE_YOUTUBE_URL = m = re.compile('^http://localhost:[0-9]+/youtube/(.+)$')

class PluginInterface(plugin.Plugin):
    """
    Youtube flash player plugin.

    This plugin requires either Chromium or Chrome to work and the Adobe flash plugin.

    To activate this plugin:
    | CHROME_PATH='/path/to/chrome'
    | plugin.activate('video.ytflashplayer')

    """
    def __init__(self):
        plugin.Plugin.__init__(self)
        if hasattr(config, 'CHROME_PATH') and config.CHROME_PATH:
            plugin.register(YTFlashPlayer(), plugin.VIDEO_PLAYER, True)
        else:
            print 'Youtube Flash Player disabled, CHROME_PATH is not set!'



class YTFlashPlayer:
    """
    the main class to control mplayer
    """
    def __init__(self):
        """
        init the mplayer object
        """
        self.name       = 'ytflashplayer'

        self.event_context = 'video'
        self.local_server = util.httpserver.get_local_server()
        self.local_server.register_handler('^(http://www.youtube.com/watch\?v=.+)$', self.__html_handler)
        print 'PROXY:', self.local_server.get_url('/')


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        if not item.url:
            return 0

        if RE_YOUTUBE_URL.match(item.url):
            return 1000
        return 0


    def play(self, options, item):
        """
        play a videoitem
        """
        m = RE_YOUTUBE_URL.match(item.url)
        if not m:
            return

        url = 'http://www.youtube.com/watch?v=%s' % m.group(1)

        self.options = options
        self.item    = item
        self.item_info    = None
        self.item_length  = -1
        self.item.elapsed = 0

        self.paused = False
        self.app = webbrowser.start_web_browser(url, self.__exited)
        rc.add_app(self)
        Event(PLAY_START, item).post()


    def stop(self):
        """
        Stop mplayer
        """
        if not self.app:
            return

        self.app.stop()


    def __exited(self, code):
        rc.remove_app(self)
        Event(PLAY_END).post()



    def eventhandler(self, event, menuw=None):
        """
        eventhandler for mplayer control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        logger.debug('%s.eventhandler(event=%s)', self.__class__, event)
        
        if not self.app:
            return self.item.eventhandler(event)

        if event in (STOP, PLAY_END, USER_END):
            self.stop()
            return self.item.eventhandler(event)

        if event == TOGGLE_OSD:
            dialog.show_play_state(dialog.PLAY_STATE_INFO, self.item, self.get_time_info)
            return True
        
        if event == PAUSE or event == PLAY:
            self.paused = not self.paused

            if self.paused:
                dialog.show_play_state(dialog.PLAY_STATE_PAUSE, self.item, self.get_time_info)
                webbrowser.ipc.pauseVideo()
            else:
                dialog.show_play_state(dialog.PLAY_STATE_PLAY, self.item, self.get_time_info)
                webbrowser.ipc.playVideo()
            return True

        if event == SEEK:
            self.paused = False
            webbrowser.ipc.seekVideo(event.arg)
            return True

        if event == 'WEB_IPC':
            if event.arg['event'] == 'error':
                self.stop()
                return True
            if event.arg['event'] == 'state':
                if event.arg['data'] == 0:
                    self.stop()
                    return True
                return True

        # nothing found? Try the eventhandler of the object who called us
        return self.item.eventhandler(event)


    def get_html(self, url):
        u = urllib2.urlopen(url+'&has_verified=1')
        yt_page = u.read()
        u.close()

        soup = BeautifulSoup(yt_page)
        embed = soup.find(id='movie_player')
        if embed is None:
            print '%s: failed to movie_player element'
            filename = url.replace('http://www.youtube.com/watch?v=', '')
            f = open('/tmp/youtube-' + filename,'w')
            f.write(yt_page)
            f.close()
        embed = str(embed)

        embed = re.sub('width="[0-9]+"', 'width="%d"' % (config.CONF.width-2), embed)
        embed = re.sub('height="[0-9]+"', 'height="%d"' % (config.CONF.height-2), embed)

        f = open(os.path.join(webbrowser.HTML_DIR, 'ytflashplayer.html'))
        html = f.read()
        f.close()

        return html.replace('$EMBED$', embed)



    def __html_handler(self, request, url):
        html = self.get_html(url)

        request.send_response(200)
        request.send_header('mime-type', 'text/html')
        request.send_header('content-length', '%d' % len(html))
        request.end_headers()

        request.wfile.write(html)
        request.wfile.flush()


    def get_time_info(self):
        return webbrowser.ipc.getTimes()


