# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# tv.py - IdleBarplugin for monitoring the xmltv-listings
# -----------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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


# python modules
import os
import glob
import time

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config
import util.tv_util as tv_util


class PluginInterface(IdleBarPlugin):
    """
    Informs you, when the xmltv-listings expires.

    Activate with:
    plugin.activate('idlebar.tv', level=20, args=(listings_threshold,))
    listings_threshold must be a number in hours.  For example if you put
    args=(12, ) then 12 hours befor your xmltv listings run out the tv icon
    will present a warning.  Once your xmltv data is expired it will present
    a more severe warning.  If no args are given then no warnings will be
    given.
    """
    def __init__(self, listings_threshold=-1):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.tv'
        self.listings_threshold = listings_threshold
        self.next_guide_check = 0
        self.listings_expire = 0
        self.tvlockfile = config.FREEVO_CACHEDIR + '/record.*'
        icondir = os.path.join(config.ICON_DIR, 'status')
        self.TVLOCKED     = os.path.join(icondir, 'television_active.png')
        self.TVFREE       = os.path.join(icondir, 'television_inactive.png')
        self.NEAR_EXPIRED = os.path.join(icondir, 'television_near_expired.png')
        self.EXPIRED      = os.path.join(icondir, 'television_expired.png')

    def checktv(self):
        if len(glob.glob(self.tvlockfile)) > 0:
            return 1
        return 0

    def draw(self, (type, object), x, osd):

        if self.checktv() == 1:
            return osd.draw_image(self.TVLOCKED, (x, osd.y + 10, -1, -1))[0]

        if self.listings_threshold != -1:
            now = time.time()

            if now > self.next_guide_check:
                _debug_('TV: checking guide')
                self.listings_expire = tv_util.when_listings_expire()
                _debug_('TV: listings expire in %s hours' % self.listings_expire)
                # check again in 10 minutes
                self.next_guide_check = now + 10*60

            if self.listings_expire == 0:
                return osd.draw_image(self.EXPIRED, (x, osd.y + 10, -1, -1))[0]
            elif self.listings_expire <= self.listings_threshold:
                return osd.draw_image(self.NEAR_EXPIRED, (x, osd.y + 10, -1, -1))[0]

        return osd.draw_image(self.TVFREE, (x, osd.y + 10, -1, -1))[0]
