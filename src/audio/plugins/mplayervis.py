# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Native Freevo MPlayer Audio Visualization Plugin
# -----------------------------------------------------------------------
# $Id$
#
# Notes: - I'm no fan of all the skin.clear() being done :(
# Todo:  - Find a way to stop the skin when in full-screen mode
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

"""
Native Freevo MPlayer Audio Visualization Plugin
"""

__author__ = 'Viggo Fredriksen <viggo@katatonic.org>'

import os, time
from threading import Lock
try:
    import pygoom
except ImportError:
    raise ImportError('[audio.mplayervis]: Pygoom not available, please install '+
                    'or remove this plugin (http://freevo.sf.net/pygoom).')

if not hasattr(pygoom, 'HEXVERSION') and pygoom.HEXVERSION < 0x000200f0:
    raise ImportError('pygoom too old, you need version 0.2.0 or higher')

# pygame modules
from pygame import Surface, Rect, image, transform
from pygame.time import Clock
import pygame
from pprint import pformat

# kaa modules
from kaa import Timer, OneShotTimer

# freevo modules
import config
import plugin, rc, skin, osd

from event import *
from animation import render, BaseAnimation
from audio.player import PlayListSuccession


if config.DEBUG_DEBUGGER:
    import pdb, pprint, traceback

MMAP_FILE = '/tmp/mpav'
skin = skin.get_singleton()
osd  = osd.get_singleton()


class MpvMode:
    """
    MODE definitions
    """
    DOCK = 0 # dock
    FULL = 1 # fullscreen
    NOVI = 2 # no view

    def __init__(self, mode=DOCK):
        self.mode = mode

    def __repr__(self):
        if self.mode == MpvMode.DOCK: return 'DOCK'
        if self.mode == MpvMode.FULL: return 'FULL'
        if self.mode == MpvMode.NOVI: return 'NOVI'
        return 'UNKNOWN'

    def __cmp__(self, other):
        if isinstance(other, MpvMode):
            if self.mode > other.mode: return 1
            if self.mode < other.mode: return -1
        else:
            if self.mode > other: return 1
            if self.mode < other: return -1
        return 0

    def __index__(self):
        return self.mode

    def __int__(self):
        return self.mode

    def __add__(self, other):
        self.mode = (self.mode + int(other)) % 3
        return self

    def __sub__(self, other):
        self.mode = (self.mode - int(other)) % 3
        return self



