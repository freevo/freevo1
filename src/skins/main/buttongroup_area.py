# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# textentry_area.py - A text entry area for the Freevo skin
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


import copy
import types
from area import Skin_Area
from skin_utils import *
from skin import eval_attr
import config

class Buttongroup_Area(Skin_Area):
    """
    this call defines the Button Group area
    """

    def __init__(self):
        Skin_Area.__init__(self, 'buttongroup')
        self.button_group = None


    def update_content_needed(self):
        """
        check if the content needs an update
        """
        return True


    def update_content(self):
        """
        update the listing area
        """
        menuw     = self.menuw
        settings  = self.settings
        layout    = self.layout
        area      = self.area_val
        content   = self.calc_geometry(layout.content, copy_object=True)

        if not hasattr(menuw, "button_group"):
            return

        button_group = menuw.button_group

        if self.button_group != button_group:
            self.button_group = button_group

        unselected_style = content.types['default']
        selected_style = content.types['selected']

        # Overload the item type for the padding variables
        padding_type = content.types['padding']
        if padding_type:
            padding_horizontal = padding_type.width
            padding_vertical   = padding_type.height
        else:
            padding_horizontal = 2
            padding_vertical   = 2

        rows = button_group.rows
        columns = button_group.columns
        button_width = (content.width - (padding_horizontal * (columns - 1)))/ columns
        button_height = (content.height - (padding_vertical * (rows - 1)))/ rows
        y = content.y
        for row in button_group.buttons:
            x = content.x
            for button in row:
                if button is not None:
                    if button == button_group.selected_button:
                        style = selected_style
                    else:
                        style = unselected_style
                    if style.rectangle:
                        w,h,r = self.get_item_rectangle(style.rectangle,  button_width,  button_height)
                        self.drawroundbox(x, y, r.width, r.height, r)
                    self.drawstring(button.text,  style.font, content, x, y,  button_width,  button_height,
                                    align_h=style.align,  align_v=style.valign)
                x += button_width + padding_horizontal

            y += button_height + padding_vertical
