# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screensaver/__init__.py - the Freevo Screensaver
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:
#
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
# ----------------------------------------------------------------------- */


import time
import os
import random
import traceback
import pygame

import config
import plugin
import rc

from event import Event
import osd
import skin

import kaa


osd = osd.get_singleton()
#skin = skin.get_singleton()

class PluginInterface(plugin.DaemonPlugin):
    """
    An inbuilt Freevo Screensaver that requires no other program be installed to
    run.
    This plugin just proves the necessary logic to determine when to launch and
    stop a screensaver, to see some exciting (!?) graphics on the screen while it
    is active you need to activate at least one screensaver child plugin.

    For example
    | plugin.activate('screensaver')
    | plugin.activate('screensaver.balls')
    | plugin.activate('screensaver.bouncing_freevo')

    Would activate and cycle between the balls screensaver and the bouncing
    freevo logo screensaver.

    Use 'freevo plugins -l' to see a list of available ScreenSaverPlugins.
    """

    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        plugin.DaemonPlugin.__init__(self)
        self.event_listener = True
        self.last_event = time.time()
        self.screensaver_showing = False
        self.menuw = None
        self.start_delay = config.SCREENSAVER_DELAY
        self.cycle_time = config.SCREENSAVER_CYCLE_TIME
        self.plugins = None
        self.start_timer = kaa.OneShotTimer(self.start_saver)
        self.dpms_timer = kaa.OneShotTimer(self.enable_dpms)
        self.dpms_enabled = False
        self.timer = None
        _debug_('Screensaver install (delay = %d)' % self.start_delay)


    def config(self):
        _debug_('config()', 2)
        return [
            ('SCREENSAVER_DELAY', 300, '# of seconds to wait to start saver.'),
            ('SCREENSAVER_CYCLE_TIME', 60, '# of seconds to run a screensaver before starting another saver.'),
            ('SCREENSAVER_SCREEN_OFF_DELAY', 3600, '# of seconds screensaver has been active before using DPMS to turn the display off, set to 0 to disable' )
        ]


    def eventhandler(self, event=None, menuw=None, arg=None):
        """
        eventhandler to handle the events. Always return False since we
        are just a listener and really can't send back True.
        """
        _debug_('eventhandler(event=%r, menuw=%r, arg=%r)' % (event.name, menuw, arg), 2)
        if menuw:
            self.menuw = menuw

        if plugin.isevent(event) != 'IDENTIFY_MEDIA':
            self.start_timer.start(self.start_delay)

        if self.screensaver_showing:
            self.stop_saver()
            return True

        return False


    def shutdown(self):
        _debug_('shutdown()', 2)
        self.stop_saver()


    def start_saver(self):
        _debug_('start_saver()', 2)
        if self.screensaver_showing or not skin.active():
            return
        self.screensaver_showing = True
        if self.plugins is None:
            self.plugins = plugin.get('screensaver')
            _debug_('plugins=%r' % (self.plugins))

        osd.screensaver_running = True
        skin.clear()
        self.current_saver = None
        self.index = 0
        plugins_count = len(self.plugins)
        _debug_('found %s screensaver(s)' % plugins_count)
        if config.SCREENSAVER_SCREEN_OFF_DELAY:
            _debug_('Enabling DPMS timer')
            self.dpms_timer.start(config.SCREENSAVER_SCREEN_OFF_DELAY)
        self.__next()


    def stop_saver(self):
        _debug_('stop_saver()', 2)
        if self.timer is not None:
            self.disable_dpms()
            self.dpms_timer.stop()
            self.timer.stop()
            self.screensaver_showing = False
            skin.redraw()
            osd.screensaver_running = False
            osd.update()
            _debug_('Screensaver thread stopped')


    def enable_dpms(self):
        self.dpms_enabled = True
        self.timer.stop()
        osd.clearscreen(osd.COL_BLACK)
        osd.update()
        _debug_('Forced DPMS OFF')
        os.system('xset dpms force off')
    
    def disable_dpms(self):
        self.dpms_enabled = False
        _debug_('Forced DPMS ON')
        os.system('xset dpms force on')

    def __next(self):
        plugins_count = len(self.plugins)
        # No current screensaver so select one of the installed screensaver
        # plugins at random
        # if current_saver is None:
        if plugins_count == 1:
            self.current_saver = self.plugins[0]
        elif plugins_count > 1 and plugins_count <= 4:
            self.current_saver = self.plugins[self.index]
            self.index += 1
            if self.index >= plugins_count:
                self.index = 0
        elif plugins_count > 4:
            self.index = random.randint(0, len(self.plugins) - 1)
            self.current_saver = self.plugins[self.index]

        # No screensaver found just sleep for 200ms
        if self.current_saver is None:
            self.timer = kaa.OneShotTimer(self.__next)
            self.timer.start(0.2)
        else:
            self.__run_screensaver__(self.current_saver)

    def __run_screensaver__(self, screensaver):
        _debug_('__run_screensaver__(screensaver=%r)' % (screensaver.plugin_name,), 2)
        try:
            fps = screensaver.start(osd.width, osd.height)
            time_per_frame = 1.0 / fps
            max_iterations = int(self.cycle_time / time_per_frame)
            iteration = 0

            self.__draw(screensaver, time_per_frame, 0, max_iterations )

        except:
            print 'Screensaver %s crashed!' % screensaver.plugin_name
            traceback.print_exc()
            # Remove the broken screensaver so we don't try to run it again
            self.plugins.remove(screensaver)


    def __draw(self, screensaver, time_per_frame, iteration, max_iterations):
        s = time.time()
        try:
            screensaver.draw(osd.screen)
            pygame.display.flip()
        except:
            iteration = max_iterations
            print 'Screensaver %s crashed!' % screensaver.plugin_name
            traceback.print_exc()
            # Remove the broken screensaver so we don't try to run it again
            self.plugins.remove(screensaver)

        e = time.time()
        t = e - s
        iteration += 1
        if iteration < max_iterations:
            d = time_per_frame - t
            if d < 0.0:
                d = time_per_frame
            self.timer = kaa.OneShotTimer(self.__draw, screensaver, time_per_frame, iteration, max_iterations)
            self.timer.start(d)
        else:
            try:
                screensaver.stop()
            except:
                print 'Screensaver %s crashed when stopping' % screensaver.plugin_name
            osd.clearscreen(osd.COL_BLACK)
            osd.update()
            self.__next()



class ScreenSaverPlugin(plugin.Plugin):
    def __init__(self):
        _debug_('ScreenSaverPlugin.__init__()', 2)
        plugin.Plugin.__init__(self)
        self._type = 'screensaver'


    def start(self, width, height):
        _debug_('start(width=%r, height=%r)' % (width, height), 2)
        """
        Initialise the screensaver before each run.
        Returns the number of frames per second the saver
        wants to run at.
        """
        return 25


    def stop(self):
        _debug_('stop()', 2)
        """
        Deinitialise the screensaver after each run.
        """
        pass


    def draw(self, surface):
        """
        Draw a frame onto the supplied surface called
        every 1/fps seconds (where fps was returned by start())
        """
        _debug_('draw(surface=%r)' % (surface,), 2)
        pass
