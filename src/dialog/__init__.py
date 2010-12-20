# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Module used to display information on top of the menu or video.
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

There are 2 types of display:
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

@var overlay_display_support_dialogs: Whether the display to use if none is
    provided by the application, supports dialogs.
"""
import skins.osd.xml
import config


_osd_display = None
_overlay_display = None
_display = None

overlay_display_supports_dialogs = False

# Play state constants
PLAY_STATE_PLAY         = 'play'
PLAY_STATE_PAUSE        = 'pause'
PLAY_STATE_REWIND       = 'rewind'
PLAY_STATE_FFORWARD     = 'fastforward'
PLAY_STATE_SEEK_BACK    = 'seekback'
PLAY_STATE_SEEK_FORWARD = 'seekforward'
PLAY_STATE_PLAY_SLOW    = 'slow'
PLAY_STATE_PLAY_FAST    = 'fast'
PLAY_STATE_INFO       = 'info'

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
        display.enabled()

def set_overlay_display(display):
    """
    Set the display to be used if an external application doesn't provide a
    display, or the display only supports text.
    @param display: The display to be used for external applications.
    """
    global _overlay_display
    _overlay_display = display
    if display:
        global overlay_display_supports_dialogs
        overlay_display_supports_dialogs = display.supports_dialogs

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

    if _display:
        _display.disabled()

    if app_display and (app_display.supports_dialogs or not _overlay_display):
        _display = app_display
    elif _overlay_display:
        _display = _overlay_display
    else:
        import display
        _display = display.Display(False) # Create a dummy display

    if _display:
        _display.enabled()
    return _display


def disable_overlay_display():
    """
    Set the display back to the OSD display.
    """
    global _display
    if _display:
        _display.disabled()

    _display = _osd_display

    if _display:
        _display.enabled()


def get_display():
    """
    Retrieve the current display used for displaying messages, volume and dialogs.

    @return: The current display or None if not set.
    """
    return _display

def is_dialog_supported():
    """
    Retrieve whether the current display supports graphics dialogs or not.
    @return: True if the display supports graphics dialogs, False if not.
    """
    if _display:
        return _display.supports_dialogs

    return False

def is_dialog_showing():
    """
    Retrieve whether a dialog is currently being displayed.

    @return: True if a dialog is being displayed, False if not.
    """
    if _display and _display.supports_dialogs:
        return _display.current_dialog != None

    return False

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

def show_alert(message, type=None, handler=None):
    """
    Helper function to show a message that requires user input to close.

    @param message: Message to display.
    @param type: The type of the alert to show either None, 'warning' or 'error'.
    @param handler: Function to call when dialog is closed.
    """
    if not is_dialog_supported():
        raise DialogsNotSupportedError()

    from dialog.dialogs import ButtonDialog
    dialog = ButtonDialog(((_('Close'), handler),), message, type=type)
    dialog.show()

def show_confirmation(message, proceed_handler=None, cancel_handler=None,
                               proceed_text=None, cancel_text=None, type=None):
    """
    Helper function to show a message that requires confirmation to proceed
    (ie an OK/Cancel).

    @param message: Message to display.
    @param proceed_handler: Function to call if OK is selected.
    @param cancel_handler: Function to call if Cancel is selected.
    @param proceed_text: Text to use for the proceed button (defaults to OK if this is None).
    @param cancel_text: Text to use for the cancel button (defaults to Cancel if this is None).
    @param type: Type of the dialog box being display, can be one of the standard ButtonDialog types.
    """
    if not is_dialog_supported():
        raise DialogsNotSupportedError()

    if proceed_text is None:
        proceed_text = _('OK')

    if cancel_text is None:
        cancel_text = _('Cancel')

    from dialog.dialogs import ButtonDialog
    dialog = ButtonDialog(((proceed_text, proceed_handler),
                           (cancel_text, cancel_handler, True)),
                           message,
                           type=type)
    dialog.show()

def show_working_indicator(message):
    """
    Helper function to show that some work is taking place and that freevo hasn't
    crashed.
    @param message: Message to be displayed by the dialog.
    @return: A dialog object which the caller should call hide() on when work has completed.
    """
    from dialog.dialogs import ProgressDialog
    dialog = ProgressDialog(message, indeterminate=True)
    dialog.show()
    return dialog

def show_play_state(state, item, get_time_info=None):
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
                    info
    @param get_time_info: A function to call to retrieve information about the
    current position and total play time, or None if not available. The function
    will return a tuple of elapsed time, total time and percent through the file.
    Both total time and percent position are optional.
    """
    if _display:
        _display.show_play_state(state, item, get_time_info)


def handle_event(event):
    """
    Passed the supplied event to the active display for processing.

    @param event: Event to process
    @return: True if processed, False otherwise
    """
    if _display:
        return _display.handle_event(event)
    return False

def handle_mouse_event(event):
    if _display and hasattr(_display, 'handle_mouse_event'):
        _display.handle_mouse_event(event)

class DialogsNotSupportedError(Exception):
    """
    Exception that is raised when an attempt is made to show a dialog and the
    active display doesn't support dialogs.
    """
    pass
