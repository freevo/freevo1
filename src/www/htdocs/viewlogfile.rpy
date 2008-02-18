# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to show all plugins
# -----------------------------------------------------------------------
# $Id$
#
# Notes: viewlogfile.rpy args : displayfile="logfile to display" eg
#
# Todo: Update file list when updating the log viewer.
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
import os

from www.web_types import HTMLResource, FreevoResource
import util, config

TRUE = 1
FALSE = 0


def ReadFile(file, number_lines = 40):
    lconf_hld = open(file, 'r')
    retlines = lconf_hld.readlines()[number_lines * -1:]

    rlines = ''
    retlines.reverse()
    for ln in retlines:
        rlines += ln

    return rlines


def CreateListBox(cname, grps, cvalue, opts):
    ctrl = '\n<select name="%s" value=""  id="%s" %s>' % (cname, cname, opts)

    for grp in grps:
        if grp == cvalue:
            ctrl  += '\n    <option value="' + grp + '" selected="yes">' + grp + '</option>'
        else:
            ctrl  += '\n    <option value="' + grp + '">' + grp + '</option>'
    ctrl += '\n</select>'
    return ctrl


def GetLogFiles(logfile_directory):
    filelist = os.listdir(logfile_directory)
    for l in filelist:
        if not l.endswith('.log'):
            filelist.remove(l)

    filelist.sort()
    return filelist


def addPageRefresh():
    prhtml = '<script type="text/JavaScript">window.onload=beginrefresh</script>'
    prhtml += '\n<span class="refresh" id="refresh"  align="Center">Refresh In : ??</span>'
    return prhtml


class ViewLogFileResource(FreevoResource):

    def _render(self, request):

        fv = HTMLResource()
        form = request.args
        dfile = fv.formValue(form, 'displayfile')

        if not dfile:
            if config.__dict__.has_key('VIEWLOG_FILE'):
                dfile = config.VIEWLOG_FILE
            else:
                dfile = 'webserver-0.log'
        else:
            config.VIEWLOG_FILE = dfile

        if config.__dict__.has_key('FREEVO_LOGDIR'):
            logfile_directory = config.FREEVO_LOGDIR
        else:
            logfile_directory = config.LOGDIR

        full_file_name = os.path.join(logfile_directory, dfile)
        update = fv.formValue(form, 'update')

        rows = fv.formValue(form, 'rows')
        if not rows:
            if config.__dict__.has_key('VIEWLOG_ROWS'):
                rows = config.VIEWLOG_ROWS
            else:
                rows = '20'
        else:
            config.VIEWLOG_ROWS = rows
        rows = int(rows)

        delayamount = fv.formValue(form, 'delayamount')
        print "Delay Amount = %r " % delayamount
        if not delayamount:
            if config.__dict__.has_key('VIEWLOGS_DELAY'):
                delayamount = config.VIEWLOGS_DELAY
            else:
                delayamount = 9999
        else:
            config.VIEWLOG_DELAY = delayamount

        if update:
            fv.res = ReadFile(full_file_name, rows)
            return String(fv.res)

        fv.printHeader(_('viewlog'), 'styles/main.css', 'scripts/viewlogfile.js', selected=_('View Logs'))

        fv.res += '\n<link rel="stylesheet" href="styles/viewlogfile.css" type="text/css" />\n'
        fv.res  += '\n<br><div class="viewlog">'
        fv.res  += '\n<form id="viewlog_form" name="viewlog_form" action="viewlogfile.rpy" method="get">'
        fv.res += '<br>'

        logfiles = GetLogFiles(logfile_directory)
        js_update = 'onchange=UpdateDisplay()'

        fv.res +=  'Log File :  ' + CreateListBox('logfile', logfiles, dfile, js_update)
        fv.res  += '<input type="Button" value="Refresh" onclick=%s >' % js_update
        js_delay = 'onchange = "UpdateDelay()"'
        txt_name = '"delayamount"'
        txt_ctrl = '<input type="textbox" name=%s id=%s value="%s" size="3" %s >'
        fv.res += txt_ctrl % (txt_name, txt_name, delayamount, js_delay)
        fv.res += ' Refresh Delay '

        fv.res += txt_ctrl % ("rows", "rows", rows, js_update)
        fv.res += 'Rows'
        fv.res += addPageRefresh()
        fv.res += "</form>"

        ta_name = '"loglines"'
        fv.res +=  '<textarea  id=%s name=%s  wrap="OFF" READONLY ></textarea>' % (ta_name, ta_name)
        fv.res += '</div>\n'

        fv.printFooter()
        return String(fv.res)

resource = ViewLogFileResource()
