# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Native Freevo MPlayer Audio Visualization Plugin
# -----------------------------------------------------------------------
# $Id$
#
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

__author__           = 'Viggo Fredriksen'
__author_email__     = 'viggo@katatonic.org'
__maintainer__       = 'Gorka Olaizola'
__maintainer_email__ = 'gorka@escomposlinux.org'

try:
    import pygoom
except:
    raise Exception('[audio.mplayervis]: Pygoom not available, please install '+
                    'or remove this plugin (http://freevo.sf.net/pygoom).')


# pygame  modules
import pygame

# freevo modules
import plugin, config, rc, skin, osd

import os, childapp, kaa, re

from event import *
from animation import render, BaseAnimation

mmap_file = '/tmp/mpav.%s' % os.getpid()
skin = skin.get_singleton()
osd  = osd.get_singleton()


class MpvGoom(BaseAnimation):
    """
    Class to interface with the pygoom module
    """
    message    = None
    coversurf  = None

    def __init__(self, x, y, width, height, coverfile=None):
        """ Initialise the MPlayer Visualization Goom """
        _debug_('MpvGoom.__init__(x=%r y=%r width=%r height=%r coverfile=%r)' % (x, y, width, height, coverfile), 2)
        self.coverfile = coverfile

        self.mplayer = None

        BaseAnimation.__init__(self, (x, y, width, height), fps=100, bg_update=False, bg_redraw=False)
        _debug_('pygoom.set_exportfile(mmap_file=%r)' % (mmap_file), 2)
        pygoom.set_exportfile(mmap_file)
        _debug_('pygoom.set_resolution(width=%r, height=%r, 0)' % (width, height), 2)
        pygoom.set_resolution(width, height, 0)
        if int(config.MPLAYERVIS_FPS) != 25:
            pygoom.set_fps(config.MPLAYERVIS_FPS)

        self.vis_sizes = {
            '4:3': {
                'small' : { 'w': 320, 'h': 240 },
                'medium': { 'w': 640, 'h': 480 },
                'large' : { 'w': 800, 'h': 600 }
            },
            '16:9': {
                'small' : { 'w': 320, 'h': 180 },
                'medium': { 'w': 640, 'h': 360 },
                'large' : { 'w': 800, 'h': 450 }
            },
        }

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

        self.bmovl_filename = '/tmp/bmovl.%s' % os.getpid()
        self.bmovl_file = None

        self.info = None

        self.running = True

        self.gooms = None

        self.current_view = config.MPLAYERVIS_MODE

        self.clock = pygame.time.Clock()

        self.alpha_start    = 192
        self.alpha_step     = 38
        self.alpha_current  = self.alpha_start

    def set_cover(self, coverfile):
        """
        Set a blend image to toggle between visual and cover
        Updated when resolution is changed
        """
        _debug_('set_cover(coverfile=%r)' % (coverfile,), 1)
        self.coverfile = coverfile


    def set_visual(self, visual):
        """ pass the visualisation effect to pygoom """
        _debug_('set_visual(visual=%r)' % (visual,), 1)
        pygoom.set_visual(visual)


    def set_title(self, title):
        """ pass the song title to pygoom """
        _debug_('set_title(title)=%r' % (title,), 1)
        pygoom.set_title(title)


    def set_message(self, message):
        """ pass the song message to pygoom """
        _debug_('set_message(message=%r)' % (message,), 1)
        pygoom.set_message(message)


    def set_alpha(self, high, low):
        """ Get the alpha level for a count """
        _debug_('set_alpha(high=%r low=%r)' % (high, low,), 2)
        alpha = self.fader(high, low)
        if alpha < 0:   alpha = 0
        if alpha > 255: alpha = 255
        return alpha


    def set_resolution(self, x, y, width, height, cinemascope=0, clear=False):
        """ Set the resolution of the pygoom window """
        _debug_('set_resolution(x=%r, y=%r, width=%r, height=%r, cinemascope=%r, clear=%r)' % \
            (x, y, width, height, cinemascope, clear), 1)
        r = pygame.Rect (x, y, width, height)
        if r == self.rect:
            return

        # clear info
        self.info = None

        self.rect = r
        _debug_('pygoom.set_resolution(width=%r, height=%r, cinemascope=%r)' % (width, height, cinemascope), 2)
        pygoom.set_resolution(width, height, cinemascope)
        self.gooms = pygoom.get_surface()

        # change the cover if neceserry
        s = None
        if self.coverfile:
            try:
                s = pygame.image.load(self.coverfile).convert()
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

            self.coversurf = (pygame.transform.scale(s,(w, h)), x, y)


    def set_fullscreen(self):
        """ Set the mode to full screen """
        _debug_('set_fullscreen()', 1)

        if config.MPLAYERVIS_FULL_SCALING_MODE == 'mplayer':
            self.set_fullscreen_mplayer_scaling()

        else:
            self.set_fullscreen_software_scaling(config.MPLAYERVIS_FULL_SOFTWARE_SCALING_DIVISOR)


    def set_fullscreen_software_scaling(self, divisor=1):
        w, h = config.MPLAYERVIS_FULL_SOFTWARE_GEOMETRY.split('x')

        w = float(w) / config.IMAGEVIEWER_ASPECT
        w = int(w)
        h = int(h)

        # Centre on display
        x = int(config.CONF.width - w) / 2
        y = int(config.CONF.height - h) / 2
        _debug_('software scaling x=%r y=%r w=%r h=%r divisor=%r' % (x, y, w, h, divisor), 2)

        self.set_resolution(x, y, int(w/divisor), int(h/divisor), 0)


    def set_fullscreen_mplayer_scaling(self):
        aspect = config.MPLAYERVIS_FULL_MPLAYER_ASPECT
        size = config.MPLAYERVIS_FULL_MPLAYER_SIZE

        w = self.vis_sizes[aspect][size]['w']
        h = self.vis_sizes[aspect][size]['h']

        x = 0
        y = 0

        _debug_('mplayer scaling x=%r y=%r w=%r h=%r' % (x, y, w, h), 2)
        self.set_resolution(x, y, w, h, 0)

        self.close_bmovl()
        self.init_bmovl()

        kaa.Timer(self.start_mplayer).start(1)


    def start_mplayer(self):
        command = self.create_video_command()
        self.mplayer = MPlayerVideoApp(command)

        return False


    def set_info(self, info, timeout=5000):
        """
        Pass a info message on to the screen.

        @param info: text to draw
        @param timeout: how long to display
        """
        _debug_('set_info(info=%r, timeout==%r)' % (info, timeout), 2)

        font = skin.get_font('widget')

        count = info.count('\n') + 1

        x = config.OSD_OVERSCAN_LEFT
        y = config.OSD_OVERSCAN_TOP

        w = self.gooms.get_width() - x
        h = (font.height * count) + font.height

        self.alpha_current = self.alpha_start

        s = pygame.Surface((w, h), pygame.SRCALPHA | pygame.RLEACCEL)
        s.set_alpha(self.alpha_current)

        osd.drawstringframed(info, 0, 0, w, h, font, fgcolor=0xfff5ff00, layer=s, dim=False)

        self.m_timer   = pygame.time.get_ticks()
        self.m_timeout = timeout
        self.m_timeout2 = timeout * 2
        self.info      = (s, x, y, w, h)


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


    def fade_in_wait_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        if self.counter == 0:
            self.counter = self.fade_counter
            self.state = self.fade_machine['fade_in']


    def fade_in_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.fade_counter, self.counter)
        if self.counter == 0:
            self.counter = self.fade_out_wait_counter
            self.state = self.fade_machine['fade_out_wait']


    def fade_out_wait_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        if self.counter == 0:
            self.counter = self.fade_counter
            self.state = self.fade_machine['fade_out']


    def fade_out_state(self):
        if self.counter > 0:
            self.counter -= self.fade_step
        if self.counter < 0:
            self.counter = 0
        self.alpha = self.set_alpha(self.counter, 0)
        if self.counter == 0:
            self.counter = self.fade_in_wait_counter
            self.state = self.fade_machine['fade_in_wait']


    def timerhandler(self):
        """
        The timer handler
        Uses a state machine
        """
        #_debug_('timerhandler()', 2)
        # draw the cover
        if self.current_view == NOVI:
            return True

        if not self.running:
            return self.running

        self.gooms = pygoom.get_surface()

        if self.coversurf:
            self.state()
            if self.alpha > 0:
                s, x, y = self.coversurf
                _debug_('self.alpha=%r' % (self.alpha,), 2)
                s.set_alpha(self.alpha)
                _debug_('self.gooms.blit(s=%r, (x=%r, y=%r))' % (s, x, y), 2)
                self.gooms.blit(s, (x, y))

        # draw the info
        if not self.running:
            return self.running

        if self.info:
            s, x, y, w, h = self.info

            diff = pygame.time.get_ticks() - self.m_timer

            if  diff > self.m_timeout and diff < self.m_timeout2:
                self.alpha_current = self.alpha_current - self.alpha_step

                if self.alpha_current < 0:
                    self.alpha_current = 0

                s.set_alpha(self.alpha_current)

            elif diff > self.m_timeout2:
                self.info = False
                s.fill(0)

            _debug_('self.gooms.blit(s=%r, (x=%r, y=%r))' % (s, x, y), 2)
            y =  self.gooms.get_height() - h - config.OSD_OVERSCAN_BOTTOM
            self.gooms.blit(s, (x, y))

        if self.current_view == DOCK:

            osd.putsurface(self.gooms, self.rect.left, self.rect.top)
            osd.update(self.rect)

            self.clock.tick(config.MPLAYERVIS_FPS) 

