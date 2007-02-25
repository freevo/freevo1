# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# weather.py - a plugin to obtain detailed weather forecast information
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:
#   X pull down weather on demand MENU_SELECT (need to fix popup behavior)
#   X Ability to specify custom location name in PLUGIN_WEATHER_LOCATIONS
#   - get location name back onto details screen
#   - i18n support
#   - a freevo helper to grab weather data behind the scenes
#
# activate:
#
#    plugin.activate('weather', level=45)
#    PLUGIN_WEATHER_LOCATIONS = [ ("USNC0559", 0, "Home sweet home") ]
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

# date/time
import time

#regular expression
import re

# rdf modules
from xml.dom.ext.reader import Sax2
import urllib

#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui.PopupBox import PopupBox
from item import Item

#get the singletons so we get skin info and access the osd
skin = skin.get_singleton()
osd  = osd.get_singleton()

#check every 2 hours
WEATHER_AGE = 7200
WEATHER_DIR = os.path.join(config.SHARE_DIR, 'images', 'weather')

WEATHER_DATA = [
    ('1', _('Cloudy'), 'cloudy.png'),
    ('3', _('Mostly Cloudy'), 'mcloudy.png'),
    ('4', _('Partly Cloudy'), 'pcloudy.png'),
    ('13', _('Light Rain'), 'lshowers.png'),
    ('14', _('Showers'), 'showers.png'),
    ('16', _('Snow'), 'snowshow.png'),
    ('18', _('Rain'), 'showers.png'),
    ('19', _('AM Showers'), 'showers.png'),
    ('20', _('Fog'), 'fog.png'),
    ('21', _('Few Showers'), 'lshowers.png'),
    ('22', _('Mostly Sunny'), 'sunny.png'),
    ('24', _('Sunny'), 'sunny.png'),
    ('25', _('Scattered Flurries'), 'flurries.png'),
    ('26', _('AM Clouds/PM Sun'), 'pcloudy.png'),
    ('27', _('Isolated T-Storms'), 'thunshowers.png'),
    ('28', _('Scattered Thunderstorms'), 'thunshowers.png'),
    ('29', _('PM Showers'), 'showers.png'),
    ('30', _('PM Showers/Wind'), 'showers.png'),
    ('31', _('Rain/Snow Showers'), 'rainsnow.png'),
    ('32', _('Few Snow Showers'), 'flurries.png'),
    ('33', _('Cloudy/Wind'), 'cloudy.png'),
    ('34', _('Flurries/Wind'), 'flurries.png'),
    ('35', _('Mostly Cloudy/Windy'), 'mcloudy.png'),
    ('36', _('Rain/Thunder'), 'thunshowers.png'),
    ('37', _('Partly Cloudy/Windy'), 'pcloudy.png'),
    ('38', _('AM Rain/Snow Showers'), 'rainsnow.png'),
    ('40', _('Light Rain/Wind'), 'lshowers.png'),
    ('41', _('Showers/Wind'), 'showers.png'),
    ('42', _('Heavy Snow'), 'snowshow.png'),
    ('43', _('Drizzle'), 'showers.png'),
    ('44', _('Mostly Sunny/Wind'), 'sunny.png'),
    ('45', _('Flurries'), 'flurries.png'),
    ('47', _('Rain/Wind'), 'showers.png'),
    ('49', _('Sct Flurries/Wind'), 'flurries.png'),
    ('50', _('Sct Strong Storms'), 'thunshowers.png'),
    ('51', _('PM T-Storms'), 'thunshowers.png'),
    ('53', _('Thunderstorms'), 'thunshowers.png'),
    ('55', _('Sunny/Windy'), 'sunny.png'),
    ('56', _('AM Thunderstorms'), 'thunshowers.png'),
    ('62', _('AM Rain'), 'showers.png'),
    ('64', _('Iso T-Storms/Wind'), 'thunshowers.png'),
    ('65', _('Rain/Snow'), 'rainsnow.png'),
    ('66', _('Sct T-Storms/Wind'), 'showers.png'),
    ('67', _('AM Showers/Wind'), 'showers.png'),
    ('70', _('Sct Snow Showers'), 'snowshow.png'),
    ('71', _('Snow to Ice/Wind'), 'snowshow.png'),
    ('76', _('AM Ice'), 'rainsnow.png'),
    ('77', _('Snow to Rain'), 'rainsnow.png'),
    ('80', _('AM Light Rain'), 'lshowers.png'),
    ('81', _('PM Light Rain'), 'lshowers.png'),
    ('82', _('PM Rain'), 'showers.png'),
    ('84', _('Snow Showers'), 'snowshow.png'),
    ('85', _('Rain to Snow'), 'rainsnow.png'),
    ('86', _('PM Rain/Snow'), 'snowshow.png'),
    ('88', _('Few Showers/Wind'), 'showers.png'),
    ('90', _('Snow/Wind'), 'snowshow.png'),
    ('91', _('PM Rain/Snow Showers'), 'rainsnow.png'),
    ('92', _('PM Rain/Snow/Wind'), 'rainsnow.png'),
    ('93', _('Rain/Snow Showers/Wind'), 'rainsnow.png'),
    ('94', _('Rain/Snow/Wind'), 'rainsnow.png'),
    ('98', _('Light Snow'), 'flurries.png'),
    ('100', _('PM Snow'), 'snowshow.png'),
    ('101', _('Few Snow Showers/Wind'), 'snowshow.png'),
    ('103', _('Light Snow/Wind'), 'flurries.png'),
    ('104', _('Wintry Mix'), 'flurries.png'),
    ('105', _('AM Wintry Mix'), 'rainsnow.png'),
    ('106', _('Hvy Rain/Freezing Rain'), 'rainsnow.png'),
    ('108', _('AM Light Snow'), 'flurries.png'),
    ('109', _('PM Rain/Snow/Wind'), 'rainsnow.png'),
    ('114', _('Rain/Freezing Rain'), 'showers.png'),
    ('118', _('T-Storms/Wind'), 'thunshowers.png'),
    ('123', _('Sprinkles'), 'lshowers.png'),
    ('125', _('AM Snow Showers'), 'snowshow.png'),
    ('126', _('AM Clouds/PM Sun/Wind'), 'pcloudy.png'),
    ('128', _('AM Rain/Snow/Wind'), 'rainsnow.png'),
    ('130', _('Rain to Snow/Wind'), 'rainsnow.png'),
    ('132', _('Snow to Wintry Mix'), 'snowshow.png'),
    ('133', _('PM Snow Showers/Wind'), 'snowshow.png'),
    ('135', _('Snow and Ice to Rain'), 'rainsnow.png'),
    ('137', _('Heavy Rain'), 'showers.png'),
    ('138', _('AM Rain/Ice'), 'showers.png'),
    ('145', _('AM Snow Showers/Wind'), 'snowshow.png'),
    ('146', _('AM Light Snow/Wind'), 'flurries.png'),
    ('150', _('PM Light Rain/Wind'), 'lshowers.png'),
    ('152', _('AM Light Wintry Mix'), 'rainsnow.png'),
    ('153', _('PM Light Snow/Wind'), 'flurries.png'),
    ('154', _('Heavy Rain/Wind'), 'showers.png'),
    ('155', _('PM Snow Shower'), 'snowshow.png'),
    ('158', _('Snow to Rain/Wind'), 'rainsnow.png'),
    ('164', _('PM Light Rain/Ice'), 'showers.png'),
    ('167', _('AM Snow'), 'snowshow.png'),
    ('171', _('Snow to Ice'), 'snowshow.png'),
    ('172', _('Wintry Mix/Wind'), 'rainsnow.png'),
    ('175', _('PM Light Snow'), 'flurries.png'),
    ('178', _('AM Drizzle'), 'lshowers.png'),
    ('189', _('Strong Storms/Wind'), 'thunshowers.png'),
    ('193', _('PM Drizzle'), 'lshowers.png'),
    ('194', _('Drizzle'), 'lshowers.png'),
    ('201', _('AM Light Rain/Wind'), 'lshowers.png'),
    ('204', _('AM Rain/Wind'), 'showers.png'),
    ('223', _('Wintry Mix to Snow'), 'rainsnow.png'),
    ('231', _('Rain'), 'showers.png'),
    ('240', _('AM Light Rain/Ice'), 'rainsnow.png'),
    ('259', _('Hvy Rain/Freezing Rain'), 'showers.png'),
    ('271', _('Snow Showers/Windy'), 'snowshow.png'),
    ('988', _('Partly Cloudy/Windy'), 'pcloudy.png'),
    ('989', _('Light Rain Shower'), 'lshowers.png'),
    ('990', _('Light Rain with Thunder'), 'thunshowers.png'),
    ('991', _('Light Drizzle'), 'lshowers.png'),
    ('992', _('Mist'), 'fog.png'),
    ('993', _('Smoke'), 'fog.png'),
    ('994', _('Haze'), 'fog.png'),
    ('995', _('Light Snow Shower'), 'flurries.png'),
    ('996', _('Light Snow Shower/ Windy'), 'flurries.png'),
    ('997', _('Clear'), 'fair.png'),
    ('998', _('A Few Clouds'), 'pcloudy.png'),
    ('999', _('Fair'), 'fair.png')
 ]

