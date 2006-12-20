# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# vfd.py - use PyVFD to display menus and players
# -----------------------------------------------------------------------
# $Id: vfd.py $
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('vfd')
# Todo:        
#    1) Use Threads. pyusb is too blocking!
#    2) See if it's possible to scroll the display
# -----------------------------------------------------------------------
# $Log$
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
# ----------------------------------------------------------------------- */


from menu import MenuItem
import copy
import time
import plugin
from event import *
from struct import *
import config
import util
from util.tv_util import get_chan_displayname
import sys
import os

try:
    import pyusb
except:
    print String(_("ERROR")+": "+_("You need pyusb (http://pyusb.berlios.de/) to run \"vfd\" plugin."))

dbglvl=1

# Configuration: (Should move to freevo_conf.py?)
sep_str = " | " # use as separator between two strings. Like: "Length: 123<sep_str>Plot: ..."
sep_str_mscroll = "   " # if string > width of vfd add this 

# Animaton-Sequence used in audio playback
# Some displays (like the CrytstalFontz) do display the \ as a /
animation_audioplayer_chars = ['-','\\','|','/']

# Bitmapped codes for icons
Clock =       0x10000000 
Radio =       0x08000000
Music =       0x04000000
CD_DVD =      0x02000000
Television =  0x01000000
Camera =      0x00100000
Rewind =      0x00080000
Record =      0x00040000
Play =        0x00020000
Pause =       0x00010000
Stop =        0x00001000
FastForward = 0x00000800
Reverse =     0x00000400
Repeat =      0x00000200
Mute =        0x00000100

def rjust( s, n ):
    return s[ : n ].rjust( n )

# menu_info: information to be shown when in menu
# Structure:
#
# menu_info = {
#     <TYPE> : [ ( <ATTRIBUTE>, <FORMAT_STRING> ), ... ],
#    }
# <ATTRIBUTE> is some valid attribute to item.getattr()
menu_info = {
    "main" : [ ],
    "audio" : [ ( "length", _( "Length" ) + ": %s" ),
                ( "artist", _( "Artist" ) + ": %s" ),
                ( "album", _( "Album" )   + ": %s" ),
                ( "year", _( "Year" )     + ": %s" ) ],
    "audiocd" : [ ( "len(tracks)", _( "Tracks" ) + ": %s" ),
                  ( "artist", _( "Artist" ) + ": %s" ),
                  ( "album", _( "Album" )   + ": %s" ),
                  ( "year", _( "Year" )     + ": %s" ) ],
    "video" : [ ( "length", _( "Length" )   + ": %s" ),
                ( "geometry", _( "Resolution" ) + ": %s" ),
                ( "aspect", _( "Aspect" ) + ": %s" ),
                ( "tagline", _( "Tagline" ) + ": %s" ),
                ( "plot", _( "Plot" ) + ": %s" ) ],
    "dir" : [ ( "plot", _( "Plot" ) + ": %s" ),
              ( "tagline", _( "Tagline" ) + ": %s" ) ],
    "image" : [ ( "geometry", _( "Geometry" ) + ": %s" ),
                ( "date", _( "Date" ) + ": %s" ),
                ( "description", _( "Description" ) + ": %s" ) ],
    "playlist" : [ ( "len(playlist)", _( "%s items" ) ) ],
    "mame" : [ ( "description", _( "Description" ) + ": %s" ) ],
    "unknow" : [ ]
    }
# menu_strinfo: will be passed to time.strinfo() and added to the end of info (after menu_info)
menu_strinfo = {
    "main" : "%H:%M - %a, %d-%b", # I like time in main menu
    "audio" : None,
    "audiocd" : None,
    "video" : None,
    "image" : None,
    "dir" : None,
    "playlist" : None,
    "mame" : None,
    "unknow" : None
    }


