# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# rc.py - Remote control / Event and Callback handling
# -----------------------------------------------------------------------
# $Id$
#
# Notes: This is the only class to be thread safe!
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


import os
import copy
import time
import thread
import types

import config
import evdev

from event import Event, BUTTON

SHUTDOWN = -1

PYLIRC     = False
_singleton = None


def get_singleton(**kwargs):
    """
    get the global rc object
    """
    global _singleton

    # One-time init
    if _singleton == None:
        _singleton = EventHandler(**kwargs)
        
    return _singleton


def post_event(event):
    """
    add an event to the event queue
    """
    return get_singleton().post_event(event)


def app(application=0):
    """
    set or get the current app/eventhandler
    """
    if not application == 0:
        context = 'menu'
        if hasattr(application, 'app_mode'):
            context = application.app_mode
        if hasattr(application, 'eventhandler'):
            application = application.eventhandler
        get_singleton().set_app(application, context)

    return get_singleton().get_app()


def set_context(context):
    """
    set the context (map with button->event transformation
    """
    return get_singleton().set_context(context)


def register(function, repeat, timer, *arg):
    """
    register an function to be called
    repeat: if true, call the function later again
    timer:  timer * 0.01 seconds when to call the function
    """
    return get_singleton().register(function, repeat, timer, *arg)


def unregister(object):
    """
    unregister an object from the main loop
    """
    return get_singleton().unregister(object)


def shutdown():
    """
    shutdown the rc
    """
    return get_singleton().shutdown()


def poll():
    """
    poll all registered callbacks
    """
    return get_singleton().poll()


def get_event(blocking=False):
    """
    get next event. If blocking is True, this function will block until
    there is a new event (also call all registered callbacks while waiting)
    """
    return get_singleton().get_event(blocking)


# --------------------------------------------------------------------------------

# --------------------------------------------------------------------------------
# internal classes of this module
# --------------------------------------------------------------------------------

class Lirc:
    """
    Class to handle lirc events
    """
    def __init__(self):
        try:
            global pylirc
            import pylirc
        except ImportError:
            print 'WARNING: PyLirc not found, lirc remote control disabled!'
            raise
        try:
            if os.path.isfile(config.LIRCRC):
                self.resume()
            else:
                raise IOError
        except RuntimeError:
            print 'WARNING: Could not initialize PyLirc!'
            raise
        except IOError:
            print 'WARNING: %s not found!' % config.LIRCRC
            raise

        self.nextcode = pylirc.nextcode

        self.previous_code            = None
        self.repeat_count             = 0
        self.firstkeystroke           = 0.0
        self.lastkeystroke            = 0.0
        self.lastkeycode              = ''
        self.default_keystroke_delay1 = 0.25  # Config
        self.default_keystroke_delay2 = 0.25  # Config

        global PYLIRC
        PYLIRC = True

        
    def resume(self):
        """
        (re-)initialize pylirc, e.g. after calling close()
        """
        pylirc.init('freevo', config.LIRCRC)
        pylirc.blocking(0)


    def suspend(self):
        """
        cleanup pylirc, close devices
        """
        pylirc.exit()


    def get_last_code(self):
        """
        read the lirc interface
        """
        result = None

        if self.previous_code != None:
            # Let's empty the buffer and return the most recent code
            while 1:
                list = self.nextcode();
                if list != []:
                    break
        else:
            list = self.nextcode()

        if list == []:
            list = None

        if list != None:
            result = list

        self.previous_code = result
        return result



    def poll(self, rc):
        """
        return next event
        """
        list = self.get_last_code()

        if list == None:
            nowtime = 0.0
            nowtime = time.time()
            if (self.lastkeystroke + self.default_keystroke_delay2 < nowtime) and \
                   (self.firstkeystroke != 0.0):
                self.firstkeystroke = 0.0
                self.lastkeystroke = 0.0
                self.repeat_count = 0

        if list != None:
            nowtime = time.time()

            if list:
                for code in list:
                    if ( self.lastkeycode != code ):
                        self.lastkeycode = code
                        self.lastkeystroke = nowtime
                        self.firstkeystoke = nowtime

            if self.firstkeystroke == 0.0 :
                self.firstkeystroke = time.time()
            else:
                if (self.firstkeystroke + self.default_keystroke_delay1 > nowtime):
                    list = []
                else:
                    if (self.lastkeystroke + self.default_keystroke_delay2 < nowtime):
                        self.firstkeystroke = nowtime

            self.lastkeystroke = nowtime
            self.repeat_count += 1

            for code in list:
                return code

        
# --------------------------------------------------------------------------------

