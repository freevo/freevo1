#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Input helper to process LIRC and other input devices.
# -----------------------------------------------------------------------
# $Id: imdb.py 11565 2009-05-25 18:36:59Z duncan $
#
# Notes:
#
# Todo:
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
import logging
logger = logging.getLogger("freevo.helpers.inputhelper")

import fcntl
import os
import sys
import struct
import time

import kaa

import config

wire_format = struct.Struct('d30p')


def post_key(key):
    """
    Send key to main process.
    """
    os.write(fd, wire_format.pack(time.time(), key))


class Lirc:
    """
    Class to handle lirc events
    """
    def __init__(self):
        logger.log( 9, 'Lirc.__init__()')
        try:
            global pylirc
            import pylirc
        except ImportError:
            logger.warning('PyLirc not found, lirc remote control disabled!')
            raise

        try:
            if os.path.isfile(config.LIRCRC):
                self.resume()
            else:
                raise IOError
        except RuntimeError:
            logger.warning('Could not initialize PyLirc!')
            raise
        except IOError:
            logger.warning('%r not found!', config.LIRCRC)
            raise

        global PYLIRC
        PYLIRC = True
        self.last_code = [None, 0, False]


    def __process_key(self, code):
        now = time.time()

        if self.last_code[0] == code:
            diff = now - self.last_code[1]

            if diff > config.LIRC_KEY_REPEAT[0] and self.last_code[2]:
                post_key(code)
                self.last_code = [code, now, False]
                return

            if diff > config.LIRC_KEY_REPEAT[1] and not self.last_code[2]:
                post_key(code)
                self.last_code = [code, now, False]
                return
        else:
            post_key(code)
            self.last_code = [code, now, True]


    def resume(self):
        """
        (re-)initialize pylirc, e.g. after calling close()
        """
        logger.log( 9, 'Lirc.resume()')
        fd = pylirc.init('freevo', config.LIRCRC)

        self.dispatcher = kaa.IOMonitor(self._handle_lirc_input)
        self.dispatcher.register(fd)


    def _handle_lirc_input(self):
        codes = pylirc.nextcode()
        if codes:
            for code in codes:
                self.__process_key(code)


    def suspend(self):
        """
        cleanup pylirc, close devices
        """
        logger.log( 9, 'Lirc.suspend()')
        self.dispatcher.unregister()
        pylirc.exit()


class Evdev:
    """
    Class to handle evdev events
    """
    def __init__(self):
        """
        init all specified devices
        """
        logger.log( 9, 'Evdev.__init__()')
        global evdev
        import evdev
        self._devs = []
        self._movements = {}
        self._bufkeys = {}
        self._lastkey = {}
        self._devpath = {}
        if (
            config.EVENT_MULTIKEYS == True and
            (config.EVDEV_MULTIKEYS_REPEAT == None or
             config.EVDEV_MULTIKEYS_REPEAT < 0.05)
           ):
            config.EVDEV_MULTIKEYS_REPEAT = 0.05
            logger.info("Set default config value EVDEV_MULTIKEYS_REPEAT: %r", 
                config.EVDEV_MULTIKEYS_REPEAT)

        for dev in config.EVENT_DEVS:
            self.initdev(dev)

        logger.info("Added evdev devices: %r", self._devpath)


    def initdev(self, dev):
        """
        init specified device
        """
        e = None

        if os.path.exists(dev):
            try:
                e = evdev.evdev(dev)
                self._devpath[e] = dev
            except:
                print "Problem opening event device '%s'" % dev

        else:
            names = []
            name = dev
            for dev in os.listdir('/dev/input'):
                if not dev.startswith('event'):
                    continue

                try:
                    dev = '/dev/input/' + dev
                    e = evdev.evdev(dev)
                except:
                    continue

                names.append(e.get_name())
                if e.get_name() == name:
                    break
            else:
                e = None
                logger.warning("Could not find device named '%s', possible are:\n  - %s", name, '\n  - '.join(names))
                
            if e is not None:
                self._devpath[e] = name

        if e is not None:
            logger.info("Added input device '%s': %s, object: %r", dev, e.get_name(), e)
            m = kaa.IOMonitor(self.__handle_event, e)
            m.register(e._fd)
            self._devs.append(m)

            if config.EVENT_MULTIKEYS == True:
                self._bufkeys[e] = None
                self._lastkey[e] = None

            self._movements[e] = {}

    def __handle_event(self, dev):
        """
        Handle evdev events
        """
        try:
            event = dev.read()
        except:
            logger.info("Lost input device, object: '%r'", dev)
            try:
                dev.close()
            except:
                pass

            time.sleep(5)
            try:
                self.initdev(self._devpath[dev])
            except:
                pass

            return

        if event is None:
            return

        evtime, type, code, value = event

        if type == 'EV_KEY':
            self._movements[dev] = {}

            if config.EVENT_MULTIKEYS == True and value > 0:
                if self._bufkeys[dev] is None:
                    self._bufkeys[dev] = code
                else:
                    self._bufkeys[dev] = self._bufkeys[dev] + '+' + code
            else:
                if config.EVENTMAP.has_key(code):
                    # 0 = release, 1 = press, 2 = repeat
                    if value > 0:
                        post_key(config.EVENTMAP[code])

        elif type == 'EV_SYN':
            if config.EVENT_MULTIKEYS == True:
                bufkeys = self._bufkeys[dev]
                self._bufkeys[dev] = None
                if config.KEYSMAP.has_key(bufkeys) and config.EVENTMAP.has_key(config.KEYSMAP[bufkeys]):
                    code = config.KEYSMAP[bufkeys]
                    key = config.EVENTMAP[code]
                    if self._lastkey[dev] == None:
                        self._lastkey[dev] = [evtime, key]
                    else:
                        if self._lastkey[dev][1] <> key or (evtime - self._lastkey[dev][0]) > config.EVDEV_MULTIKEYS_REPEAT:
                            self._lastkey[dev] = [evtime, key]
                            post_key(key)

        elif type == 'EV_REL':
            if config.EVENTMAP.has_key(code):
                if self._movements[dev].has_key(code):
                    self._movements[dev][code] += value
                else:
                    self._movements[dev][code] = value

                if self._movements[dev][code] < -10:
                    self._movements[dev] = {}
                    post_key(config.EVENTMAP[code][0])
                elif self._movements[dev][code] > 10:
                    self._movements[dev] = {}
                    post_key(config.EVENTMAP[code][1])


def handle_stdin():
    """
    Handle commands sent via stdin
    """
    cmd = sys.stdin.readline().strip()
    if cmd == 'suspend':
        for i in inputs:
            if hasattr(i, 'suspend'):
                i.suspend()

    elif cmd == 'resume':
        for i in inputs:
            if hasattr(i, 'resume'):
                i.resume()

    elif cmd == 'quit' or cmd == '':
        sys.exit(0)


if len(sys.argv) < 2:
    sys.stderr.write('No fd specified!')
    sys.exit(1)

fd = int(sys.argv[1])
logger.debug('Using pipe fd %d', fd)

# Put fd in non-blocking mode
flag = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, flag | os.O_NDELAY)


inputs = []
try:
    inputs.append(Lirc())
except:
    pass

if config.EVENT_DEVS:
    try:
        inputs.append(Evdev())
    except:
        pass

if len(inputs) > 0:
    stdin_dispatcher = kaa.IOMonitor(handle_stdin)
    stdin_dispatcher.register(sys.stdin)

    kaa.main.run()
else:
    sys.stderr.write('No inputs to work, exit!')