class MpvGoom(BaseAnimation):
    """
    Class to interface with the pygoom module
    """
    message    = None
    coversurf  = None

    def __init__(self, x, y, width, height, title=None, coverfilename=None):
        """
        Initialise the MPlayer Visualization Goom
        """
        _debug_('%s.__init__(x=%r y=%r width=%r height=%r coverfilename=%r)' % (
            self.__class__, x, y, width, height, coverfilename))
        self.mode = MpvMode(config.MPLAYERVIS_MODE)
        self.coverfilename = coverfilename
        self.showfps = False

        if not os.path.exists(MMAP_FILE):
            f = open(MMAP_FILE, 'w')
            s = str(chr(0)) * 2064
            f.write(s)
            f.close()

        #pygoom.debug(2)
        BaseAnimation.__init__(self, (x, y, width, height), fps=100, bg_update=False, bg_redraw=False)
        # goom doesn't handle Unicode, so make it a string
        self.goom = pygoom.PyGoom(width, height, MMAP_FILE, songtitle=String(title) or '')
        self.infodata = None

        self.width = width
        self.height = height
        self.fade_step = config.MPLAYERVIS_FADE_STEP
        self.init_counter = self.fade_step * config.MPLAYERVIS_INIT_COUNTER
        self.fade_in_wait_counter = self.fade_step * config.MPLAYERVIS_FADE_IN_WAIT_COUNTER
        self.fade_out_wait_counter = self.fade_step * config.MPLAYERVIS_FADE_OUT_WAIT_COUNTER
        self.fade_counter = self.fade_step * config.MPLAYERVIS_FADE_COUNTER
        self.fade_machine = {
            'init': self.init_state,
            'fade_out_wait': self.fade_out_wait_state,
            'fade_out': self.fade_out_state,
            'fade_in_wait': self.fade_in_wait_state,
            'fade_in': self.fade_in_state,
        }
        self.state = self.fade_machine['init']
        self.counter = self.init_counter
        self.fader = lambda n, m: int(float(n-m)/float(2))
        self.alpha = self.set_alpha(self.counter, 0)

        self.clock = Clock()
        self.running = False
        self.timer = Timer(self.goom_surface_update)
        self.last_time = 0
        self.message_counter = 1 # skip message at start
        self.messages = []


    def __del__(self):
        _debug_('MpvGoom.__del__')


    def set_visual(self, visual):
        """ pass the visualisation effect to goom """
        _debug_('set_visual(visual=%r)' % (visual,))
        self.goom.fxmode = visual


    def set_songtitle(self, songtitle):
        """ pass the song title to goom """
        _debug_('set_songtitle(songtitle=%r)' % (songtitle,))
        self.goom.songtitle = str(songtitle)


    def set_message(self, message):
        """ pass a message to goom """
        _debug_('set_message(message=%r)' % (message,))
        self.goom.message = str(message)


    def set_alpha(self, high, low):
        """ Get the alpha level for a count """
        _debug_('set_alpha(high=%r low=%r)' % (high, low,), 2)
        alpha = self.fader(high, low)
        if alpha < 0:   alpha = 0
        if alpha > 255: alpha = 255
        return alpha


    def set_coverimage(self, coverfilename):
        """
        Set a blend image to toggle between visual and cover
        Updated when resolution is changed
        """
        _debug_('%s.set_coverimage(coverfilename=%r)' % (self.__class__, coverfilename))
        self.coverfilename = coverfilename
        self.set_coverimagesurf(coverfilename)


    def set_coverimagesurf(self, coverfilename):
        """
        Get the cover image surface
        The image is scaled to the size of the suface keeping the aspect of the surface

        @param coverfilename: the file name for the cover image
        @returns: a surface
        """
        _debug_('%s.set_coverimagesurf(coverfilename=%r)' % (self.__class__, coverfilename))
        # change the cover if necessary
        coversurf = None
        if coverfilename:
            try:
                coversurf = image.load(coverfilename).convert()
                #coversurf.set_colorkey(-1) # make top-left pixel transparent
            except Exception, why:
                _debug_(why, DWARNING)

        if coversurf is not None:
            # scale and fit to the rect
            w, h   = coversurf.get_size()
            aspect = float(w)/float(h)

            if aspect < 1.0:
                #w = self.rect.width
                w = self.width
                h = float(w) / aspect
                x = 0
                #y = (self.rect.height - h) / 2
                y = (self.height - h) / 2
            else:
                #h = self.rect.height
                h = self.height
                w = float(h) * aspect
                y = 0
                #x = (self.rect.width - w)  / 2
                x = (self.width - w)  / 2

            self.coversurf = (transform.scale(coversurf, (w, h)), x, y)
        else:
            self.coversurf = coversurf
        _debug_('self.coversurf=%r coversurf=%r' % (self.coversurf, coversurf))


    def set_resolution(self, x, y, width, height, zoom=1):
        """ Set the resolution of the goom window """
        _debug_('%s.set_resolution(x=%r, y=%r, width=%r, height=%r, zoom=%r)' % (
            self.__class__, x, y, width, height, zoom))
        self.width = width
        self.height = height
        r = Rect(x, y, width / zoom, height / zoom)
        if r == self.rect:
            return
        self.rect = r

        # clear info
        self.infodata = None

        _debug_('self.goom.resolution(width=%r, height=%r)' % (width / zoom, height / zoom))
        self.goom.resolution(width / zoom, height / zoom)
        self.set_coverimagesurf(self.coverfilename)
        self.c_timer   = time.time()


    def set_fullscreen(self):
        """ Set the mode to full screen """
        _debug_('set_fullscreen()')
        w, h = config.MPLAYERVIS_FULL_GEOMETRY.split('x')

        # trying to figure out if it is possible to keep the aspect ratio
        #w = config.CONF.width-(config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT)
        #w = int(float(w) * config.OSD_PIXEL_ASPECT)
        #w = config.CONF.width

        w = float(w) / config.OSD_PIXEL_ASPECT
        w = int(w)
        h = int(h)

        # Centre on display
        x = int(config.CONF.width - w) / 2
        x = int(float(x) / config.OSD_PIXEL_ASPECT)
        y = int(config.CONF.height - h) / 2
        _debug_('x=%r y=%r w=%r h=%r' % (x, y, w, h))

        self.set_resolution(x, y, w, h, 2 ** config.MPLAYERVIS_FULL_ZOOM)


    def set_dock(self):
        """ Set the mode to full screen """
        _debug_('set_dock()')
        # get the rect from skin
        imgarea = skin.areas['view']
        c = imgarea.calc_geometry(imgarea.layout.content, copy_object=True)
        w = c.width   - 2*c.spacing
        h = c.height  - 2*c.spacing
        x = c.x + c.spacing
        y = c.y + c.spacing
        _debug_('c=%r, w=%r, h=%r, x=%r, y=%r' % (c, w, h, x, y))

        # check if the view-area has a rectangle
        #try:
        #    r = c.types['default'].rectangle
        #    x -= r.x
        #    y -= r.y
        #    w += 2*r.x
        #    h += 2*r.y
        #except:
        #    pass

        self.set_resolution(x, y, w, h, 2 ** config.MPLAYERVIS_DOCK_ZOOM)


    def set_info(self, info, timeout=5):
        """
        Pass a info message on to the screen.

        @param info: text to draw
        @param timeout: how long to display
        """
        _debug_('set_info(info=%r, timeout=%r)' % (info, timeout))

        font = skin.get_font('widget')
        w = font.stringsize(info)
        h = font.height
        x = config.OSD_OVERSCAN_LEFT+5
        x = int(float(x) / config.OSD_PIXEL_ASPECT)
        y = config.OSD_OVERSCAN_TOP+5

        s = Surface((w, h), 0, 32)
        _debug_('s=%r info=%r font=%r x=%r y=%r w=%r h=%r' % (s, info, font, x, y, w, h))

        self.infodata  = (s, info, font, x, y, w, h)
        self.m_timer   = time.time()
        self.m_timeout = timeout


    def draw_info(self, gooms):
        """
        Draw the info
        @param gooms: Goom surface
        """
        _debug_('draw_info()', 2)
        if self.infodata is not None:
            (s, info, font, x, y, w, h) = self.infodata
            if time.time() - self.m_timer > self.m_timeout:
                self.infodata = None
                s.fill(0)
                return

            osd.drawstringframed(info, 0, 0, w, h, font, mode='hard', layer=s)
            gooms.blit(s, (x, y))


    def init_state(self):
        #_debug_('init_state()')
        if self.counter > 0:
            # Initial fade out is twice as fast as normal
            self.counter -= (self.fade_step * 2)
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.counter, 0)
        if self.counter == 0:
            self.counter = self.fade_in_wait_counter
            self.state = self.fade_machine['fade_in_wait']


    def fade_in_wait_state(self):
        #_debug_('fade_in_wait_state()')
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        if self.counter == 0:
            self.counter = self.fade_counter
            self.state = self.fade_machine['fade_in']


    def fade_in_state(self):
        #_debug_('fade_in_state()')
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.fade_counter, self.counter)
        if self.counter == 0:
            self.counter = self.fade_out_wait_counter
            self.state = self.fade_machine['fade_out_wait']


    def fade_out_wait_state(self):
        #_debug_('fade_out_wait_state()')
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        if self.counter == 0:
            self.counter = self.fade_counter
            self.state = self.fade_machine['fade_out']


    def fade_out_state(self):
        #_debug_('fade_out_state()')
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.counter, 0)
        if self.counter == 0:
            self.counter = self.fade_in_wait_counter
            self.state = self.fade_machine['fade_in_wait']


    def goom_surface_update(self):
        """
        The timer handler
        Uses a state machine to control the display of the cover image
        """
        #_debug_('goom_surface_update()')
        try:
            # draw the cover
            if not self.running:
                return False

            if self.mode == MpvMode.FULL:
                if self.message_counter == 0:
                    if self.messages:
                        self.goom.message = '\n'.join(self.messages)
                self.message_counter = (self.message_counter + 1) % config.MPLAYERVIS_MSG_FRAMES


            gooms = self.goom.process()

            # write the goom surface to the display
            if self.mode == MpvMode.FULL:
                zoom = 2 ** config.MPLAYERVIS_FULL_ZOOM
                for i in range(config.MPLAYERVIS_FULL_ZOOM):
                    gooms = transform.scale2x(gooms)
                self.rect.width = gooms.get_width()
                self.rect.height = gooms.get_height()
                #print 'zoom=%r %r rect=%r' % (zoom, range(config.MPLAYERVIS_FULL_ZOOM), self.rect) #DJW
            elif self.mode == MpvMode.DOCK:
                zoom = 2 ** config.MPLAYERVIS_DOCK_ZOOM
                for i in range(config.MPLAYERVIS_DOCK_ZOOM):
                    gooms = transform.scale2x(gooms)
                self.rect.width = gooms.get_width()
                self.rect.height = gooms.get_height()
                #print 'zoom=%r %r rect=%r' % (zoom, range(config.MPLAYERVIS_DOCK_ZOOM), self.rect) #DJW

            if self.showfps:
                self.goom.fps = self.clock.get_fps()
            else:
                self.goom.fps = -1

            if self.coversurf:
                self.state()
                if self.alpha > 0:
                    s, x, y = self.coversurf
                    _debug_('self.alpha=%r' % (self.alpha,), 2)
                    s.set_alpha(self.alpha)
                    _debug_('gooms.blit(s=%r, (x=%r, y=%r))' % (s, x, y), 2)
                    gooms.blit(s, (x, y))

            if self.mode == MpvMode.FULL:
                self.draw_info(gooms)
            osd.putsurface(gooms, self.rect.left, self.rect.top)
            osd.update(self.rect)
            self.clock.tick()

            return True
        except Exception, why:
            traceback.print_exc()
            _debug_(why, DWARNING)


    def poll(self, current_time):
        """
        override to get extra performance
        """
        #_debug_('poll(current_time=%r)' % (current_time,))
        return



