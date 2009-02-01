# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# weather.py - IdleBarplugin for weather
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
import time
import string
from threading import Thread, Condition

import kaa.imlib2 as imlib2

import config
import plugin
from plugins.idlebar import IdleBarPlugin
import util.pymetar as pymetar

from benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL


class WeatherFetcher(Thread):
    """
    Class to fetch the weather in a thread
    """
    def __init__(self, refreshinterval, metarcode, tempunits, cachefile):
        """ Initialise the thread """
        Thread.__init__(self)
        _debug_('WeatherFetcher.__init__(refreshinterval=%r, metarcode=%r, tempunits=%r, cachefile=%r)' % (
            refreshinterval, metarcode, tempunits, cachefile), 2)
        self.refreshinterval = refreshinterval
        self.metarcode = metarcode
        self.tempunits = tempunits
        self.cachefile = cachefile
        self.stopping = False
        self.temperature = '?'
        self.icon = 'na.png'


    @benchmark(benchmarking & 0x1, benchmarkcall)
    def run(self):
        """
        Thread to fetch the weather and write the results to a cache file
        """
        _debug_('WeatherFetcher(%r) thread started' % (self.metarcode,), 1)
        while not self.stopping:
            refreshtime = time.time() + self.refreshinterval
            _debug_('WeatherFetcher(%r).run' % (self.metarcode,), 1)
            try:
                rf = pymetar.ReportFetcher(self.metarcode)
                rp = pymetar.ReportParser()
                rep = rf.FetchReport()
                pr = rp.ParseReport(rep)

                if pr.getTemperatureCelsius():
                    if self.tempunits == 'F':
                        self.temperature = '%2d' % pr.getTemperatureFahrenheit()
                    elif self.tempunits == 'K':
                        self.temperature = '%3d' % pr.getTemperatureCelsius() + 273
                    else:
                        self.temperature = '%2d' % pr.getTemperatureCelsius()
                else:
                    self.temperature = '?'

                if pr.getPixmap():
                    self.icon = pr.getPixmap() + '.png'
                else:
                    self.icon = 'na.png'

                try:
                    cachefile = open(self.cachefile, 'w+')
                    cachefile.write(self.temperature + '\n')
                    cachefile.write(self.icon + '\n')
                    cachefile.close()
                    _debug_('WeatherFetcher cache (%s %s)' % (self.temperature, self.icon), 1)
                except IOError, why:
                    _debug_('Failed to create %r: %s' % (self.cachefile, why), DWARNING)

            except Exception, why:
                _debug_(why, DERROR)

            _debug_('WeatherFetcher(%r).ran' % (self.metarcode,), 1)

            while time.time() < refreshtime:
                if self.stopping:
                    break
                time.sleep(1)
        _debug_('WeatherFetcher(%r) thread finished' % (self.metarcode,), 1)



class PluginInterface(IdleBarPlugin):
    """
    Shows the current weather.

    Activate with:
    | plugin.activate('idlebar.weather', level=30, args=('4-letter code', ))

    For weather station codes see: http://www.nws.noaa.gov/tg/siteloc.shtml
    You can also set the unit as second parameter in args ('C', 'F', or 'K')
    """

    def __init__(self, zone='CYYZ', units='C'):
        """
        Initialise an instance of the PluginInterface
        """
        _debug_('PluginInterface.__init__(zone=%r, units=%r)' % (zone, units), 2)
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.weather'
        self.tempunits = units
        self.metarcode = zone
        self.cachefile = config.FREEVO_CACHEDIR + '/weather'
        self.cachetime = 0
        self.fetcher = WeatherFetcher(config.IDLEBAR_WEATHER_REFRESH, self.metarcode, self.tempunits, self.cachefile)
        self.fetcher.start()


    def config(self):
        return [
            ('IDLEBAR_WEATHER_REFRESH', 3600, 'The time to refresh the weather cache'),
        ]


    def shutdown(self):
        """
        System Shutdown; stop the fetcher thread and wait for it to finish
        """
        _debug_('shutdown()', 2)
        self.fetcher.stopping = True
        self.fetcher.join()


    def checkweather(self):
        """
        We don't want to do this every 30 seconds, so we need
        to cache the date somewhere.
        """
        _debug_('checkweather()', 2)
        try:
            temperature, icon = '?', 'na.png'
            if os.path.isfile(self.cachefile):
                cachefd = open(self.cachefile, 'r')
                newlist = map(string.rstrip, cachefd.readlines())
                temperature, icon = newlist
                cachefd.close()
            return temperature, icon
        except Exception, why:
            _debug_(why, DERROR)


    def calc_positions(self, osd, image_w, image_h, text_w, text_h):
        """
        Calculate the position of the image and text
        @returns: tuple of positions and width
        """
        if image_w >= text_w:
            image_x = 0
            text_x = ((image_w - text_w) / 2)
        else:
            image_x = ((text_w - image_w) / 2)
            text_x = 0
        image_y = osd.y + 7
        text_y = osd.y + 55 - text_h
        width = image_w > text_w and image_w or text_w
        return (image_x, image_y, text_x, text_y, width)


    def draw(self, (type, object), x, osd):
        """
        Draw the icon and temperature on the idlebar
        @returns: width of the icon
        """
        _debug_('draw((type=%r, object=%r), x=%r, osd=%r)' % (type, object, x, osd), 2)
        temp, icon = self.checkweather()
        image_file = os.path.join(config.ICON_DIR, 'weather', icon)
        w, h = imlib2.open(image_file).size
        temperature = u'%s\xb0' % temp
        font = osd.get_font(config.OSD_IDLEBAR_FONT)
        widthtxt = font.stringsize(temperature)
        (image_x, image_y, text_x, text_y, width) = self.calc_positions(osd, w, h, widthtxt, font.h)
        osd.draw_image(image_file, (x+image_x, image_y, -1, -1))
        osd.write_text(temperature, font, None, x+text_x, text_y, widthtxt, font.h, 'center', 'top')
        return width
