# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# web interface to edit local_config.py
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
#            Update button on collapsed settigns. eg, enable/disable.
#            Display logos, move then channels moved up and down.
#            Items List add new Line, once old new line is outdate.
#            Remove SKIN_XML_FILE from file types.
#            Create Directory option ?
#            Auto add quotes to strings.
#            Inbedding pick list options in local_conf ?
#            Fix JOY_CMDS ?
#            Keymap syntax checking.
#            OSD_FONT_PATH should have a browse buttons.
#            Fix () around MPLAYER SUFFIX.
#            Weather Location add links to sites to get locations.
#            Plugins - Problem with not picking up plugin arg when combined with level.
#            Enabling AUDIO_ALBUM_TREE_SPEC, check span disappears.
#            Updaet WWW_PERSONNEL_PAGE with Args eg. config.rpy&expAll=T.
#            Help - Comments , problem with over writing.

#import sys
import os.path
import string
import types
import time
import operator
from www.web_types import HTMLResource, FreevoResource

from www.configlib import *
import config
from event import *
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

        if  len(fln.split("=")) > 1 and not fln.startswith('"'):
            cfg_control = ConfigControl(fln)

            if cfg_control.type:
                cfg_control.startline = startline
                cfg_control.endline = cnt
                cfg_control.control_name = cfg_control.ctrlname + '_' + str(startline)
                fconfig.append(cfg_control)

        cnt += 1

    #fconfig.sort(key=operator.itemgetter('control_name'))
    return fconfig

class ConfigControl():

    def __init__(self, config_line):
        #print 'ConfigControl.__init__(config_line=%r)' % (config_line,)

        self.type = None
        self.comments = ''
        self.startline = -1
        self.endline = -1
        self.fileline = None
        self.control_name = None
        self.control_type = None

        tln = config_line.strip()
        tln = tln.replace('\n', '')

        self.enabled = True
        if tln.startswith('#'):
            self.enabled = False
            tln = tln.lstrip('#')
            tln = tln.lstrip()

        fsplit = tln.split('=')
        self.type = 'textbox'
        self.ctrlname  = fsplit[0].strip()
        self.group = GetVarGroup(self.ctrlname)

        if not self.ctrlname.isupper() and self.group <> 'KeyMap':
            self.type = ''

        if (not config.__dict__.has_key(self.ctrlname)):
            try:
                fvvalue = eval('config.' + self.ctrlname)
            except Exception, e:
                fvvalue = ''

        ctrlvalue = fsplit[1].split('#')
        self.comments = ''
        if len(ctrlvalue) == 2:
            self.comments = ctrlvalue[1]

        self.ctrlvalue = Unicode(ctrlvalue[0].strip())
        self.ctrlvalue = self.ctrlvalue.replace('"', "'")

        self.control_type = getCtrlType(self.ctrlname,self.ctrlvalue,self.type)

        if self.ctrlname.startswith('"'):
            self.type = ''

    def html_control(self):
        cvalue = self.ctrlvalue
        ctype = self.type
        ctrltype = getCtrlType(self.ctrlname,cvalue,ctype)

        htmlctrl = ''
        if ctrltype == 'textbox':
            other_opts = 'class = "%s"' % self.ctrlname
            htmlctrl = '<span class="DefaultTextBox">\n'
            htmlctrl += CreateTextBox(self.control_name, self.ctrlname, cvalue, other_opts)
            htmlctrl += '</span>\n'
        elif ctrltype == 'boolean':
            js_onchange = ' onchange=CheckValue("%s","textbox",0)' % self.control_name
            htmlctrl  = CreateSelectBoxControl(self.control_name, ['True', 'False'], cvalue, js_onchange)
        elif ctrltype == 'keymap':
            htmlctrl = KeyMapControl(self.control_name,self.control_name, cvalue)
        elif ctrltype == 'tv_channels':
            htmlctrl = CreateTV_Channels_ctrl(self.control_name, cvalue)
        elif ctrltype == 'fileitemlist':
            htmlctrl = CreateFileItemList(self.control_name, cvalue ,self.ctrlname)
        elif ctrltype == 'dictionary':
            htmlctrl = CreateDictionaryControl(self.control_name, cvalue)
        elif ctrltype == 'itemlist':
            htmlctrl = CreateListControl(self.control_name, cvalue )

        return htmlctrl



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


