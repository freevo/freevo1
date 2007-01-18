#!/usr/bin/python

# -----------------------------------------------------------------------
# proginfo.rpy - Dynamically update program info popup box.
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
from twisted.web.woven import page
import util
import config 
import kaa.metadata as metadata 
from twisted.web import static

MAX_DESCRIPTION_CHAR = 1000

class FileInfoResource(FreevoResource):

    def __init__(self):
        print '__init__(self)'
        self.allowed_dirs = []
        self.allowed_dirs.extend(config.VIDEO_ITEMS)
        self.allowed_dirs.extend(config.AUDIO_ITEMS)
        self.allowed_dirs.extend( [ ('Recorded TV', config.TV_RECORD_DIR) ])
        self.allowed_dirs.extend(config.IMAGE_ITEMS)

    def _render(self, request):
        print '_render(self, %s)' % (request)
        fv = HTMLResource()
        form = request.args
        file = fv.formValue(form, 'dir')
        img = fv.formValue(form, 'img')
        
        if file:
            medium = metadata.parse(file)
            #print medium
            title = ""
            info = "<table>"
            (basedir, item) = os.path.split(file)
            
            fxd_file = file[:file.rindex('.')] + ".fxd"
            if os.path.exists(fxd_file):
                fxd_info = self.get_fxd_info(fxd_file)
                i = 0            
                for z in fxd_info:
                    if z and z != "cover-img":
                        info += "<tr><td><b>" + fxd_info.keys()[i] + ": </b></td><td>"+fxd_info.values()[i]+"</td></tr>"
                    i +=1
                title=fxd_info['title']
                if not title:
                    title = util.mediainfo.get(item)['title']
                    if not title:
                        title = item
            else:
                media_info = util.mediainfo.get(file)
                title = media_info['title']
                if not title:
                    title = item
                #audio info
                if media_info['artist']:
                    info+='<tr><td><b>Artist: </b></td><td>'+media_info['artist']+'</td></tr>'
                if media_info['album']:
                    info+='<tr><td><b>Album: </b></td><td>'+media_info['album']+'</td></tr>'
                if media_info['genre']:
                    info+='<tr><td><b>Genre: </b></td><td>'+media_info['genre']+'</td></tr>'
                if media_info['length']:
                    length = str(int(media_info['length']) / 60) + " min."
                    info+='<tr><td><b>Length: </b></td><td>'+length+'</td></tr>'
                #movie info
                if media_info['height'] and media_info['width']:
                    info +='<tr><td><b>Dimensions: </b></td><td>'+str(media_info['height'])+' x '\
                        +str(media_info['width'])+'</td></tr>' 
                if media_info['type']:
                   info+='<tr><td><b>Type: </b></td><td>'+media_info['type']+'</td></tr>' 
            #add size
            info+='<tr><td><b>Size: </b></td><td>'+str((os.stat(file)[6]/1024)/1024)+' MB</td></tr>'
            info+= "</table>"
            
            file_link = self.convert_dir(file)
            
            fv.res += (
               u"<script>\n" \
               u"var doc = parent.top.document;\n" \
               u"doc.getElementById('file-head').innerHTML = '%s';\n"\
               u"doc.getElementById('file-info').innerHTML = '%s';\n"\
               u"doc.getElementById('file-play-button').onclick = %s;\n"\
               u"doc.getElementById('file-play-using-vlc').onclick = %s;\n"\
               u"doc.getElementById('program-waiting').style.display = 'none';\n" \
               u"doc.getElementById('program-info').style.visibility = 'visible';\n" \
               u"</script>\n"
            ) % ( Unicode(title.replace("'", "\\'")),
                  Unicode(info.replace("'", "\\'")),
                  "function() { window.open(\"%s\"); }" % (file_link),
                  '\
                  function() { \
                      vlc_window = window.open(""); \
                      vlc_window.document.write(\'<html><head><title>VLC Player</title></head><body>\'); \
                      vlc_window.document.write(\'<embed type="application/x-vlc-plugin" name="video" autoplay="yes" \'); \
                      vlc_window.document.write(\'width="640" height="480" target="http://\'); \
                      vlc_window.document.write(location.hostname + \':\' + location.port + \'/' + urllib.quote(file_link) + '"/><br/>\'); \
                      vlc_window.document.write(\'<a href="javascript:;" onclick="document.video.play()">Play</a>&nbsp\'); \
                      vlc_window.document.write(\'<a href="javascript:;" onclick="document.video.pause()">Pause</a>&nbsp\'); \
                      vlc_window.document.write(\'<a href="javascript:;" onclick="document.video.stop()">Stop</a>&nbsp\'); \
                      vlc_window.document.write(\'<a href="javascript:;" onclick="document.video.fullscreen()">Fullscreen</a>\'); \
                      vlc_window.document.write(\'</body></html>\'); \
                  }\
                  '
            )           

        elif img:
            _img = img.split("_")#
            img_name = _img[len(_img)-1]
            height = fv.formValue(form, 'h')
            width = fv.formValue(form, 'w')
            fv.res += (
               u"<html>" \
               u"<head><title>%s</title>" \
               u"<link href=\"styles/main.css\" rel=\"stylesheet\" type=\"text/css\" /></head>" \
               u"<body>"\
               u"<img src=\"%s\" height=\"%s\" width=\"%s\" />"\
               u"</body></html>"
            ) % ( img_name, img, height, width )
            
        return String(fv.res)
    
    def get_fxd_info(self, fxd_file):
        print 'get_fxd_info(self, %r)' % (fxd_file)
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
        print 'convert_dir(self, dir_str=%r)' % (dir_str)
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
