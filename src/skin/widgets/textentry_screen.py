# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# textentry_screen.py - This is the Freevo top-level skin widget code.
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

from event import *
from skin.models import Button, ButtonGroup, TextEntry

import skin
skin_object = skin.get_singleton()
#skin_object:
if skin_object:
    skin_object.register('textentry', ('screen', 'title','textentry', 'buttongroup', 'plugin'))

class TextEntryScreen:
    def __init__(self, action, title, text='', alpha=True, numeric=True, symbol=True):
        """
        Used to display and control the

        @param actions: Tuple containing a name and an action function that will be called
                  with the menu widget and the contents of the text entry field when
                  selected.
        @param title:   The title to display at the top of the screen.
        @param text:    Initial text for the text entry field.
        @param alpha:   Whether to display the alphabet character board
        @param numeric: Whether to display the number character board.
        @param symbol:  Whether to display the symbol character board.
        """
        self.title = title
        self.text_entry = TextEntry(text)

        # Create common buttons
        self.action_button = Button(action[0], self.activate_action, action[1])
        self.left_button   = Button(_('Left'), self.move_caret, 'left')
        self.right_button  = Button(_('Right'), self.move_caret, 'right')
        self.delete_button = Button(_('Delete'), self.delete_char, None)

        # Make sure at least one character board is enabled.
        if not (alpha or numeric or symbol):
            # raise RuntimeError, 'At least one character board should be enabled!'

            return

        # Work out whether we need a column to select different character boards.
        if (alpha and not numeric and not symbol) or \
           (not alpha and numeric and not symbol) or \
           (not alpha and not numeric and symbol):
            columns = 6
        else:
            columns = 7

        #
        # Create button groups for alphabet/numbers/symbols
        #
        if alpha:
            self.alphabet_button_group = ButtonGroup(6, columns)
            keys = _('ABCDEFGHIJKLMNOPQRSTUVWXYZ ')
            self.__init_keyboard_buttons(keys,  self.alphabet_button_group)

        if numeric:
            self.numbers_button_group = ButtonGroup(6, columns)
            keys = _('1234567890')
            self.__init_keyboard_buttons(keys,  self.numbers_button_group)

        if symbol:
            self.symbols_button_group = ButtonGroup(6, columns)
            keys = _('!"#$%^&*();:\'@~?,.<>-=+\[]{}')
            self.__init_keyboard_buttons(keys,  self.symbols_button_group)

        # If more than 1 character board is selected add the buttons to switch
        # between them.
        if (alpha and numeric) or (alpha and symbol) or (numeric and symbol):
            if alpha:
                characters_button = Button(_('ABC'),  self.change_button_group,
                                                           self.alphabet_button_group)
                if numeric:
                    self.numbers_button_group.set_button(0, 5, characters_button)
                if symbol:
                    self.symbols_button_group.set_button(0, 5, characters_button)

            if numeric:
                numbers_button = Button(_('123'),  self.change_button_group,
                                                        self.numbers_button_group)
                if alpha:
                    self.alphabet_button_group.set_button(1, 5, numbers_button)
                if symbol:
                    self.symbols_button_group.set_button(1, 5, numbers_button)

            if symbol:
                symbols_button = Button(_('Symbls'),  self.change_button_group,
                                                           self.symbols_button_group)
                if alpha:
                    self.alphabet_button_group.set_button(2, 5, symbols_button)
                if numeric:
                    self.numbers_button_group.set_button(2, 5, symbols_button)

        if alpha:
            self.button_group = self.alphabet_button_group
        elif numeric:
            self.button_group = self.numbers_button_group
        elif symbol:
            self.button_group = self.symbols_button_group


    def show(self, menuw):
        """
        Display the Text Entry Screen.
        This places the screen on the top of the menu stack.
        """
        self.menuw = menuw
        menuw.pushmenu(self)


    def refresh(self):
        """
        Redraw the screen.
        """
        if self.menuw.children:
            return
        skin_object.draw('textentry', self)


    def eventhandler(self, event, menuw=None):
        """
        Event handler to handle button navigation and selection.
        """
        event_consumed = False
        redraw = False

        if event is MENU_SELECT:
            self.button_group.selected_button.select()
            event_consumed = True

        elif event in (MENU_LEFT, MENU_RIGHT, MENU_DOWN, MENU_UP):
            if event is MENU_LEFT:
                redraw = self.button_group.move_left()
            elif event is MENU_RIGHT:
                redraw = self.button_group.move_right()
            elif event is MENU_DOWN:
                redraw = self.button_group.move_down()
            elif event is MENU_UP:
                redraw = self.button_group.move_up()
            event_consumed = True

        if redraw:
            self.refresh()

        return event_consumed


    def insert_key(self, arg):
        """
        Button action to insert a character.
        """
        self.text_entry.insert_char_at_caret(arg)
        self.refresh()


    def move_caret(self, arg):
        """
        Button action to move the caret.
        """
        if arg == 'left':
            self.text_entry.caret_left()
        elif arg == 'right':
            self.text_entry.caret_right()
        self.refresh()


    def delete_char(self, arg):
        """
        Button action to delete a character.
        """
        self.text_entry.delete_char_at_caret()
        self.refresh()


    def change_button_group(self, arg):
        """
        Button action to switch to a different button group.
        """
        self.button_group = arg
        self.button_group.set_selected(self.button_group.buttons[0][0])
        self.refresh()


    def activate_action(self, arg):
        """
        Button action to call the user supplied handler.
        """
        arg(self.menuw, self.text_entry.text)


    def __init_keyboard_buttons(self, keys, button_group):
        """
        Initialise a button group by spliting the keys argument into
        characters and add each to the button group as a button.
        """
        r = 0
        c = 0
        for key in keys:
            if key == ' ':
                text = _('Space')
            else:
                text = key
            button_group.set_button(r, c, Button(text, self.insert_key, key))
            c += 1
            if c == 5:
                r += 1
                c = 0
        # Add common buttons to the group
        column = button_group.columns - 1
        button_group.set_button(0, column, self.action_button)
        button_group.set_button(1, column, self.left_button)
        button_group.set_button(2, column, self.right_button)
        button_group.set_button(3, column, self.delete_button)


    def getattr(self, attr):
        """
        Used by the skin to retrieve named details about this object.
        """
        return getattr(self, attr, u'')
