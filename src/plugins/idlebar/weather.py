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


class WeatherFetcher(Thread):
    """
    Class to fetch the weather in a thread
    """
    def __init__(self, condition, metarcode, tempunits, cachefile):
        """ Initialise the thread """
        Thread.__init__(self)
        _debug_('WeatherFetcher.__init__(condition=%r, metarcode=%r, tempunits=%r, cachefile=%r)' % (condition, metarcode, tempunits, cachefile), 2)
        self.condition = condition
        self.metarcode = metarcode
        self.tempunits = tempunits
        self.cachefile = cachefile
        self.stopping = False

    def run(self):
        _debug_('WeatherFetcher.run()', 2)
        self.condition.acquire()
        _debug_('WeatherFetcher condition.acquired', 2)
        try:
            while not self.stopping:
                _debug_('WeatherFetcher condition.waiting', 2)
                self.condition.wait()
                _debug_('WeatherFetcher condition.waited', 2)
                if self.stopping:
                    break
                #_debug_('ReportFetcher(%r)' % (self.metarcode,), 2)
                try:
                    rf = pymetar.ReportFetcher(self.metarcode)
                    rep = rf.FetchReport()
                    rp=pymetar.ReportParser()
                    pr=rp.ParseReport(rep)
                    if (pr.getTemperatureCelsius()):
                        if self.tempunits == 'F':
                            temperature = '%2d' % pr.getTemperatureFahrenheit()
                        elif self.tempunits == 'K':
                            ktemp = pr.getTemperatureCelsius() + 273
                            temperature = '%3d' % ktemp
                        else:
                            temperature = '%2d' % pr.getTemperatureCelsius()
                    else:
                        temperature = '?'  # Make it a string to match above.
                    if pr.getPixmap():
                        icon = pr.getPixmap() + '.png'
                    else:
                        icon = 'na.png'
                    try:
                        cachefile = open(self.cachefile, 'w+')
                        cachefile.write(temperature + '\n')
                        cachefile.write(icon + '\n')
                        cachefile.close()
                        _debug_('WeatherFetcher cache written', 2)
                    except IOError, why:
                        _debug_('Failed to create %r: %s' % (self.cachefile, why), 2)

                except Exception, why:
                    _debug_(why, 2)
        finally:
            self.condition.release()
            _debug_('WeatherFetcher condition.released', 2)



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
        """
        _debug_('PluginInterface.__init__(zone=%r, units=%r)' % (zone, units), 2)
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        IdleBarPlugin.__init__(self)
        self.plugin_name = 'idlebar.weather'
        self.TEMPUNITS = units
        self.METARCODE = zone
        self.WEATHERCACHE = config.FREEVO_CACHEDIR + '/weather'
        self.cachetime = 0
        self.condition = Condition()
        self.fetcher = WeatherFetcher(self.condition, self.METARCODE, self.TEMPUNITS, self.WEATHERCACHE)
        self.fetcher.start()


    def config(self):
        return [
            ('IDLEBAR_WEATHER_REFRESH', 3600, 'The time to refresh the weather cache'),
        ]


    def shutdown(self):
        _debug_('shutdown()', 2)
        self.condition.acquire()
        _debug_('checkweather condition.acquired', 2)
        try:
            self.condition.notifyAll()
        finally:
            self.condition.release()
        self.fetcher.stopping = True
        self.fetcher.join()


    def checkweather(self):
        """
        We don't want to do this every 30 seconds, so we need
        to cache the date somewhere.
        """
        _debug_('checkweather()', 2)
        self.condition.acquire()
        _debug_('checkweather condition.acquired', 2)
        try:
            try:
                if os.path.isfile(self.WEATHERCACHE):
                    cachetime = os.path.getmtime(self.WEATHERCACHE)
                else:
                    cachetime = 0
                # Tell the thread to run once
                if time.time() - cachetime > config.IDLEBAR_WEATHER_REFRESH:
                    self.condition.notify()
                    _debug_('checkweather condition.notified', 2)

                # First time around or when there is no network there may be no weather cache file
                _debug_('cachetime=%r diff=%s' % (cachetime, cachetime - self.cachetime), 2)
                if cachetime:
                    cachefile = open(self.WEATHERCACHE, 'r')
                    newlist = map(string.rstrip, cachefile.readlines())
                    temperature, icon = newlist
                    cachefile.close()
                    self.cachetime = cachetime
                    _debug_('checkweather returning %r' % ((temperature, icon),), 2)
                    return temperature, icon
                else:
                    _debug_('checkweather returning %r' % (('?', 'na.png'),), 2)
                return '?', 'na.png'
            except Exception, why:
                _debug_(why, 2)
        finally:
            self.condition.release()
            _debug_('checkweather condition.released', 2)


    def calc_positions(self, osd, image_w, image_h, text_w, text_h):
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
