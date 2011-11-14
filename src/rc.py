# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Remote control / Event and Callback handling
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
Remote control / Event and Callback handling

This module is thread safe
"""
import logging
logger = logging.getLogger("freevo.rc")

import os
import copy
import time
import threading
import traceback

import kaa

import config

import pygame
import pygame.locals

from event import Event, BUTTON


SHUTDOWN = -1

PYLIRC     = False
_singleton = None

def get_singleton(**kwargs):
    """
    get the global rc object
    """
    _debug_('rc.get_singleton(kwargs=%r)' % (kwargs,), 4)
    global _singleton

    # One-time init
    if _singleton is None:
        _singleton = EventHandler(**kwargs)

    return _singleton


def post_event(event):
    """
    add an event to the event queue
    """
    _debug_('rc.post_event(event=%r)' % (event.name,), 2)
    return get_singleton().post_event(event)


def focused_app():
    """
    Return the current app object which has focus.
    """
    return get_singleton().get_app()


def app(application=0):
    """
    set or get the current app/eventhandler
    """
    _debug_('rc.app(application=%r)' % (application,), 4)
    if application != 0 and application != None:
        context = 'menu'
        if hasattr(application, 'app_mode'):
            context = application.app_mode
        # XXX Hmm this will make life difficult converting to kaa EventHandler
        if hasattr(application, 'eventhandler'):
            application = application.eventhandler
        add_app(application, context)

    return get_singleton().get_app()


def add_app(app):
    context = 'menu'
    if hasattr(app, 'event_context'):
        context = app.event_context
    _debug_('rc.add_app: Setting app %r (context %s)' % (app, context))
    get_singleton().add_app(app, context)


def remove_app(app):
    _debug_('rc.remove_app: Removing app %r ' % app)
    get_singleton().remove_app(app)


def set_app_context(app, context):
    get_singleton().set_app_context(app, context)


def get_app_context(app):
    return get_singleton().get_app_context(app)


def set_context(context):
    """
    set the context (map with button->event transformation
    """
    _debug_('rc.set_context(context=%r)' % (context,), 2)
    return get_singleton().set_context(context)


def register(function, repeat, timer, *arg):
    """
    register an function to be called
    repeat: if true, call the function later again
    timer:  timer * 0.01 seconds when to call the function
    """
    _debug_('rc.register(function=%r, repeat=%r, timer=%r, arg=%r)' % (function, repeat, timer, arg), 3)
    return get_singleton().register(function, repeat, timer, *arg)


def unregister(object):
    """
    unregister an object from the main loop
    """
    _debug_('rc.unregister(object=%r)' % (object,), 2)
    return get_singleton().unregister(object)


def shutdown():
    """
    shutdown the rc
    """
    _debug_('rc.shutdown()', 2)
    return get_singleton().shutdown()


def suspend():
    """
    suspend the rc
    """
    _debug_('rc.suspend()', 2)
    return get_singleton().suspend()


def resume():
    """
    resume the rc
    """
    _debug_('rc.resume()', 2)
    return get_singleton().resume()


# --------------------------------------------------------------------------------

# --------------------------------------------------------------------------------
# internal classes of this module
# --------------------------------------------------------------------------------
class InputHelper:
    """
    Class to handle input from the input helper app, which is used to process
    lirc and evdev events.
    """
    def __init__(self, rc):
        self.rc = rc

        import struct
        import subprocess
        import sys
        self.pipe = os.pipe()
        self.wire_format = struct.Struct('d30p')

        self.input = subprocess.Popen([sys.executable, os.path.join(os.environ['FREEVO_HELPERS'],'inputhelper.py'),
                                       str(self.pipe[1])],
                                        stdin=subprocess.PIPE)

        self.monitor = kaa.IOMonitor(self._handle_input)
        self.monitor.register(self.pipe[0])


    def _handle_input(self):
        """
        Handle input events from input helper over stderr
        """
        data = os.read(self.pipe[0], self.wire_format.size)
        if data:
            t, key = self.wire_format.unpack(data)
            if time.time() - t < 0.5:
                self.rc.post_key(key)
        else:
            self.input = None


    def __send_cmd(self, cmd):
        """
        Send a command to the input helper
        """
        try:
            if self.input:
                self.input.stdin.write(cmd + '\n')
        except:
            pass


    def suspend(self):
        """
        Suspend handling of input
        """
        self.__send_cmd('suspend')


    def resume(self):
        """
        Resume handling of input.
        """
        self.__send_cmd('resume')


    def shutdown(self):
        """
        Shutdown the helper
        """
        self.__send_cmd('quit')
        self.input.wait()

# --------------------------------------------------------------------------------

class Keyboard:
    """
    Class to handle keyboard input
    """
    def __init__(self, rc):
        """
        init the keyboard event handler
        """
        self.rc = rc
        _debug_('Keyboard.__init__()', 2)
        get_pygame_handler().register_handler(pygame.locals.KEYDOWN, self.__process_key_event)


    def __convert_modifier(self, modifier):
        """
        Converts pygame modifiers to config's modifier
        """
        result = 0
        if modifier & pygame.locals.KMOD_ALT:
            result = result | config.M_ALT
        if modifier & pygame.locals.KMOD_CTRL:
            result = result | config.M_CTRL
        if modifier & pygame.locals.KMOD_SHIFT:
            result = result | config.M_SHIFT
        return result
    
    
    def __process_key_event(self, event):
        """ Process pygame key down events """
        if self.rc.context == 'input' and event.key > 30:
            try:
                if event.unicode != u'':
                    self.rc.post_key(event.unicode)
                    return 
            except:
                pass
        
        key = event.key
        if not key:
            key = event.scancode
            key = key | config.M_SCAN
        key = key | self.__convert_modifier(event.mod)

        if key in config.KEYMAP.keys():
            self.rc.post_key(config.KEYMAP[key])
            return
        
        # don't know what this is, post it as it is
        try:
            if event.unicode != u'':
                self.rc.post_key(event.unicode)
        except:
            pass


class Mouse:
    """
    Class to handle mouse input
    """
    def __init__(self, rc):
        """
        Init the mouse event handler
        """
        global dialog
        import dialog        
        self.rc = rc
        pgh = get_pygame_handler()
        pgh.register_handler(pygame.locals.MOUSEMOTION, self.__process_mouse_motion)
        pgh.register_handler(pygame.locals.MOUSEBUTTONDOWN, self.__process_mouse_btn_down)
        pgh.register_handler(pygame.locals.MOUSEBUTTONUP, self.__process_mouse_btn_up)
        self.hide_mouse_timer = kaa.OneShotTimer(self.__hide_mouse)


    def __hide_mouse(self):
        self.hide_mouse_timer.stop()
        pygame.mouse.set_visible(0)


    def __show_mouse(self):
        # Check if mouse should be visible or hidden
        mouserel = pygame.mouse.get_rel()
        mousedist = (mouserel[0]**2 + mouserel[1]**2) ** 0.5

        if mousedist > 4.0:
            pygame.mouse.set_visible(1)
            self.hide_mouse_timer.start(2)

    
    def __process_mouse_motion(self, event):
        """
        Process mouse motion events.
        """
        self.__show_mouse()
        mouse_evt = Event('MOUSE_MOTION')
        mouse_evt.pos = event.pos
        self.rc.post_event(mouse_evt)


    def __process_mouse_btn_down(self, event):
        """
        Process mouse button down events.
        """
        self.__show_mouse()
        mouse_evt = Event('MOUSE_BTN_PRESS')
        mouse_evt.pos = event.pos
        mouse_evt.button = event.button
        self.rc.post_event(mouse_evt)

    
    def __process_mouse_btn_up(self, event):
        """
        Process mouse button up events.
        """
        self.__show_mouse()
        mouse_evt = Event('MOUSE_BTN_RELEASE')
        mouse_evt.pos = event.pos
        mouse_evt.button = event.button
        self.rc.post_event(mouse_evt)

# --------------------------------------------------------------------------------

class Joystick:
    """
    Class to handle joystick input
    """
    def __init__(self, rc):
        _debug_('Joystick.__init__()', 2)
        self.rc = rc
        pygame.joystick.init()
        if pygame.joystick.get_count() < 1:
            pygame.joystick.quit()
        if pygame.joystick.get_count() == 1:
            config.JOYSTICK_ID = 0
        self.joystick = pygame.joystick.Joystick(config.JOYSTICK_ID)
        self.joystick.init()
        print self.joystick.get_name()
        print self.joystick.get_numaxes()
        print self.joystick.get_numbuttons()
        print self.joystick.get_numhats()
        print self.joystick.get_numballs()
        pgh = get_pygame_handler()
        pgh.register_handler(pygame.locals.JOYBUTTONDOWN, self.__process_btn)
        pgh.register_handler(pygame.locals.JOYAXISMOTION, self.__process_axis)
        pgh.register_handler(pygame.locals.JOYBALLMOTION, self.__process_ball)
        pgh.register_handler(pygame.locals.JOYHATMOTION, self.__process_hat)
        

    def __process_hat(self, evt):
        print evt


    def __process_ball(self, evt):
        print evt


    def __process_axis(self, evt):
        print evt


    def __process_btn(self, evt):
        print evt


# --------------------------------------------------------------------------------

class TCPNetwork:
    """
    Class to handle network control via TCP connection instead of UDP.
    """
    def __init__(self, rc):
        """
        init the network event handler
        """
        _debug_('TCPNetwork.__init__()', 1)
        self.rc = rc
        self.socket = kaa.Socket()
        self.socket.signals['new-client'].connect(self.__accept)
        self.socket.listen((config.REMOTE_CONTROL_TCP_HOST, config.REMOTE_CONTROL_TCP_PORT))
    
    def __accept(self, socket):
        """
        Accept a new TCP connection
        """
        socket.signals['readline'].connect(self.__recv)

    def __recv(self, data):
        """
        Handle received data
        """
        self.rc.post_key(data.strip())


class UDPNetwork:
    """
    Class to handle network control
    """
    def __init__(self, rc):
        """
        init the network event handler
        """
        _debug_('UDPNetwork.__init__()', 2)
        self.rc = rc
        import socket
        self.port = config.REMOTE_CONTROL_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        self.channel = kaa.IOChannel(self.sock)
        self.channel.signals['read'].connect(self.__recv)
        
    def __recv(self, data):
        """
        Handle received data
        """
        self.rc.post_key(data)


# --------------------------------------------------------------------------------

class EventHandler:
    """
    Class to transform input keys or buttons into events. This class
    also handles the complete event queue (post_event)
    """
    def __init__(self, use_pylirc=1, use_netremote=1, is_helper=1):
        _debug_('EventHandler.__init__(use_pylirc=%r, use_netremote=%r, is_helper=%r)' % \
            (use_pylirc, use_netremote, is_helper), 1)

        _debug_('config.HELPER=%r' % (config.HELPER,))

        self.inputs = []
        if not config.HELPER:
            self.inputs.append(InputHelper(self))
            #if use_pylirc:
            #    try:
            #        self.inputs.append(Lirc(self))
            #    except:
            #        pass

            if config.SYS_USE_KEYBOARD:
                try:
                    self.inputs.append(Keyboard(self))
                except:
                    pass
            
            if config.SYS_USE_MOUSE:
                try:
                    self.inputs.append(Mouse(self))
                except:
                    pass

            if config.SYS_USE_JOYSTICK:
                try:
                    self.inputs.append(Joystick(self))
                except:
                    pass

            #if config.EVENT_DEVS:
            #    try:
            #        self.inputs.append(Evdev(self))
            #    except:
            #        pass

            if use_netremote and config.ENABLE_NETWORK_REMOTE and config.REMOTE_CONTROL_PORT:
                self.inputs.append(UDPNetwork(self))

            if use_netremote and config.ENABLE_TCP_NETWORK_REMOTE and config.REMOTE_CONTROL_TCP_PORT:
                self.inputs.append(TCPNetwork(self))

        self.app                = None
        self.context            = 'menu'
        self.apps               = []
        self.shutdown_callbacks = []
        # lock all critical parts
        self.lock               = threading.RLock()

        #kaa.Timer(self.poll).start(config.POLL_TIME)
        _debug_('EventHandler.self.inputs=%r' % (self.inputs,), 1)


    def add_app(self, app, context):
        self.app = app
        self.context = context
        self.apps.append([app, context])


    def remove_app(self, app):
        if app == self.app:
            self.apps.pop()
            self.app,self.context = self.apps[-1]
            _debug_('Focused App=%r context=%r' % (self.app,self.context))
        else:
            for i in xrange(len(self.apps)):
                if self.apps[i][0] == app:
                    del self.apps[i]


    def set_app_context(self, app, context):
        if app == self.app:
            self.context = context
            self.apps[-1][1] = context
            _debug_('Focus App Context changed to %r' % context)
        else:
            for i in xrange(len(self.apps)):
                if self.apps[i][0] == app:
                    self.apps[i][1] = context


    def set_app(self, app, context):
        """
        set default eventhandler and context
        """
        _debug_('EventHandler.set_app(app=%r, context=%r)' % (app, context), 2)
        self.app     = app
        self.context = context


    def get_app(self):
        """
        get current eventhandler (app)
        """
        _debug_('EventHandler.get_app()', 4)
        return self.app


    def set_context(self, context):
        """
        set context for key mapping
        """
        _debug_('EventHandler.set_context(context=%r)' % (context,), 2)
        print('EventHandler context=%r' % (context,)) #DJW
        self.context = context


    def post_event(self, event):
        """
        add event to the queue
        """
        _debug_('EventHandler.post_event(event=%r)' % (event.name,), 2)
        if not isinstance(event, Event):
            event = Event(event, context=self.context)
        event.post()


    def post_key(self, key):
        """
        Map the specified key to event based on the current context and add it 
        to the queue.
        """
        self.key_event_mapper(key).post()


    def key_event_mapper(self, key):
        """
        map key to event based on current context
        """
        _debug_('EventHandler.key_event_mapper(key=%r)' % (key,), 2)
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
            _debug_('no event mapping for key %r in context %r' % (key, self.context), DINFO)
            _debug_('send button event BUTTON arg=%r' % (key,))
        return Event(BUTTON, arg=key)


    def register(self, function, repeat, timer, *arg):
        """
        register an function to be called
        repeat: if true, call the function later again
        timer:  timer * 0.01 seconds when to call the function
        """
        _debug_('EventHandler.register(function=%r, repeat=%r, timer=%r, arg=%r)' % (function, repeat, timer, arg), 2)
        self.lock.acquire()
        try:
            if timer == SHUTDOWN:
                _debug_('register shutdown callback: %s' % function, 2)
                self.shutdown_callbacks.append([ function, arg ])
            else:
                print 'Deprecated use of register, use kaa.Timer/OneShotTimer instead of this function!'
        finally:
            self.lock.release()


    def unregister(self, function):
        """
        unregister an object from the main loop
        """
        _debug_('EventHandler.unregister(function=%r)' % (function,), 2)
        self.lock.acquire()
        try:
            for c in copy.copy(self.shutdown_callbacks):
                if c[0] == function:
                    _debug_('unregister shutdown callback: %s' % function, 2)
                    self.shutdown_callbacks.remove(c)
        finally:
            self.lock.release()


    def suspend(self):
        _debug_('EventHandler.suspend()', 2)
        for i in self.inputs:
            if hasattr(i, 'suspend'):
                i.suspend()


    def resume(self):
        _debug_('EventHandler.resume()', 2)
        for i in self.inputs:
            if hasattr(i, 'resume'):
                i.resume()


    def shutdown(self):
        """
        shutdown the rc
        """
        _debug_('EventHandler.shutdown()', 2)
        for c in copy.copy(self.shutdown_callbacks):
            _debug_('shutting down %s' % c[0], 2)
            c[0](*c[1])
        
        for i in self.inputs:
            if hasattr(i, 'shutdown'):
                i.shutdown()


__pygame_handler = None

def get_pygame_handler():
    """ Returns the pyGame event handler object """
    global __pygame_handler
    if __pygame_handler is None:
        __pygame_handler = PYGameEventHandler()
    return __pygame_handler


class PYGameEventHandler:
    """ Event handling thread for pygame events.
    
    Clients should use register_handler to receive the events they are 
    interested in. If a client no longer wants to receive events then use 
    unregister_handler to stop being called with the specified event type.
    
    Registered handlers will be called the event that caused them to be called.
    
    def handler(event):
        pass
        
    """
    def __init__(self):
        self.handlers = {}
        self.thread = None

    
    def start(self):
        """
        Start handling pygame events 
        
        Called by the OSD module after the display is created.
        """
        if self.thread is None:
            self.thread = threading.Thread(target=self.process_events)
            self.thread.setDaemon(True)
            self.thread.start()

    
    def stop(self):
        """ 
        Stop handling pygame events.
        
        Called by the OSD module before the display is destroyed.
        """
        if self.thread:
            pygame.event.post(pygame.event.Event(pygame.locals.USEREVENT, 
                                {'action': 'quit'}))
            print 'Waiting for event thread'
            self.thread.join()
            self.thread = None

    
    def register_handler(self, event_type, handler):
        """ 
        Register a callable to be called when a specific type of event is 
        received. 
        """
        self.handlers[event_type] = handler
        if self.thread:
            pygame.event.post(pygame.event.Event(pygame.locals.USEREVENT, 
                                {'action': 'enable_event', 'event_type': event_type}))


    def unregister_handler(self, event_type, handler):
        """ Unregister to stop recieving events of the specified type """
        if event_type in self.handlers and self.handlers[event_type] == handler:
            del self.handlers[event_type]
            if self.thread:
                pygame.event.post(pygame.event.Event(pygame.locals.USEREVENT, 
                                {'action': 'disable_event', 'event_type': event_type}))


    def process_events(self):
        """ Internal function to process the pygame events"""
        # Disable all events initially
        pygame.event.set_allowed(None)
        
        # Now enable only those we want
        pygame.event.set_allowed(pygame.locals.USEREVENT)
        pygame.event.set_allowed(self.handlers.keys())
        
        while True:
            evt = pygame.event.wait()
            
            if evt.type == pygame.locals.USEREVENT:
                if evt.action == 'quit':
                    break
                
                elif evt.action == 'enable_event':
                    pygame.event.set_allowed(evt.event_type)

                elif evt.action == 'disable_event':
                    pygame.event.set_blocked(evt.event_type)

            elif evt.type in self.handlers:
                try:
                    self.handlers[evt.type](evt)
                except:
                    traceback.print_exc()
