# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to encoding server
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.www.htdocs.encoding_web.")

import sys
import time
import os
import os.path
import signal

import config
import subprocess
import string
import math
from freevo.www.configlib import *

from video.encodingclient import EncodingClientActions

from www.web_types import HTMLResource, FreevoResource
from freevo.plugins.cd_burn import *
from urllib import urlopen
from getopt import getopt
from stat import *

def addPageRefresh(display_timer = True):
    """
    """
    display_style = 'display:none'
    if display_timer:
        display_style = 'display:""'
    logger.log( 9, 'addPageRefresh()')
    prhtml = '<script type="text/JavaScript" src="scripts/encoding_web.js">window.onload=beginrefresh</script>\n'
    prhtml += '<span class="refresh" style=%s id="refresh" >Refresh In : ??</span>\n' % display_style
    return prhtml


def GetFileList(browse_dir, display_hidden = False):
    """
    """
    logger.log( 9, 'GetFileList(browse_dir=%r, dispay_hidden=%r)', browse_dir, display_hidden)

    file_list_ctrl = ''
    if not browse_dir:
        browse_dir = None
    else:
        if not os.path.exists(browse_dir):
            browse_dir = None

    if not browse_dir:
        file_list_ctrl += '<ul>\n'
        for vitem in config.VIDEO_ITEMS:
            ctrl_onclick = "ChangeDirectory('%s')" % vitem[1]
            file_list_ctrl += '<li><a onclick="%s">%s</a></li>\n' % (ctrl_onclick, vitem[1])
        file_list_ctrl += '</ul>\n'
        return file_list_ctrl

    dir_list = os.listdir(browse_dir)
    dir_list.sort()

    file_list_ctrl = '%s : %s' % ('Browsing Directory', browse_dir)
    file_list_ctrl += '<div class="filelist">\n<ul>\n'

    parent_dir = os.path.split(browse_dir)[0]
    file_list_ctrl += '<li class="directory">\n'
    file_list_ctrl += '<a onclick=ChangeDirectory("%s")>..</a>\n' % (  parent_dir )
    file_list_ctrl += '</li>\n'

    for display_file in dir_list:
        show_file = True
        if display_file.startswith('.'):
            if not display_hidden:
                show_file = False

        full_file = os.path.join(browse_dir, display_file)
        if show_file:
            if  os.path.isdir(full_file):
                file_list_ctrl += '<li class="directory">\n'
                change_dir = "ChangeDirectory('%s')" % full_file
                file_list_ctrl += '<a onclick="%s">\n' % change_dir
                file_list_ctrl += display_file
                file_list_ctrl += '</a>\n'
                file_list_ctrl += '</li>\n'

    for display_file in dir_list:
        show_file = True
        full_file = os.path.join(browse_dir, display_file)

        js_encode = "EncodeFile('%s')" % (full_file)
        if display_file.startswith('.'):
            if not display_hidden:
                show_file = False

        if show_file:
            file_suffix =  os.path.splitext(display_file)[1].strip('.')

            if not os.path.isdir(full_file) and file_suffix in config.VIDEO_SUFFIX:
                file_list_ctrl += '<li class="file">\n'
                file_list_ctrl += '<a onclick="%s";>Encode Video</a>\n' % (js_encode)
                file_list_ctrl += '%s' %  display_file
                file_list_ctrl += '</li>\n'

    file_list_ctrl += '</div>\n</ul>\n'
    return file_list_ctrl



