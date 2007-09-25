#!/usr/bin/python
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

from www.web_types import HTMLResource, FreevoResource

def ReadConfig():
    lconf = config.CONFIG_EDIT_FILE
    lconf_hld = open(lconf,"r")
    fconf = lconf_hld.readlines()
    return fconf

def WriteConfigFile(filename,conf):
    cfile = open(filename,"w")
    for ln in conf:
        cfile.write(ln)
    cfile.close

def UpdateConfig(varName,varValue,varEnable,sline,eline):
    fconf = ReadConfig()
    cred = '#FF0000'
    cgreen = '#00FF00'
    color = cred
    status = 'NOT Updated, Error'
    blOK = False

    newline = varName + " = " + varValue
    # Check the syntax of the new line.
    if CheckSyntax(newline):
        blOK = True
        color = cgreen
        status = "Updated"

    if not blOK and varEnable == "FALSE":
        blOK = True
        color = cred
        status = "Updated, Error if Enabled"

    if FileTypeVar(varName) and blOK:
        if os.path.exists(varValue):
            color = cred
            status = "Updated, Missing File"
        else:
            color = cgreen
            status = "Updated"

    if varEnable == "FALSE":
        newline = "# " + newline

    reload = False
    fconf[sline] = newline + '\n'
    if sline < eline:
        cline = sline + 1
        while cline <= eline:
            fconf.pop(cline)
            cline += 1
            reload = True
            color = cred
            status = "RELOAD PAGE"

    if blOK:
         WriteConfigFile(config.CONFIG_EDIT_FILE,fconf)

    results = '<font color="%s">%s</font>' % (color , status)
    return results

def DeleteLines(startline,endline):
    rconf = ReadConfig()
    
    dellines = "<ul>"
    for dline in range(startline, endline+1):
        rline = rconf.pop(startline)
        rline = rline.replace("<","&lt;")
        rline = rline.replace(">","&gt;")
        dellines += "<li>%s</li>" % rline
    dellines += "</ul>"

    WriteConfigFile(config.CONFIG_EDIT_FILE,rconf)
    return dellines

def CheckSyntax(fvsetting):
    status = False
    try :
        exec fvsetting
        status = True
    except :
        status = False
    return status

def GetItemsArray(cvalue):
    itemlist = ""
    cmd = 'itemlist = ' + cvalue
    if CheckSyntax(cmd):
        exec cmd
    return itemlist
    
def GetGroupList(cfgvars):
    grps = []
    for vrs in cfgvars:
        grp = vrs['group']
        if not grp in grps:
            grps.append(grp)
    grps.sort()
    return grps

def NewLineControl():
    ctrl = ""
    ctrl += '<input  id="newname" name="newname" size="40"> ='
    ctrl += '<input  id="newvalue" name="newvalue" size="40">'
    ctrl += '<input type="button" onclick="FilterList(\'filterlist\')" value="New Setting"><br><br>\n'
    return ctrl


def ParseList(cname,cvalue):
    itemlistsvars = ["VIDEO_ITEMS","AUDIO_ITEMS","IMAGE_ITEMS","GAME_ITEMS","PERSONAL_WWW_PAGE"]

    elemsep = ","
    if cname in itemlistsvars:
        elemsep = ")"
    rows = cvalue.count(elemsep) + 1
    if rows > 5:
        rows = 5
    cvalue = cvalue.replace(elemsep,elemsep + "\n")
    ctrl = '<textarea  id= "%s_tb" rows = %s cols=55 wrap="SOFT" name=%s_tb>%s</textarea>'  % (cname, str(rows),cname,cvalue)
    return ctrl    
   
def CreateFilterControl(grps,cvalue):
    ctrl = '\n<select name="filterlist" value="%s"  id="filterlist">' % cvalue
    ctrl += '\n    <option value="All">All</option>'
    for grp in grps:
        if grp == cvalue:
            ctrl  += '\n    <option value="%s" selected="yes">%s</option>' % (grp , grp)
        else:
            ctrl  += '\n    <option value="%s">%s</option>' % (grp,grp)
    ctrl += '\n</select>'
    ctrl += '<input type="button" onclick="FilterList(\'filterlist\')" value="Apply Fiilter"><br><br>\n'
    return ctrl

