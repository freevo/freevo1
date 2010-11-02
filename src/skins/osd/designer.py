# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# OSD skin designer objects
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
from dialog.widgets import ToggleMenuItemModel
import os
import traceback
import copy

import util.fxdparser
import config

import kaa
from kaa import imlib2

from skins.osd.xml import attr_int, attr_str, attr_color, attr_bool, load as load_skin
import skins.osd.skin as osd_skin

from dialog.widgets import *
#
# Property Types
#

# String - can be followed by either a list of options or a function to call to
#          retrieve the list.
PROP_TYPE_STRING = 'string'

# Text - Multiline text.
PROP_TYPE_TEXT = 'text'

# Int - Followed by a tuple containing the lower and upper bounds
PROP_TYPE_INT    = 'int'

# Image - Filename of an image file (.png or .jpeg/.jpg) in the icon theme directory,
#         or an expression that evaluates to an image file in the icon directory.
PROP_TYPE_IMAGE   = 'image'

# Bool - True of false value
PROP_TYPE_BOOL   = 'bool'

# Option - A fixed list of options one of which must be selected follows this.
PROP_TYPE_OPTION = 'option'

class InvalidValueError(Exception):
    def __init__(self, msg):
        super(InvalidValueError, self).__init__()
        self.msg = msg

class DesignerObject(object):
    """
    Base class for all designer objects.

    @ivar has_children: Whether this object can have children.
    @ivar children: List of children this child contains.
    @ivar parent: The parent of this object.
    @ivar type: String describing the type of object.
    @ivar signals: Available signals include:

        - property-changed: Emitted when a property is changed, passes
          object,property, old_value, new_value

        - child-added: Emitted when a child is added, passes object, child

        - child-removed: Emitted when a child is removed, passes object, child

    @ivar properties: A tuple of tuples containing a property name, text
          description, property type and optionally additional type
          information.

          Property type is one of the following:

            - PROP_TYPE_STRING (string): can be followed by either a list of
              options or a function to call to retrieve the list.

            - PROP_TYPE_INT (int): Followed by a tuple containing the lower and
              upper bounds.

            - PROP_TYPE_IMAGE (image): Filename of an image file (.png or
              .jpeg/.jpg) in the icon theme directory, or an expression that
              evaluates to an image file in the icon directory.

            - PROP_TYPE_BOOL (bool): True of false value

            - PROP_TYPE_OPTION (option): A fixed list of options one of which
              must be selected follows this.
    """
    def __init__(self, node=None):
        self.properties = ()
        self.parent = None
        self.children = None
        self.has_children = False
        self.type = ''
        self.signals = kaa.Signals()
        self.signals['property-changed'] = kaa.Signal()
        self.signals['child-added'] = kaa.Signal()
        self.signals['child-removed'] = kaa.Signal()

    def copy(self):
        node = self.to_fxd_node()
        return self.__class__(node)

    def to_fxd_node(self):
        return None

    def get_prop(self, name):
        return getattr(self, name)

    def set_prop(self, name, value):
        old_value = self.get_prop(name)
        setattr(self, name, value)
        self.signals['property-changed'].emit(self, name, old_value, value)

    def add_child(self, child):
        if self.has_children and self.children is None:
            self.children = []
        self.children.append(child)
        child.parent = self
        if hasattr(child, 'added'):
            child.added(self)
        self.signals['child-added'].emit(self, child)

    def insert_child(self, index, child):
        if self.has_children and self.children is None:
            self.children = []

        self.children.insert(index, child)
        child.parent = self
        if hasattr(child, 'added'):
            child.added(self)
        self.signals['child-added'].emit(self, child)

    def remove_child(self, child):
        if self.children is None:
            return

        self.children.remove(child)
        if hasattr(child, 'removed'):
            child.removed(self)
        child.parent = None
        self.signals['child-removed'].emit(self, child)

    def get_theme(self):
        parent = self.parent
        while parent and not isinstance(parent, ThemeObject):
            parent = parent.parent
        return parent

