# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Runs an application in a child process
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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

"""
Runs an application in a child process
"""
import logging
logger = logging.getLogger("freevo.childapp")

import sys
import time
import os
import threading, thread
import signal
import copy
from subprocess import Popen, PIPE

import kaa
import config
import osd
import rc
import util

from event import *



class ChildApp:
    """
    Base class for started child processes
    """
    ready = False

    def __init__(self, app, debugname=None, doeslogging=0, callback_use_rc=True):
        """
        Initialise ChildApp
        """
        logger.log( 9, 'ChildApp.__init__(app=%r, debugname=%r, doeslogging=%r)', app, debugname, doeslogging)
        # Use a non reentrant lock, stops kill being called twice
        self.lock = threading.Lock()
        self.status = None

        prio = 0

        if isinstance(app, unicode):
            logger.debug('%r is a unicode string', app)
            app = app.encode(config.LOCALE, 'ignore')

        if isinstance(app, str):
            # app is a string to execute. It will be executed by 'sh -c '
            # inside the popen code
            if app.find('--prio=') == 0 and not config.RUNAPP:
                try:
                    prio = int(app[7:app.find(' ')])
                except:
                    pass
                app = app[app.find(' ')+1:]
            if app.find('--prio=') == 0:
                self.binary = app[app.find(' ')+1:].lstrip()
            else:
                self.binary = app.lstrip()

            command = ('%s %s' % (config.RUNAPP, app)).strip()
            app_name = app[:app.find(' ')]

        else:
            app = filter(len, app)

            if app[0].find('--prio=') == 0 and not config.RUNAPP:
                try:
                    prio = int(app[0][7:])
                except:
                    pass
                app = copy.copy(app[1:])

            self.binary = str(' ').join(app)

            if config.RUNAPP:
                command = [ config.RUNAPP ] + app
            else:
                command = app

            app_name = app[0]

        if app_name.rfind('/') > 0:
            app_name = app_name[app_name.rfind('/')+1:]
        else:
            app_name = app_name

        if debugname:
            app_name = debugname

        if doeslogging or config.DEBUG_CHILDAPP:
            doeslogging = 1

        command_isstr = isinstance(command, str)
        if command_isstr:
            command_shell = True
            command_str = command
        else:
            command_shell = False
            command_str = ' '.join(command)
        self.child = None
        try:
            self.child = Popen(command, shell=command_shell, stdin=PIPE, stdout=PIPE, stderr=PIPE, \
                universal_newlines=True)
            try:
                logger.debug('Running (%s) %r%s with pid %s priority %s', command_isstr and 'str' or 'list', command_str, command_shell and ' in shell' or '', self.child.pid, prio)


            except Exception, why:
                print why
        except OSError, why:
            logger.error('Cannot run %r: %s', command_str, why)
            self.ready = False
            return

        self.so = Read_Thread('stdout', self.child.stdout, self.stdout_cb, app_name, doeslogging, callback_use_rc)
        self.so.setDaemon(1)
        self.so.start()

        self.se = Read_Thread('stderr', self.child.stderr, self.stderr_cb, app_name, doeslogging, callback_use_rc)
        self.se.setDaemon(1)
        self.se.start()

        if prio and config.CONF.renice:
            logger.debug('%s %s -p %s', config.CONF.renice, prio, self.child.pid)
            os.system('%s %s -p %s 2>/dev/null >/dev/null' % \
                      (config.CONF.renice, prio, self.child.pid))

        self.ready = True


    def write(self, line):
        """
        Send a string to the app.
        if the child is already dead, there is nothing to do
        """
        if self.child:
            logger.log( 9, 'ChildApp.write(line=%r) to pid %s', line.strip('\n'), self.child.pid)
            #self.child.communicate(line)
            try:
                self.child.stdin.write(line)
                self.child.stdin.flush()
            except IOError:
                logger.warning('ChildApp.write(line=%r): failed', line.strip('\n'))


    def stdout_cb(self, line):
        """
        Override this method to receive stdout from the child app
        The function receives complete lines
        """
        logger.log( 9, 'ChildApp.stdout_cb(line=%r)', line)
        pass


    def stderr_cb(self, line):
        """
        Override this method to receive stderr from the child app
        The function receives complete lines
        """
        logger.log( 9, 'ChildApp.stderr_cb(line=%r)', line)
        pass


    def isAlive(self):
        logger.log( 8, 'ChildApp.isAlive()')
        if not hasattr(self, 'child'):
            return False
        if self.child is None:
            return False
        if not self.ready: # return true if constructor has not finished yet
            return True
        return self.child.poll() is None


    def kill(self, signal=15):
        """
        Kill the application
        """
        logger.log( 9, 'ChildApp.kill(signal=%r)', signal)
        # killed already
        if not hasattr(self, 'child'):
            logger.error('This should never happen!')
            return

        if not self.child:
            logger.info('Already dead')
            return

        locked = self.lock.acquire()
        try:
            # maybe child is dead and only waiting?
            self.status = self.child.poll()
            if self.status is not None:
                logger.debug('killed %s the easy way, status %s', self.child.pid, self.status)
                if not self.child.stdin.closed: self.child.stdin.close()
                self.child = None
                return

            if signal:
                logger.debug('killing pid %s signal %s', self.child.pid, signal)
                try:
                    os.kill(self.child.pid, signal)
                except OSError, why:
                    logger.debug('OSError killing pid %s: %s', self.child.pid, e)

            for i in range(60):
                self.status = self.child.poll()
                if self.status is not None:
                    logger.debug('killed %s with signal %s, status %s', self.child.pid, signal, self.status)
                    break
                time.sleep(0.1)
            else:
                signal = 9
                logger.debug('zapping %s signal %s', self.child.pid, signal)
                try:
                    os.kill(self.child.pid, signal)
                except OSError, why:
                    logger.debug('OSError zapping pid %s: %s', self.child.pid, why)
                for i in range(20):
                    self.status = self.child.poll()
                    if self.status is not None:
                        logger.debug('zapped %s with signal %s, status %s', self.child.pid, signal, self.status)
                        break
                    time.sleep(0.1)
                else:
                    # Problem: the program had more than one thread, each thread has a
                    # pid. We killed only a part of the program. The file handles are
                    # still open, the program still lives. If we try to close the infile
                    # now, Freevo will die.
                    # Solution: there is no good one, let's try killall on the binary. It's
                    # ugly but it's the _only_ way to stop this nasty app
                    signal = 15
                    logger.debug('killing all %r signal %s', self.binary, signal)
                    util.killall(self.binary, sig=signal)
                    for i in range(20):
                        self.status = self.child.poll()
                        if self.status is not None:
                            logger.debug('killed all %r with signal %s, status %s', self.binary, signal, self.status)
                            break
                        time.sleep(0.1)
                    else:
                        # Still not dead. Puh, something is really broken here.
                        signal = 9
                        logger.debug('zapping all %r signal %s', self.binary, signal)
                        util.killall(self.binary, sig=signal)
                        for i in range(20):
                            self.status = self.child.poll()
                            if self.status is not None:
                                logger.debug('zapped all %r with signal %s, status %s', self.binary, signal, self.status)
                                break
                            time.sleep(0.1)
                        else:
                            logger.error('PANIC can\'t kill program')
        finally:
            self.lock.release()
        if not self.child.stdin.closed: self.child.stdin.close()
        self.child = None



