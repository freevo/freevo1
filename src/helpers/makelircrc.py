#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# makelircrc.py - helper to generate lircrc
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
import config
import sys
import os

iscode = re.compile('^[ \t]*([^ #\t]*)[ \t]*(0x[0-9A-Fa-f]*)').match

# config list to start with
lircdconf_list = [ '/etc/lircd.conf', '/etc/lirc/lircd.conf' ]

needed  = []
mapping = []
unused  = []

alternatives = {
    'QUIT'      : 'EXIT',
    'BACK/EXIT' : 'EXIT',
    'OSD' : 'DISPLAY',
    'FF'  : 'FFWD',
    'FORWARD': 'FFWD',
    'REV' : 'REW',
    'REWIND' : 'REW',
    'PREV'   : 'CH-',
    'NEXT'   : 'CH+',
    'MENU/I' : 'MENU',
    'OK'     : 'SELECT',
    'GO'     : 'ENTER',
    'RECORD' : 'REC',
    }


def findIncludes(name):
    """returns a list of files included in lircd.conf via the 'include' keyword"""
    list = []
    file = open(name, 'r')
    for line in file.readlines():
        if line.find('include ') != -1:
            list.append(line.split()[1])
    return list

def parseFile(name):
    found_codes = 0
    file = open(name, 'r')
    for line in file.readlines():
        # find the codes section
        if line.find('begin codes') != -1:
            found_codes += 1
        # continue in the codes section
        if found_codes > 0:
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
    return found_codes

# argument parsing
if len(sys.argv)>1 and sys.argv[1] in ('-h', '--help'):
    print 'script to write the freevo lircrc file'
    print 'usage: makelircrc [-w] [section_index] [button=comand]'
    print
    print 'The -w will write the settings to %s' % config.LIRCRC
    print 'If this is not the file the information should be written to, set'
    print 'LIRCRC in your local_conf.py to the correct filename. If the file'
    print 'exists, it will be overwritten.'
    print
    print 'If started with no options, this script will print the suggested mapping'
    print 'and a list of buttons not used right now and a list of events in Freevo'
    print 'without a button. You can either change EVENTS in local_conf.py or define'
    print 'a mapping on your own.'
    print
    sys.exit(0)

for type in config.EVENTS:
    for button in config.EVENTS[type]:
        if not button in needed:
            needed.append(button)

write_option = False
use_pos = None
pos = 0

for arg in sys.argv[1:]:
    if arg == '-w':
        write_option = True

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
        pos = parseFile(lircdconf)
        if pos != 1:
            print "Warning: your %s seems to contain %d sections starting with \"begin codes\"." % (lircdconf, pos)

# write result to file
if write_option:
    out = open(config.LIRCRC, 'w')
    for event, button in mapping:
        out.write('begin\n')
        out.write('    prog   = freevo\n')
        out.write('    button = %s\n' % button)
        out.write('    config = %s\n' % event)
        out.write('end\n')
    out.close()
    print "Success: %s button mappings written to %s!" % (len(mapping), config.LIRCRC)
    sys.exit(0)

# print stuff to stdout
print 'Mapping:'
print
for event, button in mapping:
    print '  %-10s: %-10s' % (button, event)
print
if unused:
    print 'The following buttons are not used by Freevo.'
    print 'You may want to enhance EVENTS in local_conf.py to make use of the buttons'
    print
    for i in unused:
        print '  %s' % i
    print
if needed:
    print 'The following buttons are needed for Freevo and not defined yet.'
    if unused:
        print 'Since you have unused buttons, you may want to set a button to a missing one'
        print 'Right now, the output file will have an unused mapping for %s. You' % unused[0]
        print 'could assign this button by calling this script with the extra parameter'+\
              '\'%s=%s\'.' % (unused[0], needed[0])
        print 'You can add this parameter as often as needed.'
        print 'Please send good mappings to missing buttons to the Freevo developers to add'
        print 'them into this script.'
    else:
        print 'Since there are no unused buttons anymore, you need to change EVENTS in'
        print 'local_conf.py'
    print
    for i in needed:
        print '  %s' % i
    print
#if use_pos == None and pos > 1:
#    print 'Your %s seems to contain %d sections starting with "begin codes".' % (x.name, pos)
#    print 'You should select the one best matching your remote by giving its number (1..%d)' % (pos, )
#    print 'on the commandline.'