class ThemeObject(DesignerObject):
    def __init__(self):
        super(ThemeObject, self).__init__()
        self.has_children = True
        self.children = []
        self.type = 'theme'
        self.properties = (
                           ('name', 'Name', PROP_TYPE_STRING),
                           ('description', 'Description', PROP_TYPE_TEXT),
                           ('version', 'Version', PROP_TYPE_STRING),
                           ('author', 'Author', PROP_TYPE_STRING),
                           ('email', 'Email Address', PROP_TYPE_STRING),
                           ('width', 'Width', PROP_TYPE_INT, (0, 0xffff)),
                           ('height', 'Height', PROP_TYPE_INT, (0, 0xffff)),
                           ('icontheme', 'Icon theme', PROP_TYPE_STRING),
                           ('include', 'Parent OSD theme', PROP_TYPE_STRING)
                           )
        self.width = 800
        self.height = 600
        self.icontheme = ''
        self.include= 'base'
        self.name = 'Theme'
        self.author = ''
        self.description = ''
        self.version = '1.0'
        self.email = ''

    def load(self, filename):
        fxd = util.fxdparser.FXD(filename)
        fxd.set_handler('osds', self._load_handler)
        fxd.parse()

    def _load_handler(self, fxd, node):
        file_geometry = attr_str(node, 'geometry', '800x600')
        if file_geometry:
            w, h = file_geometry.split('x')
        else:
            w = config.CONF.width
            h = config.CONF.height

        self.width = int(w)
        self.height = int(h)

        self.include  = attr_str(node, 'include', '')
        if self.include:
            load_skin(self.include)

        self.icontheme = attr_str(node, 'icontheme', '')
        if self.icontheme:
            osd_skin.set_icon_theme(self.icontheme)

        for cnode in node.children:
            obj = None

            if cnode.name == 'font':
                obj = FontObject(cnode)
            elif cnode.name == 'color':
                obj = ColorObject(cnode)
            elif cnode.name == 'osd':
                obj = DialogObject(cnode)
            elif cnode.name == 'widgetstyle':
                obj = WidgetStyleObject(cnode)
            elif cnode.name == 'name':
                self.name = cnode.textof()
            elif cnode.name == 'author':
                self.email = attr_str(cnode, 'email', '')
                self.author = cnode.textof()
            elif cnode.name == 'description':
                self.description = cnode.textof()
            elif cnode.name == 'version':
                self.version = cnode.textof()

            if obj:
                self.add_child(obj)

        for child in self.children:
            if isinstance(child, WidgetStyleObject):
                child.update_widget_style()

    def save(self, filename):
        fxd = util.fxdparser.FXDtree('')
        attrs = (('geometry', '%dx%d' % (self.width, self.height)),)
        if self.icontheme:
            attrs += (('icontheme', self.icontheme),)
        if self.include:
            attrs += (('include', self.include),)

        node = util.fxdparser.XMLnode('osds', attrs)
        fxd.add(node)
        node.children.append(util.fxdparser.XMLnode('name', None, self.name))
        node.children.append(util.fxdparser.XMLnode('author', (('email', self.email),), self.author))
        node.children.append(util.fxdparser.XMLnode('description', None, self.description))
        node.children.append(util.fxdparser.XMLnode('version', None, self.version))
        for child in self.children:
            child_node = child.to_fxd_node()
            node.children.append(child_node)

        fxd.save(filename)

    def set_prop(self, name, value):
        super(ThemeObject, self).set_prop(name, value)
        if name == 'include':
            load_skin(value)

        elif name == 'icontheme':
            osd_skin.set_icon_theme(self.icontheme)

    def get_font(self, name):
        for child in self.children:
            if isinstance(child,FontObject) and child.name == name:
                return child.get_font()
        return imlib2.Font(name)

    def get_color(self, name):
        for child in self.children:
            if isinstance(child,ColorObject) and child.name == name:
                return child.get_color()
        values = name.split(',', 4)
        try:
            if len(values) == 4:
                color = (
                         int(values[0]),
                         int(values[1]),
                         int(values[2]),
                         int(values[3]),
                         )
            else:
                color = (
                         int(values[0]),
                         int(values[1]),
                         int(values[2]),
                         )
            return color
        except:
            pass
        return None

    def get_font_names(self):
        result = []
        for child in self.children:
            if isinstance(child,FontObject):
                result.append(child.name)
        result.sort()
        return result

    def get_color_names(self):
        result = []
        for child in self.children:
            if isinstance(child,ColorObject):
                result.append(child.name)
        result.sort()
        return result