def wget(iUrl):
    for i in range(3):
        try:
            t1 = time.time()
            fd = urllib.urlopen(iUrl)
            data = fd.read()
            fd.close()
            t2 = time.time()
            print "Weather download: ", iUrl, "-", "%.1f" % (t2-t1), "sec"
            return data
        except IOError:
            print "retrying wget '%s'" % (iUrl,)
            pass

def toCelcius(fTemp):
    try:
        tTemp = float (fTemp )
    except ValueError:
        tTemp = 0.0
    nTemp = (5.0/9.0)*(tTemp - 32.0)
    return "%d" % (nTemp,)

def toKilometers(miles):
    try:
        tTemp = float(miles)
    except ValueError:
        tTemp = 0.0
    nTemp = tTemp*1.6
    return "%d" % (int(nTemp),)

def toBarometer(baro):
    try:
        tTemp = float(baro)
    except ValueError:
        tTemp = 0.0
    nTemp = tTemp*3.386
    return "%.1f" % (nTemp,)


class PluginInterface(plugin.MainMenuPlugin):
    """
    A plugin to obtain more detailed weather forecast information

    To activate, put the following lines in local_conf.py:

    plugin.activate('weather', level=45)
    PLUGIN_WEATHER_LOCATIONS = [ ("<val1>", <bool>, "<str>"), ("<val2>", <bool>, "<str>"), ...]

    where <val#> is a zipcode or
    and <bool> (1 == convert to SI Units; 0 == do not convert)
    and <str> is a custom name you wish to use for this location
    """
    # make an init func that creates the cache dir if it don't exist
    def __init__(self):
        if not hasattr(config, 'PLUGIN_WEATHER_LOCATIONS'):
            self.reason = 'PLUGIN_WEATHER_LOCATIONS not defined'
            return
        plugin.MainMenuPlugin.__init__(self)

    def config(self):
        return [('PLUGIN_WEATHER_LOCATIONS', [("USNC0559", 0)],
                 "Location codes to grab forecasts for")]

    def items(self, parent):
        return [ WeatherMainMenu(parent) ]


