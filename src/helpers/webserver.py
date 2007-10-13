#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# webserver.py - start the webserver
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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


import sys, os
import config

appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
appconf = appname.upper()

# change uid
if __name__ == '__main__':
    uid='config.'+appconf+'_UID'
    gid='config.'+appconf+'_GID'
    try:
        if eval(uid) and os.getuid() == 0:
            os.setgid(eval(gid))
            os.setuid(eval(uid))
            os.environ['USER'] = pwd.getpwuid(os.getuid())[0]
            os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
    except Exception, e:
        print e

from twisted.internet import app
from twisted.web import static, server, vhost, script
from twisted.python import log
import twisted.web.rewrite as rewrite


if len(sys.argv)>1 and sys.argv[1] == '--help':
    print 'start or stop the internal webserver'
    print 'usage freevo webserver [ start | stop ]'
    sys.exit(0)

# No debugging in this module
DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            log.debug(String(text))
        except:
            print String(text)

def helpimagesrewrite(request):
    if request.postpath and request.postpath[0]=='help' and request.postpath[1]=='images':
        request.postpath.pop(0)
        request.path = '/'+'/'.join(request.prepath+request.postpath)
    if request.postpath and request.postpath[0]=='help' and request.postpath[1]=='styles':
        request.postpath.pop(0)
        request.path = '/'+'/'.join(request.prepath+request.postpath)

def main():
    # the start and stop stuff will be handled from the freevo script

    logfile = '%s/%s-%s.log' % (config.FREEVO_LOGDIR, appname, os.getuid())
    log.startLogging(open(logfile, 'a'))

    if os.path.isdir(os.path.join(os.environ['FREEVO_PYTHON'], 'www/htdocs')):
        docRoot = os.path.join(os.environ['FREEVO_PYTHON'], 'www/htdocs')
    else:
        docRoot = os.path.join(config.SHARE_DIR, 'htdocs')

    root = static.File(docRoot)
    root.processors = { '.rpy': script.ResourceScript, }

    child_resources = []
    child_resources.extend(config.VIDEO_ITEMS)
    child_resources.extend(config.AUDIO_ITEMS)
    child_resources.extend(config.IMAGE_ITEMS)
    child_resources.extend([('Recorded TV', config.TV_RECORD_DIR)])
    child_resources.extend([('Webserver Cache', config.WEBSERVER_CACHEDIR)])
    for item in child_resources:
        if isinstance(item, tuple) and len(item) == 2:
            (title, path) = item
            root.putChild(path.replace("/", "_"), static.File(path))

    root.putChild('vhost', vhost.VHostMonsterResource())
    rewriter =  rewrite.RewriterResource(root, helpimagesrewrite)
    if (config.DEBUG == 0):
        site = server.Site(rewriter, logPath='/dev/null')
    else:
        site = server.Site(rewriter)

    application = app.Application('web')
    application.listenTCP(config.WEBSERVER_PORT, site)
    application.run(save=0)


if __name__ == '__main__':
    import traceback
    import time
    while 1:
        try:
            start = time.time()
            main()
            break
        except:
            traceback.print_exc()
            if start + 10 > time.time():
                print 'server problem, sleeping 1 min'
                time.sleep(60)