def GetGroupList(cfgvars):
    '''
    '''
    _debug_('GetGroupList(cfgvars=%r)' % (cfgvars), 2)
    grps = ['Other','KeyMap']
    agrps = []
    for vrs in cfgvars:
        grp = vrs.group
        agrps.append(grp)
        if not grp in grps:
            grps.append(grp)

    for vrs in cfgvars:
        ngrp = agrps.count(vrs.group)
        if ngrp == 1:
            grps.remove(vrs.group)
            vrs.group = 'Other'

    grps.sort()
    return grps


def getCtrlType(cname, cvalue, vtype):
    '''
    '''
    _debug_('getCtrlType(cname=%r, cvalue=%r, vtype=%r)' % (cname, cvalue, vtype), 2)
    if cvalue == 'True' or cvalue == 'False':
        return 'boolean'
    if cname == 'TV_CHANNELS':
        return 'tv_channels'
    if cname.startswith('KEYMAP'):
        return 'keymap'
    if FileTypeVarArray(cname):
        return 'fileitemlist'
    if cvalue.startswith('{'):
        return 'dictionary'
    if cvalue.startswith('['):
        return 'itemlist'
    if vtype == 'list':
        return 'itemlist'
    return 'textbox'


def CreateFileBrowseControl(cname,setting_name):
    '''
    '''
    _debug_('CreateFileBrowseControl(cname, setting_name)', 2)

    if DirTypeVar(setting_name) or FileTypeVarArray(setting_name) :
        js_browsefiles = 'onclick=BrowseFiles("%s","%s","D")' % ( cname , setting_name )
    else:
        js_browsefiles = 'onclick=BrowseFiles("%s","%s","F")' % ( cname , setting_name )

    btn_browse_id = '%s_browse' % cname
    btn_browse = '<input type="button" id="%s" class="BrowseButton" value="" title="Display File Browser" %s>\n' % ( btn_browse_id, js_browsefiles )
    btn_opts = 'title="Display File Browser %s' % js_browsefiles
    btn_browse = CreateHTMLinput('button',btn_browse_id,'', '',other_opts = '')

    js_cancel = 'onclick=CancelBrowse("%s")' % cname
    btn_cancel_id = '%s_cancel' % cname
    style = 'display:none'
    cancel_button = '<input type="button" value="" title="Close File Browser" class="CloseBrowseButton"  id="%s" %s style=%s>\n' % (btn_cancel_id , js_cancel, style)
    browse_area = '<div id="%s_filebrowse" class="file_browse" style=%s></div>\n' % ( cname, style )
    file_browse_control = btn_browse + cancel_button + browse_area
    return file_browse_control


def Display_TV_Logo(channel):
    station = channel.split(',')[1].strip()
    station_name =  station.split(' ')[-1].strip("'")

    if os.path.isdir(os.path.join(os.environ['FREEVO_PYTHON'], 'www/htdocs')):
        docRoot = os.path.join(os.environ['FREEVO_PYTHON'], 'www/htdocs')
    else:
        docRoot = os.path.join(config.SHARE_DIR, 'htdocs')

    imgfile = os.path.join(docRoot,'images/logos/',station_name + '.gif')
    if not os.path.exists(imgfile):
        station_name = 'BLANK'

    logo = '<img class="TvLogo" src="images/logos/%s.gif" >\n' % station_name
    return logo


