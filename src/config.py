# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Handle the configuration file init. Also start logging.
# -----------------------------------------------------------------------
# $Id$
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

"""
Handle the configuration file initialization
and start logging.

Try to find the freevo_config.py config file in the following places:
    1. ~/.freevo/freevo_config.py       The user's private config
    2. /etc/freevo/freevo_config.py     Systemwide config
    3. ./freevo_config.py               Defaults from the freevo dist
"""
import logging
import plugin

logger = logging.getLogger("freevo.config")

import sys, os, time, re, string, pwd
from threading import RLock
import setup_freevo
import traceback
import __builtin__
import locale
import logging

try:
    import freevo.version as version
except:
    import version

DINFO = 0
DWARNING = -1
DERROR = -2
DCRITICAL = -3

locale.setlocale(locale.LC_TIME, '')

if sys.hexversion >= 0x02030000:
    import warnings
    warnings.simplefilter("ignore", category=FutureWarning)
    warnings.simplefilter("ignore", category=DeprecationWarning)

# For Internationalization purpose
# an exception is raised with Python 2.1 if LANG is unavailable.
import gettext
try:
    gettext.install('freevo', os.environ['FREEVO_LOCALE'], 1)
except: # unavailable, define '_' for all modules
    import __builtin__
    __builtin__.__dict__['_'] = lambda m: m


# temp solution until this is fixed to True and False
# in all freevo modules
__builtin__.__dict__['TRUE']  = 1
__builtin__.__dict__['FALSE'] = 0


# String helper function. Always use this function to detect if the
# object is a string or not. It checks against str and unicode
def __isstring__(s):
    return isinstance(s, str) or isinstance(s, unicode)

__builtin__.__dict__['isstring'] = __isstring__


class Logger:
    """
    Class to create a logger object which will send messages to stdout and log them
    into a logfile
    """
    def __init__(self, logger, fp):
        self.logger = logger
        self.buffer = ''
        self.fp = fp


    def write(self, msg):
        global lock
        if lock:
            lock.acquire()
        try:
            if isinstance(msg, unicode):
                msg = msg.encode(LOCALE, 'replace')
            self.fp.write(msg)
            self.fp.flush()
            self.buffer += msg
            pos = self.buffer.find('\n')
            start_pos = 0
            while pos != -1:
                self.logger.info('%s', self.buffer[start_pos:pos])
                start_pos = pos + 1
                pos = self.buffer.find('\n', start_pos)
            if start_pos:
                self.buffer = self.buffer[start_pos:]
        except:
            logging.error('Logger', exc_info=True)
        if lock:
            lock.release()
        return

    def log(self, msg):
        self.write(msg + '\n')


    def flush(self):
        pass

    def close(self):
        pass


