# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Native Freevo MPlayer Audio Visualization Plugin
# -----------------------------------------------------------------------
# $Id$
#
# Notes: - I'm no fan of all the skin.clear() being done :(
# Todo:  -
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
try:
    import pygoom
except:
    raise Exception('[audio.mplayervis]: Pygoom not available, please install '+
                    'or remove this plugin (http://freevo.sf.net/pygoom).')

if not hasattr(pygoom, 'HEXVERSION') and pygoom.HEXVERSION < 0x000200f0:
    raise Exception('pygoom too old, you need version 0.2.0 or higher')

# pygame  modules
from pygame import Rect, image, transform, Surface

# kaa modules
from kaa import Timer

# freevo modules
import plugin, config, rc, skin, osd

from event import *
from animation import render, BaseAnimation

from util.benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL

if config.DEBUG_DEBUGGER:
    import pdb, pprint, traceback

mmap_file = '/tmp/mpav'
skin = skin.get_singleton()
osd  = osd.get_singleton()


class MpvGoom(BaseAnimation):
    """
    Class to interface with the pygoom module
    """
    message    = None
    coversurf  = None

    @benchmark(benchmarking & 0x100, benchmarkcall)
    def __init__(self, x, y, width, height, title='', coverfile=None):
        """
        Initialise the MPlayer Visualization Goom
        """
        _debug_('MpvGoom.__init__(x=%r y=%r width=%r height=%r coverfile=%r)' % (x, y, width, height, coverfile), 1)
        self.mode = config.MPLAYERVIS_MODE
        self.coverfile = coverfile

        if not os.path.exists(mmap_file):
            f = open(mmap_file, 'w')
            s = str(chr(0)) * 2064
            f.write(s)
            f.close()

        BaseAnimation.__init__(self, (x, y, width, height), fps=100, bg_update=False, bg_redraw=False)
        self.goom = pygoom.PyGoom(width, height, mmap_file, songtitle=title)

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

        self.running = False
        Timer(self.timerhandler).start(1.0 / config.MPLAYERVIS_FPS)
        self.last_time = 0


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def set_cover(self, coverfile):
        """
        Set a blend image to toggle between visual and cover
        Updated when resolution is changed
        """
        _debug_('set_cover(coverfile=%r)' % (coverfile,), 1)
        self.coverfile = coverfile


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def set_visual(self, visual):
        """ pass the visualisation effect to goom """
        _debug_('set_visual(visual=%r)' % (visual,), 1)
        self.goom.fxmode = visual


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def set_message(self, message):
        """ pass the song message to goom """
        _debug_('set_message(message=%r)' % (message,), 1)
        self.goom.message = message


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def set_alpha(self, high, low):
        """ Get the alpha level for a count """
        _debug_('set_alpha(high=%r low=%r)' % (high, low,), 2)
        alpha = self.fader(high, low)
        if alpha < 0:   alpha = 0
        if alpha > 255: alpha = 255
        return alpha


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def set_resolution(self, x, y, width, height, clear=False):
        """ Set the resolution of the goom window """
        _debug_('set_resolution(x=%r, y=%r, width=%r, height=%r, clear=%r)' % (x, y, width, height, clear), 1)
        r = Rect (x, y, width, height)
        if r == self.rect:
            return

        # clear info
        self.info = None

        self.rect = r
        _debug_('self.goom.resolution(width=%r, height=%r)' % (width, height), 1)
        self.goom.resolution(width, height)


        # change the cover if neceserry
        s = None
        if self.coverfile:
            try:
                s = image.load(self.coverfile).convert()
                s.set_colorkey(-1) # make top-left pixel transparent
            except:
                pass
        if s:
            # scale and fit to the rect
            w, h   = s.get_size()
            aspect = float(w)/float(h)

            if aspect < 1.0:
                w = self.rect.width
                h = float(w) / aspect
                x = 0
                y = (self.rect.height - h) / 2
            else:
                h = self.rect.height
                w = float(h) * aspect
                y = 0
                x = (self.rect.width - w)  / 2

            self.coversurf = (transform.scale(s,(w, h)), x, y)
            self.c_timer   = time.time()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def set_fullscreen(self):
        """ Set the mode to full screen """
        _debug_('set_fullscreen()', 1)
        w, h = config.MPLAYERVIS_FULL_GEOMETRY.split('x')
        #w = config.CONF.width-(config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT)
        #w = int(float(w) * config.IMAGEVIEWER_ASPECT)
        #w = config.CONF.width

        w = float(w) / config.IMAGEVIEWER_ASPECT
        w = int(w)
        h = int(h)

        #h = config.CONF.height-(config.OSD_OVERSCAN_TOP+config.OSD_OVERSCAN_BOTTOM)
        #h = int(float(h) * config.IMAGEVIEWER_ASPECT)
        #h = config.CONF.height

        # Centre on display
        x = int(config.CONF.width - w) / 2
        y = int(config.CONF.height - h) / 2
        _debug_('x=%r y=%r w=%r h=%r' % (x, y, w, h), 1)

        if config.MPLAYERVIS_FAST_FULLSCREEN:
            self.set_resolution(x, y, w/2, h/2)
        else:
            self.set_resolution(x, y, w, h)


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def set_info(self, info, timeout=5):
        """
        Pass a info message on to the screen.

        @param info: text to draw
        @param timeout: how long to display
        """
        _debug_('set_info(info=%r, timeout=%r)' % (info, timeout), 1)

        font = skin.get_font('widget')
        w = font.stringsize(info)
        h = font.height
        x = config.OSD_OVERSCAN_LEFT+5
        y = config.OSD_OVERSCAN_TOP+5

        s = Surface((w, h), 0, 32)

        osd.drawstringframed(info, 0, 0, w, h, font, mode='hard', layer=s)

        self.m_timer   = time.time()
        self.m_timeout = timeout
        self.info      = (s, x, y, w, h)


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def init_state(self):
        if self.counter > 0:
            # Initial fade out is twice as fast as normal
            self.counter -= (self.fade_step * 2)
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.counter, 0)
        if self.counter == 0:
            self.counter = self.fade_in_wait_counter
            self.state = self.fade_machine['fade_in_wait']


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def fade_in_wait_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        if self.counter == 0:
            self.counter = self.fade_counter
            self.state = self.fade_machine['fade_in']


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def fade_in_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.fade_counter, self.counter)
        if self.counter == 0:
            self.counter = self.fade_out_wait_counter
            self.state = self.fade_machine['fade_out_wait']


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def fade_out_wait_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        if self.counter == 0:
            self.counter = self.fade_counter
            self.state = self.fade_machine['fade_out']


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def fade_out_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.counter, 0)
        if self.counter == 0:
            self.counter = self.fade_in_wait_counter
            self.state = self.fade_machine['fade_in_wait']


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def timerhandler(self):
        """
        The timer handler
        Uses a state machine
        """
        #_debug_('timerhandler()', 1)
        # draw the cover
        if not self.running:
            return False

        gooms = self.goom.process()
        if self.coversurf:
            self.state()
            if self.alpha > 0:
                s, x, y = self.coversurf
                _debug_('self.alpha=%r' % (self.alpha,), 2)
                s.set_alpha(self.alpha)
                _debug_('gooms.blit(s=%r, (x=%r, y=%r))' % (s, x, y), 2)
                gooms.blit(s, (x, y))

        #if not self.running:
        #    return False

        # draw the info
        if self.info:
            s, x, y, w, h = self.info

            if time.time() - self.m_timer > self.m_timeout:
                self.info = False
                s.fill(0)

            _debug_('gooms.blit(s=%r, (x=%r, y=%r))' % (s, x, y), 2)
            gooms.blit(s, (x, y))

        # write the goom surface to the display
        if self.mode == FULL and config.MPLAYERVIS_FAST_FULLSCREEN:
            gooms = transform.scale2x(gooms)
            self.rect.width = gooms.get_width() * 2
            self.rect.height = gooms.get_height() * 2
        osd.putsurface(gooms, self.rect.left, self.rect.top)
        osd.update(self.rect)

        # write the goom surface to the display
        if hasattr(self, 'lastmode'):
            if self.mode != self.lastmode:
                #print self.lastmode, '->', self.mode, gooms.get_rect(), self.rect
                self.lastmode = self.mode
        else: # first time called
            #print '-1', '->', self.mode, gooms.get_rect(), self.rect
            self.lastmode = self.mode

        return True


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def poll(self, current_time):
        """
        override to get extra performance
        """
        return



