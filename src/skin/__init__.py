# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo top-level skin code.
# -----------------------------------------------------------------------
# $Id$
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

"""
Freevo top-level skin module.

Works as a middle layer between the users preferred skin and rest of the
system.

Which skin you want to use is set in freevo_config.py. This small module gets
your skin preferences from the configuration file and loads the correct skin
implementation into the system.

The path to the skin implementation is also added to the system path.

get_singleton() returns an initialized skin object which is kept unique and
consistent throughout.
"""

import plugin
import config
import sys
import types
import os.path

#from models import *

_singleton = None

# a list of all functions the skin needs to have
__skin_functions__ = ( 'Rectange', 'Image', 'Area', 'register', 'delete', 'change_area',
            'set_base_fxd', 'load', 'get_skins', 'get_settings',
            'toggle_display_style', 'get_display_style', 'get_popupbox_style',
            'get_font', 'get_image', 'get_icon', 'items_per_page', 'clear', 'redraw',
            'prepare', 'draw' )



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
        exec('import skins.' + config.SKIN_MODULE + '.' + config.SKIN_MODULE + ' as skinimpl')

        _debug_('Imported skin %r' % (config.SKIN_MODULE,))

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
                attr_global_dict['buttonbar_height'] = config.BUTTONBAR_HEIGHT
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
    for i in __skin_functions__:
        exec('%s = _singleton.%s' % (i,i))

else:
    # set all skin functions to the dummy function so nothing
    # bad happens when we call it from inside a helper
    class dummy_class:
        def __init__(*arg1, **arg2):
            pass

    def dummy_function(*arg1, **arg2):
        pass

    for i in __skin_functions__:
        if i[0] == i[0].upper():
            exec('%s = dummy_class' % i)
        else:
            exec('%s = dummy_function' % i)
