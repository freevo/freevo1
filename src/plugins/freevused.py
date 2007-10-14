# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# freevused.py - Get events from a Bemused like client
# -----------------------------------------------------------------------
# $Id$
#
# Notes: This is a plugin to remote control Freevo with a bluetooth mobile
#        phone using a j2me client running in the phone.
#
# Activate:
#
#---------------------------------------------------- /etc/freevo/local.conf
#
# plugin.activate('freevused')
#
# if RFCOMM port is already binded wait this seconds to retry binding
#
# FVUSED_BIND_TIMEOUT = 30
#
# Send received event to OSD
#
# FVUSED_OSD_MESSAGE = True
#
# Translation of commands from j2me client to events of Freevo
#
#   FVUSED_CMDS = {
#
#     'PREV': 'UP',                # 1st row left
#     'STRT': 'SELECT',            # 1nd row center
#     'NEXT': 'DOWN',              # 1st row right
#     'RWND': 'LEFT',              # 2nd row left
#     'PAUS': 'PAUSE',             # 2nd row center
#     'FFWD': 'RIGHT',             # 2nd row right
#     'VOL-': 'MIXER_VOLDOWN',     # 3rd row left
#     'STOP': 'EXIT',              # 3rd row center
#     'VOL+': 'MIXER_VOLUP',       # 3rd row right
#     'VOLM': 'MIXER_MUTE',        # 4th row left
#     'SLCT': 'ENTER',             # 4th row center
#     'MAIN': 'STOP',              # 4th row right

#     'DISP': 'DISPLAY',           # More actions
#     'EJEC': 'EJECT',
#     'DEAU': 'DISPLAY',
#     'CHA+': 'CH+',
#     'CHA-': 'CH-',
#     'RECO': 'REC',
#     'GUID': 'GUIDE',
#     'NUM0': '0',                 # Numeric keyboard
#     'NUM1': '1',
#     'NUM2': '2',
#     'NUM3': '3',
#     'NUM4': '4',
#     'NUM5': '5',
#     'NUM6': '6',
#     'NUM7': '7',
#     'NUM8': '8',
#     'NUM9': '9',
#
#     'STAT': 'FVUSED_ITEM_INFO'
#   }
#
#---------------------------------------------------- /etc/freevo/local.conf
#
# Changelog
#
# 1.5
#
# - Added i18n to the midlet
# - Added information of the current playing element
# - Modified debug info levels
#
# 1.4
#
# - Added menu browsing in the phone screen
#
# 1.3
#
# - Cosmetic improvements
# - Send posted event message to OSD
# - Added more Freevo events to the j2me client. It supports now a
#   numeric keyboard and display, eject, guide, rec and channel up and down.
#
# 1.2
#
# - Stop advertising only if it's binded. It seems that pyBluez changed its
#   behavior and now raises an error if calling stop_advertising when it's
#   not advertising.
# - Chris Lombardi reported that the newer phones require to set rfcomm
#   sockets to be advertised as a serial port class using the serial port
#   profile.
# - The rfcomm socket it is not hardcoded now.
#
# 1.1
#
# - Added support for entering TEXT event from client
# - Added support for volume mixer events
# - Remove polling. Now process_data is made in the bluetooth thread
#
# 1.0
#
# Initial release
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
# with self program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------

import config
import plugin
import rc
import event as em
import menu
import audio.audioitem as aitem
import video.videoitem as vitem

import audio.player as player


import plugin

try:
    import bluetooth
except:
    print String(_("ERROR")+": "+_("You need pybluez (http://org.csail.mit.edu/pybluez/) to run \"freevused\" plugin."))

import thread, time

