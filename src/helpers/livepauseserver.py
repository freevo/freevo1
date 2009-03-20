# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Livepause backend server
# -----------------------------------------------------------------------
# $Id$
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

import config

from tv.plugins.livepause.backend import LocalBackend,BACKEND_SERVER_PORT,BACKEND_SERVER_SECRET, MEDIA_SERVER_PORT
import kaa
import kaa.rpc

import sys
import os.path
import logging

appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
appconf = appname.upper()

# change uid
if __name__ == '__main__':
    config.DEBUG_STDOUT = 0
    uid = 'config.'+appconf+'_UID'
    gid = 'config.'+appconf+'_GID'
    if hasattr(config, uid):
        try:
            if eval(uid) and os.getuid() == 0:
                os.setgid(eval(gid))
                os.setuid(eval(uid))
                os.environ['USER'] = pwd.getpwuid(os.getuid())[0]
                os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
        except Exception, why:
            print why
            sys.exit(1)

DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG
LOGGING = hasattr(config, 'LOGGING_'+appconf) and eval('config.LOGGING_'+appconf) or config.LOGGING

logfile = '%s/%s-%s.log' % (config.FREEVO_LOGDIR, appname, os.getuid())
sys.stdout = open(logfile, 'a')
sys.stderr = sys.stdout

logging.getLogger('').setLevel(LOGGING)
logging.basicConfig(level=LOGGING, \
    #datefmt='%a, %H:%M:%S', # datefmt does not support msecs :(
    format='%(asctime)s %(levelname)-8s %(message)s', \
    filename=logfile, filemode='a')

class RemoteBackend(LocalBackend):
    def __init__(self):
        super(RemoteBackend, self).__init__()
        self.client = None

    @kaa.rpc.expose('set_mode')
    def set_mode(self, mode):
        super(RemoteBackend, self).set_mode(mode)

    @kaa.rpc.expose('get_buffer_info')
    def get_buffer_info(self):
        return super(RemoteBackend, self).get_buffer_info()

    @kaa.rpc.expose('seekto')
    def seekto(self, to_time):
        return super(RemoteBackend, self).seekto(to_time)

    @kaa.rpc.expose('seek')
    def seek(self, time_delta):
        return super(RemoteBackend, self).seek(time_delta)

    @kaa.rpc.expose('disable_buffering')
    def disable_buffering(self):
        super(RemoteBackend, self).disable_buffering()

    @kaa.rpc.expose('change_channel')
    def change_channel(self, channel):
        super(RemoteBackend, self).change_channel(channel)

    @kaa.rpc.expose('save')
    def save(self, filename, time_start, time_end):
        super(RemoteBackend, self).save(filename, time_start, time_end)

    @kaa.rpc.expose('cancelsave')
    def cancelsave(self):
        super(RemoteBackend, self).cancelsave()
        
    @kaa.rpc.expose('set_events_enabled', add_client=True)
    def set_events_enabled(self, client, enable):
        self.client = client
        client.signals['closed'].connect(self.disconnected)
        super(RemoteBackend, self).set_events_enabled(enable)

    def send_event(self, to_send):
        if self.client:
            try:
                self.client.rpc('send_event', to_send)
            except:
                _debug_('Failure sending event to client!')

    def disconnected(self):
        self.client = None


def main():
    if hasattr(config, 'LIVE_PAUSE2_BACKEND_SERVER_PORT'):
        socket = ('', config.LIVE_PAUSE2_BACKEND_SERVER_PORT)
    else:
        socket = ('', BACKEND_SERVER_PORT)
    if hasattr(config, 'LIVE_PAUSE2_BACKEND_SERVER_SECRET'):
        secret = config.LIVE_PAUSE2_BACKEND_SERVER_SECRET
    else:
        secret = BACKEND_SERVER_SECRET

    if not hasattr(config, 'LIVE_PAUSE2_PORT'):
        config.LIVE_PAUSE2_PORT = MEDIA_SERVER_PORT
 
    _debug_('socket=%r, secret=%r' % (socket, secret))

    server = RemoteBackend()

    try:
        rpc = kaa.rpc.Server(socket, secret)
    except Exception:
        raise

    rpc.connect(server)

    _debug_('kaa.main starting')
    kaa.main.run()
    _debug_('kaa.main finished')


if __name__ == '__main__':
    import socket
    import glob

    sys.stdout = config.Logger(sys.argv[0] + ':stdout')
    sys.stderr = config.Logger(sys.argv[0] + ':stderr')

    try:
        _debug_('main() starting')
        main()
        _debug_('main() finished')
    except SystemExit:
        _debug_('main() stopped')
        pass
    except Exception, why:
        import traceback
        traceback.print_exc()
        _debug_(why, DWARNING)
