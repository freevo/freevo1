# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dvdcopy.py - Plugin for using dvdbackup to copy a DVD to HDD
# -----------------------------------------------------------------------
# $Id$
#
# Author: Adam Charrett
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
# with this program; if not, write to the Free Software Foundation
#
# -----------------------------------------------------------------------

#Import statements
from os.path import join, split
import plugin, config, menu
from gui.AlertBox import AlertBox
from gui.PopupBox import PopupBox
from plugins.idlebar import IdleBarPlugin
from childapp import ChildApp

import threading
import time
import os.path


drive_jobs = {}
for media in config.REMOVABLE_MEDIA:
    drive_jobs[media] = None

class PluginInterface(plugin.ItemPlugin):
    """
    Allows copying a DVD to HDD using dvdbackup.

    This plugin allows you to 'enter' a DVD and choose from copying the whole
    DVD, just the feature or a title.

    While the DVD is being copied an icon is placed in the idlebar and removed
    when the copy process finishes.

    If you decided you want to stop the copying process for any reason,
    simply  enter the DVD again and select the cancel DVD copy.

    To activate use:
    | plugin.activate('video.dvdcopy')
    """
    def __init__(self):
        if not config.DVDCOPY_DIR:
            self.reason = 'DVDCOPY_DIR not set'
            return
        if not config.CONF.dvdbackup:
            self.reason = 'dvdbackup not detected'
            return
        plugin.ItemPlugin.__init__(self)

        #Activate IdleBar monitor plugin.
        if config.DVDCOPY_IDLEBAR:
            idlebar_plugin = DVDCopyIdleBar()
            plugin.activate(idlebar_plugin, level=40)



    def config(self):
        return [ ('DVDCOPY_IDLEBAR', True, 'Use the idlebar to display status'),
                 ('DVDCOPY_DIR', None, 'Directory to copy DVDs to.')]

    def actions(self, item):
        if item.type == 'video' and item.mode == 'dvd' and \
             hasattr(item, 'media') and hasattr(item.media, 'devicename'):
            self.dvdsource = item.media.devicename
            if self.dvdsource in drive_jobs and drive_jobs[self.dvdsource]:
                return [ (self.cancel_copy, _('Cancel DVD copy'))]
            else:
                if hasattr(item, 'info_type') and item.info_type == "track":
                    self.title = item.url[6:]

                    self.item = item
                    return [ (self.copy_title, _('Copy this title to HDD')) ]
                else:
                    self.item = item
                    return [ (self.copy_dvd, _('Copy the entire disc to HDD')),
                             (self.copy_feature, _('Copy the feature to HDD'))]
        return []

    def copy_title(self, menuw=None, arg=None):
        self.menuw = menuw
        self.add_job(JOB_TYPE_TITLE, self.dvdsource, self.title)

    def copy_dvd(self, menuw=None, arg=None):
        self.menuw = menuw
        self.add_job(JOB_TYPE_ENTIRE_DISC, self.dvdsource)

    def copy_feature(self, menuw=None, arg=None):
        self.menuw = menuw
        self.add_job(JOB_TYPE_FEATURE, self.dvdsource)

    def cancel_copy(self, menuw=None, arg=None):
        global drive_jobs
        job = drive_jobs[self.dvdsource]
        if job:
            job.cancel()
        self.menuw.back_one_menu()

    def add_job(self, type, source, title=None):
        global drive_jobs
        drive_jobs[source] = DVDCopyJob(type, source, title)

        AlertBox(width=400, height=200, text=_("Copy started"), handler=self.mopup).show()

    def mopup(self):
        self.menuw.back_one_menu()


JOB_TYPE_ENTIRE_DISC='Disc'
JOB_TYPE_FEATURE='Feature'
JOB_TYPE_TITLE='Title'

class DVDCopyJob:
    def __init__(self, type, source, title=None):
        self.source = source
        self.type = type
        self.title = title
        self.thread = threading.Thread(target=self.__copy)
        self.thread.start()

    def __copy(self):
        global drive_jobs
        args = [config.CONF.dvdbackup, '-i', self.source, '-o', config.DVDCOPY_DIR]

        if self.type == JOB_TYPE_FEATURE:
            args.append('-F')
        elif self.type == JOB_TYPE_TITLE:
            args.append('-t')
            args.append(self.title)
        else:
            args.append('-M')
        # Do the copy
        self.childapp = ChildApp(args)

        while self.childapp.isAlive():
            time.sleep(0.2)

        drive_jobs[self.source] = None

    def cancel(self):
        self.childapp.kill()



class DVDCopyIdleBar(IdleBarPlugin):
    def __init__(self):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.DVDCopy'
        self.icon = os.path.join(config.ICON_DIR, 'status/copy_to_hdd.png')

    def draw(self, (type, object), x, osd):
        global drive_jobs
        draw_icon = False
        for job in drive_jobs.values():
            if job:
                draw_icon = True
                break

        if draw_icon:
            width = osd.draw_image(self.icon, (x, osd.y + 10, -1, -1))[0]
        else:
            width = 0

        return width