DIALOG_EXAMPLE_INFO = {
    'message'    : { 'message': _('Hello')},
    'volume'     : { 'muted' : False,
                     'volume' : 50,
                     'channel' : 'main',
                     'channel_name': _('Volume')
                   },
    'play_state' : { 'state'             : 'play',
                     'current_time'     : 0,
                     'total_time'       : 100,
                     'current_time_str' : '00:00:00',
                     'total_time_str'   : '00:01:40',
                     'percent'          : 0,
                     'percent_str'      : '0%',
                    },
    '1button'     : { 'button': ButtonModel('OK'),
                      'message': _('Hello')
                    },
    '2button'     : { 'button1': ButtonModel('OK'),
                      'button2': ButtonModel('Cancel'),
                      'message': _('Hello')
                    },
    '3button'     : { 'button1': ButtonModel('Yes'),
                      'button2': ButtonModel('No'),
                      'button3': ButtonModel('Cancel'),
                      'message': _('Hello')
                    },
    'menu'        : { 'title' : _('Menu Title'),
                      'menu'  : MenuModel([ MenuItemModel('Item 1'),
                                            MenuItemModel('Item 2'),
                                            MenuItemModel('Item 3'),
                                            ToggleMenuItemModel('Toggle 4'),
                                            ToggleMenuItemModel('Toggle 5'),
                                            ToggleMenuItemModel('Toggle 6'),
                                            MenuItemModel('Item 7'),
                                            MenuItemModel('Item 8'),
                                            MenuItemModel('Item 9'),
                                          ])
                    },
    'bboptionsmenu': {'menu'  : MenuModel([ MenuItemModel('Item 1'),
                                            MenuItemModel('Item 2'),
                                            MenuItemModel('Item 3'),
                                            MenuItemModel('Item 4'),
                                            MenuItemModel('Item 5'),
                                            MenuItemModel('Item 6'),
                                            MenuItemModel('Item 7'),
                                            MenuItemModel('Item 8'),
                                            MenuItemModel('Item 9'),
                                          ])
                    }
}
DIALOG_EXAMPLE_INFO['menu']['menu'].set_active(True)
DIALOG_EXAMPLE_INFO['bboptionsmenu']['menu'].set_active(True)

