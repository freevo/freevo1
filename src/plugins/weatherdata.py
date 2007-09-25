#!/usr/bin/env python
#
# using Firefox 1click weather
# wget 'http://ff.1click.weather.com/weather/local/SZXX0033?dayf=5&unit=m'
# wget 'http://ff.1click.weather.com/weather/local/SZXX0033?cc=*&unit=m'

import cElementTree as ET
import cPickle, pickle
from pprint import pprint


class WeatherData:
    """Main weather data class
    """
    def __init__(self, tree):
        self.tree = tree
        self.head = None
        self.loc = None
        self.eloc = None
        self.cc = None
        self.dayf = None
        self.TREE = {
            'head' : 'WeatherData.Head',
            'loc'  : 'WeatherData.Loc',
            'eloc' : 'WeatherData.Eloc',
            'cc'   : 'WeatherData.Cc',
            'dayf' : 'WeatherData.DayF',
        }
        parse(self)

    def __str__(self):
        return 'WeatherData'


#391 lines
    class Loc:
        """ Location information
        <loc id="SZXX0033">
          <dnam>Zurich, Switzerland</dnam>
          <tm>7:46 AM</tm>
          <lat>47.38</lat>
          <lon>8.54</lon>
          <sunr>6:57 AM</sunr>
          <suns>7:47 PM</suns>
          <zone>2</zone>
        </loc>
        """
        def __init__(self, tree):
            self.tree = tree
            self.id = None
            self.dnam = None
            self.tm = None
            self.lat = None
            self.lon = None
            self.sunr = None
            self.suns = None
            self.zone = None
            self.TREE = {
                'dnam'    : 'dnam',
                'tm'      : 'tm',
                'lat'     : 'lat',
                'lon'     : 'lon',
                'sunr'    : 'sunr',
                'suns'    : 'suns',
                'zone'    : 'zone',
            }
            parse(self)


        def __str__(self):
            return 'Loc'

    class Head:
        """ Header information
        <head>
          <locale>en_US</locale>
          <form>MEDIUM</form>
          <ut>C</ut>
          <ud>km</ud>
          <us>km/h</us>
          <up>mb</up>
          <ur>mm</ur>
        </head>
        """

        def __init__(self, tree):
            self.tree = tree
            self.locale = None
            self.form = None
            self.ut = None
            self.ud = None
            self.us = None
            self.mb = None
            self.mm = None
            self.TREE = {
                'locale' : 'locale',
                'form'   : 'form',
                'ut'     : 'ut',
                'ud'     : 'ud',
                'us'     : 'us',
                'up'     : 'up',
                'ur'     : 'ur',
            }
            parse(self)

        def __str__(self):
            return 'Head'


    class Eloc:
        """ Extended location
        <eloc id="SZXX0033">
          <dma>N/A</dma>
          <rgn4>N/A</rgn4>
          <rgn9>N/A</rgn9>
          <st>*</st>
          <ctry>SZ</ctry>
          <zip>N/A</zip>
        </eloc>
        """
        def __init__(self, tree):
            self.tree = tree
            self.id = None
            self.dma = None
            self.rgn4 = None
            self.rgn9 = None
            self.st = None
            self.ctry = None
            self.zip = None
            self.TREE = {
                'id' : 'id',
                'dma' : 'dma',
                'rgn4' : 'rgn4',
                'rgn9' : 'rgn9',
                'st' : 'st',
                'ctry' : 'ctry',
                'zip' : 'zip',
            }
            parse(self)

        def __str__(self):
            return 'Eloc'

    class Cc:
        """ Current conditions
        <cc>
          <lsup>9/11/07 7:20 AM Local Time</lsup>
          <obst>Zurich, Switzerland</obst>
          <tmp>9</tmp>
          <flik>9</flik>
          <t>Partly Cloudy</t>
          <icon>30</icon>
          <bar>
          </bar>
          <wind>
          </wind>
          <hmid>93</hmid>
          <vis>10.0</vis>
          <uv>
          </uv>
          <dewp>8</dewp>
          <moon>
          </moon>
        </cc>
        """
        def __init__(self, tree):
            self.tree = tree
            self.lsup = None
            self.obst = None
            self.tmp = None
            self.flik = None
            self.t = None
            self.icon = None
            self.bar = None
            self.wind = None
            self.hmid = None
            self.vis = None
            self.uv = None
            self.dewp = None
            self.moon = None
            self.TREE = {
                'lsup' : 'lsup',
                'obst' : 'obst',
                'tmp' : 'tmp',
                'flik' : 'flik',
                't' : 't',
                'icon' : 'icon',
                'bar' : 'WeatherData.Bar',
                'wind' : 'WeatherData.Wind',
                'hmid' : 'hmid',
                'vis' : 'vis',
                'uv' : 'WeatherData.Uv',
                'dewp' : 'dewp',
                'moon' : 'WeatherData.Moon',
            }
            parse(self)

        def __str__(self):
            return 'Cc'


    class Bar:
        """
        <bar>
          <r>1020.0</r>
          <d>rising</d>
        </bar>
        """
        def __init__(self, tree):
            self.tree = tree
            self.r = None
            self.d = None
            self.TREE = {
                'r' : 'r',
                'd' : 'd',
            }
            parse(self)

        def __str__(self):
            return 'Bar'


    class Uv:
        """
        <uv>
          <i>0</i>
          <t>Low</t>
        </uv>
        """
        def __init__(self, tree):
            self.tree = tree
            self.i = None
            self.t = None
            self.TREE = {
                'i' : 'i',
                't' : 't',
            }
            parse(self)

        def __str__(self):
            return 'Uv'


    class Moon:
        """
        <moon>
          <icon>29</icon>
          <t>New</t>
        </moon>
        """
        def __init__(self, tree):
            self.tree = tree
            self.icon = None
            self.t = None
            self.TREE = {
                'icon' : 'icon',
                't' : 't',
            }
            parse(self)

        def __str__(self):
            return 'Moon'


    class DayF:
        """ Day forecast
        <dayf>
          <lsup>9/11/07 2:27 AM Local Time</lsup>
          <day d="0" t="Tuesday" dt="Sep 11">
          </day>
        </dayf>
        """
        def __init__(self, tree):
            self.tree = tree
            self.lsup = None
            self.day = None
            self.TREE = {
                'lsup' : 'lsup',
                'day'  : 'WeatherData.Day',
            }
            parse(self)

        def __str__(self):
            return 'DayF'

    class Day:
        """ Day information
        <day d="4" t="Saturday" dt="Sep 15">
          <hi>19</hi>
          <low>12</low>
          <sunr>7:03 AM</sunr>
          <suns>7:39 PM</suns>
          <part p="d">
          </part>
        </day>
        """
        def __init__(self, tree):
            self.tree = tree
            self.d = None
            self.t = None
            self.dt = None
            self.hi = None
            self.low = None
            self.sunr = None
            self.suns = None
            self.parts = None
            self.TREE = {
                'd' : 'd',
                't' : 't',
                'dt' : 'dt',
                'hi' : 'hi',
                'low' : 'low',
                'sunr' : 'sunr',
                'suns' : 'suns',
                'part' : 'WeatherData.Part',
            }
            parse(self)

        def __str__(self):
            return 'Day'

    class Part:
        """ Part of a day information
        <part p="n">
          <icon>29</icon>
          <t>Partly Cloudy</t>
          <wind>
          </wind>
          <bt>P Cloudy</bt>
          <ppcp>10</ppcp>
          <hmid>82</hmid>
        </part>
        """
        def __init__(self, tree):
            self.tree = tree
            self.p = None
            self.icon = None
            self.t = None
            self.wind = None
            self.bt = None
            self.ppcp = None
            self.hmid = None
            self.TREE = {
                'icon' : 'icon',
                't' : 't',
                'wind' : 'WeatherData.Wind',
                'bt' : 'bt',
                'ppcp' : 'ppcp',
                'hmid' : 'hmid',
            }
            parse(self)

        def __str__(self):
            return 'Part'

    class Wind:
        """ Wind information
        <wind>
          <s>6</s>
          <gust>N/A</gust>
          <d>109</d>
          <t>ESE</t>
        </wind>
        """
        def __init__(self, tree):
            self.tree = tree
            self.s = None
            self.gust = None
            self.d = None
            self.t = None
            self.TREE = {
                's' : 's',
                'gust' : 'gust',
                'd' : 'd',
                't' : 't',
            }
            parse(self)

        def __str__(self):
            return 'Wind'