class PluginInterface(plugin.Plugin):
    """
    Native mplayer audiovisualization for Freevo.
    Dependant on the pygoom-2k4-0.2.0 module and goom-2k4

    Activate with:
    | plugin.activate('audio.mplayervis')
    | The following can be set in local_conf.py:
    |   MPLAYERVIS_MODE Set the initial mode of the display, 0 is DOCK, 1 is FULL or 2 is NONE
    |   MPLAYERVIS_INIT_COUNTER is the number of steps  before the image fades, should be >= 255
    |   MPLAYERVIS_FADE_IN_WAIT_COUNTER is the number of steps to wait before cover image fades in
    |   MPLAYERVIS_FADE_OUT_WAIT_COUNTER is the number of steps to wait before cover image fades out
    |   MPLAYERVIS_FADE_COUNTER is the number of steps for fade transition
    |   MPLAYERVIS_FADE_STEP is the number of steps per timer loop
    |   MPLAYERVIS_MESSAGE_FMT is a string format for a message
    |     %(a)s : artist
    |     %(l)s : album
    |     %(n)s : trackno
    |     %(t)s : title
    |     %(e)s : elapsed
    |     %(i)s : item.image
    |     %(y)s : year
    |     %(s)s : length

    The number of steps is proportional to time of a fade transition, each step if 1/10 sec

    When activated the following events can be used:
        - DISPLAY changes the view mode
        - SUBTITLE toggles the title on and off
        - LANG toggles the message on and off (not sure if this works)
        - 0-9 selects the visual effect mode
    """
    player = None
    visual = None
    view   = MpvMode.DOCK
    vis_mode = -1
    passed_event = False
    detached = False

    def __init__(self):
        """ Initialist the PluginInterface """
        _debug_('PluginInterface.__init__()')
        plugin.Plugin.__init__(self)
        self._type    = 'mplayer_audio'
        self.app_mode = 'audio'
        self.title    = None
        self.message  = None
        self.infodata = None
        self.message_fmt = config.MPLAYERVIS_MESSAGE_FMT

        # Event for changing between viewmodes
        config.EVENTS['audio']['SUBTITLE'] = Event('DISPLAY_TITLE')   #'l'
        config.EVENTS['audio']['ENTER']    = Event('DISPLAY_MESSAGE') #'a'
        config.EVENTS['audio']['LANG']     = Event('DISPLAY_FPS')     #'ENTER'
        config.EVENTS['audio']['DISPLAY']  = Event('CHANGE_MODE')     #'d'
        config.EVENTS['audio']['+'] = Event('NEXT_VISUAL')
        config.EVENTS['audio']['-'] = Event('CHANGE_VISUAL', arg=-1)
        config.EVENTS['audio']['0'] = Event('CHANGE_VISUAL', arg=0)
        config.EVENTS['audio']['1'] = Event('CHANGE_VISUAL', arg=1)
        config.EVENTS['audio']['2'] = Event('CHANGE_VISUAL', arg=2)
        config.EVENTS['audio']['3'] = Event('CHANGE_VISUAL', arg=3)
        config.EVENTS['audio']['4'] = Event('CHANGE_VISUAL', arg=4)
        config.EVENTS['audio']['5'] = Event('CHANGE_VISUAL', arg=5)
        config.EVENTS['audio']['6'] = Event('CHANGE_VISUAL', arg=6)
        config.EVENTS['audio']['7'] = Event('CHANGE_VISUAL', arg=7)
        config.EVENTS['audio']['8'] = Event('CHANGE_VISUAL', arg=8)
        config.EVENTS['audio']['9'] = Event('CHANGE_VISUAL', arg=9)

        self.plugin_name = 'audio.mplayervis'
        plugin.register(self, self.plugin_name)

        self.view = MpvMode(config.MPLAYERVIS_MODE)
        self.view_func = [self.dock, self.fullscreen, self.noview]
        self.initialised = False
        self.timer = OneShotTimer(self._paused_handler)


    def config(self):
        """
        Define the configuration variables
        """
        _debug_('PluginInterface.config()')
        return [
            ('MPLAYERVIS_MODE', 0, 'Set the initial mode of the display, 0)DOCK, 1)FULL or 2)NOVI'),
            ('MPLAYERVIS_INIT_COUNTER', 255, 'Counter before the image fades, should be >= 255'),
            ('MPLAYERVIS_FADE_IN_WAIT_COUNTER', 150, 'Counter to wait before cover image fade in'),
            ('MPLAYERVIS_FADE_OUT_WAIT_COUNTER', 0, 'Counter to wait before cover image fade out'),
            ('MPLAYERVIS_FADE_COUNTER', 50, 'Counter for fade transition'),
            ('MPLAYERVIS_FADE_STEP', 3, 'Number of steps per timer loop'),
            ('MPLAYERVIS_MESSAGE_FMT', 'Artist: %(a)s\n Album: %(l)s\n Title: %(t)s\n Track: %(n)s\n', \
                'Message format for the message'),
            ('MPLAYERVIS_FULL_GEOMETRY', '%dx%d' % (config.CONF.width, config.CONF.height), 'Full screen geometry'),
            ('MPLAYERVIS_FULL_ZOOM', 1, 'Fullscreen surface is zoomed by 2^ZOOM'),
            ('MPLAYERVIS_DOCK_ZOOM', 1, 'Docked surface is zoomed by 2^ZOOM'),
            ('MPLAYERVIS_FPS', 15, 'Max FPS of visualization'),
            ('MPLAYERVIS_MSG_FRAMES', 1000, 'Number of frames between messages in full-screen mode'),
        ]


    def toggle_view(self):
        """
        Toggle between view modes
        """
        _debug_('toggle_view()')
        self.view += 1

        if not self.visual:
            self.start_visual()
        else:
            self.view_func[self.view]()


    def eventhandler(self, event=None, arg=None):
        """
        eventhandler to simulate hide/show of mpav
        """
        _debug_('mplayervis1.eventhandler(event=%r, arg=%r)' % (event.name, arg))

        if plugin.isevent(event) == 'DETACH':
            PluginInterface.detached = True
            self.stop_visual()

        elif plugin.isevent(event) == 'ATTACH':
            PluginInterface.detached = False
            self.start_visual()

        elif event == PLAY_START:
            if self.player.playerGUI.succession == PlayListSuccession.FIRST:
                self.start_visual()
            else:
                self.resume_visual()
            self.item_info(self.message_fmt)

        elif event == PLAY_END:
            if self.player.playerGUI.succession == PlayListSuccession.LAST:
                self.stop_visual()
            else:
                self.pause_visual()

        elif event == STOP:
            PluginInterface.detached = False
            self.stop_visual()

        elif event == 'CHANGE_MODE':
            self.toggle_view()
            return True

        elif event == 'DISPLAY_FPS':
            if self.visual is not None:
                self.visual.showfps = not self.visual.showfps
            _debug_('showfps=%s' % (self.visual.showfps))
            return True

        elif event == 'DISPLAY_TITLE':
            if not self.title:
                self.title = self.item_info('%(t)s')
            _debug_('title=%s' % (self.title))
            if self.visual is not None:
                self.visual.set_songtitle(self.title)
            return True

        elif event == 'DISPLAY_MESSAGE':
            #self.message = not self.message and self.item_info(self.message_fmt) or ''
            if not self.message:
                self.message = self.item_info(self.message_fmt)
            _debug_('message=%s' % (self.message))
            if self.visual is not None:
                self.visual.set_message(self.message)
            return True

        elif event == 'NEXT_VISUAL':
            PluginInterface.vis_mode += 1
            if PluginInterface.vis_mode > 9: PluginInterface.vis_mode = -1
            _debug_('vis_mode=%s' % (PluginInterface.vis_mode))
            if self.visual is not None:
                self.visual.set_visual(PluginInterface.vis_mode)
                rc.post_event(Event(OSD_MESSAGE, arg=_('FXMODE is %s' % PluginInterface.vis_mode)))
            return True

        elif event == 'CHANGE_VISUAL':
            PluginInterface.vis_mode = event.arg
            if PluginInterface.vis_mode < -1: PluginInterface.vis_mode = -1
            if PluginInterface.vis_mode > 9: PluginInterface.vis_mode = 9
            _debug_('vis_mode=%s' % (PluginInterface.vis_mode))
            if self.visual is not None:
                self.visual.set_visual(PluginInterface.vis_mode)
                rc.post_event(Event(OSD_MESSAGE, arg=_('FXMODE is %s' % PluginInterface.vis_mode)))
            return True

        elif event == OSD_MESSAGE:
            if self.visual is not None: # and self.view == MpvMode.FULL:
                self.visual.set_info(event.arg)
                return True

        if self.passed_event:
            self.passed_event = False
            return False
        self.passed_event = True

        return False


    def _paused_handler(self):
        """
        This is only called if there is only one track to play
        """
        _debug_('_paused_handler')
        #rc.post_event does not seem to work
        #rc.post_event(Event(STOP))
        self.stop_visual()
        # need to redraw the screen some how
        skin.redraw()


    def item_info(self, fmt=None):
        """
        Set the messages that scroll up the screen
        @returns: info about the current playing song
        """
        _debug_('item_info(fmt=%r)' % (fmt,))

        #print('self.item=\n%s' % (pformat(self.item.__dict__),))
        #print('self.item.info=\n%s' % (pformat(self.item.info.__dict__),))
        item     = self.item
        info     = item.info
        image    = item.image
        title    = item.title if hasattr(item, 'title') else info['title'] if 'title' in info else item.name
        artist   = item.artist if hasattr(item, 'artist') else info['artist']
        album    = item.album if hasattr(item, 'album') else info['album']
        trackno  = item.trackno if hasattr(item, 'trackno') else info['trackno']
        trackof  = item.trackof if hasattr(item, 'trackof') else info['trackof']
        year     = item.userdate if hasattr(item, 'userdate') else info['userdate'] if 'userdate' in info \
            else info['year']
        genre    = item.genre if hasattr(item, 'genre') else item['genre']
        length   = '%i:%02i' % (int(item.length/60), int(item.length%60)) if item.length else ''
        elapsed  = '%i:%02i' % (int(item.elapsed/60), int(item.elapsed%60)) if item.elapsed else ''

        song = {
            'i' : image,
            't' : title,
            'a' : artist,
            'l' : album,
            'n' : trackno,
            'N' : trackof,
            'y' : year,
            'g' : genre,
            's' : length,
            'e' : elapsed,
        }
        _debug_('song=\n%s' % (pformat(song),))

        if self.visual is not None:
            self.visual.messages = []
            self.visual.message_counter = 1
            if song['t']:
                self.visual.messages.append(str('%(t)s' % song))
            if song['a']:
                self.visual.messages.append(str('%(a)s' % song))
            if song['l']:
                self.visual.messages.append(str('%(l)s' % song))
            if song['n'] and song['N']:
                self.visual.messages.append(str('%(n)s/%(N)s' % song))
            elif song['n']:
                self.visual.messages.append(str('%(n)s' % song))
            if song['g']:
                self.visual.messages.append(str('%(g)s' % song))
            if song['y']:
                self.visual.messages.append(str('%(y)s' % song))
            # the last line of messages will stay in the middle of the screen
            # this will cause all message to scroll off the top of the screen
            self.visual.messages.append('')

        if not fmt:
            if year:
                fmt = u'%(a)s : %(l)s  %(n)s.  %(t)s (%(y)s)   [%(s)s]'
            else:
                fmt = u'%(a)s : %(l)s  %(n)s.  %(t)s [%(s)s]'

        result = ''
        try:
            result = fmt % song
        except Exception, why:
            traceback.print_exc()
            _debug_(why, DERROR)
        _debug_('item_info: result=%r' % (result,))
        return result


    def dock(self):
        _debug_('dock()')
        self.visual.mode = MpvMode.DOCK

        if rc.app() != self.player.eventhandler:
            rc.app(self.player)

        self.visual.set_dock()
        if not self.player.playerGUI.visible:
            osd.active = True
            skin.resume()
            self.player.playerGUI.show()


    def fullscreen(self):
        _debug_('fullscreen()')
        self.visual.mode = MpvMode.FULL

        if self.player.playerGUI.visible:
            self.player.playerGUI.hide()
            osd.active = False

        self.visual.set_fullscreen()
        skin.clear()
        skin.suspend()
        rc.app(self)


    def noview(self):
        _debug_('noview()')

        self.visual.mode = MpvMode.NOVI

        if rc.app() != self.player.eventhandler:
            rc.app(self.player)

        if self.visual is not None:
            self.stop_visual()

        if not self.player.playerGUI.visible:
            osd.active = True
            skin.resume()
            self.player.playerGUI.show()


    def start_visual(self):
        _debug_('%s.start_visual() self.view=%r self.succession=%r' % (self.__class__,
            self.view, self.player.playerGUI.succession))
        #if self.player.playerGUI.succession != PlayListSuccession.FIRST:
        #    return

        self.timer.stop()

        if self.visual is not None and self.visual.running:
            return

        if self.view == MpvMode.NOVI:
            return

        if rc.app() == self.player.eventhandler:
            title = self.item.title if hasattr(self.item, 'title') and self.item.title else self.item.name
            self.visual = MpvGoom(300, 300, 150, 150, title, self.item.image)
            if self.visual is None:
                raise Exception('Cannot initialise MpvGoom')

            #if self.view == MpvMode.FULL:
            self.visual.set_info(self.item.name, 10)
            self.title = None
            self.message = None

            _debug_('self.visual.running=%r -> True' % (self.visual.running,))
            self.visual.running = True
            self.view_func[self.view]()
            self.visual.start()
            self.visual.timer.start(1.0 / config.MPLAYERVIS_FPS)
            if self.view == MpvMode.FULL:
                skin.suspend()


    def pause_visual(self):
        _debug_('%s.pause_visual() self.view=%r self.succession=%r' % (self.__class__,
            self.view, self.player.playerGUI.succession))
        self.timer.start(5)


    def resume_visual(self):
        _debug_('%s.resume_visual() self.view=%r self.succession=%r' % (self.__class__,
            self.view, self.player.playerGUI.succession))
        self.timer.stop()
        if self.visual is not None:
            self.title = None
            self.message = None
            if self.view == MpvMode.FULL:
                skin.clear()
        else:
            self.start_visual()


    def stop_visual(self):
        _debug_('%s.stop_visual() self.view=%r self.succession=%r' % (self.__class__,
            self.view, self.player.playerGUI.succession))
        self.timer.stop()
        if self.visual is not None:
            _debug_('self.visual.running=%r -> False' % (self.visual.running,))
            self.visual.timer.stop()
            self.visual.running = False
            self.visual.remove()
            self.visual = None
            self.goom = None
        osd.active = True
        skin.resume()


    def play(self, command, player):
        """
        Play the track
        @param command: mplayer command
        @param player: the player object
        """
        _debug_('%s.play(command=%r, player=%r)' % (self.__class__, command, player))
        self.player = player
        self.item   = player.playerGUI.item
        if self.visual is not None:
            title = self.item.title if hasattr(self.item, 'title') else self.item.name
            self.visual.set_songtitle(title)
            self.visual.set_coverimage(self.item.image)

        #if config.MPLAYERVIS_HAS_TRACK:
        #    return command + [ '-af', 'export=%s' % MMAP_FILE + ',track=5:1500' ]
        return command + [ '-af', 'export=%s' % MMAP_FILE ]


    def stop(self):
        _debug_('%s.stop()' % (self.__class__,))


    def stdout(self, line):
        """
        get information from mplayer stdout

        It should be safe to do call start() from here
        since this is now a callback from main.
        """
        _debug_('stdout(line=%r)' % (line), 2)

        if PluginInterface.detached:
            return

        memory_mapped = False
        if line.find('[export] Memory mapped to file: ' + MMAP_FILE) == 0:
            memory_mapped = True
            _debug_("Detected MPlayer 'export' audio filter! Using MPAV.")

        #if not self.visual.running:
        #    if memory_mapped and not self.visual:
        #        self.start_visual()
        return