class VideoGroup:
    """
    """
    def __init__(self, vdev=None, vvbi='/dev/vbi', adev=None, input_type=None,
                 input_num=0, tuner_norm=None, tuner_chanlist=None,
                 tuner_type='internal', tuner_chan=None, irsend_trans=None,
                 record_group=None, desc='Freevo Default Video Group',
                 group_type='normal', cmd=None, avol=0):
        """
        Initialise an instance of a VideoGroup

        @ivar vdev: The video recording device, such as /dev/video0.
        @ivar vvbi: The video vbi device, such as /dev/vbi0.
        @ivar adev: The audio device, such as: None, /dev/dsp.
        @ivar avol: Default sound level for this videogroup (v4l2 value, 0 if not set)
        @ivar input_type: tuner, webcam
        @ivar input_num: The number of this input according to V4L
        @ivar tuner_type: internal (on a v4l device), or external (cable or sat box)
        @ivar tuner_norm: NTSC, PAL, SECAM
        @ivar tuner_chanlist: us-cable,
        @ivar tuner_chan: If using input_type=tuner and tuner_type=external set this to
            what channel it needs to be to get the signal, usually 3 or 4.
        @ivar irsend_trans: IR transmitter to use for multiple external tuners.
        @ivar record_group: VideoGroup that records for this tuner, default is to use the
            same device for record and play
        @ivar desc: A nice description for this VideoGroup.
        @ivar group_type: Special variable to identify devices like dvb or ivtv.  This
            can be one of: 'normal', 'ivtv', 'dvb', 'tvalsa' or 'webcam'.
        @ivar cmd: Command for execute external prog after the channel switched,
            such as 'sudo /usr/local/bin/setuptuner'
        """

        (v_norm, v_input, v_clist, v_dev) = TV_SETTINGS.split()
        if vdev is None:
            vdev = v_dev
        if input_type is None:
            input_type = v_input
        if tuner_norm is None:
            tuner_norm = v_norm
        if tuner_chanlist is None:
            tuner_chanlist = v_clist

        self.vdev = vdev
        self.vvbi = vvbi
        self.adev = adev
        self.avol = avol
        self.input_type = string.lower(input_type)
        self.input_num  = int(input_num)
        self.tuner_type = tuner_type
        self.tuner_norm = string.upper(tuner_norm)
        self.tuner_chanlist = tuner_chanlist
        self.tuner_chan = tuner_chan
        self.irsend_trans = irsend_trans
        self.record_group = record_group
        self.desc = desc
        self.group_type = group_type
        self.in_use = FALSE
        self.tuner = None
        self.cmd = None
        if cmd != None and isinstance(cmd, str) and cmd.strip() != '':
            self.cmd = cmd.strip()

    def __str__(self):
        s = '<%s: %s %s:%r %r>' % (self.group_type, self.vdev, self.input_num, self.input_type, self.tuner_norm)
        return s


    def checkvdev(self, vdev):
        """
        Check if the video device is correctly configured
        """
        from tv.v4l2 import Videodev
        try:
            dev = Videodev(vdev)
            try:
                if input_type != 'webcam':
                    try:
                        if input_type:
                            input_num = dev.getinputbyname(input_type)[0]
                    except KeyError, e:
                        print 'cannot find tuner %r for %r\npossible values are: %r' % \
                            (input_type, vdev, dev.inputs.keys())
                        sys.exit(1)
                    try:
                        if tuner_norm:
                            tuner_std = dev.getstdbyname(tuner_norm)
                    except KeyError, e:
                        print 'cannot find norm %r for %r\npossible values are: %r' % \
                            (tuner_norm, vdev, dev.standards.keys())
                        sys.exit(1)
                    print '%r:%r=%r' % (vdev, input_type, input_num)
                    print '%r:%r=%r' % (vdev, tuner_norm, tuner_std)
                else:
                    print '%r:%r=%r' % (vdev, input_type, dev.inputs.keys())
                    print '%r:%r=%r' % (vdev, tuner_norm, dev.standards.keys())
            finally:
                dev.close()
        except OSError, e:
            print 'Video device %r: %s' % (vdev, e)


def print_config_changes(conf_version, file_version, changelist):
    """
    print changes made between version on the screen
    """
    ver_old = float(file_version)
    ver_new = float(conf_version)
    if ver_old == ver_new:
        return
    print
    print 'You are using version %s, changes since then:' % file_version
    changed = [(cv, cd) for (cv, cd) in changelist if cv > ver_old]
    if not changed:
        print 'The changelist has not been updated, please notify the developers!'
    else:
        for change_ver, change_desc in changed:
            print 'Version %s:' % change_ver
            for line in change_desc.split('\n'):
                print '    ', line.strip()
            print
    print


def print_help():
    """
    print some help about config files
    """
    print("""Freevo is not completely configured to start The configuration is based
    on three files. This may sound oversized, but this way it's easier to
    configure.

    First Freevo loads a file called 'freevo.conf'. This file will be generated
    by calling 'freevo setup'. Use 'freevo setup --help' to get information
    about the parameter. Based on the information in that file, Freevo will
    guess some settings for your system. This takes place in a file called
    'freevo_config.py'. Since this file may change from time to time, you
    should not edit this file. After freevo_config.py is loaded, Freevo will
    look for a file called 'local_conf.py'. You can overwrite the variables
    from 'freevo_config.py' in here. There is an example for 'local_conf.py'
    called 'local_conf.py.example' in the Freevo distribution.

    If you need more help, use the internal webserver to get more information
    how to setup Freevo. To do this, you need to set WWW_USERS = { 'username' :
    'password' } in your local_conf.py and then you can access the doc at
    http://localhost:8080/help/

    The location of freevo_config.py is %s""" % os.environ['FREEVO_CONFIG'])

    print('Freevo searches for freevo.conf and local_conf.py in the following locations:')
    for dirname in cfgfilepath:
        print '  '+dirname
    print



