# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# xml dialog definition module for livepause osd
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
import os.path

import skin

import util.vfs as vfs
import util.fxdparser
from kaa import imlib2

__all__ = ['load']


fonts = {}
colors = {}
dialog_definitions = {}
widget_styles = {}

def attr_int(node, attr, default, scale=1.0):
    """
    return the attribute as integer
    """
    try:
        if node.attrs.has_key(('', attr)):
            val = node.attrs[('', attr)]

            try:
                value = eval(val)
                return int(round(scale * value))
            except:
                return ('int(%s)' % str(val), scale)

    except ValueError:
        pass
    return default

def attr_str(node, attr, default):
    """
    return the attribute as string
    """
    if node.attrs.has_key(('', attr)):
        return node.attrs[('', attr)].encode(config.LOCALE)
    return default

def attr_color(node, attr, default, allow_names=True):
    """
    return the attribute as tuple of 3 or 4 values
    """
    if node.attrs.has_key(('', attr)):
        value = node.attrs[('', attr)]
        components = value.split(',', 4)
        if len(components) == 4:
            result = (int(components[0]),
                      int(components[1]),
                      int(components[2]),
                      int(components[3]))
            return result
        elif len(components) == 3:
            result = (int(components[0]),
                      int(components[1]),
                      int(components[2]))
            return result
        else:
            if value:
                return str(value)
            else:
                # When a empty string is supplied return the default.
                return default
    return default


def attr_bool(node, attr, default):
    """
    return the attribute as bool
    """
    if node.attrs.has_key(('', attr)):
        value = node.attrs[('', attr)].title()
        return bool(eval(value))
    return default


def scale_and_save_image(filename, scale):
    if scale == (1.0, 1.0):
        return filename

    root,ext = os.path.splitext(filename)
    cache_dir = vfs.getoverlay(filename)
    cache_file = '%dx%d%s' % (skin.USABLE_WIDTH, skin.USABLE_HEIGHT, ext)
    cache_filename = os.path.join(cache_dir, cache_file)
    _debug_('Looking for %s' % cache_filename)
    if vfs.exists(cache_filename) and vfs.mtime(cache_filename) > vfs.mtime(filename):
        return cache_filename
    image = imlib2.open_without_cache(filename)
    new_width = int(float(image.width) * scale[0])
    new_height = int(float(image.height) * scale[1])
    image = image.scale((new_width, new_height))

    # Make sure the file can be created.
    if not vfs.exists(cache_dir):
        os.makedirs(cache_dir)
    image.save(cache_filename)

    return cache_filename

class XMLOSDObject(object):
    def __init__(self, node, scale):
        x = attr_int(node, 'x', 0, scale[0])
        y = attr_int(node, 'y', 0, scale[1])
        width = attr_int(node, 'width', 0, scale[0])
        height = attr_int(node, 'height', 0, scale[1])

        self.pos =  (x,y)
        self.size = (width, height)


class Text(XMLOSDObject):
    def __init__(self, node, scale):
        XMLOSDObject.__init__(self, node, scale)
        self.font = attr_str(node, 'font', '')
        self.align = attr_str(node, 'align', 'left')
        self.valign = attr_str(node, 'valign', 'top')

        self.fgcolor = attr_color(node, 'fgcolor', None)
        self.bgcolor = attr_color(node, 'bgcolor', None)

        self.expression = attr_str(node, 'expression', '')

    def instantiate(self):
        #Resolve font
        font = resolve_font(self.font)

        #Resolve colors
        fgcolor = resolve_color(self.fgcolor)
        bgcolor = resolve_color(self.bgcolor)

        return skin.OSDText(self.pos, self.size, self.expression,
                        font, fgcolor, bgcolor, self.valign, self.align)

class Image(XMLOSDObject):
    def __init__(self, node, scale):
        XMLOSDObject.__init__(self, node, scale)
        self.expression = attr_str(node, 'expression', 'True')
        self.src = attr_str(node, 'src', '')
        self.srcexpr = attr_str(node, 'srcexpr', '')
        self.scale = scale
        self.scale_type = attr_str(node, 'scale', 'noscale')


    def resolve_src(self):
        if self.src:
            self.src = skin.find_image(self.src)
            if self.scale_type == 'noscale':
                # Only scale the image to the overall geometry, not to the size
                # of the area.
                self.src = scale_and_save_image(self.src, self.scale)
        else:
            self.src = ''


    def instantiate(self):
        self.resolve_src()
        return skin.OSDImage(self.pos, self.size, self.src, self.expression, self.srcexpr, self.scale_type)

class Percent(Image):
    def __init__(self, node, scale):
        Image.__init__(self, node, scale)
        self.vertical = attr_bool(node, 'vertical', False)

    def instantiate(self):
        self.resolve_src()
        return skin.OSDPercent(self.pos, self.size,
                           self.vertical, self.src, self.expression)


class Widget(XMLOSDObject):
    def __init__(self, node, scale):
        XMLOSDObject.__init__(self, node, scale)
        width = attr_int(node, 'width', 0, 1.0)
        height = attr_int(node, 'height', 0, 1.0)
        self.original_size = (width, height)
        self.name = attr_str(node, 'name', '')
        self.style = attr_str(node, 'style', '')
        left  = attr_str(node, 'left', None)
        right = attr_str(node, 'right', None)
        up    = attr_str(node, 'up', None)
        down  = attr_str(node, 'down', None)
        self.navigation = (left,right,up,down)

    def instantiate(self):
        return skin.OSDWidget(self.pos, self.size, self.original_size, self.name, self.style, self.navigation)


class Menu(Widget):
    def __init__(self, node, scale):
        Widget.__init__(self, node, scale)
        self.items_per_page = attr_int(node, 'itemsperpage', 5)

    def instantiate(self):
        return skin.OSDMenu(self.pos, self.size, self.original_size, self.name, self.style, self.items_per_page)


