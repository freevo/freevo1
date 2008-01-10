# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# A Wiimote interface
# -----------------------------------------------------------------------
# $Id$
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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

# bluetooth imports
import bluetooth

# kaa imports
import kaa.notifier

import time

#import sys
#import os
#import select
#import struct
#import traceback

import config
import plugin
import rc

rc = rc.get_singleton()


CMD_SET_REPORT = 0x52

RID_LEDS = 0x11
RID_MODE = 0x12

MODE_BASIC = 0x30
MODE_ACC = 0x31

LED1_ON = 0x10
LED2_ON = 0x20
LED3_ON = 0x40
LED4_ON = 0x80


buttonmap = {
    '2': 0x0001,
    '1': 0x0002,
    'B': 0x0004,
    'A': 0x0008,
    'MINUS': 0x0010,
    'HOME': 0x0080,
    'LEFT': 0x0100,
    'RIGHT': 0x0200,
    'DOWN': 0x0400,
    'UP': 0x0800,
    'PLUS': 0x1000,
}

buttonpress = {
    '2': 0,
    '1': 0,
    'B': 0,
    'A': 0,
    'MINUS': 0,
    'HOME': 0,
    'LEFT': 0,
    'RIGHT': 0,
    'DOWN': 0,
    'UP': 0,
    'PLUS': 0,
}

movetimes = {
    'RIGHT' : 0,
    'LEFT' : 0,
    'DOWN' : 0,
    'UP' : 0,
}


