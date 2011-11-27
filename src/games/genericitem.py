# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# genericitem.py - Item for generic objects
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
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
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.games.genericitem")


import os

import config
import game

TRUE  = 1
FALSE = 0

import rc
import time
import copy

from item import Item
import event as em
from struct import *
from string import *
from re import *


class GenericItem(Item):
    def __init__(self, file, cmd=None, args=None, imgpath=None, parent=None):
        logger.log( 9, 'GenericItem.__init__(file=%r, cmd=%r, args=%r, imgpath=%r, parent=%r)', file, cmd, args, imgpath, parent)

        Item.__init__(self, parent)
        self.type  = 'generic'            # fix value
        self.set_url(file, info=True)
        self.parent = parent

        self.name = os.path.splitext(os.path.basename(file))[0]

        # find image for this file
        shot = imgpath + '/' + os.path.splitext(os.path.basename(file))[0] + ".png"
        if os.path.isfile(shot):
            self.image = shot
        elif os.path.isfile(os.path.splitext(file)[0] + ".png"):
            self.image = os.path.splitext(file)[0] + ".png"

        command = ['--prio=%s' % config.GAMES_NICE, cmd]
        command.extend(args.split())
        if os.path.getsize(file) > 0:
            command.append(file)

        self.command = command

        self.game_player = game.get_singleton()


    def sort(self, mode=None):
        """
        Returns the string how to sort this item
        """
        logger.log( 9, 'sort(mode=%r)', mode)
        return self.name


    # ------------------------------------------------------------------------
    # actions:


    def actions(self):
        logger.log( 9, 'actions()')
        return [ ( self.play, 'Play' ) ]


    def play(self, arg=None, menuw=None):
        logger.log( 9, 'play(arg=%r, menuw=%r)', arg, menuw)
        self.parent.current_item = self

        if not self.menuw:
            self.menuw = menuw

        if self.menuw.visible:
            self.menuw.hide()

        logger.debug("Playing:  %s", self.filename)

        self.game_player.play(self, menuw)


    def stop(self, menuw=None):
        logger.log( 9, 'stop(menuw=%r)', menuw)
        self.game_player.stop()


    def eventhandler(self, event, menuw=None):
        logger.log( 9, 'eventhandler(event=%r, menuw=%r)', event, menuw)

        if event == em.STOP:
            self.stop()
            if not menuw == None:
                menuw.refresh(reload=1)

        # give the event to the next eventhandler in the list
        return Item.eventhandler(self, event, menuw)
