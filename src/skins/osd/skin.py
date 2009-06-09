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
import copy

import config

from time import strftime

from kaa import imlib2
from util import vfs, objectcache

widget_styles = {}
definitions = {}
icontheme = None
# Dictionary mapping <filename>-<scaletype>-<size> to an image
image_cache = objectcache.ObjectCache(30, 'dialog images')

USABLE_WIDTH  = config.CONF.width-(config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT)
USABLE_HEIGHT = config.CONF.height-(config.OSD_OVERSCAN_TOP+config.OSD_OVERSCAN_BOTTOM)
USABLE_RESOLUTION = '%dx%d' % (USABLE_WIDTH, USABLE_HEIGHT)

# Make sure that the font path is added to imlib2
imlib2.add_font_path(config.FONT_DIR)

def register_definition(name, position, size):
    osdcontainer = OSDDialog(name, position, size)
    definitions[name] = osdcontainer
    return osdcontainer

def get_definition(name):
    if name in definitions:
        return definitions[name]
    return None

def register_widget_style(name, states):
    widget_styles[name] = states

def unregister_widget_style(name):
    global widget_styles
    if name in widget_styles:
        del widget_styles[name]

def get_widget_style(name):
    if name in widget_styles:
        return widget_styles[name]
    return {}

def set_icon_theme(theme):
    global icontheme
    icontheme = theme

class OSDDialog(object):
    def __init__(self, name, position, size):
        self.name = name
        self.position = position
        self.size = size
        self.objects = []
        self.image = None

    def add_text(self, pos, size, expr, font, fgcolor, bgcolor, valign, halign):
        self.objects.append(OSDText(pos, size, expr, font, fgcolor, bgcolor, valign, halign))

    def add_image(self, pos, size, image, expr):
        self.objects.append(OSDImage(pos, size, image, expr))

    def add_percent(self, pos, size, vertical, images, expr):
        self.objects.append(OSDPercent(pos, size, vertical, images, expr))

    def add(self, obj):
        self.objects.append(obj)

    def get_widget_at(self, pos):
        if pos[0] > self.position[0] and pos[0] < self.position[0] + self.size[0] and \
            pos[1] > self.position[1] and pos[1] < self.position[1] + self.size[1]:
            x = pos[0] - self.position[0]
            y = pos[1] - self.position[1]
            for obj in self.objects:
                if isinstance(obj, OSDWidget):
                    if x > obj.pos[0] and x < obj.pos[0] + obj.size[0] and \
                        y > obj.pos[1] and y < obj.pos[1] + obj.size[1]:
                        return obj.name
        return None


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
                report_error('Caught exception while processing OSD element!' + traceback.format_exc())
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

    def __str__(self):
        return '%s (%d,%d) %dx%d' % (self.__class__.__name__, self.pos[0], self.pos[1], self.size[0], self.size[1])

