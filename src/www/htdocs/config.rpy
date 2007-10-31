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

# Displays a webpages to allow the user to edit settings in the local_conf.py  !
#
# config.rpy?expAll=True - Will Expand all the settings.
# config.rpy?expAll=True#SETTINGNAME - Will got directly to a setting.
# config.rpy?configfile=/etc/freevo/local_conf.py - Open other config file.
#
# Required configedit.rpy - To write the settings to the local_conf.py
#
# Todo : Fix headlines with ? and & messing with url  !!
#            Fix File Items stuff and the '  single quote, and display update button on edit.

import sys
import os.path
import string
import types
import time
import urllib
import operator
from www.web_types import HTMLResource, FreevoResource
#from helpers.convert_config import change, change_map

from configlib import * 
import config
import util

def ParseConfigFile(rconf):
    '''
    '''
    _debug_('ParseConfigFile(rconf=%r)' % (rconf), 2)
    cnt = 0
    fconfig = []
    while cnt < len(rconf):
        startline = cnt
        ln = rconf[cnt]
        if ln.find('[') <> -1:
            if ln.find(']') <> -1:
                fln = ln
            else:
                fln = ln
                while ln.find(']') == -1:
                    cnt += 1
                    ln = rconf[cnt]
                    ln = ln.strip('#')
                    ln = ln.strip()
                    fln += ln

        elif ln.find('{') <> -1:
            if ln.find('}') <> -1:
                fln = ln
            else:
                fln = ln
                while ln.find('}') == -1:
                    cnt += 1
                    ln = rconf[cnt]
                    ln = ln.strip('#')
                    ln = ln.split('#')[0]
                    ln = ln.strip()
                    fln += ln
                fln = fln.replace('\n', '')
        else:
            fln = ln

        if  len(fln.split("=")) > 1:
            pln = ParseLine(fln)

            if pln['type']:
                pln['startline'] = startline
                pln['endline'] = cnt
                pln['control_name'] = pln['ctrlname'] + '_' + str(startline)
                fconfig.append(pln)
        cnt += 1

    fconfig.sort(key=operator.itemgetter('control_name'))
    return fconfig

    
def ParseLine(cline):
    '''
    '''
    _debug_('ParseLine(cline=%r)' % (cline), 2)
    lparsed = {'ctrlname': '',
               'ctrlvalue': '',
               'checked': True,
               'type' : '',
               'comments' : '',
               'group' :'',
               'startline':'',
               'endline':'',
               'fileline':cline,
               'control_name':'',
               'vartype':''
    }

    tln = cline.strip()
    tln = tln.replace('\n', '')

    if tln.startswith('#'):
        lparsed['checked'] = False
        tln = tln.lstrip('#')
        tln = tln.lstrip()

    fsplit = tln.split('=')
    lparsed['type'] = 'textbox'
    lparsed['ctrlname'] = fsplit[0].strip()
    lparsed['group'] = GetVarGroup(lparsed['ctrlname'])


    if not lparsed['ctrlname'].isupper():
        lparsed['type'] = ''

    if lparsed['group'] == 'KeyMap':
        lparsed['type'] = 'keymap'

    if (not config.__dict__.has_key(lparsed['ctrlname'])):
        try:
            fvvalue = eval('config.' + lparsed['ctrlname'])
        except Exception, e:
            fvvalue = ''

    ctrlvalue = fsplit[1].split('#')
    if len(ctrlvalue) == 2:
        lparsed['comments'] = ctrlvalue[1]

    lparsed['ctrlvalue'] = Unicode(ctrlvalue[0].strip())
    lparsed['vartype'] = VarType(lparsed['ctrlname'], lparsed['ctrlvalue'])
    lparsed['ctrlvalue'] = lparsed['ctrlvalue'].replace('"', "'")

    if lparsed['ctrlname'].startswith('"'):
        lparsed['type'] = ''
    return lparsed


