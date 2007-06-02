#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# makestationlist.py - Generates stationlist.xml for use with tvtime
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo: Map the various frequencies from freevo.conf to the frequencies
#       for tv time.
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
Band name          Channels provided
US Cable           1-99
US Cable 100       100-125
US Two-Way         T7, T8, T9, T10, T11, T12 T13, T14
US Broadcast       2-83
China Broadcast    1-68, A1-A7, B1-B31, C1-C5
Japan Broadcast    1-62
Japan Cable        13-63
VHF E2-E12         E1-E12
VHF S1-S41         S1-S41
VHF Misc           X, Y, Z, Z+1, Z+2
VHF France         K01-K10, KB-KQ, H01-H19
VHF Russia         R1-R12, SR1-SR19
VHF Australia      AS1-AS12, AS5A, AS9A
VHF Italy          A-H, H1, H2
VHF Ireland        I1-I9
VHF South Africa   1-13
UHF                U21-U69
UHF Australia      AU28-AU69
Australia Optus    01-058
'''

import sys
import config
import cgi

bands = [
    'US Cable', 'US Cable 100', 'US Two-Way', 'US Broadcast',
    'China Broadcast', 'Japan Broadcast', 'Japan Cable',
    'VHF E2-E12', 'VHF S1-S41', 'VHF Misc', 'VHF France',
    'VHF Russia', 'VHF Australia', 'VHF Italy', 'VHF Ireland',
    'VHF South Africa', 'UHF', 'UHF Australia', 'Australia Optus'
]

if len(sys.argv)>1 and sys.argv[1] == '--help':
    print 'convert local_conf.py station list for tvtime'
    print 'option: --band <name>\nwhere: name is one of:\n\'%s\'' % '\', \''.join(bands)
    print
    sys.exit(0)

band = "US-Cable"
if len(sys.argv)>2 and sys.argv[1] == '--band':
    if sys.argv[2] in bands:
        band = sys.argv[2]

norm = config.CONF.tv.upper()

fp = open('/tmp/stationlist.xml','w')

fp.write('<?xml version="1.0"?>\n')
fp.write('<!DOCTYPE stationlist PUBLIC "-//tvtime//DTD stationlist 1.0//EN" "http://tvtime.sourceforge.net/DTD/stationlist1.dtd">\n')
fp.write('<stationlist xmlns="http://tvtime.sourceforge.net/DTD/">\n')
fp.write('  <list norm="%s" frequencies="%s">\n' % (norm, band))

c = 0
for m in config.TV_CHANNELS:
    if config.FREQUENCY_TABLE.has_key(m[2]):
        channelfreq = float(config.FREQUENCY_TABLE[m[2]]) / 1000.0
        fp.write('    <station name="%s" active="1" position="%s" band="Custom" channel="%sMHz"/>\n' % \
            (cgi.escape(m[1]), c, channelfreq))
    else:
        fp.write('    <station name="%s" active="1" position="%s" band="%s" channel="%s"/>\n' % \
            (cgi.escape(m[1]), c, band, m[2]))
    c = c + 1

fp.write('  </list>\n')
fp.write('</stationlist>\n')
fp.close()
