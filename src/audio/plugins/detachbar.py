# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Audio DetachBar plug-in
# -----------------------------------------------------------------------
# $Id$
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
Audio DetachBar plug-in

Author: Viggo Fredriksen <viggo@katatonic.org>
"""

# python specific
import time

from kaa import Timer
from kaa import EventHandler

# freevo specific
import config
import skin
import audio.player
import plugin
import rc
from event import *

from benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL
benchmarking = 0
benchmarkcall = False

# barstates
BAR_NOTSET=0            # state not set
BAR_HIDE=1              # timedout, reset and change poll interval
BAR_SHOW=2              # show the bar
BAR_WAIT=3              # wait for new track

def formatstate(state):
    """
    returns state formatted as a string
    """
    return state is None     and 'BAR_NONE' \
        or state == BAR_HIDE and 'BAR_HIDE' \
        or state == BAR_SHOW and 'BAR_SHOW' \
        or state == BAR_WAIT and 'BAR_WAIT' \
        or 'BAR_NOTSET'



class PluginInterface(plugin.DaemonPlugin):
    """
    This plugin enables a small bar showing information about audio being played
    when detached with the detach plugin.

    If the idlebar is loaded and there is enough space left there, this plugin
    will draw itself there, otherwise it will draw at the right bottom of the
    screen.

    A dot (graphvis) diagram of the states the bar has
    dot -Tpng -odetach.png detach.dot

    | digraph finite_state_machine {
    |   rankdir=TB;
    |   size="8,5"
    |   node [shape = doublecircle]; Hide;
    |   node [shape = circle];
    |   { rank = same; "Wait"; "Show"; }
    |   Hide -> Show [ label = "detach(start timer)" ];
    |   Show -> Wait [ label = "play_end" ];
    |   Show -> Hide [ label = "stop(stop timer)" ];
    |   Wait -> Hide [ label = "stop(stop timer)" ];
    |   Show -> Show [ label = "play_start" ];
    |   Wait -> Show [ label = "play_start" ];
    |   Wait -> Hide [ label = "timeout(stop timer)" ];
    | }
    """
    detached = False

    @benchmark(benchmarking & 0x100, benchmarkcall)
    def __init__(self):
        """initialise the DaemonPlugin interface"""
        _debug_('detachbar.PluginInterface.__init__()', 2)
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'audio.detachbar'
        self.player = None
        self.timer = Timer(self._timer_handler)
        self.event = EventHandler(self._event_handler)
        self.event.register()
        self.state = BAR_NOTSET
        self.update(BAR_HIDE)
        # tunables
        self.wait_timeout = 3  # 3 seconds till we hide the bar


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def _event_handler(self, event):
        _debug_('_event_handler(event=%s)' % (event,), 2)
        if plugin.isevent(event) == 'DETACH':
            PluginInterface.detached = True
            self.update(BAR_SHOW)
        elif plugin.isevent(event) == 'ATTACH':
            PluginInterface.detached = False
            self.update(BAR_HIDE)
        elif event == STOP:
            PluginInterface.detached = False
            self.update(BAR_HIDE)
        elif event == BUTTON and event.arg == 'STOP':
            PluginInterface.detached = False
            self.update(BAR_HIDE)
        elif PluginInterface.detached:
            if event == PLAY_START:
                self.update(BAR_SHOW)
            elif event == PLAY_END:
                self.update(BAR_WAIT)


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def _timer_handler(self):
        _debug_('_timer_handler()', 2)
        self.update()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def update(self, state=None):
        """
        update the bar according to bar state
        """
        _debug_('update()', 3)
        if state is not None:
            if state == BAR_SHOW:
                self.show()
                self.timer.start(1.0)
            elif state == BAR_HIDE:
                self.timer.stop()
                self.hide()
            elif state == BAR_WAIT:
                self.time = time.time()
            self.state = state

        if self.state == BAR_SHOW:
            skin.redraw()
        elif self.state == BAR_HIDE:
            skin.redraw()
        elif self.state == BAR_WAIT:
            if self.time and (time.time() - self.time) > self.wait_timeout:
                self.update(BAR_HIDE)


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def show(self):
        """
        used when showing for the first time
        """
        _debug_('show()', 2)
        self.player = audio.player.get()
        if self.player:
            self.getinfo()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def hide(self):
        """
        used when hiding the bar
        """
        _debug_('hide()', 2)
        self.render = []
        self.player = None
        self.time   = None
        self.bar    = None


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def stop(self):
        """
        stops the player, waiting for timeout
        """
        _debug_('stop()', 2)
        #self.state = BAR_WAIT
        #self.time  = time.time()


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def draw(self, (type, object), osd):
        """
        draws the bar
        called from the skin's redraw method
        """
        _debug_('draw((type=%r, object=%r), osd=%r)' % (type, object, osd), 3)
        if self.player is None:
            return

        #if self.state == BAR_WAIT:
        #    # when idle, wait for a new player
        #    if audio.player.get():
        #        self.show()

        #elif self.state == BAR_SHOW:
        #    if self.player and not self.player.running:
        #        # player stopped, we also stop
        #        # and wait for a new one
        #        self.player = None
        #        self.stop()
        #        return

        #    if type == 'player':
        #        # Oops, showing the player again, stop me
        #        self.stop()
        #        self.hide()
        #        return

        font = osd.get_font('detachbar')

        if font == osd.get_font('default'):
            font = osd.get_font('info value')

        self.calculatesizes(osd, font)

        if self.image:
            x = self.x - self.h
            width  = self.w + 70 - 10
        else:
            x = self.x
            width = self.w

        if not self.idlebar:
            y = self.y - 10
            height = self.h
            osd.drawroundbox(x, y, width, height, (0xf0ffffffL, 5, 0xb0000000L, 10))

        if self.image:
            osd.draw_image(self.image, (x+5, self.y, 50, 50))

        y = self.t_y

        for r in self.render:
            osd.write_text(r, font, None, self.t_x, y, self.t_w, self.font_h, 'center', 'center')
            y += self.font_h

        try:
            if self.player.item.length:
                progress = '%s/%s' % (self.formattime(self.player.item.elapsed),
                    self.formattime(self.player.item.length))
            else:
                progress = '%s' % self.formattime(self.player.item.elapsed)
        except AttributeError:
            progress = ''

        osd.write_text(progress, font, None, self.t_x, y, self.t_w, self.font_h, 'center', 'center')


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def getinfo(self):
        """
        sets an array of things to draw
        """
        _debug_('getinfo()', 2)
        self.render = []
        self.calculate = True
        info = self.player.item.info

        self.image = self.player.item.image
        # artist : album
        if info['artist'] and info['album']:
            self.render += [ '%s : %s' % (info['artist'], info['album']) ]
        elif info['album']:
            self.render += [ info['album'] ]
        elif info['artist']:
            self.render += [ info['artist'] ]

        # trackno - title
        if info['trackno'] and info['title']:
            self.render += [ '%s - %s' % (info['trackno'], info['title'] ) ]
        elif info['title']:
            self.render += [ info['title'] ]

        # no info available
        if len(self.render) == 0:
            self.render += [ self.player.item.name ]


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def calculatesizes(self, osd, font):
        """
        sizecalcs is not necessery on every pass
        """
        _debug_('calculatesizes(osd=%r, font=%r)' % (osd, font), 3)
        if not hasattr(self, 'idlebar'):
            self.idlebar = plugin.getbyname('idlebar')
            if self.idlebar:
                self.idlebar_max = osd.width + osd.x
                for p in plugin.get('idlebar'):
                    if hasattr(p, 'clock_left_position'):
                        self.idlebar_max = p.clock_left_position

                if self.idlebar_max - self.idlebar.free_space < 250:
                    _debug_('free space in idlebar to small, using normal detach', DINFO)
                    self.idlebar = None


        pad_internal = 5 # internal padding for box vs text

        if self.calculate:
            self.calculate = False
            self.font_h = font.font.height

            total_width = osd.width + 2*osd.x
            total_height = osd.height + 2*osd.y
            pad = 10 # padding for safety (overscan may not be 100% correct)
            bar_height = self.font_h
            bar_width = 0

            for r in self.render:
                bar_height += self.font_h
                bar_width = max(bar_width, font.font.stringsize(r))

            y = total_height - bar_height - config.OSD_OVERSCAN_BOTTOM - skin.attr_global_dict['buttonbar_height']
            x = total_width - bar_width - config.OSD_OVERSCAN_RIGHT
            self.y = y - osd.y - pad - pad_internal
            self.x = x - osd.x - pad - pad_internal
            self.w = bar_width + pad + pad_internal + 10
            self.h = 70
            self.t_y = self.y + pad_internal
            self.t_x = self.x + pad_internal
            self.t_w = bar_width + 5 # in case of shadow

        if self.idlebar:
            self.y = osd.y + 5
            self.x = self.image and self.idlebar.free_space + 70 or self.idlebar.free_space
            self.t_y = self.y
            self.t_x = self.x
            self.t_w = min(self.t_w, self.idlebar_max - self.x - 30)


    @benchmark(benchmarking & 0x100, benchmarkcall)
    def formattime(self, seconds):
        """
        returns string formatted as mins:seconds
        """
        _debug_('formattime(seconds=%r)' % (seconds,), 3)
        try:
            mins = 0
            mins = int(seconds) / 60
            secs = int(seconds) % 60
        except ValueError:
            return ''

        if secs<10:
            secs = '0%s' % secs
        else:
            secs = '%s' % secs
        return '%i:%s' % (mins, secs)