def CreateTV_Channels_ctrl(cname, cvalue):
    '''
    '''
    _debug_('CreateTV_Channels_ctrl(cname, cvalue)', 2)
    vitems = GetItemsArray(cvalue)
    ctrl = ''

    if vitems:
        for r, e in enumerate(vitems):
            ctrl += '<li class="TV_Channels_Line">\n'
            up_title = 'title="Move Channel Up in the List."'
            js_moveup = 'onclick=MoveTVChannel("%s",%i,%i) class="TV_Button"' % (cname, r, -11 )
            ctrl += '<a class="ChannelUp" %s %s>Up</a>\n' % (js_moveup, up_title )

            control_id = '%s_item%i' % ( cname, r )
            tv_line = unicode(str(e))
            ctrl += Display_TV_Logo(tv_line)
            html_textbox = CreateHTMLinput('textbox', control_id, tv_line, '30',  'class="TV_Channel"' )
            ctrl += html_textbox

            if r <>  (len(vitems) -1):
                js_movedown = 'onclick=MoveTVChannel("%s",%i,%i) class="TV_Button"' % (cname, r, 1 )
                down_title = 'title="Move Channel Down in the List."'
                ctrl += '<a class="ChannelDown" %s %s>Down</a>\n' %  ( js_movedown, down_title)

            ctrl += '</li>\n'

    js_onclick = 'onclick=Detect_Channels("%s")' % cname
    ctrl += '<a %s>Auto Detect Channels</a>' % js_onclick
    ctrl += '</span>\n'
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
            lineid = '%s_line_%i' % (cname, r)
            ctrl += '<li class="Setting_Controls" id="%s">\n' % (lineid)

            if type(e) == types.StringType or type(e) ==  types.IntType:
                control_id = '%s_file%i' % ( cname, r)
                html_input = CreateHTMLinput('textbox', control_id, e, '' )
                browse_file_ctrl = CreateFileBrowseControl(control_id,setting_name)

                ctrl += html_input
                fcheck = ErrorMessage('FILE',control_id,e)

            else:
                label_ctrl_id = '%s_label%i' % ( cname, r )
                js_onchange = 'onchange=CheckValue("%s","fileitemlist","%i")' % (cname, r)
                label_ctrl = CreateHTMLinput('textbox', label_ctrl_id, e[0], '', js_onchange)

                dir_ctrl_id = '%s_file%i' % ( cname, r )
                js_onchange = 'onchange=CheckValue("%s","fileitemlist","%i")' % (cname, r)
                dir_ctrl = CreateHTMLinput('textbox', dir_ctrl_id, e[1], '', js_onchange )
                browse_file_ctrl = CreateFileBrowseControl(dir_ctrl_id,setting_name)

                ctrl += label_ctrl
                ctrl += dir_ctrl
                fcheck = ErrorMessage('FILE',dir_ctrl_id,e[1])

            ctrl += DeleteListItem(lineid,cname + '_btn_update')
            ctrl += fcheck
            ctrl += browse_file_ctrl
            ctrl += '</li>\n'

        r += 1;
        ctrl += '<li class="Setting_Controls" id="%s_line_%i">\n' % ( cname, r)
        js_onchange = 'onchange=CheckValue("%s","fileitemlist","%i")' % (cname, r)
        label_ctrl_id = '%s_label%i' % ( cname, r )
        ctrl += CreateHTMLinput('textbox', label_ctrl_id, '', '', '')

        dir_ctrl_id = '%s_file%i' % ( cname, r )
        ctrl += CreateHTMLinput('textbox', dir_ctrl_id, '', '', js_onchange )

        dir_ctrl_id = '%s_file%i' % ( cname, r )
        dir_ctrl = CreateHTMLinput('textbox', dir_ctrl_id, e[1], '', js_onchange )
        browse_file_ctrl = CreateFileBrowseControl(dir_ctrl_id,setting_name)
        ctrl += browse_file_ctrl

        ctrl += '<span class="" id="%s_check_%i"></span>\n' % (cname, r)
        ctrl += '</li>\n'

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
    js_onchange = 'onchange=CheckValue("%s","dictionary","")' % cname

    if vitems:
        for r, e in enumerate(vitems):
            pword =  vitems[e]
            lineid = '%s_line_%i' % (cname, r)
            ctrl += '<li class="Setting_Controls" id="%s">\n' % lineid

            label_ctrl_id = '%s_key%i' % ( cname, r)
            ctrl += CreateHTMLinput('textbox', label_ctrl_id, e, '15', js_onchange)

            value_ctrl_id = '%s_value%i' % ( cname, r )
            ctrl += CreateHTMLinput(ctrl2type, value_ctrl_id, vitems[e], '15', js_onchange)

            ctrl += DeleteListItem(lineid,cname + '_btn_update')
            ctrl += '</li>\n'

        lineid = '%s_line_%i' % (cname, r+1)
        ctrl += '<li class="Setting_Controls" id="%s">\n' % lineid
        label_ctrl_id = '%s_key%i' % ( cname, r+1)
        ctrl += CreateHTMLinput('textbox', label_ctrl_id, '', '15', '')

        value_ctrl_id = '%s_value%i' % ( cname, r+1 )
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

            lineid = '%s_line%i' % (cname, r)
            ctrl += '<li class="Setting_Controls" id="%s">\n' % lineid
            ctrl += ctrl_line
            ctrl += DeleteListItem(lineid, cname + '_btn_update')
            ctrl += '</li>\n'

        if not cvalue.strip().startswith('('):
            r+= 1;
            lineid = '%s_line%i' % (cname, r)
            ctrl += '<li class="Setting_Controls" id="%s">\n' % lineid
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

    ctrl = '<textarea id= "%s" rows="%i" cols="35" wrap="SOFT" %s>\n'  % (cname, rows, js_onchange)
    ctrl += cvalue
    ctrl += '</textarea>\n'
    return ctrl