def GetVarGroup(setting_name):
    '''
    '''
    _debug_('GetVarGroup(setting_name=%r)' % (setting_name), 2)

    group = setting_name.split('_')[0].capitalize()
    if setting_name.startswith('KEYMAP'):
        group = 'KeyMap'

    if setting_name.endswith('_VOLUME'):
        group = 'Volume'

    return group


def GetItemsArray(cvalue):
    '''
    '''
    _debug_('GetItemsArray(cvalue=%r)' % (cvalue), 2)
    itemlist = None
    cmd = 'itemlist = ' + cvalue
    if CheckSyntax(cmd):
        exec cmd
    return itemlist


def GetGroupList(cfgvars):
    '''
    '''
    _debug_('GetGroupList(cfgvars=%r)' % (cfgvars), 2)
    grps = ['Other','KeyMap']
    agrps = []
    for vrs in cfgvars:
        grp = vrs['group']
        agrps.append(grp)
        if not grp in grps:
            grps.append(grp)

    for vrs in cfgvars:
        ngrp = agrps.count(vrs['group'])
        if ngrp == 1:
            grps.remove(vrs['group'])
            vrs['group'] = 'Other'

    grps.sort()
    return grps


def getCtrlType(cname, cvalue, vtype):
    '''
    '''
    _debug_('getCtrlType(cname=%r, cvalue=%r, vtype=%r)' % (cname, cvalue, vtype), 2)
    if vtype == 'boolean':
        return 'boolean'
    if cname == 'TV_CHANNELS':
        return 'tv_channels'

    if cname.startswith('KEYMAP'):
        return 'keymap'

    if FileTypeVarArray(cname):
        return 'fileitemlist'
    if cvalue.startswith('{'):
        return 'itemlist'
    if cvalue.startswith('['):
        return 'itemlist'
    if vtype == 'list':
        return 'itemlist'
    return 'textbox'


def isNumber(s):
    '''
    '''
    _debug_('isNumber(s=%r) % (s)', 2)
    try:
        i = int(s)
        return True
    except ValueError:
        return False


def FileTypeVarArray(cname):
    '''
    '''
    _debug_('FileTypeVarArray(cname=%r)' % (cname), 2)
    filevars = ['VIDEO_ITEMS', 'AUDIO_ITEMS', 'IMAGE_ITEMS', 'GAME_ITEMS']

    if cname in filevars:
        return True
    return False


def DirTypeVar(cname):
    '''
    '''
    _debug_('FileTypeVar(cname)', 2)
    vtype = cname.split('_')[-1]
    print cname
    filetypes = ['DIR']
    filevars = ['RSS_AUDIO', 'RSS_VIDEO', 'RSS_FEEDS', 'FREEVO_LOGDIR']

    if cname.endswith('DIR'):
        return True
    if cname in filevars:
        return True
    return False


def FileTypeVar(cname):
    '''
    '''
    _debug_('FileTypeVar(cname)', 2)
    vtype = cname.split('_')[-1]
    filetypes = ['PATH', 'DIR', 'FILE', 'DEVICE', 'CMD']
    filevars = ['XMLTV_GRABBER', 'RSS_AUDIO', 'RSS_VIDEO', 'RSS_FEEDS', 'XMLTV_SORT', 'LIRCRC']

    if vtype in filetypes:
        return True
    if cname in filevars:
        return True
    return False


def VarType(setting_name, cvalue):
    '''
    '''
    _debug_('VarType(cvalue)', 2)
    if setting_name == "TV_CHANNELS":
        return 'tv_channels'

    if setting_name.startswith('KEYMAP'):
        return 'keymap'

    if setting_name == 'RADIO_STATIONS':
        return 'tv_channels'

    if FileTypeVarArray(setting_name):
        return 'filelist'

    if setting_name == 'IMAGEVIEWER_ASPECT':
        return 'string'

    if cvalue.startswith("'") and cvalue.endswith("'"):
        return 'string'
    if isNumber(cvalue):
        return "number"
    if cvalue.startswith('[') and cvalue.endswith(']'):
        return "list"
    if cvalue.startswith('(') and cvalue.endswith(')'):
        return "list"
    if cvalue.startswith('{') and cvalue.endswith('}'):
        return "dictionary"
    if cvalue.startswith('True') or cvalue.startswith('False'):
        return 'boolean'
    return 'Unknow'


