# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# transcode.py - Idlebar plugin for showing encoding status
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
import time, re

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


class PluginInterface(IdleBarPlugin):
    """
    Shows the status of the current encoding job

    Activate with:
    | plugin.activate('idlebar.transcode')
    """

    def __init__(self):
        """ Initialise the transcode idlebar plug-in """
        _debug_('transcode.PluginInterface.__init__()', 2)
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.transcode'

        self.background = os.path.join(config.ICON_DIR, 'status/enc_background.png')
        self.leftclamp  = os.path.join(config.ICON_DIR, 'status/enc_leftclamp.png')
        self.rightclamp = os.path.join(config.ICON_DIR, 'status/enc_rightclamp.png')
        self.notrunning = os.path.join(config.ICON_DIR, 'status/enc_notrunning.png')
        self.nojobs     = os.path.join(config.ICON_DIR, 'status/enc_nojobs.png')
        self.audio      = os.path.join(config.ICON_DIR, 'status/enc_audio.png')
        self.video      = os.path.join(config.ICON_DIR, 'status/enc_video.png')
        self.video1     = os.path.join(config.ICON_DIR, 'status/enc_video1.png')
        self.video2     = os.path.join(config.ICON_DIR, 'status/enc_video2.png')
        self.video3     = os.path.join(config.ICON_DIR, 'status/enc_video3.png')
        self.multiplex  = os.path.join(config.ICON_DIR, 'status/enc_multiplex.png')

        self.cacheimg = {}
        self.background_w, self.background_h = (0, 0)
        self.leftclamp_w, self.leftclamp_h = (0, 0)
        self.rightclamp_w, self.rightclamp_h = (0, 0)
        self.remaining_min = re.compile('[0-9]*')
        self.remaining = ''
        self.progress  = 0
        self.progress_x = None
        self.leftclamp_x = 0
        self.rightclamp_x = 0

        self.poll_interval = 82 # 82*1/120th seconds (~1sec)
        self.draw_interval = self.poll_interval
        self.last_interval = self.poll_interval
        self.lastdraw  = 0
        self.lastpoll  = 0
        self.drawtime  = 0
        server_string  = 'http://%s:%s/' % (config.ENCODINGSERVER_IP, config.ENCODINGSERVER_PORT)
        self.server    = xmlrpclib.Server(server_string, allow_none=1)

        self.skin      = skin.get_singleton()
        self.calculate = True
        self.jobs      = ''
        self.mode      = 'Not Running'
        self.state     = 'noserver'
        self.laststate = None
        self.percent   = 0.0
        self.running   = False
        self.font      = self.skin.get_font('small0')
        if self.font == skin.get_font('default'):
            self.font = skin.get_font('info value')
        _debug_('transcode.PluginInterface.__init__() done.')


    def config(self):
        _debug_('config()', 2)
        return [
            ('ENCODINGSERVER_IP', 'localhost', 'The host name or IP address of the encoding server'),
            ('ENCODINGSERVER_PORT', 6666, 'The port of the encoding server'),
        ]


    def getprogress(self):
        """
        Get the progress & pass information of the job currently encoding.

        This call returns False if no job is currently encoding (fx the queue is not active).
        When the queue is active, this call returns a tuple of 4 values:
            (friendlyname, status, perc, timerem)

        friendlyname is the friendlyname you assigned to the encoding job
        status is the current status of the encoding job, represented by an integer:
            - 0 Not set (this job hasn't started encoding). Never used in this context
            - 1 Audio pass in progress
            - 2 First (analyzing) video pass (only used in multipass encoding)
            - 3 Final video pass
            - 4 Postmerge (not used atm). Final merging or similar processing in progress
        perc is the percentage completed of the current pass
        timerem is the estimated time remaining of the current pass, formatted as a human-readable string.
        """
        _debug_('getprogress()', 2)

        try:
            (status, response) = self.server.getProgress()
        except:
            return (False, 'EncodingClient: connection error')

        return returnFromJelly(status, response)


    def listjobs(self):
        """
        Get a list with all jobs in the encoding queue and their current state

        Returns a list of tuples containing all the current queued jobs. When the queue
        is empty, an empty list is returned.  Each job in the list is a tuple
        containing 3 values (idnr, friendlyname, status) These values have the same
        meaning as the corresponding values returned by the getProgress call
        """
        _debug_('listjobs() server=%r' % self.server, 2)
        result = (FALSE, [])

        try:
            (status, response) = self.server.listJobs()
        except:
            return (False, 'EncodingClient: connection error')
        result = returnFromJelly(status, response)
        _debug_('listjobs() result=%r' % (result, ), 2)
        return result


    def getimage(self, image, osd, cache=False):
        """
        Load the image from the cache when available otherwise load the image and save
        in the cache.
        """
        _debug_('getimage(image=%r, osd=%r, cache=%s)' % (image, osd, cache), 2)
        if image.find(config.ICON_DIR) == 0 and image.find(osd.settings.icon_dir) == -1:
            new_image = os.path.join(osd.settings.icon_dir, image[len(config.ICON_DIR)+1:])
            if os.path.isfile(new_image):
                image = new_image
        if cache:
            if image not in self.cacheimg.keys():
                self.cacheimg[image] = pygame.image.load(image)
            return self.cacheimg[image]

        return pygame.image.load(image)


    def set_sprite(self):
        """ set the sprite image name and the drawing interval """
        _debug_('set_sprite()', 2)
        (status, jobs) = self.listjobs()
        if not status:
            self.sprite = self.notrunning
            self.state = 'noserver'
            self.jobs = _('encoding server not running')
            self.draw_interval = 5000
            self.running = False
            return (self.background_w, self.background_h);
        if not jobs:
            self.sprite = self.nojobs
            self.state = 'nojobs'
            self.jobs = _('encoding server has no jobs')
            self.draw_interval = 5000
            self.running = False
            return (self.background_w, self.background_h);
        self.state = 'active'
        (idnr, jobname, jobstate) = jobs[0]
        joblist = jobname
        for job in jobs[1:]:
            (idnr, jobname, jobstate) = job
            joblist += ', ' + jobname
        self.jobs = joblist
        self.running = True

        (status, progress) = self.getprogress();
        if status:
            if progress[1] == 0:
                self.sprite = self.nojobs
                self.mode = 'Not started'
                self.state = 'active'
                self.draw_interval = 5000
            elif progress[1] == 1:
                self.sprite = self.audio
                self.mode = 'Audio'
                self.state = 'audio'
                self.draw_interval = 200
            elif progress[1] == 2:
                self.sprite = self.video1
                self.mode = 'Video-1'
                self.state = 'video'
                self.draw_interval = 1000
            elif progress[1] == 3:
                self.sprite = self.video2
                self.mode = 'Video-2'
                self.state = 'video'
                self.draw_interval = 1000
            elif progress[1] == 4:
                self.sprite = self.multiplex
                self.mode = 'Multiplexing'
                self.state = 'multiplexing'
                self.draw_interval = 1000
            remaining = self.remaining_min.search(progress[3])
            self.remaining = remaining and remaining.group() or ''
            self.progress = progress[2]
            self.percent = progress[2] / 100.0
            return (self.background_w, self.background_h);


    def calculatesizes(self, osd, font):
        """size calcs is not necessery on every pass
        There are some shortcuts here, the left and right clamps are the same with
        all sprites are the same size and the background
        return true when the progress has changed, false otherwise
        """
        _debug_('calculatesizes(osd, font)', 2)
        if self.progress_x == None:
            background = self.getimage(self.background, osd)
            rightclamp = self.getimage(self.rightclamp, osd, True)
            leftclamp = self.getimage(self.leftclamp, osd, True)
            self.background_w, self.background_h = background.get_size()
            self.leftclamp_w, self.leftclamp_h = leftclamp.get_size()
            self.rightclamp_w, self.rightclamp_h = rightclamp.get_size()
            _debug_('background: w=%s, h=%s' % (self.background_w, self.background_h), 2)
            _debug_('leftclamp: w=%s, h=%s' % (self.leftclamp_w, self.leftclamp_h), 2)
            _debug_('rightclamp: w=%s, h=%s' % (self.rightclamp_w, self.rightclamp_h), 2)

        progress_x = ((self.background_w - (2 * self.leftclamp_w)) * self.progress) / 200
        _debug_('progress_x=%s, background_w=%s, leftclamp_w=%s, progress=%s' % \
            (progress_x, self.background_w, self.leftclamp_w, self.progress), 3)

        if self.progress_x != progress_x:
            self.progress_x = progress_x
            self.leftclamp_x = self.progress_x
            self.rightclamp_x = self.background_w - self.rightclamp_w - self.progress_x
            _debug_('progress_x=%s, leftclamp_x=%s, rightclamp_x=%s' % \
                (self.progress_x, self.leftclamp_x, self.rightclamp_x), 2)
            return True
        return False


    def draw(self, (type, object), x, osd):
        """ Build the image by blitting sub images on the background and draw the background """
        _debug_('draw((type=%r, object=), x=%r, osd=)' % (type, x), 3)
        now = time.time()
        duration = now - self.drawtime
        _debug_("draw=%.2f, interval=%s, state=%s" % (duration, self.draw_interval, self.state), 2)
        self.drawtime = now
        self.lastdraw = now

        (sprite_w, sprite_h) = self.set_sprite()
        self.calculatesizes(osd, self.font)

        background = self.getimage(self.background, osd)
        if self.sprite:
            sprite = self.getimage(self.sprite, osd)
            background.blit(sprite, (0, 0), (0, 0, self.background_w, self.background_h))
        leftclamp = self.getimage(self.leftclamp, osd, True)
        rightclamp = self.getimage(self.rightclamp, osd, True)
        background.blit(leftclamp, (self.leftclamp_x, 1), (0, 0, self.leftclamp_w, self.leftclamp_h))
        background.blit(rightclamp, (self.rightclamp_x, 1), (0, 0, self.rightclamp_w, self.rightclamp_h))
        osd.drawimage(background, (x, osd.y, -1, -1) )[0]
        if self.remaining:
            font = osd.get_font('small0')
            widthdf = font.stringsize(self.remaining)
            remaining_x = x + ((self.background_w - widthdf) / 2)
            remaining_y = osd.y + self.background_h - font.h + 10
            _debug_('remaining=%r x=%s y=%s widthdf=%s font.h=%s' % \
                (self.remaining, remaining_x, remaining_y, widthdf, font.h))
            osd.write_text(self.remaining, font, None, remaining_x, remaining_y, widthdf, font.h, 'center', 'top')

        return self.background_w


    def poll(self):
        """poll function"""
        now = time.time()
        pollduration = now - self.lastpoll
        drawduration = now - self.lastdraw
        self.lastpoll = now
        _debug_("poll(): poll=%.2f, draw=%.2f, interval=%s, state=%s" % \
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
        _debug_('update()', 2)
        bar = plugin.getbyname('idlebar')
        if bar: bar.poll()
