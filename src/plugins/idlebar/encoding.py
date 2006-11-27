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
import time

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config
from util.marmalade import jellyToXML, unjellyFromXML
from gui import Progressbar

DEBUG=config.DEBUG

def returnFromJelly(status, response):
    """Un-serialize EncodingServer responses"""
    if status:
        return (status, unjellyFromXML(response))
    else:
        return (status, response)


class PluginInterface(plugin.DaemonPlugin):
    """
    This plugin shows the current encoding status
    Activate with:
    plugin.activate('idlebar.encoding', level=0)
    """
    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        self.poll_interval = 300 # 1/10th seconds (30secs)
        self.plugin_name = 'video.encodingstatus'
        server_string = 'http://%s:%s/' % \
                        (config.ENCODINGSERVER_IP, config.ENCODINGSERVER_PORT)
        self.server   = xmlrpclib.Server(server_string, allow_none=1)

        self.barimg   = os.path.join(config.ICON_DIR, 'status/encoding_bar.png')
        self.boximg   = os.path.join(config.ICON_DIR, 'status/encoding_box.png')
        self.image    = None
        self.cacheimg = {}
        self.muted    = False
        self.encoding = -1
        self.progress = 0
        self.jobname  = 'test'
        self.calculate = True
        self.jobs     = ''
        self.state    = 'Not Running'
        self.text     = []
        self.percent  = 0.0
        self.running  = False
        self.now      = None
        #self.bar     = Progressbar(self.tx, y, 100, 20, full=100)


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


    def settext(self):
        """
        set the text
        """
        (status, jobs) = self.listjobs()
        if not status:
            self.jobs = 'encoding server not running'
            self.poll_interval = 5000
            self.running = False
            return 0;
        if not jobs:
            self.jobs = 'encoding server has no jobs'
            self.poll_interval = 5000
            self.running = False
            return 0;
        (idnr, jobname, jobstate) = jobs[0]
        joblist = jobname
        for job in jobs[1:]:
            (idnr, jobname, jobstate) = job
            joblist += ', ' + jobname
        self.jobs = joblist
        self.running = True

        self.text = []
        (status, progress) = self.getprogress();
        if progress[1] == 0:
            self.state = 'Not started'
            self.poll_interval = 5000
        elif progress[1] == 1:
            self.state = 'Audio'
            self.poll_interval = 10
        elif progress[1] == 2:
            self.state = 'Video-1'
            self.poll_interval = 100
        elif progress[1] == 3:
            self.state = 'Video-2'
            self.poll_interval = 100
        elif progress[1] == 4:
            self.state = 'Multiplexing'
        self.text.append("%s %s%% %s" % (self.state, progress[2], progress[3]))
        self.percent = progress[2] / 100.0


    def calculatesizes(self,osd,font):
        """
        sizecalcs is not necessery on every pass
        """
        if not hasattr(self, 'idlebar'):
            self.idlebar = plugin.getbyname('idlebar')
            if self.idlebar:
                self.idlebar_max = osd.width + osd.x
                print 'idlebar_max:', self.idlebar_max, 'free_space:', self.idlebar.free_space
                for p in plugin.get('idlebar'):
                    if hasattr(p, 'clock_left_position'):
                        self.idlebar_max = p.clock_left_position

                if self.idlebar_max - self.idlebar.free_space < 250:
                    _debug_('free space in idlebar to small, using normal detach')
                    self.idlebar = None
        #DJW turned off idlebar for now
        self.idlebar = None

        if self.calculate:
            self.calculate = False
            self.font_h = font.font.height
            pad_internal = 5 # internal padding for box vs text

            if DEBUG >= 2:
                print 'osd.width:', osd.width, 'osd.height:', osd.height, 'osd.x:', osd.x, 'osd.y:', osd.y
            screen_width = osd.width + 2*osd.x
            screen_height = osd.height + 2*osd.y

            bar_width = font.font.stringsize(self.jobs)
            bar_height = self.font_h
            if self.running:
                w,h = self.getimage(self.boximg, osd).get_size()
                bar_width = max(bar_width, w)
                bar_height += h
                for text in self.text:
                    bar_width = max(bar_width, font.font.stringsize(text))
                    bar_height += self.font_h
            bar_width = max(bar_width, 200)
            bar_width = min(bar_width, 400)

            if DEBUG >= 2:
                print 'screen_width:', screen_width, 'screen_height:', screen_height, \
                    'bar_width:', bar_width, 'bar_height:', bar_height, 'font_h:', self.font_h
            self.boxh = bar_height + (pad_internal * 2)
            self.boxw = bar_width + (pad_internal * 2)
            self.by = screen_height - osd.y - self.boxh
            self.bx = osd.x
            self.ty = self.by + pad_internal
            self.tx = self.bx + pad_internal
            self.texth = bar_height
            self.textw = bar_width
            if DEBUG >= 2:
                print 'self.bx:', self.bx, 'self.by:', self.by, 'self.boxh:', self.boxh, 'self.boxw:', self.boxw 
                print 'self.tx:', self.tx, 'self.ty:', self.ty, 'self.texth:', self.texth, 'self.textw:', self.textw

        if self.idlebar:
            self.by = osd.y
            self.ty = self.by
            if self.image:
                self.bx = self.idlebar.free_space + 70
            else:
                self.bx = self.idlebar.free_space
            self.tx = self.bx
            self.textw = min(self.textw, self.idlebar_max - self.bx - 30)


    def draw(self, (type, object), osd):
        font = osd.get_font('detachbar')
        if font == osd.get_font('default'):
            font = osd.get_font('info value')

        self.calculate = True
        self.settext()
        self.calculatesizes(osd,font)

        osd.drawroundbox(self.bx, self.by, self.boxw, self.boxh,
            (0xf0ffffffL, 3, 0xb0000000L, 10))
        #if not self.idlebar:
        #    osd.drawroundbox(100, 100, 300, 300,
        #        color=0xf0ffffffL, border_size=5, border_color=0xb0000000L, radius=10)


        y = self.ty
        osd.write_text(self.jobs, font, None, self.tx, y, self.textw, self.font_h, 'center', 'center')
        if self.running:
            y += self.font_h
            encbar = self.getimage(self.barimg, osd, True)
            encbox = self.getimage(self.boximg, osd)
            w,h = encbox.get_size()
            encbox.blit(encbar, (3,3), (0, 0, (w * self.percent), h))
            x = (self.textw - w) / 2
            osd.drawroundbox(self.tx+x-2, y-2, w+4, h+4,
                (0xf0ffffffL, 2, 0xb000ffffL, 0))
            osd.drawimage(encbox, (self.tx+x, y, -1, -1) )[0]
            y += h
            #y += 20
            for text in self.text:
                osd.write_text(text, font, None, self.tx, y, self.textw, self.font_h, 'center', 'center')
                y += self.font_h

        return self.textw


    def poll(self):
        now = time.time()
        if self.now:
            if DEBUG >= 2:
                print "%.3f" % (now - self.now), self.poll_interval, self.state
        self.now = now
        #self.draw()


    def update(self):
        bar = plugin.getbyname('idlebar')
        if bar: bar.poll()
