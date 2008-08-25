# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# base.py - base osd module for livepause osd
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

import config
import osd

definitions = {}

def register_definition(name, background, location):
    osdcontainer = OSDContainer(background, location)
    definitions[name] = osdcontainer
    return osdcontainer

def get_definition(name):
    return definitions[name]

class OSDContainer(object):
    def __init__(self, background, location):
        # Load background image
        filename = os.path.join(config.IMAGE_DIR, os.path.join('osd', background))
        self.location = location
        self.background = filename
        self.objects = []
        self.surface = None

    def add_text(self, x, y, w, h, expr, font, fgcolor, bgcolor, valign, halign):
        self.objects.append(TextOSDObject(x, y, w, h, expr, font, fgcolor, bgcolor, valign, halign))

    def add_image(self, x, y, w, h, image, expr):
        self.objects.append(ImageOSDObject(x, y, w, h, image, expr))

    def add_percent(self, x, y, w, h, images, expr):
        self.objects.append(PercentOSDObject(x, y, w, h, images, expr))

    def prepare(self):
        # Load background image
        self.surface = osd.get_singleton().loadbitmap(self.background)
        for obj in self.objects:
            obj.prepare()

    def render(self, value_dict):
        surface = self.surface.copy()
        for obj in self.objects:
            obj.render(self.surface, value_dict)

        return surface

    def finish(self):
        # Release surface
        self.surface = None
        for obj in self.objects:
            obj.finish()

class OSDObject(object):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def prepare(self):
        pass

    def render(self, surface, value_dict):
        pass

    def finish(self):
        pass

class TextOSDObject(OSDObject):
    def __init__(self, x, y, w, h, expr, font, fgcolor, bgcolor, valign, halign):
        OSDObject.__init__(self, x, y, w, h)
        self.expr = expr
        self.font = font
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.valign = valign
        self.halign = halign


    def render(self, surface, value_dict):
        to_render = self.expr % value_dict
        osd.get_singleton().drawstringframed(to_render, self.x, self.y, self.w, self.h,
                                             self.font, self.fgcolor, self.bgcolor,
                                             self.halign, self.valign, layer=surface)

class ImageOSDObject(OSDObject):
    def __init__(self, x, y, w, h, image, expr):
        OSDObject.__init__(self, x, y, w, h)
        filename = os.path.join(config.IMAGE_DIR, os.path.join('osd', image))
        self.image = filename
        self.image_surface = None
        self.expr = expr

    def prepare(self):
        self.image_surface = osd.get_singleton().loadbitmap(self.image)

    def render(self, surface, value_dict):
        if eval(self.expr, value_dict):
            osd.get_singleton().drawsurface(self.image_surface,
                                            bbx=self.x, bby=self.y, bbw=self.w, bbh=self.h,
                                            layer=surface)

    def finish(self):
        self.image_surface = None

class PercentOSDObject(ImageOSDObject):
    def __init__(self, x, y, w, h, image, expr, vertical):
        ImageOSDObject.__init__(self, x, y, w, h, image, expr)
        self.vertical = vertical

    def render(self, surface, value_dict):
        percent = min(1.0, max(0, eval(self.expr, value_dict)))
        if self.vertical:
            im_x = 0
            x = self.x
            w = self.w
            h = int(float(self.h) * percent)
            im_y = self.h - h
            y = self.y + im_y

        else:
            im_x = 0
            im_y = 0
            x = self.x
            y = self.y
            w = int(float(self.w) * percent)
            h = self.h

        osd.get_singleton().drawsurface(self.image_surface,x=im_x, y=im_y,
                                        bbx=x, bby=y, bbw=w, bbh=h,
                                        layer=surface)