def CreateFileBrowseControl(cname,setting_name):
    '''
    '''
    _debug_('CreateFileBrowseControl(cname, setting_name)', 2)

    if DirTypeVar(setting_name) or FileTypeVarArray(setting_name) :
        js_browsefiles = 'onclick=BrowseFiles("%s","%s","D")' % ( cname , setting_name )
    else:
        js_browsefiles = 'onclick=BrowseFiles("%s","%s","F")' % ( cname , setting_name )

    btn_browse_id = '%s_browse' % cname
    btn_browse = '<input type="button" id="%s" value="Browse" %s>' % ( btn_browse_id, js_browsefiles )
    js_cancel = 'onclick=CancelBrowse("%s")' % cname
    btn_cancel_id = '%s_cancel' % cname
    style = 'display:none'
    cancel_button = '<input type="button" value="Cancel" id="%s" %s style=%s>' % (btn_cancel_id , js_cancel, style)
    browse_area = '<div id="%s_filebrowse" class="file_browse" style=%s></div>' % ( cname, style )
    file_browse_control = btn_browse + cancel_button + browse_area
    return file_browse_control


def CreateTV_Channels_ctrl(cname, cvalue):
    '''
    '''
    _debug_('CreateTV_Channels_ctrl(cname, cvalue)', 2)
    vitems = GetItemsArray(cvalue)
    ctrl = ''

    if vitems:
        for r, e in enumerate(vitems):
            ctrl += '<li class="TV_Channels_Line">'
            js_moveup = 'onclick=MoveTVChannel("%s",%i,%i)' % (cname, r, -11 )
            ctrl += CreateHTMLinput('button','','Up','10', js_moveup)

            control_id = '%s_item%i' % ( cname, r )
            tv_line = unicode(str(e))
            html_textbox = CreateHTMLinput('textbox', control_id, tv_line, '30',  '' )
            ctrl += html_textbox

            if r <>  (len(vitems) -1):
                js_movedown = 'onclick=MoveTVChannel("%s",%i,%i)' % (cname, r, 1 )
                ctrl += CreateHTMLinput('button','','Down','10', js_movedown )

            ctrl += '</li>\n'
    ctrl += '</span>'
    return ctrl


def CreateFileItemList(cname, cvalue,setting_name):
    '''
    '''
    _debug_('CreateFileItemList(cname, cvalue, cenabled), setting_name)', 2)
    vitems = GetItemsArray(cvalue)
    ctrl = ''

    maxcols = 1
    if vitems:
        txtops = ''
        for r, e in enumerate(vitems):
            filecheck = ''
            chkClass = ''

            ctrl += '<li class="Setting_Controls">'

            if type(e) == types.StringType or type(e) ==  types.IntType:
                control_id = '%s_label%i' % ( cname, r)
                html_input = CreateHTMLinput('textbox', control_id, e, '', '' )
                browse_file_ctrl = CreateFileBrowseControl(control_id,setting_name)

                ctrl += html_input
                if not os.path.exists(e):
                    filecheck = 'Missing File'
                    chkClass = 'CheckWarning'

            else:
                js_onchange = 'onchange=CheckValue("%s","fileitemlist","%i")' % (cname, r)
                label_ctrl_id = '%s_label%i' % ( cname, r )
                label_ctrl = CreateHTMLinput('textbox', label_ctrl_id, e[0], '', '')

                dir_ctrl_id = '%s_file%i' % ( cname, r )
                dir_ctrl = CreateHTMLinput('textbox', dir_ctrl_id, e[1], '', js_onchange )
                browse_file_ctrl = CreateFileBrowseControl(dir_ctrl_id,setting_name)

                ctrl += label_ctrl
                ctrl += dir_ctrl

                if not os.path.exists(e[1]):
                    filecheck = 'Missing File'
                    chkClass = 'CheckWarning'

            span_id = '%s_check_%i' % ( cname, r )
            ctrl += browse_file_ctrl
            ctrl += '<span class="%s" id="%s">%s</span>' % ( chkClass, span_id, filecheck)
            ctrl += '</li>'

        r += 1;

        ctrl += '<li class="Setting_Controls">'
        js_onchange = 'onchange=CheckValue("%s","fileitemlist","%i")' % (cname, r)
        label_ctrl_id = '%s_label%i' % ( cname, r )
        ctrl += CreateHTMLinput('textbox', label_ctrl_id, '', '', '')

        dir_ctrl_id = '%s_file%i' % ( cname, r )
        ctrl += CreateHTMLinput('textbox', dir_ctrl_id, '', '', js_onchange )
        ctrl += '<span class="" id="%s_check_%i"></span' % (cname, r)
        ctrl += '</li>'

    ctrl += '</span>\n'
    return ctrl