def ParseConfigFile(rconf):
     cnt = 0
     fconfig = []
     while cnt < len(rconf):
           startline = cnt
           ln = rconf[cnt]
           if ln.find("[") <> -1:
              if ln.find("]") <> -1:
                  fln = ln  
              else:
                  fln = ln
                  while ln.find("]") == -1:
                     cnt += 1
                     ln = rconf[cnt]
                     ln = ln.strip("#")
                     ln = ln.strip()
                     fln += ln
           
           elif ln.find("{") <> -1:
              if ln.find("}") <> -1:
                  fln = ln  
              else:
                  fln = ln
                  while ln.find("}") == -1:
                     cnt += 1
                     ln = rconf[cnt]
                     ln = ln.strip("#")
                     ln = ln.strip()
                     fln += ln
                  fln = fln.replace("\n","")
           else:
               fln = ln
           pln = ParseLine(fln)
           if pln['type']:
               pln['startline'] = startline
               pln['endline'] = cnt
               fconfig.append(pln)
           cnt += 1
     fconfig.sort()
     return fconfig

def CreatePluginControl(nctrl):
    htmlctrl = HTMLResource()
    htmlctrl.tableRowOpen('class="chanrow"')
   
    checked = "Deactivated"
    btnName = "Activate"
    if nctrl['checked']:
        checked = "Activated"
        btnName = "Deactivate"

    cname = "'" + nctrl['ctrlname'] + "'"
    chkbox = ""
    htmlctrl.tableCell('<input type="button" onclick="SaveValue(' + cname + ')" value="' + btnName + '">\n','')
    htmlctrl.tableCell('<input type="button" onclick="DeleteLines(' + cname + ')" value="Delete">\n','')

#    chkbox += '<a href="config.rpy?delete=TRUE&startline=' + str(nctrl['startline']) + '&endline=' + str(nctrl['endline']) + '">delete</a>'
    chkbox += '<input type="hidden" id="' + nctrl['ctrlname'] + '_startline" value="' + str(nctrl['startline']) + '">\n'
    chkbox += checked + '\n'

    htmlctrl.tableCell(chkbox,'')
    htmlctrl.tableCell(nctrl['ctrlname'],'align="right"')
          
    if nctrl['level']:
       inputbox = '<input name="LEVEL' + nctrl['ctrlname'] + '" size="2" value="' + nctrl['level'] + '">'
       htmlctrl.tableCell(inputbox,'align="right"')
         
    htmlctrl.tableRowClose()
    return htmlctrl.res

def CreateControl(nctrl):
    htmlctrl = HTMLResource()
    htmlctrl.tableRowOpen('class="chanrow"')
   
    checked = ""
    if nctrl['checked']:
        checked = "checked"

    cname = "'" + nctrl['ctrlname'] + "'"
    chkbox = ""
    htmlctrl.tableCell('<input type="button" onclick="SaveValue(' + cname + ')" value="Update">\n','')
    delbtn = '<input type="button" onclick="DeleteLines(%f,%f)" value="Delete">\n' % ( nctrl['startline'],nctrl['endline'] )
    htmlctrl.tableCell( delbtn ,'')
    #htmlctrl.tableCell('<a href="config.rpy?delete=TRUE&startline=' + str(nctrl['startline']) + '&endline=' + str(nctrl['endline']) + '">delete</a>','')
    chkbox += '<input type="hidden" id="' + nctrl['ctrlname'] + '_startline" value="' + str(nctrl['startline']) + '">\n'
    chkbox += '<input type="hidden" id="' + nctrl['ctrlname'] + '_endline" value="' + str(nctrl['endline']) + '">\n'
    chkbox += '<input type="checkbox" id = "' + nctrl['ctrlname'] + '_chk" name="Enable' + nctrl['ctrlname'] + '"value="" ' + checked + '>\n'

    htmlctrl.tableCell(chkbox,'')
    htmlctrl.tableCell(nctrl['ctrlname'],'align="right"')
          
    if nctrl['type'] == "textbox":
       inputbox = CreateTextBox(nctrl['ctrlvalue'],nctrl['ctrlname'],nctrl['vartype'])
       htmlctrl.tableCell(inputbox,'colspan="1" align="left"')

    chkline = nctrl['ctrlname'] + " = " + nctrl['ctrlvalue']
    
    lcheck = '<font color="#00FF00">OK</font>'
    if not CheckSyntax(chkline):
        lcheck = '<font color="#FF0000">Error</font>'

    else:
        if FileTypeVar(nctrl['ctrlname']):
            filename = nctrl['ctrlvalue'].replace("'","").strip()
            if not os.path.exists(filename):
                lcheck = '<font color="#FF0000">Missing File - ' + filename + '</font>'
    
    check = '<div id="%s_check">%s</div>' % (nctrl['ctrlname'],lcheck)
    opts = 'align="left" id="' + nctrl['ctrlname'] + '_check"'
    htmlctrl.tableCell(lcheck,opts)
    htmlctrl.tableCell(nctrl['comments'],'align="left"')
    htmlctrl.tableRowClose()
    return htmlctrl.res


