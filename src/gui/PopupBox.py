# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# PopupBox - A dialog box for freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Todo: o Add sanitychecking on all arguments.
#       o Add actual support for icons, not just brag about it.
#       o Start using the OSD imagecache for rectangles.
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
import logging
logger = logging.getLogger("freevo.gui.PopupBox")


import config
import skin
import rc
from event import *

from GUIObject import *
from Window    import *
from Label     import *


class PopupBox(Window):
    """
    Trying to make a standard popup/dialog box for various usages.
    """
    def __init__(self, text, handler=None, x=0, y=0, width=0, height=0,
                 icon=None, vertical_expansion=1, text_prop=None, parent='osd'):
        """
        Initialise an instance of a PopupBox

        @ivar x: x coordinate. Integer
        @ivar y: y coordinate. Integer
        @ivar width: Integer
        @ivar height: Integer
        @ivar text: String to print.
        @ivar icon: icon
        @ivar text_prop: A dict of 4 elements composing text proprieties
          { 'align_h': align_h, 'align_v': align_v, 'mode': mode, 'hfill': hfill }:
            - align_v = text vertical alignment
            - align_h = text horizontal alignment
            - mode    = hard (break at chars); soft (break at words)
            - hfill   = True (don't shorten width) or False
        """

        self.handler = handler
        Window.__init__(self, parent, x, y, width, height)
        self.text_prop = text_prop or { 'align_h': 'center',
                                        'align_v': 'center',
                                        'mode'   : 'soft',
                                        'hfill'  : True }

        self.font = None
        if self.skin_info_font:
            self.set_font(self.skin_info_font.name, self.skin_info_font.size, Color(self.skin_info_font.color))
        else:
            self.set_font(config.OSD_DEFAULT_FONTNAME, config.OSD_DEFAULT_FONTSIZE)

        if not width:
            tw = self.font.stringsize(text) + self.h_margin*2
            if tw < self.osd.width * 2 / 3:
                self.width = max(self.osd.width / 2, tw)

        self.__init__content__()

        if type(text) in StringTypes:
            self.label = Label(text, self, Align.CENTER, Align.CENTER, text_prop=self.text_prop)
        else:
            raise TypeError, text

        if icon:
            self.set_icon(icon)


    def get_text(self):
        """
        Get the text to display

        @returns: text
        """
        return self.label.text


    def get_font(self):
        """
        Does not return OSD.Font object, but the filename and size as list.
        """
        return ('normal', self.font.name, int(self.font.size), self.font.color)


    def set_font(self, file, size, color):
        """
        Set the font.

        Just hands the info down to the label. Might raise an exception.
        """
        if not self.font:
            self.font = self.osd.getfont(file, size)

        self.font.size = size
        self.font.color = color


    def get_icon(self):
        """
        Returns the icon of the popupbox (if set).
        """
        return self.icon


    def set_icon(self, image):
        """
        Set the icon of the popupbox.
        Also scales the icon to fit the size of the box.

        Not working right now
        """
        pass


    def eventhandler(self, event):
        logger.log( 9, 'PopupBox: event = %s', event)

        if event == INPUT_EXIT:
            self.destroy()
            return True
        
        elif event == MOUSE_BTN_PRESS and event.button == 3:
            self.destroy()
            return True

        return False
