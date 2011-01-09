# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# scrollabletext_screen.py - A widget to handle scrollable text.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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

import rc
from event import *
from skin.models import ScrollableText

import skin
skin_object = skin.get_singleton()

class ScrollableTextScreen:
    """
    A scrollable text screen
    """
    def __init__(self, layout, text):
        """
        Used to display and control the position of text in a scrollable area.

        @param layout: Skin layout to use.
        @param text: This is the text to scroll.
        """
        self.layout = layout
        self.scrollable_text = ScrollableText(text)

    def show(self, menuw):
        """
        Display the screen and make it the active 'menu'.

        @param menuw: The menu widget to push this screen onto.
        """
        self.menuw = menuw
        self.blend = 1
        menuw.pushmenu(self)
        self.blend = False
        if hasattr(self, 'event_context'):
            _debug_('scrollabletext_screen: setting context to %s' % self.event_context, 2)
            rc.set_context(self.event_context)

    def refresh(self):
        """
        Redraw the screen.
        """
        if self.menuw.children:
            return
        skin_object.draw(self.layout, self, blend=self.blend)

    def eventhandler(self, event, menuw=None):
        """
        eventhandler to handle events that relate to scrolling the text
        in the scrollable_text area/object.
        Any events not directly handled here are passed to the registered
        client_eventhandler.

        @param event: The event to handle.
        @param menuw: The Menu Widget that called this handler.
        """
        event_consumed = False
        if event == MENU_UP:
            self.scrollable_text.scroll(True)
            self.refresh()
            event_consumed = True

        elif event == MENU_DOWN:
            self.scrollable_text.scroll(False)
            self.refresh()
            event_consumed = True

        elif event == MENU_SUBMENU:
            # open the submenu for this item
            if hasattr(self.menuw.menustack[-2],'is_submenu'):
                # there is already a submenu, we can return to
                self.menuw.eventhandler('MENU_BACK_ONE_MENU')
                event_consumed = True
            else:
                # we have to create a new submenu
                self.menuw.delete_menu()
                self.menuw.eventhandler('MENU_SUBMENU')
                event_consumed = True

        elif event == MENU_SELECT:
            # just close this again
            self.menuw.eventhandler('MENU_BACK_ONE_MENU')
            event_consumed = True

        return event_consumed

    def getattr(self, attr):
        """
        Used by the skin to retrieve named details about this object.
        """
        return getattr(self, attr, u'')
