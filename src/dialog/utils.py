# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo module to handle channel changing.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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


import os.path

import config

import dialog

def get_xine_config_file():
    """
    This function checks to see if the current overlay display supports graphics
    and if so copies the xine config file and modifies the copy to disable the OSD.

    @return: The name of a modified config file if the overlay display supports
    graphics or None if the default should be used.
    """
    config_file = None # Use default
    if dialog.overlay_display_supports_dialogs:
        config_file = os.path.join(config.FREEVO_STATICDIR, 'xine.config')
        user_config_file = os.path.expanduser('~/.xine/config')

        if not os.path.exists(config_file) or \
           os.path.getmtime(user_config_file) > os.path.getmtime(config_file):
            outfile = open(config_file, 'w')
            try:
                infile = open(user_config_file, 'r')
                for line in infile:
                    if line.startswith('gui.osd_enabled'):
                        outfile.write('#' + line)
                    else:
                        outfile.write(line)
            finally:
                try:
                    infile.close()
                except:
                    pass

            outfile.write('#FREEVO: Disabled osd as overlay supports graphics\n')
            outfile.write('gui.osd_enabled:0\n')
            outfile.close()

    return config_file