# layouts: dict of layouts (screens and widgets)
# Structure:
#
# layouts = { <#_OF_LINES_IN_DISPLAY> :
#             { <#_OF_CHARS_IN_LINES> :
#                { <SCREEN_NAME> :
#                  <WIDGET_NAME> : ( <WIDGET_TYPE>,
#                                    <WIDGET_PARAMETERS>,
#                                    <PARAMETERS_VALUES> ),
#                  ...
#                  <MORE_WIDGETS>
#                  ...
#                },
#                ...
#                <MORE_SCREENS>
#                ...
#              }
#           }
# Note:
#    <PARAMETERS_VALUES>: will be used like this:
#       <WIDGET_PARAMETERS> % eval( <PARAMETERS_VALUES> )
#    There should be at least these screens:
#       welcome: will be the shown during the startup
#          menu: will be used in menu mode
#        player: will be used in player mode
#            tv: will be used in tv mode
# Values should match the ones supported by VFDd (man VFDd)
layouts = { 1 : # 1 line display
            { 20 : # 20 chars per line
              # Welcome screen
              { "welcome":
                { "title"    : ( "title",
                                 "Freevo",
                                 None ),
                  "calendar" : ( "scroller",
                                 "" + _( "Today is %s." ) + "%s",
                                 "( time.strftime('%A, %d-%B'), self.get_sepstrmscroll(time.strftime('%A, %d-%B')) )" ),
                  "clock"    : ( "string",
                                 "%s",
                                 "( time.strftime('%T') )" )
                  },

                 "menu"    :
                 { "title_v"  : ( "scroller",
                                  "%s%s",
                                  "( menu.heading, self.get_sepstrmscroll(menu.heading) )" ),
                   "item_v"   : ( "scroller",
                                  "%s%s",
                                  "( title, self.get_sepstrmscroll(title) )" )
                   },

                 "audio_player":
                 { "music_v"   : ( "scroller",
                                   "%s%s",
                                   "( title, self.get_sepstrmscroll(title) )" ),
                  "time_v1"   : ( "string",
                                  "'% 2d:%02d/'",
                                  "( int(player.length / 60), int(player.length % 60) )" ),
                  "time_v2"   : ( "string",
                                  "'% 2d:%02d'",
                                  "( int(player.elapsed / 60), int(player.elapsed % 60) )" ),
                  "time_v3"   : ( "string",
                                  "'( %2d%%)'",
                                  "( int(player.elapsed * 100 / player.length) )" ),
                  # animation at the begining of the time line
                  "animation_v": ( "string", "'%s'",
                                   "animation_audioplayer_chars[player.elapsed % len(animation_audioplayer_chars)]")
                   },

                 "radio_player":
                 { "radio_v"   : ( "scroller",
                                   "%s%s",
                                   "( title, self.get_sepstrmscroll(title) )" ),
                  "time_v1"   : ( "string",
                                  "'% 2d:%02d/'",
                                  "( int(player.length / 60), int(player.length % 60) )" ),
                  "time_v2"   : ( "string",
                                  "'% 2d:%02d'",
                                  "( int(player.elapsed / 60), int(player.elapsed % 60) )" ),
                  "time_v3"   : ( "string",
                                  "'( %2d%%)'",
                                  "( int(player.elapsed * 100 / player.length) )" ),
                  # animation at the begining of the time line
                  "animation_v": ( "string", "'%s'",
                                   "animation_audioplayer_chars[player.elapsed % len(animation_audioplayer_chars)]")
                   },

                "video_player"  :
                { "video_v"   : ( "scroller",
                                  "%s%s",
                                "( title, self.get_sepstrmscroll(title) )" ),
                  "time_v1"   : ( "string",
                                  "'%s /'",
                                  "( length )" ),
                  "time_v2"   : ( "string",
                                  "'%s'",
                                  "( elapsed )" ),
                  # animation at the begining of the time line
                  "animation_v": ( "string", "'%s'",
                                   "animation_audioplayer_chars[player.elapsed % len(animation_audioplayer_chars)]")
                  },


                 "tv":
                 { "chan_v"   : ( "scroller",
                                  "%s%s",
                                  "( get_chan_displayname(tv.channel_id), self.get_sepstrmscroll( get_chan_displayname(tv.channel_id)) )" ),
                   "prog_v"   : ( "scroller",
                                  "%s%s",
                                  "( tv.title, self.get_sepstrmscroll(tv.title) )" )
                   }
                } # screens
              } # chars per line
            } # lines per display

