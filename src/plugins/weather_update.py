# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# weather.py Freevo Weather Plugin
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   To enable add the following to your local_conf.py
#
#   plugin.activate('weather_update')
#   WEATHER_UPDATE_INTERVAL = 10
#
#   The WEATHER_UPDATE_INTERVAL is set in whole minutes.
#   The weather plugin will grab new data if the cache is older than
#   two hours, so set the update interval to more often than that.
#
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al. 
# Please see the fout freevo/Docs/CREDITS for a complete list of authors.
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
import time
import config

if hasattr(config, 'PLUGIN_WEATHER_LOCATIONS'):
    while hasattr(config, 'WEATHER_UPDATE_INTERVAL'):
        location = []
        dataurl = []
        WEATHER_DIR = os.path.join(config.SHARE_DIR, 'images', 'weather')
        for local in config.PLUGIN_WEATHER_LOCATIONS:
            location = local[0]
            dataurl = 'http://www.msnbc.com/m/chnk/d/weather_d_src.asp?acid=%s' % location
            mapurl = 'http://w3.weather.com/weather/map/%s?from=LAPmaps' % location
            cacheDir = '%s/weather_%s' % (config.FREEVO_CACHEDIR, location)
            cacheFile = '%s/data' % (cacheDir)
            mapFile = '%s/map' % (cacheDir)

            if not os.path.isdir(cacheDir):
                os.mkdir(cacheDir, stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))

            os.system ('wget %s -O %s 2> /dev/null' % (dataurl, cacheFile))
            os.system ('wget %s -O %s 2> /dev/null' % (mapurl, mapFile))
            if config.DEBUG == 1:
                print 'Updated weather data for \"%s\"' % (location)
            time.sleep(config.WEATHER_UPDATE_INTERVAL * 60)
    else:
        print 'WEATHER_UPDATE_INTERVAL not defined in local_conf.py'
else:
    print 'PLUGIN_WEATHER_LOCATIONS not defined in local_conf.py'
