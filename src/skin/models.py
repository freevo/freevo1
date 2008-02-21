# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo top-level skin model code.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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


class ScrollableText:
    """
    Container for scrolling text using the skin area "scrollabletext"
    """
    def __init__(self, text):
        """
        Initialise the scrollable text area with the text to scroll.
        """
        self.text = text
        self.page = []
        self.lines = []
        self.max_lines = 1

    def get_page(self):
        """
        Returns the page of text to display.
        """
        return self.page

    def __get_line__(self, string, max_width, font, word_splitter, hard):
        """
        calculate _one_ line.
        @returns: a list
            - string to draw
            - rest that didn't fit
            - True if this function stopped because of a <nl>.
        """
        c = 0                           # num of chars fitting
        width = 0                       # width needed
        ls = len(string)
        space = 0                       # position of last space
        last_char_size = 0              # width of the last char
        last_word_size = 0              # width of the last word

        data = None
        while(True):
            if width > (max_width - 1):
                # ok, that's it. We don't have any space left
                break
            if ls == c:
                # everything fits
                return (string, '', False)
            if string[c] == '\n':
                # linebreak, we have to stop
                return (string[:c], string[c+1:], True)
            if string[c] in word_splitter:
                # rememeber the last space for mode == 'soft' (not hard)
                space = c
                last_word_size = 0

            # add a char
            last_char_size = font.charsize(string[c])
            width += last_char_size
            last_word_size += last_char_size
            c += 1

        rest_start = c

        if not hard:
            # go one word back, than it fits
            c = space
            if string[c] == ' ':
                rest_start = c + 1

        # calc the matching and rest string and return all this
        return (string[:c], string[rest_start:], False)

    def layout(self, width, height, font):
        """
        Layout the text into lines/pages based on the width, height and font
        supplied.
        """
        self.first_line_index = 0
        self.max_lines = height / font.height
        self.lines = []
        rest = self.text
        while rest:
            line, rest, nl = self.__get_line__(rest, width, font.font, ' ', False)
            if not line and rest and not nl:
                line, rest, nl = self.__get_line__(rest, width, font.font, ' -_', False)
                if not line and rest and not nl:
                    line, rest, nl = self.__get_line__(rest, width, font.font, ' -_', True)

            self.lines.append(line)

        self.build_page()


    def build_page(self):
        """
        Create the page based on the first_line_index.
        """
        self.page = []
        if self.first_line_index + self.max_lines >= len(self.lines):
            self.page = self.lines[self.first_line_index:]
        else:
            end_line_index = self.first_line_index + self.max_lines
            self.page = self.lines[self.first_line_index:end_line_index]

    def more_lines_up(self):
        """
        Returns true if the first line of the page is not the top of text, false
        if we are at the top.
        """
        return self.first_line_index != 0

    def more_lines_down(self):
        """
        Returns true if there are more lines below the bottom line of the
        current page.
        """
        return self.first_line_index + self.max_lines < len(self.lines)

    def scroll(self, up):
        """
        Scrolls the current page, up if 'up' is true or down if it is false, by
        one line.
        """
        # The text is not larger than the area so no need to scroll.
        if len(self.lines) <= self.max_lines:
            return

        if up:
            self.first_line_index = max(0, self.first_line_index - 1)
        else:
            self.first_line_index = min(self.first_line_index + 1,
                min(len(self.lines) - 1, len(self.lines) - self.max_lines))
        self.build_page()


class TextEntry:
    """
    Data model for a single line of editable text.
    """

    def __init__(self, text, left_to_right=True):
        """
        Initialise the model with the specified text and direction of input.
        """
        self.text = text
        self.left_to_right = left_to_right
        self.caret_position = 0


    def caret_left(self):
        """
        Moves the caret, marking the position the next character will be
        inserted at, left one character.
        """
        self.caret_position -= 1
        if self.caret_position < 0:
            self.caret_position = 0


    def caret_right(self):
        """
        Moves the caret, marking the position the next character will be
        inserted at, right one character.
        """
        self.caret_position += 1
        if self.caret_position > len(self.text):
            self.caret_position = len(self.text)


    def delete_char_at_caret(self):
        """
        Delete one character at the current caret position and possibly update
        the caret position.
        """
        # TODO: Right to Left handling
        if self.caret_position == 0:
            return
        if self.caret_position == 1:
            self.text = self.text[self.caret_position:]
        else:
            self.text = self.text[:self.caret_position - 1] + self.text[self.caret_position:]
        self.caret_position -= 1

    def insert_char_at_caret(self, char):
        """
        Insert one character at the current caret positon and possibly update
        the caret position.
        """
        if self.caret_position == 0:
            self.text = char + self.text
        elif self.caret_position == len(self.text):
            self.text = self.text + char
        else:
            self.text = self.text[:self.caret_position] + char + self.text[self.caret_position:]

        # TODO: Right to Left handling
        self.caret_position += 1


