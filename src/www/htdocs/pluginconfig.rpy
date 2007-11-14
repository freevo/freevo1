# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# pluginconfig - update plugin settings in local_conf.py
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
import urllib
import operator
import os
import popen2
from signal import *

import config
from www.configlib import *
from www.web_types import HTMLResource, FreevoResource
import util
from plugin import is_active, activate, remove

from helpers.plugins import parse_plugins
from helpers.plugins import html_info
import os

TRUE = 1
FALSE = 0

def ParsePluginName(line):
    '''
    '''
    _debug_('ParsePluginName(line=%r)' % (line), 2)
    sline = line.replace('"', "'")
    sline = sline.split("'")
    if len(sline) > 2:
        pname = sline[1]
    else:
        pname =  'error'
    return pname


def GetConfigSetting(cfile, vname):
    '''
    '''
    _debug_('GetConfigSetting(cfile=%r, vname=%r)' % (cfile, vname), 2)

    lconf = ReadConfig(cfile)
    ret = ''
    for ln in lconf:
        ln = ln.strip('#')
        ln = ln.strip()
        if ln.startswith(vname):
            sln = ln.split('=')
            if len(sln) > 1:
                ret = sln[1].split('#')[0]
    return ret


def ReadConfigPlugins(cfile):
    '''
    '''
    _debug_('ReadConfigPlugins(cfile=%r)' % (cfile), 2)
    rconf = ReadConfig(cfile)
    pluginlines = []
    cnt = 0
    while cnt < len(rconf):
        pline = {'name':'', 'lineno':0, 'orgline':'', 'enabled':False, 'removed':False}
        ln = rconf[cnt].strip()
        pline['enabled'] = True

        if ln.startswith('#'):
            pline['enabled'] = False
            ln = ln.strip('#')
            ln = ln.strip()

        if ln.startswith('plugin'):
            pline['name'] = ParsePluginName(ln)
            pline['lineno'] = cnt
            pline['orgline'] = rconf[cnt]
            pluginlines.append(pline)

        cnt += 1

    return pluginlines


def GetPlugConfig(plugin):
    '''
    '''
    _debug_('GetPlugConfig(plugin=%r)' % (plugin), 2)

    config_list = []
    if plugin[5].find('config') > 0:
        exec (plugin[5])
        config_list = return_config()

    return config_list


def SortPlugins(pluginlist, plugin_grps):
    '''
    '''
    _debug_('SortPlugins(pluginlist=%r, plugin_grps=%r)' % (pluginlist, plugin_grps), 2)
    sorted = []
    for plugin in pluginlist:
        pgrp = plugin[0].split('.')[0]
        if not pgrp  in plugin_grps:
            pgrp = 'Global'
        sorted.append([pgrp, plugin])
    return sorted


def get_config_setting(lconf, plugin_name):
    '''
    '''
    _debug_('get_config_setting(lconf=%r, plugin_name=%r)' % (lconf, plugin_name), 2)
    conf_line = 'None'
    confentry = False
    linenumber = -1
    for lnum, lcline in enumerate(lconf):
        if  lcline['name'] == plugin_name:
            conf_line = lcline['orgline']
            linenumber = lcline['lineno']
            confentry = True
    return conf_line, linenumber


def plugin_level_control(lconf_line, plugin):
    '''
    '''
    _debug_('plugin_level_control(lconf_line=%r, plugin=%r)' % (lconf_line, plugin), 2)

    # check to see if the plugin supports levels.
    lconf_line = lconf_line.replace(' ', '')
    if lconf_line.find('level=') == -1:
        plugin_info = plugin[4].replace(' ', '')
        if plugin_info.find('level=') == -1:
            level = 'none'
        else:
            level = 45
    else:
        level = lconf_line.split('level=')[1]
        level = level.replace(')', '')

    level_ctrl = ''
    if level <> "none":
        level_ctrl = '<li class="Plugin_Level">\n'
        level_ctrl += '<label for="%s_level">Level:</label>' % plugin[0]
        level_ctrl += CreateHTMLinput('input',plugin[0] + '_level', level, '2', '')
        level_ctrl += '</li>\n'

    return level_ctrl


