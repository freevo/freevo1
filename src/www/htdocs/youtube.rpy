#!/usr/bin/python
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


import sys
import os
import os.path
import config
from www.web_types import HTMLResource, FreevoResource
from urllib import urlopen
from getopt import getopt

def createDownload(url, proxy=None):
    instream=urlopen(url, None, proxy)

    filename=instream.info().getheader("Content-Length")
    if filename==None:
        filename="temp"

    return (instream, filename)


def getURLName(url):
    directory=os.curdir

    name="%s%s%s" % (
        directory,
        os.sep,
        url.split("/")[-1]
    )

    print "NAME "
    print name
    return name

def download_url (dl_url):
    print "Download URL - " + dl_url
    url = dl_url

    try:
        outfile=open(getURLName(url), "wb")
        fileName=outfile.name.split(os.sep)[-1]
        fileName = config.YOUTUBE_DIR + fileName
        print "FILENAME - " + fileName

        url, length=createDownload(url, None)
        if not length:
            length="?"
        print "Downloading %s (%s bytes) ..." % (url.url, length)

        if length!="?":
            length=float(length)
        bytesRead=0.0

        for line in url:
            bytesRead+=len(line)
            outfile.write(line)

        url.close()
        outfile.close()
        print "Done"

    except Exception, e:
        return "Error downloading %s: %s" % (dl_url, e)

    return "Done downloading - " + dl_url

def download_youtube(yt_url, yt_out):

    cmd = "python " + config.YOUTUBE_DL + " -t  " + yt_url
    pwdcur = os.getcwd()
    pwddl = config.YOUTUBE_DIR
    os.chdir(pwddl)

    cnt = 1
    for ln in os.popen(cmd).readline():
        print "COUNTING"
        print cnt
        cnt = cnt + 1
        print ln

#    child = os.popen(cmd)
#    data = child.read()

#    err = child.close()
#    if err:
#        raise RuntimeError, '%s failed w/ exit code %d' % (command, err)
    os.chdir(pwdcur)
    return "<br/><br/>Done downloading " + yt_url


class YouTubeResource(FreevoResource):

    def _render(self, request):
        fv = HTMLResource()
        fv.printHeader(_('YouTube'), 'styles/main.css',selected=_('YouTube'))
        form = request.args

        # Check to see if youtube-dl script exists.
        if not os.path.exists(config.YOUTUBE_DL):
            fv.res += '<br/><br/><br/><b>Unable to locate youtube-dl script  "' + config.YOUTUBE_DL + '" </b><br/>'
            fv.res += 'Download scripts from  <a href="http://www.arrakis.es/~rggi3/youtube-dl/">http://www.arrakis.es/~rggi3/youtube-dl/</a>'
            fv.res += '<br/>Add YOUTUBE_DL = "path and file name to youtube_dl script"<br/>'

        if not os.path.exists(config.YOUTUBE_DIR):
            fv.res += '<br/><b>Unable to locate youtube download location "' + config.YOUTUBE_DIR + '" </b><br/>'
            fv.res += 'Add YOUTUBE_DIR = "download directory" to your local_conf.py'


        yturl = fv.formValue(form,'yt_url')
        if yturl :
            print yturl
            yt_status = download_youtube(yturl,"")
            fv.res += "<br/>" + yt_status

        yturl = ""
        fv.res  += '<br/><form id="YouTube Download" action="youtube.rpy" method="get">'
        fv.res  += '<div class="searchform"><br/><b>Youtube URL :</b><input type="text" name="yt_url" size="40" value="' + yturl + '" />'
        fv.res  += '<input type="submit" value=" Download! " />'
        fv.res  += '</div>'
        fv.res  += '</form>'

        dlurl = fv.formValue(form,'dl_url')
        if dlurl :
            dl_status = download_url(dlurl)
            fv.res += "<br/>" + dl_status
        else :
            dlurl = ""

        fv.res  += '<br/><form id="Url Download" action="youtube.rpy" method="get">'
        fv.res  += '<div class="searchform"><br/><b>Download URL :</b><input type="text" name="dl_url" size="40" value="' + dlurl + '" />'
        fv.res  += '<input type="submit" value=" Download! " />'
        fv.res  += '</div>'
        fv.res  += '</form>'

        return String( fv.res )

resource = YouTubeResource()
