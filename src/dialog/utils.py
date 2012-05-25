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
from dialog.dialogs import MessageDialog 

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


def show_message(message, name='message', duration=None):
    """
    Helper function that shows the skinnable osd message dialog
    @param message:  message to be displayed
    @param name:     name of the dialog used to load  appropriate skin object
                     Default is ’message’, ‘status’ is also available. 
                     See dialog/dialogs.py and osd skin definitions for available
                     names/dialog types
    @param duration: duration the msg is displayed. Default is None which defaults
                     to the standard duration of the MessageDialog, currently 3 secs
                     0 will display indefinitely, until hide_message() is called
                     In this cae caller is responsible for cleaning up, either hide 
                     and finish the dialog or call dialog.util.hide_message()!
    @return:         instantiated MessageDialog object, needed for subsequent call
                     to hide_message
    """
    dialog = MessageDialog(message)
    dialog.name = name
    if duration is None:
        dialog.show()
    else:
        dialog.show(duration)
    
    return dialog
    

def hide_message(dialog):
    """
    Helper function that hides and finishes the osd message dialog, 
    created by show_dialog()
    @param dialog:   dialog object returned previously by show_dialog()
    """
    # check if we have a valid object and check the type too, in case
    # someone passed us wrong type, to prevent runtime errors.
    if dialog and isinstance(dialog, MessageDialog):
        dialog.hide()
        dialog.finish()
