# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# skin.py - This is the Freevo top-level skin code.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    Works as a middle layer between the users preferred skin and rest of
#    the system.
#
#    Which skin you want to use is set in freevo_config.py. This small
#    module gets your skin preferences from the configuration file and loads
#    the correct skin implementation into the system.
#
#    The path to the skin implementation is also added to the system path.
#
#    get_singleton() returns an initialized skin object which is kept unique
#    and consistent throughout.
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


import plugin
import config
import sys
import types
import os.path

_singleton = None

# a list of all functions the skin needs to have
__all__ = ( 'Rectange', 'Image', 'Area', 'register', 'delete', 'change_area',
            'set_base_fxd', 'load', 'get_skins', 'get_settings',
            'toggle_display_style', 'get_display_style', 'get_popupbox_style',
            'get_font', 'get_image', 'get_icon', 'items_per_page', 'clear', 'redraw',
            'prepare', 'draw' )


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
        calculate _one_ line. Returns a list:
        string to draw, rest that didn't fit and True if this
        function stopped because of a \n.
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
        Layout the text into lines/pages based on the width,height and font
        supplied.
        """
        self.first_line_index = 0
        self.max_lines = height / font.height
        self.lines = []
        rest = self.text
        while rest:
            line, rest, nl = self.__get_line__(rest, width, font, ' ', False)
            if not line and rest and not nl:
                line, rest, nl = self.__get_line__(rest, width, font, ' -_', False)
                if not line and rest and not nl:
                    line, rest, nl = self.__get_line__(rest, width, font, ' -_', True)

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


def get_singleton():
    """
    Returns an initialized skin object, containing the users preferred
    skin.
    """
    global _singleton
    if _singleton == None:
        # we don't need this for helpers
        if config.HELPER:
            return None

        # Loads the skin implementation defined in freevo_config.py
        exec('import skins.' + config.SKIN_MODULE  + '.' + config.SKIN_MODULE  + \
             ' as skinimpl')

        _debug_('Imported skin %s' % config.SKIN_MODULE,2)

        _singleton = skinimpl.Skin()

    return _singleton


def active():
    """
    returns if the skin is active right now (not cleared)
    """
    return not _singleton.force_redraw

def eval_attr(attr_value, max):
    """
    Returns attr_value if it is not a string or evaluates it substituting max
    for 'MAX' or 'max' in the attr_value string.
    """
    if isinstance(attr_value,types.TupleType):
        global attr_global_dict
        if attr_global_dict is None:
            attr_global_dict = {}

            # Setup idlebar related values
            p = plugin.getbyname('idlebar')
            if p:
                attr_global_dict['idlebar'] = 1
                attr_global_dict['idlebar_height'] = 60
            else:
                attr_global_dict['idlebar'] = 0
                attr_global_dict['idlebar_height'] = 0

            # Setup buttonbar related values
            p = plugin.getbyname('buttonbar')
            if p:
                attr_global_dict['buttonbar'] = 1
                attr_global_dict['buttonbar_height'] = 60
            else:
                attr_global_dict['buttonbar'] = 0
                attr_global_dict['buttonbar_height'] = 0
        attr_str,scale = attr_value
        # Set max values
        if max is not None:
            scaled_max = int(round(float(max) / scale))
            attr_global_dict['MAX'] = scaled_max
            attr_global_dict['max'] = scaled_max

        return int(round(scale * eval(attr_str, attr_global_dict)))

    return attr_value

attr_global_dict = None

if __freevo_app__ == 'main':
    # init the skin
    get_singleton()

    # the all function to this module
    for i in __all__:
        exec('%s = _singleton.%s' % (i,i))

else:
    # set all skin functions to the dummy function so nothing
    # bad happens when we call it from inside a helper
    class dummy_class:
        def __init__(*arg1, **arg2):
            pass

    def dummy_function(*arg1, **arg2):
        pass

    for i in __all__:
        if i[0] == i[0].upper():
            exec('%s = dummy_class' % i)
        else:
            exec('%s = dummy_function' % i)