class ChildApp2(ChildApp):
    """
    Enhanced version of ChildApp handling most playing stuff
    """
    def __init__(self, app, debugname=None, doeslogging=0, stop_osd=2, callback_use_rc=True):
        """
        Initialise ChildApp2
        """
        logger.debug('ChildApp2.__init__(app=%r, debugname=%r, doeslogging=%r, stop_osd=%r)', app, debugname, doeslogging, stop_osd)

        self.timer = kaa.Timer(self.poll)
        self.timer.start(0.1)
        rc.register(self.stop, True, rc.SHUTDOWN)

        self.is_video = 0                       # Be more explicit
        if stop_osd == 2:
            self.is_video = 1
            rc.post_event(Event(VIDEO_START))
            stop_osd = config.OSD_STOP_WHEN_PLAYING

        self.stop_osd = stop_osd
        if self.stop_osd:
            osd.stop()

        if hasattr(self, 'item'):
            rc.post_event(Event(PLAY_START, arg=self.item))

        # return status of the child
        self.status = 0

        # start the child
        ChildApp.__init__(self, app, debugname, doeslogging, callback_use_rc)


    def stop_event(self):
        """
        event to send on stop
        """
        logger.log( 9, 'ChildApp2.stop_event()')
        return PLAY_END


    def stop(self, cmd=''):
        """
        stop the child
        """
        logger.log( 9, 'ChildApp2.stop(cmd=%r)', cmd)
        self.timer.stop()
        rc.unregister(self.stop)

        if cmd and self.isAlive():
            self.write(cmd)
            # wait for the app to terminate itself
            for i in range(60):
                if not self.isAlive():
                    break
                time.sleep(0.1)

        # kill the app
        if self.isAlive():
            self.kill()

        # Ok, we can use the OSD again.
        if self.stop_osd:
            osd.restart()

        if self.is_video:
            rc.post_event(Event(VIDEO_END))


    def poll(self):
        """
        stop everything when child is dead
        """
        logger.log( 8, 'ChildApp2.poll()')
        if not self.isAlive():
            rc.post_event(self.stop_event())
            self.stop()