def CreateDictionaryControl(cname, cvalue):
    '''
    '''
    _debug_('CreateDictionaryControl(cname=%r, cvalue=%r)' % (cname, cvalue), 2)
    ctrl2type = 'textbox'
    if cname.startswith('WWW_USERS'):
        ctrl2type = 'password'

    vitems = GetItemsArray(cvalue)
    ctrl = '<ul class="ItemList">'

    if vitems:
        for r, e in enumerate(vitems):
            pword =  vitems[e]
            ctrl += '<li class="Setting_Controls">'

            label_ctrl_id = '%s_item%i%i' % ( cname, r, 0 )
            ctrl += CreateHTMLinput('textbox', label_ctrl_id, e, '15', '')

            value_ctrl_id = '%s_item%i%i' % ( cname, r , 1 )
            ctrl += CreateHTMLinput(ctrl2type, value_ctrl_id, vitems[e], '15', '')
            ctrl += '</li>\n'

        ctrl += '<li class="Setting_Controls">'
        label_ctrl_id = '%s_item%i%i' % ( cname, r+1, 0 )
        ctrl += CreateHTMLinput('textbox', label_ctrl_id, '', '15', '')

        value_ctrl_id = '%s_item%i%i' % ( cname, r+1 , 1 )
        ctrl += CreateHTMLinput(ctrl2type, value_ctrl_id, '', '15', '')
        ctrl += '</li>\n'
        ctrl += '</ul>\n'

    return ctrl


def CreateListControl(cname, cvalue):
    '''
    '''
    _debug_('CreateListControl(cname=%r, cvalue=%r )' % (cname, cvalue ), 2)

    ctrl = '<ul class="ItemList">\n'
    vitems = GetItemsArray(cvalue)
    maxcols = 1
    if vitems:
        txtops = ''

        for r, e in enumerate(vitems):
            vtype = type(e)
            js_onchange = 'onchange=CheckValue("%s","itemlist","%i")' % (cname, r)

            if vtype == types.StringType or vtype == types.FloatType or vtype == types.IntType:

                html_textbox_id = '%s_item%i%i' % ( cname, r, 0 )
                html_textbox = CreateHTMLinput('textbox', html_textbox_id, e, '15', js_onchange)
                ctrl_line = html_textbox

            else:
                cols = 0
                ctrl_line = ''
                for c, e2 in enumerate(e):
                    cols += 1;
                    html_textbox_id = '%s_item%i%i' % ( cname, r, c )
                    html_textbox = CreateHTMLinput('textbox', html_textbox_id, e2, '15', js_onchange)
                    ctrl_line += html_textbox

                maxcols = max(cols,maxcols)

            ctrl += '<li class="Setting_Controls">'
            ctrl += ctrl_line
            ctrl += '</li>\n'

        if not cvalue.strip().startswith('('):
            ctrl += '<li class="Setting_Controls">\n'
            r+= 1;
            js_onchange = 'onchange=CheckValue("%s","itemlist","%i")' % (cname, r)
            for c in range(0, maxcols):
                html_textbox_id = '%s_item%i%i' % ( cname, r, c )
                html_textbox = CreateHTMLinput('textbox', html_textbox_id, '', '15', js_onchange)
                ctrl += html_textbox
            ctrl += '</li>\n'

        ctrl += '</ul>\n'
        return ctrl

    ctrl = CreateTextArea(cname, cvalue)
    return ctrl


