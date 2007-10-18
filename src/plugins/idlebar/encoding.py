# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# encoding.py - IdleBarplugin for showing encoding status
# -----------------------------------------------------------------------
# $Id$
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
import skin
from plugins.idlebar import IdleBarPlugin
import plugin, config
from util.marmalade import jellyToXML, unjellyFromXML
from gui import Progressbar
import rc


def returnFromJelly(status, response):
    """Un-serialize EncodingServer responses"""
    _debug_('returnFromJelly(status, response)', 2)
    if status:
        return (status, unjellyFromXML(response))
    else:
        return (status, response)


class PluginInterface(plugin.DaemonPlugin):
    """
    This plugin shows the current encoding status
    Activate with:
    | plugin.activate('idlebar.encoding')
    """

    def __init__(self):
        _debug_('__init__(self)', 2)
        plugin.DaemonPlugin.__init__(self)
        #IdleBarPlugin.__init__(self)
        self.poll_interval = 82 # 82*1/120th seconds (~1sec)
        self.draw_interval = self.poll_interval
        self.last_interval = self.poll_interval
        self.lastdraw  = 0
        self.lastpoll  = 0
        self.plugin_name = 'video.encodingstatus'
        server_string  = 'http://%s:%s/' % \
                        (config.ENCODINGSERVER_IP, config.ENCODINGSERVER_PORT)
        self.server    = xmlrpclib.Server(server_string, allow_none=1)

        self.skin      = skin.get_singleton()
        self.barimg    = os.path.join(config.ICON_DIR, 'status/encoding_bar.png')
        self.boximg    = os.path.join(config.ICON_DIR, 'status/encoding_box.png')
        self.boxborder = 3
        self.padding   = 5 # internal padding for box vs text
        self.image     = None
        self.cacheimg  = {}
        self.muted     = False
        self.encoding  = -1
        self.progress  = 0
        self.jobname   = ''
        self.calculate = True
        self.jobs      = ''
        self.mode      = 'Not Running'
        self.text      = []
        self.percent   = 0.0
        self.running   = False
        self.drawtime  = 0
        self.polltime  = 0
        self.state     = 'noserver'
        self.laststate = None
        self.font      = self.skin.get_font('detachbar')
        if self.font == skin.get_font('default'):
            self.font = skin.get_font('info value')


    def config(self):
        return [ ('ENCODING_IDLEBAR', True, 'Use the idlebar'), ]


    def getprogress(self):
        _debug_('getprogress(self)', 2)
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
        _debug_('listjobs(self)', 2)
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
        _debug_('getimage(self, image, osd, cache=False)', 2)
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
        _debug_('settext(self)', 2)
        """
        set the text
        """
        (status, jobs) = self.listjobs()
        if not status:
            self.state = 'noserver'
            self.jobs = _('encoding server not running')
            self.draw_interval = 5000
            self.running = False
            return 0;
        if not jobs:
            self.state = 'nojobs'
            self.jobs = _('encoding server has no jobs')
            self.draw_interval = 5000
            self.running = False
            return 0;
        self.state = 'active'
        (idnr, jobname, jobstate) = jobs[0]
        joblist = jobname
        for job in jobs[1:]:
            (idnr, jobname, jobstate) = job
            joblist += ', ' + jobname
        self.jobs = joblist
        self.running = True

        self.text = []
        (status, progress) = self.getprogress();
        if status:
            if progress[1] == 0:
                self.mode = 'Not started'
                self.state = 'active'
                self.draw_interval = 5000
            elif progress[1] == 1:
                self.mode = 'Audio'
                self.state = 'audio'
                self.draw_interval = 200
            elif progress[1] == 2:
                self.mode = 'Video-1'
                self.state = 'video'
                self.draw_interval = 1000
            elif progress[1] == 3:
                self.mode = 'Video-2'
                self.state = 'video'
                self.draw_interval = 1000
            elif progress[1] == 4:
                self.mode = 'Multiplexing'
                self.state = 'multiplexing'
                self.draw_interval = 1000
            self.text.append("%s %s%% %s" % (self.mode, progress[2], progress[3]))
            self.percent = progress[2] / 100.0


    def calculatesizes(self, osd, font):
        _debug_('calculatesizes(self, osd, font)', 2)
        """
        sizecalcs is not necessery on every pass
        """
        if config.ENCODING_IDLEBAR:
            if not hasattr(self, 'idlebar'):
                self.idlebar = plugin.getbyname('idlebar')
                if self.idlebar:
                    self.idlebar_max = osd.width + osd.x
                    _debug_('idlebar_max=%s, free_space=%s' % (self.idlebar_max, self.idlebar.free_space), 2)
                    for p in plugin.get('idlebar'):
                        if hasattr(p, 'clock_left_position'):
                            self.idlebar_max = p.clock_left_position

                    if self.idlebar_max - self.idlebar.free_space < 250:
                        _debug_('free space in idlebar to small, using normal detach')
                        self.idlebar = None
                    else:
                        # this doesn't work, but needs to for the detachbar
                        self.idlebar.take_space(250)
        else:
            self.idlebar = None

        if self.idlebar:
            self.boxborder = 0
            self.padding = 0

        if self.calculate:
            self.calculate = False
            self.font_h = font.font.height

            _debug_('osd.width=%s, osd.height=%s, osd.x=%s, osd.y=%s' % (osd.width, osd.height, osd.x, osd.y), 2)
            screen_width = osd.width + 2*osd.x
            screen_height = osd.height + 2*osd.y

            used_width = font.font.stringsize(self.jobs) - 1
            # ensure that the box width is between min and max
            used_width = max(used_width, 200)
            used_width = min(used_width, 280)
            used_height = self.font_h
            if self.running:
                w, h = self.getimage(self.boximg, osd).get_size()
                used_width = max(used_width, w)
                used_height += h
                for text in self.text:
                    used_width = max(used_width, font.font.stringsize(text)) - 1
                    used_height += self.font_h

            _debug_('screen_width=%s, screen_height=%s, used_width=%s, used_height=%s, font_h=%s' % \
                (screen_width, screen_height, used_width, used_height, self.font_h), 2)
            self.boxw = used_width + (self.padding + self.boxborder) * 2
            self.boxh = used_height + (self.padding + self.boxborder) * 2
            self.bx = osd.x
            self.by = screen_height - osd.y - self.boxh
            self.textw = used_width
            self.texth = used_height
            self.tx = self.bx + self.boxborder + self.padding
            self.ty = self.by + self.boxborder + self.padding

        if self.idlebar:
            if self.image:
                self.bx = self.idlebar.free_space + 250 + 70
            else:
                self.bx = self.idlebar.free_space + 250
            self.by = osd.y
            self.tx = self.bx + self.boxborder + self.padding
            self.ty = self.by + self.boxborder + self.padding
            self.textw = min(self.textw, self.idlebar_max - self.bx - 30)


    def draw(self, (type, object), osd):
        _debug_('draw(self, (type, object), osd)', 2)
        now = time.time()
        duration = now - self.drawtime
        _debug_("draw=%.2f, interval=%s, state=%s" % (duration, self.draw_interval, self.state), 2)
        self.drawtime = now
        self.lastdraw = now

        self.calculate = True
        self.settext()
        self.calculatesizes(osd, self.font)

        _debug_('self:bx=%s, by=%s, boxh=%s, boxw=%s, border=%s, padding=%s' % \
            (self.bx, self.by, self.boxh, self.boxw, self.boxborder, self.padding), 2)
        if self.idlebar:
            osd.drawroundbox(self.bx, self.by, self.boxw, self.boxh,
                (0xffffffffL, self.boxborder, 0x40ffff00L, 0))
                #  A R G B                      A R G B
                #  background border_width      border     border_radius
        else:
            osd.drawroundbox(self.bx, self.by, self.boxw, self.boxh,
                (0xf0ffffffL, self.boxborder, 0xb0000000L, self.boxborder))

        _debug_('self:tx=%s, ty=%s, texth=%s, textw=%s' % (self.tx, self.ty, self.texth, self.textw), 2)
        y = self.ty
        osd.write_text(self.jobs, self.font, None, self.tx, y, self.textw, self.font_h, 'center', 'center')
        if self.running:
            y += self.font_h
            encbar = self.getimage(self.barimg, osd, True)
            encbox = self.getimage(self.boximg, osd)
            w, h = encbox.get_size()
            encbox.blit(encbar, (3, 3), (0, 0, (w * self.percent), h))
            x = (self.textw - w) / 2
            #osd.drawroundbox(self.tx+x-2, y-2, w+4, h+4,
            #    (0xf0ffffffL, 2, 0xb000ffffL, 0))
            osd.drawimage(encbox, (self.tx+x, y, -1, -1) )[0]
            y += h
            for text in self.text:
                osd.write_text(text, self.font, None, self.tx, y, self.textw, self.font_h, 'center', 'center')
                y += self.font_h

        return self.textw


    def poll(self):
        '''poll function'''
        now = time.time()
        pollduration = now - self.lastpoll
        drawduration = now - self.lastdraw
        self.lastpoll = now
        _debug_("poll(self): poll=%.2f, draw=%.2f, interval=%s, state=%s" % \
            (pollduration, drawduration, self.draw_interval, self.state), 2)
        if drawduration >= self.draw_interval / 100:
            if skin.active():
                skin.redraw()

        # this is how to change the poll interval on the fly
        #if self.last_interval <> self.poll_interval:
        #    self.last_interval = self.poll_interval
        #    rc.unregister(self.poll)
        #    rc.register(self.poll, True, self.poll_interval)
        #    #print self.__dict__


    def update(self):
        _debug_('update(self)', 2)
        bar = plugin.getbyname('idlebar')
        if bar: bar.poll()