#
# get information about what is started here:
# helper = some script from src/helpers or is webserver or recordserver
#
HELPER          = False
HELPER_APP      = None
IS_RECORDSERVER = False
IS_WEBSERVER    = False
IS_ENCODINGSERVER = False
IS_RSSSERVER = False
IS_PROMPT = False

__builtin__.__dict__['__freevo_app__'] = os.path.splitext(os.path.basename(sys.argv[0]))[0]

if sys.argv[0].find('main.py') == -1:
    HELPER = True
    HELPER_APP = os.path.basename(sys.argv[0]).replace('.py','')
    if sys.argv[0].find('recordserver.py') != -1:
        IS_RECORDSERVER = True
    elif sys.argv[0].find('webserver.py') != -1:
        IS_WEBSERVER = True
    elif sys.argv[0].find('encodingserver.py') != -1:
        IS_ENCODINGSERVER = True
    elif sys.argv[0].find('rssserver.py') != -1:
        IS_RSSSERVER = True
    elif sys.argv[0] == '':
        IS_PROMPT = True

#
# Send debug to stdout as well as to the logfile?
#
DEBUG_STDOUT = 0

#
# debugging messages are set by the logging level
# except for higher debugging message levels
# the DEBUG setting is overridden in local_conf.py
#
DEBUG = 0

LOGGING = logging.DEBUG


def make_freevodir(envvar, linux_dir, bsd_dir, private_dir):
    """
    Make the freevo specific directory and return it's name
    """
    if os.environ.has_key('OS_' + envvar):
        os_dirname = os.environ['OS_' + envvar]
    elif os.uname()[0] == 'FreeBSD':
        os_dirname = bsd_dir
    else:
        os_dirname = linux_dir

    if os.environ.has_key('FREEVO_' + envvar):
        freevo_dirname = os.environ['FREEVO_' + envvar]
    else:
        freevo_dirname = os.path.join(os_dirname, 'freevo')

    if not os.path.isdir(freevo_dirname):
        try:
            print 'trying "%s"...' % (freevo_dirname)
            os.makedirs(freevo_dirname)
            os.chmod(freevo_dirname, 01777)
        except OSError:
            freevo_dirname = os.path.join(os.environ['HOME'], '.freevo', private_dir)
            if not os.path.isdir(freevo_dirname):
                try:
                    print 'trying "%s"...' % (freevo_dirname)
                    os.makedirs(freevo_dirname)
                    os.chmod(freevo_dirname, 0755)
                except OSError, e:
                    print 'Warning: %s does not exist and can\'t be created' % freevo_dirname
                    print 'Please create this directory as root and set permissions for the'
                    print 'Freevo user to write to it.'
                    os_dirname = '/tmp'
                    freevo_dirname = os.path.join(os_dirname, 'freevo')
                    if not os.path.isdir(freevo_dirname):
                        try:
                            print 'trying "%s"...' % (freevo_dirname)
                            os.makedirs(freevo_dirname)
                        except OSError:
                            os_dirname = '/tmp'
                            freevo_dirname = os.path.join(os_dirname, ('freevo-' + os.getuid()), private_dir)
                            if not os.path.isdir(freevo_dirname):
                                print 'trying "%s"...' % (freevo_dirname)
                                os.makedirs(freevo_dirname)
                    print 'Using %s as cache directory, but this is a bad idea' % freevo_dirname
                    print
    return (os_dirname, freevo_dirname)


#
# find the log directory
#
OS_LOGDIR, FREEVO_LOGDIR = make_freevodir('LOGDIR', '/var/log', '/var/log', 'log')

#
# Freevo static dir:
#
# Under Linux, use /var/lib. Under FreeBSD, use /var/db.
#
OS_STATICDIR, FREEVO_STATICDIR = make_freevodir('STATICDIR', '/var/lib', '/var/db', 'static')

#
# Freevo cache dir:
#
# Under Linux, use /var/cache. Under FreeBSD, use /var/db.
#
OS_CACHEDIR, FREEVO_CACHEDIR = make_freevodir('CACHEDIR', '/var/cache', '/var/db', 'cache')

#
# Redirect stdout and stderr to stdout and /tmp/freevo.log
#
lock = RLock()

def _stack_function_(message='', limit=None):
    import traceback
    stack = traceback.extract_stack()
    if stack:
        if limit:
            logging.debug('%s\n*** %s' % (message, '*** '.join(traceback.format_list(stack[-limit-1:-1]))))
        else:
            logging.debug('%s\n*** %s' % (message, '*** '.join(traceback.format_list(stack)[0:-1])))


