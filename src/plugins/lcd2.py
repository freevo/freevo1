# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# lcd2.py - use PyLCD to display menus and players on a display
# -----------------------------------------------------------------------
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('lcd2')
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

import config
import plugin
from event import *
from menu import MenuItem
from time import strftime

try:
    import pylcd
except:
    _debug_(_('You need pylcd to run "lcd2x16" plugin.'), DERROR)

class LcdFrame(object):
    def __init__(self, lcd, name, col, start, end):
        """
        Class to provide LCD-frames with priorities and timers.
        """
        self.lcd = lcd
        self.name = name
        self.width = end-start+1
        self.text = ''
        self.prio = 0
        self.timer = 0

        lcd.widget_add('s','f_'+name,'frame')
        lcd.widget_set('s','f_'+name,'%d %d %d %d %d 1 h 0' % (start, col, end, col, self.width))
        lcd.widget_add('s','w_'+name,'string -in f_'+name)

    def draw(self, text, prio=0, timer=0):
        if (prio >= self.prio) or (self.timer == 0):
            self.prio = prio
            self.timer = timer
            if (text != self.text):
                self.lcd.widget_set('s','w_'+self.name,'1 1 "%s"' % text.encode('latin1'))
                self.text = text

    def draw_right(self, text, prio=0, timer=0):
        spaces = self.width-len(text)
        self.draw((' '*spaces)+text, prio, timer)

    def timertick(self):
        if self.timer > 0: self.timer -= 1


