#
# TV analyser
#
import sys, os, glob, re, copy
try:
    import config
    import tv.v4l2
    freevo = True
except ImportError:
    freevo = False


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
        print 'DEBUG: devices:1:', self.devices
        self.devices = self._method1(self.devices)
        print 'DEBUG: devices:2:', self.devices
        self.devices = self._method2(self.devices)
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
    SAA = ('saa7134',)
    WEBCAM = ('webcam',)

    def __init__(self, devices):
        self.devices = devices


    def build(self):
        number = 0
        print 'TV_VIDEO_GROUPS = ['
        for device in self.devices:
            videodev = tv.v4l2.Videodev(os.path.join('/dev', device['device']))
            #print videodev.__dict__
            if videodev.driver in self.DVB:
                print '  # DVB device, group %s' % (number)
            elif videodev.driver in self.IVTV:
                print '  # IVTV device, group %s' % (number)
            elif videodev.driver in self.SAA:
                print '  # SAA device, group %s' % (number)
            elif videodev.driver in self.WEBCAM:
                print '  # WEBCAM device, group %s' % (number)
            else:
                continue
            print '  VideoGroup('
            print '    vdev = %r' % (os.path.join('/dev', device['device']),)
            for input, values in videodev.inputs.items():
                if values[0] == 0:
                    print '    Tuner Number %r' % values[0]
                    print '    Tuner is %r' % values[1]
            print '  ),'
            number += 1
        print ']'


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
            if freevo:
                v = tv.v4l2.Videodev(os.path.join('/dev', device['device']))
                v.print_settings()
            print



if __name__ == '__main__':
    # this won't work if procfs is mounted somewhere else
    f = open('/proc/mounts')
    for line in f.readlines():
        fields = line.split()
        if fields[2] == 'sysfs':
            break
    else:
        print 'Cannot find mounted sysfs'
        sys.exit(1)
    sysfs = fields[1]

    # Check that there are video4linux devices
    video4linux_path = os.path.join(sysfs, 'class', 'video4linux')
    if not os.path.isdir(video4linux_path):
        print 'Cannot find video4linux in sysfs'
        sys.exit(1)

    analyser = AnalyseVideo4Linux(video4linux_path)
    v4ldevices = analyser.v4ldevices()

    if len(analyser.devices) > 0:
        print 'Devices not checked'
        print '%s' % ('-' * 41)
        for device in analyser.devices:
            print device

    builder = VideoGroupBuilder(v4ldevices)
    builder.dump()
    if freevo:
        builder.build()
