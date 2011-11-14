# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Local HTTP Server
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
import logging
logger = logging.getLogger("freevo.util.httpserver")

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn

import Queue
import re
import select
import socket
import threading
import traceback
import urlparse

_local_server_singleton = None

def get_local_server():
    global _local_server_singleton
    if _local_server_singleton is None:
        _local_server_singleton = LocalServer()
    return _local_server_singleton

class LocalServer(ThreadingMixIn, HTTPServer):
    """
    Class to server files/data over http the to localhost only.
    """
    def __init__(self):
        HTTPServer.__init__(self, ('localhost', 0), RegExRequestHandler)
        self.base_url = 'http://localhost:%d' % self.server_port
        self.handlers = []
        self.register_handler('^http://.*$', proxy_handler)
        self.stop = False
        thread = threading.Thread(target=self.serve_forever)
        thread.setDaemon(True)
        thread.start()


    def serve_forever(self):
        """
        Start HTTP server and wait for connections.
        """
        while not self.stop:
            try:
                self.handle_request()
            except:
                traceback.print_exc()


    def shutdown(self):
        """Shutdown the local HTTP server.
        """
        self.stop = True
        self.socket.close()


    def register_handler(self, regex, handler):
        """Register a handler callback for the specifed regular expression object.
        The handler will be called with the BaseHTTPRequestHandler object and the match object from the regular
        expression.
        """
        self.handlers.insert(0, (re.compile(regex), handler))


    def unregister_handler(self, regex):
        """Unregister the specified regular expression handler.
        """
        for i in range(0,self.handlers):
            if self.handers[i][0].pattern == regex:
                del self.handlers[i]
                break


    def get_url(self, path):
        """Returns the URL on the local server for the specified path.
        """
        return self.base_url + path

#
# Following code copied from TinyHTTPProxy
#
def proxy_handler(request):
    (scm, netloc, path, params, query, fragment) = urlparse.urlparse(
        request.path, 'http')
    if scm!='http' or fragment or not netloc:
        request.send_error(400, "bad url %s" % request.path)
        return
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if request.connect_to(netloc, soc):
            soc.send("%s %s %s\r\n" % (request.command,
                                       urlparse.urlunparse(('', '', path,
                                                            params, query,
                                                            '')),
                                       request.request_version))
            request.headers['Connection'] = 'close'
            del request.headers['Proxy-Connection']
            for key_val in request.headers.items():
                soc.send("%s: %s\r\n" % key_val)
            soc.send("\r\n")
            request.read_write(soc)
    finally:
        soc.close()
        request.connection.close()



class RegExRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request handler that matches regular expressions to handler callbacks.
    """
    def do_GET(self):
        if self.path.startswith(self.server.base_url):
            self.path = self.path[len(self.server.base_url):]
        handled = False
        for regex, handler in self.server.handlers:
            m = regex.match(self.path)
            if m:
                handled = True
                try:
                    handler(self, *m.groups())
                except:
                    traceback.print_exc()
                break

        if not handled:
            self.send_error(404)

    do_HEAD   = do_GET
    do_POST   = do_GET
    do_PUT    = do_GET
    do_DELETE = do_GET


    def connect_to(self, netloc, soc):
        i = netloc.find(':')
        if i >= 0:
            host_port = netloc[:i], int(netloc[i+1:])
        else:
            host_port = netloc, 80

        try:
            soc.connect(host_port)
        except socket.error, arg:
            try:
                msg = arg[1]
            except:
                msg = arg
            self.send_error(404, msg)
            return 0
        return 1

    def read_write(self, soc, max_idling=20, local=False):
        iw = [self.connection, soc]
        local_data = ""
        ow = []
        count = 0
        while True:
            count += 1
            (ins, _, exs) = select.select(iw, ow, iw, 1)
            if exs:
                break
            if ins:
                for i in ins:
                    if i is soc:
                        out = self.connection
                    else:
                        out = soc
                    data = i.recv(8192)
                    if data:
                        if local:
                            local_data += data
                        else:
                            out.send(data)
                        count = 0
            if count == max_idling:
                break
        if local:
            return local_data
        return None


    def do_CONNECT(self):
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if self.connect_to(self.path, soc):
                self.log_request(200)
                self.wfile.write(self.protocol_version +
                                 " 200 Connection established\r\n")
                self.wfile.write("Proxy-agent: %s\r\n" % self.version_string())
                self.wfile.write("\r\n")
                self.read_write(soc, 300)
        finally:
            soc.close()
            self.connection.close()

    def log_message(self, format, *args):
        _debug_(format % args, 2)


class LongPollHandler(object):
    """Class to make long polling handlers easier.
    Simply creating a LongPollHandler object specifying the content type that will be returned by the handler then
    register it with the local server instance.

    lphandler = QueuedLongPollHandler()
    get_local_server().register_handler('^/longpolldemo$', lphandler)

    To send data to be picked up by the next request to the registered url simply append it to the lphandler.

    lphandler.append('Example data')
    """
    def __init__(self, content_type='text/plain'):
        self.queue = Queue.PriorityQueue()
        self.lock = threading.Lock()
        self.waiting_count = 0
        self.content_type = content_type


    def __call__(self, request):
        request.send_response(200)
        request.send_header('mime-type', self.content_type)
        request.end_headers()
        request.request.settimeout(None)
        self.lock.acquire()
        self.waiting_count += 1
        data = self.queue.get()[1]
        try:
            request.wfile.write(data)
        except:
            queue.put((0,data))
        self.waiting_count -= 1
        self.lock.release()


    def append(self, data):
        self.queue.put((100, data))

        
    def shutdown(self):
        for i in range(0, self.waiting_count):
            self.queue.put((0,''))


if __name__ == '__main__':
    import sys
    long_poll_html="""
<html>
<head>
<title>Long Poll Test</title>
<script type="text/javascript">
function longpoll(){
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/longpollcmd', true);
    xhr.timeout = 50000;
    xhr.onreadystatechange = function () {
        if ((this.readyState == 3 || this.readyState == 4) && this.status == 200) {
            cmd = document.getElementById('cmd');
            cmd.innerHTML = this.responseText;
            longpoll();
        }
    };
    xhr.ontimeout = longpoll;
    xhr.send();
}
longpoll();
</script>
</head>
<body>
<div id="cmd">Unset</div>
</body>
</html>
"""
    def _debug_(text, l=0):
        print text

    def html_handler(request):
        request.send_response(200)
        request.send_header('mime-type', 'text/html' )
        request.end_headers()
        request.wfile.write(long_poll_html)


    def handler(request, arg):
        request.send_response(200)
        request.send_header('mime-type', 'text/plain' )
        request.end_headers()
        request.wfile.write('Got arg %s' % arg)

    s = get_local_server()
    lphandler = LongPollHandler()
    s.register_handler('^/(.*)$', handler)
    s.register_handler('^/longpoll.html$', html_handler)
    s.register_handler('^/longpollcmd', lphandler)

    print s.get_url('/')

    while True:
        cmd = sys.stdin.readline()
        if cmd.strip():
            lphandler.append(cmd)
        else:
            break

    lphandler.shutdown()
    s.shutdown()