def _debug_function_(s, level=1):
    """
    The debug function that is mapped to the _debug_ builtin There are different
    levels of debugging and logging. Debug messages range from 1 (default) to 9
    (most verbose), logging messages range from NOTSET to DCRITICAL
    """
    if DEBUG < level:
        return
    if not s:
        return
    global lock
    global DEBUG_STDOUT
    if lock:
        lock.acquire()
    try:
        try:
            # add the current trace to the string
            if isinstance(s, unicode):
                s = s.encode(encoding, 'replace')
            where =  traceback.extract_stack(limit = 2)[0]
            msg = '%s (%s): %s' % (where[0][where[0].rfind('/')+1:], where[1], s)
            prefix = ''
            # log all the messages
            if level <= DCRITICAL:
                logging.critical(msg)
                prefix = _('CRITICAL')
            elif level == DERROR:
                logging.error(msg)
                prefix = _('ERROR')
            elif level == DWARNING:
                logging.warning(msg)
                prefix = _('WARNING')
            elif level == DINFO:
                logging.info(msg)
                prefix = _('INFO')
            else:
                logging.debug(msg)
                prefix = _('DEBUG')
            # print the message for info, warning, error and critical
            if level <= DWARNING or DEBUG_STDOUT:
                sys.__stdout__.write('%s: %s\n' % (prefix, s))
                sys.__stdout__.flush()
        except UnicodeEncodeError:
            print "_debug_ failed: %r" % msg
        except Exception, why:
            print "_debug_ failed: %r" % why
    finally:
        if lock:
            lock.release()


__builtin__.__dict__['_debug_'] = _debug_function_
__builtin__.__dict__['_stack_'] = _stack_function_
__builtin__.__dict__['DCRITICAL'] = DCRITICAL
__builtin__.__dict__['DERROR'] = DERROR
__builtin__.__dict__['DWARNING'] = DWARNING
__builtin__.__dict__['DINFO'] = DINFO


#
# Config file handling
#
cfgfilepath = ['.', os.path.expanduser('~/.freevo'), '/etc/freevo', '/usr/local/etc/freevo']


#
# Default settings
# These will be overwritten by the contents of 'freevo.conf'
#
CONF = setup_freevo.FreevoConf()

#
# Read the environment set by the start script
#
SHARE_DIR   = os.path.abspath(os.environ['FREEVO_SHARE'])
CONTRIB_DIR = os.path.abspath(os.environ['FREEVO_CONTRIB'])

SKIN_DIR  = os.path.join(SHARE_DIR, 'skins')
ICON_DIR  = os.path.join(SHARE_DIR, 'icons')
IMAGE_DIR = os.path.join(SHARE_DIR, 'images')
FONT_DIR  = os.path.join(SHARE_DIR, 'fonts')

RUNAPP = os.environ['RUNAPP']
logger.debug('RUNAPP: %s', RUNAPP)

logger.info('LOGDIR: %s %s', OS_LOGDIR, FREEVO_LOGDIR)
logger.info('STATICDIR: %s %s', OS_STATICDIR, FREEVO_STATICDIR)
logger.info('CACHEDIR: %s %s', OS_CACHEDIR, FREEVO_CACHEDIR)

#
# Check that freevo_config.py is not found in the config file dirs
#
for dirname in cfgfilepath[1:]:
    freevoconf = os.path.join(dirname, 'freevo_config.py')
    if os.path.isfile(freevoconf):
        print(('\nERROR: freevo_config.py found in %s, please remove it and use local_conf.py instead!') % freevoconf)
        sys.exit(1)

#
# Search for freevo.conf:
#
for dirname in cfgfilepath:
    freevoconf = os.path.join(dirname, 'freevo.conf')
    logger.debug('Trying freevo configuration file "%s"...', freevoconf)
    if os.path.isfile(freevoconf):
        logger.info('Loading freevo configuration file "%s"', freevoconf)

        commentpat = re.compile('([^#]*)( *#.*)')
        c = open(freevoconf)
        for line in c.readlines():
            if commentpat.search(line):
                line = commentpat.search(line).groups()[0]
            line = line.strip()
            if len(line) == 0:
                continue
            vals = line.split()
            logger.debug('Cfg file data: "%s"', line)
            try:
                name, val = vals[0].strip(), vals[2].strip()
            except:
                print 'Error parsing config file data "%s"' % line
                continue
            CONF.__dict__[name] = val

        c.close()
        w, h = CONF.geometry.split('x')
        x, y = CONF.position.split(',')
        CONF.width, CONF.height = int(w), int(h)
        CONF.x, CONF.y = int(x), int(y)
        break
