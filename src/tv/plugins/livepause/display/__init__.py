# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# display.py - the Freevo livepause osd module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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
import os.path
import time

import config
import osd
import pygame.image

from tv.plugins.livepause.display.base import OSD
from tv.plugins.livepause.display.text import TextOSD
from tv.plugins.livepause.display.graphics import GraphicsOSD
from tv.plugins.livepause.display import x11graphics

def get_osd(player):
    """
    Get the best supported OSD available.
    @return: An OSD object
    """
    if player.supports_graphics:
        return GraphicsOSD(player)
    elif x11graphics.available:
        return x11graphics.X11GraphicsOSD(player)
    if player.supports_text:
        return TextOSD(player)
    else:
        return OSD(player) # Dummy OSD does nothing
