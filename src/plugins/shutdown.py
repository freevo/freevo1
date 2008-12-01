# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# shutdown plug-in and handling
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


import os
import time
import sys

import config

from gui import ConfirmBox
from item import Item
from plugin import MainMenuPlugin

from dialog.dialogs import ButtonDialog

def shutdown(menuw=None, argshutdown=None, argrestart=None, exit=False):
    """
    Function to shut down freevo or the whole system. This system will be
    shut down when argshutdown is True, restarted when argrestart is true,
    else only Freevo will be stopped.
    """
    _debug_('shutdown(menuw=%r, argshutdown=%r, argrestart=%r, exit=%r)' % (menuw, argshutdown, argrestart, exit), 2)
    import osd
    import plugin
    import rc
    import util.mediainfo

    osd = osd.get_singleton()

    util.mediainfo.sync()
    if not osd.active:
        # this function is called from the signal handler, but
        # we are dead already.
        sys.exit(0)

    osd.clearscreen(color=osd.COL_BLACK)
    osd.drawstringframed(_('shutting down...'), 0, 0, osd.width, osd.height,
        osd.getfont(config.OSD_DEFAULT_FONTNAME, config.OSD_DEFAULT_FONTSIZE),
        fgcolor=osd.COL_ORANGE, align_h='center', align_v='center')
    osd.update()
    time.sleep(0.5)

    if argshutdown or argrestart:
        # shutdown dual head for mga
        if config.CONF.display == 'mga':
            os.system('%s runapp matroxset -f /dev/fb1 -m 0' % os.environ['FREEVO_SCRIPT'])
            time.sleep(1)
            os.system('%s runapp matroxset -f /dev/fb0 -m 1' % os.environ['FREEVO_SCRIPT'])
            time.sleep(1)

        _debug_('mga:plugin.shutdown()', 2)
        plugin.shutdown()
        _debug_('mga:rc.shutdown()', 2)
        rc.shutdown()
        _debug_('mga:osd.shutdown()', 2)
        osd.shutdown()

        if argshutdown and not argrestart:
            os.system(config.SYS_SHUTDOWN_CMD)
        elif argrestart and not argshutdown:
            os.system(config.SYS_RESTART_CMD)
        # let freevo be killed by init, looks nicer for mga
        while 1:
            time.sleep(1)
        return

    #
    # Exit Freevo
    #

    # Shutdown any daemon plugins that need it.
    _debug_('plugin.shutdown()', 2)
    plugin.shutdown()

    # Shutdown all children still running
    _debug_('rc.shutdown()', 2)
    rc.shutdown()

    # SDL must be shutdown to restore video modes etc
    _debug_('osd.clearscreen(color=osd.COL_BLACK)', 2)
    osd.clearscreen(color=osd.COL_BLACK)
    _debug_('osd.shutdown()', 2)
    osd.shutdown()

    _debug_('config.shutdown()', 2)
    config.shutdown()

    if exit:
        # realy exit, we are called by the signal handler
        sys.exit(0)

    _debug_('%s stop' % os.environ['FREEVO_SCRIPT'], 2)
    os.system('%s stop' % os.environ['FREEVO_SCRIPT'])

    # Just wait until we're dead. SDL cannot be polled here anyway.
    while 1:
        time.sleep(1)



class ShutdownItem(Item):
    """
    Item for shutdown
    """
    def __init__(self, parent=None):
        _debug_('ShutdownItem.__init__(parent=%r)' % (parent,), 2)
        Item.__init__(self, parent, skin_type='shutdown')
        self.menuw = None


    def actions(self):
        """
        return a list of actions for this item
        """
        _debug_('ShutdownItem.actions()', 2)
        if config.SYS_SHUTDOWN_CONFIRM:
            items = [ (self.confirm_freevo, _('Shutdown Freevo') ),
                          (self.confirm_system, _('Shutdown system') ),
                          (self.confirm_system_restart, _('Restart system') ) ]
        else:
            items = [ (self.shutdown_freevo, _('Shutdown Freevo') ),
                          (self.shutdown_system, _('Shutdown system') ),
                          (self.shutdown_system_restart, _('Restart system') ) ]
        if config.SYS_SHUTDOWN_ENABLE:
            items = [ items[1], items[0], items[2] ]

        return items


    def confirm_freevo(self, arg=None, menuw=None):
        """
        Pops up a ConfirmBox.
        """
        _debug_('confirm_freevo(arg=%r, menuw=%r)' % (arg, menuw), 2)
        self.menuw = menuw
        what = _('Do you really want to shut down Freevo?')
        dialog = ButtonDialog(((_('Shutdown'), self.shutdown_freevo), (_('Cancel'), None, True)),
                               what, ButtonDialog.QUESTION_TYPE)
        dialog.show()


    def confirm_system(self, arg=None, menuw=None):
        """
        Pops up a ConfirmBox.
        """
        _debug_('confirm_system(arg=%r, menuw=%r)' % (arg, menuw), 2)
        self.menuw = menuw
        what = _('Do you really want to shut down the system?')
        dialog = ButtonDialog(((_('Shutdown'), self.shutdown_system), (_('Cancel'), None, True)),
                               what, ButtonDialog.QUESTION_TYPE)
        dialog.show()


    def confirm_system_restart(self, arg=None, menuw=None):
        """
        Pops up a ConfirmBox.
        """
        _debug_('confirm_system_restart(arg=%r, menuw=%r)' % (arg, menuw), 2)
        self.menuw = menuw
        what = _('Do you really want to restart the system?')
        dialog = ButtonDialog(((_('Restart'), self.shutdown_system_restart), (_('Cancel'), None, True)),
                               what, ButtonDialog.QUESTION_TYPE)
        dialog.show()


    def shutdown_freevo(self, arg=None, menuw=None):
        """
        shutdown freevo, don't shutdown the system
        """
        _debug_('shutdown_freevo(arg=%r, menuw=%r)' % (arg, menuw), 2)
        shutdown(menuw=menuw, argshutdown=False, argrestart=False)


    def shutdown_system(self, arg=None, menuw=None):
        """
        shutdown the complete system
        """
        _debug_('shutdown_system(arg=%r, menuw=%r)' % (arg, menuw), 2)
        shutdown(menuw=menuw, argshutdown=True, argrestart=False)


    def shutdown_system_restart(self, arg=None, menuw=None):
        """
        restart the complete system
        """
        _debug_('shutdown_system_restart(arg=%r, menuw=%r)' % (arg, menuw), 2)
        shutdown(menuw=menuw, argshutdown=False, argrestart=True)



class PluginInterface(MainMenuPlugin):
    """
    Plugin to shutdown Freevo from the main menu
    """

    def items(self, parent):
        _debug_('items(parent=%r)' % (parent,), 2)
        return [ ShutdownItem(parent) ]
