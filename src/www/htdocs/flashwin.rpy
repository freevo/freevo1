# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to play files using flash
# -----------------------------------------------------------------------
# $Id: flashwin.rpy 10391 2008-02-20 20:52:22Z duncan $
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
import util
import config
import mimetypes
import kaa.metadata as metadata
from twisted.web import static

class FlashWinResource(FreevoResource):

    def __init__(self):
        #print 'FlashWinResource.__init__(self)'
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
            (mimetype, encoding) = mimetypes.guess_type(file_link)

            fv.res += u'''<html><body>
<script type="text/javascript">
document.write("<object type=\\"application/x-shockwave-flash\\" data=\\"http://player.longtailvideo.com/player.swf\\" width=\\"640\\" height=\\"480\\">");
document.write("<param name=\\"movie\\" value=\\"http://player.longtailvideo.com/player.swf\\" />");
document.write("<param name=\\"allowFullScreen\\" value=\\"true\\" />");
document.write("<param name=\\"wmode\\" value=\\"transparent\\" />");
document.write("<param name=\\"flashVars\\" value=\\"controlbar=over&amp;image=" + location.protocol +"//"+ location.host + "/M_poster.jpg&amp;file=" + location.protocol + "//" + location.host + "/%s\\" />");
document.write("<img alt='Big Buck Bunny' src='http://sandbox.thewikies.com/vfe-generator/images/big-buck-bunny_poster.jpg' width='640' height='480' title='No video playback capabilities, please download the video below' />");
document.write("</object>");
</script></body></html>''' % (urllib.quote(file_link))

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


resource = FlashWinResource()
