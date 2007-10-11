#! /usr/bin/python
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
from www.web_types import HTMLResource, FreevoResource
import util, config
from plugin import is_active
from helpers.plugins import parse_plugins
from helpers.plugins import info_html
import os

TRUE = 1
FALSE = 0


def ReadConfig(cfile):
    lconf = cfile
    lconf_hld = open(lconf, 'r')
    fconf = lconf_hld.readlines()
    lconf_hld.close
    return fconf


def ParsePluginName(line):
    sline = line.replace('"', "'")
    sline = sline.split("'")
    if len(sline) > 2:
        pname = sline[1]
    else:
        pname =  'error'
    return pname


def GetConfigSetting(cfile, vname):

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

    config_list = []
    if plugin[5].find('config') > 0:
        exec (plugin[5])
        config_list = return_config()

    return config_list


def SortPlugins(pluginlist, plugin_grps):
    sorted = []
    for plugin in pluginlist:
        pgrp = plugin[0].split('.')[0]
        if not pgrp  in plugin_grps:
            pgrp = 'Global'
        sorted.append([pgrp, plugin])
    return sorted

def CreateListBox(cname, grps, cvalue, opts):
    ctrl = '\n<select name="%s" value=""  id="%s" %s>' % (cname, cname, opts)
    for grp in grps:
        if grp == cvalue:
            ctrl  += '\n    <option value="' + grp + '" selected="yes">' + grp + '</option>'
        else:
            ctrl  += '\n    <option value="' + grp + '">' + grp + '</option>'
    ctrl += '\n</select>'
    return ctrl


def get_config_setting(lconf, plugin_name) :
    conf_line = 'None'
    confentry = False
    linenumber = -1
    for lnum, lcline in enumerate(lconf):

        if  lcline['name'] == plugin_name:

            conf_line = lcline['orgline']
            linenumber = lcline['lineno']
            confentry = True
    return conf_line, linenumber

def plugin_level_control(lconf_line, plugin) :
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
        level_ctrl = 'Level :<input  id="%s_level" name="newname" size="2" value="%s">' % (plugin[0], level)

    return level_ctrl


def get_plugin_status(plugin_name,  lconfline)    :
    status = 'Deactive'

    if is_active(plugin_name):
        status = 'Active'

    if is_active(plugin_name) and lconfline != "None":
        status = 'Active'

    if lconfline.startswith('plugin.remove'):
        status = 'Removed'

    return status

def get_plugin_args(config_line):

    plugin_args = ''
    if config_line.find("args=") <> -1:
        plugin_args = config_line.split('args=')[1]
        print "PLugin Args Found !!!"

    return plugin_args


def displayplugin(cfile, plugin, lconf, expAll):
    ctrlopts = ['Active', 'Deactive', 'Remove']
    html = HTMLResource()

    # check tos ee fi the plugin has a line in localconf
    lconfline, linenumber = get_config_setting(lconf, plugin[0])

    plugin_args = get_plugin_args(lconfline)

    level = 'N/A'
    pluginname = plugin[0]
    status = get_plugin_status(pluginname, lconfline)
    pc_opts = 'onchange=UpdatePlugin("%s")' % pluginname

    spDisable_open = ''
    spDisable_close = ''
    if status != "Active":
        spDisable_open = '<span class="disablecontrol">'
        spDisable_close = '</span>'

    dstyle = 'none'
    if expAll:
        dstyle = ''

    html.res += '<li>%s<span class="PluginStatus%s">%s</span>%s' % (spDisable_open, status, status, spDisable_close)
    html.res += spDisable_open
    html.res += CreateListBox(pluginname + '_cmd', ctrlopts, status, pc_opts)
    html.res +=  '<input type="hidden" id="%s_lineno" value="%i">\n' % (pluginname, linenumber)
    html.res += '<a  onclick=DisplayList("%s_info")>%s</a></li>\n' % (pluginname,   pluginname)
    html.res += spDisable_close
    html.res += '<span id=%s_updateinfo></span>' % pluginname

    html.res += '<ul id="%s_info" style="display:%s;")>\n' %  (pluginname, dstyle)
    html.res += '<li><span id="%s_config_line" class="config_line">%i - %s</span></li>'  %  (pluginname, linenumber, lconfline)

    html.res += '<li>' + plugin_level_control(lconfline, plugin) + '</li>'
    html.res += '<li> Plugin Args :<input  id="%s_args" name="newname" size="20" value="%s">%s</li>' % \
        (pluginname, plugin_args, plugin_args)


    html.res += dispay_vars(plugin, cfile)
    html.res += '<li><div class="plugin_info">%s</div></li>' % plugin[4].replace('\n', '<br>\n')
    html.res += '</ul>'
    return html.res

