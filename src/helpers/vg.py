#
# TV analyser
#
import sys, os, glob, re
d = '/sys/class/video4linux'
os.listdir(d)
pat = re.compile('(\D+)(\d+)')

def cmp_device(lhs, rhs):
    types = [ 'video', 'vbi', 'radio' ]
    lhs_grp = pat.match(lhs).groups()
    rhs_grp = pat.match(rhs).groups()
    lhs_val = types.index(lhs_grp[0]) * 100 + int(lhs_grp[1])
    rhs_val = types.index(rhs_grp[0]) * 100 + int(rhs_grp[1])
    return lhs_val - rhs_val

def cmp_video4linux(lhs, rhs):
    lhs_dev = lhs.split(':')[1]
    rhs_dev = rhs.split(':')[1]
    return cmp_device(lhs_dev, rhs_dev)

# For each video device find its family of video devices
video4linux_devs = {}
for video4linux_dev in os.listdir(d):
    device = os.path.join(d, video4linux_dev, 'device', 'video4linux:*')
    devs = glob.glob(device)
    devs.sort(cmp_video4linux)
    v4l2dev = []
    for dev in devs:
        v4l2dev.append(dev.split(':')[1])
    if video4linux_dev not in video4linux_devs:
        video4linux_devs[video4linux_dev] = v4l2dev

# Reduce the family of video devices to one per physical device
x = list(video4linux_devs)
x.sort(cmp_device)
devices = []
v4ldevices = {}
for dev in x:
    if dev not in devices:
        devices += video4linux_devs[dev]
        v4ldevices[dev] = video4linux_devs[dev]

# Print out the sorted results and the details
import config
import tv.v4l2
x = list(v4ldevices)
x.sort(cmp_device)
for dev in x:
    print dev
    print '%s' % ('-' * 41)
    for v4ldev in v4ldevices[dev]:
        name = open(os.path.join(d, v4ldev, 'name')).read().strip()
        print '%-8s: %s' % (v4ldev, name)
    print '%s' % ('-' * 41)
    v = tv.v4l2.Videodev(os.path.join('/dev', dev))
    v.print_settings()
    print 
