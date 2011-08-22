# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Module for controlling a simple undecorated web browser.
# -----------------------------------------------------------------------
# $Id: youtube.py 11862 2011-08-07 11:56:13Z adam $
#
# -----------------------------------------------------------------------
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
'''
Module for controlling a simple undecorated web browser.
'''
import config

import json
import threading

from kaa.process import Process

import event
from util.httpserver import get_local_server, LongPollHandler

JSON_MIMETYPE= 'application/json'
JS_MIMETYPE = 'application/javascript'

INITIAL_HTML="""
<html>
<head>
<title>Freevo</title>
<script type="text/javascript">
window.resizeTo(%d, %d);
window.moveTo(%d,%d);
</script>
</head>
<body style="background-color: black;">
<script type="text/javascript">
window.location = "%s";
</script>
</body>
</html>
"""


IPC_JS = """
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
"""

_initial_url = None

def start_web_browser(initial_url, exit_handler=None):
    """
    Create a new instance of a web browser.
    @param initial_url: Optional initial URL to be displayed.
    """
    global _initial_url
    _initial_url = initial_url
    local_server = get_local_server()
    proxy = 'localhost:%d' % local_server.server_port
    start_url = 'http://freevo/wbinitial.html'
    browser_process = Process([config.CHROME_PATH, '--app='+start_url, '--proxy-server=' + proxy])
    if exit_handler:
        browser_process.signals['exited'].connect(exit_handler)
    browser_process.start()
    return browser_process


class WebIPC(object):
    def __init__(self, server):
        self.return_pending = False
        self.return_event = threading.Event()
        self.lphandler = LongPollHandler(JSON_MIMETYPE)
        self.server = server
        server.register_handler('^.*/freevo/ipc$', self.__ipc_handler)
        server.register_handler('^.*/freevo/ipc.js$', self.__js_handler)


    def __ipc_handler(self, request):
        if request.command == 'POST':
            self.__send_handler(request)
        if request.command == 'GET':
            self.lphandler(request)
        else:
            request.send_error(405)


    def __js_handler(self, request):
        request.send_response(200)
        request.send_header('content-type', JS_MIMETYPE)
        request.end_headers()
        request.wfile.write(IPC_JS)


    def __send_handler(self, request):
        l = int(request.headers.getheader('Content-Length'))
        s = request.rfile.read(l)
        try:
            result = None
            args = json.loads(s)
            if args['cmd'] == 'return':
                if self.return_pending:
                    self.return_pending = False
                    self.return_result = args.get('data')
                    self.return_event.set()
                else:
                    _debug_('Unexpected return!')
            elif args['cmd'] == 'event':
                event.Event('WEB_IPC', args['data']).post()
            else:
                _debug_('Unexpected ')

            if result is None:
                result = {}

            request.send_response(200)
            request.send_header('content-type', JSON_MIMETYPE)
            request.end_headers()
            json.dump(result, request.wfile)
        except:
            request.send_error(500)


    def __calljs(self, js):
        self.return_pending = True
        self.lphandler.append(json.dumps({'cmd':js}))
        self.return_event.wait()
        return self.return_result


    def __getattr__(self, item):
        return JSObject(self.__calljs, None, item)


class JSObject(object):
    def __init__(self, ipc, parent, name):
        self.ipc = ipc
        self.parent = parent
        self.name = name


    def __getattr__(self, item):
        return JSObject(self.ipc, self, item)


    def __call__(self, *args, **kwargs):
        n = self.name
        p = self.parent
        while p is not None:
            n = p.name + '.' + n
            p = p.parent
        return self.ipc('%s(%s)' % (n, json.dumps(args)[1:-1]))


def _get_initial_HTML(request):
    html =  INITIAL_HTML % (config.CONF.width, config.CONF.height, config.CONF.x, config.CONF.y, _initial_url)
    request.send_response(200)
    request.send_header('content-type', 'text/html')
    request.send_header('content-length', str(len(html)))
    request.end_headers()
    request.wfile.write(html)


get_local_server().register_handler('^http://freevo/wbinitial.html$', _get_initial_HTML)

ipc = WebIPC(get_local_server())