#            _debug_('config FPS: %d, Current FPS: %d' % (config.MPLAYERVIS_FPS, self.clock.get_fps()), 2)


        elif self.current_view == FULL:

            if config.MPLAYERVIS_FULL_SCALING_MODE == 'mplayer':
                self.write_bmovl_frame()
            else:
                if config.MPLAYERVIS_FULL_SOFTWARE_SCALING_DIVISOR > 1:
                    gooms = pygame.transform.scale(self.gooms, (config.CONF.width, config.CONF.height))
                    self.rect.width = gooms.get_width()
                    self.rect.height = gooms.get_height()
                else:
                    gooms = self.gooms

                osd.putsurface(gooms, self.rect.left, self.rect.top)
                osd.update(self.rect)

                self.clock.tick(config.MPLAYERVIS_FPS) 



        return self.running


    def poll(self, current_time):
        """
        override to get extra performance
        """
        return


    def write_bmovl_frame(self):

        if self.bmovl_file and self.mplayer and self.mplayer.isAlive():
            try:
                os.write(self.bmovl_file, "RGBA32 %d %d 0 0 0 0\n" % (self.gooms.get_width(), self.gooms.get_height()))
                os.write(self.bmovl_file, pygame.image.tostring(self.gooms, 'RGBA'))
            except OSError, (errno, strerror):
                if self.mplayer:
                    self.mplayer.stop()
                self.close_bmovl()
                _debug_("write_bmovl_frame: %s" % strerror)


    def init_noview(self):
        if config.MPLAYERVIS_FULL_SCALING_MODE == 'mplayer':
            self.stop_fullscreen_mplayer()


    def stop_fullscreen_mplayer(self):
        _debug_('stop_mplayer_fullscreen()', 1)
        if self.mplayer:
            self.mplayer.kill()
            self.mplayer = None

        self.close_bmovl()


    def stop_pygoom(self):
        _debug_('stop_pygoom()', 1)
        pygoom.quit()


    def stop(self):
        _debug_('MPVGoom stop()', 1)
        self.running = False


    @kaa.threaded('bmovl')
    def init_bmovl(self):
        _debug_('init_bmovl()', 1)
        try:
            os.mkfifo(self.bmovl_filename)
        except OSError:
            _debug_('init_bmovl: %s already exists' % self.bmovl_filename)

        self.bmovl_file = os.open(self.bmovl_filename, os.O_WRONLY)


    @kaa.threaded('bmovl')
    def close_bmovl(self):
        _debug_('close_bmovl()', 1)
        if self.bmovl_file:
            os.close(self.bmovl_file)
            os.unlink(self.bmovl_filename)
            self.bmovl_file = None


    def create_video_command(self):

        # Build the MPlayer command
        args = {
            'cmd': config.MPLAYER_CMD,
            'vo': '-vo %s' % config.MPLAYER_VO_DEV,
            'vo_opts': config.MPLAYER_VO_DEV_OPTS,
            'ao': '-ao null',
            'default_args': config.MPLAYER_ARGS_DEF.split(),
            'geometry': '',
            'verbose': '',
            'vf': ['bmovl=0:1:%s' % self.bmovl_filename],
            'url': '%s/mplayervis/freevo-%s-%s.avi' % (config.IMAGE_DIR, config.MPLAYERVIS_FULL_MPLAYER_SIZE, config.MPLAYERVIS_FULL_MPLAYER_ASPECT)
        }

        args['geometry'] = '-geometry %s:%s' % (config.CONF.width, config.CONF.height)

        if config.DEBUG_CHILDAPP:
            args['verbose'] = '-v'

        vo = ['%(vo)s' % args, '%(vo_opts)s' % args]
        vo = filter(len, vo)
        vo = ':'.join(vo)

        command = ['%(cmd)s' % args]
        command += str('%(verbose)s' % args).split()
        command += str('%(geometry)s' % args).split()
        command += vo.split()
        command += str('%(ao)s' % args).split()
        command += args['default_args']
        command += ['-vf', '%s' % ','.join(args['vf'])]
        command += ['-osdlevel', '0']
        command += ['-fs']
        command += ['-slave']

        # use software scaler?
        if '-nosws' in command:
            command.remove('-nosws')
        elif '-framedrop' not in command:
            command += config.MPLAYER_SOFTWARE_SCALER.split()

        command = filter(len, command)

        command += ['%(url)s' % args]

        return command

    def start_timer(self):
        kaa.Timer(self.timerhandler).start(float(1 / config.MPLAYERVIS_FPS))

        return False


