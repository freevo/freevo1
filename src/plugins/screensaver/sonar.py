# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screensaver/sonar.py - the Freevo Screensaver
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
logger = logging.getLogger("freevo.plugins.screensaver.sonar")

import random
import math
import pygame

# freevo modules
import config
import osd
from plugins.screensaver import ScreenSaverPlugin

osd = osd.get_singleton()

class PluginInterface(ScreenSaverPlugin):
    """
    A Sonar like screensaver
    """
    def __init__(self):
        logger.log( 9, 'PluginInterface.__init__()')
        ScreenSaverPlugin.__init__(self)
        self.plugin_name = 'screensaver.sonar'
        self.fps = config.SONAR_FPS

    def config(self):
        logger.log( 9, 'config()')
        return [
            ('SONAR_FPS', 25, 'Frames per second'),
            ('SONAR_MAX_CONTACTS', 100, 'Maximum number of contacts'),
            ('SONAR_MIN_CONTACTS', 1, 'Minimum number of contacts'),
        ]


    def start(self, width, height):
        logger.log( 9, 'start(width=%r, height=%r)', width, height)
        self.width = width
        self.height = height
        
        
        diameter = min(width, height) - 10
        self.radius = diameter / 2
        self.center_pos = (width / 2, height /2)
        self.sonar_color = (85,255,0, 255)

        self.age_colors = []
        self.max_age = 20
        for i in xrange(0,self.max_age):
            color = pygame.color.Color(*self.sonar_color)
            hsla = color.hsla
            color.hsla = (hsla[0], (hsla[1] *(self.max_age - i)) / self.max_age, (hsla[2] * (self.max_age - i)) / self.max_age, hsla[3])
            self.age_colors.append(color)

        
        self.outside_pos = []
        self.degrees_sin = []
        self.degrees_negcos = []
        self.degrees = 0
        for i in xrange(0, 360):
            r = math.radians(i)
            self.degrees_sin.append(math.sin(r))
            self.degrees_negcos.append(-math.cos(r))
            self.outside_pos.append((int(self.center_pos[0] + self.radius * self.degrees_sin[i]),
                                int(self.center_pos[1] + self.radius * self.degrees_negcos[i])))


        self.contacts = []
        for i in xrange(0, random.randint(1,20)):
            self.contacts.append((random.randint(0,359), random.randint(5, self.radius)))
        return self.fps


    def draw(self, screen):
        black = (0,0,0)
        osd.mutex.acquire()
        try:
            screen.lock()
            screen.fill(black)
            for age in xrange(self.max_age - 1, 0, -1):
                pygame.draw.polygon(screen, self.age_colors[age], [self.center_pos,
                                                                   self.outside_pos[self.degrees - age],
                                                                   self.outside_pos[self.degrees - age + 1],
                                                                   self.center_pos])

            pygame.draw.line(screen, self.age_colors[0], self.center_pos, self.outside_pos[self.degrees], 2)

            for contact_angle, contact_distance in self.contacts:
                age = (self.degrees - contact_angle) / (360/self.max_age)
                if age < 0:
                    age += self.max_age
                contact_pos = (int(self.center_pos[0] + contact_distance * self.degrees_sin[contact_angle]),
                                int(self.center_pos[1] + contact_distance * self.degrees_negcos[contact_angle]))
                pygame.draw.circle(screen, self.age_colors[age], contact_pos, (self.max_age - age)/4)


            for r in xrange(self.radius, 0, -self.radius/4):
                pygame.draw.circle(screen, self.sonar_color, self.center_pos, r, 1)

            for d in xrange(0,360, 15):
                if d % 90:
                    pygame.draw.line(screen, self.sonar_color, (int(self.center_pos[0] + ((self.radius*7)/8) * self.degrees_sin[d]),
                                                            int(self.center_pos[1] + ((self.radius*7)/8) * self.degrees_negcos[d])),
                                                            self.outside_pos[d], 2)
                else:
                    pygame.draw.line(screen, self.sonar_color, self.center_pos, self.outside_pos[d], 2)

            self.degrees += 1
            if self.degrees == 360:
                self.degrees = 0
        finally:
            screen.unlock()
            osd.mutex.release()