def CreateTextBox(cname, setting_name, cvalue, other_opts = None):
    '''
    '''
    _debug_('CreateTextBox(cname, cvalue,  plugin_group, cenabled)', 2)
    cvalue = cvalue.strip()

    ctrl = ""
    js_onchange = 'onchange=CheckValue("%s","textbox",0)' % cname
    if not other_opts:
        other_opts = ''

    control_value = cvalue.strip("'")
    ctrl_opts = '%s %s' % (js_onchange, other_opts)
    html_input = CreateHTMLinput('textbox', cname, control_value, '', ctrl_opts)
    ctrl += html_input

    if FileTypeVar(setting_name) or DirTypeVar(setting_name):
        browse_file_control = CreateFileBrowseControl(cname,setting_name)
        ctrl += browse_file_control

    return ctrl


def KeyMapControl(cname, setting_name, cvalue ):
    '''
    '''
    _debug_('KeyMapControl(cname, cvalue,  cenabled)', 2)
    cvalue = cvalue.strip()
    key_name = setting_name.split('[')[1].strip(']')

    ctrl = 'KEYMAP['
    js_onchange = 'onchange=CheckValue("%s","keymap",0)' % cname

    ctrl += CreateHTMLinput('textbox',cname + '_key' ,key_name,'10',js_onchange)
    ctrl += '] ='
    ctrl += CreateHTMLinput('textbox', cname + '_event', cvalue, '10', js_onchange)

    return ctrl


def DeleteListItem(lineid,updateid):
    btn_class = 'class="DeleteButton"'
    btn_title = 'title ="Delete Line from List"'
    btn_js = 'onclick=DeleteItemLine("%s","%s")' % ( lineid , updateid )

    btn_opts = '%s %s %s' % (btn_title, btn_class, btn_js)
    btnDelete = CreateHTMLinput('button','delete','','',btn_opts)
    return btnDelete


def StartControlLine(nctrl):
    _debug_('StartControlLine(%r)' % nctrl ,2)
    ctrl = ''
    cname = nctrl.control_name

    ctrl += CreateHTMLinput('hidden',cname + "_startline", nctrl.startline)
    ctrl += CreateHTMLinput('hidden',cname + "_endline", nctrl.endline)
    ctrl += CreateHTMLinput('hidden',cname + "_ctrlname", nctrl.ctrlname)
    stringtype = nctrl.ctrlvalue.startswith("'")
    ctrl += CreateHTMLinput('hidden',cname + "_string",stringtype)

    return  ctrl


def DeleteButton(nctrl):

    js_delete = 'onclick=DeleteLines("%s",%i,%i)' %  (nctrl.control_name, nctrl.startline,nctrl.endline)
    btn_class = 'class="DeleteButton"'
    btn_title = 'title="Delete Lines %i to %i from local_conf.py"' % ( nctrl.startline, nctrl.endline )
    del_opts = '%s %s %s' % (btn_class, js_delete , btn_title)
    delbtn = CreateHTMLinput('button',nctrl.control_name + '_delete','','',del_opts)
    return delbtn

def EnableCheckBox(nctrl):
    if nctrl.enabled:
        checked = 'checked'
    else:
        checked = ''

    jsonChange = ' onchange=CheckValue("%s","%s",0)'  % (nctrl.control_name, nctrl.control_type)
    chkbox = CreateHTMLinput('checkbox',nctrl.control_name + '_chk','' , ''  , jsonChange + " " + checked)
    return chkbox