else:
    print
    print 'Error: freevo.conf not found'
    print
    print_help()
    sys.exit(1)


#
# search missing programs at runtime
#
for program, valname, needed in setup_freevo.EXTERNAL_PROGRAMS:
    if not hasattr(CONF, valname) or not getattr(CONF, valname):
        setup_freevo.check_program(CONF, program, valname, needed)
    if not hasattr(CONF, valname) or not getattr(CONF, valname):
        setattr(CONF, valname, '')

#
# fall back to x11 if display is mga or fb and DISPLAY ist set
# or switch to fbdev if we have no DISPLAY and x11 or dga is used
#
if not HELPER:
    if os.environ.has_key('DISPLAY') and os.environ['DISPLAY']:
        if CONF.display in ('mga', 'fbdev'):
            print
            print 'Warning: display is set to %s, but the environment ' % CONF.display + \
                  'has DISPLAY=%s.' % os.environ['DISPLAY']
            print 'this could mess up your X display, setting display to x11.'
            print 'If you really want to do this, start \'DISPLAY="" freevo\''
            print
            CONF.display = 'x11'
    else:
        if CONF.display == 'x11':
            print
            print 'Warning: display is set to %s, but the environment ' % CONF.display + \
                  'has no DISPLAY set. Setting display to fbdev.'
            print
            CONF.display = 'fbdev'

elif CONF.display == 'dxr3':
    # don't use dxr3 for helpers. They don't use the osd anyway, but
    # it may mess up the dxr3 output (don't ask why).
    CONF.display = 'fbdev'

#
# Load freevo_config.py:
#
if os.path.isfile(os.environ['FREEVO_CONFIG']):
    logger.debug('Loading cfg: %s', os.environ['FREEVO_CONFIG'])
    logger.info('Loading freevo configuration file: "%s"', os.environ['FREEVO_CONFIG'])
    try:
        execfile(os.environ['FREEVO_CONFIG'], globals(), locals())
    except Exception, why:
        traceback.print_exc()
        raise SystemExit
    logger.info('Loaded freevo configuration file: "%s"', os.environ['FREEVO_CONFIG'])
else:
    print
    print "Error: %s: no such file" % os.environ['FREEVO_CONFIG']
    print
    sys.exit(1)


#
# Search for local_conf.py:
#
for dirname in cfgfilepath:
    overridefile = os.path.join(dirname, 'local_conf.py')
    logger.debug('Trying local configuration file "%s"...', overridefile)
    if os.path.isfile(overridefile):
        logger.info('Loading local configuration file: "%s"', overridefile)
        our_locals = {}
        try:
            execfile(overridefile, globals(), our_locals)
        except Exception, why:
            traceback.print_exc()
            raise SystemExit
        locals().update(our_locals)
        logger.info('Loaded local configuration file: "%s"', overridefile)

        try:
            CONFIG_VERSION
        except NameError:
            print
            print 'Error: your local_conf.py file has no version information'
            print 'Please check freevo_config.py for changes and set CONFIG_VERSION'
            print 'in %s to %s' % (overridefile, LOCAL_CONF_VERSION)
            print
            sys.exit(1)

        if int(str(CONFIG_VERSION).split('.')[0]) != int(str(LOCAL_CONF_VERSION).split('.')[0]):
            print
            print 'Error: The version information in freevo_config.py doesn\'t'
            print 'match the version in your local_conf.py.'
            print 'Please check freevo_config.py for changes and set CONFIG_VERSION'
            print 'in %s to %s' % (overridefile, LOCAL_CONF_VERSION)
            print_config_changes(LOCAL_CONF_VERSION, CONFIG_VERSION, LOCAL_CONF_CHANGES)
            sys.exit(1)

        if int(str(CONFIG_VERSION).split('.')[1]) != int(str(LOCAL_CONF_VERSION).split('.')[1]):
            print
            print 'Warning: freevo_config.py was changed, please check local_conf.py'
            print_config_changes(LOCAL_CONF_VERSION, CONFIG_VERSION, LOCAL_CONF_CHANGES)
        break

else:
    print
    print 'Error: local_conf.py not found'
    print
    print_help()
    print
    print 'Since it\'s highly unlikly you want to start Freevo without further'
    print 'configuration, Freevo will exit now.'
    sys.exit(0)