def parse(obj):
    """ Parse an object using the tree information and build a class hierarchy.
    For list items add to a list of the name with a 's' appended

    This code is a little bit complex :)
    """
    if hasattr(obj.tree, 'items'):
        for k,v in obj.tree.items():
            code = 'obj.%s = "%s"' % (k, v)
            exec code

    for k,v in obj.TREE.items():
        elements = obj.tree.findall(k)
        if not elements:
            continue

        # just one element
        if len(elements) == 1:
            for element in elements:
                children = element.getchildren()
                if children:
                    code = 'obj.%s = %s(element)' % (k, v)
                else:
                    code = 'obj.%s = element.text.strip()' % (k)
                exec code
            continue

        # list of elements
        code = 'obj.%ss = []' % k
        exec code
        for element in elements:
            children = element.getchildren()
            if children:
                code = '%s = %s(element)' % (k, v)
            else:
                code = 'obj.%s = element.text.strip()' % (k)
            exec code
            code = 'obj.%ss.append(%s)' % (k, k)
            exec code
        continue

    return obj


if __name__ == '__main__':
    location_tree=ET.parse('SZXX0033-eloc.xml')
    location = WeatherData(location_tree)
    conditions_tree=ET.parse('SZXX0033-cc.xml')
    conditions = WeatherData(conditions_tree)
    forecast_tree=ET.parse('SZXX0033-dayf5.xml')
    forecast = WeatherData(forecast_tree)
    print dir(forecast)
    for i in dir(forecast):
        item = eval('forecast.%s' % (i))
        #print i, type(item), item
    #pprint(forecast)
    f = open('forecast.pickle', 'w')
    #pickle.dump(forecast, f, pickle.HIGHEST_PROTOCOL)
    #pickle.dump(forecast_tree, f, pickle.HIGHEST_PROTOCOL)
    f.close()

    print dir(forecast.loc)
    print forecast.loc.id
    print dir(forecast.dayf)
    print forecast.dayf.lsup
    print dir(forecast.dayf.day)
    print type(forecast.dayf.days)
    print forecast.dayf.days
    for day in forecast.dayf.days:
        print dir(day)
        print day.dt
        print type(day.parts)
        for part in day.parts:
            print dir(part)
            print dir(part.wind)
            print part.wind.s, part.wind.t

    print location.eloc.ctry