class PluginInterface(plugin.DaemonPlugin):
    """
    This plugin is a customized version of lcd.py, which fits not well for 2x16 lcds.

    @requires: lcdproc installed and LCDd running. U{http://lcdproc.sourceforge.net/}
    @requires: pylcd installed U{http://www.schwarzvogel.de/software-pylcd.shtml}

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    | plugin.activate('lcd2x16')
    """
    __author__           = 'Andreas Dick'
    __author_email__     = 'andudi@gmx.ch'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'

    def __init__(self):
        """
        Init the lcd screen and this plugin
        """
        plugin.DaemonPlugin.__init__(self)

        self.poll_interval = 20         # timer resolution is 200ms
        self.poll_menu_only = 0         # lcd even if player is on
        self.event_listener = 1         # listening to events

        self.menu_pos = (0, 1)          # to detect menu position changes

        # use pylcd to connect to LCDd
        try:
            self.lcd = pylcd.client()
            self.lcd.connect()
            self.lcd.screen_add('s')
            self.lcd.screen_set('s', '-priority foreground -heartbeat off')
        except:
            _debug_(_('LCD plugin will not load! Maybe you don\'t have LCDd (lcdproc daemon) running?'), DERROR)
            return

        # prepare the lcd frames for different types
        info_width = 7
        width = self.lcd.d_width
        height = self.lcd.d_height

        # menu, title and player lines (could be configured in local_conf.py?)
        self.lcd_head = LcdFrame(self.lcd, 'head', col=1, start=1, end=(width-info_width-1))
        self.lcd_info = LcdFrame(self.lcd, 'info', col=1, start=(width-info_width+1), end=width)
        self.lcd_menu_sel = LcdFrame(self.lcd, 'msel', col=2, start=1, end=width)
        if height == 2:
            self.lcd_menu_add = [] # no additional menue lines
            self.lcd_title = self.lcd_menu_sel # use bottom line, share with menu selection
            self.lcd_player = self.lcd_menu_sel # use bottom line, share with menu selecton
        elif height == 3:
            self.lcd_menu_add = [LcdFrame(self.lcd, 'madd0', col=3, start=1, end=width)]
            self.lcd_title = self.lcd_menu_sel # use middle line for titles, share with menu selection
            self.lcd_player = self.lcd_menu_add[0] # use last line for player info
        elif height == 4:
            self.lcd_menu_add = [LcdFrame(self.lcd, 'madd0', col=3, start=1, end=width),
                                 LcdFrame(self.lcd, 'madd1', col=4, start=1, end=width)]
            self.lcd_title = self.lcd_menu_add[0] # use third line for titles, share with additional menu line
            self.lcd_player = self.lcd_menu_add[1] # use last line for player, share with additional menu line
        else:
            _debug_(_('LCD not supported yet!'), DERROR)

        # updating menu head
        self.lcd_head.draw('Freevo')

        # register this pluing
        plugin.register(self, 'lcd2')


    def menu_clear(self):
        """
        clear the lcd menu lines when starting player
        """
        if self.menu_pos != (0, 0):
            self.lcd_menu_sel.draw('')
            for lcd_menu_add in self.lcd_menu_add:
                lcd_menu_add.draw('')
            self.menu_pos = (0, 0)


    def draw(self, (type, object), osd):
        """
        called from plugin.py at redraw
        """
        if type == 'menu':
            # prepare menu header, try to find out types in menustack
            # (this could be improved with more general infos in the player items)
            level = len(object.menustack)-1
            if level == 0:
                head = 'Freevo'
            elif object.menustack[0].selected.arg[0] == 'audio':
                if level == 1:
                    head = 'Musik'
                elif object.menustack[1].selected.info.disc:
                    head = 'Audio-CD'
                elif object.menustack[1].selected.name.split()[0] == 'USB':
                    head = 'USB'
                elif object.menustack[1].selected.type == 'dir':
                    head = 'MP3'
                elif object.menustack[1].selected.type == 'webradio':
                    head = 'Radio'
            elif object.menustack[0].selected.arg[0] == 'image':
                if level == 1:
                    head = 'Images'
                elif object.menustack[1].selected.info.disc:
                    head = 'Foto-CD'
                elif object.menustack[1].selected.name.split()[0] == 'USB':
                    head = 'USB'
                elif object.menustack[1].selected.type == 'dir':
                    head = 'Fotos'
            elif object.menustack[0].selected.arg[0] == 'video': # not yet well supported
                if level == 1:
                    head = 'Videos'
                elif object.menustack[1].selected.info.disc:
                    head = 'DVD/VCD'
                elif object.menustack[1].selected.name.split()[0] == 'USB':
                    head = 'USB'
                elif object.menustack[1].selected.type == 'dir':
                    head = 'Videos'
            # update menu header
            try:    self.lcd_head.draw(head)
            except: self.lcd_head.draw('NONE')

            # prepare index position and update selected menu item
            items = len(object.menu_items)
            if items:
                selection = object.menustack[-1].selected
                index = object.menustack[-1].choices.index(selection) + 1
                self.lcd_menu_sel.draw(selection.name)
            else:
                index = 0
                self.lcd_menu_sel.draw('Zurück')

            # update info frames with menu position
            if (level, index) != self.menu_pos:
                self.menu_pos = (level, index)
                info = '%d/%d' % (index, items)
                self.lcd_info.draw_right(info, 5, 8)

            # update additional menu lines
            for lcd_menu_add in self.lcd_menu_add:
                try:    line = object.menustack[-1].choices[index].name
                except: line = ''
                lcd_menu_add.draw(line)
                index += 1

        elif type == 'player':
            # clear menu lines before playing
            self.menu_clear()

            player = object
            if player.type == 'audio':
                # prepare player infos
                title = player.name
                trackno = player.getattr('trackno')
                time = player.elapsed
                length = player.length

                if length:
                    # audio like MP3 and CD-ROM
                    if (self.lcd_title == self.lcd_player): # if lines are shared
                        if (time < 3) or ((time % 10) < 2):
                            self.lcd_title.draw('%s %s' % (trackno, title))
                        else:
                            self.lcd_player.draw_right('%d:%02d/%d:%02d' % (time//60, time%60, length//60, length%60))
                    else:
                        self.lcd_title.draw('%s %s' % (trackno, title))
                        self.lcd_player.draw_right('%d:%02d/%d:%02d' % (time//60, time%60, length//60, length%60))
                else:
                    # audio streams like Radio
                    if time > 0: self.lcd_title.draw(title)
                    else:        self.lcd_title.draw('...')

#            elif player.type == 'video':
                # not yet!



    def poll(self):
        """
        plugin polling, period is 200ms
        """
        # update info timer and the clock at a low prio
        self.lcd_info.timertick()
        self.lcd_info.draw_right(strftime('%H:%M'), 1, 5)


    def eventhandler(self, event, menuw=None):
        """
        called from plugin.py if an event occure
        -> to be done: define events in event.py
        """
        # show player infos while playing
        if event == VIDEO_START:
            self.menu_clear()
            self.lcd_head.draw('DVD/SVCD')
        elif event == 'VIDEO_PLAY_INFO':
            (elapsed, length) = event.arg
            self.lcd_player.draw_right('%d:%02d/%d:%02d' % (elapsed//60, elapsed%60, length//60, length%60))

        # show volume in info area, grab it afer MIXER message from the OSD message
        if event == 'MIXER_VOLUME_INFO':
            self.lcd_info.draw('VOL%3s%%' % event.arg, 5, 12)
        elif event == 'MIXER_MUTE_INFO':
            self.lcd_info.draw('MUTED', 5, 12)

        # show image view, play, pause and duration
        elif event == 'IMAGE_VIEW_INFO':
            self.menu_clear()
            if (self.lcd_title == self.lcd_player):
                self.lcd_title.draw('%s/%s %s' % event.arg)
            else:
                self.lcd_title.draw(event.arg[2])
                self.lcd_player.draw_right('%s/%s' % (event.arg[0], event.arg[1]))
        elif event == 'IMAGE_PLAY_INFO':
            self.lcd_info.draw('TIME%2ss' % event.arg, 5, 12)
        elif event == 'IMAGE_PAUSE_INFO':
            self.lcd_info.draw('PAUSE', 5, 12)

        # show LIRC status in the info area (lirc button that changes the meaning of the iMON button)
        elif event.arg == 'LIRC_MODE_VOLUME':
            self.lcd_info.draw('VOLUME', 5, 12)
        elif event.arg == 'LIRC_MODE_MENU':
            self.lcd_info.draw('MENU', 5, 12)
        elif event.arg == 'LIRC_MODE_PLAYER':
            self.lcd_info.draw('PLAYER', 5, 12)

        return 0