#
# Change UID/GID
#

if HELPER and not IS_PROMPT:
    app = HELPER_APP.upper()
    uid = app + '_UID'
    gid = app + '_GID'
    try:
        if eval(uid) and os.getuid() == 0:
            os.setgid(eval(gid))
            os.setuid(eval(uid))
    except Exception, why:
        pass
#
# Setup logging
#
if not IS_PROMPT:
    try:
        appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        if not appname:
            appname = 'prompt'
        logfile = os.path.join(FREEVO_LOGDIR, '%s-%s.log' % (appname, os.getuid()))
        fp = open(logfile, 'a')
        fp.close()
        # simple log rotation.. should use logging.handlers.RotatingFileHandler
        if os.path.exists(logfile) and os.path.getsize(logfile) > 2**22:
            os.rename(logfile, logfile+'.0')
    except IOError, e:
        print '%s' % e
        logfile = '/dev/null'

    logging.basicConfig(level=LOGGING, format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s',
        filename=logfile, filemode='a')

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = Logger(logging.getLogger('stdout'), sys.stdout)
    sys.stderr = Logger(logging.getLogger('stderr'), sys.stderr)
    ts = time.asctime(time.localtime(time.time()))
    sys.stdout.log('=' * 80)
    sys.stdout.log('Freevo %s started at %s' % (version.version, ts))
    sys.stdout.log('-' * 80)


def shutdown():
    sys.stdout.log('-' * 80)
    sys.stdout.log('Freevo %s finished at %s' % (version.version, ts))
    sys.stdout.log('=' * 80)
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = old_stdout
    sys.stderr = old_stderr

# set the umask
os.umask(UMASK)


#if not HELPER:
logging.getLogger('').setLevel(LOGGING)
for module, level in LOGGERS.items():
    logging.getLogger(module).setLevel(level)

#
# force fullscreen when freevo is it's own windowmanager
#
if len(sys.argv) >= 2 and sys.argv[1] == '--force-fs':
    START_FULLSCREEN_X = 1


#
# set default font
#
OSD_DEFAULT_FONTNAME = os.path.join(FONT_DIR, OSD_DEFAULT_FONTNAME)

#
# set list of video files to []
# (fill be filled from the plugins)
#
VIDEO_SUFFIX = []

for p in plugin.getall():
    if p.startswith('video'):
        suffix = p[6:].upper()
        if suffix:
            try:
                for s in eval('VIDEO_%s_SUFFIX' % suffix):
                    if not s in VIDEO_SUFFIX:
                        VIDEO_SUFFIX.append(s)
            except NameError:
                pass


#
# set data dirs
# if not set, set it to root and home dir
# if set, make all path names absolute
#
for type in ('video', 'audio', 'image', 'games'):
    n = '%s_ITEMS' % type.upper()
    x = eval(n)
    if x == None:
        x = []
        if os.environ.has_key('HOME') and os.environ['HOME']:
            x.append(('Home', os.environ['HOME']))
        x.append(('Root', '/'))
        exec('%s = x' % n)
        if not HELPER and plugin.is_active('mediamenu', type):
            print
            print 'Error: %s not set, set it to Home directory' % n
            print
        if type == 'video':
            VIDEO_ONLY_SCAN_DATADIR = True

    elif type == 'games':
        abs = []
        for d in x:
            pos = d[1].find(':')
            if pos == -1:
                abs.append((d[0], os.path.abspath(d[1]), d[2]))
            else:
                if pos > d[1].find('/'):
                    abs.append((d[0], os.path.abspath(d[1]), d[2]))
                else:
                    abs.append((d[0], d[1][0:pos+1] + os.path.abspath(d[1][pos+1:]), d[2]))
        exec ('%s = abs' % n)
    else:
        # The algorithm doesn't work for GAMES_ITEMS, so we leave it out
        abs = []
        for d in x:
            if isstring(d):
                pos = d.find(':')
                if pos == -1:
                    abs.append(os.path.abspath(d))
                else:
                    if pos > d.find('/'):
                        abs.append(os.path.abspath(d))
                    else:
                        abs.append(d[0:pos+1] + os.path.abspath(d[pos+1:]))
            else:
                pos = d[1].find(':')
                if pos == -1:
                    abs.append((d[0], os.path.abspath(d[1])))
                else:
                    if pos > d[1].find('/'):
                        abs.append((d[0], os.path.abspath(d[1])))
                    else:
                        abs.append((d[0], d[1][0:pos+1] + os.path.abspath(d[1][pos+1:])))
        exec ('%s = abs' % n)



