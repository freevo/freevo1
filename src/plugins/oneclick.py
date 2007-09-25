# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# oneclick.py - a plugin to obtain detailed weather forecast information
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:
#   X pull down weather on demand MENU_SELECT (need to fix popup behavior)
#   X Ability to specify custom location name in ONECLICK_LOCATIONS
#   - get location name back onto details screen
#   - i18n support
#   - a freevo helper to grab weather data behind the scenes
#
# activate:
#
#    plugin.activate('oneclick', level=45)
#    ONECLICK_LOCATIONS = [ ("USNC0559", "", "Home sweet home", 0) ]
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

#python modules
import os, stat, re, copy
import sys

# date/time
import time

#regular expression
import re

# rdf modules
from xml.dom.ext.reader import Sax2
import urllib, urllib2

#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui.PopupBox import PopupBox
from item import Item

from weatherdata import WeatherData

GUI = True
if __name__ == '__main__':
    GUI = False

#get the singletons so we get skin info and access the osd
skin = skin.get_singleton()
osd = osd.get_singleton()

#check every 1 hour
WEATHER_AGE = 3600
WEATHER_AGE = 3600 * 24
WEATHER_DIR = os.path.join(config.SHARE_DIR, 'images', 'weather')
WEATHER_DIR = '/sources/svn/freevo-1.x/testing/Duncan/weather/1click/images'

#FIXME Not sure that all of these are correctly named
WEATHER_ICONS = {
#  icon      twc.com      image               fallback
     '0': ( 'twc/0.png', 'thunderstorm.png', 'thunshowers.png'),
     '1': ( 'twc/1.png', 'thunderstorm.png', 'thunshowers.png'),
     '2': ( 'twc/2.png', 'thunderstorm.png', 'thunshowers.png'),
     '3': ( 'twc/3.png', 'thunderstorm.png', 'thunshowers.png'),
     '4': ( 'twc/4.png', 'thunderstorm.png', 'thunshowers.png'),
     '5': ( 'twc/5.png', 'sleet.png', 'rainsnow.png'),
     '6': ( 'twc/6.png', 'hail.png', 'rainsnow.png'),
     '7': ( 'twc/7.png', 'mixed.png', 'rainsnow.png'),
     '8': ( 'twc/8.png', 'freezingfog.png', 'fog.png'),
     '9': ( 'twc/9.png', 'drizzle.png', 'fog.png'),
    '10': ('twc/10.png', 'freezingrain.png', 'rainsnow.png'),
    '11': ('twc/11.png', 'lightrain.png', 'lshowers.png'),
    '12': ('twc/12.png', 'rain.png', 'showers.png'),
    '13': ('twc/13.png', 'lightsnowshowers.png', 'flurries.png'),
    '14': ('twc/14.png', 'mediumsnowshowers.png', 'flurries.png'),
    '15': ('twc/15.png', 'freshsnow.png', 'flurries.png'),
    '16': ('twc/16.png', 'snow.png', 'flurries.png'),
    '17': ('twc/17.png', 'thunderstorm.png', 'thunshowers.png'),
    '18': ('twc/18.png', 'drizzle.png', 'showers.png'),
    '19': ('twc/19.png', 'dust.png', 'fog.png'),
    '20': ('twc/20.png', 'mist.png', 'fog.png'),
    '21': ('twc/21.png', 'haze.png', 'fog.png'),
    '22': ('twc/22.png', 'smoke.png', 'fog.png'),
    '23': ('twc/23.png', 'windy.png', 'pcloudy.png'),
    '24': ('twc/24.png', 'windy.png', 'pcloudy.png'),
    '25': ('twc/25.png', 'freezing.png', 'pcloudy.png'),
    '26': ('twc/26.png', 'cloudy-n.png', 'pcloudy.png'),
    '27': ('twc/27.png', 'mostlycloudy-n.png', 'mcloudy.png'),
    '28': ('twc/28.png', 'mostlycloudy.png', 'mcloudy.png'),
    '29': ('twc/29.png', 'partlycloudy-n.png', 'pcloudy.png'),
    '30': ('twc/30.png', 'partlycloudy.png', 'pcloudy.png'),
    '31': ('twc/31.png', 'clear-n.png', 'sunny.png'),
    '32': ('twc/32.png', 'sunny.png', 'sunny.png'),
    '33': ('twc/33.png', 'mostlyclear.png', 'sunny.png'),
    '34': ('twc/34.png', 'mostlysunny.png', 'sunny.png'),
    '35': ('twc/35.png', 'thunderstorm.png', 'thunshowers.png'),
    '36': ('twc/36.png', 'hotandsunny.png', 'sunny.png'),
    '37': ('twc/37.png', 'isolatedthunderstorms.png', 'thunshowers.png'),
    '38': ('twc/38.png', 'scatteredthunderstorms.png', 'thunshowers.png'),
    '39': ('twc/39.png', 'sunnyintervals.png', 'showers.png'),
    '40': ('twc/40.png', 'heavyrain.png', 'showers.png'),
    '41': ('twc/41.png', 'snowshowers.png', 'snowshow.png'),
    '42': ('twc/42.png', 'snow.png', 'rainsnow.png'),
    '43': ('twc/43.png', 'snow.png', 'rainsnow.png'),
    '44': ('twc/44.png', 'na.png', 'unknown.png'),
    '45': ('twc/45.png', 'rainshowers-n.png', 'rainsnow.png'),
    '46': ('twc/46.png', 'snowshowers-n.png', 'snowshow.png'),
    '47': ('twc/47.png', 'scatteredthunderstorms-n.png', 'thunshowers.png'),
    'na': ('twc/na.png', 'na.png', 'unknown.png'),
}


