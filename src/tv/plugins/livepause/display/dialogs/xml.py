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

USABLE_WIDTH  = config.CONF.width-(config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT)
USABLE_HEIGHT = config.CONF.height-(config.OSD_OVERSCAN_TOP+config.OSD_OVERSCAN_BOTTOM)

fonts = {}
colors = {}
dialog_definitions = {}

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

        components = node.attrs[('', attr)].split(',', 4)
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
            return str(node.attrs[('', attr)])
    return default


def attr_location(node, attr, default):
    """
    return the attribute as a location
    """
    if node.attrs.has_key(('', attr)):
        location_str = node.attrs[('', attr)]

        if location_str == 'top':
            return dialogs.LOCATION_TOP
        elif location_str == 'bottom':
            return dialogs.LOCATION_BOTTOM
        elif location_str == 'right':
            return dialogs.LOCATION_RIGHT
        elif location_str == 'left':
            return dialogs.LOCATION_LEFT
        elif location_str == 'center':
            return dialogs.LOCATION_CENTER
        elif location_str == 'topright':
            return dialogs.LOCATION_TOP_RIGHT
        elif location_str == 'topleft':
            return dialogs.LOCATION_TOP_LEFT
        elif location_str == 'bottomright':
            return dialogs.LOCATION_BOTTOM_RIGHT
        elif location_str == 'bottomleft':
            return dialogs.LOCATION_BOTTOM_LEFT

    return default

def attr_bool(node, attr, default):
    """
    return the attribute as bool
    """
    if node.attrs.has_key(('', attr)):
        value = node.attrs[('', attr)]
        return bool(eval(value))
    return default

def search_file(file, search_dirs):
    for s_dir in search_dirs:
        dfile=os.path.join(s_dir, file)

        if vfs.isfile(dfile):
            return vfs.abspath(dfile)

        if vfs.isfile("%s.png" % dfile):
            return vfs.abspath("%s.png" % dfile)

        if vfs.isfile("%s.jpg" % dfile):
            return vfs.abspath("%s.jpg" % dfile)

    print 'osd error: can\'t find image \"%s\"' % file
    if config.DEBUG:
        print 'image search path is:'
        for s in search_dirs:
            print s
    print
    return ''

def scale_and_save_image(filename, scale):
    root,ext = os.path.splitext(filename)
    new_filename = vfs.getoverlay("%s-%dx%d%s" % (root, USABLE_WIDTH, USABLE_HEIGHT, ext))
    if vfs.exists(new_filename) and vfs.mtime(new_filename) > vfs.mtime(filename):
        return new_filename

    image = imlib2.open_without_cache(filename)
    new_width = int(float(image.width) * scale[0])
    new_height = int(float(image.height) * scale[1])
    image = image.scale((new_width, new_height))
    # Make sure the file can be created.
    vfs.open(new_filename, 'w').close()
    image.save(new_filename)

    return new_filename

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

    def instantiate(self, dialog):
        #Resolve font
        font = resolve_font(self.font)

        #Resolve colors
        fgcolor = resolve_color(self.fgcolor)
        bgcolor = resolve_color(self.bgcolor)

        dialog.add_text(self.pos, self.size, self.expression,
                        font, fgcolor, bgcolor, self.valign, self.align)

class Image(XMLOSDObject):
    def __init__(self, node, scale):
        XMLOSDObject.__init__(self, node, scale)
        self.expression = attr_str(node, 'expression', 'True')
        filename = attr_str(node, 'src', '')
        if filename:
            filename = search_file(filename,
                                   [os.path.join(config.IMAGE_DIR, 'osd'),
                                   config.IMAGE_DIR])
            self.filename = scale_and_save_image(filename, scale)
        else:
            self.filename = ''

    def instantiate(self, dialog):
        dialog.add_image(self.pos, self.size, self.filename, self.expression)

class Percent(Image):
    def __init__(self, node, scale):
        Image.__init__(self, node, scale)
        self.vertical = attr_bool(node, 'vertical', False)

    def instantiate(self, dialog):
        dialog.add_percent(self.pos, self.size,
                           self.vertical, self.filename, self.expression)

class Dialog(object):
    def __init__(self, node, scale):
        self.name = attr_str(node, 'name', '')
        width = attr_int(node, 'width', 0, scale[0])
        height = attr_int(node, 'height', 0, scale[1])
        self.size = (width, height)
        x = attr_int(node, 'x', 0, scale[0])
        y = attr_int(node, 'y', 0, scale[1])
        self.position = (x,y)

        self.osd_objects = []
        for node in node.children:
            if node.name == 'text':
                self.osd_objects.append(Text(node, scale))
            elif node.name == 'image':
                self.osd_objects.append(Image(node, scale))
            elif node.name == 'percent':
                self.osd_objects.append(Percent(node, scale))

    def instantiate(self):
        dialog = skin.register_definition(self.name, self.position, self.size)

        for osd_object in self.osd_objects:
            osd_object.instantiate(dialog)

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
    colors[label] = value

def resolve_color(color):
    if isinstance(color, str):
        if color in colors:
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

    scale = (float(USABLE_WIDTH)/float(w),
             float(USABLE_HEIGHT)/float(h))

    for node in node.children:
        if node.name == 'font':
            parse_font(node, scale)
        elif node.name == 'color':
            parse_color(node)
        elif node.name == 'osd':
            dialog = Dialog(node,scale)
            dialog_definitions[dialog.name] = dialog


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

    parser = util.fxdparser.FXD(filename)
    parser.set_handler('osds', osds_callback)
    parser.parse()

def load(filename):
    global fonts, colors, dialog_definitions
    fonts = {}
    colors = {}
    dialog_definitions = {}

    parse(filename)

    prepare_fonts()

    for dialog in dialog_definitions.values():
        dialog.instantiate()