class Dialog(object):
    def __init__(self, node, scale):
        self.name = attr_str(node, 'name', '')
        width = attr_int(node, 'width', 0, scale[0])
        height = attr_int(node, 'height', 0, scale[1])
        self.size = (width, height)
        x = attr_int(node, 'x', 0, scale[0]) + config.OSD_OVERSCAN_LEFT
        y = attr_int(node, 'y', 0, scale[1]) + config.OSD_OVERSCAN_TOP
        self.position = (x,y)

        self.osd_objects = []
        for node in node.children:
            if node.name == 'text':
                self.osd_objects.append(Text(node, scale))
            elif node.name == 'image':
                self.osd_objects.append(Image(node, scale))
            elif node.name == 'percent':
                self.osd_objects.append(Percent(node, scale))
            elif node.name == 'widget':
                self.osd_objects.append(Widget(node, scale))
            elif node.name == 'menu':
                self.osd_objects.append(Menu(node, scale))

    def instantiate(self):
        dialog = skin.register_definition(self.name, self.position, self.size)

        for osd_object in self.osd_objects:
            dialog.add(osd_object.instantiate())

class XMLFont(object):
    def __init__(self, node, scale):
        self.label = attr_str(node, 'label', '')
        self.name = attr_str(node, 'name', '')
        self.size = attr_int(node, 'size', 0, scale[1])
        self.color = attr_color(node, 'color', (0 , 0, 0))
        self.font = None

    def instantiate(self):
        if not self.font:
            color = resolve_color(self.color)
            self.font = imlib2.load_font(self.name, self.size)

            if self.font:
                self.font.set_color(color)

def parse_style_state(snode, scale):
    objects = []

    for node in snode.children:
        if node.name == 'text':
            objects.append(Text(node, scale))
        elif node.name == 'image':
            objects.append(Image(node, scale))
        elif node.name == 'percent':
            objects.append(Percent(node, scale))

    return objects

def parse_widget_style(node, scale):
    name = attr_str(node, 'name', '')
    style_states = {}
    for snode in node.children:
        if snode.name == 'widgetstate':
            state_name = attr_str(snode, 'state', '')
            style_states[state_name] = parse_style_state(snode, scale)

    widget_styles[name] = style_states


def instantiate_widget_styles():
    for name, states in widget_styles.items():
        skin_states = {}
        for state, components in states.items():
            objects = []
            for component in components:
                objects.append(component.instantiate())
            skin_states[state] = objects
        skin.register_widget_style(name, skin_states)

def parse_font(node, scale):
    global fonts
    font = XMLFont(node, scale)
    fonts[font.label] = font

def prepare_fonts():
    global fonts
    for font in fonts.values():
        font.instantiate()

def resolve_font(font):
    global fonts
    if font in fonts:
        return fonts[font].font
    else:
        return imlib2.Font(font)

def parse_color(node):
    global colors
    label = attr_str(node, 'label', '')
    value = attr_color(node, 'value', (0 , 0, 0), False)
    _debug_('Color %s = %r' % (label, value))
    colors[label] = value

def resolve_color(color):
    _debug_('Resolving %r type = %r' % (color, type(color)), 2)
    if isinstance(color, str):
        _debug_('Colors %r' %(colors.keys()), 2)
        if color in colors:
            _debug_('Resolved %s to %r' % (color, colors[color]), 2)
            return colors[color]
        else:
            _debug_('Color %s not found!' % color)
            return (0, 0, 0)
    else:
        return color

def osds_callback(fxd, node):
    global dialog_definitions
    file_geometry = attr_str(node, 'geometry', '800x600')
    if file_geometry:
        w, h = file_geometry.split('x')
    else:
        w = config.CONF.width
        h = config.CONF.height

    include  = attr_str(node, 'include', '')

    if include:
        parse(include)

    icontheme = attr_str(node, 'icontheme', None)
    if icontheme:
        skin.set_icon_theme(icontheme)

    scale = (float(skin.USABLE_WIDTH)/float(w),
             float(skin.USABLE_HEIGHT)/float(h))

    for node in node.children:
        if node.name == 'font':
            parse_font(node, scale)
        elif node.name == 'color':
            parse_color(node)
        elif node.name == 'osd':
            dialog = Dialog(node, scale)
            dialog_definitions[dialog.name] = dialog
        elif node.name == 'widgetstyle':
            parse_widget_style(node, scale)


def parse(filename):
    if not vfs.isfile(filename):
        if vfs.isfile(filename+'.fxd'):
            filename += '.fxd'

        elif vfs.isfile(vfs.join(config.SKIN_DIR, 'osd', '%s.fxd' % filename)):
            filename = vfs.join(config.SKIN_DIR, 'osd', '%s.fxd' % filename)

        else:
            filename = vfs.join(config.SKIN_DIR, 'osd', filename)

    if not vfs.isfile(filename):
        _debug_('Failed to load OSD skin file: %s' % filename)
        return
    _debug_('Loading OSD skin file %s' % filename)
    parser = util.fxdparser.FXD(filename)
    parser.set_handler('osds', osds_callback)
    parser.parse()

def load(filename):
    global fonts, colors, dialog_definitions, widget_styles
    fonts = {}
    colors = {}
    dialog_definitions = {}
    widget_styles = {}

    pdir = os.path.join(config.SKIN_DIR, 'plugins/osd')
    if os.path.isdir(pdir):
        for p in util.match_files(pdir, [ 'fxd' ]):
            parse(p)

    parse(filename)

    prepare_fonts()

    for dialog in dialog_definitions.values():
        dialog.instantiate()

    instantiate_widget_styles()
