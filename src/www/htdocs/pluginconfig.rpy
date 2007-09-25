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
from plugin import is_active
from helpers.plugins import parse_plugins
from helpers.plugins import info_html

TRUE = 1
FALSE = 0

def ReadConfig():
    lconf = config.CONFIG_EDIT_FILE
    lconf_hld = open(lconf,"r")
    fconf = lconf_hld.readlines()
    lconf_hld.close
    return fconf

def WriteConfigFile(filename,conf):
    cfile = open(filename,"w")
    for ln in conf:
        cfile.write(ln)
    cfile.close

def UpdatePlugin(pcmd,pname,pline):
    lconf = ReadConfig()

    # Check to see if a line exists all ready.
    status = "ERROR"
    print pline
    pline = int(pline)

    if pline == -1:
        lconf.append("")
        pline = len(lconf) - 1

    if pline <> -1:
       lcline = lconf[pline]
       if pcmd == "Disabled":
           nline = "# plugin.activate('%s') \n" % pname
           status =  "DISABLE Plugin " + pname + "\n" + nline
           lconf[pline] = nline
           WriteConfigFile(config.CONFIG_EDIT_FILE,lconf)

       elif pcmd == "REMOVE":
           nline = "plugin.remove('%s')\n" % pname
           status =  "REMOVE Plugin " + pname + "\n" + nline
           lconf[pline] = nline
           WriteConfigFile(config.CONFIG_EDIT_FILE,lconf)

       elif pcmd == "Enabled":
           nline = "plugin.activate('%s')\n" % pname
           status =  "ACTIVATE Plugin " + pname + "\n" + nline
           lconf[pline] = nline
           WriteConfigFile(config.CONFIG_EDIT_FILE,lconf)

       elif pcmd == "DELETE":
           status = "ACTIVATE Plugin " + pname

    return status
   
def ParsePluginName(line):
    sline = line.split("'")
    if len(sline) > 2:
        pname = sline[1]
    else:
        pname = "error"
    return pname

def GetConfigSetting(vname):
    lconf = ReadConfig()
    print "Search for Congin Setting = %s" % vname
    ret = ""
    for ln in lconf:
        ln = ln.strip("#")
        ln = ln.strip()
        if ln.startswith(vname):
           print "LINE FOUND"
           sln = ln.split("=")
           print sln
           if len(sln) > 1:
              ret = sln[1].split("#")[0]
    return ret
           
def ReadConfigPlugins():
    rconf = ReadConfig()
    pluginlines = []
    cnt = 0
    while cnt < len(rconf):
        pline = {'name':'','lineno':0,'orgline':'','enabled':False,'removed':False}
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

def GetPlugConfig(pname,all_plugins):
    config_list = []
    for p in all_plugins:
        if p[0] == pname:
           if p[5].find('config') > 0:
               exec (p[5])
               config_list = return_config()
    return config_list
    
def CreateListBox(cname,grps,cvalue,opts):
    ctrl = '\n<select name="%s" value=""  id="%s" %s>' % ( cname , cname, opts )
    for grp in grps:
        if grp == cvalue:
            ctrl  += '\n    <option value="' + grp + '" selected="yes">' + grp + '</option>'
        else:
            ctrl  += '\n    <option value="' + grp + '">' + grp + '</option>'
    ctrl += '\n</select>'
    return ctrl

def displayplugin(plugin,group,pfilter,lconf,plugins_all):
    html = HTMLResource()
   
    pluginname = plugin[0]
    for e in plugin:
        if e.find("level") <> -1:
            level = "30" 

    status = "Deactive"
    btnlabel = "Disabled"
    jscmd = "EnablePlugin"
    if is_active(plugin[0]):
        status = "Active"
        btnlabel = "Enabled"
        jscmd = "DisablePlugin"
        
    # check tos ee fi the plugin has a line in localconf
    lconfline = "No local_conf.py entry"
    confentry = False
    linenumber = -1
    for lnum , lcline in enumerate(lconf):
        if  lcline['name'] == plugin[0]:
            lconfline = lcline['orgline']
            linenumber = lcline['lineno']
            confentry = True
    level = "N/A"
    
    if is_active(plugin[0]) and not confentry:
         status = "Active"
         btnlabel = "Enabled"
         jscmd = "RemovePlugin"

    if lconfline.startswith("plugin.remove"):
         status = "Removed"
         btnlabel = "Removed"
         jscmd = "EnablePlugin"
  
    cmds = ["Enabled","Disabled","Removed"]
    jsupdate = 'onchange="UpdatePlugin(\'%s\')"' % pluginname
    btns = CreateListBox(pluginname + "_cmd",cmds,btnlabel,jsupdate)
    btns += '<input type="hidden" id="%s_lineno" value="%i">\n' % ( pluginname , linenumber )

    if pfilter == "(All)" or status == pfilter:
        html.tableRowOpen()
        html.tableCell(group)
        html.tableCell(btns)
        html.tableCell(status)
        html.tableCell(plugin[0],'align="left"')
        html.tableCell(lconfline,'align="left"')
        html.tableRowClose()

        clist = GetPlugConfig(plugin[0],plugins_all)
        for vr in clist:
            html.tableRowOpen()
            html.tableCell("")
            html.tableCell("")
            html.tableCell(vr[0],'align="Right"')
            curvalue = GetConfigSetting(vr[0])
            print "CURRENT VALUE = %s" % curvalue
            html.tableCell('<input type="textbox" value="%s">'  % curvalue ,'align="Left"')
            html.tableCell(vr[2],'align="Left"')
            html.tableRowClose()

    return html.res
    