def wget(url):
    ''' get a file from the url '''
    _debug_('wget(%s)' % (url), 2)
    txdata = None
    txheaders = {
        'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.7) Gecko/20070914 Firefox/2.0.0.7'
    }
    req = urllib2.Request(url, txdata, txheaders)
    try:
        t1 = time.time()
        response = urllib2.urlopen(req)
        try:
            data = response.read()
        finally:
            response.close()
            t2 = time.time()
        if response.msg == 'OK':
            return data
        _debug_('Downloaded "%s" in %.1f seconds' % (url, t2 - t1))
    except urllib2.HTTPError, error:
        print 'getting %r failed: %s' % (url, error)
    except ValueError, error:
        try:
            fd = open(url)
            data = fd.read()
            fd.close()
            return data
        except:
            print 'invalid url %r failed: %s' % (url, error)
    return None


def toCelcius(fTemp):
    _debug_('toCelcius(fTemp)', 2)
    try:
        tTemp = float (fTemp )
    except ValueError:
        tTemp = 0.0
    nTemp = (5.0/9.0)*(tTemp - 32.0)
    return "%d" % (nTemp,)

def toKilometers(miles):
    _debug_('toKilometers(miles)', 2)
    try:
        tTemp = float(miles)
    except ValueError:
        tTemp = 0.0
    nTemp = tTemp*1.6
    return "%d" % (int(nTemp),)

def toBarometer(baro):
    _debug_('toBarometer(baro)', 2)
    try:
        tTemp = float(baro)
    except ValueError:
        tTemp = 0.0
    nTemp = tTemp*3.386
    return "%.1f" % (nTemp,)


class PluginInterface(plugin.MainMenuPlugin):
    '''
    A plugin to obtain more detailed weather forecast information

    To activate, put the following lines in local_conf.py:

    plugin.activate('oneclick', level=45)
    ONECLICK_LOCATIONS = [
      ("<loc>", [metric], [mapuri], [location name]),
      ("<loc>", [metric], [mapuri], [location name]),
    ...
    ]

    where:
    <loc> is a zipcode or an airport code
    [metric] (1 == convert to SI Units; 0 == do not convert)
    [mapuri] is the map's url, doesn't parse the page for a map url
    [location name] is a custom name you wish to use for this location
    '''
    def __init__(self):
        '''
        '''
        _debug_('PluginInterface.__init__()', 2)
        if not hasattr(config, 'ONECLICK_LOCATIONS'):
            self.reason = 'ONECLICK_LOCATIONS not defined'
            return
        plugin.MainMenuPlugin.__init__(self)

    def config(self):
        '''
        '''
        _debug_('config()', 2)
        return [
            ('ONECLICK_LOCATIONS', [('USNC0559', 0)], 'Location codes for current conditions and forecasts'),
            ('ONECLICK_URL_CURC', 'http://ff.1click.weather.com/weather/local/%s?cc=*%s', 'Current Conditions URL'),
            ('ONECLICK_URL_DAYF', 'http://ff.1click.weather.com/weather/local/%s?dayf=5%s', 'Day Forecast URL'),
            ('ONECLICK_URL_ELOC', 'http://ff.1click.weather.com/weather/local/%s?eloc=st', 'Extended Location URL'),
            ('ONECLICK_URL_MAP',  'http://www.weather.com/weather/map/%s?from=LAPmaps', 'Radar Map URL')
        ]

    def items(self, parent):
        '''
        '''
        _debug_('items(self, parent)', 2)
        return [ WeatherMainMenu(parent) ]


