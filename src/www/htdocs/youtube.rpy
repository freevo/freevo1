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
import time
import os
import os.path
import config
import subprocess
import string
import math

from www.web_types import HTMLResource, FreevoResource
from urllib import urlopen
from getopt import getopt

print "CONFIG====="
print (config)

def xmlStatus(fstatus):
    xmlstatus = ""
    xmlstatus += "<PERCENT>" + fstatus['percent'] + "</PERCENT>"
    xmlstatus += "<DOWNLOADED>" + fstatus['downloaded'] + "</DOWNLOADED>"
    xmlstatus += "<FILESIZE>" + fstatus['filesize'] + "</FILESIZE>"
    xmlstatus += "<SPEED>" + fstatus['speed'] + "</SPEED>"
    xmlstatus += "<ETA>" + fstatus['eta'] + "</ETA>"

    return xmlstatus

# Get optimum 1k exponent to represent a number of bytes
def optimum_k_exp(num_bytes):
    const_1k = 1024
    if num_bytes == 0:
        return 0
    return long(math.log(num_bytes, const_1k))


# Get optimum representation of number of bytes
def format_bytes(num_bytes):
    const_1k = 1024
    try:
        exp = optimum_k_exp(num_bytes)
        suffix = 'bkMGTPEZY'[exp]
        if exp == 0:
            return '%s%s' % (num_bytes, suffix)
        converted = float(num_bytes) / float(const_1k**exp)
        return '%.2f%s' % (converted, suffix)
    except IndexError:
        return "Error"


def getStatus(ytfile):
    fileStatus = {'percent': '--.-%', 'downloaded': 'done' , 'filesize': 'DONE' ,'speed' : '--', 'eta' : '--:--'}
    fileStatus['filesize'] = format_bytes(os.path.getsize(config.YOUTUBE_DIR + ytfile))
    logfile = config.YOUTUBE_DIR + ".tmp/" + os.path.splitext(ytfile)[0] + ".log"
    if os.path.exists(logfile):
        lfhandle = open(logfile, "r")
        llines = lfhandle.readlines()
        try :
            if len(llines) == 5:
                status = llines[4].split("\r")[-1]
                status = status.split()
                fileStatus['percent'] = status[3]
                fileStatus['downloaded'] = status[5]
                fileStatus['filesize'] = status[7].strip(")")
                fileStatus['speed'] = status[9]
                fileStatus['eta'] = status[11]
            else:
                fileStatus['percent'] = "NA"
                fileStatus['downloaded'] = "NA"
                fileStatus['speed'] = "NA"
                fileStatus['eta'] = "Unknown"
        except Exception, e:
            fileStatus['percent'] = "NA"
            fileStatus['downloaded'] = "NA"
            fileStatus['speed'] = "NA"
            fileStatus['eta'] = "Unknown"
    return fileStatus


def getXML():

    dfiles = '<?xml version="1.0" encoding="ISO-8859-1" ?>'
    dfiles += '<FILELIST>'
    enablerefresh = False

    filelist = os.listdir(config.YOUTUBE_DIR)
    filelist.sort()
    for fl in filelist :
        if fl != ".tmp" and fl != "folder.fxd" :
            # check for log file.
            dfiles += '<FILE id="' + fl + '">'
            dfiles += '<FILENAME>' + fl + '</FILENAME>'
            fstats = getStatus(fl)
            dfiles += xmlStatus(fstats)
            dfiles += '</FILE>'
    dfiles += "</FILELIST>"
    retdfile = []
    retdfile.append(dfiles)
    retdfile.append(enablerefresh)
    return retdfile

