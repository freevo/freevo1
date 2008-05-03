# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dialog definition and rendering module for livepause osd
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

import os.path
import traceback

import config

from time import strftime

from kaa import imlib2

__all__ = ['register_definition', 'get_definition',
           'OSDObject', 'OSDTextObject', 'OSDImageObject', 'OSDPercentObject'
           ]

definitions = {}

def register_definition(name, position, size):
    osdcontainer = OSDDialog(name, position, size)
    definitions[name] = osdcontainer
    return osdcontainer

def get_definition(name):
    if name in definitions:
        return definitions[name]
    return None

class OSDDialog(object):
    def __init__(self, name, position, size):
        # Load background image
        self.name = name
        self.position = position
        self.size = size
        self.objects = []
        self.image = None

    def add_text(self, pos, size, expr, font, fgcolor, bgcolor, valign, halign):
        self.objects.append(OSDTextObject(pos, size, expr, font, fgcolor, bgcolor, valign, halign))

    def add_image(self, pos, size, image, expr):
        self.objects.append(OSDImageObject(pos, size, image, expr))

    def add_percent(self, pos, size, vertical, images, expr):
        self.objects.append(OSDPercentObject(pos, size, vertical, images, expr))

    def add(self, obj):
        self.objects.append(obj)


    def prepare(self):
        # Load background image
        self.image = imlib2.new(self.size)
        for obj in self.objects:
            obj.prepare()

    def render(self, value_dict):
        self.image.clear()
        for obj in self.objects:
            try:
                obj.render(self.image, value_dict)
            except:
                _debug_('Caught exception while processing OSD element!' + traceback.format_exc())

        return self.image

    def finish(self):
        # Release surface
        self.image = None
        for obj in self.objects:
            obj.finish()

class OSDObject(object):
    def __init__(self, pos, size):
        self.pos = pos
        self.size = size

    def prepare(self):
        pass

    def render(self, image, value_dict):
        pass

    def finish(self):
        pass

