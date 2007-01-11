# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# autoshutdown.py - Automated Shutdown
# -----------------------------------------------------------------------
# $Id$
#
# Author: thehog@t3i.nl
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
import commands
import config
import plugin
import menu
import event as em
from gui import ConfirmBox
from item import Item
from gui.AlertBox import AlertBox
import tv.record_client as record_client

DEBUG = config.DEBUG

# Exception handling classes
class ExInternalError : pass

class ExNoRecordServer(Exception) : pass

class ExNoDefaultWakeup(Exception) : pass

class ExIndexNotAvailable(Exception) : pass

class ExNoWakeupNeeded(Exception) : pass

class ExNextWakeupSoon(Exception) : pass

class ExProcessRunning(Exception) : pass

class ExRecordingInProgress(Exception) : pass

# ***************************************************************
# CLASS PluginInterface
# ***************************************************************
class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to shutdown Freevo from the main menu
    
    At each shutdown this plugin configures the system to 
    bootup for the next recording or a configured default time. 
    The wakeup can be done via acpi-alarm or nvram-wakeup.
    Moreover it adds warning information about the next
    recording to the shutdown confirmation messages.
    
    Activate with:
    plugin.remove('shutdown')
    plugin.activate('autoshutdown',level=90)
    
    Configuration:
    ENABLE_SHUTDOWN_SYS = 1
    AUTOSHUTDOWN_METHOD = 'acpi|nvram'
    AUTOSHUTDOWN_WAKEUP_CMD = PATH/TO/THE/WAKEUP_SCRIPT
    AUTOSHUTDOWN_DEFAULT_WAKEUP_TIME = "13:00"
    AUTOSHUTDOWN_FORCE_DEFAULT_WAKEUP = True
    
    The wakeup methode can be either nvram or acpi.
        
    NVRAM:
    If you want to use nvram-wakeup, 
    you will need a working nvram configuration first.
    (This plugin can deal automatically with the often needed reboot).
    Put the path to nvram-wakeup in AUTOSHUTDOWN_WAKEUP_CMD. 
    
    More variables:
    AUTOSHUTDOWN_NVRAM_OPT = "--syslog"
    AUTOSHUTDOWN_BIOS_NEEDS_REBOOT = True
    
    Your boot loader can be either GRUB or LILO:
    AUTOSHUTDOWN_BOOT_LOADER = "GRUB|LILO"
        
    AUTOSHUTDOWN_REMOUNT_BOOT_CMD = "/bin/mount"
    AUTOSHUTDOWN_REMOUNT_BOOT_OPT = "/boot -o remount,rw"
    AUTOSHUTDOWN_GRUB_CMD = "/sbin/grub-set-default 0"
    AUTOSHUTDOWN_GRUB_OPT = "0"
    AUTOSHUTDOWN_LILO_CMD = "/sbin/lilo"
    AUTOSHUTDOWN_LILO_OPT = "-R PowerOff"
    
    ACPI:
    If you want to use acpi instead, you need to create a small script:
    
    !/bin/sh
    ##############################   
    #acpi_wakeup.sh
    ##############################
    echo "$1" >/proc/acpi/alarm   
    
    and put its path in AUTOSHUTDOWN_WAKEUP_CMD. 
    You have to be root or use sudo for this to work.    
    
    """
    
    def items(self, parent):
        return [ ShutdownMenuItem(parent) ]
   

# ***************************************************************
# CLASS ShutdownMenuItem
# ***************************************************************
class ShutdownMenuItem(Item):
    def __init__(self, parent=None):
        Item.__init__(self, parent, skin_type='shutdown')
        self.idletimer = plugin.getbyname('autoshutdowntimer')

    # -----------------------------------------------------------
    # TEXT FORMATTING
    # -----------------------------------------------------------
    def message_check(self, wakeup=False):
        try:
            is_shutdown_allowed()
        except ExRecordingInProgress:
            msg = _("A recording is in progress.")
        except ExNextWakeupSoon:
            if (wakeup):
                msg = _("Would wakeup again within %d minutes." % int(config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME))
            else:
                msg = ""
        except ExProcessRunning:
            msg = _("There are important processes running.")
        else:
            if wakeup:
                try:
                    next = get_next_wakeup()
                except ExNoWakeupNeeded:
                    msg = _("No wakeup scheduled.")
                else:
                    next_msg = Unicode(time.strftime( config.TV_DATETIMEFORMAT, time.localtime(next)))
                    next_min = int((next - time.time()) / 60)
                    msg = _("The next wakeup is scheduled at") + "\n" + next_msg
            else:
                msg = ""
        return msg


    # -----------------------------------------------------------
    # ACTIONS
    # -----------------------------------------------------------
    def actions(self):
        if (self.idletimer.ispaused()):
            itemname = _('Resume automatic shutdown')
        else:
            itemname = _('Pause automatic shutdown')
        items = [
            (self.confirm_shutdown_wakeup,  _('Shutdown and wakeup') ),
            (self.confirm_toggle_timer,         itemname ),
            (self.confirm_restart_system,   _('Restart system') ),
            (self.confirm_shutdown_system,  _('Shutdown system') ),
            (self.confirm_shutdown_freevo,  _('Shutdown freevo') ),
        ]
        return items


    # -----------------------------------------------------------
    # CONFIRMATION
    # -----------------------------------------------------------
    def confirm_shutdown_wakeup(self, arg=None, menuw=None):
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('SHUTDOWN SYSTEM?')
            info = self.message_check(wakeup=True)
            msg = title + "\n\n" + info
            ConfirmBox(text=msg, handler=self.shutdown_wakeup, default_choice=1).show()
        else:
            self.shutdown_wakeup(arg, menuw)


    def confirm_toggle_timer(self, arg=None, menuw=None):
        self.toggle_timer(arg, menuw)


    def confirm_restart_system(self, arg=None, menuw=None):
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('RESTART SYSTEM?')
            info = self.message_check(wakeup=False)
            if (info == None):
                info = ""
            else:
                info = "\n\n" + info
            msg =  title + "\n" + _("(wakeup disabled)") + info
            ConfirmBox(text=msg, handler=self.restart_system, default_choice=1).show()
        else:
            self.restart_system(arg, menuw)


    def confirm_shutdown_system(self, arg=None, menuw=None):
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('SHUTDOWN SYSTEM?')
            info = self.message_check(wakeup=False)
            if (info == None):
                info = ""
            else:
                info = "\n\n" + info
            msg =  title + "\n" + _("(wakeup disabled)") + info
            ConfirmBox(text=msg, handler=self.shutdown_system, default_choice=1).show()
        else:
            self.shutdown_system(arg, menuw)


    def confirm_shutdown_freevo(self, arg=None, menuw=None):
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('SHUTDOWN FREEVO?')
            info = self.message_check(wakeup=False)
            if (info == None):
                info = ""
            else:
                info = "\n\n" + info
            msg =  title + "\n" + _("(wakeup disabled)") + info
            ConfirmBox(text=msg, handler=self.shutdown_freevo, default_choice=1).show()
        else:
            self.shutdown_freevo(arg, menuw)


    # -----------------------------------------------------------
    # ACTIONS
    # -----------------------------------------------------------
    def shutdown_wakeup(self, arg=None, menuw=None):
        shutdown_action(action=Shutdown.SHUTDOWN_WAKEUP)


    def toggle_timer(self, arg=None, menuw=None):
        if (self.idletimer.ispaused()):
            newname = _('Pause automatic shutdown')
            self.idletimer.resume()
        else:
            newname = _('Resume automatic shutdown')
            self.idletimer.pause()
        old = menuw.menustack[-1].selected
        pos = menuw.menustack[-1].choices.index(menuw.menustack[-1].selected)
        new = menu.MenuItem(newname, old.function, old.arg, old.type)
#       new.image = old.image
#       if hasattr(old, 'display_type'):
#           new.display_type = old.display_type
        menuw.menustack[-1].choices[pos] = new
        menuw.menustack[-1].selected = menuw.menustack[-1].choices[pos]
        menuw.init_page()
        menuw.refresh()
    def restart_system(self, arg=None, menuw=None):
        shutdown_action(action=Shutdown.RESTART_SYSTEM)


    def shutdown_system(self, arg=None, menuw=None):
        shutdown_action(action=Shutdown.SHUTDOWN_SYSTEM)


    def shutdown_freevo(self, arg=None, menuw=None):
        shutdown_action(action=Shutdown.SHUTDOWN_FREEVO)


# ***************************************************************
# CLASS autoshutdowntimer
# ***************************************************************
class autoshutdowntimer(plugin.DaemonPlugin):
    """
    Plugin to shutdown Freevo automatically with a timer
    
    This plugin provides a timer which causes a shutdown of the system
    after a certain idle time has passed. 
    
    Activate with:
    plugin.activate('autoshutdown.autoshutdowntimer')    
    
    Variables:
    AUTOSHUTDOWN_TIMER_TIMEOUT=30
    AUTOSHUTDOWN_ALLOWED_IDLE_TIME = 15
        
    After AUTOSHUTDOWN_TIMER_TIMEOUT minutes of idle time the system goes down,
    unless the time until the next recording is 
    less than AUTOSHUTDOWN_ALLOWED_IDLE_TIME.
    
    Moreover one can define a list of external commands,
    which freevo should check for before shutting down the 
    system. If one of these commands is running,
    the shutdown is stopped.
    
    AUTOSHUTDOWN_PROCESS_LIST = ['mplayer', 'tv_grab']  
    
    In the shutdown menu there is a item to pause/resume
    the automatic shutdown.
          
    """


    def __init__(self):
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'autoshutdowntimer'
        self.event_listener = True
        # poll interval in 1/100 second
        self.poll_interval = 2000
        self.reset()
        self.resume()
        _debug_("autoshutdown timer initialized")


    def ispaused(self):
        return self.lock


    def pause(self):
        self.lock = True
        _debug_("autoshutdown timer paused")


    def resume(self):
        self.lock = False
        self.reset()
        _debug_("autoshutdown timer resumed")


    def reset(self):
        self.idle_base = time.time()
        self.delay = 0
        _debug_("autoshutdown timer reset")


    def eventhandler(self, event = None, menuw=None, arg=None):
        if not self.lock:
            if not event.name == 'IDENTIFY_MEDIA' and not event.name == 'SCREENSAVER_START':
                self.reset()
                _debug_("timer reset, received event %s" % event.name)
        return FALSE


    def poll(self):
        if not self.lock:
            # calculate passed and remaining time
            tdif = (time.time() - self.idle_base)
            trem = (config.AUTOSHUTDOWN_TIMER_TIMEOUT + self.delay - (tdif/60))

            if not config.AUTOSHUTDOWN_WHILE_USER_LOGGED:
                if len(os.popen("/usr/bin/who").read()) > 4:
                    _debug_("not shuttng down, someone is logged in")
                    _debug_("retry in 1 minute")
                    self.delay += 1
                    return

            if (tdif > ((config.AUTOSHUTDOWN_TIMER_TIMEOUT + self.delay) * 60) ):
                try:
                    is_shutdown_allowed()
                except ExRecordingInProgress:
                    _debug_("not shuttng down, a recording is in progress")
                    _debug_("retry in 5 minutes")
                    self.delay += 5;
                except ExNextWakeupSoon:
                    _debug_("not shuttng down, next wakeup is nearby")
                    self.reset();
                except ExProcessRunning:
                    _debug_("not shuttng down, an external process is running")
                    _debug_("retry in 5 minutes")
                    self.delay += 5;
                else:
                    _debug_("Shutdown issued by autoshutdown timer!")
                    shutdown_action(action=Shutdown.SHUTDOWN_WAKEUP)
            else:
                _debug_("idle for %d seconds, %d minutes remaining" % (tdif, trem))


# ***************************************************************
# CLASS SHUTDOWN
# ***************************************************************
class Shutdown:
    SHUTDOWN_WAKEUP, RESTART_SYSTEM, SHUTDOWN_SYSTEM, SHUTDOWN_FREEVO, IGNORE  = range(5)


# ***************************************************************
# PUBLIC HELPER FUNTIONS
# ***************************************************************
# -----------------------------------------------------------
# is_shutdown_allowed
# checks if a shutdown is allowed
# -----------------------------------------------------------
# Input:    None
# Result:   True or excetion
# Raises:   ExRecordingInProgress if there is a recording
#           ExNextWakeupSoon if the next wakeup is nearby
#           ExProcessRunning if there is an important process
# -----------------------------------------------------------
def is_shutdown_allowed():
    now = time.time()
    try:
        t = __get_scheduled_recording(0)
    except ExIndexNotAvailable:
        t = now + (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60) + 1
    except ExNoRecordServer:
        t = now + (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60) + 1
    if (t - now < 0):
        raise ExRecordingInProgress
    if ((t - now) <= (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60)):
        raise ExNextWakeupSoon
    if (__check_processes()):
        raise ExProcessRunning
    return True


# -----------------------------------------------------------
# get_next_wakeup
# Calculate the next wakeup time in seconds UTC
# -----------------------------------------------------------
# Input:    None
# Result:   UTC time of next wakeup
# Raises:   ExNoWakeupNeeded if no wakeup needed
# -----------------------------------------------------------
def get_next_wakeup():
    scheduled_utc_s = 0
    default_utc_s = 0
    now = time.time()
    i = 0
    # find first scheduled recording in the future
    while scheduled_utc_s < now:
        try:
            scheduled_utc_s = __get_scheduled_recording(i)
        except ExNoRecordServer:
            _debug_("Record serer is down")
            break
        except ExIndexNotAvailable:
            _debug_("No more recordings available")
            break
        i = i + 1
    # find next default wakeup
    try:
        default_utc_s = __get_next_default_wakeup()
    except ExNoDefaultWakeup:
            _debug_("Default wakeup is disabled")
    # test which wakeup time applies
    if (default_utc_s == 0) and (scheduled_utc_s == 0):
            # no default and scheduled wakeups available
            _debug_("No wakeup time available")
            raise ExNoWakeupNeeded
    elif (default_utc_s > 0) and (scheduled_utc_s > 0):
        # default wakeup and scheduled wakeups available
        if config.AUTOSHUTDOWN_FORCE_DEFAULT_WAKEUP and default_utc_s < scheduled_utc_s:
            # forced default wakeup is sooner than scheduled wakeup
            wakeup = default_utc_s
        else:
            # no forced default wakeup or scheduled wakeup is sooner
            wakeup = scheduled_utc_s
    else: # (default_utc_s > 0) xor (scheduled_utc_s > 0):
        # pick the largest one
        wakeup = max(default_utc_s, scheduled_utc_s)
        _debug_("Picked wakeup at %s" % time.ctime(wakeup))
    return wakeup


# -----------------------------------------------------------
# shutdown_action
# schedules a wakeup and shuts down
# -----------------------------------------------------------
# Input:    action (type Shutdown)
# Result:   -
# Raises:   -
# -----------------------------------------------------------
def shutdown_action(action=None):
    if (action == Shutdown.SHUTDOWN_WAKEUP):
        _debug_("shutdown wakeup")
        action = __schedule_wakeup_and_shutdown()
    if (action == Shutdown.RESTART_SYSTEM):
        _debug_("restart system")
        __cleanup_freevo()
        __syscall(config.RESTART_SYS_CMD, config.AUTOSHUTDOWN_PRETEND)
        # wait until the system halts/reboots
        while 1:
            time.sleep(1)
    elif (action == Shutdown.SHUTDOWN_SYSTEM):
        _debug_("shutdown system")
        __cleanup_freevo()
        __syscall(config.SHUTDOWN_SYS_CMD, config.AUTOSHUTDOWN_PRETEND)
        # wait until the system halts/reboots
        while 1:
            time.sleep(1)
    elif (action == Shutdown.SHUTDOWN_FREEVO):
        _debug_("shutdown freevo")
        __cleanup_freevo()
        sys.exit(0)
    elif (action == Shutdown.IGNORE):
        pass
    else:
        raise ExInternalError
    return


# ***************************************************************
# PRIVATE HELPER FUNTIONS
# ***************************************************************
# -----------------------------------------------------------
# __schedule_wakeup
# Schedules a wakeup in the bios
# -----------------------------------------------------------
# Input:    -
# Result:   next action (shutdown or reboot)
# Raises:   -
# -----------------------------------------------------------
def __schedule_wakeup_and_shutdown():
    try:
        wakeup_utc_s = get_next_wakeup()
    except ExNoWakeupNeeded:
        _debug_("No wakeup needed, shutting down")
        if not config.AUTOSHUTDOWN_PRETEND:
            next_action = Shutdown.SHUTDOWN_SYSTEM
        else:
            next_action = Shutdown.IGNORE
    else:
             
        # wake up a little earlier because of the time the booting takes
        # 180 s = 3 min should be enough 
        wakeup_utc_s = wakeup_utc_s - 180
        
        # let's see which methode we should use for wakeup
        if config.AUTOSHUTDOWN_METHOD.upper() == 'ACPI':
            cmd = '%s "%s"' % (config.AUTOSHUTDOWN_WAKEUP_CMD, \
                time.strftime('%F %H:%M', time.localtime(wakeup_utc_s)))
            _debug_(" Wakeup-command %s" %cmd)
            __syscall(cmd) 
            next_action =  Shutdown.SHUTDOWN_SYSTEM
        elif config.AUTOSHUTDOWN_METHOD.upper() == 'NVRAM':
            cmd = "%s %s --settime %d" % (config.AUTOSHUTDOWN_WAKEUP_CMD, \
                config.AUTOSHUTDOWN_NVRAM_OPT, int(wakeup_utc_s))
            ec = __syscall(cmd)
            if ec < 0 and ec > 1:
                _debug_("Wakeup-command command '%s' failed!" % cmd,0)
                raise ExInternalError
            elif ec == 1 or config.AUTOSHUTDOWN_BIOS_NEEDS_REBOOT:
                # needs a reboot
                if config.AUTOSHUTDOWN_BOOT_LOADER.upper() == "GRUB":
                    if config.AUTOSHUTDOWN_REMOUNT_BOOT_CMD:
                        cmd = "%s %s" % (config.AUTOSHUTDOWN_REMOUNT_BOOT_CMD, \
                                         config.AUTOSHUTDOWN_REMOUNT_BOOT_OPT)
                        __syscall(cmd)
                    cmd = config.AUTOSHUTDOWN_GRUB_CMD
                    __syscall(cmd)
                    _debug_("Wakeup set, reboot needed")
                    next_action = Shutdown.RESTART_SYSTEM
                elif config.AUTOSHUTDOWN_BOOT_LOADER.upper() == "LILO":
                    cmd = "%s %s" % (config.AUTOSHUTDOWN_LILO_CMD, \
                                     config.AUTOSHUTDOWN_LILO_OPT)
                    __syscall(cmd)
                    _debug_("Wakeup set, reboot needed")
                    next_action = Shutdown.RESTART_SYSTEM
                else:
                    raise ExInternalError
            else:
                _debug_("Wakeup set, shutdown needed")
                next_action =  Shutdown.SHUTDOWN_SYSTEM
        else:
            raise ExInternalError
            
    return next_action


# -----------------------------------------------------------
# __cleanup_freevo
# Performs necessary actions for freevo shutdown
# -----------------------------------------------------------
# Input:    -
# Result:   -
# Raises:   -
# -----------------------------------------------------------
def __cleanup_freevo():
    import osd
    import plugin
    import rc
    import util.mediainfo
    osd = osd.get_singleton()
    util.mediainfo.sync()
    if not config.HELPER:
        if not osd.active:
            # this function is called from the signal
            # handler, but we are dead already.
            sys.exit(0)
        osd.clearscreen(color=osd.COL_BLACK)
        osd.drawstringframed(
            _('shutting down...'),
            0, 0, osd.width, osd.height,
            osd.getfont(config.OSD_DEFAULT_FONTNAME,
            config.OSD_DEFAULT_FONTSIZE),
            fgcolor=osd.COL_ORANGE,
            align_h='center', align_v='center'
        )
        osd.update()
        time.sleep(0.5)
    # shutdown all daemon plugins
    plugin.shutdown()
    # shutdown registered callbacks
    rc.shutdown()
    if not config.HELPER:
        # shutdown the screen
        osd.clearscreen(color=osd.COL_BLACK)
        osd.shutdown()


# -----------------------------------------------------------
# __get_scheduled_recording
# Get the start time of a recording from the reordserver
# -----------------------------------------------------------
# Input:    index 0..n
# Result:   UTC time of next recording
# Raises:   ExNoRecordServer if the recordserver is down
#           ExIndexNotAvailable
# -----------------------------------------------------------
def __get_scheduled_recording(index):
    try:
        #(result, response) = record_client.updateFavoritesSchedule()
        (result, schedule) = record_client.getScheduledRecordings()
    except:
        raise ExNoRecordServer
    else:
        scheduled_programs = []
        if result > 0:
            proglist = schedule.getProgramList().values()
            if ((index + 1) > len(proglist) ):
                raise ExIndexNotAvailable
            else:
                f = lambda a, b: cmp(a.start, b.start)
                proglist.sort(f)
                wakeup = proglist[index].start
                _debug_("Scheduled recording %d at %s is %s" % (index, \
                        time.ctime(wakeup), proglist[index]))
        else:
            raise ExIndexNotAvailable
    
    # we must take in consideration the TV_RECORD_PADDING_PRE here, 
    # otherwise we are to late for the recording
        
    # try if the user configured some paddings
    try:
        pre_padding = config.TV_RECORD_PADDING_PRE
    except:
        pre_padding = 0    
    try:
        padding = config.TV_RECORD_PADDING
    except:
        padding = 0   
    # take the longer padding    
    if pre_padding < padding:
        pre_padding = padding
    # and substract it from the next wakeup time
    wakeup = wakeup - pre_padding       
    return wakeup


# -----------------------------------------------------------
# __get_next_default_wakeup
# Calculate the next default wakeup time in seconds UTC
# -----------------------------------------------------------
# Input:    None
# Result:   UTC time of next default wakeup
# Raises:   ExNoDefaultWakeup if default wakeup not available
# -----------------------------------------------------------
def __get_next_default_wakeup():
    if not config.AUTOSHUTDOWN_DEFAULT_WAKEUP_TIME:
        raise ExNoDefaultWakeup
    else:
        # get local time in seconds
        today_loc_t = time.localtime()
        today_loc_s = time.mktime(today_loc_t)
        # split default time in hour and minute parts
        def_wakeup_loc_t = config.AUTOSHUTDOWN_DEFAULT_WAKEUP_TIME.split(':')
        def_wakeup_loc_t[0] = int(def_wakeup_loc_t[0])
        def_wakeup_loc_t[1] = int(def_wakeup_loc_t[1])
        # calculate the default wakeup time in utc seconds
        # test def_wakeup against current local time
        if ((def_wakeup_loc_t[0]*60 + def_wakeup_loc_t[1]) < (today_loc_t[3]*60 + today_loc_t[4])):
            # def_wakeup is in the past; add a day
            next_def_loc_t = (
                today_loc_t[0], today_loc_t[1], today_loc_t[2], def_wakeup_loc_t[0] + 24,
                def_wakeup_loc_t[1], 0, today_loc_t[6], today_loc_t[7], today_loc_t[8]
            )
        else:
            # def_wakeup is in the future
            next_def_loc_t = (
                today_loc_t[0], today_loc_t[1], today_loc_t[2], def_wakeup_loc_t[0],
                def_wakeup_loc_t[1], 0, today_loc_t[6], today_loc_t[7], today_loc_t[8]
            )
        # convert next_def to utc seconds
        wakeup = time.mktime(next_def_loc_t)
        _debug_("Default wakeup at %s" % time.ctime(wakeup))
    return wakeup


# -----------------------------------------------------------
# __check_processes
# checks if important processes are running
# -----------------------------------------------------------
# Input:    None
# Result:   True/False
# Raises:   -
# -----------------------------------------------------------
def __check_processes():
    if not config.AUTOSHUTDOWN_PROCESS_LIST:
        return False
    else:
        delimiter='|'
        searchstring = delimiter.join(config.AUTOSHUTDOWN_PROCESS_LIST)
        cmd = 'ps -eo cmd | egrep -v "grep" | egrep "(/|[[:space:]]|^)(%s)($|[[:space:]])"' % searchstring
        result = __syscall(cmd)
        if (result == 0):
            _debug_('external process(es) running')
            return True
        else:
            _debug_('no external process(es) running')
            return False


# -----------------------------------------------------------
# __syscall
# Calls system command and logs it
# -----------------------------------------------------------
# Input:    cmd, pretend
# Result:   -
# Raises:   -
# -----------------------------------------------------------
def __syscall(cmd, pretend=False):
    result = 0
    if pretend:
        _debug_("Pretending syscall: %s" % cmd)
    else:
        _debug_("Executing syscall: %s" % cmd)
        result = os.system(cmd)
    return result