def displayfiles(fvhtml):
    fvhtml.res += ''
    fvhtml.tableOpen('class="library" id="filelist"')
    fvhtml.tableRowOpen('class="chanrow"')
    fvhtml.tableCell('Current Downloads','class ="guidehead"  colspan="2"')
    fvhtml.tableCell('% Done','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('Size','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('Speed','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('ETA','class ="guidehead"  colspan="1"')
    fvhtml.tableRowClose()

    enablerefresh = False

    filelist = os.listdir(config.YOUTUBE_DIR)
    filelist.sort()
    for fl in filelist :

        # check to see if the file is currently being downloaded.
        if fl != ".tmp" and fl != "folder.fxd" :

            # check for log file.
            flstatus = getStatus(fl)
            fvhtml.tableRowOpen('class="chanrow" colspan="1" id="'+fl +'"')
            fvhtml.tableCell('<a href="youtube.rpy?Delete=1&file=' + fl + '">DELETE</a>','class="basic" colspan="1"')
            fvhtml.tableCell(fl,'class="basic" colspan="1"')
            fvhtml.tableCell(flstatus['percent'],'class="basic" colspan="1" id="' + fl + '.PERCENT"')
            fvhtml.tableCell(flstatus['downloaded'],'class="basic" colspan="1" id = "' + fl + '.SOFAR"')
            fvhtml.tableCell(flstatus['filesize'],'class="basic" colspan="1" id="' + fl + '.FILESIZE"')
            fvhtml.tableCell(flstatus['speed'],'class="basic" colspan="1" id="' + fl + '.SPEED"')
            fvhtml.tableCell(flstatus['eta'],'class="basic" colspan="1" id="' + fl + '.ETA"')
            fvhtml.tableRowClose()

    fvhtml.tableClose()
    retdfile = []
    retdfile.append(fvhtml.res)
    retdfile.append(enablerefresh)
    return retdfile


def CleanupLogFiles():
    logfiles = os.listdir(config.YOUTUBE_DIR + ".tmp/")

    for lfile in logfiles:
        # Check to see if the movie file exists.
        vfile = config.YOUTUBE_DIR + os.path.splitext(lfile)[0] + ".flv"
        if not os.path.exists(vfile):
            os.remove(config.YOUTUBE_DIR + ".tmp/" + lfile)


def download_youtube(yt_url, yt_out):

    stime = time.localtime()
    cmd = "python " + config.YOUTUBE_DL + " -t " + yt_url
    pwdcur = os.getcwd()
    os.chdir(config.YOUTUBE_DIR)

    # get the file name from the url.
    logfile = config.YOUTUBE_DIR + ".tmp/" +  yt_url.split("=")[-1] + ".log"
    ytpid = 0
    lfile = open (logfile, "w")
    ytpid = subprocess.Popen((config.YOUTUBE_DL,"-t",yt_url),universal_newlines=True,stdout=lfile).pid
    os.chdir(pwdcur)
    dlstatus = "<br><br>Starting download of " + yt_url + " <br>"
    dlstatus = dlstatus + '<input type="text" name="pid" size="40" value="' + str(ytpid) + '" />'

    return dlstatus

def download_url(dl_url, dl_out):

    stime = time.localtime()
    cmd = "python " + config.DOWNLOAD_DL + " " + dl_url
    pwdcur = os.getcwd()
    os.chdir(config.YOUTUBE_DIR)

    # get the file name from the url.
    logfile = config.YOUTUBE_DIR + ".tmp/partfile" +  dl_url.split("/")[-1]
    logfile = os.path.splitext(logfile)[0] + ".log"
    ytpid = 0
    lfile = open (logfile, "w")
    ytpid = subprocess.Popen((config.DOWNLOAD_DL,dl_url),universal_newlines=True,stdout=lfile).pid
    os.chdir(pwdcur)
    dlstatus = ""

    return dlstatus


def addPageRefresh():

    prhtml = '<script type="text/JavaScript" src="scripts/youtube.js">window.onload=beginrefresh</script>'
    prhtml += '\n<form name="refreshForm">'
    prhtml += '\n    <div class="searchform"><br><b>Refresh In :</b>'
    prhtml += '\n    <input type="text" name="visited" value="1" size="4" align="middle" />'
    prhtml += '\n    </div>'
    prhtml += '\n</form><br>'
    return prhtml


class YouTubeResource(FreevoResource):

    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        blxml = fv.formValue(form,"xml")
        if blxml :
            fdisplay = getXML()
            fv.res += fdisplay[0]
            return String( fv.res )

        fv.printHeader(_('YouTube'), 'styles/main.css',selected=_('YouTube'))

        yterrors = []
        if (not config.__dict__.has_key('YOUTUBE_DIR')):
            yterrors.append('Unable to Find YOUTUDE_DIR setting in local_conf.py')
            yterrors.append('Add YOUTUBE_DIR = "Directory to Save Downloads." to your local_conf.py')
            config.YOUTUBE_DIR = "MISSING"
        if (not config.__dict__.has_key('YOUTUBE_DL')):
            yterrors.append('Unable to Find YOUTUDE_DL setting in local_conf.py')
            yterrors.append('Add YOUTUBE_DL = "Path to youtube-dl script" to your local_conf.py')
            config.YOUTUBE_DL = "MISSING"
        if (not config.__dict__.has_key('DOWNLOAD_DL')):
            yterrors.append('Unable to Find DOWNLOAD_DL setting in local_conf.py')
            yterrors.append('Add DOWNLOAD_DL = "Path to downloadurl.py script" to your local_conf.py')
            config.DOWNLOAD_DL = "MISSING"

        if len(yterrors) > 0:
            fv.printMessages(yterrors)
            return String( fv.res )


        fldelete = fv.formValue(form,'Delete')
        if fldelete:
            filename = fv.formValue(form,'file')
            if filename:
                filename = config.YOUTUBE_DIR + filename
                if os.path.exists(filename):
                    os.remove(filename)
                    fv.res += "DELETED FILE - " + filename

        yturl = ""
        if not os.path.exists(config.YOUTUBE_DL):
            fv.res += '<br><br><br><b>Unable to locate youtube-dl script  "' + config.YOUTUBE_DL + '" </b><br>'
            fv.res += 'Download scripts from  <a href="http://www.arrakis.es/~rggi3/youtube-dl/">http://www.arrakis.es/~rggi3/youtube-dl/</a>'
            fv.res += '<br>Add YOUTUBE_DL = "path and file name to youtube_dl script"<br>'
        else:
            fv.res  += '\n<br><form id="YouTube Download" action="youtube.rpy" method="get">'
            fv.res  += '\n<div class="searchform"><br><b>Youtube URL :</b><input type="text" name="yt_url" size="40" value="' + yturl + '" />'
            fv.res  += '\n<input type="submit" value=" Download! " />'
            fv.res  += '\n</div>'
            fv.res  += '\n</form>'

            yturl = fv.formValue(form,'yt_url')
            if yturl :
                yt_status = str(download_youtube(yturl,""))
                refreshon = True

        if not os.path.exists(config.YOUTUBE_DIR):
            fv.res += '<br><b>Unable to locate youtube download location "' + config.YOUTUBE_DIR + '" </b><br>'
            fv.res += 'Add YOUTUBE_DIR = "download directory" to your local_conf.py'


        if os.path.exists(config.YOUTUBE_DIR):
            if not os.path.exists(config.YOUTUBE_DIR + ".tmp"):
                os.mkdir(config.YOUTUBE_DIR + ".tmp")

        dlurl = fv.formValue(form,'dl_url')
        if dlurl :
            dl_status = download_url(dlurl,"")
            fv.res += "<br>" + dl_status
            refreshon = True

        dlurl = ""
        fv.res  += '\n<form id="Url Download" action="youtube.rpy" method="get">'
        fv.res  += '\n    <div class="searchform"><br><b>Download URL :</b>'
        fv.res  += '\n       <input type="text" name="dl_url" size="40" value="' + dlurl + '" />'
        fv.res  += '\n       <input type="submit" value=" Download! " />'
        fv.res  += '\n    </div>'
        fv.res  += '\n</form><br>\n'

        fdisplay = displayfiles(fv)
        fv.res  +=  addPageRefresh()

        return String( fv.res )

resource = YouTubeResource()
