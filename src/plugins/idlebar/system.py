# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# IdleBar plugins for monitoring the system
# -----------------------------------------------------------------------
# $Id$
#
# Documentation moved to the corresponding classes, so that the help
# interface returns something usefull.
# Available plugins:
#       idlebar.system.procstats
#       idlebar.system.sensors
#       idlebar.system.sensors2
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


import time
import os
import string
import types
import re

import kaa.imlib2 as imlib2

import config
from plugins.idlebar import IdleBarPlugin

def calc_positions(osd, image_w, image_h, text_w, text_h):
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


class procstats(IdleBarPlugin):
    """
    Retrieves information from /proc/stat and shows them in the idlebar.
    This plugin can show semi-accurate cpu usage stats and free memory
    in megabytes (calculated approx. as MemFree+Cached?)

    Activate with
    | plugin.activate('idlebar.system.procstats', level=20) for defaults or
    | plugin.activate('idlebar.system.procstats', level=20, args=(Mem, Cpu, Prec))
    where
        - Mem:  Draw memfree  (default=1, -1 to disable)
        - Cpu:  Draw cpuusage (default=1, -1 to disable)
        - Prec: Precision used when drawing cpu usage (default=1)
    """
    def __init__(self, Mem=1, Cpu=1, Prec=1):
        IdleBarPlugin.__init__(self)
        self.drawCpu = Cpu
        self.drawMem = Mem
        self.precision = Prec
        self.time = 0
        self.lastused = 0
        self.lastuptime = 0


    def config(self):
        return [
            ('SENSORS_PLATFORM_PATH', '/sys/devices/platform', 'path to the sensor devices'),
            ('SENSORS_I2CDEV_PATH', '/sys/bus/i2c/devices', 'path to the i2c devices'),
        ]


    def getStats(self):
        """
        Don't get the stats for each update
        as it gets annoying while navigating
        Update maximum every 10 seconds
        """
        if (time.time()-self.time)>10:
            self.time = time.time()

            if self.drawMem == 1:
                self.getMemUsage()

            if self.drawCpu == 1:
                self.getCpuUsage()

    def getMemUsage(self):
        """
        May not be correct, but i like to see
        total free mem as freemem+cached
        """
        free    = 0
        meminfo = None
        try:
            meminfo = file('/proc/meminfo', 'r').read().strip()
        except OSError:
            _debug_('[procstats]: The file /proc/meminfo is not available', DWARNING)

        if meminfo:
            i = 0
            meminfo = meminfo.split()
            for l in meminfo:
                if l in ['MemFree:', 'Buffers:', 'Cached:']:
                    free += int(meminfo[i+1])
                i += 1

        self.currentMem = _('%iM') % (free/1024)

    def getCpuUsage(self):
        """
        This could/should maybe be an even more
        advanced algorithm, but it will suffice
        for normal use.

        Note:
        cpu defined as 'cpu <user> <nice> <system> <idle>'
        at first line in /proc/stat
        """
        uptime = 0
        used = 0
        f = open('/proc/stat')
        if f:
            stat = string.split(f.readline())
            used = long(stat[1])+long(stat[2])+long(stat[3])
            uptime = used + long(stat[4])
        f.close()
        usage = (float(used-self.lastused)/float(uptime-self.lastuptime))*100
        self.lastuptime = uptime
        self.lastused = used
        self.currentCpu = _('%s%%') % round(usage, self.precision)


    def draw(self, (type, object), x, osd):
        try:
            self.getStats()
        except:
            _debug_('[procstats]: Not working, this plugin is only tested with 2.4 and 2.6 kernels')

        font = osd.get_font(config.OSD_IDLEBAR_FONT)
        widthtot = 0

        if self.drawCpu == 1:
            image_file = os.path.join(config.ICON_DIR, 'misc', 'cpu.png')
            w, h = imlib2.open(image_file).size
            text_w = font.stringsize(self.currentCpu)
            (image_x, image_y, text_x, text_y, width) = calc_positions(osd, w, h, text_w, font.h)
            osd.draw_image(image_file, (x+image_x, image_y, -1, -1))
            osd.write_text(self.currentCpu, font, None, x+text_x, text_y, text_w, font.h, 'center', 'top')
            widthtot += width + 5
            x += width + 5

        if self.drawMem == 1:
            image_file = os.path.join(config.ICON_DIR, 'misc', 'memory.png')
            w, h = imlib2.open(image_file).size
            text_w = font.stringsize(self.currentMem)
            (image_x, image_y, text_x, text_y, width) = calc_positions(osd, w, h, text_w, font.h)
            osd.draw_image(image_file, (x+image_x, image_y, -1, -1))
            osd.write_text(self.currentMem, font, None, x+text_x, text_y, text_w, font.h, 'center', 'top')
            widthtot += width + 5
            x += width + 5

        return widthtot - 5