class WeatherItem(Item):
    """
    Item for the menu for one rss feed
    """
    def __init__(self, parent, iLocation):
        Item.__init__(self, parent)

        self.parent       = parent

        # Flag to indicate whether this item is able to be displayed
        self.error        = 0

        self.location     = None
        self.convertData  = 0
        self.name         = None
        self.city         = None
        self.state        = None
        self.country      = None
        self.curTemp      = None
        self.updated      = None
        self.curIcon      = None
        self.curWind      = None
        self.windDir      = None
        self.barometer    = None
        self.curHumid     = None
        self.curFeel      = None
        self.uvIndex      = None
        self.visibility   = None
        self.shortdesc    = None
        self.description  = None
        self.forecastData = None
        self.pastTime     = 0

        self.date         = []
        self.weatherIcon  = []
        self.highTemp     = []
        self.lowTemp      = []
        self.weatherType  = []
        self.wdata        = []

        self.popupParam = None

        # were we asked to convert to SI units?
        if isinstance(iLocation, tuple):
            self.location    = iLocation[0]
            if len(iLocation) > 1:
                self.convertData = int(iLocation[1])
            if len(iLocation) > 2:
                self.name        = str(iLocation[2])

            self.popupParam = Unicode(self.name)

        else:
            self.location    = iLocation
            self.convertData = 0
            self.popupParam = self.location

        self.dataurl        = "http://www.msnbc.com/m/chnk/d/weather_d_src.asp?acid=%s" % (self.location,)
        self.mapurl         = "http://w3.weather.com/weather/map/%s?from=LAPmaps" % (self.location,)
        self.mapurl2        = None
        self.maplink        = None
        self.weatherData    = None
        self.weatherMapData = None

        self.cacheDir  = '%s/weather_%s' % (config.FREEVO_CACHEDIR, self.location)
        self.cacheFile = '%s/data' % (self.cacheDir,)
        self.mapFile   = '%s/map' % (self.cacheDir,)
        if not os.path.isdir(self.cacheDir):
            os.mkdir(self.cacheDir, stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))
        self.last_update = 0

        #get forecast data
        self.getForecast()

    def isValid(self):
        return not self.error

    def getHumidity(self):
        return "%s %%" % (self.curHumid,)

    def getBarometer(self):
        if self.convertData:
            return "%s kPa" % (self.barometer,)
        else:
            return "%s in" % (self.barometer,)

    def getWind(self):
        if self.convertData:
            return "%s km/h" % (self.curWind,)
        else:
            return "%s mph" % (self.curWind,)

    def getTemp(self):
        if self.convertData:
            return u"%s\xb0 C" % (self.curTemp,)
        else:
            return u"%s\xb0 F" % (self.curTemp,)

    def getLastUpdated(self):
        if self.convertData:
            # day / month / year  24hour:min:sec
            return _("Last updated: %s") % (time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(self.last_update)),)
        else:
            # month / day / year  12hour:min:sec [AM|PM]
            return _("Last updated: %s") % (time.strftime("%m/%d/%Y %I:%M:%S %p", time.localtime(self.last_update)),)

    def getFeel(self):
        if self.convertData:
            return u"%s\xb0 C" % (self.curFeel,)
        else:
            return u"%s\xb0 F" % (self.curFeel,)

    def getVisibility(self):
        if float(self.visibility) == 999.00:
            return _("Unlimited")
        elif self.convertData:
            return "%s km" % (self.visibility,)
        else:
            return "%s mi" % (self.visibility,)

    def start_detailed_interface(self, arg=None, menuw=None):
        WeatherDetailHandler(arg, menuw, self)

    def actions(self):
        """
        return a list of actions for this item
        """
        return [ (self.start_detailed_interface, _('Show Weather Details')) ]

    def saveToCache(self):
        util.save_pickle(self.weatherData, self.cacheFile)
        # attempt to save weathermap
        try:
            if self.weatherMapData is not None:
                imgfd = os.open(self.mapFile, os.O_CREAT|os.W_OK)
                os.write(imgfd, self.weatherMapData)
                os.close(imgfd)
        except:
            print "failed while saving weather map to cache '%s'" % (self.mapFile,)

    def loadFromCache(self):
        self.weatherData = util.read_pickle(self.cacheFile)

        try:
            size = int(os.stat(self.mapFile)[6])
        except:
            print "Weather ERROR: failed attempting to load %s radar map from cache" % (self.location,)
            pass
        else:
            imgfd = os.open(self.mapFile, os.R_OK)
            self.weatherMapData = os.read(imgfd, size)
            os.close(imgfd)

    def needRefresh(self):
        '''is the cache too old?'''
        if (os.path.isfile(self.cacheFile) == 0 or \
            (abs(time.time() - os.path.getmtime(self.cacheFile)) > WEATHER_AGE)):
            return 1
        else:
            return 0

    def getForecast(self, force=0):
        '''grab the forecast, updating for the website if needed'''

        # check cache
        try:
            if force or self.needRefresh():
                self.updateData()
            else:
                self.loadFromCache()
        except:
            self.error = 1
            print "ERROR obtaining forecast data for '%s'" % (self.location,)
        else:
            # set the last update timestamp
            self.last_update = os.path.getmtime(self.cacheFile)

            # now convert the self.weatherData structure to parsable information
            try:
                self.convertWeatherData()
            except:
                self.error = 1
                import traceback, sys
                print "ERROR parsing forecast data for '%s'" % (self.location,)
                print "\tThis could indicate a failed download of weather data from msnbc.  "\
                      "You can confirm this by examining the contents of the file '%s'.  "\
                      "Below is also the traceback indicating where we discovered the problem "\
                      "with the weather file.  If the weather file appears intact, please report " \
                      "this to the 'freevo-users@lists.sourceforge.net'\n" % (self.cacheFile,)
                output = apply(traceback.format_exception, sys.exc_info())
                output = ''.join(output)
                output = urllib.unquote(output)
                print output

    def GetString(self, var):
        '''when given a variable, it returns the value stored in the MSNBC forecast data'''

        regexp  = re.compile('%s = "[^"]*"' % (var,))
        results = regexp.search(self.weatherData)
        (start, end) = results.span()
        start += len(var) + 4 # the 4 chars is the ' = "'
        end   -= 1  # strip off the right "
        return self.weatherData[start:end]

    def updateData(self):
        popup = PopupBox(text=_('Fetching Weather for %s...') % self.popupParam)
        popup.show()

        # parse the document
        try:
            self.weatherData = wget(self.dataurl)
        except:
            popup.destroy()
            raise WeatherError, 'Weather ERROR: failed attempting to grab forecast for %s' % self.location

        #TODO: Get description from http://weather.noaa.gov/pub/data/forecasts/zone/nc/ncz041.txt

        # obtain radar map
        popup.destroy()
        popup = PopupBox(text=_('Fetching Radar Map for %s...' % self.popupParam))
        popup.show()
        try:
            if self.maplink is None:

                # get the first web page
                for attempt in range(3):
                    weatherPage  = wget (self.mapurl)
                    try:
                        # find link to map page
                        regexp       = re.compile ('if \(isMinNS4\) var mapNURL = "[^"]*";', re.IGNORECASE )
                        results      = regexp.search(weatherPage)
                        (start, end) = results.span()
                        # TODO: I don't like having fixed length offsets from start, end
                        weatherPage2 = "http://w3.weather.com/%s" % (weatherPage[start+29:end-2],)

                        mapPage      = wget (weatherPage2)
                        # find a link to the real doplay map
                        regexp       = re.compile('<img NAME="mapImg" SRC="http://image.weather.com[^"]*jpg"', re.IGNORECASE)
                        results      = regexp.search(mapPage)
                        (start, end) = results.span()
                        # TODO: I don't like having fixed length offsets from start, end
                        self.maplink = mapPage[start+24:end-1]
                        break;
                    except:
                        print "Retrying [%d] %s" % (attempt,self.mapurl)
                        pass

            # pull down the map locally
            try:
                self.weatherMapData = wget(self.maplink)
            except:
                print 'Weather ERROR: failed attempting to download radar map from %s' % self.maplink
        except:
            print 'Weather ERROR: failed attempting to locate radar map URL for %s' % self.location
            self.weatherMapData = None
            pass

            import traceback, sys
            output = apply(traceback.format_exception, sys.exc_info())
            output = ''.join(output)
            output = urllib.unquote(output)
            print output

        #write the file
        self.saveToCache()

        popup.destroy()

    def convertWeatherData(self):
        self.city    = self.GetString("this.swCity")
        self.state   = self.GetString("this.swSubDiv")
        self.country = self.GetString("this.swCountry")
        self.curTemp = self.GetString("this.swTemp")
        self.updated = self.GetString("this.swLastUp")

        # reset variables
        self.date        = []
        self.weatherIcon = []
        self.highTemp    = []
        self.lowTemp     = []
        self.weatherType = []

        # set the location name (if one was not specified in the WEATHER_LOCATIONS"
        if self.name is None:
            self.name    = "%s" % (self.city)

        # convert temperature
        if self.curTemp is None or len(self.curTemp) == 0:
            self.curTemp = "-na-"
            self.updated = self.updated + " (Not All Information Available)"
        else:
            if self.convertData:
                self.curTemp = toCelcius(self.curTemp)

        self.curIcon   = self.GetString("this.swCIcon")
        self.curWind   = self.GetString("this.swWindS")

        # convert wind
        if self.convertData:
            self.curWind = toKilometers(self.curWind)

        self.windDir   = self.GetString("this.swWindD")
        self.barometer = self.GetString("this.swBaro")

        # convert barometer
        if self.convertData:
            self.barometer = toBarometer(self.barometer)

        self.curHumid = self.GetString("this.swHumid")
        self.curFeel  = self.GetString("this.swReal")

        # convert feels-like temp
        if self.convertData:
            self.curFeel = toCelcius(self.curFeel)

        self.uvIndex     = self.GetString("this.swUV")
        self.visibility  = self.GetString("this.swVis")
        if not self.visibility:
           self.visibility = 0.0

        # convert visibility
        if self.convertData and float(self.visibility) != 999.0:
            self.visibility = toKilometers(self.visibility)

        self.shortdesc = _(self.GetString("this.swConText"))
        if self.shortdesc is None or len(self.shortdesc) == 0:
            self.shortdesc = self.curIcon

        self.forecastData = self.GetString("this.swFore")
        holdings     = []
        holdings     = self.forecastData.split("|")
        dayNum       = int(holdings[0])
        curDay       = int(time.strftime("%u")) + 1 # day of week 2(mon) - 1(sun)

        if dayNum != curDay:
            self.pastTime = 1

        ltime = time.localtime()
        ctr   = 0
        for i in range(5,10):
            (mons, days, years) = holdings[i].split("/")
            mons  = int(mons)
            days  = int(days)
            years = int(years)
            dnum  = (ltime[6] + ctr) % 7
            self.date.append(time.strftime("%A", (years, mons, days, ltime[3], ltime[4], ltime[5], \
                dnum, ltime[7], ltime[8])))
            ctr += 1

        # weather icon
        for i in (10,11,12,13):
            self.weatherIcon.append(holdings[i])

        # calculate high temps
        for i in (20,21,22,23):
            if self.convertData:
                holdings[i] = toCelcius(holdings[i])
            self.highTemp.append(holdings[i])

        # calculate low temps
        for i in (40,41,42,43):
            if self.convertData:
                holdings[i] = toCelcius(holdings[i])
            self.lowTemp.append(holdings[i])

        for i in (15,16,17,18):
            self.weatherType.append(holdings[i])

        self.setWeatherTypeIcon()
        self.setWeatherIcon()

        # Create description
        self.description = "%s %s %s" % (self.shortdesc, _("at"), self.getTemp())

    def setWeatherIcon(self):
        '''set the weather icon given the short forecast description'''

        match = weatherTypes.findType(name=self.shortdesc)
        if match:
            self.curIcon     = match.getIcon()
        else:
            self.curIcon     = "unknown.png"

        # set the Item.image value
        self.image = os.path.join(WEATHER_DIR, self.curIcon)
        return

    def setWeatherTypeIcon(self):
        '''obtain the weather icons for multiple day forecast'''

        #start = 1
        #if self.pastTime:
        #    start = 0
        #i = start
        i = 0
        while i < 4:

            match = weatherTypes.findType(number=self.weatherType[i])
            if match:
                self.weatherType[i] = match.getName()
                self.weatherIcon[i] = match.getIcon()
            else:
                self.weatherType[i] = "%s (%s)" % (_("Unknown"), self.weatherType[i])
                self.weatherIcon[i] = "unknown.png"
            i += 1

