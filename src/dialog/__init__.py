# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo module to handle channel changing.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
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

"""
Module used to display information on top of the menu or video.

There are 2 types of display,
 1. OSD     - Displays information on top of the menu/main skin.
 2. Overlay - Displays information on top of video/external apps.

@var PLAY_STATE_PLAY: Play state constant for playing.
@var PLAY_STATE_PAUSE: Play state constant for paused.
@var PLAY_STATE_REWIND: Play state constant for rewinding.
@var PLAY_STATE_FFORWARD: Play state constant for fast forwarding.
@var PLAY_STATE_SEEK_BACK: Play state constant for seeking backward.
@var PLAY_STATE_SEEK_FORWARD: Play state constant for seeking forward.
@var PLAY_STATE_PLAY_SLOW: Play state constant for playing slow.
@var PLAY_STATE_PLAY_FAST: Play state constant for playing fast.
"""
import skins.osd.xml
import config


_osd_display = None
_overlay_display = None
_display = None

# Play state constants
PLAY_STATE_PLAY         = 'play'
PLAY_STATE_PAUSE        = 'pause'
PLAY_STATE_REWIND       = 'rewind'
PLAY_STATE_FFORWARD     = 'fastforward'
PLAY_STATE_SEEK_BACK    = 'seekback'
PLAY_STATE_SEEK_FORWARD = 'seekforward'
PLAY_STATE_PLAY_SLOW    = 'slow'
PLAY_STATE_PLAY_FAST    = 'fast'

def init():
    # Load the skin file
    skins.osd.xml.load(config.DIALOG_SKIN_XML_FILE)


def set_osd_display(display):
    """
    Set the display to be used when in the menu/main skin.
    @param display: The display to use as the OSD display
    """
    global _display, _osd_display
    _osd_display = display
    if _display is None:
        _display = display

def set_overlay_display(display):
    """
    Set the display to be used if an external application doesn't provide a
    display, or the display only supports text.
    @param display: The display to be used for external applications.
    """
    global _overlay_display
    _overlay_display = display

def enable_overlay_display(app_display):
    """
    Enable the overlay display.
    The overlay display will be app_display if it is not None and supports dialogs,
    or if there is no external overlay display available.
    @param app_display: Application embedded display.
    @return: The enabled display object.
    @rtype: dialog.display.Display
    """
    global _display
    if app_display and (app_display.supports_dialogs or not _overlay_display):
        _display = app_display
    elif _overlay_display:
        _display = _overlay_display
    else:
        import display
        _display = display.Display(False) # Create a dummy display
    print 'Overlay display enabled (%s)' % _display.__class__.__name__
    return _display


def disable_overlay_display():
    """
    Set the display back to the OSD display.
    """
    global _display
    _display = _osd_display


def get_display():
    """
    Retrieve the current display used for displaying messages, volume and dialogs.

    @return: The current display or None if not set.
    """
    return _display


def show_volume(level, muted, channel=None):
    """
    Helper function to display the volume level and whether it has been muted.

    @param level: Main volume level.
    @param muted: True if audio output has been muted, False otherwise.
    @param channel: The channel to show the volume for or None for the main level.
    Valid channels names are:
     - main
     - center
     - surround
     - lfe
    """
    if _display:
        _display.show_volume(level, muted, channel)


def show_message(message):
    """
    Helper function to show a generic message.

    @param message: Message to display.
    """
    if _display:
        _display.show_message(message)


def show_play_state(state, get_time_info=None):
    """
    Helper function to show the playing state of the current media.

    @param state: The play state can be one of the following:
                    play
                    pause
                    rewind
                    fastforward
                    seekback
                    seekforward
                    slow
                    fast
    @param get_time_info: A function to call to retrieve information about the
    current position and total play time, or None if not available. The function
    will return a tuple of total time and elapsed time.
    """
    if _display:
        _display.show_play_state(state, get_time_info)


def handle_event(event):
    """
    Passed the supplied event to the active display for processing.

    @param event: Event to process
    @return: True if processed, False otherwise
    """
    if _display:
        return _display.handle_event(event)
    return False