def get_plugin_status(plugin_name, lconfline):
    '''
    '''
    _debug_('get_plugin_status(plugin_name=%r, lconfline=%r)' % (plugin_name, lconfline), 2)
    status = 'Deactive'

    if is_active(plugin_name):
        status = 'Active'

    if is_active(plugin_name) and lconfline != "None":
        status = 'Active'

    if lconfline.startswith('plugin.remove'):
        status = 'Removed'

    return status


def get_plugin_args(config_line):
    '''
    '''
    _debug_('get_plugin_args(config_line=%r)' % (config_line), 2)

    plugin_args = ''
    if config_line.find("args=") <> -1:
        plugin_args = config_line.split('args=')[1]

    return plugin_args


def PluginHelpLink(plugin_group, plugin_name):
    '''
    '''
    _debug_('PluginHelpLink(plugin_group=%r, plugin_name=%r)' % (plugin_group, plugin_name ), 2)

    href = 'help/plugins.rpy?type=%s#%s' % ( plugin_group.lower(),  plugin_name.lower()  )
    plugin_help = '<a href="%s" class="Help_Link">' % href
    plugin_help += ' Help '
    plugin_help += '</a>\n'

    return plugin_help


def displayplugin(cfile, plugin, lconf, expAll , plugin_group):
    '''
    '''
    _debug_('displayplugin(cfile=%r, plugin=%r, lconf=%r, expAll=%r, plugin_group=%r)' %  \
           (cfile, plugin, lconf, expAll, plugin_group), 2)

    ctrlopts = ['Active', 'Deactive', 'Removed']
    html = ''

    # check tos ee fi the plugin has a line in localconf
    lconfline, linenumber = get_config_setting(lconf, plugin[0])
    plugin_args = get_plugin_args(lconfline)

    level = 'N/A'
    pluginname = plugin[0]
    status = get_plugin_status(pluginname, lconfline)
    pc_opts = 'onchange=UpdatePlugin("%s")' % pluginname

    if status == 'Active':
        html = '<div class="enablecontrol">\n'
    else:
        html = '<div class="disablecontrol">\n'

    dstyle = 'none'
    if expAll:
        dstyle = ''

    html += '<li class="PluginHeader">\n'
    html += '<span class="PluginStatus" id="%s_status">' % ( pluginname )
    html += '<a class="PluginStatus%s">%s</a>\n' % ( status, status )
    html += '</span>'
    html += CreateSelectBoxControl(pluginname + '_cmd', ctrlopts, status, pc_opts)
    html += CreateHTMLinput('hidden',pluginname + '_lineno', str(linenumber) , '','')

    html += PluginHelpLink( plugin_group, pluginname )
    js_onclick = 'onclick=DisplayList("%s_info")' % pluginname
    html += '<a class="Plugin_Name" %s name="%s" >' % (js_onclick,  pluginname)
    html += pluginname
    html += '</a>\n'

    html += '<span id=%s_updateinfo></span>\n' % pluginname
    html += '<ul id="%s_info" class="PluginInfoList" style=display:%s;)>\n' % (pluginname, dstyle)
    html += plugin_level_control(lconfline, plugin)

    html += '<li class="Plugin_Level">\n'
    html += '<label for="%s_args">Plugin Args:</label>' % pluginname
    html += CreateHTMLinput('textbox',pluginname + '_args', plugin_args, '20','')
    html += '</li>\n'

    html += '<li class="Plugin_Line" id="%s_config_line">\n' % pluginname
    html += '%i - %s' %  ( linenumber, lconfline)
    html += '</li>\n'

    html += Display_Vars(plugin, cfile)
    html += '<li class="Plugin_Info">\n'
    html += plugin[4].replace('\n', '<br>\n')

    html += '</li>\n'
    html += '</ul>\n'
    html += '</div>\n'
    return html