class WeatherItem(Item):
    '''
    Item for the menu for one feed
    '''
    def __init__(self, parent, location):
        _debug_('WeatherItem.__init__(parent=%r, location=%r)' % (parent, location), 2)
        Item.__init__(self, parent)

        self.parent = parent

        # Flag to indicate whether this item is able to be displayed
        self.error = 0

        self.location = None
        self.ismetric = False
        self.name = None
        self.city = None
        self.state = None
        self.tm = None
        self.latitude = None
        self.longitude = None
        self.sunrise = None
        self.sunset = None

        self.unit_t = None
        self.unit_d = None
        self.unit_s = None
        self.unit_p = None
        self.unit_r = None
        self.country = None

        self.updated = 0.0
        self.observation_station = None
        self.temperature = None
        self.feeling = None
        self.current_conditions = None
        self.icon = None
        self.pressure = None
        self.pressure_change = None
        self.wind_speed = None
        self.wind_direction = None
        self.humidity = None
        self.visibility = None
        self.uv_index = None
        self.uv_type = None
        self.dew_point = None
        self.moon_icon = None
        self.moon_phase = None

        self.description = None
        self.forecastData = None
        self.pastTime = 0
        self.date = []
        self.weatherIcon = []
        self.highTemp = []
        self.lowTemp = []
        self.weatherType = []
        self.wdata = []
        self.popupParam = None
        self.mapuri = None

        if isinstance(location, tuple):
            self.location = location[0]
            if len(location) > 1:
                self.ismetric = bool(location[1])
            if len(location) > 2:
                self.mapuri = str(location[2])
            if len(location) > 3:
                self.name = str(location[3])
        else:
            self.location = location
            self.ismetric = False

        self.popupParam = Unicode(self.location)
        if self.name:
            self.popupParam = Unicode(self.name)

        self.units = self.ismetric and '&unit=m' or ''
        self.url_curc = config.ONECLICK_URL_CURC % (urllib.quote(self.location), self.units)
        self.url_dayf = config.ONECLICK_URL_DAYF % (urllib.quote(self.location), self.units)
        self.url_eloc = config.ONECLICK_URL_ELOC % (urllib.quote(self.location))
        self.mapurl = config.ONECLICK_URL_MAP % (self.location,)
        self.weatherData = None
        self.weatherMapData = None

        self.cacheDir = '%s/weather_%s' % (config.FREEVO_CACHEDIR, self.location)
        self.cacheElocation = '%s/location.pickle' % (self.cacheDir)
        self.cacheCurrent = '%s/current.pickle' % (self.cacheDir)
        self.cacheForecast = '%s/forecast.pickle' % (self.cacheDir)
        self.mapFile = '%s/map.jpeg' % (self.cacheDir)
        self.mapPage1 = '%s/mappage1.html' % (self.cacheDir)
        self.mapPage2 = '%s/mappage2.html' % (self.cacheDir)
        if not os.path.isdir(self.cacheDir):
            os.mkdir(self.cacheDir, stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))
        self.last_update = 0

        #get forecast data
        self.getForecast()

    def getForecast(self, force=0):
        '''grab the forecast, updating for the website if needed'''
        _debug_('getForecast(force=%s)' % (force), 2)

        # check cache
        try:
            if force or self.needsRefresh():
                self.updateData()
                self.updateMap()
            else:
                self.loadFromCache()
        except IOError, e:
            self.error = 1
            print "failed to update data for '%s': %s" % (self.location, e)
        else:
            # set the last update timestamp
            self.last_update = os.path.getmtime(self.cacheCurrent)

            # now convert the self.weatherData structure to parsable information
            self.convertWeatherData()
            try:
                self.convertWeatherData()
            except Exception, error:
                print 'Failed to convert data for %s: %s' % (self.location, error)


    def needsRefresh(self):
        '''is the cache too old?'''
        _debug_('needsRefresh()', 2)
        if (os.path.isfile(self.cacheCurrent) == 0 or \
            (abs(time.time() - os.path.getmtime(self.cacheCurrent)) > WEATHER_AGE)):
            return 1
        else:
            return 0

    def updateData(self):
        '''update the cache data from the 1click service
        @notes the elocation is not updated as it is static
        '''
        _debug_('updateData()', 2)
        if GUI:
            popup = PopupBox(text=_('Fetching Weather for %s...') % self.popupParam)
            popup.show()

        if not os.path.isfile(self.cacheElocation):
            try:
                elocationData = wget(self.url_eloc)
                self.elocationData = elocationData
            except Exception, error:
                print 'Failed to get extended location data for %s: %s' % (self.location, error)
        else:
            self.elocationData = util.read_pickle(self.cacheElocation)

        try:
            self.currentData = wget(self.url_curc)
            #print 'currentData:', self.currentData
        except Exception, error:
            print 'Failed to get the current conditions data for %s: %s' % (self.location, error)
            if os.path.isfile(self.cacheCurrent):
                self.currentData = util.read_pickle(self.cacheCurrent)
            else:
                self.currentData = None
        try:
            self.forecastData = wget(self.url_dayf)
            #print 'forecastData:', self.forecastData
        except Exception, error:
            print 'Failed to get the forecast data for %s: %s' % (self.location, error)
            if os.path.isfile(self.cacheForecast):
                self.forecastData = util.read_pickle(self.cacheForecast)
            else:
                self.forecastData = None

        if GUI:
            popup.destroy()

        if not self.currentData or not self.forecastData:
            # raise an error
            return

        self.saveToCache()
        return


    def updateMap(self):
        ''' Update the weather map '''
        _debug_('updateMap()', 2)
        # obtain radar map
        if self.mapuri:
            try:
                if GUI:
                    popup = PopupBox(text=_('Fetching Radar Map for %s...') % self.popupParam)
                    popup.show()
                try:
                    self.weatherMapData = wget(self.mapuri)
                    self.saveMapToCache()
                except Exception, error:
                    print 'Cannot download the map for "%s" from %s: %s' % (self.location, self.mapuri, error)
                return
            finally:
                if GUI:
                    popup.destroy()

        try:
            if GUI:
                popup = PopupBox(text=_('Fetching Radar Map for %s...') % self.popupParam)
                popup.show()
            # get the first web page
            weatherPage = wget(self.mapurl)
            if config.DEBUG:
                f = open(self.mapPage1, 'w')
                f.write(weatherPage)
                f.close()
            try:
                # find link to map page
                regexp = re.compile ('if \(isMinNS4\) var mapNURL = "([^"]*)";', re.IGNORECASE)
                results = regexp.search(weatherPage)
                print 'weatherPage=%r' % (results.groups())
                weatherPage2 = "http://www.weather.com/%s" % (results.groups()[0])

                mapPage = wget(weatherPage2)
                if config.DEBUG:
                    f = open(self.mapPage2, 'w')
                    f.write(weatherPage)
                    f.close()
                # find a link to the real weather map
                regexp = re.compile('<img NAME="mapImg" SRC="(http://image.weather.com[^"]*jpg)"', re.IGNORECASE)
                results = regexp.search(mapPage)
                print 'mapPage=%r' % (results.groups())
                self.mapuri = results.groups()[0]
                self.weatherMapData = wget(self.mapuri)
                self.saveMapToCache()
                return
            except Exception, error:
                print 'Cannot download the map for "%s" from %s: %s' % (self.location, self.mapurl, error)

        finally:
            if GUI:
                popup.destroy()

    def saveToCache(self):
        _debug_('saveToCache()', 2)
        util.save_pickle(self.elocationData, self.cacheElocation)
        util.save_pickle(self.currentData, self.cacheCurrent)
        util.save_pickle(self.forecastData, self.cacheForecast)

    def saveMapToCache(self):
        ''' save weather map to the cache '''
        try:
            if self.weatherMapData is not None:
                imgfd = os.open(self.mapFile, os.O_CREAT|os.W_OK)
                os.write(imgfd, self.weatherMapData)
                os.close(imgfd)
        except Exception, error:
            print 'failed saving weather map to cache "%s": %s' % (self.mapFile, error)

    def loadFromCache(self):
        ''' load the data and the map from the cache '''
        _debug_('loadFromCache()', 2)
        self.elocationData = util.read_pickle(self.cacheElocation)
        self.currentData = util.read_pickle(self.cacheCurrent)
        self.forecastData = util.read_pickle(self.cacheForecast)

        try:
            size = int(os.stat(self.mapFile)[6])
        except Exception, error:
            _debug_('failed loading weather map for "%s" from cache: %s' % (self.location, error), config.DWARNING)
            pass
        else:
            imgfd = os.open(self.mapFile, os.R_OK)
            self.weatherMapData = os.read(imgfd, size)
            os.close(imgfd)

    def actions(self):
        ''' return a list of actions for this item '''
        _debug_('actions()', 2)
        return [ (self.start_detailed_interface, _('Show Weather Details')) ]

    def start_detailed_interface(self, arg=None, menuw=None):
        ''' detail handler '''
        _debug_('start_detailed_interface(arg=%r, menuw=%r)' % (arg, menuw), 2)
        WeatherDetailHandler(arg, menuw, self)

    def isValid(self):
        ''' reports is an error was detected '''
        _debug_('isValid()', 2)
        return not self.error

    def getLastUpdated(self):
        ''' parse the lsup time
        @notes there seems to be a problem with AM/PM not parsing correctly
        '''
        _debug_('getLastUpdated() "%s"' % self.updated, 2)
        try:
            value = time.strptime(self.updated.replace(' AM Local Time', ''), '%m/%d/%y %H:%M')
            return time.strftime("%c", time.localtime(time.mktime(value)))
        except ValueError, e:
            try:
                value = time.strptime(self.updated.replace(' PM Local Time', ''), '%m/%d/%y %H:%M')
                (year, mon, day, hour, min, sec, weekday, yearday, saving) = value
                value = (year, mon, day, hour+12, min, sec, weekday, yearday, saving)
                return time.strftime("%c", time.localtime(time.mktime(value)))
            except ValueError, error:
                print error
                return self.updated.replace(' Local Time', '')
        #if self.ismetric:
        #    return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(self.updated))
        #else:
        #    return time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(self.updated))

    def getObservationStation(self):
        ''' get the observation station '''
        _debug_('getObservationStation()', 2)
        return "%s" % (self.observation_station)

    def getTemperature(self):
        _debug_('getTemperature()', 2)
        return u"%s\xb0%s" % (self.temperature, self.unit_t)

    def getFeeling(self):
        _debug_('getFeeling()', 2)
        return u"%s\xb0%s" % (self.feeling, self.unit_t)

    def getCurrentCondition(self):
        ''' gets the current conditions '''
        _debug_('getCurrentCondition()', 2)
        return "%s" % (self.current_conditions)

    def getIcon(self):
        ''' gets the current conditions icon '''
        _debug_('getIcon()', 2)
        return "%s" % (self.icon)

    def getPressure(self):
        _debug_('getPressure()', 2)
        if self.pressure_change == 'N/A':
            return "%s %s" % (self.pressure, self.unit_p)
        return "%s %s %s %s" % (self.pressure, self.unit_p, _('and'), self.pressure_change)

    def getPressureValue(self):
        _debug_('getPressureValue()', 2)
        return "%s %s" % (self.pressure, self.unit_p)

    def getPressureChange(self):
        _debug_('getPressureChange()', 2)
        return "%s" % (self.pressure_change)

    def getWind(self):
        _debug_('getWind()', 2)
        if self.wind_direction == 'CALM':
            return "%s" % (self.wind_speed)
        elif self.wind_direction == 'VAR':
            return "%s %s %s %s" % (_('Variable'), _('at'), self.wind_speed, self.unit_s)
        return "%s %s %s %s" % (self.wind_direction, _('at'), self.wind_speed, self.unit_s)

    def getWindDir(self):
        _debug_('getWindDir()', 2)
        return "%s" % (self.wind_direction)

    def getWindSpeed(self):
        _debug_('getWindSpeed()', 2)
        return "%s %s" % (self.wind_speed, self.unit_s)

    def getHumidity(self):
        _debug_('getHumidity()', 2)
        return "%s%%" % (self.humidity)

    def getVisibility(self):
        _debug_('getVisibility()', 2)
        return "%s %s" % (self.visibility, self.unit_d)

    def getUvIndex(self):
        _debug_('getUvIndex()', 2)
        return "%s" % (self.uv_index)

    def getUvType(self):
        _debug_('getUvType()', 2)
        return "%s" % (self.uv_type)

    def getDewPoint(self):
        _debug_('getDewPoint()', 2)
        return u"%s\xb0%s" % (self.dew_point, self.unit_t)

    def getMoonIcon(self):
        _debug_('getMoonIcon()', 2)
        return "%s" % (self.moon_icon)

    def getMoonPhase(self):
        _debug_('getMoonPhase()', 2)
        return "%s" % (self.moon_phase)

    def getSunrise(self):
        _debug_('getSunrise()', 2)
        return "%s" % (self.sunrise)

    def getSunset(self):
        _debug_('getSunset()', 2)
        return "%s" % (self.sunset)


    def convertWeatherData(self):
        '''
        convert the xml weather information for the skin
        '''
        _debug_('convertWeatherData()', 2)
        #print self.elocationData
        #print self.currentData
        #print self.forecastData
        elocation = WeatherData(self.elocationData)
        current = WeatherData(self.currentData)
        forecast = WeatherData(self.forecastData)

        if not self.name:
            self.name = elocation.loc.dnam

        dnam = elocation.loc.dnam.split(', ')
        ctry = elocation.eloc.ctry
        if ctry in ('US'):
            self.city = dnam[0]
            self.state = dnam[1]
            self.country = ctry
        else:
            self.city = dnam[0]
            self.state = ''
            self.country = dnam[1]
        print 'city=%s, state=%s, country=%s' % (self.city, self.state, self.country)

        # reset variables
        self.date = []
        self.weatherIcon = []
        self.highTemp = []
        self.lowTemp = []
        self.weatherType = []

        self.unit_t = current.head.ut
        self.unit_d = current.head.ud
        self.unit_s = current.head.us
        self.unit_p = current.head.up
        self.unit_r = current.head.ur

        self.tm = current.loc.tm
        self.latitude = current.loc.lat
        self.longitude = current.loc.lon
        self.sunrise = current.loc.sunr
        self.sunset = current.loc.suns
        self.zone = current.loc.zone

        self.updated = current.cc.lsup
        self.observation_station = current.cc.obst
        self.temperature = current.cc.tmp
        self.feeling = current.cc.flik
        self.current_conditions = current.cc.t
        self.icon = current.cc.icon
        self.pressure = current.cc.bar.r
        self.pressure_change = current.cc.bar.d
        self.wind_speed = current.cc.wind.s
        self.wind_direction = current.cc.wind.t
        self.humidity = current.cc.hmid
        self.visibility = current.cc.vis
        self.uv_index = current.cc.uv.i
        self.uv_type = current.cc.uv.t
        self.dew_point = current.cc.dewp
        self.moon_icon = current.cc.moon.icon
        self.moon_phase = current.cc.moon.t

        self.description = '%s %s %s' % (self.current_conditions, _("at"), self.getTemperature())
        self.image = self.getDayImage(self.icon)

        # skip today in the days
        for day in forecast.dayf.days[1:]:
            self.date.append(day.t)
            self.highTemp.append(day.hi)
            self.lowTemp.append(day.low)
            for part in day.parts:
                if part.p == 'd':
                    self.weatherIcon.append(self.getDayImage(part.icon))
                    self.weatherType.append(part.t)


    def getDayImage(self, num):
        '''obtain the weather icons for multiple day forecast'''
        _debug_('getDayImage()', 2)

        icon = os.path.join(WEATHER_DIR, WEATHER_ICONS[num][1])
        if not os.path.isfile(icon):
            icon = os.path.join(WEATHER_DIR, WEATHER_ICONS[num][2])
            if not os.path.isfile(icon):
                icon = os.path.join(WEATHER_DIR, WEATHER_ICONS[num][0])
        if not os.path.isfile(icon):
            icon = os.path.join(WEATHER_DIR, 'na.png')
        print '%s: %s %s' % (num, icon, os.path.split(WEATHER_ICONS[num][1])[1])
        return icon


    def getMoonImage(self, num):
        '''obtain the weather icons for multiple day forecast'''
        _debug_('getMoonImage()', 2)

        icon = os.path.join(WEATHER_DIR, 'moons', '%s.png' % (num))
        print '%s: %s' % (num, icon)
        return icon


