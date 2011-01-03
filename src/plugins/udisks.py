# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in to use the DBus Udisk/DeviceKit Disks interface to retrieve available
# removable devices.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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
import directory

try:
    from util.udisks import *
    udisks_available = True
except ImportError:
    udisks_available = False

class PluginInterface(plugin.Plugin):
    """
    Plug-in to use the DBus Udisk/DeviceKit Disks interface to retrieve available
    removable devices and add them to the Movies,Music, Picture and Games menus.

    Activate with:
    | plugin.activate('udisks')

    """
    def __init__(self):
        if not udisks_available:
            self.reason = "Failed to import dbus"
            return
        plugin.Plugin.__init__(self)
        self.devices = Devices()
        plugin.activate(self.devices, 'video')
        plugin.activate(self.devices, 'audio')
        plugin.activate(self.devices, 'image')
        plugin.activate(self.devices, 'games')

class Devices(plugin.MainMenuPlugin):
    """
    Plug-in to use the DBus Udisk/DeviceKit Disks interface to retrieve available
    removable devices and add them to the a specific menu.

    Activate with:
    | plugin.activate('udisks.Devices', 'video')

    """
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
        self.udisks = get_udisks_interface()

    def items(self, parent):
        items = []
        if self.udisks:
            for drive in self.udisks.get_removable_drives():
                if drive.get_prop(drive.IS_MOUNTED):
                    items.append(DeviceDirItem(drive, parent))
        return items


class DeviceDirItem(directory.DirItem):
    """
    Item class for udisks devices.
    """
    def __init__(self, device, parent):
        self.device = device
        dir = str(self.device.get_prop(device.MOUNT_PATHS)[0])
        directory.DirItem.__init__(self, dir, parent)
        self.display_type = parent.display_type
        self.skin_display_type = parent.display_type

    def actions(self):
        """
        return a list of actions for this item
        """
        actions = directory.DirItem.actions(self)
        actions.append((self.__detach, _('Detach')))
        return actions

    def __detach(self, arg=None, menuw=None):
        if self.device.get_prop(self.device.IS_PARTITION):
            self.device.unmount()
            d = self.device.get_partition_slave()
        else:
            d = self.device
        d.detach()
        menuw.back_one_menu()
