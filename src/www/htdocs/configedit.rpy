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
#
# &syntaxcheck=False - Disable Syntax Check on update.
# cmd=DISPLAYCONFIG - Loop throught config and display all config settings.
# local_conf.py  CONFIG_REALTIME_UPDATE = True , try to setting the var, if kinda sketchy on this one.
# 
#  Todo: FIX CONFIG file name STUFF.



import sys
import os
import os.path
import config
import string
import types
import time
import subprocess

import plugins 
from www.configlib import  *

from stat import *
from www.web_types import HTMLResource, FreevoResource


def LogTransaction(cmd, lineno, line):
    '''
    '''
    _debug_('LogTransaction(cmd=%r, lineno=%r, line=%r)' % ( cmd, lineno, line ), 2)
    if config.__dict__.has_key('FREEVO_LOGDIR'):
        logfile_directory = config.FREEVO_LOGDIR
    else:
        logfile_directory = config.LOGDIR

    log_filename = os.path.join(config.FREEVO_LOGDIR, 'webconfig-%s.log' % ( os.getuid()))

    logfile = open (log_filename, 'a')
    logtime = time.strftime('%Y-%m-%d %H:%M:%S')
    message = 'Line : %i  %s %s ' % ( lineno, cmd, line)
    mess =  logtime + " -- " + message
    logfile.write (mess)
    logfile.close


def WriteConfigFile(filename, conf):
    '''
    '''
    _debug_('WriteConfigFile(filename=%r, conf=%r)' % ( filename, conf ), 2)
    cfile = open(filename, 'w')
    for ln in conf:
        cfile.write(ln)
    cfile.close


def cmdCreateFXDFile(fxd_file, fxd_title, fxd_url):
    '''
    '''
    _debug_('cmdCreateFXDFile(xfd_file=%r, fxd_title=%r, fxd_url=%r)' % ( fxd_file, fxd_title, fxd_url ), 2)

    fxd_file_handle = open(fxd_file, 'w' )
    fxd_file_handle.write('<freevo>')
    fxd_file_handle.write('<title>%s</title>' % fxd_title)
    fxd_file_handle.write('<audio> ')
    fxd_file_handle.write('<mplayer_options></mplayer_options> ')
    fxd_file_handle.write('<url>%s</url>' % fxd_url)
    fxd_file_handle.write('</audio>')
    fxd_file_handle.write('<info> ')
    fxd_file_handle.write('<genre>Alternative</genre> ')
    fxd_file_handle.will('<desc></desc>')
    fxd_file_handle.write('</info> ')
    fxd_file_handle.write('</freevo> ')
    fxd_file_handle.close()

 

def cmdBrowseFiles(browse_dir,browse_area, setting_name,  browse_type =  'F', display_hidden = False):
    '''
    '''
    _debug_('cmdBrowseFiles(browse_dir=%r, browse_area=%r, setting_name=%r, browse_type=%r, dispay_hidden=%r)' % \
        ( browse_dir, browse_area, setting_name, browse_type, display_hidden ) , 2)

    print "Browing files !!!"
    browse_dir = browse_dir.strip("'")
    browse_dir = os.path.dirname(browse_dir)

    if not os.path.exists(browse_dir):
        browse_dir = '/'

    dir_list = os.listdir(browse_dir)
    dir_list.sort()

    file_list_ctrl = 'Current Directory : %s' % browse_dir
    file_list_ctrl += '<div class="filelist"><ul>'

    if browse_dir <> "/":
        parent_dir = os.path.split(browse_dir)[0]
        file_list_ctrl += '<li class="directory">'
        file_list_ctrl += '<a onclick=getFileList("%s","%s","%s","F")>..</a>' % (  browse_area , parent_dir, setting_name )
        file_list_ctrl += '</li>'

    for display_file in dir_list:
        show_file = True
        if display_file.startswith('.'):
            if not display_hidden:
                show_file = False

        full_file = os.path.join(browse_dir,display_file)
        cur_type = "F"
        if os.path.isdir(full_file):
            cur_type = "D"

        if show_file:
            if cur_type == "D":
                file_list_ctrl += '<li class="directory">'
                file_list_ctrl += '<a onclick=SelectFile("%s","%s")>' % (full_file, browse_area)
                file_list_ctrl += 'Select '
                file_list_ctrl += '</a>'
                file_list_ctrl += '<a onclick=getFileList("%s","%s/","%s","F")>' % ( browse_area, full_file, setting_name)
                file_list_ctrl += display_file
                file_list_ctrl += '</a>'
                file_list_ctrl += '</li>'

    if browse_type == 'F':
        for display_file in dir_list:
            show_file = True
            if display_file.startswith('.'):
                if not display_hidden:
                    show_file = False

            full_file = os.path.join(browse_dir,display_file)

            cur_type = "F"
            if os.path.isdir(full_file):
                cur_type = "D"

            if show_file:
                if cur_type <> "D":
                    file_list_ctrl += '<li class="file">'
                    js_onclick = 'onclick=SelectFile("%s","%s","%s")' % (full_file, browse_area, setting_name)
                    file_list_ctrl += '<a id="file" %s >%s' % (js_onclick, display_file )
                    file_list_ctrl += '</a>\n'
                    file_list_ctrl += '</li>'

    file_list_ctrl += '</div></ul>'
    return file_list_ctrl