class DialogObject(DesignerObject):
    count = 1
    def __init__(self, node=None):
        super(DialogObject, self).__init__(node)
        self.type = 'dialog'
        self.has_children = True
        self.children = []
        self.info_dict = {}
        self.properties = (
                           ('name', 'Name', PROP_TYPE_STRING, ('volume', 'message', '1button', '2button', '3button' , 'menu', 'bboptionsmenu', 'play_state')),
                           ('x', 'X', PROP_TYPE_INT, (0, 2000)),
                           ('y', 'Y', PROP_TYPE_INT, (0, 2000)),
                           ('width', 'Width', PROP_TYPE_INT, (0, 2000)),
                           ('height', 'Height', PROP_TYPE_INT, (0, 2000)),
                           )
        if node:
            self.name = attr_str(node, 'name', '')
            if self.name in DIALOG_EXAMPLE_INFO:
                self.info_dict = copy.copy(DIALOG_EXAMPLE_INFO[self.name])
            self.x = attr_int(node, 'x', 0)
            self.y = attr_int(node, 'y', 0)
            self.width = attr_int(node, 'width', 100)
            self.height = attr_int(node, 'height', 100)
            for cnode in node.children:
                obj = None
                if cnode.name == 'text':
                    obj = TextObject(cnode)
                elif cnode.name == 'image':
                    obj = ImageObject(cnode)
                elif cnode.name == 'percent':
                    obj = PercentObject(cnode)
                elif cnode.name == 'widget':
                    obj = WidgetObject(cnode)
                elif cnode.name == 'menu':
                    obj = MenuObject(cnode)
                if obj:
                    self.add_child(obj)
        else:
            self.name = 'dialog%d' % DialogObject.count
            DialogObject.count += 1

            self.width  = 100
            self.height = 100
            self.x = 0
            self.y = 0

    def set_prop(self, name, value):
        if name == 'name':
            if name in DIALOG_EXAMPLE_INFO:
                self.info_dict = copy.copy(DIALOG_EXAMPLE_INFO[name])
        super(DialogObject, self).set_prop(name, value)

    def to_fxd_node(self):
        node = util.fxdparser.XMLnode('osd', (('name', self.name),
                                              ('x', str(self.x)),
                                              ('y', str(self.y)),
                                              ('width', str(self.width)),
                                              ('height', str(self.height))))
        for child in self.children:
            cnode = child.to_fxd_node()
            node.children.append(cnode)
        return node

    def get_position(self):
        return (self.x, self.y)

    def set_position(self, x, y):
        self.x = x
        self.y = y

    def get_size(self):
        return (self.width, self.height)

    def set_size(self, w, h):
        self.width = w
        self.height = h

    def update_position_size(self):
        x1 = 0xffff
        y1 = 0xffff
        x2 = 0
        y2 = 0
        for child in self.children:
            rect = self.get_child_rect(child)
            x1 = min(x1, self.x + rect[0])
            y1 = min(y1, self.y + rect[1])
            x2 = max(x2, self.x + rect[0] + rect[2])
            y2 = max(y2, self.y + rect[1] + rect[3])

        delta_x = self.x - x1
        delta_y = self.y - y1

        for child in self.children:
            try:
                child.x =str(int(child.x) + delta_x)
            except:
                child.x = child.x + '+%d' %delta_x
            try:
                child.y =str(int(child.y) + delta_y)
            except:
                child.y = child.y + '+%d' %delta_y
        self.x = x1
        self.y = y1
        self.width = x2 - x1
        self.height = y2 - y1


    def get_child_rect(self, child):
        try:
            x = int(eval(child.x, self.info_dict))
        except:
            x = 0
        try:
            y = int(eval(child.y, self.info_dict))
        except:
            y = 0

        try:
            w = int(eval(child.width, self.info_dict))
        except:
            w = 1

        try:
            h = int(eval(child.height, self.info_dict))
        except:
            h = 1

        return (x,y,w,h)

    def find_child(self, x, y):
        result = None
        for child in self.children:
            rect = self.get_child_rect(child)
            if rect[0] <= x and rect[1] <= y and \
                rect[0] + rect[2] > x and rect[1] + rect[3] > y:
                result = child
        return result

    def get_widgets(self):
        result = []
        for child in self.children:
            if isinstance(child, WidgetObject):
                result.append(child)

        return result

    def draw(self):
        img = imlib2.new((self.width, self.height))
        img.clear()
        for child in self.children:
            try:
                child.draw(img, self.info_dict)
            except:
                osd_skin.report_error('Caught exception while processing OSD element!' + traceback.format_exc())
        return img

class ColorObject(DesignerObject):
    count = 1

    def __init__(self, node=None):
        super(ColorObject, self).__init__(node)
        self.properties = (
                           ('name', 'Name', PROP_TYPE_STRING),
                           ('red', 'Red', PROP_TYPE_INT, (0, 0xff)),
                           ('green', 'Green', PROP_TYPE_INT, (0, 0xff)),
                           ('blue', 'Blue', PROP_TYPE_INT, (0, 0xff)),
                           ('alpha', 'Alpha', PROP_TYPE_INT, (0, 0xff)),
                           )

        self.type = 'color'

        if node:
            self.name = attr_str(node, 'label', '')
            value = attr_color(node, 'value', (0 , 0, 0), False)
            self.red = value[0]
            self.green = value[1]
            self.blue = value[2]
            if len(value) == 4:
                self.alpha = value[3]
            else:
                self.alpha = 0xff
        else:
            self.name = 'Color%d' % ColorObject.count
            ColorObject.count += 1
            self.red = 0xff
            self.green = 0xff
            self.blue = 0xff
            self.alpha = 0xff

    def get_color(self):
        return (self.red, self.green, self.blue, self.alpha)

    def to_fxd_node(self):
        return util.fxdparser.XMLnode('color', (('label', self.name),
                                                ('value', '%d,%d,%d,%d' % (self.red, self.green, self.blue, self.alpha)),
                                                ))

