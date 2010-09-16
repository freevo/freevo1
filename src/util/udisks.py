# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# DBus Udisk/DeviceKit Disks interface
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

import dbus


bus = dbus.SystemBus()


class DBusDisksProxy(object):
    """
    Common DBus interface class for the disks interface.
    """
    def __init__(self, path):
        """
        Create a new instance with the DBus interface path.
        """
        self.proxy = bus.get_object(self.BUS, path)
        self.disks_iface = dbus.Interface(self.proxy, self.INTF)

    def get_optical_drives(self):
        """
        Retrieve a list of the optical device objects.
        """
        optical = []
        for device_path in self.disks_iface.EnumerateDevices():
            device_proxy = bus.get_object(self.BUS, device_path)
            device = self.DEVICE_CLASS(device_path)
            if device.is_optical():
                optical.append(device)

        return optical

    def get_removable_drives(self):
        """
        Retrieve a list of the removable device objects.
        """
        removable = []
        for device_path in self.disks_iface.EnumerateDevices():
            device_proxy = bus.get_object(self.BUS, device_path)
            device = self.DEVICE_CLASS(device_path)
            if device.is_removable() and not device.is_optical():
                removable.append(device)

        return removable


class DBusDisksDeviceProxy(object):
    """
    Common DBus interface class for Device objects.
    """

    def __init__(self, path):
        """
        Create a new instance with the DBus object path.
        """
        self.proxy = bus.get_object(self.BUS, path)
        self.disks_iface = dbus.Interface(self.proxy, self.INTF)
        self.props_iface = dbus.Interface(self.proxy, "org.freedesktop.DBus.Properties")

    def get_prop(self, name):
        """
        Retrieve a property of the object.
        """
        return self.props_iface.Get(self.INTF, name)

    def is_optical(self):
        """
        Is this an optical device.
        """
        return self.get_prop(self.IS_OPTICAL) and not self.get_prop(self.IS_SYS_INTERNAL)

    def is_removable(self):
        """
        Is this a removable device.
        """
        if self.get_prop(self.IS_SYS_INTERNAL):
            return False
        if self.get_prop(self.IS_REMOVABLE) or self.get_prop(self.CAN_DETACH):
            if not self.get_prop(self.IS_PARTITION_TABLE):
                return True
        return False

    def get_partition_slave(self):
        """
        Retrieve the partition table device object.
        """
        if not self.get_prop(self.IS_PARTITION):
            return None
        return self.__class__(self.get_prop(self.PARTITION_SLAVE))

    def detach(self):
        """
        Request the device be detached.
        """

        self.disks_iface.DriveDetach(dbus.Array([], 's'))

    def unmount(self):
        """
        Unmount the filesystem.
        """
        self.disks_iface.FilesystemUnmount(dbus.Array([], 's'))


class DeviceKitDisksDeviceProxy(DBusDisksDeviceProxy):
    """
    DeviceKit Disks Device object interface
    """
    INTF = "org.freedesktop.DeviceKit.Disks.Device"
    BUS="org.freedesktop.DeviceKit.Disks"
    MOUNT_PATHS = "device-mount-paths"
    IS_MOUNTED = "device-is-mounted"
    IS_SYS_INTERNAL = "device-is-system-internal"
    IS_PARTITION_TABLE = "device-is-partition-table"
    IS_PARTITION = "device-is-partition"
    MEDIA_COMPATIBILITY = "drive-media-compatibility"
    CURRENT_MEDIA = "drive-media"
    CAN_DETACH = "drive-can-detach"
    CAN_EJECT = "drive-is-media-ejectable"
    IS_REMOVABLE = "device-is-removable"
    IS_OPTICAL = "device-is-optical-disc"
    PRESENTATION_NAME = "device-presentation-name"
    PARTITION_SLAVE = "partition-slave"


class UDisksDeviceProxy(DBusDisksDeviceProxy):
    """
    UDisks Device object interface
    """
    INTF = "org.freedesktop.UDisks.Device"
    BUS ="org.freedesktop.UDisks"
    MOUNT_PATHS = "DeviceMountPaths"
    IS_MOUNTED = "DeviceIsMounted"
    IS_SYS_INTERNAL = "DeviceIsSystemInternal"
    IS_PARTITION_TABLE = "DeviceIsPartitionTable"
    IS_PARTITION = "DeviceIsPartition"
    MEDIA_COMPATIBILITY = "DriveMediaCompatibility"
    CURRENT_MEDIA = "DriveMedia"
    CAN_DETACH = "DriveCanDetach"
    CAN_EJECT = "DriveIsMediaEjectable"
    IS_REMOVABLE = "DeviceIsRemovable"
    IS_OPTICAL = "DeviceIsOpticalDisc"
    PRESENTATION_NAME = "DevicePresentationName"
    PARTITION_SLAVE = "PartitionSlave"


class DeviceKitDisksProxy(DBusDisksProxy):
    """
    DBus interface class for DeviceKit Disks
    """
    INTF = "org.freedesktop.DeviceKit.Disks"
    BUS="org.freedesktop.DeviceKit.Disks"
    DEVICE_CLASS = DeviceKitDisksDeviceProxy

    def __init__(self):
        super(DeviceKitDisksProxy, self).__init__("/org/freedesktop/DeviceKit/Disks")


class UDisksProxy(DBusDisksProxy):
    """
    DBus Interface class for udisks
    """
    INTF = "org.freedesktop.UDisks"
    BUS ="org.freedesktop.UDisks"
    DEVICE_CLASS = UDisksDeviceProxy

    def __init__(self):
        super(UDisksProxy, self).__init__("/org/freedesktop/UDisks")


def get_udisks_interface():
    """
    Retrieve the interface to udisk or its predecessor DeviceKit Disks.
    """
    try:
        return UDisksProxy()
    except:
        traceback.print_exc()
    try:
        return DeviceKitDisksProxy()
    except:
        traceback.print_exc()
    return None
