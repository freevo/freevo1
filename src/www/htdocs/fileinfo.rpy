# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Dynamically update program info popup box.
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

import util
import config
import kaa.metadata as metadata
from twisted.web import static

MAX_DESCRIPTION_CHAR = 1000

class FileInfoResource(FreevoResource):

    def __init__(self):
        self.allowed_dirs = []
        self.allowed_dirs.extend(config.VIDEO_ITEMS)
        self.allowed_dirs.extend(config.AUDIO_ITEMS)
        self.allowed_dirs.extend( [ ('Recorded TV', config.TV_RECORD_DIR) ])
        self.allowed_dirs.extend(config.IMAGE_ITEMS)

    def _render(self, request):
        fv = HTMLResource()
        form = request.args
        file = fv.formValue(form, 'dir')
        img = fv.formValue(form, 'img')

        if file:
            medium = metadata.parse(file)
            title = ''
            (basedir, item) = os.path.split(file)

            fxd_file = file[:file.rindex('.')] + '.fxd'
            if os.path.exists(fxd_file):
                fxd_info = self.get_fxd_info(fxd_file)
                title=fxd_info['title']
                if not title:
                    title = util.mediainfo.get(item)['title']
                    if not title:
                        title = item
                info = ''
                status = ''
                if fxd_info.has_key('watched'):
                    if fxd_info['watched'] == 'False':
                        status='unwatched'
                    else:
                        status='watched'
                if fxd_info.has_key('keep'):
                    if fxd_info['keep'] == 'True':
                        status='keep'
                if status:
                    info += '<img src="images/library/television_'+status+'.png" width=23 height=23 align="right"/>'
                if fxd_info.has_key('tagline'):
                    info += '"'+fxd_info['tagline']+'"<br/>'
                if fxd_info.has_key('plot'):
                    info += fxd_info['plot']+'<br/>'
                if info != '':
                    info += '<p>'
                if fxd_info.has_key('userdate'):
                    info += '<b>Recorded:</b>&nbsp;'+fxd_info['userdate']+' '
                if fxd_info.has_key('runtime'):
                    info += '<b>Runtime:</b>&nbsp;'+fxd_info['runtime']+' '
                info += '<b>Size:</b>&nbsp;'+str((os.stat(file)[6]/1024)/1024)+' MB'
            else:
                media_info = util.mediainfo.get(file)
                title = Unicode(media_info['title'])
                if not title:
                    title = string.replace(os.path.splitext(item)[0],"_"," ")
                #audio info
                info = ""
                if media_info['artist']:
                    info += Unicode(media_info['artist'])+'<br/>'
                if media_info['album']:
                    info += '"'+Unicode(media_info['album'])+'"'
                if media_info['userdate']:
                    info += ' - '+Unicode(media_info['userdate'])
                if media_info['album'] or media_info['userdate']:
                    info += '<br/>'
                if media_info['genre']:
                    info += Unicode(media_info['genre'])+'<br/>'
                if info != '':
                    info += '<p>'
                if media_info['length']:
                    min = int(media_info['length'] / 60)
                    sec = int(media_info['length'] - (min * 60))
                    info += '<b> Length:&nbsp;</b>'+str(min)+':'+str(sec)
                info += ' <b>Size:&nbsp;</b>'+str((os.stat(file)[6]/1024)/1024)+' MB'
                if media_info['track']:
                    info += ' <b>Track:&nbsp;</b>'+media_info['track']
                if media_info['bitrate'] or media_info['samplerate']:
                    info += ' <b>Stream Info:&nbsp;</b>'
                if media_info['bitrate']:
                    info += str(media_info['bitrate'])+'Kbps'
                if media_info['bitrate'] and media_info['samplerate']:
                    info += '/'
                if media_info['samplerate']:
                    info += str(media_info['samplerate']/1000)+'kHz'

                #movie info
                if media_info['height'] and media_info['width']:
                    info += ' <b>Dimensions:&nbsp;</b>'+str(media_info['width'])+' x '+str(media_info['height'])
                if media_info['type']:
                    info += ' <b>Type:&nbsp;</b>'+media_info['type']+'<br/>'

            file_link = self.convert_dir(file)

            fv.res += (
               u"<html>\n<head>\n" \
               u'<meta http-equiv="Content-Type" content= "text/html; charset='+ config.encoding +'"/>\n' \
               u"<script>\n" \
               u"var doc = parent.top.document;\n" \
               u"doc.getElementById('file-head').innerHTML = '%s';\n"\
               u"doc.getElementById('file-info').innerHTML = '%s';\n"\
               u"doc.getElementById('file-play-button').onclick = %s;\n"\
               u"doc.getElementById('file-play-using-vlc').onclick = %s;\n"\
               u"doc.getElementById('file-play-using-html5').onclick = %s;\n"\
               u"doc.getElementById('file-play-using-flash').onclick = %s;\n"\
               u"doc.getElementById('program-waiting').style.display = 'none';\n" \
               u"doc.getElementById('program-info').style.visibility = 'visible';\n" \
               u"</script>\n" \
               u"</head>\n<html>\n"
            ) % ( Unicode(title.replace("'", "\\'")),
                  Unicode(info.replace("'", "\\'")),
                  "function() { window.open(\"%s\"); }" % (urllib.quote(file_link)),
                  "function() { window.open(\"vlcwin.rpy?dir=%s\"); }" % (urllib.quote(file_link)),
                  "function() { window.open(\"html5win.rpy?dir=%s\"); }" % (urllib.quote(file_link)),
                  "function() { window.open(\"flashwin.rpy?dir=%s\"); }" % (urllib.quote(file_link))
            )

        elif img:
            _img = img.split("_")#
            img_name = _img[len(_img)-1]
            height = fv.formValue(form, 'h')
            width = fv.formValue(form, 'w')
            fv.res += (
               u"<html>" \
               u"<head><title>%s</title>" \
               u'<meta http-equiv="Content-Type" content= "text/html; charset='+ config.encoding +'"/>\n' \
               u"<link href=\"styles/main.css\" rel=\"stylesheet\" type=\"text/css\" /></head>" \
               u"<body>"\
               u"<img src=\"%s\" height=\"%s\" width=\"%s\" />"\
               u"</body></html>"
            ) % ( img_name, img, height, width )

        return String(fv.res)

    def get_fxd_info(self, fxd_file):
        #print 'get_fxd_info(self, %r)' % (fxd_file)
        fxd_info = {}
        parser = util.fxdparser.FXD(fxd_file)
        parser.parse()
        for a in parser.tree.tree.children:
            if a.name == 'movie':
                fxd_info.update({'title':str(a.attrs.values()[0])})
            cover = parser.childcontent(a, "cover-img")
            if cover:
                fxd_info.update({'cover-img':cover})
            for b in a.children:
                if b.name == 'info':
                    for c in b.children:
                        name = c.name.replace('\r', '').replace('\n', ' ')
                        first_cdata = c.first_cdata.replace('\r', '').replace('\n', ' ')
                        if first_cdata == '' or first_cdata == 'None':
                            continue
                        fxd_info.update({str(name):str(first_cdata)})
        return fxd_info

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


resource = FileInfoResource()
