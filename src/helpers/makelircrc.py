#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# helper to generate lircrc
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


import re
import sys
import os
from optparse import IndentedHelpFormatter, OptionParser
from pprint import pprint

import config

isitem = re.compile('^[ \t]*([^ #\t]*)[ \t]*([\S]*)').match
iscode = re.compile('^[ \t]*([^ #\t]*)[ \t]*(0x[0-9A-Fa-f]*)').match

# config list to start with
lircdconf_list = [ '/etc/lircd.conf', '/etc/lirc/lircd.conf' ]

needed  = []
mapping = []
unused  = []

def parse_options():
    """
    Parse command line options
    """
    import version
    formatter = IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter,
        usage="freevo %prog [options] [BUTTON=EVENT]",
        version='%prog ' + str(version.version))
    parser.prog = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    parser.description = "Helper to write the freevo lircrc file"
    parser.add_option('-v', '--verbose', action='count', default=0,
        help='set the level of verbosity [default:%default]')
    parser.add_option('--lircrc', metavar='FILE', default=config.LIRCRC,
        help='the lircrc file [default:%default]')
    parser.add_option('-r', '--remote', metavar='NAME', default=None,
        help='the name of the remote in the lircrc file [default:%default]')
    parser.add_option('-w', '--write', action='store_true', default=False,
        help='write the lircrc file, this will overwrite an existing file!')

    opts, args = parser.parse_args()
    return opts, args


opts, args = parse_options()

alternatives = {
    'QUIT'     : 'EXIT',
    'BACK'     : 'EXIT',
    'BACK/EXIT': 'EXIT',
    'OSD'      : 'DISPLAY',
    'FF'       : 'FFWD',
    'FORWARD'  : 'FFWD',
    'REV'      : 'REW',
    'REWIND'   : 'REW',
    'PREV'     : 'CH-',
    'NEXT'     : 'CH+',
    'MENU/I'   : 'MENU',
    'OK'       : 'SELECT',
    'GO'       : 'ENTER',
    'RECORD'   : 'REC',
}

for arg in args:
    try:
        button, event = arg.split('=')
        button = button.strip().upper()
        event  = event.strip().upper()
        alternatives[button] = event
        print >>sys.__stderr__, 'Added alternative %r as %r' % (button, event)
    except ValueError, why:
        pass


def findIncludes(name):
    """returns a list of files included in lircd.conf via the 'include' keyword"""
    list = []
    file = open(name, 'r')
    for line in file.readlines():
        if line.find('include ') != -1:
            list.append(line.split()[1])
    return list


class ParseState:
    IDLE           = 0
    IN_REMOTE      = 1
    IN_CODES       = 2
    IN_OTHER_CODES = 3
    def __init__(self):
        self.state = ParseState.IDLE

    def __str__(self):
        if self.state == ParseState.IDLE: return 'IDLE'
        if self.state == ParseState.IN_REMOTE: return 'IN_REMOTE'
        if self.state == ParseState.IN_CODES: return 'IN_CODES'
        if self.state == ParseState.IN_OTHER_CODES: return 'IN_OTHER_CODES'
        return 'UNKNOWN'


