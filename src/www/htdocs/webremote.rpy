# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# webremote.rpy - Web Based Remote Control for Freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo: Graphical design to resemble a real remote control
#       Normal key presses to actviate the functions
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
            if code == 'VOLP': code = 'VOL+';
            if code == 'VOLM': code = 'VOL-';
            if code == 'CHP':  code = 'CH+';
            if code == 'CHM':  code = 'CH-';

            host = config.REMOTE_CONTROL_HOST
            port = config.REMOTE_CONTROL_PORT
            buf  = 1024
            addr = (host, port)

            UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            UDPSock.sendto(code, addr)
            UDPSock.close()
            return;

        fv.res += """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
   <title>Freevo | WebRemote</title>
   <meta http-equiv="Content-Type" content= "text/html; charset=UTF-8"/>
   <link rel="stylesheet" href="styles/main.css" type="text/css" />

   <style type="text/css" media="screen">
     body  { background: #666699; }
     h3 { color: white; }
     table { width: auto; }
     td    { padding: 1px; }
     button.remote { width: 60px; height: 30px; background: #eee; font-size: 12px; text-align: center; padding: 0; }
     button.remote:hover { background: #fed; }
   </style>

   <script type="text/javascript">
   <!--
     // Resize window
     function resizeWindow () {
       window.resizeTo(230, 495)
       window.toolbar.visible     = false
       window.statusbar.visible   = false
       window.scrollbars.visible  = false
       window.personalbar.visible = false
     }

     // AJAX Functions
     var xmlHttp = false;

     function getXMLHttpObject () {
       if (window.XMLHttpRequest) {
         xmlHttp=new XMLHttpRequest()
       }
       else if (window.ActiveXObject) {
         xmlHttp=new ActiveXObject("Microsoft.XMLHTTP")
       }
       return xmlHttp
       try {
         xmlHttp = new ActiveXObject("Msxml2.XMLHTTP");   // Internet Explorer 1st try
       } catch (e) {
         try {
           xmlHttp = new ActiveXObject("Microsoft.XMLHTTP"); // Internet Explorer 2nd try
         } catch (e2) {
           xmlHttp = false;
         }
       }
       if (!xmlHttp && typeof XMLHttpRequest != 'undefined') {
         xmlHttp = new XMLHttpRequest();                      // Mozilla, Firefox, Opera
       }
     }

     function send_code( code ) {
       if (! xmlHttp) {
         getXMLHttpObject();
       }
       var url = 'webremote.rpy?code=' + code + '&sid=' + Math.random();
       xmlHttp.open('GET', url, true);
       xmlHttp.send(null);
     }
   -->
   </script>
</head>

<body onLoad="resizeWindow();">

<center>
<h3>Freevo WebRemote</h3>

<table border="0" cellspacing="1" cellpadding="0">

<tr><td>&nbsp;</td>
    <td><button class="remote" accesskey="8" onClick="send_code('UP');"><img src="../icons/up.png"></button></td>
    <td>&nbsp;</td>
</tr>
<tr><td><button class="remote" accesskey="4" onClick="send_code('LEFT');"><img src="../icons/back.png"></button></td>
    <td><button class="remote" accesskey="5" onClick="send_code('SELECT');"><img src="../icons/button_ok.png"></button></td>
    <td><button class="remote" accesskey="6" onClick="send_code('RIGHT');"><img src="../icons/forward.png"></button></td>
</tr>
<tr><td>&nbsp;</td>
    <td><button class="remote" accesskey="2" onClick="send_code('DOWN');"><img src="../icons/down.png"></button></td>
    <td>&nbsp;</td>
</tr>

<tr style="line-height: 8px;"><td colspan="3">&nbsp;</td></tr>

<tr><td><button class="remote" accesskey="x" onClick="send_code('EXIT');"><img src="../icons/previous.png"></button></td>
    <td><button class="remote" accesskey="e" onClick="send_code('ENTER');"><img src="../icons/button_ok.png"></button></td>
    <td><button class="remote" accesskey="d" onClick="send_code('DISPLAY');"><img src="../icons/help.png"></button></td>
</tr>
<tr><td><button class="remote" accesskey="m" onClick="send_code('MENU');"><img src="../icons/player_playlist.png"></button></td>
    <td><button class="remote" accesskey="c" onClick="send_code('REC');" style="color:red">REC</button></td>
    <td><button class="remote" accesskey="j" onClick="send_code('EJECT');"><img src="../icons/player_eject.png"></button></td>
</tr>


<tr style="line-height: 8px;"><td colspan="3">&nbsp;</td></tr>

<tr><td>&nbsp;</td>
    <td><button class="remote" accesskey="p" onClick="send_code('PLAY');"><img src="../icons/player_play.png"></button></td>
    <td>&nbsp;</td>
</tr>
<tr><td><button class="remote" accesskey="r" onClick="send_code('REW');"><img src="../icons/player_rew.png"></button></td>
    <td><button class="remote" accesskey="u" onClick="send_code('PAUSE');"><img src="../icons/player_pause.png"></button></td>
    <td><button class="remote" accesskey="f" onClick="send_code('FFWD');"><img src="../icons/player_fwd.png"></button></td>
</tr>
<tr><td>&nbsp;</td>
    <td><button class="remote" accesskey="s" onClick="send_code('STOP');"><img src="../icons/player_stop.png"></button></td>
    <td>&nbsp;</td>
</tr>

<tr style="line-height: 8px;"><td colspan="3">&nbsp;</td></tr>

<tr><td><button class="remote" accesskey="+" onClick="send_code('VOLP');">VOL+</button></td>
    <td><button class="remote" accesskey="m" onClick="send_code('MUTE');"><img src="../icons/status/volume_mute.png">MUTE</button></td>
    <td><button class="remote" accesskey="c" onClick="send_code('CHP');">CH+</button></td>
</tr>
<tr><td><button class="remote" accesskey="-" onClick="send_code('VOLM');">VOL-</button></td>
    <td>&nbsp;</td>
    <td><button class="remote" accesskey="v" onClick="send_code('CHM');">CH-</button></td>
</tr>

</table>
</center>
</body>
</html>
        """

        return String( fv.res )

resource = WebRemoteResource()
