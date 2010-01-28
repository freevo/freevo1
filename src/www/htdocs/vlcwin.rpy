# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to vlc
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

import sys, os, stat, string, urllib
import time

from www.web_types import HTMLResource, FreevoResource

import config
import util
import kaa.metadata as metadata
from twisted.web import static

class VlcWinResource(FreevoResource):

    def __init__(self):
        #print 'VlcWinResource.__init__(self)'
        self.allowed_dirs = []
        self.allowed_dirs.extend(config.VIDEO_ITEMS)
        self.allowed_dirs.extend(config.AUDIO_ITEMS)
        self.allowed_dirs.extend( [ ('Recorded TV', config.TV_RECORD_DIR) ])
        self.allowed_dirs.extend(config.IMAGE_ITEMS)

    def _render(self, request):
        #print '_render(self, %s)' % (request)
        fv = HTMLResource()
        form = request.args
        file = fv.formValue(form, 'dir')

        if file:
            file_link = self.convert_dir(file)
            #print 'file_link=%s' % (file_link)

            fv.res += (
               u"<STYLE> .inputTrackerInput { height:20; width:30; font-family : Arial, Helvetica, sans-serif; font-size : 12px; } </STYLE>\n" \
               u"<script type=text/javascript src=videolan/LibCrossBrowser.js></script>\n" \
               u"<SCRIPT type=text/javascript src=videolan/EventHandler.js></SCRIPT>\n" \
               u"<SCRIPT type=text/javascript src=videolan/Bs_FormUtil.lib.js></SCRIPT>\n" \
               u"<SCRIPT type=text/javascript src=videolan/Bs_Slider.class.js></SCRIPT>\n" \
               u"<SCRIPT type=text/ecmascript src=videolan/vlc_init.js></SCRIPT>\n" \
               u"<SCRIPT type=text/ecmascript src=videolan/vlc_funcs.js></SCRIPT>\n" \
               u"<SCRIPT type=text/javascript>function UrlToPlay() {var url=\'http://\' + location.hostname + \':\' + location.port + \'/" \
               + urllib.quote(file_link) + "\'; return url;} </SCRIPT>\n" \
               u"<body onLoad='init(); doGo(UrlToPlay());'>\n" \
               u"<TABLE> <TR><TD colspan='2'>\n" \
               u"<TR><TD align='center' colspan='2'>\n" \
               u"<OBJECT classid='clsid:9BE31822-FDAD-461B-AD51-BE1D1C159921'\n" \
               u"  codebase='http://downloads.videolan.org/pub/videolan/vlc/latest/win32/axvlc.cab#Version=0,8,6,0'\n" \
               u"  width='640'\n" \
               u"  height='480'\n" \
               u"  id='vlc'\n" \
               u"  events='True'>\n" \
               u"  <param name='MRL' value='' />\n" \
               u"  <param name='ShowDisplay' value='True' />\n" \
               u"  <param name='AutoLoop' value='False' />\n" \
               u"  <param name='AutoPlay' value='False' />\n" \
               u"  <param name='Volume' value='50' />\n" \
               u"  <param name='StartTime' value='0' />\n" \
               u"  <EMBED pluginspage='http://www.videolan.org'\n" \
               u"    type='application/x-vlc-plugin'\n" \
               u"    progid='VideoLAN.VLCPlugin.2'\n" \
               u"    width='640'\n" \
               u"    height='480'\n" \
               u"    name='vlc'>\n" \
               u"  </EMBED>\n" \
               u"</OBJECT>\n" \
               u"</TD></TR><TR><TD colspan='2'>\n" \
               u"<TABLE> <TR><TD valign='top' width='550'>\n" \
               u"<DIV id='inputTrackerDiv'></DIV></TD><TD width='15%'><DIV id='info' style='text-align:center'>-:--:--/-:--:--</DIV>\n" \
               u"</TD></TR></TABLE> </TD></TR><TR><TD>\n" \
               u"<INPUT type=button id='PlayOrPause' value=' Play ' disabled onClick='doPlayOrPause();'>\n" \
               u"<INPUT type=button id='Stop' value='Stop' disabled onClick='doStop();'>&nbsp;\n" \
               u"<INPUT type=button value=' << ' onClick='doPlaySlower();'>\n" \
               u"<INPUT type=button value=' >> ' onClick='doPlayFaster();'>\n" \
               u"<INPUT type=button value=' <-> ' onClick=getVLC('vlc').video.toggleFullscreen();>\n" \
               u"AR:<SELECT readonly onChange='doChangeAspectRatio(this.value)'><OPTION value='default'>Default</OPTION>\n" \
               u"<OPTION value='1:1'>1:1</OPTION><OPTION value='4:3'>4:3</OPTION><OPTION value='16:9'>16:9</OPTION>\n" \
               u"<OPTION value='221:100'>221:100</OPTION><OPTION value='5:4'>5:4</OPTION>\n" \
               u"</SELECT>&nbsp;&nbsp;<INPUT type=button value='Version' onClick=alert(getVLC('vlc').VersionInfo);>\n" \
               u"</TD><TD align='right'> <SPAN style='text-align:center'>Volume:</SPAN>\n" \
               u"<INPUT type=button value=' - ' onClick='updateVolume(-10)'><SPAN id='volumeTextField' style='text-align: center'>\n" \
               u"--</SPAN><INPUT type=button value=' + ' onClick='updateVolume(+10)'><INPUT type=button value='Mute'\n" \
               u"onClick=getVLC('vlc').audio.toggleMute();></TD></TR></TABLE>\n" \
               u"</body></html>\n" \
            )

        return String(fv.res)

    def convert_dir(self, dir_str):
        #print 'convert_dir(self, dir_str=%r)' % (dir_str)
        for i in range(len(self.allowed_dirs)):
            val = self.allowed_dirs[i][1]
            if dir_str.startswith(val):
                child_res = val.replace("/", "_")
                location = dir_str[len(val):]
                if not location[0] == "/":
                    child_res += "/"
                return child_res + location
        return dir_str


resource = VlcWinResource()
