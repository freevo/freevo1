# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# rssserver.py - This is the Freevo RSS feed server
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

'''
In local_conf.py add the following:
RSS_FEEDS='/etc/freevo/rss.feeds'
RSS_VIDEO='/path/to/video/feeds/'
RSS_AUDIO='/path/to/podcasts/'

You will need to make a rss.feeds file: it contains the URL and the number of
days it's been published

# Begin /etc/freevo/rss.feeds

http://twit.libsyn.com/rss,7
http://leo.am/podcasts/twit,7
http://leo.am/podcasts/itn,7
http://feeds.feedburner.com/TechRenegades,7
http://www.linuxactionshow.com/?feed=rss2&cat=3,30
http://www.thelinuxlink.net/tllts/tllts.rss,30
http://www.linux-games.ca/2006/redneck.xml,360

# End /etc/freevo/rss.feeds
'''

import os,sys,threading,time
import rssperiodic
import config
from twisted.python import log

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

if len(sys.argv)>1 and sys.argv[1] == '--help':
    print 'start or stop the internal rssserver'
    print 'usage freevo rssserver [ start | stop ]'
    sys.exit(0)

# No debugging in this module
DEBUG = hasattr(config, appconf+'_DEBUG') and eval('config.'+appconf+'_DEBUG') or config.DEBUG

logfile = '%s/%s-%s.log' % (config.LOGDIR, appname, os.getuid())
log.startLogging(open(logfile, 'a'))

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            log.debug(String(text))
        except:
            print String(text)

while True:
      t = threading.Thread(rssperiodic.checkForUpdates())
      t.start()
      t.join()
      time.sleep(60)