class WeatherMainMenu(Item):
    '''
    this is the item for the main menu and creates the list
    of Weather Locations in a submenu.
    '''
    def __init__(self, parent):
        _debug_('WeatherMainMenu.__init__(parent=%r)' % (parent), 2)
        Item.__init__(self, parent, skin_type='oneclick')
        self.parent = parent
        self.name = _('Weather')

    def actions(self):
        ''' return a list of actions for this item '''
        _debug_('actions()', 2)
        items = [ (self.create_locations_menu , _('Locations')) ]
        return items

    def __call__(self, arg=None, menuw=None):
        ''' call first action in the actions list '''
        _debug_('__call__(arg=%r, menuw=%r)' % (arg, menuw), 2)
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)

    def create_locations_menu(self, arg=None, menuw=None):
        ''' '''
        _debug_('create_locations_menu(arg=%r, menuw=%r)' % (arg, menuw), 2)
        locations = []
        autoselect = 0
        # create menu items
        for location in config.ONECLICK_LOCATIONS:
            weather_item = WeatherItem(self, location)
            # Only display this entry if no errors were found
            if weather_item.isValid():
                locations.append (weather_item)

        # if only 1 valid location, autoselect it and go right to the detail screen
        if locations.__len__() == 1:
            autoselect = 1
            menuw.hide(clear=False)

        # if no locations were found, add a menu entry indicating that
        if not locations:
            nolocation = menu.MenuItem(_('No locations specified'), menuw.goto_prev_page, 0)
            locations.append(nolocation)

        # if only 1 valid menu entry present, autoselect it
        if autoselect:
            locations[0](menuw=menuw)
        else:
            # create menu
            weather_site_menu = menu.Menu(_('Locations'), locations)
            menuw.pushmenu(weather_site_menu)
            menuw.refresh()