class PluginInterface(plugin.DaemonPlugin):
    """
    Use the wiimote as an input plugin:

    | # The Bluetooth device address of the wiimote. Use "hcitool scan"
    | # to find out.
    | # Default: 00:00:00:00:00:00
    | WII_ADDRESS = "00:00:00:00:00:00"
    |
    | # wiimote button mappings
    | WII_CMDS = {
    |     'UP' : 'UP',
    |     'DOWN' : 'DOWN',
    |     'B' : 'SELECT',
    |     'A' : 'EXIT',
    |     'LEFT' : 'LEFT',
    |     'RIGHT' : 'RIGHT',
    |     'PLUS' : 'VOL+',
    |     'MINUS' : 'VOL-',
    |     '1' : 'DISPLAY',
    |     '2' : 'MENU',
    |     'HOME' : 'PLAY'
    | }
    |
    | # This option activates the acceleration mode. It ist possible to
    | # raise LEFT, RIGHT, UP and DOWN events just by turning the
    | # wiimote in the right direction.
    | WII_ACC_ACTIVATE = True
    |
    | # This button enables the acceleration mode. If the button is pressed
    | # and hold longer than acc_button_time than the mode is enabled.
    | # Otherwise the button has the normal action.
    | WII_ACC_BUTTON = "A"
    |
    | # This is the time in seconds after that the acceleration mode after
    | # pressing the acc_button will be enabled.
    | WII_ACC_BUTTON_TIME = 0.3
    |
    | # This is the time in seconds after that the RIGHT and LEFT event
    | # is fired again.
    | WII_ACC_RL_REPEAT = 0.4
    |
    | # This is the time in seconds after that the UP and DOWN event
    | # is fired again.
    | WII_ACC_UD_REPEAT = 0.2

    So these options can be overwritten in the local_conf.py file. I'm using
    debian and needed the following deb-packages:
        - libbluetooth2
        - python-bluez
        - bluez-utils
    """

    timer               = None
    rx                  = None
    cx                  = None
    rx_dispatcher       = None
    buttonmask          = 0

    active      = False
    connected   = False

    acc           = [0, 0, 0]
    acc_ref       = [0, 0, 0]
    acc_timer    = None

    KEYMAP = {}

    def __init__(self):

        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'WIIMOTE'

        self.bdaddr          = config.WII_ADDRESS
        self.acc_activate    = config.WII_ACC_ACTIVATE
        self.acc_rl_repeat   = config.WII_ACC_RL_REPEAT
        self.acc_ud_repeat   = config.WII_ACC_UD_REPEAT
        self.acc_button      = config.WII_ACC_BUTTON
        self.acc_button_time = config.WII_ACC_BUTTON_TIME

        for mapping in config.WII_CMDS:
            self.KEYMAP[mapping] = config.WII_CMDS.get(mapping, '')

        self.rx = bluetooth.BluetoothSocket( bluetooth.L2CAP )
        self.cx = bluetooth.BluetoothSocket( bluetooth.L2CAP )

        self.cx.settimeout(2)
        self.rx.settimeout(2)

        self.rx_dispatcher = kaa.notifier.SocketDispatcher(self.handle_receive)

        # start immediately for the first time
        self.timer = kaa.notifier.Timer(self.onTimer)
        self.timer.start(0.1)

        self.acc_timer = kaa.notifier.Timer(self.on_acc_timer)

        self.active = True


    def onTimer(self):
        self.timer.stop()

        if not self.connected:
            self.tryConnect()

        self.timer.start(5)


    def config(self):
        return [
            ('WII_ADDRESS', '00:00:00:00:00:00', 'The Bluetooth device address of the wiimote. Use "hcitool scan"'),
            ('WII_CMDS',
                '{ "UP" : "UP", "DOWN" : "DOWN", "B" : "SELECT", "A" : "EXIT", "LEFT" : "LEFT", "RIGHT": "RIGHT",'+
                ' "PLUS" : "VOL+", "MINUS": "VOL-", "1" : "DISPLAY", "2" : "MENU", "HOME" : "PLAY" }',
                'wiimote button mappings'),
            ('WII_ADDRESS', '00:00:00:00:00:00', 'The Bluetooth device address of the wiimote. Use "hcitool scan"'),
            ('WII_ACC_ACTIVATE', 'True', 'This option activates the acceleration mode'),
            ('WII_ACC_BUTTON', 'A', 'This button enables the acceleration mode'),
            ('WII_ACC_BUTTON_TIME', '0.3', 'This is the time in seconds after that the acceleration mode'),
            ('WII_ACC_RL_REPEAT', '0.4', 'This is the time in seconds after that the RIGHT and LEFT event is repeated'),
        ]


    def post(self, key):
        #print self.KEYMAP[key]
        command = rc.key_event_mapper(self.KEYMAP[key])
        rc.post_event(command)


    def on_acc_timer(self):
        """
        This timer handles the acceleration data if activated. First it
        calculates the differenc of the x and y values to the ref values.
        The ref values are evaluated, when the acceleration mode is
        enabled by the acc_button. Only the axis with the max value is
        considered. The events are only fired after the repeat time.
        """
        self.acc_timer.stop()

        diff_x = self.acc[0] - self.acc_ref[0];
        diff_y = self.acc[1] - self.acc_ref[1];

        if (abs(diff_x) > abs(diff_y)):
            # right / left movement
            if (abs(diff_x) > 10):

                if (diff_x > 0):
                    key = "RIGHT"
                else:
                    key = "LEFT"

                if (time.time()-movetimes[key]) > self.acc_rl_repeat:
                    self.post(key)
                    movetimes[key] = time.time()

        else:
            # up / down movement
            if (abs(diff_y) > 3):

                if (diff_y > 0):
                    key = "DOWN"
                else:
                    key = "UP"

                if (time.time()-movetimes[key]) > self.acc_ud_repeat:
                    self.post(key)
                    movetimes[key] = time.time()

        self.acc_timer.start(0.05)


    def handle_receive(self):
        try:

            data = self.rx.recv(1024)
            if len(data) == 4:
                self.handle_button(data)
            elif len(data) == 7:
                self.handle_button(data[0:4])
                self.handle_acc(data[4:7])

        except bluetooth.BluetoothError:
            self.disconnect()


    def handle_key(self, key, pressed):
        """
        If a key is pressed than the time for each button is stored. This
        is needed at this point only for tha acc_button. If it is the
        acc_button the timer for the acceleration handling is enabled.

        If a key is released the button event is fired. The acc_button event
        is only fired when the acceleration mode is not enabled.
        """
        if (pressed):
            buttonpress[key] = time.time()

            if (key == self.acc_button) & (self.acc_activate):
                #save acc state
                self.acc_ref = self.acc
                self.acc_timer.start(self.acc_button_time)

        if (not pressed):
            if (key == self.acc_button) & (self.acc_activate):

                if ((time.time()-buttonpress[key]) < self.acc_button_time):
                    self.post(key)

                self.acc_timer.stop()

            else:
                self.post(key)


    def handle_button(self, data):
        newmask = ( ord(data[2]) << 8 ) + ( ord(data[3]) )

        for key, code in buttonmap.items():
            if ( (newmask ^ self.buttonmask) & code ):
                if ( (newmask & code) == code):
                    self.handle_key(key, True)
                if ( (newmask & code) == 0 ):
                    self.handle_key(key, False)

        self.buttonmask = newmask;


    def handle_acc(self, data):
        self.acc = [ord(d) for d in data]


    def shutdown(self):
        """
        on exit just disconnect from the wiimote and stop the timers
        """
        if self.active:
            print "wii: stop"
            self.active = False
            self.acc_timer.stop()
            self.disconnect()
            self.timer.stop()


    def tryConnect(self):
        self.disconnect()

        try:
            self.rx.connect((self.bdaddr, 19))
            self.cx.connect((self.bdaddr, 17))

        except bluetooth.BluetoothError:

            self.cx.close()
            self.rx.close()

            self.cx = None
            self.rx = None

            self.rx = bluetooth.BluetoothSocket( bluetooth.L2CAP )
            self.cx = bluetooth.BluetoothSocket( bluetooth.L2CAP )

            self.rx.settimeout(2)
            self.cx.settimeout(2)

            return False

        self.rx.setblocking(False)

        self.setled(0)
        time.sleep(0.8)
        self.setled(LED1_ON | LED4_ON)

        self.connected = True

        self.setmode(MODE_ACC | MODE_BASIC);

        self.rx_dispatcher.register(self.rx.fileno())


    def setled(self, mask):
        """
        set the led on the wiimote
        """
        self.send_command(CMD_SET_REPORT, RID_LEDS, [mask])


    def send_command(self, command, report, data):
        """
        send the command to the wiimote
        """
        self.cx.send(chr(command) + chr(report) + "".join([chr(d) for d in data]))


    def setmode(self, mode):
        self.send_command(CMD_SET_REPORT, RID_MODE, [0, mode]);


    def disconnect(self):
        """
        if connected to the wiimote unregister the the bluetooth-receive-socket
        and close the sockets
        """
        if self.connected:
            self.cx.close()
            self.rx.close()
            self.rx_dispatcher.unregister()
            self.connected = False
