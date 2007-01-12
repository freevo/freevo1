# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# buttonbar.py-ButtonBar plugin
# -----------------------------------------------------------------------
# $Id:$
#
# -----------------------------------------------------------------------
# Freevo-A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the Licestringnse, or
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

# python modules
import time
import os
import locale

# freevo modules
import config
import plugin
import skin
import osd
import event

from tv.tvguide import TVGuide
from menu import MenuItem, Menu
from pygame import image,transform, Surface

# Create the OSD object
OSD = osd.get_singleton()

# Create the events and assign them to the menus.
BUTTONBAR_RED    = event.Event('BUTTONBAR_RED')
BUTTONBAR_GREEN  = event.Event('BUTTONBAR_GREEN')
BUTTONBAR_YELLOW = event.Event('BUTTONBAR_YELLOW')
BUTTONBAR_BLUE   = event.Event('BUTTONBAR_BLUE')

event.MENU_EVENTS['RED']    = BUTTONBAR_RED
event.MENU_EVENTS['GREEN']  = BUTTONBAR_GREEN
event.MENU_EVENTS['YELLOW'] = BUTTONBAR_YELLOW
event.MENU_EVENTS['BLUE']   = BUTTONBAR_BLUE

event.TVMENU_EVENTS['RED']    = BUTTONBAR_RED
event.TVMENU_EVENTS['GREEN']  = BUTTONBAR_GREEN
event.TVMENU_EVENTS['YELLOW'] = BUTTONBAR_YELLOW
event.TVMENU_EVENTS['BLUE']   = BUTTONBAR_BLUE

def advance_tv_guide(arg=0, menuw=None):
    """
    action to advance the tv guide by a number of hours passed in arg.
    """
    tvguide = menuw.menustack[-1]
    new_start_time = tvguide.start_time+(arg * 60 * 60)
    new_end_time =  tvguide.stop_time+(arg * 60 * 60)
    programs = tvguide.guide.GetPrograms(new_start_time+1, new_end_time-1, [ tvguide.start_channel])
    new_selected_program = programs[0].programs[0]
    tvguide.rebuild(new_start_time,new_end_time, tvguide.start_channel, new_selected_program)
    menuw.refresh()

class PluginInterface(plugin.DaemonPlugin):
    """
    global button bar plugin.
    """
    def __init__(self):
        """
        init the buttonbar
        """
        plugin.DaemonPlugin.__init__(self)
        plugin.register(self, 'buttonbar')
        self.poll_interval  = 10
        self.visible = True
        self.bar     = None
        self.barfile = ''
        self.surface = None
        self.colors = ('red', 'green', 'yellow', 'blue')
        self.actions = [None, None, None, None]
        self.tvguide_actions = (MenuItem('-1 Day', action= advance_tv_guide, arg= -24),
                                            MenuItem('-6 Hours', action= advance_tv_guide, arg= -6),
                                            MenuItem('+6 Hours', action= advance_tv_guide, arg= 6),
                                            MenuItem('+1 Day', action= advance_tv_guide, arg= 24)) 

        # Getting current LOCALE
        try:
            locale.resetlocale()
        except:
            pass


    def draw(self, (type, object), osd):
        """
        draw a background and color buttons
        """
        menu = osd.menu

        if (isinstance(menu, Menu) and \
            ((menu.item_types == 'main') or (menu.heading == 'Skin Selector'))) or \
            isinstance(menu, MenuItem) :
            return
            
        # draw Button bar
        w = osd.width+(2 * osd.x)
        h = osd.y+60
        y = ((osd.y * 2)+osd.height)-h

        f = skin.get_image('idlebar')

        if self.barfile != f:
            self.barfile = f
            try:
                self.bar = transform.scale(image.load(f).convert_alpha(), (w,h))
                self.bar = transform.flip(self.bar, False, True)
            except:
                self.bar = None

        # draw the cached barimage
        if self.bar:
            osd.drawimage(self.bar, (0, y, w, h), background=True)
    
        if isinstance(menu, TVGuide):
            actions = self.tvguide_actions
        else:
            # Determine the available actions
            if hasattr(menu, 'is_submenu'):
                    return
    
            actions = menu.selected.actions()
            if not actions:
               actions = []
            
            plugins = plugin.get('item')+plugin.get('item_%s' % menu.selected.type)
    
            if hasattr(menu.selected, 'display_type'):
                plugins += plugin.get('item_%s' % menu.selected.display_type)
    
            plugins.sort(lambda l, o: cmp(l._level, o._level))
                
            for p in plugins:
                for a in p.actions(menu.selected):
                    if isinstance(a, MenuItem):
                        actions.append(a)
                    elif len(a) == 2 or a[2] != 'MENU_SUBMENU':
                        actions.append(a[:2])
            
            if len(actions) == 0:
                return
                
        # Buttons modified from http://openclipart.org/cchost/media/files/kuba/1988 
        # draw the buttons
        buttonwidth = w / 4
        x = 0
        index = 0
        while (index < len(self.colors)):
            if index < len(actions):
                self.drawbutton(osd, x, y, buttonwidth, h, self.colors[index], actions[index])
                self.actions[index] = actions[index]
            else:
                self.actions[index] = None
            index += 1
            x += buttonwidth


    def drawbutton(self, osd, x, y, w, h, color, action):
        iw,ih = osd.drawimage(os.path.join(config.ICON_DIR, 'misc/'+color+'button.png' ) , (x+5, y+7, -1, -1))

        if isinstance(action, MenuItem):
            string = action.name
        else:
            string = action[1]
 
        font = osd.get_font('small0')        
        osd.drawstring(string, font, None, x = x+5+iw, y = y+5, width = w-iw, height = h-10, mode = 'soft', align_v='center')

    def eventhandler(self, event, menuw=None):
        action = None	
        result = False
        if event == BUTTONBAR_RED:
            action = self.actions[0]
            result = True
        elif event == BUTTONBAR_GREEN:
            action = self.actions[1]
            result = True
        elif event == BUTTONBAR_YELLOW:
            action = self.actions[2]
            result = True
        elif event == BUTTONBAR_BLUE:
            action = self.actions[3]
            result = True
        
        if not action:
           return result
        if isinstance(action, MenuItem):
           action.select(menuw=menuw)
        else:
           action[0](menuw=menuw)
           
        return result
