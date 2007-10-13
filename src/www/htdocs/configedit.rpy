# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
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
import os.path
import config
import string
import types
import time
from www.web_types import HTMLResource, FreevoResource


def LogTransaction(cmd, lineno, line):
    logfile = open (os.path.join(config.FREEVO_LOGDIR, 'webconfig.log'), 'a')
    logtime = time.strftime('%Y-%m-%d %H:%M:%S')
    message = 'Line : %i  %s %s ' % ( lineno, cmd, line)
    mess =  logtime + " -- " + message
    logfile.write (mess)
    logfile.close


def ReadConfig(cfile):
    lconf = cfile
    lconf_hld = open(lconf, 'r')
    fconf = lconf_hld.readlines()
    return fconf


def WriteConfigFile(filename, conf):
    cfile = open(filename, 'w')
    for ln in conf:
        cfile.write(ln)
    cfile.close


def cmdCheckValue(varName, varValue):
    retClass = 'UpdateError'
    status = 'Error !'
    blOK = False
    newline = varName + ' = ' + varValue + '\n'

    # Check the syntax of the new line.
    if CheckSyntax(newline):
        blOK = True
        retClass = 'UpdateOK'
        status = 'OK'

    if FileTypeVar(varName) and blOK:
        if os.path.exists(varValue):
            retClass='UpdateWarning'
            status = 'Missing File'
        else:
            retClass = 'UpdateOK'
            status = 'OK'

    results = '<span class="%s">%s</span>' % (retClass, status)
    return blOK, results


def UpdateSetting(cfile, varName, varValue, varEnable, sline, eline):
    llog ='Running Update on Name: %s On Lines : %i - %i' % (varName, sline, eline)
    LogTransaction(llog, 0, '')
    fconf = ReadConfig(cfile)

    blOK, results = cmdCheckValue(varName, varValue)
    newline = varName + ' = ' + varValue + '\n'

    if not blOK and varEnable == 'FALSE':
        status = 'Updated, Error if Enabled'

    if varEnable == 'FALSE':
        newline = '# ' + newline

    if newline == fconf[sline]:
        LogTransaction('Lines the Same no change :', sline, newline)

    else:
        reload = False
        LogTransaction('Line update FROM : ', sline, fconf[sline])

        for dline in range(sline, eline+1):
            rline = fconf.pop(sline)
            status = 'RELOAD PAGE'
            LogTransaction('DELETING LINE : ', dline, rline)

        fconf.insert(sline, newline)
        LogTransaction('Line update TO : ', sline, fconf[sline])

        if blOK:
            LogTransaction('Line update TO : ', sline, fconf[sline])
            WriteConfigFile(config.CONFIG_EDIT_FILE, fconf)
            results = '<span class="UpdateOK">Update Done - %s </span>' % newline
        else:
            LogTransaction('ERROR Line not UPDATED : ', sline, fconf[sline])
            results = 'Update Error'

    return results


def DeleteLines(cfile, startline, endline):
    rconf = ReadConfig(cfile)
    dellines = '<ul>'

    for dline in range(startline, endline+1):
        rline = rconf.pop(startline)
        LogTransaction('DELETING LINE : ', dline, rline)
        rline = rline.replace('<', '&lt;')
        rline = rline.replace('>', '&gt;')
        dellines += '<li>%s</li>' % rline
    dellines += "</ul><br><br>"

    WriteConfigFile(config.CONFIG_EDIT_FILE, rconf)
    return dellines


def CheckSyntax(fvsetting):
    status = False
    try :
        exec fvsetting
        status = True
    except :
        status = False
    return status


def FileTypeVarArray(cname):
    filevars = ['VIDEO_ITEMS', 'AUDIO_ITEMS', 'IMAGE_ITEMS', 'GAME_ITEMS']

    if cname in filevars:
        return True
    return False


def FileTypeVar(cname):
    vtype = cname.split('_')[-1]
    filetypes = ['PATH', 'DIR', 'FILE', 'DEV', 'DEVICE']
    filevars = ['XMLTV_GRABBER', 'RSS_AUDIO', 'RSS_VIDEO', 'RSS_FEEDS', 'XMLTV_SORT', 'LIRCRC']

    if vtype in filetypes:
        return True
    if cname in filevars:
        return True
    return False


def UpdatePlugin(cfile, pcmd, pname, pline, plugin_level):
    lconf = ReadConfig(cfile)

    # Check to see if a line exists all ready.
    status = 'ERROR'
    pline = int(pline)

    level = ''
    if plugin_level:
        level = ', level=' + plugin_level

    if pline == -1:
        lconf.append('')
        pline = len(lconf) - 1

    if pline <> -1:
        lcline = lconf[pline]

        if pcmd == 'Deactive':
            nline = "# plugin.activate('%s' %s) \n" % ( pname, level )

        elif pcmd == 'Remove':
            nline = "plugin.remove('%s')\n" % ( pname  )

        elif pcmd == 'Active':
            nline = "plugin.activate('%s' %s )\n" % ( pname, level )

        lconf[pline] = nline
        LogTransaction('Plugin Update', pline, nline)
        status = 'Plugin Line %i updated to %s ' % ( pline, nline )
        WriteConfigFile(cfile, lconf)

    return status


class ConfigEditResource(FreevoResource):

    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        configfile = fv.formValue(form, 'configfile')
        if configfile:
            if not os.path.exists(configfile):
                configfile = None
        if not configfile:
            if (not config.__dict__.has_key('CONFIG_EDIT_FILE')):
                fv.printMessages(['Unable to find local_conf.py setting CONFIG_EDIT_FILE'])
                return String ( fv.res )
            else:
                configfile = config.CONFIG_EDIT_FILE

        if not os.path.exists(configfile):
            fv.res += 'Error'
            return String ( fv.res )

        cmd = fv.formValue(form, 'cmd')
        udname = fv.formValue(form, 'udname')
        udenable = fv.formValue(form, 'udenable')
        udvalue = fv.formValue(form, 'udvalue')
        startline = fv.formValue(form, 'startline')
        endline = fv.formValue(form, 'endline')
        pluginaction = fv.formValue(form, 'pluginaction')
        pluginname = fv.formValue(form, 'pluginname')
        pluginline = fv.formValue(form, 'pluginline')

        if not cmd:
            cmd = 'VIEW'

        if cmd == 'UPDATE':
            fv.res = UpdateSetting(configfile, udname, udvalue, udenable, int(startline), int(endline))
            return String( fv.res )

        if cmd == 'CHECK' and udname and udvalue:
            ok, results = cmdCheckValue(udname, udvalue)
            fv.res = results
            return String ( fv.res )

        if cmd == 'CHECKFILE' and udvalue:
            if os.path.exists(udvalue):
                fv.res = ''
            else:
                fv.res = 'Missing File - ' + udvalue
            return String ( fv.res )

        if cmd == 'DELETE' and startline and endline:
            dlines = DeleteLines(configfile, int(startline), int(endline))
            fv.res += '<br><h4>The following Lines were deleted (RERESH REQUIRED !!) :</h4>' + dlines

        if cmd == 'PLUGINUPDATE' and pluginname and pluginline and pluginaction:
            plugin_level = fv.formValue(form, 'level')
            fv.res = UpdatePlugin(configfile, pluginaction, pluginname, pluginline, plugin_level)
            return String( fv.res )

        return String( fv.res )

resource = ConfigEditResource()