class FontObject(DesignerObject):
    count = 1

    def __init__(self, node=None):
        super(FontObject, self).__init__(node)
        self.type = 'font'
        self.properties = (
                           ('name', 'Name', PROP_TYPE_STRING),
                           ('font', 'Font', PROP_TYPE_STRING, self.get_fonts),
                           ('size', 'Size', PROP_TYPE_INT, (1, 100)),
                           ('color', 'Color', PROP_TYPE_STRING),
                           )
        if node:
            self.name = attr_str(node, 'label', '')
            self.font = attr_str(node, 'name', '')
            self.size = attr_int(node, 'size', 0)
            self.color = attr_str(node, 'color', '')
        else:
            self.name = 'Font%d' % FontObject.count
            FontObject.count += 1
            self.font = ''
            self.size = 10
            self.color = ''

    def get_fonts(self):
        fonts = []
        for filename in os.listdir(config.FONT_DIR):
            if filename.endswith('.ttf'):
                fonts.append(filename[:-4])
        fonts.sort()
        return fonts

    def to_fxd_node(self):
        return util.fxdparser.XMLnode('font', (('label', self.name),
                                               ('name', self.font),
                                               ('size', str(self.size)),
                                               ('color', self.color)))

    def get_font(self):
        color = self.get_theme().get_color(self.color)
        font = imlib2.load_font(self.font, self.size)
        if font:
            font.set_color(color)

        return font



class DialogChildObject(DesignerObject):
    def __init__(self, node=None):
        super(DialogChildObject, self).__init__(node)
        self.properties = (('name', 'Name', PROP_TYPE_STRING),
                           ('x', 'X', PROP_TYPE_STRING),
                           ('y', 'Y', PROP_TYPE_STRING),
                           ('width', 'Width', PROP_TYPE_STRING),
                           ('height', 'Height', PROP_TYPE_STRING),
                           )
        if node:
            self.name = attr_str(node, 'name', None)
            self.x = attr_str(node, 'x', '0')
            self.y = attr_str(node, 'y', '0')
            self.width = attr_str(node, 'width', '100')
            self.height = attr_str(node, 'height', '100')
        else:
            self.name = None
            self.x = '0'
            self.y = '0'
            self.width = '100'
            self.height = '100'

        self.skin_object = None

    def get_skin_object(self):
        self.skin_object.pos = ((self.x, 1.0), (self.y, 1.0))
        try:
            self.skin_object.size = (int(self.width), int(self.height))
        except:
            self.skin_object.size = ((self.width, 1.0), (self.height, 1.0))
        return self.skin_object

    def draw(self, img, info_dict):
        obj = self.get_skin_object()
        if obj:
            obj.prepare()
            obj.render(img, info_dict)
            obj.finish()

    def to_fxd_node(self):
        return util.fxdparser.XMLnode( self.type, self.get_attrs())

    def get_attrs(self):
        return (('name', self.name),
                ('x', self.x),
                ('y', self.y),
                ('width', self.width),
                ('height', self.height))

    def get_position(self):
        return self.parent.get_child_rect(self)[:2]

    def set_position(self,x,y):
        self.x = str(x)
        self.y = str(y)

    def get_size(self):
        return self.parent.get_child_rect(self)[2:]

    def set_size(self, width, height):
        self.width = str(width)
        self.height = str(height)


