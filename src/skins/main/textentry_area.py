# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# scrollabletext_area.py - A scrollable text area for the Freevo skin
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

class Textentry_Area(Skin_Area):
    """
    this call defines the Text Entry area
    """

    def __init__(self):
        Skin_Area.__init__(self, 'textentry')
        self.text_entry = None

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

        if not hasattr(menuw, "text_entry"):
            return

        text_entry = menuw.text_entry

        if self.text_entry != text_entry:
            self.text_entry = text_entry
            self.offset = 0

        text = ''
        total_width = 0
        font = content.font
        width = content.width
        caret_x = 0
        offset = self.offset

        caret_position = text_entry.caret_position
        pygame_font = font.font.font

        if offset > caret_position:
            offset = caret_position - 1
            if offset < 0:
                offset = 0
        else:
            total_width = 0
            new_offset = caret_position

            for i in range(caret_position, -1, -1):
                temp_text = text_entry.text[i:caret_position]
                total_width = font.font.stringsize(temp_text)
                if total_width > width:
                    break
                offset = i

        self.offset = offset

        total_width = 0
        for i in range(offset, len(text_entry.text)):
            total_width = font.font.stringsize(text_entry.text[offset:i+1])
            if total_width > width:
                break
            text = text_entry.text[offset:i+1]

        caret_text = text[:caret_position - offset]
        # We need a more exact position than is returned by the OSDFont class (which
        # caches character sizes but doesn't take account of kerning)
        caret_x,h = pygame_font.size(caret_text)

        # Draw Caret
        self.drawroundbox(content.x + caret_x, content.y, 2, content.height, (content.color, 0, 0x00000000, 0))

        # Draw text
        self.drawstring(text, font, content, x=content.x, align_v='center', ellipses='', dim=False)