class OSDText(OSDObject):
    def __init__(self, pos, size, expr, font, fgcolor, bgcolor, valign, halign):
        OSDObject.__init__(self, pos, size)
        _debug_('OSDText (%s,%s) %sx%s "%s" %s %s' % (pos[0], pos[1], size[0], size[1], expr, valign, halign), 2)
        self.expr = expr
        self.font = font
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.valign = valign
        self.halign = halign


    def render(self, image, value_dict):
        try:
            to_render = eval(self.expr, globals(), value_dict)
        except:
            report_error('Failed to evalutate text expression \"%s\"' % self.expr)
            to_render = ''
        x = eval_or_int(self.pos[0], value_dict)
        y = eval_or_int(self.pos[1], value_dict)
        self.__drawstring(image, to_render, (x,y), self.size,
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


class OSDImage(OSDObject):
    def __init__(self, pos, size, image, expr, image_expr=None, scale=None):
        OSDObject.__init__(self, pos, size)
        _debug_('OSDImage (%s,%s) %sx%s "%s" "%s" "%s" "%s"' % (pos[0], pos[1], size[0], size[1], image, expr, image_expr, scale), 2)
        self.image_name = image
        self.image_expr = image_expr
        self.image = None
        self.scale = scale
        self.expr = expr

    def prepare(self):
        if self.image_name:
            self.image = get_image(self.image_name, self.scale, self.size)


    def render(self, image, value_dict):
        try:
            should_draw = eval(self.expr, value_dict)
        except:
            report_error('Failed to evalutate display expression \"%s\"' % self.expr)
            should_draw = False

        if should_draw:
            to_draw = None
            if self.image_expr:
                try:
                    image_name = eval(self.image_expr, value_dict)
                    image_name = find_image(image_name)
                    to_draw = get_image(image_name, self.scale, self.size)
                except:
                    report_error('Failed to evalutate image expression \"%s\"' % self.image_expr)
            else:
                to_draw = self.image
            if to_draw:
                x = eval_or_int(self.pos[0], value_dict)
                y = eval_or_int(self.pos[1], value_dict)
                image.blend(to_draw, dst_pos=(x,y))

    def finish(self):
        self.image = None

class OSDPercent(OSDImage):
    def __init__(self, pos, size, vertical, image, expr):
        OSDImage.__init__(self, pos, size, image, expr)
        _debug_('OSDPercent (%s,%s) %sx%s "%s" "%s" %s' % (pos[0], pos[1], size[0], size[1], image, expr, vertical), 2)
        self.vertical = vertical

    def render(self, image, value_dict):
        try:
            percent = min(1.0, max(0.0, eval(self.expr, value_dict)))
        except:
            report_error('Failed to evaluate percent expression \"%s\"' % self.expr)

        if self.vertical:
            im_x = 0
            x = eval_or_int(self.pos[0], value_dict)
            w = self.size[0]
            h = int(float(self.size[1]) * percent)
            im_y = self.size[1] - h
            y = eval_or_int(self.pos[1], value_dict) + im_y

        else:
            im_x = 0
            im_y = 0
            x = eval_or_int(self.pos[0], value_dict)
            y = eval_or_int(self.pos[1], value_dict)
            w = int(float(self.size[0]) * percent)
            h = self.size[1]

        image.blend(self.image,src_pos=(im_x,im_y), src_size=(w,h), dst_pos=(x,y))

class OSDWidget(OSDObject):
    def __init__(self, pos, size, unscaled_size, name, style, navigation=None):
        OSDObject.__init__(self, pos, size)
        _debug_('OSDWidget (%s,%s) %sx%s "%s" "%s"' % (pos[0], pos[1], size[0], size[1], name, style), 2)
        self.name = name
        self.style = style
        self.unscaled_size = unscaled_size
        self.navigation = navigation
        self.image = None
        self.last_state = None
        self.cached_objects = None
        self.first_render = False

    def prepare(self):
        self.image = imlib2.new(self.size)
        self.first_render = True

    def render(self, image, value_dict):
        if self.name in value_dict:
            self.image.clear()
            model = value_dict[self.name]
            self.render_widget(self.image, model)
            image.blend(self.image, dst_pos=self.pos)
        else:
            report_error('Model (%s) not found!' % self.name)
        self.first_render = False

    def finish(self):
        self.image = None
        self.last_state = None
        if self.cached_objects:
            for obj in self.cached_objects:
                obj.finish()
            self.cached_objects = None

    def render_widget(self, image, model):
        state = model.get_state()
        if self.last_state != state:
            if self.cached_objects:
                for obj in self.cached_objects:
                    obj.finish()

            self.cached_objects = []
            self.last_state = state

            state_styles = widget_styles[self.style]
            if state in state_styles:
                objects = state_styles[state]
                widget_dict = {'model':model, 'width':self.unscaled_size[0], 'height':self.unscaled_size[1]}

                for obj in objects:
                    obj = copy.copy(obj)
                    x = eval_or_int(obj.pos[0], widget_dict)
                    y = eval_or_int(obj.pos[1], widget_dict)
                    w = eval_or_int(obj.size[0], widget_dict)
                    h = eval_or_int(obj.size[1], widget_dict)
                    obj.pos = (x,y)
                    obj.size = (w, h)
                    self.cached_objects.append(obj)
                    obj.prepare()
            else:
                report_error('State (%s) not defined in widget style %s' % (state, self.style))

        for obj in self.cached_objects:
            obj.render(image, {'model':model})

    def __str__(self):
        return '%s %s (%s) (%d,%d) %dx%d' % (self.__class__.__name__, self.name, self.style, self.pos[0], self.pos[1], self.size[0], self.size[1])

def eval_or_int(exp, exp_dict):
    if isinstance(exp, int):
        return exp
    return int(float(eval(exp[0], exp_dict)) * exp[1])


class OSDMenu(OSDWidget):
    def __init__(self, pos, size, unscaled_size, name, style, items_per_page):
        super(OSDMenu, self).__init__(pos, size, unscaled_size, name, style)
        _debug_('OSDMenu (%s,%s) %sx%s "%s" "%s" %d' % (pos[0], pos[1], size[0], size[1], name, style, items_per_page), 2)
        self.items_per_page = items_per_page
        self.items = []
        item_h = size[1] / items_per_page
        unscaled_item_h = unscaled_size[1] / items_per_page
        y = 0
        item = 0
        while item < items_per_page:
            self.items.append(OSDWidget((0,y), (self.size[0], item_h), ( unscaled_size[0], unscaled_item_h), 'item%d' % item, '%s_item' % style))
            y += item_h
            item += 1

    def prepare(self):
        super(OSDMenu, self).prepare()
        for item in self.items:
            item.prepare()


    def render_widget(self, image, model):
        if self.first_render:
            model.layout(self.items_per_page, self.pos, self.size)

        super(OSDMenu, self).render_widget(image, model)

        item = 0
        while item < self.items_per_page:
            item_model = model.get_page_item(item)
            if item_model is None:
                break
            self.items[item].render(image, {self.items[item].name:item_model})
            item += 1


    def finish(self):
        super(OSDMenu, self).finish()
        for item in self.items:
            item.finish()

def get_image(filename, scale, size):
    cache_key = '%s-%s-%dx%d' % (filename, scale, size[0], size[1])

    # First check the loaded image cache
    image = image_cache[cache_key]

    # Second check the on disk cache
    if config.CACHE_IMAGES and not image:
        if vfs.isoverlay(filename):
            cache_dir = os.path.dirname(filename)
        else:
            cache_dir = vfs.getoverlay(filename)
        root,ext = os.path.splitext(filename)
        cache_file = '%s-%s%s' % (USABLE_RESOLUTION, cache_key, ext)
        cache_filename = os.path.join(cache_dir, cache_file)

        if vfs.exists(cache_filename) and vfs.mtime(cache_filename) > vfs.mtime(filename):
            image = imlib2.load(cache_filename)
            image_cache[cache_key] = image

    # Finally load the image and scale it as required.
    if not image:
        image = imlib2.open(filename)
        w = image.width
        h = image.height
        src_size = (image.width, image.height)

        if scale == 'horizontal':
            w = size[0]
            dst_size = (w, h)

        elif scale == 'vertical':
            h = size[1]
            dst_size = (w, h)

        elif scale == 'both':
            w = size[0]
            h = size[1]
            dst_size = (w, h)

        elif scale == 'aspect':
            aspect_ratio = float(w) / float(h)
            w = size[0]
            h = int(float(w) / aspect_ratio)
            if h > size[1]:
                w = int(float(size[1]) * aspect_ratio)
                h = size[1]

            dst_size = (w, h)

        else:
            if w > size[0]:
                w = size[0]
            if h > size[1]:
                h = size[1]
            size = (w, h)
            src_size = size
            dst_size = size
        _debug_('Creating image %s (%dx%d) of size %dx%d using scale %s' % (filename, src_size[0],src_size[1], dst_size[0], dst_size[1], scale), 2)
        image = image.scale(dst_size, src_size=src_size)

        image_cache[cache_key] = image

        if config.CACHE_IMAGES:
            if not vfs.exists(cache_dir):
                os.makedirs(cache_dir)
            image.save(cache_filename)

    return image


def find_image(filename):
    _debug_('Looking for %s (icontheme %s)' % (filename, icontheme), 2)
    if icontheme:
        dirs = [os.path.join(config.IMAGE_DIR, 'osd', icontheme),
                os.path.join(config.ICON_DIR, 'osd', icontheme)]
    else:
        dirs = []
    dirs = dirs + [os.path.join(config.IMAGE_DIR, 'osd'),
                   os.path.join(config.ICON_DIR, 'osd'),
                   config.IMAGE_DIR,
                   config.ICON_DIR]
    for dir in dirs:
        dfile=os.path.join(dir, filename)

        if vfs.isfile(dfile):
            return vfs.abspath(dfile)

        if vfs.isfile("%s.png" % dfile):
            return vfs.abspath("%s.png" % dfile)

        if vfs.isfile("%s.jpg" % dfile):
            return vfs.abspath("%s.jpg" % dfile)

    report_error('Can\'t find image \"%s\"' % filename)

    if config.DEBUG:
        _debug_('image search path is:')
        for dir in dirs:
            _debug_(dir)

    return ''

def _report_error(error):
    _debug_(error, DWARNING)

report_error = _report_error