### MODE definitions
DOCK = 0 # dock (default)
FULL = 1 # fullscreen
NOVI = 2 # no view

class PluginInterface(plugin.Plugin):
    """
    Native mplayer audiovisualization for Freevo.
    Dependant on the pygoom-2k4 module and goom-2k4

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
    |
    |   MPLAYERVIS_FPS is the number of Frame per seconds to display
    |   MPLAYERVIS_FULL_SCALING_MODE is a string with the mode for scaling fullscreen. Must be one of 'mplayer' or 'software'.
    |   MPLAYERVIS_FULL_SOFTWARE_GEOMETRY is a string (WIDTH x HEIGHT) to scale the visualization area to
    |   MPLAYER_FULL_SOFTWARE_SCALING_DIVISOR is a number to divide the screen size and calculate the visualization area size
    |   MPLAYERVIS_FULL_MPLAYER_SIZE is a string with the size of the visualization area. Must be one of 'small' or 'medium'
    |   'MPLAYERVIS_FULL_MPLAYER_ASPECT is a string with the aspect ratio of the screen. Must be one of '4:3' or '16:9

    When activated the following events can be used:
        - DISPLAY changes the view mode
        - SUBTITLE toggles the title on and off
        - LANG toggles the message on and off (not sure if this works)
        - 0-9 selects the visual effect mode
    """

    player = None
    passed_event = False
    detached = False
    vis_mode = -1

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

        self.visual = None


    def config(self):
        """ """
        fps = 25

        return [
            ('MPLAYERVIS_MODE', 0, 'Set the initial mode of the display, 0)DOCK, 1)FULL or 2)NOVI'),
            ('MPLAYERVIS_FPS', fps, 'Max FPS of visualization. Fullscreen mode is limited to 25 fps'),
            ('MPLAYERVIS_INIT_COUNTER', 255, 'Counter before the image fades, should be >= 255'),
            ('MPLAYERVIS_FADE_IN_WAIT_COUNTER', int(7.5 * fps), 'Counter to wait before cover image fade in'),
            ('MPLAYERVIS_FADE_OUT_WAIT_COUNTER', 0, 'Counter to wait before cover image fade out'),
            ('MPLAYERVIS_FADE_COUNTER', int(2.5 * fps), 'Counter for fade transition'),
            ('MPLAYERVIS_FADE_STEP', int(0.15 * fps), 'Number of steps per timer loop'),
            ('MPLAYERVIS_MESSAGE_FMT', u'Artist: %(a)s\nAlbum: %(l)s\nTitle: %(t)s\nTrack: %(n)s\nLength: %(s)s', \
                'Message format for the message'),
            ('MPLAYERVIS_FULL_SCALING_MODE', 'mplayer', "Fullscreen mode for scaling visualization area. Must be one of 'mplayer' or 'software'"),

            ('MPLAYERVIS_FULL_SOFTWARE_GEOMETRY', '%dx%d' % (config.CONF.width, config.CONF.height), 'Full screen geometry in soft mode. If smaller than real screen size it centers the visualization area'),
            ('MPLAYER_FULL_SOFTWARE_SCALING_DIVISOR', 2, "Used to set the size of the visualization area. 2 means to use half the size of the full screen"),
            ('MPLAYERVIS_FULL_MPLAYER_SIZE', 'medium', "Resolution of the visualization area in fullscreen mode. Must be 'small' or 'medium'"),
            ('MPLAYERVIS_FULL_MPLAYER_ASPECT', '4:3', "Aspect ratio of the visualization widget in fullscreen mode.. Must be one of '4:3' or '16:9'")
        ]


    def play(self, command, player):
        """
        Play it
        """
        _debug_('play(command, player)', 1)
        self.player = player
        self.item   = player.playerGUI.item
        self.menuw  = player.playerGUI.menuw

        return command + [ "-af", "export=" + mmap_file ]


    def toggle_view(self):
        """
        Toggle between view modes
        """
        _debug_('toggle_view()', 1)
        self.view += 1
        if self.view > NOVI:
            self.view = DOCK

        self.view_func[self.view]()


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
        elif event == STOP:
            PluginInterface.detached = False

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

        if event == STOP:
            if self.view == FULL and config.MPLAYERVIS_FULL_SCALING_MODE == 'software':
                rc.post_event(STOP) 

            self.stop_all()

            return False

        if event == PLAY_END:
            menu = self.menuw.menustack[-1]

            if self.item == menu.choices[-1]:
                self.stop_all()

            return False

        if event == 'MPLAYERVIS_FULL_MPLAYER_END':
            if self.view == FULL:
                rc.post_event(STOP)

            rc.app(self.player)

            return True

        if self.visual and self.view == FULL:
            if event == PLAY_START:
                self.init_fullscreen()
                self.visual.set_info(self.item_info(self.message_fmt))

                return False

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


    def item_info(self, fmt=None):
        """
        Returns info about the current running song
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
        _debug_('song=%r' % (song,), 1)

        result = ''
        try:
            result = fmt % song
        except Exception, why:
            _debug_(why, DERROR)
        _debug_('item_info: result=%r' % (result,))
        return result


    def dock(self):
        _debug_('dock()', 1)

        self.visual.current_view = DOCK

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

        self.visual.set_resolution(x, y, w, h, 0, False)


    def init_fullscreen(self):
        if self.player.playerGUI.visible:
            self.player.playerGUI.hide()

        skin.clear()
        rc.app(self)


    def fullscreen(self):
        _debug_('fullscreen()', 1)

        self.init_fullscreen()

        if self.visual:
            self.visual.current_view = FULL
            self.visual.set_fullscreen()


    def noview(self):
        _debug_('noview()', 1)

        if rc.app() != self.player.eventhandler:
            rc.app(self.player)

        if self.visual:
            self.visual.current_view = NOVI
            self.visual.init_noview()

        if not self.player.playerGUI.visible:
            self.player.playerGUI.show()


    def start_visual(self):
        _debug_('start_visual()', 1)

        self.visual = MpvGoom(300, 300, 150, 150, self.item.image)

        self.view_func[self.view]()

        kaa.OneShotTimer(self.visual.start_timer).start(1)

        if self.view == FULL:
            self.visual.set_info(self.item_info(self.message_fmt))


    def restart_visual(self):
        _debug_('restart_visual()', 1)
        if self.visual:
            if not self.visual.running:
                self.visual.running = True

                self.visual.start_timer()

                if self.view == FULL:

                    if self.visual.mplayer and not self.visual.mplayer.isAlive():
                        self.fullscreen()

            else:
                _debug_('Not restarting. Visual already running', 1)


    def stop_visual(self):
        _debug_('stop_visual()', 1)
        if self.visual:
            self.visual.stop()

            if rc.app() != self.player.eventhandler:
                rc.app(self.player)


    def stop(self):
        _debug_('stop()', 1)
        self.stop_visual()


    def stop_all(self):
        _debug_('stop_all()', 1)
        if self.visual:
            self.visual.stop()

            if self.view == FULL and config.MPLAYERVIS_FULL_SCALING_MODE == 'mplayer':
                self.visual.stop_fullscreen_mplayer()

            self.visual.stop_pygoom()
            self.visual = None

        if not self.player.playerGUI.visible:
            self.player.playerGUI.show()

        return False



    def stdout(self, line):
        """
        get information from mplayer stdout

        It should be safe to do call start() from here
        since this is now a callback from main.
        """
        #_debug_('stdout(line=%r)' % (line), 2)

        if PluginInterface.detached:
            return

        if line.find("[export] Memory mapped to file: " + mmap_file) == 0:
            _debug_("Detected MPlayer 'export' audio filter! Using MPAV.")
            if self.visual:
                self.restart_visual()
            else:
                self.start_visual()


class MPlayerVideoApp(childapp.ChildApp):
    """
    class controlling the in and output from the mplayer process
    """

    def __init__(self, command):
        self.exit_type = None

        self.RE_EXIT   = re.compile("^Exiting\.\.\. \((.*)\)$").match

        rc.register(self.poll, True, 10)
        kaa.Timer(self.rewind_player).start(5)
        childapp.ChildApp.__init__(self, command)

    def rewind_player(self):
        if self.isAlive():
            self.write('seek 0 2\n')


    def poll(self):
        """
        stop everything when child is dead
        """
        _debug_('MPlayerVideoApp.poll()', 3)
        if not self.isAlive():
            self.stop()


    def stop(self):
        kaa.Timer(self.rewind_player).stop()
        rc.unregister(self.poll)

        ev = Event('MPLAYERVIS_FULL_MPLAYER_END')

        rc.post_event(ev)


    def stdout_cb(self, line):
        """
        parse the stdout of the mplayer process
        """

        # exit status
        if line.find("Exiting...") == 0:
            m = self.RE_EXIT(line)
            if m:
                self.exit_type = m.group(1)
