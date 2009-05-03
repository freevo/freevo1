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

import os, sys, codecs
from pprint import pprint
from optparse import IndentedHelpFormatter, OptionParser

import config
from tv.record_types import Favorite, ScheduledRecordings

FIELDS = ('name', 'title', 'channel', 'dow', 'mod', 'allowDuplicates', 'onlyNew', 'priority')


class Lexer:
    """
    Class to parse the favorites.txt
    """
    IDLE = 0
    QUOTED = 1
    NONQUOTED = 2
    NEWLINE = 3

    def __init__(self, fd):
        self.fd = fd
        self.state = Lexer.IDLE
        self.qstr = None
        self.linenum = 0

    def read(self):
        s = ''
        while True:
            if self.state == Lexer.NEWLINE:
                self.state = Lexer.IDLE
                yield '\n'

            c = fd.read(1)
            if c == '':
                break
            if self.state == Lexer.IDLE:
                s = ''
                if c == ' ' or c == '\t':
                    continue
                elif c == '\n':
                    self.state = Lexer.NEWLINE
                elif c == '"' or c == "'":
                    self.state = Lexer.QUOTED
                    self.qstr = c
                else:
                    self.state = Lexer.NONQUOTED
                    s = c
            elif self.state == Lexer.QUOTED:
                if c == self.qstr:
                    self.state = Lexer.IDLE
                    yield s
                elif c == '\n':
                    self.state = Lexer.NEWLINE
                    yield s
                else:
                    s += c
            elif self.state == Lexer.NONQUOTED:
                if c == ' ' or c == '\t':
                    self.state = Lexer.IDLE
                    yield s
                elif c == '\n':
                    self.state = Lexer.NEWLINE
                    yield s
                else:
                    s += c


def convert_favorites_txt():
    f = {}
    linenum = 0
    tokennum = 0
    favorites = {}
    lexer = Lexer(fd)
    for token in lexer.read():
        if token == '\n':
            linenum += 1
            if linenum == 1:
                types_version = f['name']
                print types_version
                tokennum = 0
            else:
                favorite = Favorite()
                favorite.name = f['name']
                favorite.title = f['title']
                favorite.channel = f['channel']
                favorite.dow = f['dow']
                favorite.mod = f['mod']
                favorite.priority = f['priority']
                favorite.allowDuplicates = int(f['allowDuplicates'])
                favorite.onlyNew = int(f['onlyNew'])

                print(favorite)
                favorites[favorite.name] = favorite
                tokennum = 0
                f = {}
        else:
            try:
                #print('token=%r (%s)' % (token, token))
                field = FIELDS[tokennum]
                f[field] = token.strip('"').strip("'").strip()
                tokennum += 1

            except ValueError, why:
                print why
                print tokens

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
