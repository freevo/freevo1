# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# speak.py - Festival Text-to-Speech plugin for Freevo 1.x
# -----------------------------------------------------------------------
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('speak')
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

import types
try:
    import festival
except ImportError:
    print String(_('ERROR')+': '+_('You need PyFest')+' (http://users.wpi.edu/~squirrel/programs/others/) '+_('to run the speak plugin.'))

from time import localtime, strftime

import config

from plugin import DaemonPlugin
from util.tv_util import get_chan_displayname

from item import Item
from tv.epg_types import TvProgram


class PluginInterface(DaemonPlugin):
    """
    Speak context info through Festival Text-to-Speech engine

    requires: festival installed and configured U{http://www.cstr.ed.ac.uk/}

    requires: PyFest installed U{http://users.wpi.edu/~squirrel/programs/others/}

    To activate this plugin, just put the following line into your local_conf.py:

    | plugin.activate('speak')

    Additionally you can customize the messages spoken upon startup and shutdown of Freevo by setting

    | SPEAK_WELCOME = 'Your welcome message'
    | SPEAK_SHUTDOWN = 'Your good bye message'

    """
    __author__           = 'Torsten Kurbad'
    __author_email__     = 'freevo@tk-webart.de'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = ''

    def __init__(self):
        """Initalize 'speak' plugin."""
        DaemonPlugin.__init__(self)
        # Open socket to festival server at port 1314
        self.fest = festival.open()
        # We want non-blocking behavior
        self.fest.block(False)
        # Set welcome/shutdown messages
        if config.SPEAK_WELCOME:
            self.welcome_msg = config.SPEAK_WELCOME
        else:
            self.welcome_msg = _('Welcome to Freevo!')
        if config.SPEAK_SHUTDOWN:
            self.shutdown_msg = config.SPEAK_SHUTDOWN
        else:
            self.shutdown_msg = _('Good bye!')

        # Say hello
        self.speak(self.welcome_msg)


    def speak(self, text):
        """Output 'text' through festival server."""
        if text is None:
            return
        try:
            if isinstance(text, types.UnicodeType):
                text = text.encode('iso-8859-15')
            elif isinstance(text, types.StringType):
                text = Unicode(text).encode('iso-8859-15')
        except UnicodeError:
            _debug_('UnicodeError: %s' % [x for x in text])

        _debug_('festival.say %s' % text)
        self.fest.say(text)


    def eventhandler(self, event, menuw=None):
        """Catch events to speak corresponding text."""
        _debug_('eventhandler(self, %s, %s) %s arg=%s' % (event, menuw, self, event.arg))

        if event.context is not None and event.context.endswith('menu'):
            sel = menuw.menustack[-1].selected
            if isinstance(sel, Item):
                self.speak(sel.name)
            elif isinstance(sel, TvProgram):
                text = _('channel')+(' %s, %s, ' % (get_chan_displayname(sel.channel_id), strftime('%H %M', localtime(sel.start))))+_('program')+(' %s ' % sel.title)
                self.speak(text)
            else:
                _debug_('Selected by unknown event: ')+('%s', sel.__class__, dir(menuw.menustack[-1].selected))


    def shutdown(self):
        """This method is automagically called upon shutdown of freevo."""
        self.speak(self.shutdown_msg)
        self.shutdown_msg = None
