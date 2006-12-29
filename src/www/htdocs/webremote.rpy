#!/usr/bin/python
# -----------------------------------------------------------------------
# webremote.rpy - The main index to the web interface.
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

import util, config
import socket
from www.web_types import HTMLResource, FreevoResource

class WebRemoteResource(FreevoResource):

    def _render(self, request):
        fv   = HTMLResource()
        form = request.args

        if not (config.ENABLE_NETWORK_REMOTE == 1 and config.REMOTE_CONTROL_PORT):
           fv.res += """
             The WebRemote is currently disabled.<br/><br/>
             To enable, add the following settings to your local_conf.py file and restart freevo:<br/>
             <ul>
                <li>ENABLE_NETWORK_REMOTE = 1</li>
                <li>REMOTE_CONTROL_HOST = '127.0.0.1'</li>
                <li>REMOTE_CONTROL_PORT = 16310</li>
             </ul>
           """
           return String( fv.res )

        code = fv.formValue(form, 'code')
        if code:
           if code == 'OK':     code = 'SELECT'
           if code == 'BACK':   code = 'EXIT'
           if code == 'RIGHT>': code = 'RIGHT'
           if code == '<LEFT':  code = 'LEFT'
           if code == '<REW':   code = 'REW'
           if code == 'FFWD>':  code = 'FFWD'

           # fv.res += 'DEBUG: Send %s to freevo' % code
           host = config.REMOTE_CONTROL_HOST
           port = config.REMOTE_CONTROL_PORT
           buf  = 1024
           addr = (host,port)

           UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
           UDPSock.sendto(code, addr)
           UDPSock.close()

        fv.res += """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<head>
   <title>Freevo | WebRemote</title>
   <meta http-equiv="Content-Type" content= "text/html; charset=UTF-8"/>
   <link rel="stylesheet" href="styles/main.css" type="text/css" />
   <style>
    body  { background: #666699; }
    h3 { color: white; }
    input { width:100% }
    table { width: auto; }
    td    { padding: 1px; }
    input.remote { width: 65px; height: 20px; background: #eee; font-size: 12px; }
    input.remote:hover { background: #fed; }
   </style>
</head>

<body>

<script language="JavaScript">
<!--
   window.resizeTo(240,500)
   window.toolbar.visible     = false
   window.statusbar.visible   = false
   window.scrollbars.visible  = false
   window.personalbar.visible = false
-->
</script>

<center>
<h3>Freevo WebRemote</h3>

<form name="remote" action="webremote.rpy" method="post">
<table border="0" cellspacing="1" cellpadding="0">

<tr><td>&nbsp;</td>
    <td><input class="remote" type=submit name="code" value="UP"></td>
    <td>&nbsp;</td>
</tr>
<tr><td><input class="remote" type=submit name="code" value="<LEFT"  class="remote"></td>
    <td><input class="remote" type=submit name="code" value="OK"     class="remote"></td>
    <td><input class="remote" type=submit name="code" value="RIGHT>" class="remote"></td>
</tr>
<tr><td>&nbsp;</td>
    <td><input class="remote" type=submit name="code" value="DOWN"   class="remote"></td>
    <td>&nbsp;</td>
</tr>

<tr style="line-height: 8px;"><td colspan=3>&nbsp</td></tr>

<tr><td><input class="remote" type=submit name="code" value="BACK"></td>
    <td><input class="remote" type=submit name="code" value="DISPLAY"></td>
    <td><input class="remote" type=submit name="code" value="MENU"></td>
</tr>

<tr style="line-height: 8px;"><td colspan=3>&nbsp</td></tr>

<tr><td>&nbsp;</td>
    <td><input class="remote" type=submit name="code" value="PLAY"></td>
    <td>&nbsp;</td>
</tr>
<tr><td><input class="remote" type=submit name="code" value="<REW"></td>
    <td><input class="remote" type=submit name="code" value="PAUSE"></td>
    <td><input class="remote" type=submit name="code" value="FFWD>"></td>
</tr>
<tr><td>&nbsp;</td>
    <td><input class="remote" type=submit name="code" value="REC" style="color:red"></td>
    <td>&nbsp;</td>
</tr>

<tr style="line-height: 8px;"><td colspan=3>&nbsp</td></tr>

<tr><td><input class="remote" type=submit name="code" value="VOL+"></td>
    <td><input class="remote" type=submit name="code" value="MUTE"></td>
    <td><input class="remote" type=submit name="code" value="CH+"></td>
</tr>
<tr><td><input class="remote" type=submit name="code" value="VOL-"></td>
    <td>&nbsp;</td>
    <td><input class="remote" type=submit name="code" value="CH-"></td>
</tr>

</table>
</form>
</center>
</html>
        """

        return String( fv.res )

resource = WebRemoteResource()
