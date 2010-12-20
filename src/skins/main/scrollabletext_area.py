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

class Scrollabletext_Area(Skin_Area):
    """
    this call defines the listing area
    """

    def __init__(self):
        Skin_Area.__init__(self, 'scrollabletext')
        self.last_first_line = -1
        self.scrollable_text = None


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

        if not hasattr(menuw, "scrollable_text"):
            return

        scrollable_text = menuw.scrollable_text

        if self.scrollable_text != scrollable_text:

            scrollable_text.layout(content.width, content.height, content.font)
            self.scrollable_text = scrollable_text

        page = scrollable_text.get_page()

        if not len(page):
            return

        y = 0
        for line in page:
            self.drawstring(line, content.font, content, content.x, content.y + y, mode='hard')
            y += content.font.height

        # print arrow:
        try:
            if scrollable_text.more_lines_up() and area.images['uparrow']:
                self.drawimage(area.images['uparrow'].filename, area.images['uparrow'])

            if (scrollable_text.more_lines_down() or scrollable_text.more_lines_up()) and \
                    area.images['scrollbar']:
                offset, total_lines, lines_per_page = scrollable_text.get_page_details()
                v = copy.copy(area.images['scrollbar'])
                if isinstance(area.images['scrollbar'].height, types.TupleType):                   
                    v.height = eval_attr(v.height, content.height)
                v.y += int(float(v.height) * (float(offset) / float(total_lines)))
                h = int(float(v.height) * (float(lines_per_page) / float(total_lines)))
                v.height = min(v.height, h)
                self.drawimage(area.images['scrollbar'].filename, v)

            if scrollable_text.more_lines_down() and area.images['downarrow']:
                if isinstance(area.images['downarrow'].y, types.TupleType):
                    v = copy.copy(area.images['downarrow'])
                    v.y = eval_attr(v.y, content.y + content.height)
                else:
                    v = area.images['downarrow']
                self.drawimage(area.images['downarrow'].filename, v)
        except:
            # empty menu / missing images
            pass