#----------------------------------- SENSOR --------------------------------

class sensors(IdleBarPlugin):
    """
    Displays sensor temperature information (cpu, case) and memory-stats.

    Activate with::

        plugin.activate('idlebar.system.sensors', level=40, args=(<cpusensor>, <casesensor>, <meminfo>))
        plugin.activate('idlebar.system.sensors', level=40, args=((<cpusensor>, <compute expression>),
            (<casesensor>, <compute_expression>), <meminfo>))

    cpu and case sensor are the corresponding lm_sensors, they should be:

        - temp1,
        - temp2, default for case
        - temp3, default for cpu and temp2 for case

    meminfo is the memory info you want, types are the same as in /proc/meminfo,
    MemTotal -> SwapFree.

    casesensor and meminfo can be set to None if you don't want them

    This requires a properly configure lm_sensors! If the standard sensors frontend
    delivered with lm_sensors works your OK.

    Some sensors return raw-values, which have to be computed in order
    to get correct values. This is normally stored in your /etc/sensors.conf.
    Search in the corresponding section for your chipset, and search the
    compute statement, e.g. "compute temp3 @*2, @/2". Only the third
    argument is of interest. Insert this into the plugin activation line, e.g.:
    "[...] args=(('temp3', '@*2'), [...]". The @ stands for the raw value.
    The compute expression  works for the cpu- and casesensor.

    eg: plugin.activate('idlebar.system.sensors', args=(('temp2', '(@*30/43)+25'), 'temp1'))

    """
    class sensor:
        """
        class defining a temperature sensors and memory sensors
        """
        def __init__(self, sensor, compute_expression, hotstack):
            """
            Initialise an instance of a sensor
            @param sensor: the name of the sensor
            @param compute_expression: the expression to convert a raw value to a real value
            @param hotstack: is true when the sensor is above the max
            """
            _debug_('__init__(sensor=%r, compute_expression=%r, hotstack=%r)' %
                (sensor, compute_expression, hotstack), 2)
            self.pathform_path = config.SENSORS_PLATFORM_PATH
            self.i2cdev_path = config.SENSORS_I2CDEV_PATH
            self.kernel26 = False
            self.sensor = sensor
            self.senspath = self.getSensorPath()
            self.compute_expression = compute_expression
            self.hotstack = hotstack
            self.washot = False


        def temp(self):
            def temp_compute (rawvalue):
                try:
                    temperature = eval(self.compute_expression.replace ('@', str(rawvalue)))
                except:
                    _debug_('Compute expression does not evaluate', DERROR)
                    temperature = rawvalue
                return int(temperature)

            if self.senspath == -1 or not self.senspath:
                return '?'

            if self.kernel26:
                file = os.path.join(self.senspath, 'temp_input' + self.sensor[-1])
                fhot = os.path.join(self.senspath, 'temp_max' + self.sensor[-1])
                if not os.path.exists(file):
                    file = os.path.join(self.senspath, 'temp' + self.sensor[-1] + '_input')
                    fhot = os.path.join(self.senspath, 'temp' + self.sensor[-1] + '_max')
                hotdata = open(fhot).read().strip()
            else:
                file = os.path.join(self.senspath, self.sensor)

            data = open(file).read().strip()

            if self.kernel26:
                temp = int(temp_compute(float(data[0:2])))
                hot = int(temp_compute(float(hotdata[0:2])))
            else:
                temp = int(temp_compute (float(string.split(data)[2])))
                hot = int(temp_compute (float(string.split(data)[0])))

            if temp > hot:
                if not self.washot:
                    self.hotstack = self.hotstack + 1
                    self.washot = True
            else:
                if self.washot:
                    self.hotstack = self.hotstack - 1
                    self.washot = False

            return '%s°' % temp


        def getSensorPath(self):
            """
            Find the subdirectory with the sensors, searches upto two levels
            """
            #let's try if we find a sys filesystem (and kernel2.6 style sensors)
            if os.path.exists(self.i2cdev_path):
                self.kernel26 = True
                # search the i2cdev_path for the temp sensor
                for senspath in os.listdir(self.i2cdev_path):
                    testpath = os.path.join(self.i2cdev_path, senspath)
                    if senspath == 'temp1_input':
                        return self.i2cdev_path

                # search the sub-directories of i2cdev_path for the temp sensor
                for senspath in os.listdir(self.i2cdev_path):
                    testpath = os.path.join(self.i2cdev_path, senspath)
                    try:
                        for pos_sensors in os.listdir(testpath):
                            if pos_sensors == 'temp_input1':
                                return testpath
                            if pos_sensors == 'temp1_input':
                                return testpath
                    except OSError:
                        pass

            if not os.path.exists(self.pathform_path):
                if self.kernel26:
                    print 'Kernel 2.5/2.6 detected, but no i2c sensors found'
                    print 'Did you load (or compile) the necessary bus driver'
                    print 'and sensor chip modules'
                else:
                    print 'LM_Sensors data not available? Did you load i2c-proc'
                    print 'and configured lm_sensors?'
                    print 'temperatures will be bogus'
                return -1 #failure

            for senspath in os.listdir(self.pathform_path):
                testpath = os.path.join(self.pathform_path, senspath)
                if os.path.isdir(testpath):
                    if os.path.exists(os.path.join(testpath, '%s_max' % self.sensor)):
                        return testpath



    def __init__(self, cpu='temp3', case='temp2', ram='MemTotal'):
        """
        Initialise an instance of the IdleBarPlugin.
        @param cpu: name of the cpu sensor
        @param case: name of the case (chip set) sensor
        @param ram: name of the memory to be monitored
        """
        IdleBarPlugin.__init__(self)
        self.hotstack = 0
        self.case = None

        if isinstance (cpu, types.StringType):
            self.cpu = self.sensor(cpu, '@', self.hotstack)
        else:
            self.cpu = self.sensor(cpu[0], cpu[1], self.hotstack)

        if case:
            if isinstance (case, types.StringType):
                self.case = self.sensor(case, '@', self.hotstack)
            else:
                self.case = self.sensor(case[0], case[1], self.hotstack)


        self.ram = ram
        self.retwidth = 0


    def getRamStat(self):
        """
        Get the memory information from /proc/meminfo
        """
        data = open('/proc/meminfo').read().strip()
        rxp_ram = re.compile('^%s' % self.ram)

        for line in data.split('\n'):
            m = rxp_ram.match(line)
            if m:
                return '%sM' % (int(string.split(line)[1])/1024)


    def draw(self, (type, object), x, osd):
        """
        Draw the sensors in the idlebar
        @returns: the space taken by the images
        @rtype: int
        """
        widthtot  = 0

        font = osd.get_font(config.OSD_IDLEBAR_FONT)
        if self.hotstack:
            font.color = 0xff0000
        elif not self.hotstack and font.color == 0xff0000:
            font.color = 0xffffff

        text = self.cpu.temp()
        image_file = os.path.join(config.ICON_DIR, 'misc', 'cpu.png')
        w, h = imlib2.open(image_file).size
        text_w = font.stringsize(text)
        (image_x, image_y, text_x, text_y, width) = calc_positions(osd, w, h, text_w, font.h)
        osd.draw_image(image_file, (x+image_x, image_y, -1, -1))
        osd.write_text(text, font, None, x+text_x, text_y, text_w, font.h, 'center', 'top')
        widthtot += width + 5
        x += width + 5

        if self.case:
            text = self.case.temp()
            image_file = os.path.join(config.ICON_DIR, 'misc', 'case.png')
            w, h = imlib2.open(image_file).size
            text_w = font.stringsize(text)
            (image_x, image_y, text_x, text_y, width) = calc_positions(osd, w, h, text_w, font.h)
            osd.draw_image(image_file, (x+image_x, image_y, -1, -1))
            osd.write_text(text, font, None, x+text_x, text_y, text_w, font.h, 'center', 'top')
            widthtot += width + 5
            x += width + 5

        if self.ram:
            text = self.getRamStat()
            image_file = os.path.join(config.ICON_DIR, 'misc', 'memory.png')
            w, h = imlib2.open(image_file).size
            text_w = font.stringsize(text)
            (image_x, image_y, text_x, text_y, width) = calc_positions(osd, w, h, text_w, font.h)
            osd.draw_image(image_file, (x+image_x, image_y, -1, -1))
            osd.write_text(text, font, None, x+text_x, text_y, text_w, font.h, 'center', 'top')
            widthtot += width + 5
            x += width + 5

        return widthtot - 5