def CreateConfigLine(nctrl,  expALL):
    '''
    '''
    _debug_('CreateConfigLine(nctrl=%r,  expALL=%r)' % (nctrl, expALL), 2)
    htmlctrl = ''

    control_name = nctrl.control_name
    cname = nctrl.ctrlname
    cvalue = nctrl.ctrlvalue

    htmlctrl += StartControlLine(nctrl)
    complex_ctrls = ['tv_channels','fileitemlist','dictionary','itemlist']
    simple_controls = ['textbox','boolean']

    if nctrl.enabled:
        htmlctrl += '<div id="%s_enable" clase="enablecontrol">\n' % control_name
        displayvars = ''
    else:
        htmlctrl += '<div id="%s_enable" class="disablecontrol">\n' % control_name

    displayvars = 'none'
    if expALL:
        displayvars = ''

    htmlctrl += ErrorMessage(cname,control_name, nctrl.ctrlvalue)
    htmlctrl += DeleteButton(nctrl)
    htmlctrl += EnableCheckBox(nctrl)

    if nctrl.control_type == 'keymap':
        htmlctrl += nctrl.html_control()

    setting_class = 'Setting_Line_Close'
    js_showlist = 'onclick=ShowList("%s")' % control_name
    anchor_title = 'title="%s (Click to Show / Hide %s value) "' % ( nctrl.comments , cname )

    if expALL:
        setting_class = 'Setting_Line_Open'
    if nctrl.control_type in simple_controls:
        setting_class = 'Setting_Line'
        js_showlist = ''
        anchor_title = 'title="%s"' % nctrl.comments

    anchorID = '%s_anchor' % control_name
    if nctrl.control_type <> 'keymap':
        htmlctrl += '<a class="%s" id="%s" name="%s" %s>' % ( setting_class, anchorID,   cname, js_showlist  + ' ' + anchor_title)
        htmlctrl += cname
        htmlctrl += '</a>\n'

    if  nctrl.control_type in simple_controls:
        htmlctrl += nctrl.html_control()

    jsSave =  'onclick=SaveValue("%s","%s")' % (control_name, nctrl.control_type)
    btn_update_id = '%s_btn_update' %  control_name
    htmlctrl += CreateHTMLinput('button',btn_update_id, 'Update','',jsSave + ' style=display:none;')

    if nctrl.control_type in complex_ctrls:
        htmlctrl += '<ul style= display:%s id="%s_list">\n' % (displayvars, control_name)
        htmlctrl += '<li class="Setting_Controls">\n'
        htmlctrl += nctrl.html_control()
        htmlctrl += '</li>\n'
        htmlctrl += '</ul>\n'

    htmlctrl += '<li class="File_Line" id="%s_fileline">' % control_name
    if config.DEBUG == 3:
        config_line = nctrl.fileline.replace('\n','')
        htmlctrl += '%r' % (  config_line   )

    htmlctrl += '</li>\n'
    htmlctrl += '</div>\n'

    return htmlctrl



def DisplayConfigChanges(current_version):
    '''
    '''
    _debug_('DisplayConfigChanges(current_version=%r)' % current_version, 2)

    if not current_version:
        current_version = 0

    cur_version = float(current_version)
    dsp_change = '<div class="Config_Changes">\n'
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
        dsp_change += '</div>\n'
    else:
        dsp_change = None

    return dsp_change


def GetConfigVersion(conf_data):
    '''
    '''
    _debug_('GetConfigVersion(conf_data=%r)' % conf_data,2)
    for setting in conf_data:
        if setting.ctrlname == 'CONFIG_VERSION':
            return setting.ctrlvalue
    return None


