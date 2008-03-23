# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# sounds.py - Sound effects for the freevo gui
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# $Log$
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
# ----------------------------------------------------------------------- */

import os.path
import time

import pygame.mixer

import config



# Used to cache Sound objects for configurable sounds
sounds_cache = {}


def load_sound(sound):
    """
    Return a pygame.mixer.Sound object based on sound.
    sound can be an string - containing the name of a sound effect or a filename,
    a pygame.mixer.Sound object or an file-like object.
    If sound is the name of a sound effect the pygame.mixer.Sound object will be
    cached for use again.
    """
    if not config.OSD_SOUNDS_ENABLED:
        return None

    sound_object = None

    if isinstance(sound,str):
        # sound refers to a configurable sound
        if sound in config.OSD_SOUNDS:
            # Check to see if we have already loaded this sound effect
            if sound in sounds_cache:
                sound_object = sounds_cache[sound]
            else:
                sound_file = config.OSD_SOUNDS[sound]
                if sound_file:
                    try:
                        sound_object = pygame.mixer.Sound(sound_file)
                    except:
                        pass

                    # Even if we fail to load the file cache the sound
                    # anyway so its faster next time (as we won't bother to
                    # try and load it)
                    sounds_cache[sound] = sound_object

        # sound refers to a file
        elif os.path.exists(sound):
            try:
                sound_object = pygame.mixer.Sound(sound)
            except:
                pass

    elif isinstance(sound, pygame.mixer.Sound):
        sound_object = sound
    else:
        try:
            sound_object = pygame.mixer.Sound(sound)
        except:
            pass

    return sound_object


def play_sound(sound):
    """
    Play a sound effect.
    The sound will only be played if UI_SOUNDS_ENABLED is True.
    sound can be an string - containing a sound effect name or a filename, a
    pygame.mixer.Sound object or an file-like object.
    """
    if config.OSD_SOUNDS_ENABLED and sound is not None:
        sound_object = load_sound(sound)

        if sound_object:
            sound_object.play()
            time.sleep(0.2)


if config.OSD_SOUNDS_ENABLED:
    try:
        # Initialise the mixer
        pygame.mixer.init(44100,-16,2, 1024 * 3)
    except:
        print 'Mixer initialisation failed, OSD sounds disabled!'
        config.OSD_SOUNDS_ENABLED = False

# 'Known' sounds
MENU_NAVIGATE = load_sound('menu.navigate') # Left/Right/Up/Down menu events
MENU_BACK_ONE = load_sound('menu.back_one')
MENU_SELECT   = load_sound('menu.select')
