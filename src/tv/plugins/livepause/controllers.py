# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# controllers.py - the Freevo Live Pause module for tv
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
"""
This module contains the classes used to control different types of videogroup.
A Controller must be able to tune and start the  process of filling the pause buffer
and when no longer required stop the refilling of the buffer.

DVBStreamerController - Controls local or remote DVBStreamer instances.
"""
import socket
import os
import traceback

import config
import tv.ivtv
import tv.v4l2 as V4L2

from tv.plugins.dvbstreamer.manager import DVBStreamerManager

__all__ = ['get_controller', 'Controller', 'DVBStreamerController', 'HDHomeRunController', 'IVTVController']

# Hashtable of video group types to controller object
cached_controllers = {}

def get_controller(vg_type):
    """
    Returns a Controller object based on the video group type.
    """
    result = None
    vg_type = vg_type.lower()
    # If we have already cached the controller return it.
    if vg_type in cached_controllers:
        return cached_controllers[vg_type]

    if vg_type == 'dvb':
        result = DVBStreamerController()

    elif vg_type == 'hdhomerun':
        result = HDHomeRunController()

    elif vg_type == 'ivtv':
        result = IVTVController()

    # Cache controller for next time.
    cached_controllers[vg_type] = result
    return result

class Controller(object):
    """
    Base class that all controller classes should derive from.
    """

    def __init__(self):
        pass

    def start_filling(self, buffer, videogroup, channel, timeout):
        """
        Start filling the supplied buffer using the device supplied (VideoGroup)
        after tuning to the channel specified.
        If no data is received after timeout seconds send a Data Timed out event.
        """
        pass

    def stop_filling(self):
        """
        Stop filling the buffer supplied in the previous start_filling call.
        """
        pass



class DVBStreamerController(Controller):
    """
    Class to control a DVBStreamer server.
    """

    def __init__(self):
        Controller.__init__(self)

        # Create DVBStreamer objects
        username = 'dvbstreamer'
        password = 'control'

        try:
            username = config.DVBSTREAMER_USERNAME
            password = config.DVBSTREAMER_PASSWORD
        except:
            pass

        self.manager = DVBStreamerManager(username, password)
        self.last_device = None

    def start_filling(self, buffer, videogroup, channel, timeout):
        """
        Start filling the supplied buffer using the device supplied (VideoGroup)
        after tuning to the channel specified.
        If no data is received after timeout seconds send a Data Timed out event.
        """
        device = videogroup.vdev
        try:
            self.manager.select(device,  channel)
        except:
            traceback.print_exc()

        port = 1235
        if device.find(':') != -1:
            ip_address = self.manager.controllers[device].my_ip
        else:
            ip_address = 'localhost'

        try:
            controller = self.manager.get_controller(device)
            controller.execute_command('setprop adapter.active true', True)
        except:
            _debug_('Not DVBStreamer 2.x?')

        try:
            self.manager.enable_udp_output(device,  ip_address, port)
        except:
            traceback.print_exc()

        self.last_device = device

        buffer.fill('udp', '%s:%d' % (ip_address, port))

    def stop_filling(self):
        """
        Stop filling the buffer supplied in the previous start_filling call.
        """
        try:
            self.manager.disable_output(self.last_device)
        except:
            traceback.print_exc()
        try:
            controller = self.manager.get_controller(self.last_device)
            controller.execute_command('setprop adapter.active false', True)
        except:
            _debug_('Not DVBStreamer 2.x?')



class HDHomeRunController(Controller):
    """
    Class to control an HDHomeRun box.
    """

    def __init__(self):
        Controller.__init__(self)
        self.last_device = None

    def start_filling(self, buffer, videogroup, channel, timeout):
        """
        Start filling the supplied buffer using the device supplied (VideoGroup)
        after tuning to the channel specified.
        If no data is received after timeout seconds send a Data Timed out event.
        """
        device = videogroup.vdev

        id,  tuner = device.split(':', 2)
        freq, channel = channel.split('.', 2)

        port = 1235
        ip_address = socket.gethostbyname(socket.gethostname())

        os.system('hdhomerun_config %s set /tuner%s/channel %s' % (id, tuner, freq))
        os.system('hdhomerun_config %s set /tuner%s/program %s' % (id, tuner, channel))
        os.system('hdhomerun_config %s set /tuner%s/target %s:%d' % (id, tuner, ip_address, port))

        self.last_device = (id, tuner)
        buffer.fill('udp', '%s:%d' % (ip_address, port))



    def stop_filling(self):
        """
        Stop filling the buffer supplied in the previous start_filling call.
        """
        os.system('hdhomerun_config %s set /tuner%s/target none' % self.last_device)


class IVTVController(Controller):
    """
    Class to control an IVTV based card.
    """
    def __init__(self):
        COntroller.__init__(self)
        self.settings = None

    def start_filling(self, buffer, videogroup, channel, timeout):
        """
        Start filling the supplied buffer using the device supplied (VideoGroup)
        after tuning to the channel specified.
        If no data is received after timeout seconds send a Data Timed out event.
        """
        _debug_('Opening device %r' % (videogroup.vdev))
        v = tv.ivtv.IVTV(videogroup.vdev)

        v.init_settings()

        _debug_('Setting input to %r' % (videogroup.input_type))
        v.setinputbyname(videogroup.input_type)

        cur_std = v.getstd()
        try:
            new_std = V4L2.NORMS.get(videogroup.tuner_norm)
            if cur_std != new_std:
                _debug_('Setting standard to %s' % (new_std))
                v.setstd(new_std)
        except:
            _debug_("Videogroup norm value '%s' not from NORMS: %s" % \
                (videogroup.tuner_norm, V4L2.NORMS.keys()), DERROR)

        if videogroup.cmd != None:
            _debug_("Running command %r" % videogroup.cmd)
            retcode = os.system(videogroup.cmd)
            _debug_("exit code: %g" % retcode)
        self.settings = v
        buffer.fill('psfile', videogroup.vdev)

    def stop_filling(self):
        """
        Stop filling the buffer supplied in the previous start_filling call.
        """
        if self.settings:
            self.settings.close()
            self.settings = None