class Keyboard:
    """
    Class to handle keyboard input
    """
    def __init__(self):
        """
        init the keyboard event handler
        """
        import osd
        self.callback = osd.get_singleton()._cb


    def poll(self, rc):
        """
        return next event
        """
        return self.callback(rc.context != 'input')


# --------------------------------------------------------------------------------

class TcpNetwork:
    """
    Class to handle network control via TCP connection instead of UDP.
    """
    import socket
    MAX_MESSAGE_SIZE = 255 # the maximum size of a message
    def __init__(self):
        """
        init the network event handler
        """
        self.port = config.REMOTE_CONTROL_TCP_PORT
        self.host = config.REMOTE_CONTROL_TCP_HOST
        self.sock = self.socket.socket(self.socket.AF_INET, \
                self.socket.SOCK_STREAM)
        self.sock.setsockopt(self.socket.SOL_SOCKET, \
                self.socket.SO_REUSEADDR, 1)
        self.sock.setblocking(0)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        self.connections = []

    def poll(self, rc):
        """
        return next event
        """
        self._getNewConnections()

        throwout = []
        for conn in self.connections:
            try:
                buffer = conn.recv(self.MAX_MESSAGE_SIZE)
                if len(buffer) == 0:
                    throwout.append(self.connections.index(conn))
                else:
                    return buffer.strip()
            except self.socket.error, oErr:
                # if the error is not of typ 11 there is a problem with
                # the connection, remove it from the list.
                if oErr[0] != 11:
                    throwout.append(self.connections.index(conn))

        throwout.reverse()
        for index in throwout:
            self.connections.pop(index)

    def _getNewConnections(self):
        """
        accept new connections from the socket
        """
        try:
            conn, addr = self.sock.accept()
            conn.setblocking(0)
            self.connections.append(conn)
        except:
            # do nothing
            pass



class Network:
    """
    Class to handle network control
    """
    def __init__(self):
        """
        init the network event handler
        """
        import socket
        self.port = config.REMOTE_CONTROL_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(0)
        self.sock.bind(('', self.port))
        

    def poll(self, rc):
        """
        return next event
        """
        try:
            return self.sock.recv(100)
        except:
            # No data available
            return None

# --------------------------------------------------------------------------------

class Evdev:
    """
    Class to handle evdev events
    """
    def __init__(self):
        """
        init all specified devices
        """
        self._devs = []

        for dev in config.EVENT_DEVS:
            e = None

            if os.path.exists(dev):
                try:
                    e = evdev.evdev(dev)
                except:
                    print "Problem opening event device '%s'" % dev
            else:
                name = dev
                for dev in os.listdir('/dev/input'):
                    if not dev.startswith('event'):
                        continue

                    try:
                        dev = '/dev/input/' + dev
                        e = evdev.evdev(dev)
                    except:
                        continue

                    if e.get_name() == name:
                        break
                else:
                    e = None
                    print "Could not find any device named '%s'" % name

            if e is not None:
                print "Added input device '%s': %s" % (dev, e.get_name())
                self._devs.append(e)

        self._movements = {}

    def poll(self, rc):
        """
        return next event
        """
        for dev in self._devs:
            event = dev.read()
            if event is None:
                continue

            time, type, code, value = event

            if type == 'EV_KEY':
                self._movements = {}

                if config.EVENTMAP.has_key(code):
                    # 0 = release, 1 = press, 2 = repeat
                    if value > 0:
                        return config.EVENTMAP[code]
            elif type == 'EV_REL':
                if config.EVENTMAP.has_key(code):
                    if self._movements.has_key(code):
                        self._movements[code] += value
                    else:
                        self._movements[code] = value

                    if self._movements[code] < -10:
                        self._movements = {}
                        return config.EVENTMAP[code][0]
                    elif self._movements[code] > 10:
                        self._movements = {}
                        return config.EVENTMAP[code][1]

# --------------------------------------------------------------------------------
    