class ConfigurePluginsResource(FreevoResource):

    def _render(self, request):

        fv = HTMLResource()
        form = request.args
        if not hasattr(config, 'all_plugins'):
            config.all_plugins = parse_plugins()

        all_plugins = config.all_plugins
        special_plugins = ['tv', 'video', 'audio', 'image', 'idlebar']
        plugincontrol = ['Active','Remove','Delete']

        cmd = fv.formValue(form,"cmd")
        pluginname = fv.formValue(form,"pluginname")
        pluginline = fv.formValue(form,"pluginline")
        if cmd and pluginname and pluginline:
            print "PLUGIN COMMAND -  " + cmd
            fv.res = UpdatePlugin(cmd,pluginname,pluginline)
            return String( fv.res )

        fv.printHeader(_('configplugins'), 'styles/main.css','scripts/pluginconfig.js',selected=_('Plugins'))
        #fv.tableBodyOpen()
        fv.res  += '\n<div class="searchform" align="left"><br>'
        fv.res  += '\n<br><form id="Url Download" action="pluginconfig.rpy" method="get">'
        fv.res += '<br>'
        
        filterlist = special_plugins
        filterlist.insert(0,"Global")
        filterlist.insert(0,"(All)")
        
        # Read the settings from localconf for plugins.
        lcplugins = ReadConfigPlugins()

        pluginfilter = fv.formValue(form, 'pluginfilter')
        if not pluginfilter:
            pluginfilter = "(All)"
        
        filter = fv.formValue(form, 'filterlist')
        if not filter:
            filter = "(All)"
            
        fv.tableOpen()
        fv.tableRowOpen('class="chanrow"')
        jsfilter = 'onchange="FilterListPlugin()"'
        filterboxes =CreateListBox('grpfilter',filterlist,filter,jsfilter)
        fb = ['(All)','Active','Deactive']
        filterboxes += CreateListBox('statfilter', fb  ,pluginfilter,jsfilter)
        fv.tableCell(filterboxes,'class ="guidehead"  colspan="2"')
        fv.tableCell("Status",'class ="guidehead"  colspan="1"')
        fv.tableCell("Plugin",'class ="guidehead"  colspan="1" align="left"')
        fv.tableCell('Comments','class ="guidehead"  colspan="1" align="left"')
        fv.tableRowClose()

        grp = "Global"
        fv.tableRowOpen()
        if filter == "(All)" or filter == "Global":
            for p in all_plugins:
                if not p[0][:p[0].find('.')] in special_plugins:
                    fv.res += displayplugin(p,grp,pluginfilter,lcplugins,all_plugins)
                    grp = ""

        if filter == "(All)":
            for type in special_plugins:
                grp = type
                for p in all_plugins:
                    if p[0][:p[0].find('.')] == type:
                        fv.res += displayplugin(p,grp,pluginfilter,lcplugins,all_plugins)
                        grp = ""
                        
        else:
            grp = filter
            for p in all_plugins:    
                        if p[0][:p[0].find('.')] == filter:
                            fv.res += displayplugin(p,grp,pluginfilter,lcplugins,all_plugins)
                            grp = ""

        fv.tableClose()
        fv.res += '</form>'
        fv.res += '</div>\n'
        fv.res += '<br><br>'
        fv.tableBodyClose()

        fv.printLinks(request.path.count('/')-1)
        fv.printFooter()



        return String( fv.res )

resource = ConfigurePluginsResource()
