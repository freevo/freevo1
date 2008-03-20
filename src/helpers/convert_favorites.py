# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Helper modules to convert xml favorites to pickled version
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   Run with freevo convert_favorites
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

import os
import stat
import sys

from twisted.web import sux

import config
from util.marmalade import jellyToXML, unjellyFromXML

TYPES_VERSION = 2

class Recordings:
    def getScheduledRecordings(self):
        print 'getScheduledRecordings()'
        file_ver = None
        scheduledRecordings = None

        if os.path.isfile(config.TV_RECORD_SCHEDULE):
            print 'reading cached file (%s)' % config.TV_RECORD_SCHEDULE
            if hasattr(self, 'scheduledRecordings_cache'):
                mod_time, scheduledRecordings = self.scheduledRecordings_cache
                try:
                    if os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME] == mod_time:
                        print 'Return cached data'
                        return scheduledRecordings
                except OSError, e:
                    print 'exception=%r' % e
                    pass

            try:
                f = open(config.TV_RECORD_SCHEDULE, 'r')
                scheduledRecordings = unjellyFromXML(f)
                f.close()
            except sux.ParseError, e:
                print '"%s" is invalid, removed' % (config.TV_RECORD_SCHEDULE)
                os.unlink(config.TV_RECORD_SCHEDULE)

            try:
                file_ver = scheduledRecordings.TYPES_VERSION
            except AttributeError:
                print 'The cache does not have a version and must be recreated.'

            if file_ver != TYPES_VERSION:
                print 'ScheduledRecordings version number %s is stale (new is %s), must be reloaded' % \
                    (file_ver, TYPES_VERSION)
                scheduledRecordings = None
            else:
                print 'Got ScheduledRecordings (version %s).' % file_ver

        if not scheduledRecordings:
            print 'GET: making a new ScheduledRecordings'
            scheduledRecordings = ScheduledRecordings()
            self.saveScheduledRecordings(scheduledRecordings)

        print 'ScheduledRecordings has %s items.' % len(scheduledRecordings.programList)

        try:
            mod_time = os.stat(config.TV_RECORD_SCHEDULE)[stat.ST_MTIME]
            self.scheduledRecordings_cache = mod_time, scheduledRecordings
        except OSError:
            pass
        return scheduledRecordings


def convert_schedule():
    print 'Converting favourties from %s to %s' % (config.TV_RECORD_SCHEDULE, config.TV_RECORD_FAVORITES)
    rs = Recordings()
    schedule = rs.getScheduledRecordings()
    print 'TYPES_VERSION=%r' % (schedule.TYPES_VERSION,)
    print '%-30s  %-30s %-12s %-3s %-3s %-3s %-3s' % ('Name', 'Title', 'Channel', 'Day', 'Min', 'Dup', 'New')
    print '%-30s  %-30s %-12s %-3s %-3s %-3s %-3s' % ('====', '=====', '=======', '===', '===', '===', '===')
    for name, favorite in schedule.favorites.items():
        print '%-30s: %-30s %-12s %-3s %-3s %-3s %-3s' % \
        (name, favorite.title, favorite.channel, favorite.dow, favorite.mod, favorite.allowDuplicates, favorite.onlyNew)

    import tv.record_types
    print 'You should get an error here: it is only a warning'
    sr = tv.record_types.ScheduledRecordings()

    for name, favorite in schedule.favorites.items():
        print 'Added favorite: %s' % (name,)
        sr.addFavorite(favorite)
    print 'Favorites converted successfully, existing manual recordings will need to be added manually'


def help(argv):
    print '%s [<record_schedule.xml>] [<favorites.pickle>]' % (os.path.basename(argv[0]),)
    print '  default: %r %r' % (config.TV_RECORD_SCHEDULE, config.TV_RECORD_FAVORITES)



if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] in ('-h', '--help'):
            help(sys.argv)
            exit(0)
        config.TV_RECORD_SCHEDULE = sys.argv[1]
    if len(sys.argv) > 2:
        config.TV_RECORD_FAVORITES = sys.argv[2]
    if not os.path.exists(config.TV_RECORD_SCHEDULE):
        print '%r does not exist' % (config.TV_RECORD_SCHEDULE,)
        sys.exit(2)
    if os.path.exists(config.TV_RECORD_FAVORITES):
        print '%r exists, please remove' % (config.TV_RECORD_FAVORITES,)
        sys.exit(1)
    convert_schedule()
