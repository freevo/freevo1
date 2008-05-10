# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Find video groups from Analog TV video devices
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   This module can be run under both python and freevo, only freevo mode
#   will generate the video groups
#   to run under python type:
#       python /path/to/vg.py --help (normally src/helpers/vg.py)
#   to run under freevo type:
#       freevo vg --help
#
# Todo:
#   Add DVB devices (someone with DVB card needs to do this)
#   Add more analogue devices
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

#
import sys, os, glob, re, copy
from optparse import OptionParser
try:
    import config
    from config import VideoGroup
    import tv.v4l2
    freevo = True
except ImportError:
    freevo = False


class Options(object):
    def __init__(self):
        (self.options, self.args) = self.parse()
        if freevo and self.options.write:
            try:
                self.config_file = open(self.options.config, 'a')
            except IOError, why:
                print 'Cannot open %r: %s' % (self.options.config, why)
                sys.exit(1)
        else:
            self.config_file = sys.stdout

    def parse(self):
        if freevo:
            self.config_filename = config.overridefile
        else:
            self.config_filename = 'stdout'

        parser = OptionParser(conflict_handler='resolve', usage="""
Scan the video devices to set-up the video groups
This only works for analogue devices

Usage: %prog [options]""", version='%prog 1.0')
        parser.add_option('-v', '--verbose', action='count', default=0,
            help='set the level of verbosity can be set more than once (max 2) [default:%default]')
        parser.add_option('-c', '--config', action='store', dest='config', default=self.config_filename,
            help='read the configuration from the file given [default:%default]')
        parser.add_option('-w', '--write', action='store_true', default=False,
            help='update config_file [default:%default]')
        parser.add_option('-d', '--debug', action='store_true', default=False,
            help='turn on debugging [default:%default]')
        return parser.parse_args()


class AnalyseVideo4Linux(object):
    def __init__(self, path):
        self.path = path
        self.devices = []
        self.v4l2_devmap = {}
        self.v4l2_devices = []
        self.pat = re.compile('(\D+)(\d+)')

    def cmp_device(self, lhs, rhs):
        """ Compare the device names, eg. video1 is less than vbi0 """
        types = [ 'video', 'vbi', 'radio' ]
        lhs_grp = self.pat.match(lhs).groups()
        rhs_grp = self.pat.match(rhs).groups()
        lhs_val = types.index(lhs_grp[0]) * 100 + int(lhs_grp[1])
        rhs_val = types.index(rhs_grp[0]) * 100 + int(rhs_grp[1])
        return lhs_val - rhs_val

    def _method1(self, devices):
        """ Method 1 search for Xdevice families using contents of modalias """
        video4linux_modules = {}
        for video4linux_dev in devices[:]:
            modalias_file = os.path.join(self.path, video4linux_dev, 'device', 'modalias')
            if os.path.exists(modalias_file):
                modalias = open(modalias_file).read().strip()
                if modalias in video4linux_modules:
                    video4linux_modules[modalias].append(video4linux_dev)
                else:
                    video4linux_modules[modalias] = [video4linux_dev]
                devices.remove(video4linux_dev)
        for module in video4linux_modules:
            v4l2devs = video4linux_modules[module]
            v4l2devs.sort(self.cmp_device)
            self.v4l2_devmap[v4l2devs[0]] = v4l2devs
        return devices

    def _method2(self, devices):
        """ Method 2 search for Xdevice families using video4linux:* links """
        def cmp_video4linux(self, lhs, rhs):
            lhs_dev = lhs.split(':')[1]
            rhs_dev = rhs.split(':')[1]
            return self.cmp_device(lhs_dev, rhs_dev)

        # For each video Xdevice find its family of video devices
        video4linux_devmap = {}
        for video4linux_dev in devices[:]:
            video4linux_file = os.path.join(self.path, video4linux_dev, 'device', 'video4linux:*')
            devs = glob.glob(video4linux_file)
            if len(devs) > 0 and len(devs[0].split(':')) == 1:
                continue
            devs.sort(cmp_video4linux)
            v4l2devs = []
            for dev in devs:
                v4l2devs.append(dev.split(':')[1])
            if video4linux_dev not in video4linux_devmap:
                video4linux_devmap[video4linux_dev] = v4l2devs
            devices.remove(video4linux_dev)

        # Reduce the family of video devices to one per physical device
        video4linux_devices = list(video4linux_devmap)
        video4linux_devices.sort(self.cmp_device)
        v4l2_devmap = []
        for dev in video4linux_devices:
            if dev not in v4l2_devmap:
                v4l2_devmap += video4linux_devmap[dev]
                self.v4l2_devmap[dev] = video4linux_devmap[dev]
        return devices

    def _analyse(self):
        """ Try different methods to determine the video families """
        self.devices = os.listdir(self.path)
        if options.options.debug:
            print 'DEBUG: devices:1:', self.devices
        self.devices = self._method1(self.devices)
        if options.options.debug:
            print 'DEBUG: devices:2:', self.devices
        self.devices = self._method2(self.devices)
        if options.options.debug:
            print 'DEBUG: devices:3:', self.devices
        return self.v4l2_devmap

    def v4ldevices(self):
        """ Get a list of video device families """
        self._analyse()
        v4l2_devices = list(self.v4l2_devmap)
        v4l2_devices.sort(analyser.cmp_device)
        self.v4l2_devices = []
        for device in v4l2_devices:
            self.v4l2_devices.append({'device' : device, 'family' : self.v4l2_devmap[device]})
        return self.v4l2_devices



