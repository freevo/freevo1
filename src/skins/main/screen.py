# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# The screen for the Freevo areas to draw on
# -----------------------------------------------------------------------
# $Id$
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
import logging
logger = logging.getLogger("freevo.skins.main.screen")


import config
import osd
osd = osd.get_singleton()


singleton = None

def get_singleton():
    global singleton
    if not singleton:
        singleton = Screen()
    return singleton


class SkinObjects:
    """
    object which stores the different types of objects
    an area wants to draw
    """
    def __init__(self):
        logger.log( 8, 'SkinObjects.__init__()')
        self.bgimages   = []
        self.rectangles = []
        self.images     = []
        self.text       = []
        self.skin_area  = None


class Screen:
    """
    this call is a set of surfaces for the area to do it's job
    """
    def __init__(self):
        logger.log( 8, 'Screen.__init__()')
        self.s_content      = osd.screen.convert()
        self.s_alpha        = self.s_content.convert_alpha()
        self.s_bg           = self.s_content.convert()
        self.s_screen       = self.s_content.convert()
        self.update_bg      = None
        self.update_alpha   = []
        self.update_content = []
        self.drawlist       = SkinObjects()

        self.s_alpha.fill((0,0,0,0))


    def clear(self):
        logger.log( 8, 'clear()')
        self.update_bg      = None
        self.update_alpha   = []
        self.update_content = []
        self.drawlist       = SkinObjects()


    def draw(self, obj):
        logger.log( 8, 'draw(obj=%r)', obj)
        self.drawlist.bgimages   += obj.bgimages
        self.drawlist.rectangles += obj.rectangles
        self.drawlist.images     += obj.images
        self.drawlist.text       += obj.text

        if obj.skin_area:
            if self.drawlist.skin_area is None:
                self.drawlist.skin_area = []
            self.drawlist.skin_area.append(obj.skin_area)


    def update(self, layer, rect):
        logger.log( 8, 'update(layer=%r, rect=%r)', layer, rect)
        if layer == 'content':
            self.update_content.append(rect)
        elif layer == 'alpha':
            self.update_alpha.append(rect)
        else:
            if self.update_bg:
                self.update_bg = ( min(self.update_bg[0], rect[0]),
                                   min(self.update_bg[1], rect[1]),
                                   max(self.update_bg[2], rect[2]),
                                   max(self.update_bg[3], rect[3]))
            else:
                self.update_bg = rect


    def in_update(self, x1, y1, x2, y2, update_area, full=False):
        logger.log( 8, 'in_update(x1=%r, y1=%r, x2=%r, y2=%r, update_area=%r, full=%r)', x1, y1, x2, y2, update_area, full)
        if full:
            for ux1, uy1, ux2, uy2 in update_area:
                # if the area is not complete inside the area but is inside on
                # some pixels, return False
                if (not (ux1 >= x1 and uy1 >= y1 and ux2 <= x2 and uy2 <= y2)) and \
                   (not (x2 < ux1 or y2 < uy1 or x1 > ux2 or y1 > uy2)):
                    return False
            return True

        for ux1, uy1, ux2, uy2 in update_area:
            if not (x2 < ux1 or y2 < uy1 or x1 > ux2 or y1 > uy2):
                return True
        return False


    def show(self, force_redraw=False):
        """
        the main drawing function
        """
        logger.log( 8, 'show(force_redraw=%r)', force_redraw)
        if osd.must_lock:
            # only lock s_alpha layer, because only there
            # are pixel operations (round rectangle)
            self.s_alpha.lock()

        if force_redraw:
            logger.log( 9, 'show, force update')
            self.update_bg      = (0, 0, osd.width, osd.height)
            self.update_alpha   = []
            self.update_content = []

        update_area = self.update_alpha

        # if the background has some changes ...
        if self.update_bg:
            ux1, uy1, ux2, uy2 = self.update_bg
            for x1, y1, x2, y2, image in self.drawlist.bgimages:
                if not (x2 < ux1 or y2 < uy1 or x1 > ux2 or y1 > uy2):
                    self.s_bg.blit(image, (ux1, uy1), (ux1-x1, uy1-y1, ux2-ux1, uy2-uy1))
            update_area.append(self.update_bg)

        # rectangles
        if update_area:
            self.s_alpha.fill((0,0,0,0))
            for x1, y1, x2, y2, bgcolor, size, color, radius in self.drawlist.rectangles:
                # only redraw if necessary
                if self.in_update(x1, y1, x2, y2, update_area):
                    # if the radius and the border is not inside the update area,
                    # use drawbox, it's faster
                    if self.in_update(x1+size+radius, y1+size+radius, x2-size-radius,
                                      y2-size-radius, update_area, full=True):
                        osd.drawroundbox(x1, y1, x2, y2, color=bgcolor,
                                         layer=self.s_alpha)
                    else:
                        osd.drawroundbox(x1, y1, x2, y2, color=bgcolor,
                                         border_size=size, border_color=color,
                                         radius=radius, layer=self.s_alpha)
            # and than blit only the changed parts of the screen
            try:
                for x0, y0, x1, y1 in update_area:
                    self.s_content.blit(self.s_bg, (x0, y0), (x0, y0, x1-x0, y1-y0))
                    self.s_content.blit(self.s_alpha, (x0, y0), (x0, y0, x1-x0, y1-y0))
            except:
                pass

        update_area += self.update_content

        layer = self.s_screen
        for x0, y0, x1, y1 in update_area:
            layer.blit(self.s_content, (x0, y0), (x0, y0, x1-x0, y1-y0))

        # if something changed redraw all content objects
        if update_area:
            ux1, uy1, ux2, uy2 = osd.width, osd.height, 0, 0
            for a in update_area:
                ux1 = min(ux1, a[0])
                uy1 = min(uy1, a[1])
                ux2 = max(ux2, a[2])
                uy2 = max(uy2, a[3])

            for x1, y1, x2, y2, image in self.drawlist.images:
                if self.in_update(x1, y1, x2, y2, update_area):
                    layer.blit(image, (ux1, uy1), (ux1-x1, uy1-y1, ux2-ux1, uy2-uy1))

            for x1, y1, x2, y2, text, font, height, align_h, align_v, mode, \
                    ellipses, dim in self.drawlist.text:
                if self.in_update(x1, y1, x2, y2, update_area):
                    osd.drawstringframed(text, x1, y1, x2 - x1, height, font,
                                         align_h = align_h,
                                         align_v = align_v, mode=mode,
                                         ellipses=ellipses, dim=dim, layer=layer)

        if self.drawlist.skin_area:
            for area in self.drawlist.skin_area:
                x,y,w,h,name = area
                osd.drawbox(x,y,x + w, y +h, 1, osd.COL_WHITE, 0, layer)
                osd.drawstring(name, x + 1, y + 1, fgcolor=osd.COL_WHITE, bgcolor=osd.COL_BLUE, layer=layer)
                update_area.append((x,y,x+w,y+h))

        if not update_area:
            return None

        rect = (osd.width, osd.height, 0, 0)
        for u in update_area:
            osd.screenblit(layer, (u[0], u[1]), (u[0], u[1], u[2]-u[0], u[3]-u[1]))
            rect = ( min(u[0], rect[0]), min(u[1], rect[1]),
                     max(u[2], rect[2]), max(u[3], rect[3]))
        rect = (rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1])

        if osd.must_lock:
            self.s_alpha.unlock()

        return rect