def CreateTextArea(cname, cvalue):
    '''
    '''
    _debug_('CreateTextArea(cname, cvalue)', 2)
    elemsep = ')'
    rows = cvalue.count(elemsep) + 1
    if rows > 5:
        rows = 5
    cvalue = cvalue.replace(elemsep, elemsep + "\n")
    js_onchange = 'onchange=CheckValue("%s","textbox",0)' % cname

    ctrl = '<textarea id= "%s" rows="%i" cols="35" wrap="SOFT" %s>'  % (cname, rows, js_onchange)
    ctrl += cvalue
    ctrl += '</textarea>'
    return ctrl


def CreateTextBox(cname, setting_name, cvalue, vtype, plugin_group):
    '''
    '''
    _debug_('CreateTextBox(cname, cvalue, vtype, plugin_group, cenabled)', 2)
    cvalue = cvalue.strip()

    ctrl = ""
    js_onchange = 'onchange=CheckValue("%s","textbox",0)' % cname
    if vtype == 'number':
        control_id = cname
        ctrl = '<span class="VarInputInt">'
        ctrl += CreateHTMLinput('textbox', control_id, cvalue, '50', js_onchange)
        ctrl += '</span>'
        return ctrl

    html_input = CreateHTMLinput('textbox', cname, cvalue, '50', js_onchange)
    ctrl += html_input

    if FileTypeVar(setting_name) or DirTypeVar(setting_name):
        browse_file_control = CreateFileBrowseControl(cname,setting_name)
        ctrl += browse_file_control

    return ctrl


def KeyMapControl(cname, setting_name, cvalue, vtype, plugin_group):
    '''
    '''
    _debug_('KeyMapControl(cname, cvalue, vtype, plugin_group, cenabled)', 2)
    cvalue = cvalue.strip()
    key_name = setting_name.split('[')[1].strip(']')

    ctrl = 'KEYMAP['
    js_onchange = 'onchange=CheckValue("%s","keymap",0)' % cname

    ctrl += CreateHTMLinput('textbox',cname + '_key' ,key_name,'10',js_onchange)
    ctrl += '] ='
    ctrl += CreateHTMLinput('textbox', cname + '_event', cvalue, '10', js_onchange)

    return ctrl



