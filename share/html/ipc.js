/*
# -----------------------------------------------------------------------
# Module for communication between web browser and freevo
# -----------------------------------------------------------------------
# $Id: youtube.py 11862 2011-08-07 11:56:13Z adam $
# -----------------------------------------------------------------------
#
#
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
*/

function sendEvent(event, data){
    send('event', {'event':event, 'data':data});
}

function send(cmd, data){
    var args = { 'cmd': cmd, 'data': data};
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/freevo/ipc', true);
    xhr.send(JSON.stringify(args));
}

function poll(){
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/freevo/ipc', true);
    xhr.timeout = 50000;
    xhr.onreadystatechange = function () {
        if ((this.readyState == 3 || this.readyState == 4) && this.status == 200) {
            var args = JSON.parse(this.responseText);
            var r = eval(args['cmd']);
            send('return', r);
            poll();
        }
    };
    xhr.ontimeout = poll;
    xhr.send();
}

window.onload = poll;
