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

import sys, os, stat, string
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
        self.cache_dir = '%s/link_cache/' % (config.FREEVO_CACHEDIR)
        if not os.path.isdir(self.cache_dir):
            os.mkdir(self.cache_dir, stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))

    def _render(self, request):
        fv = HTMLResource()
        form = request.args
        file = fv.formValue(form, 'dir')
        img = fv.formValue(form, 'img')
        
        if file:
            #medium = metadata.parse(file)
            title = ""
            info = "<table>"
            
            fxd_file = file[:file.rindex('.')] + ".fxd"
            if os.path.exists(fxd_file):
                fxd_info = self.get_fxd_info(fxd_file)
                i = 0            
                for z in fxd_info:
                    if z != "" and z != "cover-img":
                        info += "<tr><td><b>" + fxd_info.keys()[i] + ": </b></td><td>"+fxd_info.values()[i]+"</td></tr>"
                    i +=1
                title=fxd_info['title']
                if title == "":
                    title = util.mediainfo.get(file)['title']
            else:
                media_info = util.mediainfo.get(file)
                title = media_info['title']
                #audio info
                if media_info['artist']:
                    info+='<tr><td><b>Artist: </b></td><td>'+media_info['artist'] +'</td></tr>'
                if media_info['album']:
                    info+='<tr><td><b>Album: </b></td><td>'+media_info['album']+'</td></tr>'
                if media_info['genre']:
                    info+='<tr><td><b>Genre: </b></td><td>'+media_info['genre']+'</td></tr>'
                if media_info['length'] and media_info['length'] != 0:
                    length = str(int(media_info['length']) / 60) + " min."
                    info+='<tr><td><b>Length: </b></td><td>'+length+'</td></tr>'
                #movie info
                if media_info['height'] != "" and media_info['width'] != "":
                    info +='<tr><td><b>Dimensions: </b></td><td>'+str(media_info['height'])+' x '\
                        +str(media_info['width'])+'</td></tr>' 
                if media_info['type'] != "":
                   info+='<tr><td><b>Type: </b></td><td>'+media_info['type']+'</td></tr>' 
            #add size
            info+='<tr><td><b>Size: </b></td><td>'+str((os.stat(file)[6]/1024)/1024)+' MB</td></tr>'
            info+= "</table>"
            
            file_link = self.create_file_link(file)
            
            fv.res += (
               u"<script>\n" \
               u"var doc = parent.top.document;\n" \
               u"doc.getElementById('file-head').innerHTML = '%s';\n"\
               u"doc.getElementById('file-info').innerHTML = '%s';\n"\
               u"doc.getElementById('file-play-button').onclick = %s;\n"\
               u"doc.getElementById('program-waiting').style.display = 'none';\n" \
               u"doc.getElementById('program-info').style.visibility = 'visible';\n" \
               u"</script>\n"
            ) % ( title , 
                  info,
                  "function() { window.open(\"%s\"); }" % (file_link),    
            )           

        elif img:
            _img = img.split("_")#
            img_name = _img[len(_img)-1]
            fv.res += (
               u"<html>" \
               u"<head><title>%s</title>" \
               u"<link href=\"styles/main.css\" rel=\"stylesheet\" type=\"text/css\" /></head>" \
               u"<body>"\
               u"<img src=\"%s\" />"\
               u"</body></html>"
            ) % ( img_name, img )
            
        return String(fv.res)
    
    def create_file_link(self, file):
        cache_link = self.cache_dir + file.replace("/", "_")
        if not os.path.exists(cache_link):
            os.symlink(file, cache_link)
        return cache_link
    
    def get_fxd_info(self, fxd_file):
        fxd_info = {}
        parser = util.fxdparser.FXD(fxd_file)
        parser.parse()
        for a in parser.tree.tree.children:
            if a.name == 'movie':
                fxd_info.update({'title':str(a.attrs.values()[0])})
            for b in a.children:
                if b.name == 'cover-img':
                    fxd_info.update({'cover-img':str(b.attrs.values()[0])})
                if b.name == 'info':
                    for c in b.children:
                        fxd_info.update({str(c.name):str(c.first_cdata)})
        return fxd_info

resource = FileInfoResource()
