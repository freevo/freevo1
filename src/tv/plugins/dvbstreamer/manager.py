# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# manager.py - the Freevo DVBStreamer module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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
from tv.plugins.dvbstreamer import comms

class DVBStreamerManager:
    """
    Class to control dvbstreamer servers.
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.controllers = {}


    def get_udp_mrl(self, ip_address, port):
        """
        Get the mrl to use for dvbstreamer and xine.
        """
        return 'udp://%s:%d' %(ip_address, port)


    def get_file_mrl(self, filename):
        """
        Get the dvbstreamer mrl to use for saving to a file.
        """
        return 'file://%s' % filename


    def enable_udp_output(self, adapter, ip_address, port):
        """
        Enable UDP output to localhost:1234
        """
        self.set_mrl(adapter, self.get_udp_mrl(ip_address,port))


    def enable_file_output(self, adapter, filename):
        """
        Enable output to the specified file.
        """
        self.set_mrl(adapter, self.get_file_mrl(filename))

    def disable_output(self, adapter):
        """
        Disable output from the specified dvbstreamer instance.
        """
        _debug_('Disabling output on adapter %s' % adapter)
        self.set_mrl(adapter,  'null://')
        controller = self.get_controller(adapter)
        try:
            controller.set_adapter_active('false')
        except:
            pass


    def select(self, adapter, channel):
        """
        Select a channel on the specified dvbstreamer instance.
        """
        _debug_('Selecting channel %s on adapter %s'%(channel, adapter))
        controller = self.get_controller(adapter)
        try:
            controller.set_adapter_active('true')
        except:
            pass
        controller.set_current_service(channel)


    def set_mrl(self, adapter, mrl):
        """
        Set the mrl for the primary service filter.
        """
        controller = self.get_controller(adapter)
        controller.set_servicefilter_mrl(comms.PRIMARY_SERVICE_FILTER, mrl)


    def execute(self, adapter, cmd):
        """
        Execute a command on the specified adapter.
        """
        controller = self.get_controller(adapter)
        controller.execute_command(cmd, True)


    def get_controller(self, adapter):
        """
        Get a Controller for the specified adapter, caching the controller if one doesn't already exist.
        """
        if adapter in self.controllers:
            return self.controllers[adapter]
        if adapter.find(':') != -1:
            ip_address,dvb_adapter = adapter.split(':',2)
            dvb_adapter = int(dvb_adapter)
        else:
            ip_address = 'localhost'
            dvb_adapter = int(adapter)
        controller = comms.Controller(ip_address, dvb_adapter, self.username, self.password)
        self.controllers[adapter] = controller
        return controller
