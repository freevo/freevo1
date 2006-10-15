# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# weather.py - IdleBarplugin for weather
# -----------------------------------------------------------------------
# $Id: volume.py 5860 2004-07-10 12:33:43Z dischi $
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
import time
import string

# freevo modules
from plugins.idlebar import IdleBarPlugin
import plugin, config
import util.pymetar as pymetar


class PluginInterface(IdleBarPlugin):
    """
    Shows the current weather.

    Activate with:
    plugin.activate('idlebar.weather', level=30, args=('4-letter code', ))

    For weather station codes see: http://www.nws.noaa.gov/tg/siteloc.shtml
    You can also set the unit as second parameter in args ('C', 'F', or 'K')
    """
    def __init__(self, zone='CYYZ', units='C'):
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.weather'
        self.TEMPUNITS = units
        self.METARCODE = zone
        self.WEATHERCACHE = config.FREEVO_CACHEDIR + '/weather'
        print
        print 'WARNING: the idlebar.weather plugin downloads new weather'
        print 'information inside the main loop. This bug makes all menu'
        print 'actions _very_ slow. Consider not using this plugin for higher'
        print 'speed.'
        print


    def checkweather(self):
        # We don't want to do this every 30 seconds, so we need
        # to cache the date somewhere.
        #
        # First check the age of the cache.
        #
        if (os.path.isfile(self.WEATHERCACHE) == 0 or \
            (abs(time.time() - os.path.getmtime(self.WEATHERCACHE)) > 3600)):
            try:
                rf=pymetar.ReportFetcher(self.METARCODE)
                rep=rf.FetchReport()
                rp=pymetar.ReportParser()
                pr=rp.ParseReport(rep)
                if (pr.getTemperatureCelsius()):
                    if self.TEMPUNITS == 'F':
                        temperature = '%2d' % pr.getTemperatureFahrenheit()
                    elif self.TEMPUNITS == 'K':
                        ktemp = pr.getTemperatureCelsius() + 273
                        temperature = '%3d' % ktemp
                    else:
                        temperature = '%2d' % pr.getTemperatureCelsius()
                else:
                    temperature = '?'  # Make it a string to match above.
                if pr.getPixmap():
                    icon = pr.getPixmap() + '.png'
                else:
                    icon = 'sun.png'
                cachefile = open(self.WEATHERCACHE,'w+')
                cachefile.write(temperature + '\n')
                cachefile.write(icon + '\n')
                cachefile.close()
            except:
                try:
                    # HTTP Problems, use cache. Wait till next try.
                    cachefile = open(self.WEATHERCACHE,'r')
                    newlist = map(string.rstrip, cachefile.readlines())
                    temperature,icon = newlist
                    cachefile.close()
                except IOError:
                    print 'WEATHER: error reading cache. Using fake weather.'
                    try:
                        cachefile = open(self.WEATHERCACHE,'w+')
                        cachefile.write('?' + '\n')
                        cachefile.write('sun.png' + '\n')
                        cachefile.close()
                    except IOError:
                        print 'You have no permission to write %s' % self.WEATHERCACHE
                    return '0', 'sun.png'


        else:
            cachefile = open(self.WEATHERCACHE,'r')
            newlist = map(string.rstrip, cachefile.readlines())
            temperature,icon = newlist
            cachefile.close()
        return temperature, icon

    def draw(self, (type, object), x, osd):
        temp,icon = self.checkweather()
        font  = osd.get_font('small0')
        osd.draw_image(os.path.join(config.ICON_DIR, 'weather/' + icon),
                        (x, osd.y + 15, -1, -1))
        temp = u'%s\xb0' % temp
        width = font.stringsize(temp)
        osd.write_text(temp, font, None, x + 15, osd.y + 55 - font.h, width, font.h,
                       'left', 'top')
        return width + 15
