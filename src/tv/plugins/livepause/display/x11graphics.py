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
import config


available = False
if config.CONF.display == 'x11':
    try:
        from kaa import imlib2
        from kaa.display import X11Window
        import pygame.image

        from tv.plugins.livepause.display.graphics import GraphicsOSD

        class X11GraphicsOSD(GraphicsOSD):
            def __init__(self, player):
                GraphicsOSD.__init__(self, player)
                self.window = X11Window(size=(1,1), title='Freevo OSD')
                self.window.set_decorated(False)
                self.window.signals['expose_event'].connect(self.__redraw)
                self.image = None

            def shutdown(self):
                pass

            def show_surface(self, surface, x, y):
                format = 'RGBA'
                surface_data = pygame.image.tostring(surface, format)
                self.image = imlib2.new(surface.get_size(), surface_data, format)
                self.window.set_geometry((x,y), surface.get_size())
                self.window.set_shape_mask_from_imlib2_image(self.image)

                if self.window.get_visible():
                    self.window.raise_window()
                    self.window.render_imlib2_image(self.image)
                else:
                    self.window.show()


            def hide_surface(self):
                self.window.hide()
                self.image = None

            def __redraw(self):
                if self.image:
                    self.window.render_imlib2_image(self.image)

        available = True
    except ImportError:
        pass
