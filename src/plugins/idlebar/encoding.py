# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# encoding.py - IdleBarplugin for showing encoding status
# -----------------------------------------------------------------------
# $Id: encoding.py 8377 2006-10-15 09:44:34Z duncan $
#
# Author: Duncan Webb <duncan@freevo.org>
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


# python modules
import os, sys, pygame, xmlrpclib

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config
from util.marmalade import jellyToXML, unjellyFromXML

def returnFromJelly(status, response):
    """Un-serialize EncodingServer responses"""
    if status:
        return (status, unjellyFromXML(response))
    else:
        return (status, response)


class PluginInterface(plugin.DaemonPlugin):
    """
    This plugin shows the current encoding level on the idlebar.
    Activate with:
    plugin.activate('idlebar.encoding.Volume', level=0)
    """
    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'video.encodingstatus'
        server_string = 'http://%s:%s/' % \
                        (config.ENCODINGSERVER_IP, config.ENCODINGSERVER_PORT)
        self.server = xmlrpclib.Server(server_string, allow_none=1)

        #self.barimg   = os.path.join(config.ICON_DIR, 'status/encoding_bar.png')
        #self.outimg   = os.path.join(config.ICON_DIR, 'status/encoding_out.png')
        #self.muteimg  = os.path.join(config.ICON_DIR, 'status/encoding_mute.png')
        self.cacheimg = {}
        self.muted    = False
        self.encoding = -1
        self.progress = 0
        self.jobname = 'test'


    def getprogress(self):
        """Get the progress & pass information of the job currently encoding.
        
        This call returns False if no job is currently encoding (fx the queue is not active).
        When the queue is active, this call returns a tuple of 4 values:
            (friendlyname, status, perc, timerem)
        
        friendlyname is the friendlyname you assigned to the encoding job
        status is the current status of the encoding job, represented by an integer
            0 - Not set (this job hasn't started encoding). Never used in this context
            1 - Audio pass in progress
            2 - First (analyzing) video pass (only used in multipass encoding)
            3 - Final video pass
            4 - Postmerge (not used atm). Final merging or similar processing in progress
        perc is the percentage completed of the current pass
        timerem is the estimated time remaining of the current pass, formatted as a
            human-readable string.        
        """
        
        try:
            (status, response) = self.server.getProgress()
        except:
            return (False, 'EncodingClient: connection error')
        
        return returnFromJelly(status, response)
        
    def listjobs(self):
        """Get a list with all jobs in the encoding queue and their current state
        
        Returns a list of tuples containing all the current queued jobs. When the queue is
        empty, an empty list is returned. 
        Each job in the list is a tuple containing 3 values
            (idnr, friendlyname, status)
        These values have the same meaning as the corresponding values returned by the
            getProgress call"""
        
        try:
            (status, response) = self.server.listJobs()
        except:
            return (False, 'EncodingClient: connection error')
        
        return returnFromJelly(status, response)
        

    def getimage(self, image, osd, cache=False):
        if image.find(config.ICON_DIR) == 0 and image.find(osd.settings.icon_dir) == -1:
            new_image = os.path.join(osd.settings.icon_dir, image[len(config.ICON_DIR)+1:])
            if os.path.isfile(new_image):
                image = new_image
        if cache:
            if image not in self.cacheimg.keys():
                self.cacheimg[image] = pygame.image.load(image)
            return self.cacheimg[image]

        return pygame.image.load(image)


    def calculatesizes(self,osd,font):
        """
        sizecalcs is not necessery on every pass
        """
        if not hasattr(self, 'idlebar'):
            self.idlebar = plugin.getbyname('idlebar')
            if self.idlebar:
                self.idlebar_max = osd.width + osd.x
                for p in plugin.get('idlebar'):
                    if hasattr(p, 'clock_left_position'):
                        self.idlebar_max = p.clock_left_position

                if self.idlebar_max - self.idlebar.free_space < 250:
                    _debug_('free space in idlebar to small, using normal detach')
                    self.idlebar = None

        pad_internal = 5 # internal padding for box vs text


    def draw(self, (type, object), osd):
        font = osd.get_font('detachbar')
        if font == osd.get_font('default'):
            font = osd.get_font('info value')

        self.calculatesizes(osd,font)

        if not self.idlebar:
            osd.drawroundbox(100, 100, 300, 300, (0xf0000000L, 1, 0xb0000000L, 10))
        (status, jobs) = self.listjobs()
        if not status:
            osd.write_text('encoding server not running', font, None, 110, 110, 190, 20, 'center', 'center')
            return 0;
        if not jobs:
            osd.write_text('encoding server has no jobs', font, None, 110, 110, 190, 20, 'center', 'center')
            return 0;
        (status, progress) = self.getprogress();
        print jobs, progress

        if progress[1] == 0:
            state = 'Not started'
        elif progress[1] == 1:
            state = 'Audio'
        elif progress[1] == 2:
            state = 'Video-1'
        elif progress[1] == 3:
            state = 'Video-1'
        elif progress[1] == 4:
            state = 'Multiplexing'
        message = "%s %s%% %s" % (state, progress[2], progress[3])
#def drawstring(self, text, font, content, x=-1, y=-1, width=None, height=None,
#                   align_h = None, align_v = None, mode='hard', ellipses='...', dim=True)
        (idnr, jobname, jobstate) = jobs[0]
        joblist = jobname
        for job in jobs[1:]:
            (idnr, jobname, jobstate) = job
            joblist += ', ' + jobname
        osd.write_text(joblist, font, None, 40, 100, 300, 20, 'left', 'center', dim=False)
        osd.write_text(progress[0], font, None, 40, 120, 300, 20, 'center', 'center', dim=False)
        osd.write_text(message, font, None, 40, 140, 300, 20, 'center', 'center')

        return 0

    def update(self):
        bar = plugin.getbyname('idlebar')
        if bar: bar.poll()