class PluginInterface(plugin.DaemonPlugin):
    """
    Remote control Freevo with a bluetooth mobile phone.

    To activate add this to your local_conf.py:

    plugin.activate('freevused')

    Optionally you could set those variables if you don't like the default
    ones

    ------------------------------------------------ /etc/freevo/local.conf

    # if RFCOMM port is already binded wait this seconds to retry binding
    FVUSED_BIND_TIMEOUT = 30

    # Send received event to OSD
    FVUSED_OSD_MESSAGE = True

    #Translation of commands from j2me client to events of Freevo
    #
    FVUSED_CMDS = {

      'PREV': 'UP',                # 1st row left
      'STRT': 'SELECT',            # 1nd row center
      'NEXT': 'DOWN',              # 1st row right
      'RWND': 'LEFT',              # 2nd row left
      'PAUS': 'PAUSE',             # 2nd row center
      'FFWD': 'RIGHT',             # 2nd row right
      'VOL-': 'MIXER_VOLDOWN',     # 3rd row left
      'STOP': 'EXIT',              # 3rd row center
      'VOL+': 'MIXER_VOLUP',       # 3rd row right
      'VOLM': 'MIXER_MUTE',        # 4th row left
      'SLCT': 'ENTER',             # 4th row center
      'MAIN': 'STOP',              # 4th row right

      'DISP': 'DISPLAY',           # More actions
      'EJEC': 'EJECT',
      'DEAU': 'DISPLAY',
      'CHA+': 'CH+',
      'CHA-': 'CH-',
      'RECO': 'REC',
      'GUID': 'GUIDE',
      'NUM0': '0',                 # Numeric keyboard
      'NUM1': '1',
      'NUM2': '2',
      'NUM3': '3',
      'NUM4': '4',
      'NUM5': '5',
      'NUM6': '6',
      'NUM7': '7',
      'NUM8': '8',
      'NUM9': '9',

      'STAT': 'FVUSED_ITEM_INFO'
    }
    ------------------------------------------------ /etc/freevo/local.conf

    """

    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'freevused'

        self.event_listener = True

        self.isbinded    = False
        self.isconnected = False
        self.server_sock = None
        self.client_sock = None
        self.address     = 0
        self.port        = 0
        self.data        = ''
        self.osd_message_status = None
        self.menuw       = None

        self.menu_isfresh = False
        self.menu_client_waiting = False
        self.playing = False

        self.audioplayer = None

        if hasattr(config, 'FVUSED_BIND_TIMEOUT'):
            self.bind_timeout = config.FVUSED_BIND_TIMEOUT
        else:
            self.bind_timeout = 30

        if hasattr(config, 'FVUSED_OSD_MESSAGE'):
            self.osd_message = config.FVUSED_OSD_MESSAGE
        else:
            self.osd_message = False

        if hasattr(config, 'FVUSED_CMDS'):
            self.cmds = config.FVUSED_CMDS
        else:
            self.cmds = {

                  'PREV': 'UP',                # 1st row left
                  'STRT': 'SELECT',            # 1nd row center
                  'NEXT': 'DOWN',              # 1st row right
                  'RWND': 'LEFT',              # 2nd row left
                  'PAUS': 'PAUSE',             # 2nd row center
                  'FFWD': 'RIGHT',             # 2nd row right
                  'VOL-': 'MIXER_VOLDOWN',     # 3rd row left
                  'STOP': 'EXIT',              # 3rd row center
                  'VOL+': 'MIXER_VOLUP',       # 3rd row right
                  'VOLM': 'MIXER_MUTE',        # 4th row left
                  'SLCT': 'ENTER',             # 4th row center
                  'MAIN': 'STOP',              # 4th row right

                  'DISP': 'DISPLAY',           # More actions
                  'EJEC': 'EJECT',
                  'DEAU': 'DISPLAY',
                  'CHA+': 'CH+',
                  'CHA-': 'CH-',
                  'RECO': 'REC',
                  'GUID': 'GUIDE',
                  'NUM0': '0',                 # Numeric keyboard
                  'NUM1': '1',
                  'NUM2': '2',
                  'NUM3': '3',
                  'NUM4': '4',
                  'NUM5': '5',
                  'NUM6': '6',
                  'NUM7': '7',
                  'NUM8': '8',
                  'NUM9': '9',

                  'STAT': 'FVUSED_ITEM_INFO'
        }

        self.poll_menu_only = False

        self.rc = rc.get_singleton()

        self.FVUSED_ITEM_INFO = em.Event('FVUSED_ITEM_INFO')

        self.mixer_default_step = config.VOLUME_MIXER_STEP

        thread.start_new_thread(self.bluetoothListener, ())

    def poll(self):
        if self.menu_client_waiting:
            if self.playing:
                if self.menuw:
                    menupage = self.menuw.menustack[-1]
                    if hasattr(menupage, 'is_submenu') and menupage.is_submenu:
                        menuitem = self.menuw.menustack[-2].selected
                        self.sendMessage(_('Playing') + ' %s' % menuitem.name)
                    else:
                        menuitem = menupage.selected
                        self.sendMessage(_('Playing') + ' %s' % menuitem.name)

                    self.menu_client_waiting = False
            else:
                self.sendMenu()
                self.menu_client_waiting = False
            self.menu_isfresh = False

    def eventhandler(self, event, menuw=None):
        _debug_("Saw event %s menuw %s" % (event, menuw) )

        if menuw and isinstance(menuw, menu.MenuWidget):

            if event == em.MENU_PROCESS_END:
                self.menuw = menuw
                self.menu_isfresh = True

        else:
            if event == em.VIDEO_START:
                self.osd_message_status = self.osd_message
                self.osd_message = False
                self.playing = True
                self.menu_isfresh = True

            elif event == em.VIDEO_END:
                self.osd_message = self.osd_message_status
                self.playing = False

            elif event == em.PLAY_START:
                self.playing = True
                self.menu_isfresh = True

            elif event == em.PLAY_END:
                self.playing = False

            elif event == em.STOP:
                self.playing = False

            elif event == self.FVUSED_ITEM_INFO:
                self.sendItemStats()
                return True

        return False

    def shutdown(self):
        if self.server_sock:
            if not self.isbinded:
                bluetooth.stop_advertising(self.server_sock)
            self.server_sock.close()

        if self.client_sock:
            self.client_sock.close()


    def advertise_service(self):
        # Create the sever socket
        self.server_sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )

        # bind the socket to the first available port
        self.port = bluetooth.get_available_port( bluetooth.RFCOMM )
        try:
            err = self.server_sock.bind(("", self.port))
            err = self.server_sock.listen(1)

            # advertise our service
            bluetooth.advertise_service( self.server_sock, "Freevused",
                                  service_classes = [ bluetooth.SERIAL_PORT_CLASS ],
                                  profiles = [ bluetooth.SERIAL_PORT_PROFILE ] )

            self.isbinded = True
            _debug_("Advertising server to the world")

        except bluetooth.BluetoothError, e:
            self.isbinded = False
            _debug_("broken tooth: %s" % str(e))
            time.sleep(self.bind_timeout)


    def process_data(self):
        str_arg = ''
        command = None

        _debug_("Data received: %s" % str(self.data), 2)
        str_cmd = self.data[:4]
        if str_cmd in ('VOL-', 'VOL+', 'VOLM', 'MAIN', 'STAT'):
            command = self.cmds.get(str_cmd, '')
            if command:
                _debug_('Event Translation: "%s" -> "%s"' % (str_cmd, command))
                if str_cmd in ('VOL-', 'VOL+'):
                    self.rc.post_event(em.Event(command, arg=self.mixer_default_step))
                else:
                    self.rc.post_event(em.Event(command))

        elif str_cmd == 'TEXT':
            str_arg = self.data[4:]
            for letter in str_arg:
                command = self.rc.key_event_mapper(letter)
                if command:
                    _debug_('Event with arg Translation: "%s" -> "%s %s"' % (self.data, command, letter))
                    self.rc.post_event(command)

        elif str_cmd == 'MSND':
            self.menu_client_waiting = True

        elif str_cmd == 'MITM':
            str_arg = self.data[4:]
            try:
                pos = int(str_arg)

                menu = self.menuw.menustack[-1]
                max  = len(menu.choices)
                if pos < max:
                    menu.selected = menu.choices[pos]
                    self.rc.post_event(em.MENU_SELECT)
                else:
                    _debug_('Menu index too high!: %s (max=%s)' % (pos, max-1))

            except ValueError:
                _debug_('Menu index sent: %s' % str_arg)
                pass

        else:
            command = self.rc.key_event_mapper(self.cmds.get(self.data, ''))
            if command:
                _debug_('Event Translation: "%s" -> "%s"' % (self.data, command))
                self.rc.post_event(command)

        if command and self.osd_message:
            _debug_('OSD Event: "%s"' % (command))
            rc.post_event(em.Event(em.OSD_MESSAGE, arg=_('BT event %s' % command)))

        self.data=''


    def bluetoothListener(self):

        while True:

            # accept an incoming connection
            if not self.isbinded:
                self.advertise_service()
            elif not self.isconnected:
                _debug_("Waiting for connection on RFCOMM channel %d" % self.port)
                try:
                    self.client_sock, self.address = self.server_sock.accept()
                except bluetooth.BluetoothError, e:
                    _debug_("broken tooth: %s" % str(e))

                self.isconnected = True
                _debug_("Accepted connection from ", self.address)

            else:
            # get data from socket

                try:
                    self.data = self.client_sock.recv(1024)
                except bluetooth.BluetoothError, e:
                    self.isconnected = False
                    _debug_("broken tooth: %s" % str(e))
                self.process_data()


    def btSend(self, data=None):
        try:
            if self.client_sock and data:
                bytes = self.client_sock.send(data)
                if data == '\0':
                    _debug_("Data sent: EOS", 2)
                else:
                    _debug_("Data sent: %s" % data, 2)

                _debug_("Bytes sent: %s" % bytes, 2)

        except bluetooth.BluetoothError, e:
            self.isconnected = False
            _debug_("broken tooth: %s" % str(e))


    def sendMenu(self):
        if self.menuw:
            menu = self.menuw.menustack[-1]
            for item in menu.choices:
                self.btSend(item.name + '\n')

        self.btSend('\0')

    def sendItemStats(self):
        print "PLAYING: %s" % self.playing
        print "MENU: %s" % self.menuw
        if self.playing and self.menuw:
            menuitem = self.menuw.menustack[-1]
            if hasattr(menuitem, 'is_submenu') and menuitem.is_submenu:
                menuitem = self.menuw.menustack[-2].selected
            else:
                menuitem = self.menuw.menustack[-1].selected

            if isinstance(menuitem, aitem.AudioItem):

                self.audioplayer = player.get()
                if self.audioplayer:
                    item = self.audioplayer.item
                    if item and isinstance(item, aitem.AudioItem):
                        self.sendAudioItemStats(item)

            elif isinstance(menuitem, vitem.VideoItem):

                self.sendVideoItemStats(menuitem)

        self.btSend('\0')

    def sendAudioItemStats(self, item):

        info = item.info

        if hasattr(item, 'name') and item['name']:
            self.btSend(item['name'] + '\n')

        if info.has_key('stream_name') and info['stream_name']:
            self.btSend(_('Name') + ': ' + info['stream_name'] + '\n')

        if info.has_key('album') and info['album']:
            self.btSend(_('Album') + ': ' + info['album'] + '\n')

        if info.has_key('artist') and info['artist']:
            self.btSend(_('Artist') + ': ' + info['artist'] + '\n')

        if info.has_key('genre') and info['genre']:
            self.btSend(_('Genre') + ': ' + info['genre'] + '\n')

        if info.has_key('trackno') and info['trackno']:
            self.btSend(_('Track') + ': %s' % info['trackno'])

            if info.has_key('trackof') and info['trackof']:
                self.btSend('/%s\n' % info['trackof'])
            else:
                self.btSend('\n')

        if info.has_key('bitrate') and info['bitrate']:
            self.btSend(_('Bitrate') + ': %s\n' % info['bitrate'])

        if hasattr(item, 'length') and item['length']:
            self.btSend(_('Length') + ': %s\n' % item['length'])

    def sendVideoItemStats(self, item):

        if hasattr(item, 'name') and item['name']:
            self.btSend(item['name'] + '\n')

        if item['geometry']:
            self.btSend(_('Geometry') + ': ' + item['geometry'])

            if item['aspect']:
                self.btSend(' (' + item['aspect'] + ')\n')
            else:
                self.btSend('\n')

        if item['runtime']:
            self.btSend(_('Length') + ': ' + item['runtime'] + '\n')

    def sendMessage(self, msg):
        self.btSend(msg + '\n\0')