class VideoGroupBuilder(object):
    DVB = ('saa7133',)
    IVTV = ('ivtv', 'cx88')
    TVALSA = ('saa7134',)
    WEBCAM = ('pwc',)
    NORMAL = ('bttv',)

    def __init__(self, devices):
        self.devices = devices
        self.groups = []


    def build(self):
        for device in self.devices:
            #print device
            vdev = os.path.join('/dev', device['device'])
            if not os.path.exists(vdev):
                print >>sys.stderr, '%r does not exist' % vdev
                continue
            try:
                videodev = tv.v4l2.Videodev(vdev)
            except Exception, why:
                print >>sys.stderr, why
                continue
            #print videodev.__dict__
            group_type = 'unknown'
            adev = None
            if videodev.driver in self.DVB:
                group_type = 'dvb'
            elif videodev.driver in self.IVTV:
                group_type = 'ivtv'
            elif videodev.driver in self.TVALSA:
                group_type = 'tvalsa'
                adev = 'alsa:adevice=hw.1,0:amode=1:audiorate=32000:forceaudio:immediatemode=0'
            elif videodev.driver in self.WEBCAM:
                group_type = 'webcam'
            elif videodev.driver in self.NORMAL:
                group_type = 'normal'
            else:
                print >>sys.stderr, '%r is an unknown driver' % videodev.driver
                continue

            vvbi = None
            for member in device['family']:
                if member.startswith('vbi'):
                    vvbi = os.path.join('/dev', member)
                    break

            desc = 'unknown'
            if hasattr(videodev, 'card'):
                desc = videodev.card
            vg = VideoGroup(desc=desc, group_type=group_type, vdev=vdev, vvbi=vvbi, adev=adev)
            self.groups.append(vg)

            if hasattr(videodev, 'inputs'):
                for input, values in videodev.inputs.items():
                    # Asuming the the first device is the tuner
                    if values[0] == 0:
                        vg.input_num = values[0]
                        vg.input_type = values[1]

            tuner_norm = []
            if hasattr(videodev, 'inputs'):
                for standard, values in videodev.standards.items():
                    tuner_norm.append(values[2])
            vg.tuner_norm = ','.join(tuner_norm)
            vg.tuner_chanlist = 'FixMe'


    def write(self):
        #for vg in self.groups:
        #    print vg.__dict__
        cf = options.config_file
        print >>cf, 'TV_VIDEO_GROUPS = ['
        for num in range(len(self.groups)):
            vg = self.groups[num]
            print >>cf, '  VideoGroup( # %s device, group %s' % (vg.group_type, num)
            print >>cf, '    desc=%r,' % vg.desc
            print >>cf, '    group_type=%r,' % vg.group_type
            print >>cf, '    vdev=%r,' % vg.vdev
            print >>cf, '    vvbi=%r,' % vg.vvbi
            print >>cf, '    adev=%r,' % vg.adev
            print >>cf, '    input_type=%r,' % vg.input_type
            print >>cf, '    input_num=%r,' % vg.input_num
            print >>cf, '    tuner_norm=%r,' % vg.tuner_norm
            print >>cf, '    tuner_chanlist=%r,' % vg.tuner_chanlist
            print >>cf, '    record_group=%r' % vg.record_group
            print >>cf, '  ),'
        print >>cf, ']'


    def dump(self):
        """ Print out the sorted results and the details """
        print
        for device in self.devices:
            try:
                uevent = open(os.path.join(video4linux_path, device['device'], 'uevent')).readlines()
                bus = driver = ''
                for line in uevent:
                    if 'PHYSDEVBUS=' in line:
                        bus = line.split('=')[1].strip()
                    if 'PHYSDEVDRIVER=' in line:
                        driver = line.split('=')[1].strip()
                print '%s (%s) %s' % (device['device'], bus, driver)
            except IOError:
                print '%s' % (device['device'],)
            print '%s' % ('-' * 41)
            for v4ldev in device['family']:
                name = open(os.path.join(video4linux_path, v4ldev, 'name')).read().strip()
                print '%-8s: %s' % (v4ldev, name)
            print '%s' % ('-' * 41)
            if freevo and options.options.verbose >= 2:
                v = tv.v4l2.Videodev(os.path.join('/dev', device['device']))
                v.print_settings()
                v.close()
            print



if __name__ == '__main__':
    options = Options()
    # this won't work if procfs is mounted somewhere else
    f = open('/proc/mounts')
    for line in f.readlines():
        fields = line.split()
        if fields[2] == 'sysfs':
            break
    else:
        print >>sys.stderr, 'Cannot find mounted sysfs'
        sys.exit(1)
    sysfs = fields[1]

    # Check that there are video4linux devices
    video4linux_path = os.path.join(sysfs, 'class', 'video4linux')
    if not os.path.isdir(video4linux_path):
        print >>sys.stderr, 'Cannot find video4linux in sysfs'
        sys.exit(1)

    analyser = AnalyseVideo4Linux(video4linux_path)
    v4ldevices = analyser.v4ldevices()

    if len(analyser.devices) > 0:
        print >>sys.stderr, 'Devices not checked'
        print >>sys.stderr, '%s' % ('-' * 41)
        for device in analyser.devices:
            print >>sys.stderr, device

    builder = VideoGroupBuilder(v4ldevices)
    if not freevo or options.options.verbose >= 1:
        builder.dump()
    if freevo:
        builder.build()
        builder.write()
