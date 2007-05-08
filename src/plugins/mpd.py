# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# mpd.py - a plugin control mpd from freevo.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('mpd', level=45)
# Todo:        
#
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

#python modules
import os, stat, re, copy

# date/time
import time

#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui.PopupBox import PopupBox
from item import Item

#get the singletons so we get skin info and access the osd
skin = skin.get_singleton()
osd  = osd.get_singleton()

def execMPC(command, args):
    #cmd = "mpc " % command % args
    child = os.popen(command)
    data = child.read()
    err = child.close()
    if err:
        raise RuntimeError, '%s failed w/ exit code %d' % (command, err)
    return data

def mpdstatus():
    ms = execMPC("mpc status","")
    status = "stop"
    if ms.find("[paused]") <> -1:
           status = "Paused"
    if ms.find("[playing]") <> -1:
           status = "Playing"
    return status
 
class PluginInterface(plugin.MainMenuPlugin):
    """
    To activate, put the following lines in local_conf.py:
    plugin.activate('mpd', level=45) 
    """
    # make an init func that creates the cache dir if it don't exist
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
        
    def config(self):
        return [('mpd plugin',"what is this " ,  "Config" )]

    def items(self, parent):
        print "Plugin Interface items"
        return [ MpdMainMenu(parent) ]

class MpdItem(Item):
   # Item for the menu for one rss feed
    def __init__(self, parent):
        print "init mpd item"
        Item.__init__(self, parent)
        self.parent       = parent
        self.error        = 0
        self.location = "mpd"
        self.name = "MPD"
        self.last_update = 0 

    def start_detailed_interface(self, arg=None, menuw=None):
        print "starting detailed interface !"
        MpdDetailHandler(arg, menuw, self)

    def actions(self):
     #   return a list of actions for this item
        return [ ( self.start_detailed_interface, _('not sure what to do with this') ) ]

class MpdMainMenu(Item):
    """
    this is the item for the main menu and creates the list
    of Weather Locations in a submenu.
    """
    def __init__(self, parent):
        print "MpdMainMenu init"
        Item.__init__(self, parent, skin_type='mpd')
        self.parent = parent
        self.name   = _('MPD')

    def actions(self):
        """
        return a list of actions for this item
        """
        print "mpdmainmenu acttions"
        items = [ ( self.create_locations_menu , _('Locations') ) ]
        return items

    def __call__(self, arg=None, menuw=None):
        """
        call first action in the actions() list
        """
        print "first action"
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)


    def create_locations_menu(self, arg=None, menuw=None):
        locations  = []
        # create menu items
        print "create locatsion"
#        location = [('CAXX0177', 1, 'Greenwood')]
        mpd_item = MpdItem(self)
        locations.append(mpd_item)
        menuw.hide(clear=False)
        locations[0](menuw=menuw)

class MpdDetailHandler:
    """
    A handler class to display several detailed forecast screens and catch events
    """
    def __init__(self, iArg=None, iMenuw=None, iWeather=None ):
        print iMenuw
        print iWeather
        self.arg     = iArg
        self.menuw   = iMenuw
        self.mpd = iWeather
        self.menuw.hide(clear=False)
        rc.app(self)

        self.skins     = ('mpd')
        self.subtitles = (_('mpd'))
        self.curSkin   = 0

        print self.mpd.name
        self.title    = self.mpd.name
        self.subtitle = self.subtitles[0]
        
        # Fire up splashscreen and load the plugins
        skin.draw('mpd', self)

    def eventhandler(self, event, menuw=None):
        '''eventhandler'''
        if event == 'MENU_BACK_ONE_MENU':
            rc.app(None)
            self.menuw.show()
            return True

        elif event == 'MENU_SELECT':
            # toggle mpc off on
            execMPC("mpc toggle","")
            skin.draw( 'mpd', self )
            return True

        elif event in ('MENU_DOWN', 'MENU_RIGHT'):
            # Skip to the next track.
            print execMPC("mpc next","")
            skin.draw( 'mpd', self )
            return True

        elif event in ('MENU_UP', 'MENU_LEFT'):
            # Move to the previous track.
            execMPC("mpc prev","")
            skin.draw( 'mpd', self )
            return True
        
        return False

class MpdBaseScreen(skin.Area):
    """
    A base class for weather screens to inherit from, provides common members+methods
    """
    def __init__(self):
        print "init MpdBaseScreen"
        skin.Area.__init__(self, 'content')

        # Weather display fonts
        self.key_font      = skin.get_font('medium0')
        self.val_font      = skin.get_font('medium1')
        self.small_font    = skin.get_font('small0')
        self.big_font      = skin.get_font('huge0')

        # set the multiplier to be used in all screen drawing
        self.xmult = float( osd.width  - 2*config.OSD_OVERSCAN_X ) / 800
        self.ymult = float( osd.height - 2*config.OSD_OVERSCAN_Y ) / 600  

        self.update_functions = (self.update_info, self.update_info,
        self.update_info, self.update_info)

    def update_info(self):

        # display data
        print "update Info"
        text      = _("Song - ")
        value     = execMPC("mpc --format %title% status","")
        x_col1   = self.content.x + (50  * self.xmult) 
        x_col2   = self.content.x + (200 * self.xmult) 
        y_start  = self.content.y + (60  * self.xmult) 
        y_inc    = 40 * self.ymult
        self.write_text(text,   self.key_font,   self.content,  
        x=x_col1,  y=y_start, height=-1, width=x_col2-x_col1, align_h='right')
        self.write_text(value,  self.val_font,   self.content,  
        x=x_col2,  y=y_start, height=-1, align_h='left')

        text      = _("Artist - ")
        value     = execMPC("mpc --format %artist% status","")
        self.write_text(text,   self.key_font,   self.content,  
        x=x_col1,  y=y_start+y_inc, height=-1, width=x_col2-x_col1 , align_h='right')
        self.write_text(value,  self.val_font,   self.content,  
        x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')

        text      = _("Album - ")
        value     = execMPC("mpc --format %album%","")
        y_start   += y_inc
        self.write_text(text,   self.key_font,   self.content,  
        x=x_col1,  y=y_start+y_inc, height=-1, width=x_col2-x_col1 ,align_h='right')
        self.write_text(value,  self.val_font,   self.content,  
        x=x_col2,  y=y_start+y_inc, height=-1, align_h='left')
  
        text      = _("Status - ")
        value     = execMPC("mpc status","")
        y_start   += y_inc
        self.write_text(text,   self.key_font,   self.content,  
        x=x_col1,  y=y_start+y_inc, height=-1, width=x_col2-x_col1 ,align_h='right')
        self.write_text(value,  self.val_font,   self.content,  
        x=x_col2,  y=y_start+y_inc, height=100, align_h='left')

        # draw current condition image
        x_start = self.content.x + (450*self.xmult)
        y_start = self.content.y + (40*self.ymult)

        y_start = self.content.y + (200*self.ymult)
        y_start = self.content.y + (250*self.ymult)
        y_start = self.content.y + (250*self.ymult)
        y_start = y_start + 100
        value = mpdstatus()
        self.write_text(value, self.big_font,   self.content,  
        x=x_start, y=y_start,
        width=200*self.xmult, height=-1, align_h='center')

    def update_content(self):
        self.parent   = self.menu
        self.content  = self.calc_geometry(self.layout.content,  copy_object=True)
        self.update_functions[self.menu.curSkin]()


# create one instance of the MpdType class
skin.register ( 'mpd', ('screen', 'subtitle', 'title', 'plugin', MpdBaseScreen()) )
