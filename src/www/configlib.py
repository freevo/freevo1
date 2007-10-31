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
from www.web_types import HTMLResource, FreevoResource
import util
from plugin import is_active, activate, remove

from helpers.plugins import parse_plugins
from helpers.plugins import html_info
import os

TRUE = 1
FALSE = 0

def getpid(name, arg):
    """
    get pid of running 'name'
    """
    for fname in ('/var/run/' + name  + '-%s.pid' % os.getuid(),
                  '/tmp/' + name + '-%s.pid' % os.getuid()):
        if os.path.isfile(fname):
            f = open(fname)
            try:
                pid = int(f.readline()[:-1])
            except ValueError:
                # file does not contain a number
                return fname, 0
            f.close()

            proc = '/proc/' + str(pid) + '/cmdline'
            # FIXME: BSD support missing here
            try:
                if os.path.isfile(proc):
                    f = open(proc)
                    proc_arg = f.readline().split('\0')[:-1]
                    f.close()
                else:
                    # process not running
                    return fname, 0

            except (OSError, IOError):
                # running, but not freevo (because not mine)
                return fname, 0

            if '-OO' in proc_arg:
                proc_arg.remove('-OO')

            if proc_arg and ((arg[0].find('runapp') == -1 and \
                len(proc_arg)>2 and arg[1] != proc_arg[1]) or \
                len(proc_arg)>3 and arg[2] != proc_arg[2]):
                # different proc I guess
                try:
                    os.unlink(fname)
                except OSError:
                    pass
                return fname, 0
            return fname, pid
    return fname, 0


def GetConfigFileName(config_file_name):
    '''
    '''
    _debug_('GetConfigFileName(config_file_name=%r)' % config_file_name , 2)

    print 'CALLING CONFIGFILENAME !!!!!!!!!'
    if not config_file_name:
        if (not config.__dict__.has_key('CONFIG_EDIT_FILE')):
            return None

        else:
            config_file_name = config.CONFIG_EDIT_FILE

    if not os.path.exists(config_file_name):
        config_file_name = None

    config_file_name = '/home/dlocke/.freevo/local_conf.py'
    print config_file_name
    return config_file_name
    
    
def CheckSyntax(fvsetting):
    '''
    '''
    _debug_('CheckSyntax(fvsetting=%r)' % ( fvsetting ), 2)

    status = False
    try :
        exec fvsetting
        status = True
    except :
        status = False
    return status


def CreateSelectBoxControl(cname, grps, cvalue, opts=""):
    '''
    '''
    _debug_('CreateSelectBoxControl(cname, grps, cvalue, opts="")', 2)
    ctrl = '<select name="%s" value="%s"  id="%s" %s >\n' % (cname,  cvalue, cname, opts)
    for grp in grps:
        if grp == cvalue:
            ctrl  += '    <option value="%s" selected="yes">%s</option>\n' % (grp, grp)
        else:
            ctrl  += '    <option value="%s">%s</option>\n' % (grp, grp)
    ctrl += '</select>\n'
    return ctrl


def CreateHTMLinput(control_type, control_id, control_value, size = '',other_opts = ''):
    '''
    '''
    _debug_('CreateHTMLinput(control_type=%r, control_id=%r, value=%r, control_size=%r, other_opts=%r)' % \
            (control_type, control_id, control_value, size, other_opts ), 2)

    html_input = '<input '
    html_input += 'type = "%s" ' % control_type
    html_input += 'id = "%s" ' % control_id
    html_input += 'value = "%s" ' % control_value
    html_input += 'size = "%s" ' % size
    html_input += ' ' +  other_opts
    html_input += '>\n'

    return html_input


def ReadConfig(cfile):
    '''
    '''
    _debug_('ReadConfig(cfile=%r)' % (cfile), 2)
    lconf = cfile
    lconf_hld = open(lconf, 'r')
    fconf = lconf_hld.readlines()
    lconf_hld.close
    return fconf


def CreateSelectBoxControl(cname, grps, cvalue, opts=""):
    '''
    '''
    _debug_('CreateSelectBoxControl(cname, grps, cvalue, opts="")', 2)
    ctrl = '<select name="%s" value="%s"  id="%s" %s >\n' % (cname,  cvalue, cname, opts)
    for grp in grps:
        if grp == cvalue:
            ctrl  += '    <option value="%s" selected="yes">%s</option>\n' % (grp, grp)
        else:
            ctrl  += '    <option value="%s">%s</option>\n' % (grp, grp)
    ctrl += '</select>\n'
    return ctrl

    
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

def Server_Running(server):
    python = ['python']
    #FIXME: should detect 
    proc = [ os.path.join('/usr/lib/python2.5/site-packages/freevo/', 'helpers', server + '.py') ]
    
    if getpid(server, python + proc)[1]:
       return True
    return False


def CreateNewLineControl():
    '''
    '''
    _debug_('CreateNewLineControl()', 2)
    ctrl = '<div align="left">'
    ctrl += '<input  id="newname" name="newname" size="4"> ='
    ctrl += '<input  id="newvalue" name="newvalue" size="40">'
    ctrl += '<input type="button" onclick="AddNewLine()" value="New Setting">'
    ctrl += '<br><br>\n'
    ctrl += '</div>'
    return ctrl
    
    
def Display_Server(server):
    dserver = '<div id="%s_config_line">' % server
    dserver += '<li class="ServerList">'

    # Check to see if the server is running.
    if Server_Running(server):
        dserver += '<a class="PluginStatusActive" >Active</a>'
        js_onclick = 'onclick=ServerUpdate("%s","stop","%s")' % ( server, server )
        dserver += '<a class= "btnServer" %s >Stop</a>'  % js_onclick
    else:
       dserver += '<a class="PluginStatusDeactive">Deactive</a>'
       js_onclick = 'onclick=ServerUpdate("%s","start","%s")' % ( server, server ) 
       dserver += '<a class= "btnServer" %s >Start</a>' % js_onclick 
    dserver += server 
    dserver += '</div>'
    dserver += '</li>'

    return dserver

def Display_Helper(helper):
    dhelper = '<div id="%s_config_line">' % helper
    dhelper += '<li class="ServerList">'

    # Check to see if the server is running.
    print "SERVER RUNNING ???"
    print Server_Running(helper)
    if Server_Running(helper):
        print "SERVER RUNING !!!"
        dhelper += '<a class="PluginStatusDeactive" >Running</a>'
    else:
        js_onclick = 'onclick=StartHelper("%s","%s")' % ( helper, helper ) 
        dhelper += '<a class="PluginStatusActive" %s>Start</a>' % js_onclick

    dhelper += helper
    dhelper += '</div>'
    dhelper += '</li>'

    return dhelper