def CreateConfigLine(nctrl, plugin_group, expALL):
    '''
    '''
    _debug_('CreateConfigLine(nctrl=%r, plugin_group=%r, expALL=%r)' % (nctrl, plugin_group, expALL), 2)
    htmlctrl = ''

    control_name = nctrl['control_name']
    cname = nctrl['ctrlname']
    cvalue = nctrl['ctrlvalue']
    sline = nctrl['startline']
    eline = nctrl['endline']
    vtype = nctrl['type']
    chkline = cname + ' = ' + cvalue

    checked = ''
    if nctrl['checked']:
        checked = 'checked'
        displayvars = ''

    if not nctrl['checked']:
        htmlctrl += '<div id="%s_enable" class="disablecontrol">' % control_name
    else:
        htmlctrl += '<div id="%s_enable" clase="enablecontrol">' % control_name

    displayvars = 'none'
    if expALL:
        displayvars = ''

    lcheck = '<span class="checkOK">OK</span>'
    if not CheckSyntax(chkline):
        lcheck = '<span class="checkError">Error</span>'
    else:
        if FileTypeVar(cname):
            filename = cvalue.replace("'", '').strip()
            if not os.path.exists(filename):
                lcheck = '<span class = "CheckWarning">Missing File</span>'

    ctrltype = getCtrlType(cname, cvalue, vtype)
    jsonChange = ' onchange=CheckValue("%s","%s",0)'  % (control_name, ctrltype)
    chkbox = CreateHTMLinput('checkbox',control_name + '_chk','' , ''  , jsonChange + " " + checked)

    js_delete = 'onclick=DeleteLines("%s",%i,%i)' %  ( control_name, sline, eline)
    delbtn = CreateHTMLinput('button',control_name + '_delete','Delete','',js_delete)

    htmlctrl += '<span id="%s_check">%s</span>' % (control_name, lcheck)
    htmlctrl += delbtn
    htmlctrl += chkbox

    htmlctrl += '<a class="Setting_Line" onclick=ShowList("%s_list") name="%s">' % ( control_name, cname )
    htmlctrl += cname
    htmlctrl += '</a>'

    htmlctrl += '<ul style= display:%s id="%s_list">' % (displayvars, control_name)
    htmlctrl += CreateHTMLinput('hidden',control_name + "_startline", sline)
    htmlctrl += CreateHTMLinput('hidden',control_name + "_endline", eline)
    htmlctrl += CreateHTMLinput('hidden',control_name + "_ctrlname", cname)

    jsSave =  'onclick=SaveValue("%s","%s")' % (control_name, ctrltype)
    btn_update_id = '%s_btn_update' %  control_name
    htmlctrl += CreateHTMLinput('button',btn_update_id, 'Update','',jsSave + ' style=display:none;')

    htmlctrl += '<li class="Setting_Controls">'

    if nctrl['vartype'] == 'boolean':
        js_onchange = ' onchange=CheckValue("%s","textbox",0)' % control_name
        htmlctrl  += CreateSelectBoxControl(control_name, ['True', 'False'], cvalue, js_onchange)

    elif nctrl['vartype'] == 'tv_channels':
        htmlctrl += CreateTV_Channels_ctrl(cname, cvalue)

    elif nctrl['vartype'] == 'filelist':
        htmlctrl  += CreateFileItemList(control_name, cvalue ,cname)

    elif nctrl['vartype'] == 'dictionary':
        htmlctrl += CreateDictionaryControl(cname, cvalue)

    elif nctrl['vartype'] == 'list':
        htmlctrl += CreateListControl(control_name, cvalue )

    elif nctrl['vartype'] == 'keymap':
        htmlctrl += KeyMapControl(control_name, cname, cvalue, nctrl['vartype'], plugin_group)

    else:
        htmlctrl += CreateTextBox(control_name, cname, cvalue, nctrl['vartype'], plugin_group)

    if config.DEBUG == 2:
        config_line = nctrl['fileline'].replace('\n','')
        htmlctrl += '<li class="File_Line" id="%s_fileline">' % control_name
        htmlctrl += '%r' % (  config_line  )
        htmlctrl += '</li>'
    htmlctrl += '</li>'
    htmlctrl += '</ul>'
    htmlctrl += '</div>'

    return htmlctrl


def DisplayGroups(fconfig, expALL):
    '''
    '''
    _debug_('DisplayGroups(fconfig=%r, expALL=%r)' % (fconfig, expALL), 2)
    html =  '<ul class="GroupHeader">'

    groups = GetGroupList(fconfig)
    displayStyle = 'none'
    if expALL:
        displayStyle = ''

    for grp in groups:
        html += '<li class="VarGroupHeaderLine">'
        html += '<a class="VarGroupHeaderItem" onclick=ShowList("%s")>%s</a>\n'  % (grp, grp)
        html += '<ul id="%s" style= display:%s>\n' % (grp, displayStyle)
        for cctrl in fconfig:
            if cctrl['group'] == grp:
                lctrl = CreateConfigLine(cctrl, grp, expALL)
                html += '<li class="Setting_Line">'
                html += lctrl
                html += '</li>\n'
        html += '</ul>\n'
        html += '</li>\n'
    html += '</ul>\n'

    return html