def CreateBooleanControl(cname,cvalue):
    ctrl = '<select id = "%s_tb" name="%s_tb" value="">' % ( cname , cname )
    if cvalue.startswith("True"):
         ctrl  += '\n    <option value="True" selected="yes">True</option>'
         ctrl  += '\n    <option value="False">False</option>'
    else:
         ctrl  += '\n    <option value="True" >True</option>'
         ctrl  += '\n    <option value="False" selected="yes">False</option>'
    ctrl  += '</select>'
    return ctrl

def CreateTextBox(cvalue,cname,vtype):
    cvalue = cvalue.replace(" ","")
    cvalue = cvalue.strip()

    cid = cname + "_tb"
    ctrl = "ERROR!!!"
    if vtype == "boolean":
         ctrl = CreateBooleanControl(cname,cvalue)
    elif vtype == "list":
         ctrl = ParseList(cname,cvalue)
    else:
        tbsize = "45"
        if vtype == "number":
            tbsize = "5"
        ctrl = '<input  id="%s" name="%s_tb" size="%s" value="%s">' % (cid , cname , tbsize , cvalue)
    return ctrl

def isNumber(s):
    try:
      i = int(s)
      return True
    except ValueError:
      return False

    
def FileTypeVarArray(cname):
    filevars = ['VIDEO_ITEMS','AUDIO_ITEMS','IMAGE_ITEMS','GAME_ITEMS']
       
    if cname in filevars:
       return True
    return False
    
def FileTypeVar(cname):
    vtype = cname.split("_")[-1]
    filetypes = ['PATH','DIR','FILE','DEV','DEVICE']
    filevars = ['XMLTV_GRABBER','RSS_AUDIO','RSS_VIDEO','RSS_FEEDS','XMLTV_SORT','LIRCRC']
    
    if vtype in filetypes:
       return True     
    if cname in filevars:
       return True
    return False    

def ParsePlugin(lparsed,cline):
     lparsed['type'] = "plugin"
     tsplit = cline.split("'")
     if len(tsplit) > 2:
         lparsed['ctrlname'] = tsplit[1].strip()
     else:
         lparsed['ctrlname'] = tsplit[0].strip()
     lparsed['group'] = lparsed['ctrlname'].split(".")[0].upper()
            
     if cline.find("level=") <> -1 or cline.find('level =') <> -1:
         cline=cline.replace(" ","")
         plevel = cline[cline.find("level=")+6:cline.find("level=")+9]
         plevel = plevel.replace(")","")
         plevel = plevel.replace(",","")
         lparsed['level'] = plevel
     else:
         lparsed['level'] = "00"
            
     if cline.startswith('plugin.remove'):
         lparsed['checked'] = False
     ctrlvalue = cline.split("#")
     if len(ctrlvalue) == 2:
         lparsed['comments'] = ctrlvalue[1]
     lparsed['comments'] = cline
     return lparsed   
    

def VarType(cvalue):
    if cvalue.startswith("'") and cvalue.endswith("'"):
        return "string"
    if isNumber(cvalue):
        return "number"
    if cvalue.startswith("[") and cvalue.endswith("]"):
        return "list"
    if cvalue.startswith("(") and cvalue.endswith(")"):
        return "list"
    if cvalue.startswith("{") and cvalue.endswith("}"):
        return "list"
    if cvalue.startswith("True") or cvalue.startswith("False"):         
        return 'boolean'
    return "Unknow"
        
    