class CDBurn_WebResource(FreevoResource):

    def __init__(self):
        logger.debug('reencode.PluginInterface.__init__(self)')
        self.profile = {}
        self.profile['container'] = config.REENCODE_CONTAINER
        self.profile['resolution'] = config.REENCODE_RESOLUTION
        self.profile['videocodec'] = config.REENCODE_VIDEOCODEC
        self.profile['audiocodec'] = config.REENCODE_AUDIOCODEC
        self.profile['numpasses'] = config.REENCODE_NUMPASSES
        self.profile['videobitrate'] = config.REENCODE_VIDEOBITRATE
        self.profile['audiobitrate'] = config.REENCODE_AUDIOBITRATE
        self.profile['videofilter'] = config.REENCODE_VIDEOFILTER
        self.profile['numthreads'] = config.REENCODE_NUMTHREADS
        self.profile['altprofile'] = config.REENCODE_ALTPROFILE

        self.server = EncodingClientActions()
        self.ContainerCapList = self.server.getContainerCAP()[1]
        self.VideoCodecList   = self.server.getVideoCodecCAP()[1]
        self.AudioCodecList   = self.server.getAudioCodecCAP()[1]
        self.VideoFilters     = self.server.getVideoFiltersCAP()[1]
        self.ProfileList = ['xvid_low', 'xvid_high', 'iPod', 'Nokia770', 'DVD']

    def select_encoding_profile(self, arg=None, menuw=None):
        logger.log( 9, 'select_encoding_profile(self, arg=%r, menuw=%r)', arg, menuw)
        if arg == 'xvid_low':
            self.profile['container'] = 'avi'
            self.profile['resolution'] = 'Optimal'
            self.profile['videocodec'] = 'XviD'
            self.profile['videobitrate'] = 800
            self.profile['audiocodec'] = 'MPEG 1 Layer 3 (mp3)'
            self.profile['audiobitrate'] = 128
            self.profile['numpasses'] = 1
            self.profile['videofilter'] = 'None'
            self.profile['altprofile'] = None
        elif arg == 'xvid_high':
            self.profile['container'] = 'avi'
            self.profile['resolution'] = 'Optimal'
            self.profile['videocodec'] = 'XviD'
            self.profile['videobitrate'] = 1200
            self.profile['audiocodec'] = 'MPEG 1 Layer 3 (mp3)'
            self.profile['audiobitrate'] = 128
            self.profile['numpasses'] = 2
            self.profile['videofilter'] = 'None'
            self.profile['altprofile'] = None
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
        elif arg == 'Nokia770':
            self.profile['container'] = 'avi'
            self.profile['resolution'] = '240:144'
            self.profile['videocodec'] = 'MPEG 4 (lavc)'
            self.profile['videobitrate'] = 500
            self.profile['audiocodec'] = 'MPEG 1 Layer 3 (mp3)'
            self.profile['audiobitrate'] = 96
            self.profile['numpasses'] = 2
            self.profile['videofilter'] = 'None'
            self.profile['altprofile'] = None
        elif arg == 'DVD':
            self.profile['container'] = 'mpeg'
            self.profile['resolution'] = '720:480'
            self.profile['videocodec'] = 'MPEG 2 (lavc)'
            self.profile['videobitrate'] = 5000
            self.profile['audiocodec'] = 'AC3'
            self.profile['audiobitrate'] = 224
            self.profile['numpasses'] = 2
            self.profile['videofilter'] = 'None'
            self.profile['altprofile'] = None
        else:
            logger.error('Unknown Profile "%s"', arg)
            self.error(_('Unknown Profile')+(' "%s"' % (arg)))
        return

    def EncodingParameters(self):
        coding_parameters = '<div id="AdvancedOptions"><ul>'
        coding_parameters += '<li>Encoding Profile :'
        coding_parameters += CreateSelectBoxControl('profile', self.ProfileList, 'XviD')
        coding_parameters += '</li>'

        coding_parameters += '<li>'
        coding_parameters += '<a onclick=DisplayAdvancedOptions()>Advanced Encoding Parameters </a>'
        coding_parameters += '<ul id="AdvancedOptionsList" style=display:none>'

        container_box = CreateSelectBoxControl('container', self.ContainerCapList, self.profile['container'] )
        coding_parameters += '<li> Container : %s </li>' % container_box

        resolution_box =  CreateHTMLinput('textbox', 'resolution', self.profile['resolution'] )
        coding_parameters += '<li> Resolution : %s </li>' % resolution_box

        videocodec_box = CreateSelectBoxControl('videocodec', self.VideoCodecList, self.profile['videocodec'])
        coding_parameters += '<li> Video Codec : %s </li>' % videocodec_box

        audiocodec_box = CreateSelectBoxControl('audiocodec', self.AudioCodecList, self.profile['audiocodec'])
        coding_parameters += '<li> Audio Codec : %s </li>' % audiocodec_box

        numpasses_box = CreateHTMLinput('textbox', 'numpasses', self.profile['numpasses'])
        coding_parameters += '<li> Number of Passes : %s </li>' % numpasses_box

        videobitrate_box = CreateHTMLinput('textbox', 'videobitrate', self.profile['videobitrate'])
        coding_parameters += '<li> Video Bit Rate : %s </li>' % videobitrate_box

        audiobitrate_box = CreateHTMLinput('textbox', 'audiobitrate', self.profile['audiobitrate'])
        coding_parameters += '<li> Audio Bit Rate : %s </li>' % audiobitrate_box

        videofilter_box = CreateSelectBoxControl('videofilter', self.VideoFilters, self.profile['videofilter'])
        coding_parameters += '<li> Video Filter : %s </li>' % videofilter_box

        numthreads_box = CreateHTMLinput('textbox', 'numthreads', self.profile['numthreads'])
        coding_parameters += '<li> Number of Threads : %s </li>' % numthreads_box

        coding_parameters += '</ul></li></ul></div>'
        return coding_parameters


    def create_job(self, menuw=None, arg=None):
        logger.log( 9, 'create_job(self, arg=%r, menuw=%r)', arg, menuw)

        profile = arg
        job_status = 'Job Status'

        #we are going to create a job and send it to the encoding server, this can take some time while analyzing
        (status, resp) = self.server.initEncodingJob(self.source, self.output, self.title)
        logger.debug('initEncodingJob:status:%s resp:%s', status, resp)

        if not status:
            return 'initEncodingJob:status:%s resp:%s' % (status, resp)

        idnr = resp

        (status, resp) = self.server.setContainer(idnr, self.profile['container'])
        logger.debug('setContainer:status:%s resp:%s', status, resp)
        if not status:
            self.error(resp)
            return

        multipass = self.profile['numpasses'] > 1
        (status, resp) = self.server.setVideoCodec(idnr, self.profile['videocodec'], 0, multipass,
            self.profile['videobitrate'], self.profile['altprofile'])
        logger.debug('setVideoCodec:status:%s resp:%s', status, resp)
        if not status:
            self.error(resp)
            return

        (status, resp) = self.server.setAudioCodec(idnr, self.profile['audiocodec'], self.profile['audiobitrate'])
        logger.debug('setAudioCodec:status:%s resp:%s', status, resp)
        if not status:
            self.error(resp)
            return

        (status, resp) = self.server.setNumThreads(idnr, self.profile['numthreads'])
        logger.debug('setNumThreads:status:%s resp:%s', status, resp)
        if not status:
            self.error(resp)
            return

        #(status, resp) = self.server.setVideoFilters(idnr, self.vfilters)
        #_debug_('setVideoFilters:status:%s resp:%s' % (status, resp))

        #And finally, qeue and start the job
        (status, resp) = self.server.queueIt(idnr, True)
        logger.debug('queueIt:status:%s resp:%s', status, resp)

        if not status:
            self.error(resp)
            return

        logger.debug('boe')
        #menuw.delete_menu()
        #menuw.delete_menu()
        return job_status


    def encodingstatus(self):
        (estatus, eresponse) = self.server.getProgress()
        encodingstatus = '<div id="EncodingStatus">'
        encodingstatus += 'Encoding Status :<ul>'

        (status, response) = self.server.listJobs()
        #encodingstatus += '<Status : %r Respones: %r' % (status, response)

        if estatus:
            encodingstatus += '<li>%s</li>' % eresponse[0]
            rstatus = ''
            if eresponse[1] == 1 :
                rstatus = "Audio pass in progress"
            elif eresponse[1] ==  2:
                rstatus = 'First (analyzing) video pass'
            elif eresponse[1] == 3:
                rstatus = 'Final video pass'
            elif eresponse[1] == 4:
                rstatus = 'Postmerge'

            encodingstatus += '<li>%s</li>' % rstatus
            encodingstatus += '<li>Percent Completed : %%%r</li>' % eresponse[2]
            encodingstatus += '<li>ETA : %s</li>' % eresponse[3]
        else:
            encodingstatus += '</li>No Jobs to Encode</li>'

        encodingstatus += '</ul></div>'
        return encodingstatus


    def _render(self, request):
        """
        """
        logger.log( 9, '_render(request)')
        fv = HTMLResource()
        form = request.args

        cmd = fv.formValue(form, 'cmd')
        self.browsedir = fv.formValue(form, 'browsedir')

        browsefolder = fv.formValue(form, 'browsefolder')
        if browsefolder:
            return GetFileList(browsefolder)

        fv.printHeader(_('Web Encoder'), 'styles/main.css', selected=_('Web Encoder'))
        fv.res += '\n<link rel="stylesheet" href="styles/encoding_web.css" type="text/css" />\n'
        fv.res += '<br><br><br>'

        self.profile = {}
        self.profile['container'] = fv.formValue(form, 'container')
        if not self.profile['container']:
            self.profile['container'] = config.REENCODE_CONTAINER

        self.profile['resolution'] = fv.formValue(form, 'resolution')
        if not self.profile:
            self.profile['resolution'] = config.REENCODE_RESOLUTION

        self.profile['videocodec'] = fv.formValue(form, 'videocodec')
        if not self.profile['videocodec']:
            self.profile['videocodec'] = config.REENCODE_VIDEOCODEC

        self.profile['audiocodec'] = fv.formValue(form, 'audiocodec')
        if not self.profile['audiocodec']:
            self.profile['audiocodec'] = config.REENCODE_AUDIOCODEC

        self.profile['numpasses'] = fv.formValue(form, 'numpasses')
        if not self.profile['numpasses']:
            self.profile['numpasses'] = config.REENCODE_NUMPASSES

        self.profile['videobitrate'] = fv.formValue(form, 'videobitrate')
        if not self.profile['videobitrate']:
            self.profile['videobitrate'] = config.REENCODE_VIDEOBITRATE

        self.profile['audiobitrate'] = fv.formValue(form, 'audiobitrate')
        if not self.profile['audiobitrate']:
            self.profile['audiobitrate'] = config.REENCODE_AUDIOBITRATE

        self.profile['videofilter'] = fv.formValue(form, 'videofilter')
        if not self.profile['videofilter']:
            self.profile['videofilter'] = config.REENCODE_VIDEOFILTER

        self.profile['numthreads'] = fv.formValue(form, 'numthreads')
        if not self.profile['numthreads']:
            self.profile['numthreads'] = config.REENCODE_NUMTHREADS

        self.select_encoding_profile('Nokia770')
        preset = fv.formValue(form, "preset")
        if preset:
            self.select_encoding_profile(preset)

        cmd = fv.formValue(form, 'cmd')
        if cmd == 'encodingstatus':
            return str( self.encodingstatus() )

        encodefile = fv.formValue(form, 'encodefile')
        if encodefile:
            fv.res = 'Starting Encode Job for %s' % encodefile
            self.source = encodefile
            self.output = encodefile + '.avi'
            self.title = encodefile
            fv.res += self.create_job(encodefile)
            fv.res += self.encodingstatus()
            return str(fv.res)

        fv.res += self.EncodingParameters()
        fv.res += self.encodingstatus()
        fv.res += addPageRefresh(False)
        fv.res += '<br>'

        fv.res += '<div id="FileList">'
        fv.res += GetFileList(self.browsedir)
        fv.res += '</div>'
        fv.res += ''
        return str(fv.res)

resource = CDBurn_WebResource()
