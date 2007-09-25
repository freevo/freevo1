#! /usr/bin/python
# -----------------------------------------------------------------------
# plugins.rpy - Show all plugins
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

import sys, time

from www.web_types import HTMLResource, FreevoResource
import util, config
import os 
from plugin import is_active
from helpers.plugins import parse_plugins
from helpers.plugins import info_html

TRUE = 1
FALSE = 0

def ReadFile(file,numberlines = 40):
#    print  "READING FILE = %s Number lines = %i"  % (  file , numberlines )
    lconf_hld = open(file,"r")
    retlines = lconf_hld.readlines()[numberlines * -1:]
    
    rlines = ""
    retlines.reverse()
    for ln in retlines:
        rlines += ln 
    
    return rlines

def CreateListBox(cname,grps,cvalue,opts):
    ctrl = '\n<select name="%s" value=""  id="%s" %s>' % ( cname , cname, opts )

    for grp in grps:
        if grp == cvalue:
            ctrl  += '\n    <option value="' + grp + '" selected="yes">' + grp + '</option>'
        else:
            ctrl  += '\n    <option value="' + grp + '">' + grp + '</option>'
    ctrl += '\n</select>'
    return ctrl

def GetLogFiles():
    filelist = os.listdir( config.LOGDIR)
    for l in filelist:
        if not l.endswith(".log"):
           filelist.remove(l)
    return filelist
 
def addPageRefresh():
    style = 'style="z-index:100; position:absolute; top:150px; a"'
    style = ""
    prhtml = '<script type="text/JavaScript">window.onload=beginrefresh</script>'
    prhtml += '\n<div class="searchform" id="refresh" %s  align="Center">Refresh In : ??</div>' % style
    return prhtml
 
   
class ViewLogFileResource(FreevoResource):

    def _render(self, request):

        fv = HTMLResource()
        form = request.args
        dfile = fv.formValue(form,"displayfile")
#        print "LOG FILE = %s " % dfile
        if not dfile:
            dfile = 'webserver-0.log'
            
        dfile = config.LOGDIR + "/" + dfile
        update = fv.formValue(form,"update")
        rows = fv.formValue(form,"rows")
#        print update
        if not rows:
            rows = '20'
        rows = int(rows)
        
        if update:
            fv.res = ReadFile(dfile,rows)
            return String( fv.res )           
           
        autorefresh = fv.formValue(form,"autorefresh")
        if not autorefresh:
            autorefresh = ""
        autorefresh = "checked"
        
        numlines = fv.formValue(form,"numlines")
        if not numlines:
            numlines = 20
            
        delayamount = fv.formValue(form,"delayamount")
        if not delayamount:
            delayamount = 9999
            
        fv.printHeader(_('viewlog'), 'styles/main.css','scripts/viewlogfile.js',selected=_('View Logs'))

        fv.res  += '\n<div class="searchform" align="left"><br>'
        fv.res  += '\n<div align="left">'
        fv.res  += '\n<form id="form1" name="form1" action="viewlogfile.rpy" method="get">'
        fv.res += '<br>'
 
        logfiles = GetLogFiles()
        opts = 'onchange="UpdateDisplay()"'
        fv.res +=  "Log File :  " + CreateListBox("logfile",logfiles,dfile,opts)
#        fv.res  += '<input type="submit" value="View File">'
        fv.res += '<input type="textbox" name="delayamount" id="delayamount" value="%s" size="3" onchange="UpdateDelay()"> Refresh Delay' % delayamount
        fv.res += '<input type="textbox" name="numlines" id="numlines" value="%s" size="3" onchange="UpdateDisplay()"> Number Lines' % numlines
#        fv.res += '<input type=checkbox name="autorefresh" id="autorefresh" %s> Auto Refresh' % autorefresh
        fv.res += addPageRefresh()
        fv.res += "</form>"
        
        style = 'style="z-index:100; left:1%; width: 95%; height: 50%; position:absolute; top:220px;  bottom:2%;  padding: 2px;"'
        fv.res +=  '<br><textarea  id="loglines" name="loglines" rows = %i cols=120 wrap="OFF" READONLY %s ></textarea>'  %  ( rows , style )
        
#        fv.res += '</form>'
        fv.res += '</div>\n'
        fv.res += '</div>\n'
        fv.res += '<br><br>'
        fv.printFooter()
 
        return String( fv.res )

resource = ViewLogFileResource()