### MODE definitions
DOCK = 0 # dock (default)
FULL = 1 # fullscreen
NOVI = 2 # no view

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
    view   = DOCK
    vis_mode = -1
    passed_event = False
    detached = False

    @benchmark(benchmarking & 0x100, benchmarkcall)
    def __init__(self):
        """ Initialist the PluginInterface """
        _debug_('PluginInterface.__init__()', 1)
        plugin.Plugin.__init__(self)
        self._type    = 'mplayer_audio'
        self.app_mode = 'audio'
        self.title    = None
        self.message  = None
        self.info     = None
        self.message_fmt = config.MPLAYERVIS_MESSAGE_FMT

        # Event for changing between viewmodes
        config.EVENTS['audio']['LANG'] = Event('TOGGLE_MESSAGE')   #'a'
        config.EVENTS['audio']['SUBTITLE'] = Event('TOGGLE_TITLE') #'l'
        config.EVENTS['audio']['DISPLAY'] = Event('CHANGE_MODE')   #'d'
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

        self.view = config.MPLAYERVIS_MODE
        self.view_func = [self.dock, self.fullscreen, self.noview]
        self.initialised = False


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def config(self):
        """
        """
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
            ('MPLAYERVIS_FAST_FULLSCREEN', True, 'Fullscreen surface is doubled'),
            ('MPLAYERVIS_FPS', 25, 'Max FPS of visualization'),
            ('MPLAYERVIS_HAS_TRACK', False, 'Set to True if mplayer has -af track patch'),
        ]


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def toggle_view(self):
        """
        Toggle between view modes
        """
        _debug_('toggle_view()', 1)
        self.view += 1
        if self.view > NOVI:
            self.view = DOCK

        if not self.visual:
            self.start_visual()
        else:
            self.view_func[self.view]()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def eventhandler(self, event=None, arg=None):
        """
        eventhandler to simulate hide/show of mpav
        """
        _debug_('eventhandler(event=%r, arg=%r)' % (event.name, arg), 1)

        if plugin.isevent(event) == 'DETACH':
            PluginInterface.detached = True
            self.stop_visual()
        elif plugin.isevent(event) == 'ATTACH':
            PluginInterface.detached = False
            self.start_visual()
        elif event == PLAY_START:
            self.start_visual()
        elif event == PLAY_END:
            self.pause_visual()
        elif event == STOP:
            PluginInterface.detached = False
            self.stop_visual()

        if event == 'CHANGE_MODE':
            self.toggle_view()
            return True

        if event == 'TOGGLE_TITLE':
            self.title = not self.title and self.item.name or ''
            _debug_('title=%s' % (self.title), 1)
            self.visual.set_title(self.title)
            return True

        if event == 'TOGGLE_MESSAGE':
            self.message = not self.message and self.item_info(self.message_fmt) or ''
            _debug_('info=%s' % (self.message), 1)
            self.visual.set_message(self.message)
            return True

        if event == 'NEXT_VISUAL':
            PluginInterface.vis_mode += 1
            if PluginInterface.vis_mode > 9: PluginInterface.vis_mode = -1
            _debug_('vis_mode=%s' % (PluginInterface.vis_mode), 1)
            self.visual.set_visual(PluginInterface.vis_mode)
            rc.post_event(Event(OSD_MESSAGE, arg=_('FXMODE is %s' % PluginInterface.vis_mode)))
            return True

        if event == 'CHANGE_VISUAL':
            PluginInterface.vis_mode = event.arg
            if PluginInterface.vis_mode < -1: PluginInterface.vis_mode = -1
            if PluginInterface.vis_mode > 9: PluginInterface.vis_mode = 9
            _debug_('vis_mode=%s' % (PluginInterface.vis_mode), 1)
            self.visual.set_visual(PluginInterface.vis_mode)
            rc.post_event(Event(OSD_MESSAGE, arg=_('FXMODE is %s' % PluginInterface.vis_mode)))
            return True

        if self.visual and self.view == FULL:
            if event == OSD_MESSAGE:
                self.visual.set_info(event.arg)
                return True
            if self.passed_event:
                self.passed_event = False
                return False
            self.passed_event = True

            if event != PLAY_END:
                return self.player.eventhandler(event)

        return False


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def item_info(self, fmt=None):
        """
        Returns info about the current playing song
        """
        _debug_('item_info(fmt=%r)' % (fmt,), 1)

        if not fmt:
            fmt = u'%(a)s : %(l)s  %(n)s.  %(t)s (%(y)s)   [%(s)s]'

        item     = self.item
        info     = item.info
        image    = item.image
        title    = info['title'] and info['title'] or item.name
        artist   = info['artist']
        album    = info['album']
        trackno  = info['trackno']
        year     = info['year']
        length   = item.length and '%i:%02i' % (int(item.length/60), int(item.length%60)) or ''
        elapsed  = item.elapsed and '%i:%02i' % (int(item.elapsed/60), int(item.elapsed%60)) or ''

        song = {
            'i' : image,
            't' : title,
            'a' : artist,
            'l' : album,
            'n' : trackno,
            'y' : year,
            's' : length,
            'e' : elapsed,
        }
        _debug_('song=%r' % (song,), 2)

        result = ''
        try:
            result = fmt % song
        except Exception, why:
            _debug_(why, DERROR)
        _debug_('item_info: result=%r' % (result,))
        return result


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def dock(self):
        _debug_('dock()', 1)
        self.visual.mode = DOCK

        if rc.app() != self.player.eventhandler:
            rc.app(self.player)

        # get the rect from skin
        #  XXX someone with better knowlegde of the
        #      skin code should take a look at this
        imgarea = skin.areas['view']
        c = imgarea.calc_geometry(imgarea.layout.content, copy_object=True)
        w = c.width   - 2*c.spacing
        h = c.height  - 2*c.spacing
        x = c.x + c.spacing
        y = c.y + c.spacing

        # check if the view-area has a rectangle
        try:
            r = c.types['default'].rectangle
            x -= r.x
            y -= r.y
            w += 2*r.x
            h += 2*r.y
        except:
            pass

        self.visual.set_resolution(x, y, w, h, False)


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def fullscreen(self):
        _debug_('fullscreen()', 1)
        self.visual.mode = FULL

        if self.player.playerGUI.visible:
            self.player.playerGUI.hide()

        self.visual.set_fullscreen()
        self.visual.set_info(self.item_info(), 10)
        skin.clear()
        rc.app(self)


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def noview(self):
        _debug_('noview()', 1)

        self.visual.mode = NOVI

        if rc.app() != self.player.eventhandler:
            rc.app(self.player)

        if self.visual:
            self.stop_visual()

        if not self.player.playerGUI.visible:
            self.player.playerGUI.show()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def start_visual(self):
        _debug_('start_visual()', 1)
        if self.view == NOVI:
            return

        if self.visual:
            if self.visual.running:
                return

        if rc.app() == self.player.eventhandler:
            #if self.visual is None:
            #    self.visual = MpvGoom(300, 300, 150, 150, self.item.image)
            title = hasattr(self.item, 'title') and self.item.title or self.item.name
            self.visual = MpvGoom(300, 300, 150, 150, title, self.item.image)

            if self.view == FULL:
                self.visual.set_info(self.item.name, 10)

            self.view_func[self.view]()
            self.visual.running = True
            self.visual.start()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def pause_visual(self):
        _debug_('pause_visual()', 1)
        if self.visual:
            self.visual.running = False


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def stop_visual(self):
        _debug_('stop_visual()', 1)
        if self.visual:
            self.visual.running = False
            self.visual.remove()
            self.visual = None
            self.goom = None


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def play(self, command, player):
        """
        Play the track
        @param command: mplayer command
        @param player: the player object
        """
        _debug_('play(command=%r, player=%r)' % (command, player), 1)
        self.player = player
        self.item   = player.playerGUI.item

        if config.MPLAYERVIS_HAS_TRACK:
            return command + [ '-af', 'export=%s' % mmap_file + ',track=5:1500' ]
        return command + [ '-af', 'export=%s' % mmap_file ]


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def stop(self):
        _debug_('stop()', 1)
        if self.visual:
            self.visual.running = False


    #@benchmark(benchmarking & 0x100, benchmarkcall)
    def stdout(self, line):
        """
        get information from mplayer stdout

        It should be safe to do call start() from here
        since this is now a callback from main.
        """
        #_debug_('stdout(line=%r)' % (line), 1)
        memory_mapped = False
        if line.find('[export] Memory mapped to file: ' + mmap_file) == 0:
            memory_mapped = True
            _debug_("Detected MPlayer 'export' audio filter! Using MPAV.")

        if PluginInterface.detached:
            return

        if memory_mapped:
            self.start_visual()
            if self.visual:
                self.visual.running = True