if not TV_RECORD_DIR:
    TV_RECORD_DIR = VIDEO_ITEMS[0][1]
    if not HELPER and plugin.is_active('tv'):
        print
        print 'Error: TV_RECORD_DIR not set'
        print 'Please set TV_RECORD_DIR to the directory, where recordings should be stored'
        print 'or remove the tv plugin. Autoset variable to %s.' % TV_RECORD_DIR
        print

if not VIDEO_SHOW_DATA_DIR and not HELPER:
    print 'Error: VIDEO_SHOW_DATA_DIR not found'

#
# Autodetect the CD/DVD drives in the system if not given in local_conf.py
#
# ROM_DRIVES == None means autodetect
# ROM_DRIVES == [] means ignore ROM drives
#
if ROM_DRIVES == None:
    ROM_DRIVES = []
    if os.path.isfile('/etc/fstab'):
        re_cd        = re.compile('^(/dev/cdrom[0-9]*|/dev/[am]?cd[0-9]+[a-z]?)[ \t]+([^ \t]+)[ \t]+', re.I)
        re_cdrec     = re.compile('^(/dev/cdrecorder[0-9]*)[ \t]+([^ \t]+)[ \t]+', re.I)
        re_dvd       = re.compile('^(/dev/dvd[0-9]*)[ \t]+([^ \t]+)[ \t]+', re.I)
        re_iso       = re.compile('^([^ \t#]+)[ \t]+([^ \t]+)[ \t]+(iso|cd)9660', re.I)
        re_automount = re.compile('^none[ \t]+([^ \t]+).*supermount.*dev=([^,]+).*', re.I)
        re_bymountcd = re.compile('^(/dev/[^ \t]+)[ \t]+([^ ]*cdrom[0-9]*)[ \t]+', re.I)
        re_bymountdvd= re.compile('^(/dev/[^ \t]+)[ \t]+([^ ]*dvd[0-9]*)[ \t]+', re.I)
        fd_fstab = open('/etc/fstab')
        for line in fd_fstab:
            # Match on the devices /dev/cdrom, /dev/dvd, and fstype iso9660
            match_cd        = re_cd.match(line)
            match_cdrec     = re_cdrec.match(line)
            match_dvd       = re_dvd.match(line)
            match_iso       = re_iso.match(line)
            match_automount = re_automount.match(line)
            match_bymountcd = re_bymountcd.match(line)
            match_bymountdvd= re_bymountdvd.match(line)
            mntdir = devname = dispname = ''
            if match_cd or match_bymountcd:
                m = match_cd or match_bymountcd
                logger.debug('match_cd or match_bymountcd=%r', m.groups())
                mntdir = m.group(2)
                devname = m.group(1)
                dispname = 'CD-%s' % (len(ROM_DRIVES)+1)
            elif match_cdrec:
                logger.debug('match_cdrec=%r', match_cdrec.groups())
                mntdir = match_cdrec.group(2)
                devname = match_cdrec.group(1)
                dispname = 'CDREC-%s' % (len(ROM_DRIVES)+1)
            elif match_dvd or match_bymountdvd:
                m = match_dvd or match_bymountdvd
                logger.debug('match_dvd or match_bymountdvd=%r', m.groups())
                mntdir = m.group(2)
                devname = m.group(1)
                dispname = 'DVD-%s' % (len(ROM_DRIVES)+1)
            elif match_iso:
                logger.debug('match_iso=%r', match_iso.groups())
                mntdir = match_iso.group(2)
                devname = match_iso.group(1)
                dispname = 'CD-%s' % (len(ROM_DRIVES)+1)
            elif match_automount:
                logger.debug('match_automount=%r', match_automount.groups())
                mntdir = match_automount.group(1)
                devname = match_automount.group(2)
                # Must check that the supermount device is cd or dvd
                if devname.lower().find('cd') != -1:
                    dispname = 'CD-%s' % (len(ROM_DRIVES)+1)
                elif devname.lower().find('dvd') != -1:
                    dispname = 'DVD-%s' % (len(ROM_DRIVES)+1)
                elif devname.lower().find('hd') != -1:
                    logger.info('Trying to autodetect type of %r', devname)
                    if os.path.exists('/proc/ide/' + re.sub(r'^(/dev/)', '', devname) + '/media'):
                        if open('/proc/ide/' + re.sub(r'^(/dev/)', '', devname) + \
                            '/media', 'r').read().lower().find('cdrom') != 1:
                            dispname = 'CD-%s' % (len(ROM_DRIVES)+1)
                            logger.info('%r is a cdrom drive', devname)
                    else:
                        logger.info("%r doesn't seems to be a cdrom drive", devname)
                        mntdir = devname = dispname = ''
                else:
                    mntdir = devname = dispname = ''
            if mntdir:
                logger.info('line=%r, mntdir=%r, devname=%r, dispname=%r', line, mntdir, devname, dispname)

            if os.uname()[0] == 'FreeBSD':
                # FreeBSD-STABLE mount point is often device name + "c",
                # strip that off
                if devname and devname[-1] == 'c':
                    devname = devname[:-1]
                # Use native FreeBSD device names
                dispname = devname[5:]

            # Weed out duplicates
            for rd_mntdir, rd_devname, rd_dispname in ROM_DRIVES:
                if os.path.realpath(rd_devname) == os.path.realpath(devname):
                    if not HELPER:
                        print (('ROM_DRIVES: Auto-detected that %s is the same ' +
                                'device as %s, skipping') % (devname, rd_devname))
                    break
            else:
                # This was not a duplicate of another device
                if mntdir and devname and dispname:
                    ROM_DRIVES += [(mntdir, devname, dispname)]
                    if not HELPER:
                        print 'ROM_DRIVES: Auto-detected and added "%s"' % (ROM_DRIVES[-1], )
        fd_fstab.close()