class EventHandler:
    """
    Class to transform input keys or buttons into events. This class
    also handles the complete event queue (post_event)
    """
    def __init__(self, use_pylirc=1, use_netremote=1):

        self.inputs = []
        if use_pylirc:
            try:
                self.inputs.append(Lirc())
            except:
                pass

        if config.USE_SDL_KEYBOARD:
            try:
                self.inputs.append(Keyboard())
            except:
                pass

        try:
            self.inputs.append(Evdev())
        except:
            pass

        if use_netremote and config.ENABLE_NETWORK_REMOTE and \
               config.REMOTE_CONTROL_PORT:
            self.inputs.append(Network())

        if use_netremote and config.ENABLE_TCP_NETWORK_REMOTE and \
               config.REMOTE_CONTROL_TCP_PORT and \
               config.REMOTE_CONTROL_TCP_HOST:
            self.inputs.append(TcpNetwork())

        self.app                = None
        self.context            = 'menu'
        self.queue              = []
        self.event_callback     = None
        self.callbacks          = []
        self.shutdown_callbacks = []
        self.poll_objects       = []
        # lock all critical parts
        self.lock               = thread.allocate_lock()
        # last time we stopped sleeping
        self.sleep_timer        = 0
        

    def set_app(self, app, context):
        """
        set default eventhandler and context
        """
        self.app     = app
        self.context = context


    def get_app(self):
        """
        get current eventhandler (app)
        """
        return self.app


    def set_context(self, context):
        """
        set context for key mapping
        """
        self.context = context
        

    def post_event(self, e):
        """
        add event to the queue
        """
        self.lock.acquire()
        if not isinstance(e, Event):
            self.queue += [ Event(e, context=self.context) ]
        else:
            self.queue += [ e ]
        self.lock.release()

        if self.event_callback:
            self.event_callback()


    def key_event_mapper(self, key):
        """
        map key to event based on current context
        """
        if not key:
            return None

        for c in (self.context, 'global'):
            try:
                e = config.EVENTS[c][key]
                e.context = self.context
                return e
            except KeyError:
                pass

        if self.context != 'input':
            print 'no event mapping for key %s in context %s' % (key, self.context)
            print 'send button event BUTTON arg=%s' % key
        return Event(BUTTON, arg=key)


    def register(self, function, repeat, timer, *arg):
        """
        register an function to be called
        repeat: if true, call the function later again
        timer:  timer * 0.01 seconds when to call the function
        """
        self.lock.acquire()
        if timer == SHUTDOWN:
            _debug_('register shutdown callback: %s' % function, 2)
            self.shutdown_callbacks.append([ function, arg ])
        else:
            if repeat:
                _debug_('register callback: %s' % function, 2)
            self.callbacks.append([ function, repeat, timer, 0, arg ])
        self.lock.release()

        
    def unregister(self, function):
        """
        unregister an object from the main loop
        """
        self.lock.acquire()
        for c in copy.copy(self.callbacks):
            if c[0] == function:
                _debug_('unregister callback: %s' % function, 2)
                self.callbacks.remove(c)
        for c in copy.copy(self.shutdown_callbacks):
            if c[0] == function:
                _debug_('unregister shutdown callback: %s' % function, 2)
                self.shutdown_callbacks.remove(c)
        self.lock.release()

        
    def suspend(self):
        for i in self.inputs:
            if hasattr(i, 'suspend'):
                i.suspend()


    def resume(self):
        for i in self.inputs:
            if hasattr(i, 'resume'):
                i.resume()


    def shutdown(self):
        """
        shutdown the rc
        """
        for c in copy.copy(self.shutdown_callbacks):
            _debug_('shutting down %s' % c[0], 2)
            c[0](*c[1])


    def poll(self):
        """
        poll all registered functions
        """
        # run all registered callbacks
        for c in copy.copy(self.callbacks):
            if c[2] == c[3]:
                # time is up, call it:
                if not c[1]:
                    # remove if it is no repeat callback:
                    self.lock.acquire()
                    if c in self.callbacks: 
                        self.callbacks.remove(c)
                    self.lock.release()
                else:
                    # reset counter for next run
                    c[3] = 0
                c[0](*c[4])
            else:
                c[3] += 1


    def get_event(self, blocking=False):
        """
        get next event. If blocking is True, this function will block until
        there is a new event (also call all registered callbacks while waiting)
        """
        if blocking:
            while 1:
                # get non blocking event
                event = self.get_event(False)
                if event:
                    return event
                # poll everything
                self.poll()

                # wait some time
                duration = 0.01 - (time.time() - self.sleep_timer)
                if duration > 0:
                    time.sleep(duration)
                self.sleep_timer = time.time()

                
        # search for events in the queue
        if len(self.queue):
            self.lock.acquire()
            try:
                try:
                    ret = self.queue[0]
                    del self.queue[0]
                    return ret
                except IndexError:
                    pass
            finally:
                self.lock.release()

        # search all input objects for new events
        for i in self.inputs:
            e = i.poll(self)
            if e:
                return self.key_event_mapper(e)

        return None



    def subscribe(self, event_callback=None):
        """
        subscribe to 'post_event'
        """
        if not event_callback:
            return

        self.event_callback = event_callback