class Button:
    """
    Data model representing one button in a button group/grid.
    """

    def __init__(self, text, action, arg):
        """
        Initialise the model which will display the text specified and
        call the action function with the specified argument when selected.
        """
        self.text = text
        self.action = action
        self.arg = arg


    def select(self):
        """
        Call the action function associate with this button.
        """
        if self.action:
            self.action(self.arg)


class ButtonGroup:
    """
    Data model used to describe a grid of Buttons.

    Instance varaiables:
    buttons         = List of buttons rows containing a list of buttons (columns).
    rows            = Number of rows in the group.
    columns         = Number of columns per row.
    selected_button = Currently Selected button.
    selected_row    = The row of the currently selected button.
    selected_column =
    """

    def __init__(self, rows, columns):
        """
        Initialise the button group to contain the specified number of rows and
        columns of buttons.
        """
        self.rows = rows
        self.columns = columns
        self.selected_row = -1
        self.selected_column = -1
        self.selected_button = None
        self.buttons = []
        for r in range(rows):
            button_row = []
            for c in range(columns):
                button_row.append(None)
            self.buttons.append(button_row)


    def set_button(self, row, column, button):
        """
        Set the button at the specified row and column to be the one supplied.
        The first button added to the group will be the first selected button.
        """
        self.buttons[row][column] = button
        if self.selected_button == None:
            self.selected_button = button
            self.selected_row = row
            self.selected_column = column


    def get_button(self, row, column):
        """
        Retrieve the button at the specified row and column.
        """
        return self.buttons[row][column]


    def move_up(self):
        """
        Select the button above the currently selected button.
        """
        if self.selected_row == 0:
            for r in range(-1, self.rows * -1, -1):
                if self.buttons[r][self.selected_column]:
                    self.selected_row = self.rows+r
                    self.selected_button = self.buttons[r][self.selected_column]
                    return True
        for r in range(self.selected_row-1, -1, -1):
            if self.buttons[r][self.selected_column]:
                self.selected_row = r
                self.selected_button = self.buttons[r][self.selected_column]
                return True

        for r in range(-1, self.rows * -1, -1):
            if self.buttons[r][self.selected_column]:
                self.selected_row = self.rows+r
                self.selected_button = self.buttons[r][self.selected_column]
                return True



        return False


    def move_down(self):
        """
        Select the button below the currently selected button.
        """
        if self.selected_row + 1 == self.rows:
            for r in range(0, self.rows):
                if self.buttons[r][self.selected_column]:
                    self.selected_row = r
                    self.selected_button = self.buttons[r][self.selected_column]
                    return True
        for r in range(self.selected_row+1, self.rows):
            if self.buttons[r][self.selected_column]:
                self.selected_row = r
                self.selected_button = self.buttons[r][self.selected_column]
                return True

        for r in range(0, self.rows):
            if self.buttons[r][self.selected_column]:
                self.selected_row = r
                self.selected_button = self.buttons[r][self.selected_column]
                return True
        return False


    def move_left(self):
        """
        Select the button to the left of the currently selected button.
        """
        if self.selected_column == 0:
            for c in range(-1, self.columns * -1, -1):
                if self.buttons[self.selected_row][c]:
                    self.selected_column = self.columns+c
                    self.selected_button = self.buttons[self.selected_row][c]
                    return True

        for c in range(self.selected_column - 1, -1, -1):
            if self.buttons[self.selected_row][c]:
                self.selected_column = c
                self.selected_button = self.buttons[self.selected_row][c]
                return True
        return False


    def move_right(self):
        """
        Select the button to the right of the currently selected button.
        """
        if self.selected_column + 1 == self.columns:
            for c in range(0, self.columns, 1):
                if self.buttons[self.selected_row][c]:
                    self.selected_column = c
                    self.selected_button = self.buttons[self.selected_row][c]
                    return True
        for c in range(self.selected_column + 1, self.columns):
            if self.buttons[self.selected_row][c]:
                self.selected_column = c
                self.selected_button = self.buttons[self.selected_row][c]
                return True
        for c in range(0, self.columns, 1):
            if  self.buttons[self.selected_row][c]:
                self.selected_column = c
                self.selected_button = self.buttons[self.selected_row][c]
                return True
        return False


    def set_selected(self, button):
        """
        Set the selected button to the one specified.
        Returns True if the button was selected, False if the button is not in
        the group.
        """
        for r in range(self.rows):
            for c in range(self.columns):
                if self.buttons[r][c] == button:
                    self.selected_row = r
                    self.selected_column = c
                    self.selected_button = button
                    return True
        return False