class OSDTextObject(OSDObject):
    def __init__(self, pos, size, expr, font, fgcolor, bgcolor, valign, halign):
        OSDObject.__init__(self, pos, size)
        self.expr = expr
        self.font = font
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.valign = valign
        self.halign = halign


    def render(self, image, value_dict):
        to_render = eval(self.expr, globals(), value_dict)

        self.__drawstring(image, to_render, self.pos, self.size,
                          self.font, self.fgcolor, self.bgcolor,
                          self.halign, self.valign)

    def __get_string_width(self, font, string):
        w,h,ha,va = font.get_text_size(string)
        return ha

    def __calc_line(self, string, max_width, font, hard,
                                  ellipses, word_splitter):
        """
        calculate _one_ line for drawstringframed.
        @returns: a tuple containing
            - width used
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

        if ellipses:
            # check the width of the ellipses
            ellipses_size = self.__get_string_width(font, ellipses)
            if ellipses_size > max_width:
                # if not even the ellipses fit, we have not enough space
                # until the text is shorter than the ellipses
                width = self.__get_string_width(font, string)
                if width <= max_width:
                    # ok, text fits
                    return (width, string, '', False)
                # ok, only draw the ellipses, shorten them first
                while(ellipses_size > max_width):
                    ellipses = ellipses[:-1]
                    ellipses_size = self.__get_string_width(font, ellipses)
                return (ellipses_size, ellipses, string, False)
        else:
            ellipses_size = 0
            ellipses = ''

        data = None
        while(True):
            if width > max_width - ellipses_size and not data:
                # save this, we will need it when we have not enough space
                # but first try to fit the text without ellipses
                data = c, space, width, last_char_size, last_word_size
            if width > max_width:
                # ok, that's it. We don't have any space left
                break
            if ls == c:
                # everything fits
                return (width, string, '', False)
            if string[c] == '\n':
                # linebreak, we have to stop
                return (width, string[:c], string[c+1:], True)
            if not hard and string[c] in word_splitter:
                # rememeber the last space for mode == 'soft' (not hard)
                space = c
                last_word_size = 0

            # Work out size of line based on whole line as it can be larger
            # than just counting character widths, add a couple of pixels
            # as it seems to undercount by atleast a pixel
            last_char_size = self.__get_string_width(font, string[:c+1])
            width = self.__get_string_width(font, string[:c+1])
            last_word_size = self.__get_string_width(font, string[space:c+1])
            # print '%d : L:"%s" %d W:"%s" %d' %(c, string[:c+1], width, string[space:c+1], last_word_size)
            c += 1

        # restore to the pos when the width was one char to big and
        # incl. ellipses_size
        c, space, width, last_char_size, last_word_size = data

        if hard:
            # remove the last char, than it fits
            c -= 1
            width -= last_char_size

        else:
            # go one word back, than it fits
            c = space
            width -= last_word_size

        # calc the matching and rest string and return all this
        return (width+ellipses_size, string[:c]+ellipses, string[c:], False)


    def __drawstring(self, image, string, pos, size, font, fgcolor, bgcolor, align_h, align_v):
        """
        draws a string (text) in a frame. This tries to fit the
        string in lines, if it can't, it truncates the text,
        draw the part that fit and returns the other that doesn't.

        @param image: the image to draw to.
        @param string: the string to be drawn, supports also <nl>. <tab> is not supported.
             you need to replace it first
        """

        x, y = pos
        width, height = size
        mode = 'soft'
        ellipses = '...'

        if not string:
            return '', (x,y,x,y)

        font_height = (font.ascent + font.descent)
        line_height = font_height * 1.1
        if int(line_height) < line_height:
            line_height = int(line_height) + 1

        if width <= 0 or height < font_height:
            return string, (x,y,x,y)

        num_lines_left   = int((height+line_height-font_height) / line_height)
        lines            = []
        current_ellipses = ''
        hard = mode == 'hard'

        if num_lines_left == 1:
            ellipses = ''
            mode = hard = 'hard'

        while(num_lines_left > 0):
            # calc each line and put the rest into the next
            if num_lines_left == 1:
                current_ellipses = ellipses
            #
            # __calc_line returns a list:
            # width of the text drawn (w), string which is drawn (s),
            # rest that does not fit (r) and True if the breaking was because
            # of a \n (n)
            #

            (w, s, r, n) = self.__calc_line(string, width, font, hard,
                                                          current_ellipses, ' ')
            if s == '' and not hard:
                # nothing fits? Try to break words at ' -_' and no ellipses
                (w, s, r, n) = self.__calc_line(string, width, font, hard,
                                                              None, ' -_')
                if s == '':
                    # still nothing? Use the 'hard' way
                    (w, s, r, n) = self.__calc_line(string, width, font,
                                                                  'hard', None, ' ')
            lines.append((w, s))

            while r and r[0] == '\n':
                lines.append((0, ' '))
                num_lines_left -= 1
                r = r[1:]
                n = True

            if n:
                string = r
            else:
                string = r.strip()

            num_lines_left -= 1

            if not r:
                # finished, everything fits
                break

        # calc the height we want to draw (based on different align_v)
        height_needed = (len(lines) - 1) * line_height + font_height
        if align_v == 'bottom':
            y += (height - height_needed)
        elif align_v == 'center':
            y += int((height - height_needed)/2)

        y0    = y
        min_x = 10000
        max_x = 0

        image.set_font(font)

        for w, l in lines:
            if not l:
                continue

            x0 = x
            try:
                # calc x/y positions based on align
                if align_h == 'right':
                    x0 = x + width - w
                elif align_h == 'center':
                    x0 = x + int((width - w) / 2)

                image.draw_text((x0,y0), l, fgcolor)

            except Exception, e:
                _debug_('Render failed, skipping \'%s\': %s' % (l, e), DERROR)
                if config.DEBUG:
                    traceback.print_exc()

            if x0 < min_x:
                min_x = x0
            if x0 + w > max_x:
                max_x = x0 + w
            y0 += line_height

        return r, (min_x, y, max_x, y+height_needed)


class OSDImageObject(OSDObject):
    def __init__(self, pos, size, image, expr):
        OSDObject.__init__(self, pos, size)
        self.image_name = image
        self.image = None
        self.expr = expr

    def prepare(self):
        self.image = imlib2.open(self.image_name)


    def render(self, image, value_dict):
        if eval(self.expr, value_dict):
            image.blend(self.image, dst_pos=self.pos)

    def finish(self):
        self.image = None

class OSDPercentObject(OSDImageObject):
    def __init__(self, pos, size, vertical, image, expr):
        OSDImageObject.__init__(self, pos, size, image, expr)
        self.vertical = vertical

    def render(self, image, value_dict):
        percent = min(1.0, max(0.0, eval(self.expr, value_dict)))

        if self.vertical:
            im_x = 0
            x = self.pos[0]
            w = self.size[0]
            h = int(float(self.size[1]) * percent)
            im_y = self.size[1] - h
            y = self.pos[1] + im_y

        else:
            im_x = 0
            im_y = 0
            x = self.pos[0]
            y = self.pos[1]
            w = int(float(self.size[0]) * percent)
            h = self.size[1]

        image.blend(self.image,src_pos=(im_x,im_y), src_size=(w,h), dst_pos=(x,y))

# Make sure that the font path is added to imlib2
imlib2.add_font_path(config.FONT_DIR)
