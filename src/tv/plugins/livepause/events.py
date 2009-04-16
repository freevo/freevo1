# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# events.py - the Freevo Live Pause module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
#
# Todo:
#
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
# ----------------------------------------------------------------------- */
"""
Defines the events used by different parts of the Live Pause system to communicate data availability.

DATA_STARTED - Tuning is complete and data has started arriving.
DATA_ACQUIRED - Sent for every second of data acquired after the initial EVENT_DATA_STARTED.
DATA_TIMEDOUT - Sent if no data has been received for a configurable number of seconds.
READER_OVERTAKEN - Sent by the Slave server when it detects that it has been overtaken by the filler (and there lost data).
TV_CHANNEL_NUMBER - Sent by the live pause plugin when the user has entered a channel number to change the current channel.
LIVEPAUSE_EXITED - Sent when the livepause application has exited.
"""

import event

DATA_STARTED      = event.Event('DATA_STARTED')
DATA_ACQUIRED     = event.Event('DATA_ACQUIRED')
DATA_TIMEDOUT     = event.Event('DATA_TIMEDOUT')

READER_OVERTAKEN  = event.Event('READER_OVERTAKEN')
READER_STARVED    = event.Event('READER_STARVED')

TV_CHANNEL_NUMBER = event.Event('TV_CHANNEL_NUMBER')

LIVEPAUSE_EXITED  = event.Event('LIVEPAUSE_EXITED')

SAVE_STARTED      = event.Event('SAVE_STARTED')
SAVE_FINISHED     = event.Event('SAVE_FINISHED')
SAVE_FAILED       = event.Event('SAVE_FAILED')
