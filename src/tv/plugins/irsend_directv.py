# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Send commands to a DirecTV receiver using a shell command like
# irsend from Lirc.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:  Plugin wrapper for irsend or any other remote control command.
#
# Todo:  Clean out the junk.
#        Finish testing for irsend_core
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


import os, sys, time, string
import plugin


class PluginInterface(plugin.Plugin):
    """
    Use this plugin if you need to use Lirc's irsend (or similar) command
    to tell an external tuner to change the channel.

    Since MCEUSB transceivers can have 2 transmitters, the chosen
    transmitter must be set in local_conf.py.

    Example usage (local_conf.py):
    |   plugin_external_tuner = plugin.activate('tv.irsend_directv',
    |       args=('/usr/bin/irsend SEND_ONCE <remote_name>', '/usr/bin/irsend SET_TRANSMITTER',))

    Where <remote_name> is the name of the remote you are using to send codes
    with in lircd.conf.
    """
    def __init__(self, command, trans_cmd, enterkey=None):
        plugin.Plugin.__init__(self)

        self.command = command
        self.trans_cmd = trans_cmd
        self.enterkey = enterkey
        self.delay = '0.3'

        plugin.register(self, 'EXTERNAL_TUNER')


    def setChannel(self, chan, transmitter=None):
        transmitter = str(transmitter)
        chan = str(chan)
        digits = len(chan)
        chan_args = ''

        if transmitter:
            self.selectTransmitter(transmitter)
            self.irSleep()

        for i in range(digits):
            self.transmitSignal(chan[i])
            self.irSleep()

        if self.enterkey:
            # Sometimes you need to send "ENTER" or "SELECT"
            # after keying in a code.
            self.transmitSignal(self.enterkey)


    def transmitButton(self, button):
        print 'sending button: %s\n' % button
        self.transmitSignal(button)


    def transmitSignal(self, code):
        sendcmd = '%s %s' % (self.command, code)
        os.system(sendcmd)


    def selectTransmitter(self, transmitter):
        sendcmd = '%s %s' % (self.trans_cmd, transmitter)
        os.system(sendcmd)


    def irSleep(self):
        os.system('sleep %s' % self.delay)
