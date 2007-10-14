# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screensaver/balls.py - the Freevo Screensaver
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

from random import randint
import pygame

# freevo modules
import config
from plugins.screensaver import ScreenSaverPlugin


class PluginInterface(ScreenSaverPlugin):
    """
    A bouncing balls screensaver
    """

    def __init__(self):
        ScreenSaverPlugin.__init__(self)
        self.plugin_name = 'screensaver.balls'
        self.fps = config.BALLS_FPS

    def config(self):
        return [ ('BALLS_FPS', 25, 'Frames per second'),
                       ('BALLS_MAX_BALLS', 100, 'Maximum number of balls'),
                       ('BALLS_MIN_BALLS', 1, 'Minimum number of balls')]


    def start(self, width, height):
        self.width = width
        self.height = height
        ballcount = randint(1, 100)
        self.balls = []

        for i in range(0,ballcount):
            ball = Ball()

            ball.name = "ball " + str(i)
            ball.color = (randint(5, 255), randint(5,255), randint(5,255))
            ball.x = randint(0, width - ball.w)
            ball.y = randint(0, height - ball.h)
            ball.w = ball.h = randint(20,40)

            self.balls.append(ball)

        return self.fps

    def draw(self, screen):
        black = (0,0,0)
        dirty = []
        screen.lock()
        for ball in self.balls:
            ball.clear(screen, black)
            dirty.append(ball.rectangle())

        for ball in self.balls:
            ball.update(self.width, self.height, 0.9, 0.9)
            ball.draw(screen)
            dirty.append(ball.rectangle())

        screen.unlock()

class Ball:
    def __init__(self):
        self.name = "ball"
        self.x = 100.0
        self.y = 100.0
        self.w = 40
        self.h = 40
        self.color = (255,0,0)

        self.hspeed = randint(-4,4)
        self.haccel = 0

        self.vspeed = randint(-4,4)
        self.vaccel = 0.7

        self.stopped_count = 0
        self.kick_threshold = 50

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, (int(self.x), int(self.y), self.w, self.h))
        pygame.draw.ellipse(screen, (255,255,255), (int(self.x), int(self.y), self.w, self.h), 1)

    def clear(self, screen, color):
        pygame.draw.ellipse(screen, color, (int(self.x), int(self.y), self.w, self.h))
        pygame.draw.ellipse(screen, color, (int(self.x), int(self.y), self.w, self.h), 1)

    def update(self, width, height, walldeccel, floordeccel):
        # Update ball velocity
        self.hspeed = self.hspeed + self.haccel
        self.vspeed = self.vspeed + self.vaccel

        # Update ball position
        self.x = self.x + self.hspeed
        self.y = self.y + self.vspeed

        if int(self.x + self.w) >= width:
            self.hspeed = (self.hspeed * -1.0) * walldeccel
            self.x = width - self.w
            #self.w = self.w - 2
            #self.h = self.h + 2

        elif int(self.x) <= 0:
            self.hspeed = (self.hspeed * -1.0) * walldeccel
            self.x = 0

        if int(self.y + self.h) >= height:
            self.vspeed = (self.vspeed * -1.0) * floordeccel
            self.y = height - self.h
        elif int(self.y) <= 0:
            self.vspeed = (self.vspeed * -1.0) * floordeccel
            self.y = 0

        # If we loose all speed kick the ball :-)
        if ((self.hspeed < 0.35) and (self.hspeed > -0.35)) or ((self.vspeed < 0.35) and (self.vspeed > -0.35)):
            self.stopped_count = self.stopped_count + 1

            if self.stopped_count > self.kick_threshold:
                kick_drop = True # randint(0,1)

                if kick_drop:
                    if self.hspeed < 0.0:
                        self.hspeed = - randint(5, 20)
                    else:
                        self.hspeed = randint(5, 20)

                    if self.vspeed < 0.0:
                        self.vspeed = -randint(5, 20)
                    else:
                        self.vspeed = randint(5, 20)

                else:
                    self.y = randint(0, height / 2)

                # Reset stopped count
                self.stopped_count = 0
        else:
            self.stopped_count = 0

    def rectangle(self):
        return (int(self.x), int(self.y), self.w, self.h)