def cmdCheckValue(varName, varValue):
    '''
    '''
    _debug_('cmdCheckValue(varName=%r, varValue=%r)' % (varName, varValue ) , 2)

    retClass = 'checkError'
    status = 'Error'
    blOK = False
    newline = varName + ' = ' + varValue + '\n'

    # Check the syntax of the new line.
    if CheckSyntax(newline):
        blOK = True
        retClass = 'checkOK'
        status = 'OK'

    if FileTypeVar(varName) and blOK:
        file_name = varValue.replace("'", '').strip()

        if os.path.exists(file_name):
            retClass = 'checkOK'
            status = 'OK'
        else:
            retClass='CheckWarning'
            status = 'Missing File'

    results = '<span class="%s">%s</span>' % (retClass, status)
    return blOK, results


def UpdateSetting(cfile, varName, varValue, varEnable, sline, eline, syntaxcheck):
    '''
    '''
    _debug_('UpdateSetting(cfile=%r, varName=%r, varValue=%r, varEnable=%r, sline=%r, eline=%r, syntaxcheck=%r)' % \
            (cfile, varName, varValue, varEnable, sline, eline, syntaxcheck), 2)

    llog ='Running Update on Name: %s On Lines : %i - %i' % (varName, sline, eline)
    LogTransaction(llog, 0, '')
    fconf = ReadConfig(cfile)

    blOK, results = cmdCheckValue(varName, varValue)
    newline = varName + ' = ' + varValue + '\n'

    if not blOK and varEnable == 'FALSE':
        status = 'Updated, Error if Enabled'

    if not syntaxcheck:
        blOK = True
        status = newline

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
            WriteConfigFile(cfile, fconf)
            results = '<span class="checkOK">Update Done - %s </span>' % newline
        

        else:
            LogTransaction('ERROR Line not UPDATED : ', sline, fconf[sline])
            results = 'Update Error'

    return results


def DeleteLines(cfile, startline, endline):
    '''
    '''
    _debug_('DeleteLines(cfile=%r, startline=%r, endline=%r)' % (cfile, startline, endline), 2)

    rconf = ReadConfig(cfile)
    dellines = '<ul>'

    for dline in range(startline, endline+1):
        rline = rconf.pop(startline)
        LogTransaction('DELETING LINE : ', dline, rline)
        rline = rline.replace('<', '&lt;')
        rline = rline.replace('>', '&gt;')
        dellines += '<li>%s</li>' % rline
    dellines += "</ul><br><br>"

    WriteConfigFile(cfile, rconf)
    return dellines

def GetItemsArray(cvalue):
    '''
    '''
    _debug_('GetItemsArray(cvalue=%r)' % (cvalue), 2)
    itemlist = None
    cmd = 'itemlist = ' + cvalue
    if CheckSyntax(cmd):
        exec cmd
    return itemlist


def FileTypeVarArray(cname):
    '''
    '''
    _debug_('FileTypeVarArray(cname=%r)' % ( cname ) ,2)

    filevars = ['VIDEO_ITEMS', 'AUDIO_ITEMS', 'IMAGE_ITEMS', 'GAME_ITEMS']

    if cname in filevars:
        return True
    return False


def FileTypeVar(cname):
    '''
    '''
    _debug_('FileTypeVar(cname=%r)' % (cname ), 2)

    vtype = cname.split('_')[-1]
    filetypes = ['PATH', 'DIR', 'FILE', 'DEV', 'DEVICE']
    filevars = ['XMLTV_GRABBER', 'RSS_AUDIO', 'RSS_VIDEO', 'RSS_FEEDS', 'XMLTV_SORT', 'LIRCRC']

    if vtype in filetypes:
        return True
    if cname in filevars:
        return True
    return False


