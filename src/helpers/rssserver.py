# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo RSS feed server
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

"""
In local_conf.py add the following:

# File defining RSS feeds to monitor (see format below).
RSS_FEEDS='/etc/freevo/rss.feeds'
# Frequency (in seconds) to check for new downloads. Default is 3600 or 1 hour.
RSS_CHECK_INTERVAL=3600
# Download directory for video files.
RSS_VIDEO='/path/to/video/feeds/'
# Download directory for audio files.
RSS_AUDIO='/path/to/podcasts/'

You will need to make a rss.feeds file: it contains the URL. And after the
semicolon the number of days it's been published and how long the copy
should stay on the local machine before it gets deleted.

# Begin /etc/freevo/rss.feeds
http://twit.libsyn.com/rss;7
http://leo.am/podcasts/twit;7
http://leo.am/podcasts/itn;7
http://feeds.feedburner.com/TechRenegades;7
http://www.linuxactionshow.com/?feed=rss2&cat=3;30
http://www.thelinuxlink.net/tllts/tllts.rss;30
http://www.linux-games.ca/2006/redneck.xml;360
# End /etc/freevo/rss.feeds
"""

import os, sys, threading, time
import rssperiodic
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

if len(sys.argv)>1 and sys.argv[1] == '--help':
    print 'start or stop the internal rssserver'
    print 'usage freevo rssserver [ start | stop ]'
    sys.exit(0)


# check for expired files and delete them
to = threading.Thread(rssperiodic.checkForExpiration())
to.start()
to.join()

# than starting server to poll podcasts
while True:
    t = threading.Thread(rssperiodic.checkForUpdates())
    t.start()
    t.join()
    try:
        time.sleep(config.RSS_CHECK_INTERVAL)
    except KeyboardInterrupt:
        print 'Goodbye'
        break
    except Exception, e:
        print e
