# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screensaver/bouncing_freevo.py - the Freevo Screensaver
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
import os
from random import randint
import pygame

# freevo modules
import config
import osd
from plugins.screensaver import ScreenSaverPlugin

osd = osd.get_singleton()

class PluginInterface(ScreenSaverPlugin):
    def __init__(self):
        ScreenSaverPlugin.__init__(self)
        self.plugin_name = 'screensaver.bouncing_freevo'
        self.fps = config.BOUNCING_FREEVO_FPS
        self.image = osd.loadbitmap(os.path.join(config.IMAGE_DIR,'logo.png'))
        self.image_width = 200
        self.image_height = 98


    def config(self):
        return [ ('BOUNCING_FREEVO_FPS', 25, 'Frames per second')]


    def start(self, width, height):
        self.width = width
        self.height = height

        self.x = randint(0, width - self.image_width)
        self.y = randint(0, height - self.image_height)
        self.x_speed = randint(5,10)
        self.y_speed = randint(5,10)

        return self.fps


    def draw(self, screen):
        black = (0,0,0)
        dirty = []
        # Clear the old image
        screen.fill(black, (self.x,self.y, self.image_width, self.image_height))

        # Move the image
        self.x += self.x_speed
        if self.x < 0:
            self.x = 0
            self.x_speed *= -1
        if (self.x + self.image_width) > self.width:
            self.x = self.width - self.image_width
            self.x_speed *= -1

        self.y += self.y_speed
        if self.y < 0:
            self.y = 0
            self.y_speed *= -1

        if (self.y + self.image_height) > self.height:
            self.y = self.height - self.image_height
            self.y_speed *= -1

        screen.blit(self.image, (self.x, self.y))