class WeatherDetailHandler:
    '''
    A handler class to display several detailed forecast screens and catch events
    '''
    def __init__(self, arg=None, menu=None, weather=None):
        ''' '''
        _debug_('WeatherDetailHandler.__init__(arg=%r, menu=%r, weather=%r)' % (arg, menu, weather), 2)
        self.arg = arg
        self.menuw = menu
        self.weather = weather
        self.menuw.hide(clear=False)
        rc.app(self)

        self.skins = ('day', 'forecast', 'week', 'map')

        self.skin_num = 0
        self.subtitles = (_('Current Conditions'), _('Today\'s Forecast'),
                          _('Extended Forecast'), _('Radar Map'))

        self.title = ''
        self.subtitle = self.getSubtitle(self.skin_num)

        # Fire up splashscreen and load the plugins
        skin.draw('oneclick', self)

    def prevSkin(self):
        '''decrements the skin number round to the last skin'''
        _debug_('prevSkin()', 2)
        self.skin_num -= 1

        # out of bounds check, reset to size of skins array
        if self.skin_num < 0:
            self.skin_num = len(self.skins)-1
        self.subtitle = self.getSubtitle(self.skin_num)

    def nextSkin(self):
        '''increment the skin number round to the first skin'''
        _debug_('nextSkin()', 2)
        self.skin_num += 1

        # out of bounds check, reset to 0
        if self.skin_num >= len(self.skins):
            self.skin_num = 0
        self.subtitle = self.getSubtitle(self.skin_num)

    def getSubtitle(self, num):
        ''' returns the subtitle for a skin number '''
        _debug_('getSubtitle(num=%s)' % (num), 2)
        return '%s %s %s' % (self.subtitles[num], _('for'), self.weather.name)

    def eventhandler(self, event, menuw=None):
        '''eventhandler'''
        _debug_('eventhandler(event=%s, menuw=%r)' % (event, menuw), 2)
        if event == 'MENU_BACK_ONE_MENU':
            rc.app(None)
            self.menuw.show()
            return True

        elif event == 'MENU_SELECT':
            self.weather.getForecast(force=1)
            skin.clear()
            skin.draw('oneclick', self)
            return True

        elif event in ('MENU_DOWN', 'MENU_RIGHT'):
            self.nextSkin()
            skin.draw('oneclick', self)
            return True

        elif event in ('MENU_UP', 'MENU_LEFT'):
            self.prevSkin()
            skin.draw('oneclick', self)
            return True

        return False

