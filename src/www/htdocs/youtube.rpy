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
from stat import *

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
    fileStatus = {'percent': '-', 'downloaded': 'done' , 'filesize': 'done' ,'speed' : '--', 'eta' : '--:--'}
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
    filesXML = '<?xml version="1.0" encoding="ISO-8859-1" ?>'
    filesXML += '<FILELIST>'

    filelist = os.listdir(config.YOUTUBE_DIR)
    filelist.sort()
    for fl in filelist :
        fstat = os.stat(config.YOUTUBE_DIR + fl)[ST_MODE]
        isdir = S_ISDIR(fstat)
        if not isdir and fl != "folder.fxd" :
            # check for log file.
            filesXML += '<FILE id="' + fl + '">'
            filesXML += '<FILENAME>' + fl + '</FILENAME>'
            fstats = getStatus(fl)
            filesXML += xmlStatus(fstats)
            filesXML += '</FILE>'
    filesXML += "</FILELIST>"
    return filesXML

def displaytableheader(): 
    fvhtml = HTMLResource()

    fvhtml.tableOpen('class="library" id="filelist"')
    fvhtml.tableRowOpen('class="chanrow"')
    fvhtml.tableCell('Current Downloads','class ="guidehead"  colspan="2"')
    fvhtml.tableCell('% Done','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('Size','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('Speed','class ="guidehead"  colspan="1"')
    fvhtml.tableCell('ETA','class ="guidehead"  colspan="1"')
    fvhtml.tableRowClose()
    fvhtml.tableClose()
    return fvhtml.res

def CleanupLogFiles():
    logfiles = os.listdir(config.YOUTUBE_DIR + ".tmp/")
    for lfile in logfiles:
        # Check to see if the movie file exists.
        vfile = config.YOUTUBE_DIR + os.path.splitext(lfile)[0] + ".flv"
        if not os.path.exists(vfile):
            os.remove(config.YOUTUBE_DIR + ".tmp/" + lfile)

def startdownload(dlcommand,logfile):
    pwdcur = os.getcwd()
    os.chdir(config.YOUTUBE_DIR)
    lfile = open (logfile, "w")
    ytpid = subprocess.Popen(dlcommand,universal_newlines=True,stdout=lfile).pid
    os.chdir(pwdcur)

def download_youtube(yt_url):
    logfile = config.YOUTUBE_DIR + ".tmp/" +  yt_url.split("=")[-1] + ".log"
    startdownload((config.YOUTUBE_DL,"-t",yt_url),logfile)
   
def download_url(dl_url):

    # get the file name from the url.
    logfile = config.YOUTUBE_DIR + ".tmp/partfile" +  dl_url.split("/")[-1]
    logfile = os.path.splitext(logfile)[0] + ".log"
    startdownload((config.DOWNLOAD_DL,dl_url),logfile)
    
def addPageRefresh():
    prhtml = '<script type="text/JavaScript" src="scripts/youtube.js">window.onload=beginrefresh</script>'
    prhtml += '\n<div class="searchform" id="refresh">Refresh In : ??</div>'
    return prhtml

def envCheck():
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
    return yterrors

def doFlowPlayer(pfile):
    flash = '\n<br><br><script type="text/javascript" src="flowplayer/swfobject.js"></script>'
    flash += '\n<div align="center" id="flowplayerholder">'
    flash += '\nThis will be replaced by the player. '
    flash += '\n</div>'
    flash += '\n<script type="text/javascript">'
    flash += '\n// <![CDATA['
    flash += '\nvar fo = new SWFObject("flowplayer/FlowPlayerThermo.swf", "FlowPlayer", "468", "350", "7", "#ffffff", true);'
    flash += '\n// need this next line for local testing, its optional if your swf is on the same domain as your html page'
    flash += '\nfo.addParam("allowScriptAccess", "always");'
    flash += '\nfo.addVariable("config", "{ showPlayListButtons: true, playList: [ {overlayId: \'play\' },'
    flash += ' { url: \'http://archserve/youtube/'+ pfile + '\' } ], initialScale: \'fit\' }");'
    flash += '\nfo.write("flowplayerholder");'
    flash += '\n// ]]>'
    flash += '\n</script>'
    return flash

class YouTubeResource(FreevoResource):

    def _render(self, request):
       fv = HTMLResource()
       form = request.args

       blxml = fv.formValue(form,"xml")
       if blxml :
            fv.res = getXML()
            #fv.res += fdisplay[0]
            return String( fv.res )     

       fv.printHeader(_('YouTube'), 'styles/main.css',selected=_('YouTube'))       
       yterrors = envCheck() 
 
       playfile = fv.formValue(form,"playfile")
       if playfile:
           fv.res += doFlowPlayer(playfile)

       if config.YOUTUBE_DIR == "MISSING"  or ((config.YOUTUBE_DL == "MISSING") and (config.DOWNLOAD_DL ==  "MISSING")):
           fv.printMessages(yterrors)
           return String( fv.res )
       
       if not os.path.exists(config.YOUTUBE_DIR):
           fv.res += '<br><b>Unable to locate youtube download location "' + config.YOUTUBE_DIR + '" </b><br>' 
           fv.res += 'Add YOUTUBE_DIR = "download directory" to your local_conf.py'

       if not os.path.exists(config.YOUTUBE_DL):
           fv.res += '<br><br><br><b>Unable to locate youtube-dl script  "' + config.YOUTUBE_DL + '" </b><br>' 
           fv.res += 'Download scripts from  <a href="http://www.arrakis.es/~rggi3/youtube-dl/">http://www.arrakis.es/~rggi3/youtube-dl/</a>'
           fv.res += '<br>Add YOUTUBE_DL = "path and file name to youtube_dl script"<br>'

       if not os.path.exists(config.DOWNLOAD_DL):
           fv.res += '<br><b>Unable to locate downloadurl.py script  "' + config.YOUTUBE_DL + '" </b><br>' 
           fv.res += 'Download scripts from  <a href="http://www.arrakis.es/~rggi3/youtube-dl/">http://www.arrakis.es/~rggi3/youtube-dl/</a>'
           fv.res += '<br>Add YOUTUBE_DL = "path and file name to youtube_dl script"<br><br>'

       if os.path.exists(config.YOUTUBE_DIR):
           if not os.path.exists(config.YOUTUBE_DIR + ".tmp"):
               os.mkdir(config.YOUTUBE_DIR + ".tmp")

       fldelete = fv.formValue(form,'Delete')
       if fldelete:
            filename = fv.formValue(form,'file') 
            if filename:
                filename = config.YOUTUBE_DIR + filename
                if os.path.exists(filename):
                       os.remove(filename)
                       fv.res += "DELETED FILE - " + filename 

       dlurl = ""
       fv.res  += '\n<br><form id="Url Download" action="youtube.rpy" method="get">'
       fv.res  += '\n    <div class="searchform"><br><b>Download URL :</b>'
       fv.res  += '\n       <input type="text" name="dl_url" size="40" value="' + dlurl + '" />'
       fv.res  += '\n       <select name="dlscript" value="downloadurl">'
       fv.res  += '\n           <option value="youtube">Youtube</option>'
       fv.res  += '\n           <option value="downloadurl">Donwload Url</option>'
       fv.res  += '\        </select>'
       fv.res  += '\n       <input type="submit" value=" Download! " />'
       fv.res  += '\n    </div>'
       fv.res  += '\n</form><br>\n'

       dltype = fv.formValue(form,'dlscript')
       dlurl = fv.formValue(form,'dl_url')
       if dltype and dlurl:
           if dltype == "youtube":
             download_youtube(dlurl)
           if dltype == "downloadurl":
             download_url(dlurl)

       fv.res  += displaytableheader()       
       fv.res  +=  addPageRefresh()

#       fv.res += '<object width="425" height="350"><param name="movie" value="http://www.youtube.com/v/grCTXGW3sxQ"></param><param name="wmode" value="transparent"></param><embed src="http://www.youtube.com/v/grCTXGW3sxQ" type="application/x-shockwave-flash" wmode="transparent" width="425" height="350"></embed></object>'

       return String( fv.res )

resource = YouTubeResource()

