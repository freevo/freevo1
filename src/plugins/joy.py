# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A joystick control plugin for Freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# To use this plugin make sure that your joystick is already working
# properly and then configure JOY_DEV and JOY_CMDS in your local_conf.py.
# You will also need to have plugin.activate('joy') in your config as well.
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
import logging
logger = logging.getLogger("freevo.plugins.joy")


import sys
import os
import select
import struct
import traceback
from time import sleep

import config
import plugin
import rc

rc = rc.get_singleton()

class PluginInterface(plugin.DaemonPlugin):
    """
    A joystick control plugin for Freevo

    To use this plugin make sure that your joystick is already working properly and
    then configure JOY_DEV and JOY_CMDS in your local_conf.py.  You will also need
    to have plugin.activate('joy') in your config as well.

    If you are using the /dev/input/eventX you can use the linux event driver
    instead.
    """

    def __init__(self):
        try:
            self.device_name = config.JOY_DEVICE
            try:
                self.joyfd = os.open(self.device_name, os.O_RDONLY|os.O_NONBLOCK)
                logger.debug('self.joyfd = %s', self.joyfd)
            except OSError:
                self.reason = 'unable to open device %r' % (self.device_name,)
                return
        except AttributeError:
            if config.JOY_DEV == 0:
                self.reason = 'Joystick input module disabled'
                return

            logger.warning('JOY_DEV is deprecated, use JOY_DEVICE instead')
            self.device_name = '/dev/input/js' + str((config.JOY_DEV - 1))
            try:
                self.joyfd = os.open(self.device_name, os.O_RDONLY|os.O_NONBLOCK)
                logger.debug('self.joyfd = %s', self.joyfd)
            except OSError:
                self.device_name = '/dev/js' + str((config.JOY_DEV - 1))
                try:
                    self.joyfd = os.open(self.device_name, os.O_RDONLY|os.O_NONBLOCK)
                    logger.debug('self.joyfd = %s', self.joyfd)
                except OSError:
                    self.reason = 'unable to open device %r' % (self.device_name,)
                    return

        # ok, joystick is working
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'JOY'

        logger.info('Using joystick %s (%s) (sensitivity %s)', config.JOY_DEV, self.device_name, config.JOY_SENS)

        self.poll_interval  = 0.1
        self.poll_menu_only = False
        self.enabled = True


    def config(self):
        return [
            ('JOY_DEV', 1, 'Joystick number, 1 is "/dev/js0" or "/dev/input/js0"'),
            ('JOY_DEVICE', None, 'Joystick device, i.e. "/dev/js0" or "/dev/input/js0"'),
            ('JOY_SENS', 16384, 'Joystick sensitivity'),
            ('JOY_LOCKFILE', None, 'Joystick lock file'),
            ('JOY_CMDS', config.JOY_CMDS, 'Joystick commands'),
         ]


    def shutdown(self):
        try:
            self.joyfd.close()
        except:
            pass


    def poll(self):
        if not self.enabled:
            return

        command = ''
        (r, w, e) = select.select([self.joyfd], [], [], 0)
        logger.log( 8, 'r=%r, w=%r, e=%r', r, w, e)

        self.sensitivity = config.JOY_SENS

        if not r:
            return

        c = os.read(self.joyfd, 8)
        data = struct.unpack('IhBB', c)
        logger.log( 9, 'data=%r', data)
        if data[2] == 1 & data[1] == 1:
            button = 'button '+str((data[3] + 1))
            command = config.JOY_CMDS.get(button, '')

        if data[2] == 2:
            if ((data[3] == 1) & (data[1] < -self.sensitivity)):
                button = 'up'
                command = config.JOY_CMDS['up']
            if ((data[3] == 1) & (data[1] > self.sensitivity)):
                button = 'down'
                command = config.JOY_CMDS['down']
            if ((data[3] == 0) & (data[1] < -self.sensitivity)):
                button = 'left'
                command = config.JOY_CMDS['left']
            if ((data[3] == 0) & (data[1] > self.sensitivity)):
                button = 'right'
                command = config.JOY_CMDS['right']

        if command != '':
            logger.debug('Translation: "%s" -> "%s"', button, command)
            command = rc.key_event_mapper(command)
            if command:
                if not config.JOY_LOCKFILE:
                    rc.post_event(command)
                elif not os.path.exists(config.JOY_LOCKFILE):
                    rc.post_event(command)


    def enable(self):
        """ enable the joystick """
        # remove any pending events
        while 1:
            (r, w, e) = select.select([self.joyfd], [], [], 0)
            logger.debug('r=%r, w=%r, e=%r', r, w, e)
            if not r:
                break
            c = os.read(self.joyfd, 8)
        self.enabled = True
        return


    def disable(self):
        """ disable the joystick """
        self.enabled = False
        return