def ParseLine(cline):
    lparsed = {'ctrlname': '',
               'ctrlvalue': '' ,
               'checked': True ,
               'type' : '',
               'comments' : '',
               'level':'',
               'group' :'',
               'startline':'',
               'endline':'',
               'fileline':cline,
               'vartype':''}
    
    tln = cline.strip()
    tln = tln.replace("\n","")
    if tln.startswith("#"):
        lparsed['checked'] = False
        tln = tln.lstrip("#")
        tln = tln.lstrip()
        
    if tln.startswith('plugin'):
        return lparsed
        
    if len(tln) > 1:
        fsplit = tln.split("=")
        if len(fsplit) == 2:
            lparsed['type'] = "textbox"
            lparsed['ctrlname'] = fsplit[0].strip()
            lparsed['group'] = lparsed['ctrlname'].split("_")[0]
            if not lparsed['ctrlname'].isupper():
               lparsed['type'] = ''
            if (not config.__dict__.has_key(lparsed['ctrlname'])):
               try:
                   fvvalue = eval('config.' + lparsed['ctrlname'])
               except Exception, e:
                   fvvalue = ""
                   
            ctrlvalue = fsplit[1].split("#")
            if len(ctrlvalue) == 2:
                 lparsed['comments'] = ctrlvalue[1]
            lparsed['ctrlvalue'] = ctrlvalue[0].strip()
    lparsed['vartype'] = VarType(lparsed['ctrlvalue'])

    if lparsed['ctrlname'].startswith('"'):
        lparsed['type'] = ""
    return lparsed

def DisplaySettings(fconfig,filterlist):
     fv = HTMLResource()

     fv.tableOpen('class="library" id="filelist"')
     fv.tableRowOpen('class="chanrow"')
     fv.tableCell('','class ="guidehead"  colspan="2"')
#     fv.tableCell('','class ="guidehead"  colspan="1"')
     fv.tableCell('Enable','class ="guidehead"  colspan="1"')
     fv.tableCell('Name','class ="guidehead"  colspan="1"')
     fv.tableCell('Value','class ="guidehead"  colspan="1"')
     fv.tableCell('Comments','class ="guidehead"  colspan="1"')
     fv.tableRowClose()

     for cctrl in fconfig:
          if cctrl['type'] == "textbox":
              if filterlist and filterlist <> "All":
                  if cctrl['group'] == filterlist:
                      fv.res += CreateControl(cctrl)
              else:
                 fv.res += CreateControl(cctrl)

     fv.tableClose()
     return fv.res

class ConfigResource(FreevoResource):
    
    def _render(self, request):
         fv = HTMLResource()
         form = request.args
       
         fv.printHeader(_('Config'), 'styles/main.css','scripts/config.js',selected=_('Config'))

         if (not config.__dict__.has_key('CONFIG_EDIT_FILE')):
             fv.printMessages(["Unable to find local_conf.py setting CONFIG_EDIT_FILE"])
             return String ( fv.res )

         if not os.path.exists(config.CONFIG_EDIT_FILE):
             fv.printMessages(["Unable to find file - " + config.CONFIG_EDIT_FILE])
             return String ( fv.res )

         update = fv.formValue(form,"update")
         if update:            
             udname = fv.formValue(form,"udname")
             udenable = fv.formValue(form,"udenable")
             udvalue = fv.formValue(form,"udvalue")
             startline = fv.formValue(form,"startline")
             endline = fv.formValue(form,"endline")
             fv.res = UpdateConfig(udname,udvalue,udenable,int(startline),int(endline))
             return String( fv.res )

         delete = fv.formValue(form,"delete")
         startline = fv.formValue(form,"startline")
         endline = fv.formValue(form,"endline")
         if delete == "TRUE" and startline and endline:            
             dlines = DeleteLines(int(startline),int(endline))
             fv.res += "<br><h4>The following Lines were deleted :</h4>" + dlines
             

         rconf = ReadConfig()
         fconfig = ParseConfigFile(rconf)
       
         filterlist = fv.formValue(form,"filterlist")
         groups = GetGroupList(fconfig)
         fv.res  += '\n<br><form id="Url Download" action="config.rpy" method="get">'
         fv.res  += '\n    <div class="searchform" align="left"><br>'
         fv.res += '<div align="left">'
         fv.res += CreateFilterControl(groups,filterlist)       
#         fv.res += NewLineControl()
         fv.res += '</div>'

         fv.res += DisplaySettings(fconfig,filterlist)
         fv.res += '\n    </div>'
         fv.res += '\n</form><br>\n'               
 
         return String( fv.res )

resource = ConfigResource()