class ConfigResource(FreevoResource):

    def __init__(self):
        self.hide_disabled = False
        self.expand_all = False
        #print 'Config Resourese'


    def DisplayGroups(self,fconfig):
        '''
        '''
        _debug_('DisplayGroups(fconfig=%r)' % (fconfig), 2)
        html =  '<ul class="GroupHeader">'

        groups = GetGroupList(fconfig)
        displayStyle = 'none'
        if self.expand_all:
            displayStyle = ''

        for grp in groups:
            html += '<li class="VarGroupHeaderLine">\n'
            html += '<a class="VarGroupHeaderItem" onclick=ShowList("%s")>%s</a>\n'  % (grp, grp)
            html += '<ul id="%s_list" style= display:%s>\n' % (grp, displayStyle)
            for cctrl in fconfig:
                if cctrl.group == grp:
                    html += '<li class="LineOpen" id="%s_line">\n' % cctrl.control_name
                    html += CreateConfigLine(cctrl,  self.expand_all)
                    html += '</li>\n'
            html += '</ul>\n'
            html += '</li>\n'
        html += '</ul>\n'

        return html

    def DisplayGroup(self, grp,fconfig):
        '''
        '''
        _debug_('DisplayGroups(fconfig=%r)' % (fconfig), 2)

        groups = GetGroupList(fconfig)
        displayStyle = 'none'
        if self.expand_all:
            displayStyle = ''

        html = ''
        for cctrl in fconfig:

            if cctrl.group == grp:
                if cctrl.enabled:
                    html += '<li class="LineOpen" id="%s_line">\n' % cctrl.control_name
                    html += CreateConfigLine(cctrl,  self.expand_all)
                    html += '</li>\n'
                else:
                    if  not self.hide_disabled:
                        html += '<li class="LineOpen" id="%s_line">\n' % cctrl.control_name
                        html += CreateConfigLine(cctrl,  self.expand_all)
                        html += '</li>\n'

        return html

    def _render(self, request):
        '''
        '''
        _debug_('_render(self, request)', 2)
        fv = HTMLResource()
        form = request.args

        configfile = fv.formValue(form, 'configfile')
        configfile = GetConfigFileName(configfile)
        title = 'Config %s' %configfile
        fv.printHeader(_(title), 'styles/main.css', 'scripts/config.js', selected=_('Config'))

        fv.res += '<script language="JavaScript" type="text/JavaScript" src="scripts/browsefile.js"></script>\n'
        fv.res += '<link rel="stylesheet" href="styles/config.css" type="text/css">\n'

        if not configfile:
            fv.res += 'Unable to find file.'
            return fv.res

        wizard_groups = ['Tv','Video','Audio','Image','Headline','Www','All','Config Changes','Options']
        current_group = fv.formValue(form,"current_group")
        if not current_group:
            current_group = "Tv"
        if not current_group in wizard_groups:
            current_group = "Tv"

        rconf = ReadConfig(configfile)
        fconfig = ParseConfigFile(rconf)

        # Add Setting for Adding New KEYMAPS
#        add_keymap = {'ctrlname': 'KEYMAP[NEW]',
#               'ctrlvalue': '',
   #            'checked': False,
      #         'type' : 'keymap',
         #      'comments' : 'New Key Map',
            #   'group' :'KeyMap',
               #'startline': -1,
#               'endline': -1,
   #            'fileline': '',
      #         'control_name':'KEYMAP_NEW',
         #      'control_type':'keymap',
            #   'html_control': KeyMapControl('KEYMAP_NEW', 'KEYMAP[NEW]', '')
       # }
        #fconfig.append(add_keymap)

        expAll = fv.formValue(form, 'expAll')
        if expAll:
            self.expand_all = True

        fv.res += CreateHTMLinput('hidden','configfile', configfile,'','')
        fv.res += '<div class="VarGroups">\n'

        fv.res += '<form id="config" action="config.rpy" method="get">\n'
        fv.res += ' <div id="ConfigGroup">'
        fv.res += '<ul>'
        for group in wizard_groups:
            group_id = ""
            if current_group == group:
                group_id = "current"
            fv.res += '<li id="%s">\n' % group_id
            fv.res += '<a href="config.rpy?current_group=%s">%s</a>\n' % (group,  group)
            fv.res += '</li>\n'
        fv.res += '</ul>\n'
        fv.res += '</div>\n<br><br>'

        if current_group == "All":
            fv.res += self.DisplayGroups(fconfig)
        elif current_group == 'Config Changes':
            local_conf_ver = GetConfigVersion(fconfig)
            fv.res += DisplayConfigChanges(local_conf_ver)
        elif current_group == 'Options':
            fv.res += 'Create Options !!'
        else:
            fv.res += self.DisplayGroup(current_group,fconfig)

        fv.res + '</div>\n'

        return str(fv.res)

resource = ConfigResource()
