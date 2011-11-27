# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# screensaver/flames.py - the Freevo Screensaver
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Many thanks to Pete Shinners for his example.
# http://www.pygame.org/pcr/numpy_flames/index.php
#
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
logger = logging.getLogger("freevo.plugins.screensaver.flames")

from plugins.screensaver import ScreenSaverPlugin
import config
import osd

osd = osd.get_singleton()

import pygame, pygame.transform
from pygame.surfarray import *
from pygame.locals import *
from Numeric import *
from RandomArray import *

MAX = 246
RESIDUAL = 86
HSPREAD, VSPREAD = 26, 78
VARMIN, VARMAX = -2, 3

class PluginInterface(ScreenSaverPlugin):
    """
    A Flames simulation screensaver
    """
    def __init__(self):
        logger.log( 9, 'PluginInterface.__init__()')
        ScreenSaverPlugin.__init__(self)
        self.plugin_name = 'screensaver.flames'
        self.fps = config.FLAMES_FPS

    def config(self):
        logger.log( 9, 'config()')
        return [
            ('FLAMES_FPS', 20, 'Frames per second'),
            ('FLAMES_RES_DIVIDER', 4, 'Ratio of screen size to the size of the surface used to simulate the flames.'),
        ]


    def start(self, width, height):
        logger.log( 9, 'start(width=%r, height=%r)', width, height)
        self.width = width
        self.height = height
        self.flame = zeros(array((width, height))/config.FLAMES_RES_DIVIDER + (0,3))
        self.miniflame = pygame.Surface((width/config.FLAMES_RES_DIVIDER, height/config.FLAMES_RES_DIVIDER), 0, 8)
        setpalette(self.miniflame)
        randomflamebase(self.flame)
        return self.fps


    def draw(self, screen):
        modifyflamebase(self.flame)
        processflame(self.flame)
        blitdouble(screen, self.flame, self.miniflame)

def setpalette(screen):
    "here we create a numeric array for the colormap"
    gstep, bstep = 75, 150
    cmap = zeros((256, 3))
    cmap[:,0] = minimum(arange(256)*3, 255)
    cmap[gstep:,1] = cmap[:-gstep,0]
    cmap[bstep:,2] = cmap[:-bstep,0]
    screen.set_palette(cmap)


def randomflamebase(flame):
    "just set random values on the bottom row"
    flame[:,-1] = randint(0, MAX, flame.shape[0])


def modifyflamebase(flame):
    "slightly change the bottom row with random values"
    bottom = flame[:,-1]
    mod = randint(VARMIN, VARMAX, bottom.shape[0])
    add(bottom, mod, bottom)
    maximum(bottom, 0, bottom)
    #if values overflow, reset them to 0
    bottom[:] = choose(greater(bottom,MAX), (bottom,0))


def processflame(flame):
    "this function does the real work, tough to follow"
    notbottom = flame[:,:-1]

    #first we multiply by about 60%
    multiply(notbottom, 146, notbottom)
    right_shift(notbottom, 8, notbottom)

    #work with flipped image so math accumulates.. magic!
    flipped = flame[:,::-1]

    #all integer based blur, pulls image up too
    tmp = flipped * 20
    right_shift(tmp, 8, tmp)
    tmp2 = tmp >> 1
    add(flipped[1:,:], tmp2[:-1,:], flipped[1:,:])
    add(flipped[:-1,:], tmp2[1:,:], flipped[:-1,:])
    add(flipped[1:,1:], tmp[:-1,:-1], flipped[1:,1:])
    add(flipped[:-1,1:], tmp[1:,:-1], flipped[:-1,1:])

    tmp = flipped * 80
    right_shift(tmp, 8, tmp)
    add(flipped[:,1:], tmp[:,:-1]>>1, flipped[:,1:])
    add(flipped[:,2:], tmp[:,:-2], flipped[:,2:])

    #make sure no values got too hot
    minimum(notbottom, MAX, notbottom)


def blitdouble(screen, flame, miniflame):
    "double the size of the data, and blit to screen"
    blit_array(miniflame, flame[:,:-3])
    s2 = pygame.transform.scale(miniflame, screen.get_size())
    screen.blit(s2, (0,0))