def DisplayConfigChanges(current_version):
    '''
    '''
    _debug_('DisplayConfigChanges(current_version=%r)' % current_version, 2)

    if not current_version:
        current_version = 0

    cur_version = float(current_version)
    dsp_change = '<div class="Config_Changes">'
    dsp_change += 'Warning: freevo_config.py was changed, please check local_conf.py<br>'
    dsp_change += 'You are using version  %s, changes since then:' % current_version
    config_outdated = False

    for change in config.LOCAL_CONF_CHANGES:
         if change[0] > cur_version:
            dsp_change += '<li>\n'
            dsp_change += str(change[0]) 
            change_lines = change[1].split('\n')
            dsp_change += '<ul>\n'
            for line in change_lines:
                if len(line.strip()) > 0:
                    dsp_change += '<li>' + line + '</li>\n'
            dsp_change += '</ul>\n'
            dsp_change += '</li>\n'
            config_outdated = True

    if config_outdated:
        dsp_change += 'local_conf.py is out dated'
        dsp_change += CreateHTMLinput('Button','','Convert Config','','')
        dsp_change += '</ul>\n'
        dsp_change += '</div>\n'

    else:
        dsp_change = ''            

    return dsp_change


def GetConfigVersion(conf_data):
    '''
    '''  
    _debug_('GetConfigVersion(conf_data=%r)' % conf_data,2)
    for setting in conf_data:
         if setting['ctrlname'] == 'CONFIG_VERSION':
             return setting['ctrlvalue']
    return None

    
class ConfigResource(FreevoResource):

    def _render(self, request):
        '''
        '''
        config.DEBUG = 2
        _debug_('_render(self, request)', 2)
        fv = HTMLResource()
        form = request.args

        configfile = fv.formValue(form, 'configfile')
        configfile = GetConfigFileName(configfile)
        configfile = '/etc/freevo/local_conf.py'
        title = 'Config %s' %configfile
        fv.printHeader(_(title), 'styles/main.css', 'scripts/config.js', selected=_('Config'))

        fv.res += '<script language="JavaScript" type="text/JavaScript" src="scripts/browsefile.js"></script>'
        fv.res += '<link rel="stylesheet" href="styles/config.css" type="text/css" />\n'

        if not configfile:
            fv.res += 'Unable to find file.'
            return fv.res

        rconf = ReadConfig(configfile)
        fconfig = ParseConfigFile(rconf)

        # Add Setting for Adding New KEYMAPS
        add_keymap = {'ctrlname': 'KEYMAP[NEW]',
               'ctrlvalue': '',
               'checked': False,
               'type' : 'keymap',
               'comments' : 'New Key Map',
               'group' :'KeyMap',
               'startline': -1,
               'endline': -1,
               'fileline': '',
               'control_name':'KEYMAP_NEW',
               'vartype':'keymap'
        }
        fconfig.append(add_keymap)

        expAll = fv.formValue(form, 'expAll')
        expandAll = False
        if expAll:
            expandAll = True

        fv.res += CreateHTMLinput('hidden','configfile', configfile,'','')
        fv.res += '<div class="VarGroups">\n'

        # Check config version.
        local_conf_ver = GetConfigVersion(fconfig)
        fv.res += DisplayConfigChanges(local_conf_ver)

        fv.res += '<form id="config" action="config.rpy" method="get">\n'
        fv.res += DisplayGroups(fconfig, expandAll)
        fv.res + '</div>\n'
        fv.res += '</form><br>\n'

        return str(fv.res)

resource = ConfigResource()
