# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Window - A window for freevo.
# -----------------------------------------------------------------------
# $Id$
#
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
import rc

from GUIObject import GUIObject, Align
from Container import Container
from skin import eval_attr

class Window(GUIObject):
    """
    x         x coordinate. Integer
    y         y coordinate. Integer
    width     Integer
    height    Integer
    """

    def __init__(self, parent='osd', x=None, y=None, width=0, height=0):
        GUIObject.__init__(self, x, y, width, height)

        if not parent or parent == 'osd':
            parent = self.osd.app_list[0]

        parent.add_child(self)

        self.osd.add_app(self)

        self.event_context = 'input'
        _debug_('window: setting context to %s' % self.event_context, 2)
        rc.set_context(self.event_context)

        if not width:
            self.width  = self.osd.width / 2

        if not height:
            self.height = self.osd.height / 4

        if not self.left:
            self.left = self.osd.width/2 - self.width/2

        if not self.top:
            self.top  = self.osd.height/2 - self.height/2
            self.center_on_screen = True

        self.internal_h_align = Align.CENTER
        self.internal_v_align = Align.CENTER

        self.refresh_abs_position()

    def show(self):
        self.visible = 1
        self.osd.dialog_layer.fill((0,0,0,config.OSD_DIALOG_BACKGROUND_DIM))
        self.draw()
        self.osd.update()

    def hide(self):
        self.visible = 0
        self.osd.dialog_layer_enabled = False
        self.osd.update()

    def add_child(self, child):
        if self.content:
            self.content.add_child(child)

    def __init__content__(self):
        x, y, width, height = self.content_layout.x, self.content_layout.y, \
                              self.content_layout.width, self.content_layout.height
        width  = eval_attr(width, self.width) or self.width
        height = eval_attr(height, self.height) or self.height

        self.content = Container('frame', x, y, width, height, vertical_expansion=1)
        GUIObject.add_child(self, self.content)

        # adjust left to content
        self.left += (self.width - width-x) / 2

        self.content.internal_h_align = Align.CENTER
        self.content.internal_v_align = Align.CENTER


    def set_size(self, width, height):
        width  -= self.width
        height -= self.height

        self.width  += width
        self.height += height

        width, height = self.content_layout.width, self.content_layout.height
        self.content.width  = eval_attr(width,  self.width ) or self.width
        self.content.height = eval_attr(height, self.height) or self.height

        self.left = self.osd.width/2 - self.width/2
        self.top  = self.osd.height/2 - self.height/2

        # adjust left to content
        self.left += (self.width - self.content.width-self.content.left) / 2



    def _draw(self):
        """
        The actual internal draw function.

        """
        _debug_('Window::_draw %s' % self, 2)

        if not self.width or not self.height:
            raise TypeError, 'Not all needed variables set.'

        cheight = self.content.height
        self.content.layout()

        # resize when content changed the height because of the layout()
        if self.content.height - cheight > 0:
            self.height += self.content.height - cheight

        self.surface = self.osd.Surface(self.get_size()).convert_alpha()
        self.surface.fill((0,0,0,0))

        for o in self.background_layout:
            if o[0] == 'rectangle':
                r = copy.deepcopy(o[1])
                r.width  = eval_attr(r.width,  self.get_size()[0])
                r.height = eval_attr(r.height, self.get_size()[1])
                if not r.width:
                    r.width  = self.get_size()[0]
                if not r.height:
                    r.height = self.get_size()[1]
                if r.x + r.width > self.get_size()[0]:
                    r.width = self.get_size()[0] - r.x
                if r.y + r.height > self.get_size()[1]:
                    r.height = self.get_size()[1] - r.y
                self.osd.drawroundbox(r.x, r.y, r.x+r.width, r.y+r.height,
                                      r.bgcolor, r.size, r.color, r.radius,
                                      self.surface)

        self.get_selected_child = self.content.get_selected_child
        if not self.content.parent:
            print '******************************************************************'
            print 'Error: content has no parent, fixing...'
            print 'If you can reproduce this error message, please send a bug report'
            print 'to the freevo-devel list'
            print '******************************************************************'
            self.content.parent = self

        if not self.parent:
            print '******************************************************************'
            print 'Error: window has no parent, not showing...'
            print 'If you can reproduce this error message, please send a bug report'
            print 'to the freevo-devel list'
            print '******************************************************************'
            return

        self.content.surface = self.content.get_surface()
        self.content.draw()
        self.blit_parent()
