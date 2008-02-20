#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# wrapper for xmltv
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


import sys
import os
import shutil

import config

def usage():
    print 'Downloads the listing for xmltv and cache the data'
    print
    print 'usage: freevo tv_grab [ --query ]'
    print 'options:'
    print '  --query:  print a list of all stations. The list can be used to set TV_CHANNELS'
    sys.exit(0)


def grab():
    if not config.XMLTV_GRABBER:
        print 'No program found to grab the listings. Please set XMLTV_GRABBER'
        print 'in local.conf.py to the grabber you need'
        print
        usage()

    print 'Grabbing listings.'
    xmltvtmp = '/tmp/TV.xml.tmp'
    ec = os.system('%s --output %s --days %s' % ( config.XMLTV_GRABBER,
                                             xmltvtmp,
                                             config.XMLTV_DAYS ))

    if os.path.exists(xmltvtmp) and ec == 0:
        if os.path.isfile(config.XMLTV_SORT):
            print 'Sorting listings.'
            os.system('%s --output %s %s' % ( config.XMLTV_SORT,
                                              xmltvtmp+'.1',
                                              xmltvtmp ))

            shutil.copyfile(xmltvtmp+'.1', xmltvtmp)
            os.unlink(xmltvtmp+'.1')

        else:
            print 'Not configured to use tv_sort, skipping.'

        print 'caching data, this may take a while'

        import tv.epg_xmltv
        tv.epg_xmltv.get_guide(XMLTV_FILE=xmltvtmp)
    else:
        sys.stderr.write("ERROR: xmltv grabbing failed; "
                         "%s returned exit code %d.\n" %
                         (config.XMLTV_GRABBER, ec >> 8))
        sys.stderr.write("  If you did not change your system, it's likely that "
                         "the site being grabbed did.\n  You might want to try "
                         "whether updating your xmltv helps in that case:\n"
                         "    http://www.xmltv.org/\n")
        sys.exit(1)

if __name__ == '__main__':

    def handler(result):
        if result:
            print _('Updated recording schedule')
        else:
            print _('Not updated recording schedule')
        raise SystemExit


    if len(sys.argv)>1 and sys.argv[1] == '--help':
        usage()

    if len(sys.argv)>1 and sys.argv[1] == '--query':
        print
        print 'searching for station information'

        chanlist = config.detect_channels()

        print
        print 'Possible list of tv channels. If you want to change the station'
        print 'id, copy the next statement into your local_conf.py and edit it.'
        print 'You can also remove lines or resort them'
        print
        print 'TV_CHANNELS = ['
        for c in chanlist[:-1]:
            print '    ( \'%s\', \'%s\', \'%s\' ), ' % c
        print '    ( \'%s\', \'%s\', \'%s\' ) ] ' % chanlist[-1]
        sys.exit(0)

    grab()

    import kaa
    from tv.record_client import RecordClient

    print 'Scheduling favorites for recording:  '
    if not RecordClient().updateFavoritesSchedule(handler):
        print _('recordserver is not running')
        raise SystemExit

    kaa.main.run()
