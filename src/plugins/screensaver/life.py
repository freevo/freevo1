# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screensaver/life.py - the Freevo Screensaver
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
import logging
logger = logging.getLogger("freevo.plugins.screensaver.life")

from random import randint
import pygame

# freevo modules
import config
import osd
from plugins.screensaver import ScreenSaverPlugin
import time
osd = osd.get_singleton()
#   Current Next
STATE_DEAD_DEAD   = 0
STATE_DEAD_ALIVE  = 1
STATE_ALIVE_DEAD  = 2
STATE_ALIVE_ALIVE = 3

CURRENTLY_ALIVE = 2

class PluginInterface(ScreenSaverPlugin):
    """
    A Life game screensaver
    """
    def __init__(self):
        logger.log( 9, 'PluginInterface.__init__()')
        ScreenSaverPlugin.__init__(self)
        self.plugin_name = 'screensaver.life'
        self.fps = config.LIFE_FPS
        self.cells = []
        self.cell_w = 0
        self.cell_h = 0
        self.step = False

    def config(self):
        logger.log( 9, 'config()')
        return [
            ('LIFE_FPS', 20, 'Frames per second'),
            ('LIFE_CELL_SIZE', 20, 'Size in pixels of each cell'),
        ]


    def start(self, width, height):
        logger.log( 9, 'start(width=%r, height=%r)', width, height)
        self.width = width
        self.height = height
        cell_w = width / config.LIFE_CELL_SIZE
        cell_h = height / config.LIFE_CELL_SIZE
        self.x_offset = (width - (cell_w * config.LIFE_CELL_SIZE)) / 2
        self.y_offset = (height - (cell_h * config.LIFE_CELL_SIZE)) / 2



        self.cells = [STATE_DEAD_DEAD] * (cell_w * cell_h)
        self.cell_w = cell_w
        self.cell_h = cell_h

        self.init_cells()

        return self.fps


    def draw(self, screen):
        black = (0,0,0)
        dirty = []
        osd.mutex.acquire()
        try:

            black = (0,0,0)
            dirty = []
            # Clear the old image
            screen.lock()
            screen.fill(black)
            live_cells = False
            for y in xrange(0, self.cell_h):
                for x in xrange(0, self.cell_w):

                    state = self.get_cell_state(x,y)
                    draw = False
                    if state == STATE_DEAD_ALIVE:
                        color = (0,255,0)
                        next_state = STATE_ALIVE_ALIVE
                        live_cells = True
                        draw = True

                    elif state == STATE_ALIVE_ALIVE:
                        color = (255,255,0)
                        next_state = STATE_ALIVE_ALIVE
                        live_cells = True
                        draw = True

                    elif state == STATE_ALIVE_DEAD:
                        color = (255,0,0)
                        next_state = STATE_DEAD_DEAD
                        draw = True
                    else:
                        color = (0,0,0)
                        next_state = STATE_DEAD_DEAD
                        draw = False

                    if draw:
                        screen.fill(color, (self.x_offset + (x * config.LIFE_CELL_SIZE), self.y_offset + (y * config.LIFE_CELL_SIZE), config.LIFE_CELL_SIZE, config.LIFE_CELL_SIZE))

                    if not self.step:
                        self.set_cell_state(x,y, next_state)

            if self.step:
                self.step_cells()
                self.step = False
            else:
                if live_cells:
                    self.step = True
                else:
                    self.init_cells()

            screen.unlock()
        finally:
            osd.mutex.release()

    def init_cells(self):
        livecellcount = randint((self.cell_w * self.cell_h)/10, (self.cell_w * self.cell_h)/4)
        count = 0
        while count < livecellcount:
            x = randint(0, self.cell_w - 1)
            y = randint(0, self.cell_h - 1)

            state = self.get_cell_state(x,y)

            if state == STATE_DEAD_DEAD:
                count += 1
                self.set_cell_state(x, y, STATE_DEAD_ALIVE)


    def step_cells(self):
        for y in xrange(0, self.cell_h):
            for x in xrange(0, self.cell_w):
                cell_count = 0
                if self.get_cell_state(x - 1, y - 1) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x, y - 1) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x + 1, y - 1) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x - 1, y) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x + 1, y) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x - 1, y + 1) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x, y + 1) & CURRENTLY_ALIVE:
                    cell_count += 1
                if self.get_cell_state(x + 1, y + 1) & CURRENTLY_ALIVE:
                    cell_count += 1

                state = self.get_cell_state(x,y)
                next_state = state

                if cell_count == 3 and state == STATE_DEAD_DEAD:
                    next_state = STATE_DEAD_ALIVE
                elif (cell_count < 2 or cell_count > 3) and state == STATE_ALIVE_ALIVE:
                    next_state = STATE_ALIVE_DEAD

                self.set_cell_state(x,y, next_state)

    def get_cell_state(self, x, y):
        if x < 0 or x >= self.cell_w:
            return STATE_DEAD_DEAD
        if y < 0 or y >= self.cell_h:
            return STATE_DEAD_DEAD
        return self.cells[(y * self.cell_w) + x]

    def set_cell_state(self, x, y, state):
        self.cells[(y * self.cell_w) + x] = state
