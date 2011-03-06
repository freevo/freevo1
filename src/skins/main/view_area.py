# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A view area for the Freevo skin
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
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


from area import Skin_Area
from skin_utils import *

import skin

class View_Area(Skin_Area):
    """
    this call defines the view area
    """

    def __init__(self):
        Skin_Area.__init__(self, 'view')
        self.image = None
        self.image_loaded = False
        self.loading_image = None
        self._image = None


    def update_content_needed(self):
        """
        check if the content needs an update
        """
        item = self.viewitem
        image = None

        if hasattr(item, 'image') and item.image:
            image = item.image

        if Unicode(image) != Unicode(self.image):
            self._image = None
            self.image_loaded = False
            
        return Unicode(image) != Unicode(self.image) or self.image_loaded

    def __loaded(self, result, image_request):
        if self.image == image_request[0]:
            self.loading_image = None
            self._image = result + image_request[1:]
            self.image_loaded = True
            
            skin.redraw()

    def update_content(self):
        """
        update the view area
        """
        item = self.viewitem

        layout    = self.layout
        area      = self.area_val
        content   = self.calc_geometry(layout.content, copy_object=True)

        self.image_loaded = False

        if hasattr(item, 'type') and content.types.has_key(item.type):
            val = content.types[item.type]
        else:
            val = content.types['default']

        if hasattr(item, 'image') and item.image:
            if self.image != item.image:
                self._image = None
            self.image = item.image
        else:
            self.image = None
            return

        x0 = 0
        y0 = 0

        width  = content.width - 2*content.spacing
        height = content.height - 2*content.spacing

        if val.rectangle:
            r = self.get_item_rectangle(val.rectangle, width, height)[2]

            if r.x < 0:
                x0 -= r.x
                r.x = 0

            if r.y < 0:
                y0 -= r.y
                r.y = 0

            if r.x + r.width > x0 + width:
                r.width, width = width, width - (r.width - width)

            if r.y + r.height > y0 + height:
                r.height, height = height, height - (r.height - height)

        addx = content.x + content.spacing
        addy = content.y + content.spacing

        if self._image:
            if width != self._image[3] or height != self._image[4]:
                self._image = None

        if self._image:
            image, i_w, i_h, r_w, r_h = self._image
        else:
            if self.loading_image:
                self.loading_image.cancelled = True
            self.loading_image = AsyncImageFormatter(self.settings, item, width, height, 0, self.xml_settings.anamorphic)
            self.loading_image.connect(self.__loaded, (self.image, width, height))
            image = None

        if not image:
            return

        if content.align == 'center' and i_w < width:
            addx += (width - i_w) / 2

        if content.align == 'right' and i_w < width:
            addx += width - i_w

        if content.valign == 'center' and i_h < height:
            addy += (height - i_h) / 2

        if content.valign == 'bottom' and i_h < height:
            addy += height - i_h

        x0 += addx
        y0 += addy

        self.drawimage(image, (x0, y0))

        if val.rectangle:
            r.width -= width - i_w
            r.height -= height - i_h
            self.drawroundbox(r.x + addx, r.y + addy, r.width, r.height, r)
