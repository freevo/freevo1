# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# re-encode recorded TV programmes
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# ToDo:
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


from os.path import join, split
import plugin
import menu
import os
import config
from video.encodingclient import *
from gui.AlertBox import AlertBox
from gui.PopupBox import PopupBox


class PluginInterface(plugin.ItemPlugin):
    """
    Archive recorded TV programmes using EncodingServer

    This plugin needs a running encodingserver to work properly.
    You can start an encodingserver with 'freevo encodingserver start'.

    To activate, put the following line in local_conf.py:
    | plugin.activate('video.reencode')
    """

    def __init__(self):
        _debug_('reencode.PluginInterface.__init__(self)')
        plugin.ItemPlugin.__init__(self)
        self.title = ''
        self.source = ''
        self.output = ''
        self.resetprofile()

    def resetprofile(self):
        self.profile = {}
        self.profile['container'] = config.REENCODE_CONTAINER
        self.profile['resolution'] = config.REENCODE_RESOLUTION
        self.profile['videocodec'] = config.REENCODE_VIDEOCODEC
        self.profile['altprofile'] = config.REENCODE_ALTPROFILE
        self.profile['audiocodec'] = config.REENCODE_AUDIOCODEC
        self.profile['numpasses'] = config.REENCODE_NUMPASSES
        self.profile['numthreads'] = config.REENCODE_NUMTHREADS
        self.profile['videobitrate'] = config.REENCODE_VIDEOBITRATE
        self.profile['audiobitrate'] = config.REENCODE_AUDIOBITRATE
        self.profile['videofilter'] = config.REENCODE_VIDEOFILTER


    def config(self):
        '''config is called automatically, for default settings run:
        freevo plugins -i video.reencode
        '''
        _debug_('config(self)', 2)
        return [
            ('REENCODE_CONTAINER', 'avi', 'Container type'),
            ('REENCODE_RESOLUTION', 'Optimal', 'Resolution'),
            ('REENCODE_VIDEOCODEC', 'XviD', 'Video codec'),
            ('REENCODE_ALTPROFILE', None, 'Alternate Encoding Profile'),
            ('REENCODE_VIDEOBITRATE', '800', 'Video bit rate'),
            ('REENCODE_AUDIOCODEC', 'MPEG 1 Layer 3 (mp3)', 'Audio codec'),
            ('REENCODE_AUDIOBITRATE', '128', 'Audio bit rate'),
            ('REENCODE_NUMPASSES', '2', 'Number of passes'),
            ('REENCODE_VIDEOFILTER', 'None', 'Video Filter'),
            ('REENCODE_NUMTHREADS','1','Number of Encoding Threads'),
        ]


    #def eventhandler(self, event, menuw=None, arg=None):
    #    _debug_('eventhandler(self, event=%r, menuw=%r, arg=%r)' % (event, menuw, arg), 2)
    #    return self.item.eventhandler(event, menuw=menuw, arg=arg)


    def actions(self, item):
        _debug_('actions(self, item)', 2)

        if item.type == 'video' and item.mode == 'file':
            self.item = item
            self.title = item.name
            self.source = item.filename
            (filename, extn) = os.path.splitext(item.filename)
            self.output = filename
            _debug_('item.__dict__:' % item.__dict__, 3)
            return [ (self.encoding_profile_menu, _('Transcode this program...')) ]
        return []


    def getattr(self, attr):
        '''callback function from the skin fxd file to get the display format
        of an item, the attr represents the expression in the skin
        '''
        _debug_('getattr(self, attr=%r)' % (attr), 2)
        if attr == 'disp_title':
            return '%s' % (self.title)
        if attr == 'disp_filename':
            return '%s' % (os.path.split(self.source)[1])+'.'+self.profile['container']
        elif attr == 'disp_container':
            return '%s' % (self.profile['container'])
        elif attr == 'disp_resolution':
            return '%s' % (self.profile['resolution'])
        elif attr == 'disp_videocodec':
            return '%s' % (self.profile['videocodec'])
        elif attr == 'altprofile':
            return '%s' % (self.profile['altprofile'])
        elif attr == 'disp_videobitrate':
            return '%s' % (self.profile['videobitrate'])
        elif attr == 'disp_audiocodec':
            return '%s' % (self.profile['audiocodec'])
        elif attr == 'disp_audiobitrate':
            return '%s' % (self.profile['audiobitrate'])
        elif attr == 'disp_numpasses':
            return '%s' % (self.profile['numpasses'])
        elif attr == 'disp_numthreads':
            return '%s' % (self.profile['numthreads'])
        elif attr == 'disp_videofilter':
            return '%s' % (self.profile['videofilter'])
        return '"%s" not defined' % (attr)


    def encoding_profile_menu(self, menuw=None, arg=None):
        _debug_('encoding_profile_menu(self, menuw=%r, arg=%r)' % (menuw, arg), 2)
        menu_items = []
        menu_items += [ menu.MenuItem(_('Start Encoding'), self.create_job, self.profile) ]
        menu_items += [ menu.MenuItem(_('Select Encoding Profile'), action=self.select_profile) ]
        menu_items += [ menu.MenuItem(_('Modify Container'), action=self.mod_container) ]
        menu_items += [ menu.MenuItem(_('Modify Resolution'), action=self.mod_resolution) ]
        menu_items += [ menu.MenuItem(_('Modify Video Codec'), action=self.mod_videocodec) ]
        menu_items += [ menu.MenuItem(_('Modify Video Bitrate'), action=self.mod_videobitrate) ]
        menu_items += [ menu.MenuItem(_('Modify Audio Codec'), action=self.mod_audiocodec) ]
        menu_items += [ menu.MenuItem(_('Modify Audio Bitrate'), action=self.mod_audiobitrate) ]
        menu_items += [ menu.MenuItem(_('Modify Number of passes'), action=self.mod_numpasses) ]
        menu_items += [ menu.MenuItem(_('Modify Number of Encoder Threads'), action=self.mod_numthreads) ]
        menu_items += [ menu.MenuItem(_('Modify Video Filter (not implemented)'), action=self.mod_videofilter) ]
        encoding_menu = menu.Menu(_('Choose your encoding profile'), menu_items, item_types = 'video encoding menu')
        encoding_menu.infoitem = self
        menuw.pushmenu(encoding_menu)
        menuw.refresh()

    def select_profile(self, arg=None, menuw=None):
        _debug_('select_profile(self, arg=None, menuw=None)', 2)
        menu_items = []
        menu_items += [ menu.MenuItem(_('Xvid Low Quality'), action=self.select_encoding_profile, arg='xvid_low') ]
        menu_items += [ menu.MenuItem(_('Xvid High Quality'), action=self.select_encoding_profile, arg='xvid_high') ]
        menu_items += [ menu.MenuItem(_('iPod'), action=self.select_encoding_profile, arg='ipod') ]
        menu_items += [ menu.MenuItem(_('DVD'), action=self.select_encoding_profile, arg='MPEG 2 (lavc)') ]
        encoding_menu = menu.Menu(_('Select Profile'), menu_items, item_types = 'video encoding menu')
        encoding_menu.infoitem = self
        menuw.pushmenu(encoding_menu)
        menuw.refresh()

    def mod_container(self, arg=None, menuw=None):
        _debug_('mod_container(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for container in getContainerCAP()[1]:
            items.append(menu.MenuItem(container, action=self.alter_prop, arg=('container', container)))
        container_menu = menu.Menu(_('Modify Container'), items, item_types = 'video encoding menu')
        container_menu.infoitem = self
        menuw.pushmenu(container_menu)
        menuw.refresh()

    def mod_resolution(self, arg=None, menuw=None):
        _debug_('mod_resolution(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for resolution in ('Optimal', '1920:1080', '1280:720', '852:480', '720:576', '720:480', '320:240'):
            items.append(menu.MenuItem(resolution, action=self.alter_prop, arg=('resolution', resolution)))
        resolution_menu = menu.Menu(_('Modify Resolution'), items, item_types = 'video encoding menu')
        resolution_menu.infoitem = self
        menuw.pushmenu(resolution_menu)
        menuw.refresh()

    def mod_videocodec(self, arg=None, menuw=None):
        _debug_('mod_videocodec(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for videocodec in getVideoCodecCAP()[1]:
            items.append(menu.MenuItem(videocodec, action=self.alter_prop, arg=('videocodec', videocodec)))
        videocodec_menu = menu.Menu(_('Modify Video Codec'), items, item_types = 'video encoding menu')
        videocodec_menu.infoitem = self
        menuw.pushmenu(videocodec_menu)
        menuw.refresh()

    def mod_videobitrate(self, arg=None, menuw=None):
        _debug_('mod_videobitrate(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for videobitrate in range(400, 2001, 200):
            items.append(menu.MenuItem(videobitrate, action=self.alter_prop, arg=('videobitrate', videobitrate)))
        videobitrate_menu = menu.Menu(_('Modify Video Bitrate'), items, item_types = 'video encoding menu')
        videobitrate_menu.infoitem = self
        menuw.pushmenu(videobitrate_menu)
        menuw.refresh()

    def mod_audiocodec(self, arg=None, menuw=None):
        _debug_('mod_audiocodec(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for audiocodec in getAudioCodecCAP()[1]:
            items.append(menu.MenuItem(audiocodec, action=self.alter_prop, arg=('audiocodec', audiocodec)))
        audiocodec_menu = menu.Menu(_('Modify Video Codec'), items, item_types = 'video encoding menu')
        audiocodec_menu.infoitem = self
        menuw.pushmenu(audiocodec_menu)
        menuw.refresh()

    def mod_audiobitrate(self, arg=None, menuw=None):
        _debug_('mod_audiobitrate(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for audiobitrate in (64, 128, 192, 224):
            items.append(menu.MenuItem(audiobitrate, action=self.alter_prop, arg=('audiobitrate', audiobitrate)))
        audiobitrate_menu = menu.Menu(_('Modify Audio Bitrate'), items, item_types = 'video encoding menu')
        audiobitrate_menu.infoitem = self
        menuw.pushmenu(audiobitrate_menu)
        menuw.refresh()

    def mod_numpasses(self, arg=None, menuw=None):
        _debug_('mod_numpasses(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for numpasses in (1, 2):
            items.append(menu.MenuItem(numpasses, action=self.alter_prop, arg=('numpasses', numpasses)))
        numpasses_menu = menu.Menu(_('Modify Number of Passes'), items, item_types = 'video encoding menu')
        numpasses_menu.infoitem = self
        menuw.pushmenu(numpasses_menu)
        menuw.refresh()

    def mod_numthreads(self, arg=None, menuw=None):
        _debug_('mod_numthreads(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for numthreads in (1, 2, 3, 4, 5, 6, 7, 8):
            items.append(menu.MenuItem(numthreads, action=self.alter_prop, arg=('numthreads', numthreads)))
        numthreads_menu = menu.Menu(_('Modify Number of Encoding threads'), items, item_types = 'video encoding menu')
        numthreads_menu.infoitem = self
        menuw.pushmenu(numthreads_menu)
        menuw.refresh()

    def mod_videofilter(self, arg=None, menuw=None):
        _debug_('mod_videofilter(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        items = []
        for videofilter in getVideoFiltersCAP()[1]:
            items.append(menu.MenuItem(videofilter, action=self.alter_prop, arg=('videofilter', videofilter)))
        videofilter_menu = menu.Menu(_('Modify Video Filter'), items, item_types = 'video encoding menu')
        videofilter_menu.infoitem = self
        menuw.pushmenu(videofilter_menu)
        menuw.refresh()

    def select_encoding_profile(self, arg=None, menuw=None):
        _debug_('select_encoding_profile(self, arg=%r, menuw=%r)' % (arg, menuw), 2)

        if arg == 'xvid_low':
            self.profile['container'] = 'avi'
            self.profile['resolution'] = 'Optimal'
            self.profile['videocodec'] = 'XviD'
            self.profile['altprofile'] = None
            self.profile['videobitrate'] = 800
            self.profile['audiocodec'] = 'MPEG 1 Layer 3 (mp3)'
            self.profile['audiobitrate'] = 128
            self.profile['numpasses'] = 1
            self.profile['videofilter'] = 'None'
        elif arg == 'xvid_high':
            self.profile['container'] = 'avi'
            self.profile['resolution'] = 'Optimal'
            self.profile['videocodec'] = 'XviD'
            self.profile['altprofile'] = None
            self.profile['videobitrate'] = 1200
            self.profile['audiocodec'] = 'MPEG 1 Layer 3 (mp3)'
            self.profile['audiobitrate'] = 128
            self.profile['numpasses'] = 2
            self.profile['videofilter'] = 'None'
        elif arg == 'ipod':
            self.profile['container'] = 'mp4'
            self.profile['resolution'] = '320:240'
            self.profile['videocodec'] = 'MPEG 4 (lavc)'
            self.profile['altprofile'] = 'vcodec=mpeg4:mbd=2:cmp=2:subcmp=2:trell=yes:v4mv=yes:vglobal=1'
            self.profile['videobitrate'] = 1200
            self.profile['audiocodec'] = 'AAC (iPod)'
            self.profile['audiobitrate'] = 192
            self.profile['numpasses'] = 2
            self.profile['videofilter'] = 'ipod'
        elif arg == 'MPEG 2 (lavc)':
            self.profile['container'] = 'mpeg'
            self.profile['resolution'] = '720:480'
            self.profile['videocodec'] = 'MPEG 2 (lavc)'
            self.profile['altprofile'] = None
            self.profile['videobitrate'] = 5200
            self.profile['audiocodec'] = 'AC3'
            self.profile['audiobitrate'] = 224
            self.profile['numpasses'] = 1
            self.profile['videofilter'] = 'None'
        else:
            _debug_('Unknown Profile "%s"' % (arg), DERROR)
            self.error(_('Unknown Profile')+(' "%s"' % (arg)))
            return

        if menuw:
            menuw.back_one_menu(arg='reload')

    def alter_prop(self, arg=(None, None), menuw=None):
        _debug_('alter_prop(self, arg=%r, menuw=%r)' % (arg, menuw), 2)
        (prop, val) = arg

        if prop == 'container':
            self.profile['container'] = val
        elif prop == 'resolution':
            self.profile['resolution'] = val
        elif prop == 'videocodec':
            self.profile['videocodec'] = val
        elif prop == 'altprofile':
            self.profile['altprofile'] = val
        elif prop == 'videobitrate':
            self.profile['videobitrate'] = val
        elif prop == 'audiocodec':
            self.profile['audiocodec'] = val
        elif prop == 'audiobitrate':
            self.profile['audiobitrate'] = val
        elif prop == 'numpasses':
            self.profile['numpasses'] = val
        elif prop == 'numthreads':
            self.profile['numthreads'] = val
        elif prop == 'videofilter':
            self.profile['videofilter'] = val
        else:
            _debug_('Unknown property "%s"' % (prop), DERROR)
            self.error(_('Unknown Property')+(' "%s"' % (prop)))
            return

        if menuw:
            menuw.back_one_menu(arg='reload')


    def alter_name(self, name):
        '''alter_name is not used'''
        _debug_('alter_name(self, name=%r)' % (name), 2)
        self.menuw.refresh()


    def create_job(self, menuw=None, arg=None):
        _debug_('create_job(self, arg=%r, menuw=%r)' % (arg, menuw), 2)

        profile = arg

        #we are going to create a job and send it to the encoding server, this can take some time while analyzing

        box = PopupBox(text=_('Please wait, analyzing video...'))
        box.show()
        (status, resp) = initEncodeJob(self.source, self.output, self.title)
        _debug_('initEncodeJob:status:%s resp:%s' % (status, resp))
        box.destroy()
        if not status:
            self.error(resp)
            return

        idnr = resp

        (status, resp) = setContainer(idnr, profile['container'])
        _debug_('setContainer:status:%s resp:%s' % (status, resp))
        if not status:
            self.error(resp)
            return

        multipass = profile['numpasses'] > 1
        (status, resp) = setVideoCodec(idnr, profile['videocodec'], 0, multipass, profile['videobitrate'], profile['altprofile'])
        _debug_('setVideoCodec:status:%s resp:%s' % (status, resp))
        if not status:
            self.error(resp)
            return

        (status, resp) = setAudioCodec(idnr, profile['audiocodec'], profile['audiobitrate'])
        _debug_('setAudioCodec:status:%s resp:%s' % (status, resp))
        if not status:
            self.error(resp)
            return

        (status, resp) = setNumThreads(idnr, profile['numthreads'])
        _debug_('setNumThreads:status:%s resp:%s' % (status, resp))
        if not status:
            self.error(resp)
            return

        (status, resp) = setVideoRes(idnr, profile['resolution'])
        _debug_('setVideoRes:status:%s resp:%s' % (status, resp))
        if not status:
            self.error(resp)
            return

        #(status, resp) = setVideoFilters(idnr, vfilters)
        #_debug_('setVideoFilters:status:%s resp:%s' % (status, resp))

        #And finally, qeue and start the job
        (status, resp) = queueIt(idnr, True)
        _debug_('queueIt:status:%s resp:%s' % (status, resp))

        if not status:
            self.error(resp)
            return

        self.menuw = menuw
        AlertBox(width=400, height=200, text=_('Encoding started'), handler=self.mopup).show()

        self.resetprofile()
        _debug_('boe')
        #menuw.delete_menu()
        #menuw.delete_menu()


    def error(self, text=''):
        _debug_('error(self, text=%r)' % (text))
        AlertBox(width=400, height=200, text='ERROR: %s' % text).show()


    def mopup(self):
        _debug_('mopup(self)')
        self.menuw.delete_menu()
        self.menuw.back_one_menu()