class Read_Thread(threading.Thread):
    """
    Thread for reading stdout or stderr from the child
    """
    def __init__(self, name, fh, callback, appname=None, doeslogging=0, callback_use_rc=True):
        """
        Constructor of Read_Thread
        """
        logger.log( 9, 'Read_Thread.__init__(name=%r, fh=%r, callback=%r, appname=%r, doeslogging=%r, callback_use_rc=%r)', name, fh, callback, appname, doeslogging, callback_use_rc)

        threading.Thread.__init__(self)
        self.name = name
        self.fh = fh
        self.callback = callback
        self.callback_use_rc = callback_use_rc
        self.logger = None
        if appname and doeslogging:
            # similar to rfc 3339
            t = time.strftime('%Y-%m-%d__%H-%M-%S')
            if not os.path.isdir(os.path.join(config.FREEVO_LOGDIR, appname)):
                os.mkdir(os.path.join(config.FREEVO_LOGDIR, appname))
            logfile = os.path.join(config.FREEVO_LOGDIR, appname, '%s-%s-%s__%s.log' % (appname, name, os.getuid(), t))
            try:
                try:
                    os.unlink(logfile)
                except:
                    pass
                self.logger = open(logfile, 'w')
                logger.debug('logging %s child to "%s"', name, logfile)
            except IOError, e:
                logger.debug('cannot open "%s" for logging: %s', logfile, e)


    def run(self):
        logger.log( 9, 'Read_Thread.run()')
        try:
            self._handle_input()
        except (IOError, ValueError):
            pass


    def _handle_input(self):
        logger.log( 9, 'Read_Thread._handle_input()')
        saved = ''
        while 1:
            data = self.fh.readline(300)
            if not data:
                logger.debug('%s: no data, closing log', self.name)
                self.fh.close()
                if self.logger:
                    if saved:
                        self.logger.write(saved+'\n')
                    self.logger.close()
                break
            else:
                data = saved + data
                complete_last_line = data.endswith('\n')
                if complete_last_line:
                    data = data.strip('\n')
                lines = data.split('\n')

                if complete_last_line:
                    complete_lines = lines
                    saved = ''
                else:
                    # not seen a case where there is an incomplete last line, so this may not work
                    complete_lines = lines[:-1]
                    saved += lines[-1]
                    #print 'saved=%r complete=%s lines=%r' % (saved, complete_last_line, lines)

                for line in complete_lines:
                    if self.logger:
                        self.logger.write(line+'\n')
                        self.logger.flush()
                    if self.callback_use_rc:
                        kaa.MainThreadCallable(self.callback, line)()
                    else:
                        self.callback(line)
