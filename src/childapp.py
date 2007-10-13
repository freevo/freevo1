# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# childapp.py - Runs an application in a child process
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


import sys
import time
import os
import threading, thread
import signal
import copy
from subprocess import Popen, PIPE

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

    def __init__(self, app, debugname=None, doeslogging=0):
        self.lock = thread.allocate_lock()

        prio = 0

        if isinstance(app, unicode):
            _debug_('%r is a unicode string' % app)
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

            command = '%s %s' % (config.RUNAPP, app)
            debug_name = app[:app.find(' ')]

        else:
            while '' in app:
                app.remove('')

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

            debug_name = app[0]


        if debug_name.rfind('/') > 0:
            debug_name = debug_name[debug_name.rfind('/')+1:]
        else:
            debug_name = debug_name

        if debugname:
            debug_name = debugname

        if doeslogging or config.DEBUG_CHILDAPP:
            doeslogging = 1

        stdout_logger = os.path.join(config.FREEVO_LOGDIR, '%s-stdout-%s.log' % (debug_name, os.getuid()))
        try:
            self.stdout_log = doeslogging and open(stdout_logger, 'w') or None
        except OSError, e:
            _debug_('Cannot open "%s": %s' % (stdout_logger, e), config.DWARNING)
            self.stdout_log = None

        stderr_logger = os.path.join(config.FREEVO_LOGDIR, '%s-stderr-%s.log' % (debug_name, os.getuid()))
        try:
            self.stderr_log = doeslogging and open(stderr_logger, 'w') or None
        except OSError, e:
            _debug_('Cannot open "%s": %s' % (stderr_logger, e), config.DWARNING)
            self.stderr_log = None

        command_isstr = isinstance(command, str)
        if command_isstr:
            #command = command.strip() # strip spaces from the command string
            command_shell = True
            command_str = command
        else:
            command_shell = False
            command_str = ' '.join(command)
        self.child = None
        try:
            self.child = Popen(command, shell=command_shell, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            _debug_('Running (%s) "%s"%s with pid %s priority %s' % (\
                command_isstr and 'str' or 'list', command_str, command_shell and ' in shell' or '', \
                self.child.pid, prio), 1)
        except OSError, e:
            _debug_('Cannot run "%s": %s' % (command_str, e), config.DERROR)
            self.ready = False
            return

        self.so = Read_Thread('stdout', self.child.stdout, self.stdout_cb, debug_name, doeslogging)
        self.so.setDaemon(1)
        self.so.start()

        self.se = Read_Thread('stderr', self.child.stderr, self.stderr_cb, debug_name, doeslogging)
        self.se.setDaemon(1)
        self.se.start()

        if prio and config.CONF.renice:
            _debug_('%s %s -p %s' % (config.CONF.renice, prio, self.child.pid))
            os.system('%s %s -p %s 2>/dev/null >/dev/null' % \
                      (config.CONF.renice, prio, self.child.pid))

        self.ready = True


    # Write a string to the app.
    def write(self, line):
        _debug_('sending "%s" to pid %s' % (line.strip('\n'), self.child.pid))
        #self.shild.communicate(line)
        self.child.stdin.write(line)
        self.child.stdin.flush()


    def stdout_cb(self, line):
        '''Override this method to receive stdout from the child app
        The function receives complete lines'''
        pass


    def stderr_cb(self, line):
        '''Override this method to receive stderr from the child app
        The function receives complete lines'''
        pass


    def isAlive(self):
        if not self.child:
            return False
        if not self.ready: # return true if constructor has not finished yet
            return True
        return self.child.poll() == None


    def wait(self):
        """
        wait for the child process to stop
        returns the (pid, status) tuple
        """
        #self.child.wait()
        #self.status = self.child.returncode
        #return (self.child.pid, self.status)
        # this is the wait in ChildApp2
        try:
            pid, status = os.waitpid(self.child.pid, os.WNOHANG)
        except OSError:
            # strange, no child? So it is finished
            return True

        if pid == self.child.pid:
            self.status = self.child.returncode
            return True
        return False


    def kill(self, signal=15):
        '''
        Kill the application
        '''

        # killed already
        if not hasattr(self, 'child'):
            _debug_('This should never happen!')
            #raise 'no child attribute'
            return

        if not self.child:
            _debug_('already dead')
            #raise 'already dead'
            return

        self.lock.acquire()
        try:
            # maybe child is dead and only waiting?
            if self.child.poll() is not None:
                _debug_('killed the easy way, status %s' % (self.child.returncode))
                if not self.child.stdin.closed: self.child.stdin.close()
                if self.stdout_log: self.stdout_log.close()
                if self.stderr_log: self.stderr_log.close()
                self.child = None
                return

            if signal:
                _debug_('killing pid %s signal %s' % (self.child.pid, signal))
                try:
                    os.kill(self.child.pid, signal)
                except OSError, e:
                    _debug_('OSError killing pid %s: %s' % (self.child.pid, e))

            for i in range(60):
                if self.wait():
                    break
                time.sleep(0.1)
            else:
                signal = 9
                _debug_('killing pid %s signal %s' % (self.child.pid, signal))
                try:
                    os.kill(self.child.pid, signal)
                except OSError, e:
                    _debug_('OSError killing pid %s: %s' % (self.child.pid, e))
                for i in range(20):
                    if self.wait():
                        break
                    time.sleep(0.1)


            # now check if the app is really dead. If it is, poll()
            # will return the status code
            for i in range(5):
                if self.child.poll() is not None:
                    break
                time.sleep(0.1)
            else:
                # Problem: the program had more than one thread, each thread has a
                # pid. We killed only a part of the program. The filehandles are
                # still open, the program still lives. If we try to close the infile
                # now, Freevo will die.
                # Solution: there is no good one, let's try killall on the binary. It's
                # ugly but it's the _only_ way to stop this nasty app
                _debug_('Oops, command refuses to die, try bad hack....')
                util.killall(self.binary, sig=15)
                for i in range(20):
                    if self.child.poll() != None:
                        break
                    time.sleep(0.1)
                else:
                    # still not dead. Puh, something is realy broekn here.
                    # Try killall -9 as last chance
                    _debug_('Try harder to kill the app....')
                    util.killall(self.binary, sig=9)
                    for i in range(20):
                        if self.child.poll() != None:
                            break
                        time.sleep(0.1)
                    else:
                        _debug_('PANIC can\'t kill program', config.DERROR)
        finally:
            self.lock.release()
        if not self.child.stdin.closed: self.child.stdin.close()
        if self.stdout_log: self.stdout_log.close()
        if self.stderr_log: self.stderr_log.close()
        self.child = None



class ChildApp2(ChildApp):
    """
    Enhanced version of ChildApp handling most playing stuff
    """
    def __init__(self, app, debugname=None, doeslogging=0, stop_osd=2):
        rc.register(self.poll, True, 10)
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
        ChildApp.__init__(self, app, debugname, doeslogging)


    def stop_event(self):
        """
        event to send on stop
        """
        return PLAY_END


    def wait(self):
        """
        wait for the child process to stop
        """
        try:
            self.child.poll()
            pid, status = os.waitpid(self.child.pid, os.WNOHANG)
        except OSError, e:
            #print 'OSError: %s' % (e)
            return True

        if pid == self.child.pid:
            self.status = status
            return True
        return False


    def stop(self, cmd=''):
        """
        stop the child
        """
        rc.unregister(self.poll)
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
        if not self.isAlive():
            rc.post_event(self.stop_event())
            self.stop()



class Read_Thread(threading.Thread):
    """
    Thread for reading stdout or stderr from the child
    """
    def __init__(self, name, fh, callback, logger=None, doeslogging=0):
        '''Constructor of Read_Thread'''
        _debug_('Read_Thread.__init__(name=%r, fh=%r, callback=%r, logger=%r, doeslogging=%r' % \
            (name, fh, callback, logger, doeslogging), 2)
        threading.Thread.__init__(self)
        self.name = name
        self.fh = fh
        self.callback = callback
        self.logger = None
        if logger and doeslogging:
            logfile = os.path.join(config.FREEVO_LOGDIR, '%s-%s-%s.log' % (logger, name, os.getuid()))
            try:
                try:
                    os.unlink(logfile)
                except:
                    pass
                self.logger = open(logfile, 'w')
                _debug_('logging %s child to "%s"' % (name, logfile))
            except IOError, e:
                _debug_('cannot open "%s" for logging: %s' % (logfile, e))


    def run(self):
        try:
            self._handle_input()
        except (IOError, ValueError):
            pass


    def _handle_input(self):
        saved = ''
        while 1:
            data = self.fh.readline(300)
            if not data:
                _debug_('%s: no data, closing log' % (self.name))
                self.fh.close()
                if self.logger: self.logger.close()
                break
            else:
                data  = data.replace('\r', '\n')
                lines = data.split('\n')

                # Only one partial line?
                if len(lines) == 1:
                    saved += data
                else:
                    # Combine saved data and first line, send to app
                    if self.logger:
                        line = (saved + lines[0]).strip('\n')
                        self.logger.write(line+'\n')
                    rc.register(self.callback, False, 0, saved + lines[0])
                    saved = ''

                    # There's one or more lines + possibly a partial line
                    if lines[-1] != '':
                        # The last line is partial, save it for the next time
                        saved = lines[-1]

                        # Send all lines except the last partial line to the app
                        for line in lines[1:-1]:
                            if self.logger:
                                line = line.strip('\n')
                                self.logger.write(line+'\n')
                            rc.register(self.callback, False, 0, line)
                    else:
                        # Send all lines to the app
                        for line in lines[1:]:
                            if self.logger:
                                line = line.strip('\n')
                                self.logger.write(line+'\n')
                            rc.register(self.callback, False, 0, line)