#----------------------------------- SENSOR2 -------------------------------

class sensors2(IdleBarPlugin):
    """
    Displays sensor temperature information (cpu, system) and memory-stats.

    Activate with:
    | plugin.activate('idlebar.system.sensors2', level=40, args=(
    |     ('sensorname', 'sensorpath', 'sensortype'),
    |     ..., 'meminfo', 'meminfo',
    |     ...))
    | plugin.activate('idlebar.system.sensors2', level=40, args=(
    |     ('sensorname', 'sensorpath', 'sensortype', 'compute_expression'),
    |     ..., 'meminfo', 'meminfo',
    |     ...))

    sensorname is the corresponding lm_sensors name, this should be: temp1,
    temp2, temp3, etc.

    sensorpath is the path, where the data files corresponding to sensorname
    can be found. For Linux 2.6, this is usually
    /sys/class/hwmon/hwmon[X]/device/, with [X] = 0, 1, 2, etc.

    sensortype is one of 'sys' or 'cpu', with 'sys' designating a case sensor.
    This value only changes the displayed icon.

    compute_expression: Some sensors return raw-values, which have to be
    computed in order to get correct values. This is normally stored in your
    /etc/sensors.conf.  Search in the corresponding section for your chipset,
    and search the compute statement, e.g. "compute temp3 @*2, @/2". Only the
    third argument is of interest. Insert this into the plugin activation line,
    e.g.:

    | [...] args=(('temp3', '/sys/class/hwmon/hwmon0/device/', 'sys', '@*2'), [...]

    The @ stands for the raw value.  The compute expression works for cpu and
    sys type sensors.

    meminfo[X] is the memory info u want, types ar the same as in
    /proc/meminfo: MemTotal -> SwapFree.

    There are no default values for any sensors whatsoever. If you provide only
    one sensor tuple, be sure to append a comma for the interpreter to
    understand it, e.g.:

    | plugin.activate('idlebar.system.sensors2', level=70, args=(
    |     ('temp1', '/sys/class/hwmon/hwmon1/device/', 'cpu'),
    | ))

    The plugin requires a properly configured lm_sensors package! If the standard
    sensors frontend delivered with lm_sensors works you are most probably OK.

    Also note that the sensor and meminfo arguments can be given in arbitrary
    order and will be displayed respectively, thus the following example:

    | plugin.activate('idlebar.system.sensors2', level=70, args=(
    |     ('temp1', '/sys/class/hwmon/hwmon1/device/', 'cpu'),
    |     'MemTotal',
    |     ('temp2', '/sys/class/hwmon/hwmon0/device/', 'sys', '@*2'),
    |     ('temp1', '/sys/class/hwmon/hwmon2/device/', 'cpu'),
    |     'MemFree'))

    works as expected and displays::

        [CPU] [MemTotal] [Case] [CPU] [MemFree]

    with their corresponding icons.
    """
    class sensor:
        """
        small class defining a temperature sensor
        """
        def __init__(self, sensor, senspath, senstype, compute_expression, hotstack):
            self.sensor = sensor
            self.senspath = senspath
            self.senstype = senstype
            self.compute_expression = compute_expression
            self.hotstack = hotstack
            self.washot = False
            self.kernel26 = self.isKernel26()


        def temp(self):
            """ Compute and return the temperature value of the sensor """
            def temp_compute (rawvalue):
                try:
                    temperature = eval(self.compute_expression.replace('@', str(rawvalue)))
                except:
                    _debug_('Cannot compute expression %r' % (self.compute_expression,), DERROR)
                    temperature = rawvalue
                return int(temperature)

            hotdata = None

            if self.kernel26:
                # Several flavours of files can be found in senspath, find the right ones
                file = os.path.join(self.senspath, 'temp_input' + self.sensor[-1])
                fhot = os.path.join(self.senspath, 'temp_max' + self.sensor[-1])
                if not os.path.exists(file):
                    file = os.path.join(self.senspath, 'temp' + self.sensor[-1] + '_input')
                if not os.path.exists(fhot):
                    fhot = os.path.join(self.senspath, 'temp' + self.sensor[-1] + '_max')
                if not os.path.exists(fhot):
                    fhot = os.path.join(self.senspath, 'temp' + self.sensor[-1] + '_crit')
                if os.path.exists(fhot):
                    hotdata = open(fhot).read().strip()
            else:
                file = os.path.join(self.senspath, self.sensor)

            data = open(file).read().strip()

            if self.kernel26 and hotdata is not None:
                temp = int(temp_compute(float(data[0:2])))
                hot = int(temp_compute(float(hotdata[0:2])))
            elif len(data.split()) > 2:
                temp = int(temp_compute (float(data.split()[2])))
                hot = int(temp_compute (float(data.split()[0])))
            else:
                temp = int(temp_compute (float(data)))
                hot = temp + 1

            if temp > hot:
                if self.washot == False:
                    self.hotstack = self.hotstack + 1
                    self.washot == True
            else:
                if self.washot == True:
                    self.hotstack = self.hotstack - 1
                    self.washot = False

            return '%s°' % temp


        def isKernel26(self):
            # Are we on Linux 2.6?
            if re.compile('^2\.6').match(os.uname()[2]) is not None:
                return True
            return False


    def __init__(self, *sensors):
        """ Initialize the plug-in """
        _debug_('sensor.__init__(sensors=%r)' % (sensors,), 2)
        for sens in sensors:
            if len(sens) < 3 or len(sens) > 4:
                self.reason = _('Sensors must have three or four values:') + ' %r' % sens
                return
            if not os.path.exists(sens[1]):
                self.reason = _('Sensor')+(' %s ' % sens[1])+_('does not exist')
                return
        IdleBarPlugin.__init__(self)

        self.sens = []
        self.hotstack = 0

        # Get the parameters
        for sens in sensors:
            if isinstance (sens, types.TupleType):
                # We probably have a temperature sensor here
                if len(sens) == 4:
                    # Temperature with compute_expression...
                    self.sens.append(self.sensor(sens[0], sens[1], sens[2], sens[3], self.hotstack))
                elif len(sens) == 3:
                    # ... and without
                    self.sens.append(self.sensor(sens[0], sens[1], sens[2], '@', self.hotstack))

            elif isinstance (sens, types.StringType):
                # This will be treated as meminfo
                self.sens.append(sens)
            # XXX: Do we need an else here (to designate a config error)

        self.retwidth = 0


    def getRamStat(self, ram):
        # Get the status of the given meminfo argument
        data = open('/proc/meminfo').read().strip()
        rxp_ram = re.compile('^%s' % ram)

        for line in data.split('\n'):
            m = rxp_ram.match(line)
            if m:
                return '%sM' % (int(string.split(line)[1])/1024)


    def draw(self, (type, object), x, osd):
        # draw the icons and values
        senswidth = 0
        img_width = x + 15

        font  = osd.get_font(config.OSD_IDLEBAR_FONT)
        if self.hotstack != 0:
            font.color = 0xff0000
        elif font.color == 0xff0000 and self.hotstack == 0:
            font.color = 0xffffff

        for sens in self.sens:
            icon = None
            if isinstance(sens, self.sensor):
                # temperature sensors
                if sens.senstype.lower().startswith('c'):
                    # CPU sensor
                    icon = 'misc/cpu.png'
                if sens.senstype.lower().startswith('s'):
                    # case sensor
                    icon = 'misc/case.png'
                # XXX: Do we need an else here (to designate a config error)
                text = sens.temp()
            else:
                # meminfo
                icon = 'misc/memory.png'
                text = self.getRamStat(sens)

            if icon is not None:
                # draw everything
                senswidth = font.stringsize(text)
                osd.draw_image(os.path.join(config.ICON_DIR, icon), (img_width, osd.y + 8, -1, -1))
                osd.write_text(text, font, None, img_width + 15, osd.y + 55 - font.h, senswidth, font.h, 'left', 'top')
                # img_width is the calculated x coordinate for the next icon
                img_width = img_width + senswidth + 30
                # We only need to calculate self.retwidth,
                # if we actually drew sensor icons
                self.retwidth = img_width - x - 15

        return self.retwidth