def Display_Vars(plugin, cfile):
    '''
    '''
    _debug_('Display_Vars(plugin=%r, cfile=%r)' % (plugin, cfile), 2)

    try:
        clist = GetPlugConfig(plugin)
        dsp_vars = '<ul class="plugin_vars">\n'
        if clist:
            for cnt, vr in enumerate(clist):
                curvalue = GetConfigSetting(cfile, vr[0])
                dsp_vars += '<li class="Plugin_Var">\n'
                if not curvalue:
                    js_newsetting = 'onclick=CreateSetting("%s")' % vr[0]
                    dsp_vars += '<span class="btnAdd">'
                    dsp_vars += CreateHTMLinput('button','','Add','',js_newsetting)
                    dsp_vars += '</span>'
                    dsp_vars += '<a href="config.rpy?expAll=T#%s">\n' % vr[0]
                    dsp_vars += vr[0] + '</a>\n'
                    dsp_vars += '<span id="%s_config_line"></span>\n' % vr[0]

                else:
                    dsp_vars += '<span class="btnAdd">'
                    dsp_vars += '</span>'
                    dsp_vars += '<a href="config.rpy?expAll=T#%s">\n' % vr[0]
                    dsp_vars += vr[0] + '</a>\n'


                dsp_vars += curvalue
                dsp_vars += vr[2]
                dsp_vars += '</li>\n'
            dsp_vars += '</ul>\n'
    except SyntaxError, e:
        dsp_vars = 'plugin=%r %s\n' % (plugin[0], e)

    return dsp_vars


def display_group(dsp_group, splugins, configfile, lcplugins, expandAll):
    '''
    '''
    _debug_('display_group(dsp_group=%r, splugins=%r, configfile=%r, lcplugins=%r, expandAll=%r)' % \
        (dsp_group, splugins, configfile, lcplugins, expandAll), 2)

    grouplist = ''
    grouplist += '<a class="Plugin_Group" name="%s" onclick=DisplayList("%s_list")>\n' %  ( dsp_group, dsp_group )
    grouplist += dsp_group
    grouplist += '</a>\n'

    grouplist += '<ul id="%s_list">\n' % dsp_group
    server_list = ['recordserver','encodingserver','commdetectserver','webserver']
    helper_list = ['tv_grab', 'cache']
    server_list.sort()

    if dsp_group == 'servers':
        for server in server_list:
            grouplist += Display_Server(server)
    elif dsp_group == 'helpers':
        for helper in helper_list:
            grouplist += Display_Helper(helper)

    else:
        for plugin in splugins:
            if dsp_group == plugin[0]:
                pluginname = plugin[1][0]
                pluginctrl = displayplugin(configfile, plugin[1], lcplugins, expandAll, dsp_group)
                grouplist += pluginctrl
    grouplist += '</ul>\n'

    return grouplist

class ConfigurePluginsResource(FreevoResource):

    def _render(self, request):
        '''
        '''
        _debug_('_render(request)', 2)

        fv = HTMLResource()
        form = request.args

        configfile = fv.formValue(form, 'configfile')
        configfile = GetConfigFileName(configfile)
        title = 'Plugin Setup - %s' % configfile
        fv.printHeader(_(title), 'styles/main.css', 'scripts/pluginconfig.js', selected=_('Config Plugins'))

        if not hasattr(config, 'all_plugins'):
            config.all_plugins = parse_plugins()

        config.all_plugins.sort()

        if not configfile:
            fv.printMessages(['Unable to find file - ' + configfile])
            return fv.res

        all_plugins = config.all_plugins
        group_list = ['Global', 'tv', 'video', 'audio', 'image', 'idlebar', 'servers','helpers']
        group_list.sort()
        splugins = SortPlugins(all_plugins, group_list)

        # Read the settings from localconf for plugins.
        lcplugins = ReadConfigPlugins(configfile)

        expAll = fv.formValue(form, 'expAll')
        expandAll = False
        if expAll:
            expandAll = True

        fv.res += '<link rel="stylesheet" href="styles/config.css" type="text/css" />\n'
        fv.res += CreateHTMLinput('hidden','configfile',configfile,'','')
        fv.res += '<div class="VarGroups">\n'
        fv.res += '<form action="#" class="searchform">\n'
        fv.res += '<ul>\n'

        for grp in group_list:
            fv.res += '<li class="Plugin_Group">\n'
            fv.res += Unicode(display_group(grp, splugins, configfile, lcplugins, expandAll))
            fv.res += '</li>\n'

        fv.res += '</ul>\n'
        fv.res += '</div>\n'
        fv.res += '</form>\n'

        return str(fv.res)

resource = ConfigurePluginsResource()
