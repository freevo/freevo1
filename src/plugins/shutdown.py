# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# shutdown.py  -  shutdown plugin / handling
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.7  2004/07/10 12:33:40  dischi
# header cleanup
#
# Revision 1.6  2004/06/09 19:42:08  dischi
# fix crash
#
# Revision 1.5  2004/06/06 14:16:08  dischi
# small fix for confirm and enable shutdown sys
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


import os
import time
import sys

import config

from gui import ConfirmBox
from item import Item
from plugin import MainMenuPlugin

if config.WARN_SHUTDOWN or config.USE_NVRAM_WAKEUP:
    import tv.record_client as record_client


def shutdown(menuw=None, argshutdown=None, argrestart=None, exit=False):
    """
    Function to shut down freevo or the whole system. This system will be
    shut down when argshutdown is True, restarted when argrestart is true,
    else only Freevo will be stopped.
    """
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
                         osd.getfont(config.OSD_DEFAULT_FONTNAME,
                                     config.OSD_DEFAULT_FONTSIZE),
                         fgcolor=osd.COL_ORANGE, align_h='center', align_v='center')
    osd.update()
    time.sleep(0.5)

    if argshutdown or argrestart:  
        # shutdown dual head for mga
        if config.CONF.display == 'mga':
            os.system('%s runapp matroxset -f /dev/fb1 -m 0' % \
                      os.environ['FREEVO_SCRIPT'])
            time.sleep(1)
            os.system('%s runapp matroxset -f /dev/fb0 -m 1' % \
                      os.environ['FREEVO_SCRIPT'])
            time.sleep(1)

        plugin.shutdown()
        rc.shutdown()
        osd.shutdown()

        if argshutdown and not argrestart:
            os.system(config.SHUTDOWN_SYS_CMD)
        elif argrestart and not argshutdown:
            os.system(config.RESTART_SYS_CMD)
        # let freevo be killed by init, looks nicer for mga
        while 1:
            time.sleep(1)
        return

    #
    # Exit Freevo
    #
    
    # Shutdown any daemon plugins that need it.
    plugin.shutdown()

    # Shutdown all children still running
    rc.shutdown()

    # SDL must be shutdown to restore video modes etc
    osd.clearscreen(color=osd.COL_BLACK)
    osd.shutdown()

    if exit:
        # realy exit, we are called by the signal handler
        sys.exit(0)

    os.system('%s stop' % os.environ['FREEVO_SCRIPT'])

    # Just wait until we're dead. SDL cannot be polled here anyway.
    while 1:
        time.sleep(1)
        