class TextObject(DialogChildObject):
    count = 1
    def __init__(self, node=None):
        super(TextObject, self).__init__(node)
        self.properties = self.properties + (
                                             ('expr', 'Expression', PROP_TYPE_STRING),
                                             ('font', 'Font', PROP_TYPE_STRING, self.get_font_names),
                                             ('align', 'H Align', PROP_TYPE_OPTION, ('left', 'center', 'right')),
                                             ('valign', 'V Align', PROP_TYPE_OPTION, ('top', 'center', 'bottom')),
                                             ('fgcolor', 'Foreground', PROP_TYPE_STRING, self.get_color_names),
                                             ('bgcolor', 'Background', PROP_TYPE_STRING, self.get_color_names),
                                             )
        self.type = 'text'
        if node:
            self.expr = attr_str(node, 'expression', '')
            self.font = attr_str(node, 'font', '')
            self.align = attr_str(node, 'align', 'left')
            self.valign = attr_str(node, 'valign', 'top')
            self.fgcolor = attr_str(node, 'fgcolor', '')
            self.bgcolor = attr_str(node, 'bgcolor', '')
        else:
            self.expr = ''
            self.font = ''
            self.align = 'left'
            self.valign = 'center'
            self.fgcolor = ''
            self.bgcolor = ''
        if self.name is None:
            self.name = 'Text%d' % TextObject.count
            TextObject.count += 1
        self.skin_object = osd_skin.OSDText((self.x, self.y), (self.width, self.height),self.expr, None, None, None, self.valign, self.align)

    def get_font_names(self):
        return self.get_theme().get_font_names()

    def get_color_names(self):
        return self.get_theme().get_color_names()

    def get_attrs(self):
        if self.fgcolor and self.bgcolor:
            color_attrs = (('fgcolor', self.fgcolor), ('bgcolor', self.bgcolor))
        elif self.fgcolor:
            color_attrs = (('fgcolor', self.fgcolor),)
        elif self.bgcolor:
            color_attrs = (('bgcolor', self.bgcolor),)
        else:
            color_attrs = ()
        return super(TextObject,self).get_attrs() + (('expression', self.expr),
                                          ('font', self.font),
                                          ('align', self.align),
                                          ('valign', self.valign),
                                          ) + color_attrs
    def get_skin_object(self):
        if self.fgcolor:
            self.skin_object.fgcolor = self.get_theme().get_color(self.fgcolor)
        else:
            self.skin_object.fgcolor = None

        if self.bgcolor:
            self.skin_object.bgcolor = self.get_theme().get_color(self.bgcolor)
        else:
            self.skin_object.bgcolor = None
        self.skin_object.font = self.get_theme().get_font(self.font)
        self.skin_object.expr = self.expr
        self.skin_object.valign = self.valign
        self.skin_object.halign = self.align
        return super(TextObject, self).get_skin_object()

class ImageObject(DialogChildObject):
    count = 1
    def __init__(self, node=None):
        super(ImageObject, self).__init__(node)
        self.type = 'image'
        self.properties = self.properties + (
                                             ('expr', 'Expression', PROP_TYPE_STRING),
                                             ('src', 'Source', PROP_TYPE_IMAGE),
                                             ('src_is_expr', 'Source is Expression', PROP_TYPE_BOOL),
                                             ('scale', 'Scaling', PROP_TYPE_OPTION, ('noscale', 'horizontal','vertical','both','aspect')),
                                             ('align', 'H Align', PROP_TYPE_OPTION, ('left', 'center', 'right')),
                                             ('valign', 'V Align', PROP_TYPE_OPTION, ('top', 'center', 'bottom')),
                                             )
        if node:
            self.expr = attr_str(node, 'expression', 'True')
            self.src = attr_str(node, 'srcexpr', '')
            if self.src:
                self.src_is_expr = True
            else:
                self.src_is_expr = False
                self.src = attr_str(node, 'src', '')
            self.scale = attr_str(node, 'scale', 'noscale')
            self.align = attr_str(node, 'align', 'left')
            self.valign = attr_str(node, 'valign', 'top')
        else:
            self.expr = 'True'
            self.src = ''
            self.src_is_expr = False
            self.scale = 'noscale'
            self.align = 'left'
            self.valign = 'top'
        if self.name is None:
            self.name = 'Image%d' % ImageObject.count
            ImageObject.count += 1
        self.skin_object = osd_skin.OSDImage((self.x, self.y), (self.width, self.height), None, self.expr, None, self.scale, self.valign, self.align)


    def get_attrs(self):
        attrs = super(ImageObject,self).get_attrs() + (('expression', self.expr),
                 ('scale', self.scale), ('align', self.align), ('valign', self.valign))
        if self.src_is_expr:
            attrs += (('srcexpr', self.src),)
        else:
            attrs += (('src', self.src),)
        return attrs


    def get_skin_object(self):
        if self.src_is_expr:
            self.skin_object.image_name = None
            self.skin_object.image_expr = self.src
        else:
            self.skin_object.image_expr = None
            self.skin_object.image_name =  osd_skin.find_image(self.src)
        self.skin_object.scale = self.scale
        self.skin_object.expr = self.expr
        self.skin_object.valign = self.valign
        self.skin_object.halign = self.align
        return super(ImageObject, self).get_skin_object()