def UpdatePlugin(cfile, pcmd, pname, pline, plugin_level, plugin_args):
    lconf = ReadConfig(cfile)

    # Check to see if a line exists all ready.
    status = 'ERROR'
    pline = int(pline)

    level = ''
    if plugin_level:
        level = ', level=' + plugin_level


    args = ''
    if plugin_args:
        args = ', args =' + plugin_args

    if pline == -1:
        lconf.append('')
        pline = len(lconf) - 1

    if pline <> -1:
        lcline = lconf[pline]

        if pcmd == 'Deactive':
            nline = "# plugin.activate('%s' %s) \n" % ( pname, level )

        elif pcmd == 'Removed':
            nline = "plugin.remove('%s')\n" % ( pname  )

        elif pcmd == 'Active':
            nline = "plugin.activate('%s' %s )\n" % ( pname, level )

        lconf[pline] = nline
        LogTransaction('Plugin Update', pline, nline)
        status = 'Plugin Line %i updated to %s ' % ( pline, nline )
        WriteConfigFile(cfile, lconf)

    return status

def UpdateServer(server_name, server_cmd):
    print '%s = %s' % ( server_name, server_cmd )

    run_cmd = ['freevo',server_name,server_cmd] 
    server_pid = subprocess.Popen(run_cmd).pid
    print 'SERVER PID = %r'  % server_pid

    time.sleep(3)

    server_line = Display_Server(server_name)
    return server_line

def StartHelper(helper):
    print 'STARTING HELPER !!! == %s' % helper

    run_cmd = ['freevo',helper] 
    helper_pid = subprocess.Popen(run_cmd).pid
    print 'SERVER PID = %r'  % helper_pid

    time.sleep(3)

    helper_line = Display_Helper(helper)
    return helper_line


class ConfigEditResource(FreevoResource):

    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        configfile = fv.formValue(form, 'configfile')
        configfile = '/home/dlocke/.freevo/local_conf.py'
        if configfile:
            if not os.path.exists(configfile):
                configfile = '/etc/freevo/local_conf.py'
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
        
        realtime_update = TRUE
        if config.__dict__.has_key('CONFIG_REALTIME_UPDATE'):
            realtime_update = config.CONFIG_REALTIME_UPDATE
   
        syntaxcheck = True
        if fv.formValue(form,'syntaxcheck') == 'FALSE':
            syntaxcheck = False
    
        browse_file = fv.formValue(form,'browsefile')
        browse_area = fv.formValue(form,'browsearea')
        setting_name = fv.formValue(form,'setting_name')

        # NEED TO MOVE ON CONFIG RELATED STUFF ABOVE THE FILE CHECK !!!
        if cmd == 'BROWSEDIRECTORY' and browse_file and browse_area:
            fv.res = cmdBrowseFiles(browse_file,browse_area,setting_name,'D')
            return str( fv.res )

        if cmd == 'BROWSEFILE' and browse_file and browse_area:
            fv.res = cmdBrowseFiles(browse_file,browse_area,setting_name)
            return str( fv.res )

        if not cmd:
            cmd = 'VIEW'

        if cmd == 'UPDATE':
            fv.res = UpdateSetting(configfile, udname, udvalue, udenable, int(startline), int(endline),syntaxcheck)
 
            if realtime_update:
                check_value =   '%s = %s' %   (udname, udvalue)
                if CheckSyntax(check_value) and udenable == 'TRUE':
                    actual_value = GetItemsArray(udvalue)
                    print 'Doing Live Update %s = %s ' % ( udname, udvalue )
                    config.__dict__[udname] = actual_value
                
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
            plugin_args = fv.formValue(form,'args')
            fv.res = UpdatePlugin(configfile, pluginaction, pluginname, pluginline, plugin_level,plugin_args)
            return String( fv.res )

        server_name = fv.formValue(form,'server_name')
        server_cmd = fv.formValue(form,'server_cmd')
        if cmd == 'SERVERUPDATE' and server_cmd and server_name:
            fv.res += UpdateServer(server_name, server_cmd)

        helper_name = fv.formValue(form,'helper_name')
        if cmd == 'STARTHELPER' and helper_name:
            fv.res += StartHelper(helper_name)

        return str( fv.res )

resource = ConfigEditResource()