class ShutdownItem(Item):
    """
    Item for shutdown
    """
    def __init__(self, parent=None):
        Item.__init__(self, parent, skin_type='shutdown')
        self.menuw = None


    def actions(self):
        """
        return a list of actions for this item
        """
        if config.CONFIRM_SHUTDOWN:
            items = [ (self.confirm_freevo, _('Shutdown Freevo') ),
                          (self.confirm_system, _('Shutdown system') ),
                          (self.confirm_system_restart, _('Restart system') ) ]
        else:
            items = [ (self.shutdown_freevo, _('Shutdown Freevo') ),
                      (self.check_shutdown_system, _('Shutdown system') ),
                          (self.shutdown_system_restart, _('Restart system') ) ]
        if config.ENABLE_SHUTDOWN_SYS:
            items = [ items[1], items[0], items[2] ]

        return items


    def next_scheduled_recording(self):
        """
        return starting time of next scheduled recording (or None)
        """
        (server_available, msg) = record_client.connectionTest()
        if not server_available:
            return None
        (result, recordings) = record_client.getScheduledRecordings()
        if result:
            progs = recordings.getProgramList().values()
            if len(progs):
                progs.sort(lambda a, b: cmp(a.start, b.start))
                return progs[0].start
        return None


    def next_recording_message(self, format, start_time = None):
        if start_time == None:
            start_time = self.next_scheduled_recording()
        if start_time == None:
            return ""
        rec_distance = start_time - time.time() - config.TV_RECORD_PADDING
        if rec_distance < 0:
            result = _('A recording is in progress.')
        elif rec_distance < 60*60:
            result = _('The next scheduled recording begins in %d minutes.') % int(rec_distance/60)
        elif rec_distance < 60*60*10:
            result = _('The next scheduled recording begins at %s.') % time.strftime(config.TV_TIMEFORMAT, time.localtime(start_time))
        else:
            result = _('The next recording is scheduled for %s.') % time.strftime(config.TV_DATETIMEFORMAT, time.localtime(start_time))
        return format % result


    def confirm_freevo(self, arg=None, menuw=None):
        """
        Pops up a ConfirmBox.
        """
        self.menuw = menuw
        what = _('Do you really want to shut down Freevo?') \
               + self.next_recording_message(" %s")
        ConfirmBox(text=what, handler=self.shutdown_freevo, default_choice=1).show()
        
        
    def confirm_system(self, arg=None, menuw=None):
        """
        Pops up a ConfirmBox.
        """
        self.menuw = menuw
        what = _('Do you really want to shut down the system?') \
               + self.next_recording_message(" %s")
        ConfirmBox(text=what, handler=self.shutdown_system, default_choice=1).show()


    def confirm_system_restart(self, arg=None, menuw=None):
        """
        Pops up a ConfirmBox.
        """
        self.menuw = menuw
        what = _('Do you really want to restart the system?') \
               + self.next_recording_message(" %s")
        ConfirmBox(text=what, handler=self.shutdown_system_restart, default_choice=1).show()


    def check_shutdown_system(self, arg=None, menuw=None):
        """
        Shutdown the complete system if the next recording is not too far away
        """
        if config.WARN_SHUTDOWN:
            start_time = self.next_scheduled_recording()
            if start_time != None:
                if start_time - config.TV_RECORD_PADDING - time.time() \
                       < config.WARN_SHUTDOWN:
                    what = self.next_recording_message("%s ", start_time) + \
                           _('Do you really want to shut down the system?')
                    ConfirmBox(text=what, handler=self.shutdown_system, default_choice=1).show()
                    return
        self.shutdown_system(arg, menuw)


    def shutdown_freevo(self, arg=None, menuw=None):
        """
        Shutdown freevo, don't shutdown the system
        """
        shutdown(menuw=menuw, argshutdown=False, argrestart=False)

        
    def shutdown_system(self, arg=None, menuw=None):
        """
        Shutdown the complete system, use nvram-wakeup to schedule
        boot-up before next recording (if configured to do so).
        nvram-wakup may signal that an additional reboot is needed
        (with exitcode 1), in this case a flag file is created and the
        system is rebooted.
        """
        doShutdown = True
        if config.USE_NVRAM_WAKEUP:
            start_time = self.next_scheduled_recording()
            if start_time != None:
                wakeupTime = start_time \
                             - config.TV_RECORD_PADDING \
                             - config.BOOTTIME_PADDING
                _debug_("calling nvram-wakeup with %d" % wakeupTime)
                ec = os.system(config.NVRAM_WAKEUP_CMD % (wakeupTime,))
                _debug_(".. exitcode was %d" % ec)
                if ec == 256:
                    doShutdown = False
                    file(config.NVRAM_REBOOT_FLAG, "w").close()
                elif ec > 0:
                    ConfirmBox(text=_('Could not program computer to boot up before next recording. Shutdown anyway?'),
                               handler=self.shutdown_system_anyway, default_choice=1).show()
                    return
        shutdown(menuw=menuw, argshutdown=doShutdown, argrestart=not doShutdown)


    def shutdown_system_anyway(self, arg=None, menuw=None):
        """
        Shutdown freevo, don't shutdown the system
        """
        shutdown(menuw=menuw, argshutdown=True, argrestart=False)


    def shutdown_system_restart(self, arg=None, menuw=None):
        """
        Restart the complete system
        """
        shutdown(menuw=menuw, argshutdown=False, argrestart=True)

        
        
# According to
# http://mail.python.org/pipermail/python-list/2004-September/241553.html
# a) Python has no uptime() implementation and
# b) calling "uptime" is not more portable than parsing /proc/uptime.
# Since the latter is much easier, I will do so.. ;-)
def uptime():
    uptime, idletime = [float(f) for f in file("/proc/uptime").read().split()]
    return uptime


#
# the plugins defined here
#

class PluginInterface(MainMenuPlugin):
    """
    Plugin to shutdown Freevo from the main menu
    """

    def __init__(self, *args):
        MainMenuPlugin.__init__(self, *args)

    def items(self, parent):
        return [ ShutdownItem(parent) ]