class PercentObject(ImageObject):
    def __init__(self, node=None):
        super(PercentObject, self).__init__(node)
        self.type = 'percent'
        self.properties = self.properties[:-2] + (
                                             ('vertical','Vertical', PROP_TYPE_BOOL),
                                             )
        if node:
            self.vertical = attr_bool(node,'vertical', False)
        else:
            self.vertical = False
        self.skin_object = osd_skin.OSDPercent((self.x, self.y), (self.width, self.height), self.vertical, self.src, self.expr)

    def get_skin_object(self):
        self.skin_object.vertical = self.vertical
        return super(PercentObject, self).get_skin_object()

    def get_attrs(self):
        return super(ImageObject,self).get_attrs() + (('expression', self.expr),
                                                      ('src', self.src),
                                                      ('vertical', str(self.vertical)))

class WidgetObject(DialogChildObject):
    count = 1
    def __init__(self, node=None):
        super(WidgetObject, self).__init__(node)
        self.type = 'widget'
        self.properties = self.properties + (
                                             ('style','Style', PROP_TYPE_STRING),
                                             ('left', 'Navigate Left', PROP_TYPE_OPTION, self.get_navigation_widgets),
                                             ('right', 'Navigate Right', PROP_TYPE_OPTION, self.get_navigation_widgets),
                                             ('up', 'Navigate Up', PROP_TYPE_OPTION, self.get_navigation_widgets),
                                             ('down', 'Navigate Down', PROP_TYPE_OPTION, self.get_navigation_widgets),
                                             )
        if node:
            self.style = attr_str(node, 'style', '')
            self.left  = attr_str(node, 'left', '')
            self.right = attr_str(node, 'right', '')
            self.up    = attr_str(node, 'up', '')
            self.down  = attr_str(node, 'down', '')
        else:

            self.style = ''
            self.right = ''
            self.left = ''
            self.up = ''
            self.down = ''
        if self.name is None:
            self.name = 'widget%d' % WidgetObject.count
            WidgetObject.count += 1
        self.skin_object = osd_skin.OSDWidget((0,0), (0,0), (0,0), self.name, self.style, None)


    def set_prop(self, prop, value):
        if prop == 'name' and not value:
            raise InvalidValueError('Name must be set!')
        super(WidgetObject,self).set_prop(prop, value)

    def get_navigation_widgets(self):
        names = ['']
        for widget in self.parent.get_widgets():
            if widget!= self:
                names.append(widget.name)
        return names

    def get_attrs(self):
        return super(WidgetObject,self).get_attrs() + (('style', self.style),
                                                       ('left', self.left),
                                                       ('right', self.right),
                                                       ('up',self.up),
                                                       ('down', self.down))

    def get_skin_object(self):
        self.skin_object.pos = (int(self.x), int(self.y))
        self.skin_object.size = (int(self.width), int(self.height))
        self.skin_object.unscaled_size = self.skin_object.size
        self.skin_object.name = self.name
        self.skin_object.style = self.style
        return self.skin_object

class MenuObject(WidgetObject):
    def __init__(self, node=None):
        super(MenuObject, self).__init__(node)
        self.type = 'menu'
        self.properties = self.properties[:-2] + (
                                             ('items_per_page', 'Items per page', PROP_TYPE_INT, (2, 100)),
                                             )
        if node:
            self.items_per_page = attr_int(node, 'itemsperpage', 5)
        else:
            self.items_per_page = 5

    def get_attrs(self):
        return super(MenuObject,self).get_attrs() + (('itemsperpage', str(self.items_per_page)),)

    def get_skin_object(self):
        self.skin_object = osd_skin.OSDMenu((int(self.x), int(self.y)),
                                            (int(self.width), int(self.height)),
                                            (int(self.width), int(self.height)),
                                            self.name, self.style, self.items_per_page)
        return self.skin_object