if __name__ == '__main__':
    for location in config.ONECLICK_LOCATIONS:
        print location
        weather_item = WeatherItem(None, location)
        print weather_item
    import sys
    sys.exit(1)

class WeatherBaseScreen(skin.Area):
    ''' A base class for weather screens to inherit from, provides common members+methods '''
    def __init__(self):
        _debug_('WeatherBaseScreen.__init__()', 2)
        skin.Area.__init__(self, 'content')

        # Weather display fonts
        self.key_font = skin.get_font('medium0')
        self.val_font = skin.get_font('medium1')
        self.small_font = skin.get_font('small0')
        self.big_font = skin.get_font('huge0')

        # set the multiplier to be used in all screen drawing
        self.xmult = float(osd.width  - (config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT)) / 800
        self.ymult = float(osd.height - (config.OSD_OVERSCAN_TOP+config.OSD_OVERSCAN_BOTTOM)) / 600

        self.update_functions = (self.update_day, self.update_forecast,
                                 self.update_week, self.update_map)

    def update_day(self):
        '''
        '''
        _debug_('update_day()', 2)
        # display data
        text = _('Humidity')
        value = self.parent.weather.getHumidity()

        x_col1 = self.content.x + (50  * self.xmult)
        x_col2 = self.content.x + (250 * self.xmult)
        y_start = self.content.y + (60  * self.xmult)
        y_inc = 40 * self.ymult

        self.write_text(text, self.key_font, self.content,
            x=x_col1, y=y_start, height=-1, align_h='left')
        self.write_text(value, self.val_font, self.content,
            x=x_col2, y=y_start, height=-1, align_h='left')

        text = _('Pressure')
        value = self.parent.weather.getPressure()
        self.write_text(text, self.key_font, self.content,
            x=x_col1, y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value, self.val_font, self.content,
            x=x_col2, y=y_start+y_inc, height=-1, align_h='left')

        text = _('Wind')
        value = '%s' % (self.parent.weather.getWind())
        y_start   += y_inc
        self.write_text(text, self.key_font, self.content,
            x=x_col1, y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value, self.val_font, self.content,
            x=x_col2, y=y_start+y_inc, height=-1, align_h='left')

        text = _('Wind Chill')
        value = self.parent.weather.getFeeling()
        y_start   += y_inc
        self.write_text(text, self.key_font, self.content,
            x=x_col1, y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value, self.val_font, self.content,
            x=x_col2, y=y_start+y_inc, height=-1, align_h='left')

        text = _('Visibility')
        value = self.parent.weather.getVisibility()
        y_start   += y_inc
        self.write_text(text, self.key_font, self.content,
            x=x_col1, y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value, self.val_font, self.content,
            x=x_col2, y=y_start+y_inc, height=-1, align_h='left')

        text = _('UV Index')
        value = self.parent.weather.getUvType()
        y_start   += y_inc
        self.write_text(text, self.key_font, self.content,
            x=x_col1, y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value, self.val_font, self.content,
            x=x_col2, y=y_start+y_inc, height=-1, align_h='left')

        # draw current condition image
        x_start = self.content.x + (450*self.xmult)
        y_start = self.content.y + (40*self.ymult)
        self.draw_image(self.parent.weather.image,
            (x_start, y_start,
              int(200*self.xmult), int(150*self.ymult)))

        y_start = self.content.y + (200*self.ymult)
        self.write_text(self.parent.weather.getCurrentCondition(),
            self.key_font, self.content,
            x=x_start, y=y_start,
            width=200*self.xmult, height=-1, align_h='center')
        y_start = self.content.y + (250*self.ymult)
        self.write_text(self.parent.weather.getTemperature(),
            self.big_font, self.content,
            x=x_start, y=y_start,
            width=200*self.xmult, height=-1, align_h='center')

        x_start = self.content.x + (40*self.xmult)
        y_start = self.content.y + (350*self.ymult)
        self.write_text(self.parent.weather.getLastUpdated() ,
            self.small_font, self.content,
            x=x_start, y=y_start,
            width=self.content.width, height=-1, align_h='left')


    def update_forecast(self):
        ''' this screen is taken from the 1click weather forecast of the firefox plug-in. '''
        _debug_('update_forecast()', 2)
        x_start = self.content.x + (20 * self.xmult)
        y_start = self.content.y + (30 * self.xmult)
        weather = self.parent.weather

        lines = []
        try:
            lines.append('%s %s %s %s' %
                (_('As of:'), weather.getLastUpdated(), _('in'), weather.getObservationStation()))
            lines.append('  %s' % (weather.getCurrentCondition()))
            lines.append('  %s %s' % (_('Temperature:'), weather.getTemperature()))
            lines.append('  %s %s' % (_('Dew Point:'), weather.getDewPoint()))
            lines.append('  %s %s' % (_('Humidity:'), weather.getHumidity()))
            lines.append('  %s %s' % (_('Visibility:'), weather.getVisibility()))
            lines.append('  %s %s' % (_('Pressure:'), weather.getPressure()))
            lines.append('  %s %s' % (_('Winds:'), weather.getWind()))
            lines.append('%s' % (_('Tonight:')))
            lines.append('  %s %s' % (_('Sunset:'), weather.getSunset()))
            lines.append('  %s %s' % (_('Moon Phase:'), weather.getMoonPhase()))
        except Exception, error:
            print error
            import traceback, sys
            output = apply(traceback.format_exception, sys.exc_info())
            output = ''.join(output)
            output = urllib.unquote(output)
            print output

        y = y_start
        for line in lines:
            self.write_text(line, self.key_font, self.content,
            x=x_start, y=y, height=-1, align_h='left')
            y += (30 * self.ymult)

        try:
            x_start = self.content.x + (500 * self.xmult)
            y_start = self.content.y + (300 * self.ymult)
            iconFile = weather.getMoonImage(weather.getMoonIcon())
            #self.draw_image(iconFile,
            #    (x_start, y_start, 90, 90))
                #(x_start, y_start, int(60 * self.xmult), int(60 * self.ymult)))
            print 'x_start=%s, y_start=%s, xmult=%s, ymult=%s' % (x_start, y_start, self.xmult, self.ymult)
        except Exception, error:
            print error


    def update_week(self):
        ''' update the weeks forecast
        @remarks this can be improved
        '''
        _debug_('update_week()', 2)

        x_start = self.content.x + (10  * self.xmult)
        y_start = self.content.y + (10  * self.xmult)

        day = 0
        for x in (0, 180, 360, 540):

            x2_start = x_start + (x *self.xmult)
            y2_start = y_start

            self.write_text(Unicode(self.parent.weather.date[day]),
                self.key_font, self.content,
                x=x2_start, y=y2_start,
                width=150*self.xmult, height=-1, align_h='center')

            iconFile = os.path.join(WEATHER_DIR, self.parent.weather.weatherIcon[day])
            self.draw_image(iconFile,
                (x2_start, y2_start + (50*self.ymult), int(160*self.xmult), int(120*self.ymult)))
            self.write_text(self.parent.weather.weatherType[day],
                self.small_font, self.content,
                x=x2_start, y=y2_start + (200*self.ymult),
                width=160*self.xmult, height=-1, align_h='center')
            self.write_text(_("LO"),
                self.val_font, self.content,
                x=x2_start, y=y2_start + (260*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            self.write_text(self.parent.weather.lowTemp[day],
                self.key_font, self.content,
                x=x2_start, y=y2_start + (300*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            self.write_text(_("HI"),
                self.val_font, self.content,
                x=x2_start+(70*self.xmult), y=y2_start + (260*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            self.write_text(self.parent.weather.highTemp[day],
                self.key_font, self.content,
                x=x2_start+(70*self.xmult), y=y2_start + (300*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            day += 1

    def update_map(self):
        ''' update the contents of the skin's doppler weather map '''
        _debug_('update_map()', 2)
        if not self.parent.weather.weatherMapData:
            x_start = self.content.x + (10 * self.xmult)
            y_start = self.content.y + (10 * self.xmult)
            self.write_text(_("Error encountered while trying to download weather map"),
                self.key_font, self.content, x=x_start, y=y_start,
                width=self.content.width, height=-1, align_h='left')
        else:
            self.draw_image(self.parent.weather.mapFile,
                (self.content.x-3, self.content.y+14, self.content.width, self.content.height))

    def update_content(self):
        ''' update the contents of the skin '''
        _debug_('update_content()', 2)
        self.parent = self.menu
        self.content = self.calc_geometry(self.layout.content, copy_object=True)
        self.update_functions[self.menu.skin_num]()


# create one instance of the WeatherType class
skin.register ('oneclick', ('screen', 'subtitle', 'title', 'plugin', WeatherBaseScreen()))