class WeatherType:
    def __init__(self, iNum=0, iName="", iIcon=""):
        self.number = iNum
        self.name   = iName
        self.icon   = iIcon
    def setNumber(self, n):
        self.number = n
    def setName(self, n):
        self.name = n
    def setIcon(self, n):
        self.icon = n
    def getNumber(self):
        return self.number
    def getName(self):
        return _(self.name)
    def getIcon(self):
        return self.icon

class WeatherTypesClass:
    def __init__(self):
        self.wtypes      = []
        self.num_lookup  = {} # reverse hash to quickly get a Weathertype w/ a number
        self.name_lookup = {} # reverse hash to quickly get a Weathertype w/ a name
        self.icon_lookup = {} # reverse hash to quickly get a Weathertype w/ a icon
        self.loadWeatherTypes()
    def loadWeatherTypes(self):

        for icdata in WEATHER_DATA:
            try:
                wtype = WeatherType()
                wtype.setNumber (icdata[0])
                wtype.setName   (icdata[1])
                wtype.setIcon   (icdata[2])

                # populate reverse dictionaries
                self.num_lookup[ wtype.getNumber() ] = len(self.wtypes)
                self.name_lookup[ wtype.getName() ]  = len(self.wtypes)
                self.icon_lookup[ wtype.getIcon() ]  = len(self.wtypes)

                self.wtypes.append (wtype)
            except:
                pass
    def findType(self, number=None, name=None, icon=None):
        ''' return a type given a type number '''
        if number:
            try:
                idx = self.num_lookup[number]
                return self.wtypes[ idx ]
            except:
                return None
        elif name:
            try:
                idx = self.name_lookup[name]
                return self.wtypes[ idx ]
            except:
                return None
        elif icon:
            try:
                idx = self.icon_lookup[icon]
                return self.wtypes[ idx ]
            except:
                return None
        else:
            print "Unknown type requested in WeatherTypesClass::findType()"
            return None

    def __len__(self): return len(self.wtypes)
    def __getitem__(self, i): return self.wtypes[i]