def parseFile(name):
    state = ParseState()
    num_remotes = 0
    remotes = []
    remote_used = None
    remote_found = False
    file = open(name, 'r')
    for line in file.readlines():
        if opts.verbose >= 2:
            print >>sys.__stderr__, '%16s: %s' % (state, line.rstrip())
        # find the remote section
        if line.find('begin remote') != -1:
            remote_found = False
            num_remotes += 1
            state.state = ParseState.IN_REMOTE
        if line.find('end remote') != -1:
            state.state = ParseState.IDLE
        # find the codes section
        if line.find('begin codes') != -1:
            if remote_found:
                state.state = ParseState.IN_CODES
            else:
                state.state = ParseState.IN_OTHER_CODES
        if line.find('end codes') != -1:
            state.state = ParseState.IN_REMOTE

        if state.state == ParseState.IN_REMOTE:
            match = isitem(line)
            if match:
                item, value = match.groups()
                if item.lower() == 'name':
                    remotes.append(value)
                    if opts.verbose:
                        print >>sys.__stderr__, 'remote %s=%s' % (item, value)
                    if opts.remote:
                        # if the remote is specified then match its name
                        if opts.remote.lower() == value.lower():
                            remote_found = True
                    else:
                        # if the remote is *not* specified then use the first remote
                        if num_remotes == 1:
                            remote_found = True
                    if remote_found:
                        remote_used = value
                        if opts.verbose:
                            print >>sys.__stderr__, 'using remote %s' % (value)
        
        # continue in the codes section
        if state.state == ParseState.IN_CODES:
            match = iscode(line)
            if match:
                lirc_button = match.groups()[0]
                freevo_button = lirc_button.upper()
                if freevo_button in needed:
                    needed.remove(freevo_button)
                    mapping.append((freevo_button, lirc_button))
                elif alternatives.has_key(freevo_button) and alternatives[freevo_button] in needed:
                    needed.remove(alternatives[freevo_button])
                    mapping.append((alternatives[freevo_button], lirc_button))
                else:
                    unused.append(lirc_button)
                    mapping.append((freevo_button, lirc_button))
    file.close()
    return remote_used, remotes

for type in config.EVENTS:
    for button in config.EVENTS[type]:
        if not button in needed:
            needed.append(button)

write_option = False
use_pos = None
pos = 0

# first pass: search for included configurations
for lircdconf in lircdconf_list:
    if os.path.exists(lircdconf):
        print "Reading: %s" % (lircdconf)
        lircdconf_list += findIncludes(lircdconf)
        # remove duplicates
        lircdconf_list = list(set(lircdconf_list))

# second pass: read actual key config
for lircdconf in lircdconf_list:
    if os.path.exists(lircdconf):
        remote_used, remotes = parseFile(lircdconf)
        if remote_used is None:
            sys.exit('Failed: Cannot find remote %r, choose from:\n  "' % (opts.remote,) + \
                '",\n  "'.join(remotes) + '".')
        if opts.remote is None and len(remotes) != 1:
            print >>sys.__stderr__, 'Remote not specified using %r from:\n  "' % (remote_used,) + \
                '",\n  "'.join(remotes) + '".'

# write result to file
if opts.write:
    out = open(opts.lircrc, 'w')
    for event, button in mapping:
        out.write('begin\n')
        out.write('    prog   = freevo\n')
        out.write('    button = %s\n' % button)
        out.write('    repeat = %s\n' % 0)
        out.write('    config = %s\n' % event)
        out.write('end\n')
    out.close()
    print >>sys.__stderr__, "Success: %s button mappings written to %r" % (len(mapping), opts.lircrc)
    sys.exit(0)

# print stuff to stdout
print 'Mapping:'
print
for event, button in mapping:
    print '  %-10s: %-10s' % (button, event)
print

if unused:
    print """The following buttons are not used by Freevo.  You may want to enhance
EVENTS in local_conf.py to make use of the buttons"""
    print
    for i in unused:
        print '  %s' % i
    print

if needed:
    print 'The following buttons are needed for Freevo and not defined yet.'
    print
    for i in needed:
        print '  %s' % i
    print
    if unused:
        print """Since you have unused buttons, you may want to set a button to a missing
one Right now, the output file will have an unused mapping for %r. You
could assign this button by calling this script with the extra parameter 
\'%s=%s\'.  You can add this parameter as often as needed.  Please send
good mappings to missing buttons to the Freevo developers to add them into
this script.""" % (unused[0], unused[0], needed[0])
    else:
        print """Since there are no unused buttons anymore, you need to change EVENTS in
local_conf.py"""
    print