# poll_widgets: widgets that should be refreshed during the pool
# Structure:
#
# poll_widgets = { <#_OF_LINES_IN_DISPLAY> :
#                  { <SCREEN_NAME> : ( <WIDGET_NAME>, ... ) },
#                  ...
#                }
poll_widgets = { 1 : {
    20 : { "welcome" : [ "clock" ] },    
    },
                 }

def get_info( item, list ):
    info = ""

    for l in list:

        v = item.getattr( l[ 0 ] )
        if v:
            if info:
                info += sep_str
            info += l[ 1 ] % v

    return info


class PluginInterface( plugin.DaemonPlugin ):
    """
    Display context info on Shuttle's VFD (Versatile Front-panel Display)

    Requirements:
       * pyusb: installed (http://pyusb.berlios.de/) with name patch as
                the default module is called usb and conflicts with freevo's
                usb plugin.
       * pyusb-0.3.3-name.patch (http://www.linuxowl.com/patches/)

    Updates available from http://www.linuxowl.com/software.

    To activate this plugin, just put the following line at the end of your
    local_conf.py file:

    plugin.activate( 'vfd' )

    """
    __author__           = 'Duncan Webb'
    __author_email__     = 'duncan-ffs@linuxowl.com'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision: 20060727 $'

    def send( self, data ):
        "Send a piece of data to specified VFD device, retrying if necessary"
        attempts = 3
        while attempts > 0:
            try:
                _debug_(_("Sending data %r attempt=%d"%(data,4-attempts)), dbglvl+1)
                time.sleep(self.sleepLength)
                r=self.vfd.controlMsg(0x21,   # Message to Class Interface
                               0x09,
                               data,
                               0x0200,
                               0x0001) # Endpoint 1
                return
            except Exception,e:
                attempts -= 1
                _debug_( _( "WARNING" ) + ": " + _( "%r attempt=%d"%(data,4-attempts)), 1)

        raise e

    def msg( self, msgtype, *msgdata ):
        assert msgtype >= 0 and msgtype <= 0xf
        assert len(msgdata) <= 7

        retval = chr((msgtype<<4)+len(msgdata))
        if len(msgdata) == 1 and type(msgdata[0]) == str:
            retval += msgdata[0]+"\x00"*(7-len(msgdata[0]))
        else:
            retval += "".join([type(x) == int and chr(x) or x for x in msgdata])
            retval += "\x00"*(7-len(msgdata))
        _debug_('retval=%r, msgtype=%s, len(msgdata)=%s, msgdata=%s' % \
            (retval, msgtype, len(msgdata), msgdata), dbglvl+1)
        return retval

    def clear( self ):
        "Clear the display"
        self.last_message = None
        self.last_bitmask = None
        self.send(self.msg(1,1))

    def reset( self ):
        "Reset the cursor position"
        self.send(self.msg(1,2))

    def split( self, s, length, maxlength ):
        "Split a string into chunks, but no longer than maxlength"
        if len(s) > maxlength:
            _debug_('Truncating \"%s\" longer than %d characters' % (s,maxlength), dbglvl+1)
            s = s[:maxlength]
        s = s.center(maxlength)
        out = []
        for x in range(0,len(s),length):
            out.append(s[x:x+length])
        return out

    def message( self, msgstring, cls=0 ):
        "Update the display with a string, specifying if it should be cleared first"

        try:
            msgstring = msgstring.encode('latin1')
        except UnicodeError:
            # Strange for some reason the name changes on play
            _debug_('%s' % [x for x in msgstring])
            #_debug_('%d' % [x for x in msgstring])
            #_debug_('%s' % [type(x) for x in msgstring])

        if self.last_message == msgstring:
            return

        _debug_('message \"%s\"->\"%s\" cls=%s' % (self.last_message, msgstring, cls), dbglvl)
        self.last_message = msgstring

        msgparts = self.split(msgstring, 7, self.maxStringLength)
        _debug_('msgparts=%s' % (msgparts), dbglvl+1)

        if cls:
            self.clear()
        else:
            self.reset()

        for part in msgparts:
            self.send(self.msg(9,*part))

    def icons( self ):
        "Update icons to be shown"
        _debug_('device=%x media=%x recording=%x running=%x muted=%x volume=%x' % \
            (self.device, self.media, self.recording, self.running, self.muted, self.volume), dbglvl+1)
        self.bitmask = self.device | self.media | self.recording | self.running | self.muted | self.volume
        if self.bitmask == self.last_bitmask:
            return
        _debug_('last_bitmask=\"%r\"->bitmask=\"%r\"' % (self.last_bitmask, self.bitmask), dbglvl+1)
        self.last_bitmask = self.bitmask
        self.send(self.msg(7,pack('I', self.bitmask)))

    def set_device( self, device=None ):
        if device != None:
            self.device = device
        _debug_('device=%s, self.device=%s' % (device, self.device), dbglvl+1)

    def set_media( self, media=None ):
        if media != None:
            self.media = media
        _debug_('media=%s, self.media=%s' % (media, self.media), dbglvl)

    def set_running( self, running=None ):
        if running != None:
            self.running = running
        _debug_('running=%s, self.running=%s' % (running, self.running), dbglvl+1)

    def set_recording( self, recording=None ):
        if recording != None:
            self.recording = recording
        else:
            self.recording = (os.path.exists(self.tvlockfile) and Record) or 0
        _debug_('recording=%s, self.recording=%s' % (recording, self.recording), dbglvl+1)

    def set_mixer( self, muted=None, volume=None ):
        if self.mixer == None:
            return

        if muted == None:
            muted = self.mixer.getMuted()
        self.muted = (muted and Mute) or 0

        if volume == None:
            volume = self.mixer.getVolume()
        self.volume = int(((volume + 8.0) * 11.0) / 99.0) # 99 / 11 - 1 = 8

        _debug_('muted=%s, self.muted=%s, volume=%s, self.volume=%s' % (muted, self.muted, volume, self.volume), dbglvl)

    def widget_set( self, screen, widget, value ):
        #if widget != 'clock' and widget != 'time_v1' and widget != 'time_v2' and widget != 'time_v3' and widget != 'animation_v':
        if widget != 'clock' and widget != 'time_v2' and widget != 'time_v3' and widget != 'animation_v':
            _debug_('screen=%s, widget=%s, value=%s' % ( screen, widget, value ), dbglvl)
        if screen == "welcome":
            pass
        elif screen == "menu":
            if widget == "title_v":
                if value == "Freevo Main Menu":
                    self.set_device(0)
                elif value == "TV Main Menu":
                    self.set_device(Television)
                elif value == "Movie Main Menu":
                    self.set_device(CD_DVD)
                elif value == "Audio Main Menu":
                    self.set_device(Music)
                elif value == "Radio Stations":
                    self.set_device(Radio)
                elif value == "Image Main Menu":
                    self.set_device(Camera)
                elif value == "Headlines Sites":
                    self.set_device(0)
                elif value == "Weather":
                    self.set_device(0)
            self.set_running(0)
        elif screen == "radio_player":
            self.set_device(Radio)
        elif screen == "audio_player":
            self.set_device(Music)
        elif screen == "video_player":
            self.set_device(CD_DVD)
        elif screen == "tv":
            self.set_device(Television)
        else:
            _debug_('ERROR: unknown screen screen=%s, widget=%s, value=%s' % ( screen, widget, value ), 0)

        if widget == "title":
            pass
        elif widget == "title_v":
            pass
        elif widget == "item_v":
            self.message(value)
        elif widget == "radio_v":
            self.message(value)
        elif widget == "music_v":
            self.message(value)
        elif widget == "video_v":
            self.message(value)
        elif widget == "chan_v":
            self.message(value)
        elif widget == "prog_v":
            pass
        elif widget == "time_v1":
            pass
        elif widget == "time_v2":
            pass
        elif widget == "time_v3":
            self.set_running(Play) #work around for audio
        elif widget == "animation_v":
            pass
        elif widget == "clock":
            pass
        elif widget == "calendar":
            pass
        else:
            _debug_('ERROR: unknown widget screen=%s, widget=%s, value=%s' % ( screen, widget, value ), 0)
        self.icons()

    def __init__( self ):
        """
        init the vfd
        """
        plugin.DaemonPlugin.__init__(self)

        self.disable = 0
        self.playitem = None
        self.event_listener = 1
        self.vendorID = 4872    # Shuttle Inc
        self.productID = 0003   # VFD Module
        self.maxStringLength = 20
        self.sleepLength = 0.015
        self.vfd = None
        for bus in pyusb.busses():
            for dev in bus.devices:
                if dev.idVendor == self.vendorID and dev.idProduct == self.productID:
                    self.vfd = dev.open()
                    _debug_('Found VFD on bus %s at device %s' % (bus.dirname,dev.filename), dbglvl)

        if self.vfd == None:
            _debug_(String(_( "ERROR" )) + ":" + String(_( "Cannot find VFD device" )), 0)
            self.disable = 1
            self.reason = "Cannot find VFD device"
            return
        self.clear()

        self.mixer = plugin.getbyname('MIXER')
        if self.mixer == None:
            _debug_(String(_( "ERROR" )) + ":" + String(_( "Cannot find MIXER" )), 0)
            self.disable = 1
            self.reason = "Cannot find MIXER"
            return

        self.tvlockfile = config.FREEVO_CACHEDIR + '/record'

        self.set_device(0)
        self.set_media(0)
        self.set_running(0)
        self.set_recording(0)
        self.set_mixer(0)
        self.icons()

        self.poll_interval = 10
        self.poll_menu_only = 0
        self.height = 1
        self.width  = 20
        self.last_message = None
        self.last_bitmask = 0
        self.generate_screens()

        plugin.register( self, "vfd" )


        # Show welcome screen:
        for w in self.screens[ "welcome" ]:
            type, param, val = self.screens[ "welcome" ][ w ]            
            if val: param = param % eval( val )

            self.widget_set( "welcome", w, param )

        self.last_screen = "welcome"

        self.lsv = { } # will hold last screen value (lsv)

    def close( self ):
        """
        to be called before the plugin exists.
        """
        self.message( "bye" )

    def draw( self, ( type, object ), osd ):
        """
        'Draw' the information on the VFD display.
        """
        if self.disable: return

        #_debug_('draw(self, (%s,%s), %s)' % (type, object, osd))

        # Check if audio is detached
        # When in detached mode, do not draw the player screen
        if plugin.getbyname('audio.detachbar'):
            if type == 'player' and plugin.getbyname('audio.detachbar').status != 0:
                return

        if type == 'player':
            sname = "%s_%s" % ( object.type, type )
        else:
            sname = type

        if not self.screens.has_key( sname ):
            sname = 'menu'

        _debug_('sname=%s, last_screen=%s' % (sname, self.last_screen), dbglvl+1)
        if sname != self.last_screen:
            # recreate screen
            # This is used to handle cases where the previous screen was dirty
            # ie: played music with info and now play music without, the previous
            #     info will still be there
            self.generate_screen( sname )
            self.lsv = { } # reset last changed values

        if type == 'menu':   
            menu  = object.menustack[ -1 ]
            title = menu.selected.name
            if isinstance( menu.selected, MenuItem ):
                title = _( title )
            typeinfo = menu.selected.type
            info = ""

            if menu.selected.getattr( 'type' ):
                typeinfo = menu.selected.getattr( 'type' )

            # get info:
            if menu.selected.type and menu_info.has_key( menu.selected.type ):
                info = get_info( menu.selected, menu_info[ menu.selected.type ] )
                if menu_strinfo.has_key( menu.selected.type ) and menu_strinfo[ menu.selected.type ]:
                    if info:
                        info += sep_str
                    info += time.strftime( menu_strinfo[ menu.selected.type ] )

            # specific things related with item type
            if menu.selected.type == 'audio':
                title = String(menu.selected.getattr( 'title' ))
                if not title:
                    title = String(menu.selected.getattr( 'name' ))
                if menu.selected.getattr( 'trackno' ):
                    title = "%s - %s" % ( String(menu.selected.getattr( 'trackno' )), title )

        elif type == 'player':
            player = object
            title  = player.getattr( 'title' )
            if not title:
                title = String(player.getattr( 'name' ))

            if player.type == 'radio':
                if player.getattr( 'trackno' ):
                    title = "%s - %s" % ( String(player.getattr( 'trackno' )), title )

            elif player.type == 'audio':
                if player.getattr( 'trackno' ):
                    title = "%s - %s" % ( String(player.getattr( 'trackno' )), title )

            elif player.type == 'video':
                length = player.getattr( 'length' )
                elapsed = player.elapsed
                if elapsed / 3600:
                    elapsed ='%d:%02d:%02d' % ( elapsed / 3600, ( elapsed % 3600 ) / 60,
                                                elapsed % 60)
                else:
                    elapsed = '%d:%02d' % ( elapsed / 60, elapsed % 60)
                try:
                    percentage = float( player.elapsed / player.info.video[0].length )
                except:
                    percentage = None


        elif type == 'tv':
            tv = copy.copy( object.selected )

            if tv.start == 0:
                tv.start = " 0:00"
                tv.stop  = "23:59" # could also be: '????'
            else:
                tv.start = time.localtime( tv.start )
                tv.stop  = time.localtime( tv.stop )

                tv.start = "% 2d:%02d" % ( tv.start[ 3 ], tv.start[ 4 ] )
                tv.stop  = "% 2d:%02d" % ( tv.stop[ 3 ], tv.stop[ 4 ] )


        s = self.screens[ sname ]
        for w in s:
            t, param, val = s[ w ]
            try:
                if val: param = param % eval( val )
            except:
                param = None

            k = '%s %s' % ( sname, w )
            try:
                if String(self.lsv[ k ]) == String(param):
                    continue # nothing changed in this widget
            except KeyError:
                pass

            self.lsv[ k ] = param
            if param:
                self.widget_set( sname, w, param )

        if self.last_screen != sname:
            self.last_screen = sname


    def poll( self ):
        if self.disable: return

        if self.playitem:
            self.draw( ( 'player', self.playitem ), None )

        try:
            screens = poll_widgets[ self.lines ][ self.columns ]
        except:
            return

        for s in screens:
            widgets = screens[ s ]

            for w in widgets:
                type, param, val = self.screens[ s ][ w ]

                if val: param = param % eval( val )
                self.widget_set( s, w, param )

        self.set_recording()
        self.icons()


    def generate_screens( self ):
        screens = None
        l = self.height
        c = self.width
        # Find a screen
        # find a display with 'l' lines
        while not screens:
            try:                
                screens = layouts[ l ]
            except KeyError:
                _debug_( _( "WARNING" ) + ": " + _( "Could not find screens for %d lines VFD!" ) % l, dbglvl)
                l -= 1
                if l < 1:
                    _debug_(String(_( "ERROR" )) + ": " + String(_( "No screens found for this VFD (%dx%d)!" )) % \
                        ( self.height, self.width ), 0)
                    self.disable = 1
                    return
        # find a display with 'l' line and 'c' columns
        while not screens:
            try:
                screens = layouts[ l ][ c ]
            except KeyError:
                _debug_( _( "WARNING" ) + ": " + _( "Could not find screens for %d lines and %d columns VFD!" ) % \
                    ( l, c ), 1)
                c -= 1
                if c < 1:
                    _debug_(String(_( "ERROR" )) + ": " + String(_( "No screens found for this VFD (%dx%d)!" )) % \
                        ( self.height, self.width ), 0)
                    self.disable = 1
                    return


        self.lines = l
        self.columns = c
        try:
            self.screens = screens = layouts[ l ][ c ]
        except KeyError:
            _debug_(String(_( "ERROR" )) + ": " + String(_( "No screens found for this VFD (%dx%d)!" )) % \
                ( self.height, self.width ), 0)
            self.disable = 1
            return

        for s in screens:
            self.generate_screen( s )


    def generate_screen( self, s ):
        if not self.screens.has_key( s ):
            s = 'menu'
        widgets = self.screens[ s ]

        for w in widgets:
            type, param, val = self.screens[ s ][ w ]
            _debug_('self.screens[ %s ][ %s ]=%s' % (s,w,self.screens[ s ][ w ]), dbglvl+1)


    def eventhandler( self, event, menuw=None ):
        update_bits = 0
        _debug_('eventhandler(self, %s, %s) %s arg=%s' % (event, menuw, self, event.arg), dbglvl)

        if event == 'MIXER_MUTE':
            # it seems that the exent is received before the mixer has been set!
            self.set_mixer(self.mixer.getMuted() == 0)
            update_bits = 1
        elif event == 'MIXER_VOLDOWN' or event == 'MIXER_VOLUP':
            self.set_mixer(0)
            update_bits = 1
        elif event == 'PLAY' or event == 'PLAY_START':
            self.set_running(Play)
            self.playitem = event.arg
            update_bits = 1
        elif event == 'PLAY_END' or event == 'USER_END' or event == 'STOP':
            self.set_running(0)
            self.playitem = None
            update_bits = 1
        elif event == 'PAUSE':
            # two pauses resume play but leaves Pause!
            self.set_running(Pause)
            update_bits = 1
        elif event == 'SEEK':
            self.set_running((event.arg < 0 and Rewind) or FastForward)
            update_bits = 1
        elif event == 'PLUGIN_EVENT IDENTIFY_MEDIA':
            media = event.arg[0]
            self.set_media((hasattr(media.item, 'type') and Clock) or 0)
            update_bits = 1
        elif event == 'VIDEO_START':
            self.set_running(Play)
            update_bits = 1
        elif event == 'VIDEO_END':
            self.set_running(Stop)
            update_bits = 1
        elif event == 'BUTTON':
            pass
        elif event == 'VIDEO_SEND_MPLAYER_CMD':
            pass
        elif event == 'OSD_MESSAGE':
            pass
        elif event == 'MENU_UP':
            pass
        elif event == 'MENU_DOWN':
            pass
        elif event == 'MENU_PAGEUP':
            pass
        elif event == 'MENU_PAGEDOWN':
            pass
        elif event == 'MENU_SELECT':
            pass
        elif event == 'MENU_SUBMENU':
            pass
        elif event == 'MENU_BACK_ONE_MENU':
            pass
        elif event == 'MENU_GOTO_MAINMENU':
            pass
        else:
            #_debug_('eventhandler(self, %s, %s) %s arg=%s' % (event, menuw, self, event.arg), dbglvl)
            _debug_('\"%s\" not handled' % (event))

        if update_bits:
            self.icons()

        return 0

    def get_sepstrmscroll( self, mscrolldata ):
        """
        used for marquee scroller; returns seperator if info is wider then lcd
        """
        if len(mscrolldata) > self.width:
            return sep_str_mscroll
        else:
            return ''