def dispay_vars(plugin, cfile) :

    clist = GetPlugConfig(plugin)
    dsp_vars = '<ul class="plugin_vars">'
    for cnt, vr in enumerate(clist):
        curvalue = GetConfigSetting(cfile, vr[0])
        dsp_vars += '<li>\n'
        dsp_vars += vr[0] + '\n'
        dsp_vars += curvalue
        dsp_vars += vr[2]
        dsp_vars += '</li>\n'
    dsp_vars += '</ul>\n'

    return dsp_vars

def display_group(dsp_group, splugins, configfile, lcplugins, expandAll):

    grpheader = ''
    grpheader += '<li><a onclick=DisplayList("%s_list")>%s</a>\n'
    grouplist = grpheader  % (dsp_group, dsp_group)
    grouplist+= '    <ul id="%s_list" class="GroupHeader" >\n' % dsp_group
    for plugin in splugins:
        if dsp_group == plugin[0]:
            pluginname = plugin[1][0]
            pluginctrl = displayplugin(configfile, plugin[1], lcplugins, expandAll)
            grouplist += pluginctrl
    grouplist += '</ul>\n'
    grouplist += '</li>\n'

    return grouplist


class ConfigurePluginsResource(FreevoResource):

    def _render(self, request):

        fv = HTMLResource()
        form = request.args
        fv.printHeader(_('configplugins'), 'styles/main.css', 'scripts/pluginconfig.js', selected=_('Config Plugins'))

        if not hasattr(config, 'all_plugins'):
            config.all_plugins = parse_plugins()

        configfile = fv.formValue(form, 'configfile')
        if configfile:
            if not os.path.exists(configfile):
                configfile = None
        if not configfile:
            if (not config.__dict__.has_key('CONFIG_EDIT_FILE')):
                fv.printMessages(["Unable to find local_conf.py setting CONFIG_EDIT_FILE"])
                return String (fv.res)
            else:
                configfile = config.CONFIG_EDIT_FILE

        if not os.path.exists(configfile):
            fv.res += "Error unable to find File - %s" % configfile
            return String (fv.res)

        all_plugins = config.all_plugins
        group_list = ['Global', 'tv', 'video', 'audio', 'image', 'idlebar']
        splugins = SortPlugins(all_plugins, group_list)

        # Read the settings from localconf for plugins.
        lcplugins = ReadConfigPlugins(configfile)

        expAll = fv.formValue(form, 'expAll')
        expandAll = False
        if expAll:
            expandAll = True

        fv.res += '<link rel="stylesheet" href="styles/config.css" type="text/css" />'
        fv.res  += '\n<div class="VarGroups">\n'
        fv.res += '<form action="#" class="searchform">\n'
        fv.res += '<ul class="GroupHeader">\n'

        for grp in group_list:
            fv.res += display_group(grp, splugins, configfile, lcplugins, expandAll)

        fv.res += '</ul>\n'
        fv.res += '</div>\n'
        fv.res += '</form>\n'

        return String(fv.res)

resource = ConfigurePluginsResource()
