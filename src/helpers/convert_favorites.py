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

        if os.path.isfile(opts.schedule):
            print 'reading cached file (%s)' % opts.schedule
            if hasattr(self, 'scheduledRecordings_cache'):
                mod_time, scheduledRecordings = self.scheduledRecordings_cache
                try:
                    if os.stat(opts.schedule)[stat.ST_MTIME] == mod_time:
                        print 'Return cached data'
                        return scheduledRecordings
                except OSError, e:
                    print 'exception=%r' % e
                    pass

            try:
                f = open(opts.schedule, 'r')
                scheduledRecordings = unjellyFromXML(f)
                f.close()
            except sux.ParseError, e:
                print '"%s" is invalid, removed' % (opts.schedule)
                os.unlink(opts.schedule)

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
            mod_time = os.stat(opts.schedule)[stat.ST_MTIME]
            self.scheduledRecordings_cache = mod_time, scheduledRecordings
        except OSError:
            pass
        return scheduledRecordings


def convert_schedule(opts):
    print 'Converting favourties from %s to %s' % (opts.schedule, opts.favorites)
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



if __name__ == '__main__':
    from optparse import IndentedHelpFormatter, OptionParser

    def parse_options():
        """
        Parse command line options
        """
        import version
        formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
        parser = OptionParser(conflict_handler='resolve', formatter=formatter,
            usage="freevo %prog [options]",
            version='%prog ' + str(version.version))
        parser.prog = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        parser.description = "Helper to convert the record_schedule.xml to favorites.pickle"
        parser.add_option('-v', '--verbose', action='count', default=0,
            help='set the level of verbosity [default:%default]')
        parser.add_option('-i', '--schedule', metavar='FILE', default=config.TV_RECORD_SCHEDULE,
            help='the record schedule file [default:%default]')
        parser.add_option('-o', '--favorites', metavar='FILE', default=config.TV_RECORD_FAVORITES,
            help='the record favorites file [default:%default]')

        opts, args = parser.parse_args()

        if not os.path.exists(opts.schedule):
            parser.error('%r does not exist.' % (opts.schedule,))

        if os.path.exists(opts.favorites):
            parser.error('%r exists, please remove.' % (opts.favorites,))

        if os.path.splitext(opts.schedule)[1] != '.xml':
            parser.error('%r is not an XML file.' % (opts.schedule,))

        return opts, args


    opts, args = parse_options()

    convert_schedule(opts)
