# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Helper to convert favorites.txt to favorites.pickle
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   to run under freevo type:
#       freevo convert_favorites_txt -- --help
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

import os
import sys
import codecs
from optparse import IndentedHelpFormatter, OptionParser
import re
import config
from tv.record_types import Favorite, ScheduledRecordings

FIELDS = ('name', 'title', 'channel', 'dow', 'mod', 'allowDuplicates', 'onlyNew', 'priority')

RE_FIELDS = re.compile("^'(?P<name>.+)' '(?P<title>.+)' '(?P<channel>.+)' '(?P<dow>.+)' '(?P<mod>.+)' (?P<allowDuplicates>\d) (?P<onlyNew>\d) '(?P<priority>.+)'$")


def convert_favorites_txt():
    linenum = 0
    tokennum = 0
    types_version = fd.readline()
    print types_version
    favorites = {}
    
    for line in fd:
        m = RE_FIELDS.match(line)
        if m:
            favorite = Favorite()
            favorite.name = m.group('name')
            favorite.title = m.group('title')
            favorite.channel = m.group('channel')
            favorite.dow = m.group('dow')
            favorite.mod = m.group('mod')
            favorite.priority = m.group('priority')
            favorite.allowDuplicates = int(m.group('allowDuplicates'))
            favorite.onlyNew = int(m.group('onlyNew'))

            print(favorite)
            favorites[favorite.name] = favorite
        else:
            print 'Failed to parse line: %r' % line,

    return favorites


def parse_options():
    """
    Parse command line options
    """
    import version
    tmp = os.environ.has_key('TEMP') and os.environ['TEMP'] or '/tmp'
    formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter,
        usage="freevo %prog [options]",
        version='%prog ' + str(version.version))
    parser.prog = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    parser.description = "Helper to convert a favorites.txt to a favorites.pickle"
    parser.add_option('-v', '--verbose', action='count', default=0,
        help='set the level of verbosity [default:%default]')
    parser.add_option('--favorites-txt', metavar='FILE', default=config.TV_RECORD_FAVORITES_LIST,
        help='the favorites.txt file to read and process [default:%default]')
    parser.add_option('--favorites-pickle-out', metavar='FILE', default=os.path.join(tmp, 'favorites.pickle'),
        help='the reritten favorites.pickle file [default:%default]')
    parser.add_option('--favorites-txt-out', metavar='FILE', default=os.path.join(tmp, 'favorites.txt'),
        help='the reritten favorites.txt file [default:%default]')
    parser.add_option('--schedule-pickle-out', metavar='FILE', default=os.path.join(tmp, 'schedule.pickle'),
        help='the reritten schedule.pickle file [default:%default]')

    opts, args = parser.parse_args()
    return opts, args


opts, args = parse_options()


fencoding = 'iso-8859-15'
fencoding = 'utf-8'

fd = codecs.open(opts.favorites_txt, encoding=fencoding)
config.TV_RECORD_SCHEDULE = opts.schedule_pickle_out
config.TV_RECORD_FAVORITES = opts.favorites_pickle_out
sr = ScheduledRecordings()
sr.favorites = convert_favorites_txt()
config.TV_RECORD_FAVORITES_LIST = opts.favorites_txt_out
sr.saveFavorites()