class WidgetStyleObject(DesignerObject):
    count = 1
    def __init__(self, node=None):
        super(WidgetStyleObject, self).__init__()
        self.info_dict = {'width': 100, 'height': 100, 'model':ButtonModel('Test')}

        self.has_children = True
        self.children = []
        if node:
            self.name = attr_str(node, 'name', '')
            for cnode in node.children:
                if cnode.name == 'widgetstate':
                    self.add_child(WidgetStateObject(cnode))
        else:
            self.name = 'Style%d' % WidgetStyleObject.count
            WidgetStyleObject.count += 1

        self.orig_style = None
        self.type = 'style'
        self.properties = (('name', 'Name', PROP_TYPE_STRING),)

    def to_fxd_node(self):
        node = util.fxdparser.XMLnode('widgetstyle', (('name', self.name),))
        for child in self.children:
            cnode = child.to_fxd_node()
            node.children.append(cnode)
        return node

    def set_prop(self, prop, value):
        if prop == 'name':
            osd_skin.unregister_widget_style(self.name)
            if self.orig_style:
                osd_skin.register_widget_style(self.name, self.orig_style)
        super(WidgetStyleObject, self).set_prop(prop, value)

        if prop == 'name':
            self.update_widget_style()

    def removed(self, parent):
        osd_skin.unregister_widget_style(self.name)

    def update_widget_style(self):
        if self.parent == None:
            return
        states = {}
        for child in self.children:
            states[child.name] = child.get_skin_objects()
        self.orig_style = osd_skin.get_widget_style(self.name)
        osd_skin.register_widget_style(self.name, states)

    def add_child(self, child):
        super(WidgetStyleObject, self).add_child(child)
        child.info_dict = self.info_dict
        self.update_widget_style()

    @property
    def width(self):
        return int(self.info_dict['width'])

    @property
    def height(self):
        return int(self.info_dict['height'])


class WidgetStateObject(DialogObject):
    count = 1
    def __init__(self, node=None):
        self.info_dict = {}
        super(WidgetStateObject, self).__init__(node)
        if node:
            self.name = attr_str(node, 'state', '')
        else:
            self.name = 'State%d' % WidgetStyleObject.count
            WidgetStateObject.count += 1
        self.x = 0
        self.y = 0
        self.width = 100
        self.height = 100

        self.type = 'state'
        self.properties = (('name', 'State', PROP_TYPE_STRING,
                            ('normal', 'active', 'disabled', 'pressed',
                             'highlighted', 'normal_selected', 'normal_unselected',
                             'active_selected','active_unselected','disabled_selected',
                             'disabled_unselected','highlighted_selected',
                             'highlighted_unselected')),)


    def get_width(self):
        return int(self.info_dict['width'])

    def set_width(self, w):
        self.info_dict['width'] = w

    width = property(get_width, set_width)

    def get_height(self):
        return int(self.info_dict['height'])

    def set_height(self, h):
        self.info_dict['height'] = h

    height = property(get_height,set_height )

    def set_prop(self, prop, value):
        super(WidgetStateObject, self).set_prop(prop, value)
        self.update_widget_style()

    def add_child(self, child):
        super(WidgetStateObject, self).add_child(child)
        self.update_widget_style()
        child.signals['property-changed'].connect(self.child_prop_changed)

    def remove_child(self, child):
        super(WidgetStateObject, self).remove_child(child)
        self.update_widget_style()
        child.signals['property-changed'].disconnect(self.child_prop_changed)

    def to_fxd_node(self):
        node = util.fxdparser.XMLnode('widgetstate', (('state', self.name),))
        for child in self.children:
            cnode = child.to_fxd_node()
            node.children.append(cnode)
        return node

    def get_skin_objects(self):
        objs = []
        for child in self.children:
            objs.append(child.get_skin_object())
        return tuple(objs)

    def update_widget_style(self):
        if self.parent == None:
            return
        self.parent.update_widget_style()

    def child_prop_changed(self, child, prop, old_value, new_value):
        self.parent.update_widget_style()

    def draw(self):
        img = imlib2.new((self.width, self.height))
        img.clear()
        for child in self.children:
            try:
                obj = copy.copy(child.get_skin_object())
                x = osd_skin.eval_or_int(obj.pos[0], self.info_dict)
                y = osd_skin.eval_or_int(obj.pos[1], self.info_dict)
                w = osd_skin.eval_or_int(obj.size[0], self.info_dict)
                h = osd_skin.eval_or_int(obj.size[1], self.info_dict)
                obj.pos = (x,y)
                obj.size = (w,h)
                obj.prepare()
                obj.render(img, self.info_dict)
                obj.finish()
            except:
                traceback.print_exc()
        return img
