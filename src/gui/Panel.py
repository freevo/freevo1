# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Panel.py - A simple subclass of Container
# -----------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------
#
# Freevo - A Home Theater PC framework
#
# Copyright (C) 2002 Krister Lagerstrom, et al.
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
# ----------------------------------------------------------------------


import copy
import config

from Container      import Container
from LayoutManagers import FlowLayout

class Panel(Container):
    """
    """

    def __init__(self, left=0, top=0, width=0, height=0, bg_color=None,
                 fg_color=None, border=None, bd_color=None, bd_width=None):

        Container.__init__(self, left, top, width, height, bg_color, fg_color,
                           border, bd_color, bd_width)

        self.h_margin = 0
        self.v_margin = 0


    def set_parent(self, parent):
        Container.set_parent(self, parent)

        if self.parent:
            if isinstance(self.parent.get_layout(), FlowLayout):
                self.width = self.parent.width - 2 * self.parent.h_margin


    def _draw(self):
        self.surface = self.get_surface()
        Container._draw(self)
