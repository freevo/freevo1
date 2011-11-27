#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# start the webserver
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
import logging
logger = logging.getLogger("freevo.helpers.webserver")


import sys, os, pwd
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

from twisted.application import internet, service
from twisted.internet import reactor
from twisted.web import static, server, vhost, script, rewrite


# No debugging in this module
DEBUG = hasattr(config, 'DEBUG_'+appconf) and eval('config.DEBUG_'+appconf) or config.DEBUG


def helpimagesrewrite(request):
    if request.postpath and request.postpath[0]=='help' and request.postpath[1]=='images':
        request.postpath.pop(0)
        request.path = '/'+'/'.join(request.prepath+request.postpath)
    if request.postpath and request.postpath[0]=='help' and request.postpath[1]=='styles':
        request.postpath.pop(0)
        request.path = '/'+'/'.join(request.prepath+request.postpath)


def main():
    # the start and stop stuff will be handled from the freevo script

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
    site = server.Site(rewriter)

    try:
        application = service.Application('web', uid=eval(uid), gid=eval(gid))
    except Exception, e:
        application = service.Application('web')
        print e
    reactor.listenTCP(config.WEBSERVER_PORT, site)
    reactor.run()


if __name__ == '__main__':
    from optparse import IndentedHelpFormatter, OptionParser

    def parse_options():
        """
        Parse command line options
        """
        import version
        formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
        parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="freevo %prog [--daemon|--stop]",
            version='%prog ' + str(version.version))
        parser.prog = appname
        parser.description = "start or stop the internal webserver"

        opts, args = parser.parse_args()
        return opts, args


    opts, args = parse_options()

    try:
        logger.debug('main() starting')
        main()
        logger.debug('main() finished')
    except SystemExit:
        logger.debug('main() stopped')
        pass
    except Exception, why:
        import traceback
        traceback.print_exc()
        logger.warning(why)