#
# List of objects representing removable media, e.g. CD-ROMs,
# DVDs, etc.
#
REMOVABLE_MEDIA = []



if TV_CHANNELS == None and plugin.is_active('tv'):
    print
    print 'Error TV_CHANNELS is not set! Removing TV plugin'
    print
    TV_CHANNELS = []
    p = plugin.is_active('tv')
    plugin.remove(p[4])

#
# compile the regexp
#
VIDEO_SHOW_REGEXP_MATCH = re.compile("^.*" + VIDEO_SHOW_REGEXP).match
VIDEO_SHOW_REGEXP_SPLIT = re.compile("[\.\- ]*" + VIDEO_SHOW_REGEXP + "[\.\- ]*").split


#
# create cache subdirs
#
if not OVERLAY_DIR or OVERLAY_DIR == '/':
    print
    print 'ERROR: bad OVERLAY_DIR.'
    print 'Set OVERLAY_DIR it to a directory on the local filesystem where Freevo'
    print 'can store the metadata. Make sure this filesystem has about 100 MB free space'
    sys.exit(0)

if not os.path.isdir(OVERLAY_DIR):
    os.makedirs(OVERLAY_DIR)

# Make sure OVERLAY_DIR doesn't ends with a slash
# With that, we don't need to use os.path.join, normal string
# concat is much faster
if OVERLAY_DIR and OVERLAY_DIR.endswith('/'):
    OVERLAY_DIR = OVERLAY_DIR[:-1]
logger.info('overlaydir: %s', OVERLAY_DIR)

if not os.path.isdir(OVERLAY_DIR + '/disc'):
    os.makedirs(OVERLAY_DIR + '/disc')

if not os.path.isdir(OVERLAY_DIR + '/disc/metadata'):
    os.makedirs(OVERLAY_DIR + '/disc/metadata')

if not os.path.isdir(OVERLAY_DIR + '/disc-set'):
    os.makedirs(OVERLAY_DIR + '/disc-set')


#
# delete LD_PRELOAD for all helpers, main.py does it after
# starting the display
#
if HELPER:
    os.environ['LD_PRELOAD'] = ''

encoding = None
try:
    encoding = os.environ['LANG'].split('.')[1]
    ''.encode(encoding)
except:
    try:
        encoding = os.environ['LC_ALL'].split('.')[1]
        ''.encode(encoding)
    except:
        encoding = LOCALE

if not encoding:
    encoding = LOCALE

if not HELPER:
    logger.debug("Using '%s' encoding", encoding)

for k, v in CONF.__dict__.items():
    logger.debug('%r: %r', k, v)

# make sure USER and HOME are set
os.environ['USER'] = pwd.getpwuid(os.getuid())[0]
os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
