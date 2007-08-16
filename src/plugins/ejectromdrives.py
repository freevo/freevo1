# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ejectromdrives.py - Adds and eject entry to the submenu of items
# -----------------------------------------------------------------------
# $Id
#
# Notes: This plugin adds an entry to the submenu for ejecting the drive
#
# Version: 0.2
#
# Activate:
#   plugin.activate('ejectromdrives')
#
# Bugs:
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
import rc
import event as em
import menu

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin ejects/close the tray of rom drives.

    plugin.activate('ejectromdrives')

    """
    __author__           = 'Gorka Olaizola'
    __author_email__     = 'gorka@escomposlinux.org'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision'

    def __init__(self):
        plugin.ItemPlugin.__init__(self)
        self.item = None

    def actions(self, item):
        self.item = item
        myactions = []

        if item.media and hasattr(item.media, 'id'):
            if item.media.is_mounted():
                item.media.umount()

            if item.media.is_tray_open():
                str = _('Close drive')
            else:
                str = _('Eject drive')

            myactions.append((self.eject, str))

        return myactions


    def eject(self, arg=None, menuw=None):
        """
        ejects or closes tray
        """
        if self.item and self.item.media and hasattr(self.item.media, 'id'):
            _debug_('Item is a CD-ROM drive')

                        # Stop the running video or music in detached mode
            rc.post_event(em.Event(em.BUTTON, arg=em.STOP))

            self.item.media.move_tray(dir='toggle')

            if isinstance(menuw.menustack[-1].selected, menu.MenuItem):
                rc.post_event(em.MENU_BACK_ONE_MENU)
        else:
            _debug_('Item is not a CD-ROM drive')