class WeatherMainMenu(Item):
    """
    this is the item for the main menu and creates the list
    of Weather Locations in a submenu.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='weather')
        self.parent = parent
        self.name   = _('Weather')

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ (self.create_locations_menu , _('Locations')) ]
        return items

    def __call__(self, arg=None, menuw=None):
        """
        call first action in the actions() list
        """
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)

    def create_locations_menu(self, arg=None, menuw=None):
        locations  = []
        autoselect = 0
        # create menu items
        for location in config.PLUGIN_WEATHER_LOCATIONS:
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
    """
    A handler class to display several detailed forecast screens and catch events
    """
    def __init__(self, iArg=None, iMenuw=None, iWeather=None):
        self.arg     = iArg
        self.menuw   = iMenuw
        self.weather = iWeather
        self.menuw.hide(clear=False)
        rc.app(self)

        self.skins     = ('day', 'forecast', 'week', 'doplar')

        self.subtitles = (_('Current Conditions'), _("Today's Forecast"),
                          _("Extended Forecast"), _("Radar Map"))

        self.curSkin   = 0

        self.title    = self.weather.name
        self.subtitle = self.subtitles[0]

        # Fire up splashscreen and load the plugins
        skin.draw('weather', self)

    def prevSkin(self):
        '''decriment self.curSkin'''
        self.curSkin -= 1

        # out of bounds check, reset to size of skins array
        if self.curSkin < 0:
            self.curSkin = len(self.skins)-1
        self.subtitle = self.subtitles[self.curSkin]

    def nextSkin(self):
        '''increment self.curSkin'''
        self.curSkin += 1

        # out of bounds check, reset to 0
        if self.curSkin >= len(self.skins):
            self.curSkin = 0
        self.subtitle = self.subtitles[self.curSkin]

    def eventhandler(self, event, menuw=None):
        '''eventhandler'''
        if event == 'MENU_BACK_ONE_MENU':
            rc.app(None)
            self.menuw.show()
            return True

        elif event == 'MENU_SELECT':
            # TODO: update the current forecast data, and refresh
            self.weather.getForecast(force=1)
            skin.clear()
            skin.draw('weather', self)
            return True

        elif event in ('MENU_DOWN', 'MENU_RIGHT'):
            # Fire up the next skin
            self.nextSkin()
            skin.draw('weather', self)
            return True

        elif event in ('MENU_UP', 'MENU_LEFT'):
            # Fire up the previous skin
            self.prevSkin()
            skin.draw('weather', self)
            return True

        return False

class WeatherBaseScreen(skin.Area):
    """
    A base class for weather screens to inherit from, provides common members+methods
    """
    def __init__(self):
        skin.Area.__init__(self, 'content')

        # Weather display fonts
        self.key_font      = skin.get_font('medium0')
        self.val_font      = skin.get_font('medium1')
        self.small_font    = skin.get_font('small0')
        self.big_font      = skin.get_font('huge0')

        # set the multiplier to be used in all screen drawing
        self.xmult = float(osd.width  - 2*config.OSD_OVERSCAN_X) / 800
        self.ymult = float(osd.height - 2*config.OSD_OVERSCAN_Y) / 600

        self.update_functions = (self.update_day, self.update_forecast,
                                 self.update_week, self.update_doplar)

    def update_day(self):
        # display data
        text      = _("Humidity")
        value     = self.parent.weather.getHumidity()

        x_col1   = self.content.x + (50  * self.xmult)
        x_col2   = self.content.x + (250 * self.xmult)
        y_start  = self.content.y + (60  * self.xmult)
        y_inc    = 40 * self.ymult

        self.write_text(text,   self.key_font,   self.content,
            x=x_col1,  y=y_start, height=-1, align_h='left')
        self.write_text(value,  self.val_font,   self.content,
            x=x_col2,  y=y_start, height=-1, align_h='left')

        text      = _("Pressure")
        value     = self.parent.weather.getBarometer()
        self.write_text(text,   self.key_font,   self.content,
            x=x_col1,  y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value,  self.val_font,   self.content,
            x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')

        text      = _("Wind")
        value     = "%s %s %s" % (self.parent.weather.windDir, _("at"), self.parent.weather.getWind())
        y_start   += y_inc
        self.write_text(text,   self.key_font,   self.content,
            x=x_col1,  y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value,  self.val_font,   self.content,
            x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')

        text      = _("Wind Chill")
        value     = self.parent.weather.getFeel()
        y_start   += y_inc
        self.write_text(text,   self.key_font,   self.content,
            x=x_col1,  y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value,  self.val_font,   self.content,
            x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')

        text      = _("Visibility")
        value     = self.parent.weather.getVisibility()
        y_start   += y_inc
        self.write_text(text,   self.key_font,   self.content,
            x=x_col1,  y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value,  self.val_font,   self.content,
            x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')

        text      = _("UV Index")
        value     = self.parent.weather.uvIndex
        y_start   += y_inc
        self.write_text(text,   self.key_font,   self.content,
            x=x_col1,  y=y_start+y_inc, height=-1, align_h='left')
        self.write_text(value,  self.val_font,   self.content,
            x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')

        # draw current condition image
        x_start = self.content.x + (450*self.xmult)
        y_start = self.content.y + (40*self.ymult)
        self.draw_image(self.parent.weather.image,
            (x_start, y_start,
              int(200*self.xmult), int(150*self.ymult)))

        y_start = self.content.y + (200*self.ymult)
        self.write_text(self.parent.weather.shortdesc,
            self.key_font,   self.content,
            x=x_start, y=y_start,
            width=200*self.xmult, height=-1, align_h='center')
        y_start = self.content.y + (250*self.ymult)
        self.write_text(self.parent.weather.getTemp(),
            self.big_font,   self.content,
            x=x_start, y=y_start,
            width=200*self.xmult, height=-1, align_h='center')

        x_start = self.content.x + (40*self.xmult)
        y_start = self.content.y + (350*self.ymult)
        self.write_text(self.parent.weather.getLastUpdated() ,
            self.small_font, self.content,
            x=x_start, y=y_start,
            width=self.content.width, height=-1, align_h='left')

    def update_forecast(self):
        '''
        this screen is extremely useless, all it\'s doing is putting text
        around the day view. It would be nice if I could use the same source
        that the gnome-applet weather applet uses for detailed forecast data
        '''
        x_start = self.content.x + (20  * self.xmult)
        y_start = self.content.y + (30  * self.xmult)

        lines = []
        lines.append("%s %s %s %s." % (_("Today, a high of"),
                                         self.parent.weather.highTemp[0],
                                         _("and a low of"),
                                         self.parent.weather.lowTemp[0]))
        lines.append("%s %s %s" \
                  % (_("Currently, there is a a humidity of"),
                      self.parent.weather.getHumidity(),
                      _("and"),))

        text = _("the winds are ")
        if self.parent.weather.windDir == "CALM":
            text += "%s. " % (_("calm"),)
        else:
            text += "%s %s %s %s." % (_("coming in at"), self.parent.weather.getWind(), _("from the"), self.parent.weather.windDir)
        lines.append(text)

        if float(self.parent.weather.visibility) == 999.00:
            lines.append(_("Visibility will be unlimited today"))
        else:
            lines.append("%s %s." % (_("There will be a visibility of"), self.parent.weather.getVisibility(),))

        y = y_start
        for line in lines:
            self.write_text(line,   self.key_font,   self.content,
            x=x_start,  y=y, height=-1, align_h='left')
            y += (30 * self.ymult)

    def update_week(self):

        x_start = self.content.x + (10  * self.xmult)
        y_start = self.content.y + (10  * self.xmult)

        day = 0
        #for x in (40, 220, 400, 580):
        for x in (0, 180, 360, 540):

            x2_start = x_start + (x *self.xmult)
            y2_start = y_start

            self.write_text(Unicode(self.parent.weather.date[day]),
                self.key_font,   self.content,
                x=x2_start,  y=y2_start,
                width=150*self.xmult, height=-1, align_h='center')

            iconFile = os.path.join(WEATHER_DIR, self.parent.weather.weatherIcon[day])
            self.draw_image(iconFile,
                             (x2_start,
                               y2_start + (50*self.ymult),
                               int(160*self.xmult),
                               int(120*self.ymult)))
            self.write_text(self.parent.weather.weatherType[day],
                self.small_font,   self.content,
                x=x2_start,  y=y2_start + (200*self.ymult),
                width=160*self.xmult, height=-1, align_h='center')
            self.write_text(_("LO"),
                self.val_font,   self.content,
                x=x2_start,  y=y2_start + (260*self.ymult),
                width=90*self.xmult,  height=-1, align_h='center')
            self.write_text(self.parent.weather.lowTemp[day],
                self.key_font,   self.content,
                x=x2_start,  y=y2_start + (300*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            self.write_text(_("HI"),
                self.val_font,   self.content,
                x=x2_start+(70*self.xmult),  y=y2_start + (260*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            self.write_text(self.parent.weather.highTemp[day],
                self.key_font,   self.content,
                x=x2_start+(70*self.xmult),  y=y2_start + (300*self.ymult),
                width=90*self.xmult, height=-1, align_h='center')
            day += 1

    def update_doplar(self):
        if self.parent.weather.weatherMapData is None:
            x_start = self.content.x + (10  * self.xmult)
            y_start = self.content.y + (10  * self.xmult)
            self.write_text(_("Error encountered while trying to download Radar map"),
                self.key_font, self.content, x=x_start, y=y_start,
                width=self.content.width, height=-1, align_h='left')
        else:
            self.draw_image(self.parent.weather.mapFile, (self.content.x, self.content.y, self.content.width,
                                                           self.content.height))

    def update_content(self):
        self.parent   = self.menu
        self.content  = self.calc_geometry(self.layout.content,  copy_object=True)
        self.update_functions[self.menu.curSkin]()


# create one instance of the WeatherType class
weatherTypes = WeatherTypesClass()
skin.register ('weather', ('screen', 'subtitle', 'title', 'plugin', WeatherBaseScreen()))
