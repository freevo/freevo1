# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Automated Shutdown
# -----------------------------------------------------------------------
# $Id$
#
# Author: rvpaasen@t3i.nl
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
logger = logging.getLogger("freevo.plugins.autoshutdown")


import os
import time
import sys
import glob
import commands
import config
import plugin
import menu
import event as em
from item import Item
from gui import ConfirmBox
from gui.AlertBox import AlertBox
from tv.record_client import RecordClient
from plugins.shutdown import ShutdownModes, shutdown

recordclient = RecordClient()


class ExInternalError: pass

class ExNoRecordServer(Exception): pass

class ExRecordServerRemote(Exception): pass

class ExNoDefaultWakeup(Exception): pass

class ExIndexNotAvailable(Exception): pass

class ExNoWakeupNeeded(Exception): pass

class ExNextWakeupSoon(Exception): pass

class ExProcessRunning(Exception): pass

class ExRecordingInProgress(Exception): pass


class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to shutdown Freevo from the main menu

    At each shutdown this plugin configures the system to bootup for the
    next recording or a configured default time. The wakeup can be done via
    acpi-alarm or nvram-wakeup. Moreover it adds warning information about
    the next recording to the shutdown confirmation messages. This plugin
    calls the shutdown infrastructure of Freevo, so make sure that the
    following has been configured:
    | SYS_SHUTDOWN_ENABLE = 1
    | SYS_SHUTDOWN_CMD = 'sudo shutdown -h now'
    | SYS_RESTART_CMD = 'sudo shutdown -r now'

    Activate the main menu plugin with:
    | plugin.remove('shutdown')
    | plugin.activate('autoshutdown',level=90)

    Activate the companion timer plugin (optional):
    | plugin.activate('autoshutdown.autoshutdowntimer')

    -- autoshutdown menu item configuration --

    AUTOSHUTDOWN_CONFIRM:
    Set to True to popup dialog boxes for confirmation. This applies to
    menu plugin only, not to the autoshutdowntimer.
    | AUTOSHUTDOWN_CONFIRM = True

    -- autoshutdown timer configuration --

    AUTOSHUTDOWN_TIMER_TIMEOUT:
    Set the timeout in minutes after which the system is shutdown. The
    allowed idle time and the running processes (see below) are evaluated
    to determine if a shutdown is allowed. Menu navigation in freevo will
    reset the timer. This applies to autoshutdowntimer plugin only.
    | AUTOSHUTDOWN_TIMER_TIMEOUT = 60

    -- autoshutdown core configuration --

    AUTOSHUTDOWN_PRETEND:
    Set to True to disable the actual shutdown command. Use this when
    configuring and testing the autoshutdown plugin.
    | AUTOSHUTDOWN_PRETEND = False

    AUTOSHUTDOWN_DEFAULT_WAKEUP_TIME:
    Set the default time at which to wakeup if there are no recordings
    scheduled. The time is specified in localtime 24 hour format. Set to
    None to disable a default wakeup time. Use this if a tv guide needs
    to be downloaded an a regular basis.
    | AUTOSHUTDOWN_DEFAULT_WAKEUP_TIME = "13:00"

    AUTOSHUTDOWN_FORCE_DEFAULT_WAKEUP:
    Set to True to always wakeup at the default wakeup time. Set to False to
    only wakeup at the default wakeup time when no recordings are scheduled.
    | AUTOSHUTDOWN_FORCE_DEFAULT_WAKEUP = True

    AUTOSHUTDOWN_WAKEUP_TIME_PAD:
    Amount of pad time (in seconds) to start system boot ahead of the next
    wakeup event so that system will be ready.  Default is 180 (3 minutes).
    | AUTOSHUTDOWN_WAKEUP_TIME_PAD = 180

    AUTOSHUTDOWN_ALLOWED_IDLE_TIME:
    The number of minutes that may be spent idle until the next scheduled
    recording or default wakeup. That is, if the gap between "now" and the
    next recording or default wakeup is less than the allowed idle time then
    a shutdown is not performed but the system is left running. If the period
    from now to the next recording or default wakeup is more than the allowed
    idle time, then the system is shut down and a wakeup is scheduled. Use
    this to reduce the number of shutdown/boot sequences.
    | AUTOSHUTDOWN_ALLOWED_IDLE_TIME = 45

    AUTOSHUTDOWN_WHILE_USER_LOGGED:
    If set to True, the system will automatically shutdown even if someone
    is logged in, as reported by 'who'. Set to False to avoid Freevo to
    shutdown on your face.
    | AUTOSHUTDOWN_WHILE_USER_LOGGED = True

    AUTOSHUTDOWN_PROCESS_LIST:
    List the processes that will prevent an automatic shutdown. If there are
    important programs that should not be interrupted, then add them to this
    list. Set to None if a shutdown is always allowed.
    | AUTOSHUTDOWN_PROCESS_LIST = [
    |   'mencoder','transcode','cdrecord',
    |   'emerge','tvgids.sh','tv_grab','sshd:'
    | ]

    AUTOSHUTDOWN_PROCESS_CHECK:
    Command to check external processes before shutdown (in runtime) and
    prevent the shutdown.
    It can be useful in following cases:
    - to check if an active ssh connection is present;
    - to check if a file is open;
    - to check if a process is in-progress and so on.
    The command should return the exit code
        0   if external processes are running to prevent the shutdown,
        1   if external processes are stopped to allow the shutdown.
    | AUTOSHUTDOWN_PROCESS_LIST = '/home/user/bin/freevoshutdown_check'

    AUTOSHUTDOWN_METHOD:
    The wakeup can be done via acpi-alarm or nvram-wakeup. Set to 'acpi' to
    use the acpi method, set to 'nvram' to use nvram.
    | AUTOSHUTDOWN_METHOD = 'nvram'

    The following configures either the acpi or nvram method:

    -- autoshutdown acpi-alarm configuration --

        This method uses the wakeup on alarm function that most BIOSs have.
        The wakeup time is set by a simple:

            "echo 2004-08-02 20:15:00 >/proc/acpi/alarm"

        On most mainbords you will have to ENABLE "Wake on Timer", "Resume
        on Alarm", "RTC Alarm Resume" or similar things for the acpi wakeup
        method to work. If you want to use acpi, you need to create a small
        script:

            !/bin/sh
            echo "$1" >/proc/acpi/alarm

        Note that Freevo needs to run this with root privilege.
        | AUTOSHUTDOWN_ACPI_CMD = "sudo /PATH/TO/set_acpi.sh"

    -- autoshutdown nvram-wakeup configuration --

        This method uses the nvram-wakeup utility to write the wakeup alarm to
        the RTC in bios. Read the nvram-wakeup documentation about this topic,
        a working nvram-wakeup configuration is needed. Some bios's need a
        reboot to activate the timer. Note that Freevo needs to run this with
        root privilege.
        | AUTOSHUTDOWN_NVRAM_CMD = "sudo /usr/bin/nvram-wakeup --syslog"
        | AUTOSHUTDOWN_BIOS_NEEDS_REBOOT = True

        If the bios needs a reboot to activate RTC timer, this can be done
        via lilo or grub. Both can shutdown the system immediately after
        rebooting. Set to "GRUB" or "LILO":
        | AUTOSHUTDOWN_BOOT_LOADER = "GRUB"

    -- autoshutdown reboot lilo configuration --

        The following command with will reboot and poweroff the system
        using lilo. Note that Freevo needs to run this with root
        privilege.
        | AUTOSHUTDOWN_LILO_CMD = "/sbin/lilo -R PowerOff"

    -- autoshutdown reboot grub configuration --

        The grub-set-default command will reboot the system into a menu
        entry listed in /boot/gruub/grub.conf. Add a entry in grub.conf
        above all other entries. This entry will perform the shutdown and
        set the default entry for the next boot (probably the next entry,
        entry 1). For example:

            # /boot/grub/grub.conf

            # entry 0
            title=PowerOff
            savedefault 1
            halt

            # entry 1
            title=Gentoo Linux 2.6.29-gentoo-r5
            root (hd0,0)
            kernel /boot/bzImage-2.6.29-gentoo-r5 root=/dev/hda3
            savedefault

        Set the command to run grub-set-default. Note that Freevo needs to
        run this with root privilege.
        | AUTOSHUTDOWN_GRUB_CMD = "sudo /sbin/grub-set-default 0"

        Grub needs to write to /boot/grub/grub.conf. Set the command and
        options to remount the /boot partition writeable. Set to None if
        this is not needed. Note that Freevo needs to run this with root
        privilege.
        | AUTOSHUTDOWN_REMOUNT_BOOT_CMD = "sudo /bin/mount /boot -o remount,rw"

    """

    def config(self):
        return [
            ('SYS_SHUTDOWN_ENABLE', 1, 'enable system shutdown'),
            ('SYS_SHUTDOWN_CMD', 'sudo shutdown -h now', 'shutdown command'),
            ('SYS_RESTART_CMD', 'sudo shutdown -r now', 'reboot command'),
            ('AUTOSHUTDOWN_CONFIRM', True, 'popup dialog boxes'),
            ('AUTOSHUTDOWN_TIMER_TIMEOUT', 30, 'autoshutdowntimer timeout'),
            ('AUTOSHUTDOWN_PRETEND', False, 'pretend shutdown, for testing purpose'),
            ('AUTOSHUTDOWN_DEFAULT_WAKEUP_TIME', '13:00', 'daily wake up time'),
            ('AUTOSHUTDOWN_FORCE_DEFAULT_WAKEUP', True, 'force daily wake up'),
            ('AUTOSHUTDOWN_WAKEUP_TIME_PAD', 180, 'seconds to start ahead of time set'),
            ('AUTOSHUTDOWN_ALLOWED_IDLE_TIME', 45, 'minutes of idle time allowed'),
            ('AUTOSHUTDOWN_WHILE_USER_LOGGED', True, 'shutdown even when someone is logged in'),
            ('AUTOSHUTDOWN_PROCESS_LIST', [], 'list of processes that prevent a shutdown'),
            ('AUTOSHUTDOWN_PROCESS_CHECK', '/home/user/bin/freevoshutdown_check',
                'command to check external processes before shutdown'),
            ('AUTOSHUTDOWN_METHOD', None, 'acpi or nvram (or None to disable)'),
            ('AUTOSHUTDOWN_ACPI_CMD', 'sudo /path/to/set_acpi.sh', 'acpi wakeup command'),
            ('AUTOSHUTDOWN_NVRAM_CMD', 'sudo /usr/bin/nvram-wakeup --syslog', 'nvram wakeup command'),
            ('AUTOSHUTDOWN_BIOS_NEEDS_REBOOT', False, 'reboot to program RTC timer'),
            ('AUTOSHUTDOWN_BOOT_LOADER', None, 'lilo or grub (or None to disable)'),
            ('AUTOSHUTDOWN_LILO_CMD', 'sudo /sbin/lilo -R PowerOff', 'lilo command'),
            ('AUTOSHUTDOWN_GRUB_CMD', 'sudo /sbin/grub-set-default 0', 'grub command'),
            ('AUTOSHUTDOWN_REMOUNT_BOOT_CMD', 'sudo /bin/mount /boot -o remount,rw', 'remount command'),
        ]


    def items(self, parent):
        logger.log( 9, 'items(parent=%r)', parent)
        return [ ShutdownMenuItem(parent) ]



class ShutdownMenuItem(Item):
    def __init__(self, parent=None):
        logger.log( 9, 'ShutdownMenuItem.__init__(parent=%r)', parent)
        Item.__init__(self, parent, skin_type='shutdown')
        self.idletimer = plugin.getbyname('autoshutdowntimer')


    def message_check(self, wakeup=False):
        logger.log( 9, 'message_check(wakeup=%r)', wakeup)
        try:
            is_shutdown_allowed()
        except ExRecordingInProgress:
            msg = _('A recording is in progress.')
        except ExNextWakeupSoon:
            if (wakeup):
                msg = _('Would wakeup again within %d minutes.' % int(config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME))
            else:
                msg = ''
        except ExProcessRunning:
            msg = _('There are important processes running.')
        else:
            if wakeup:
                try:
                    next = get_next_wakeup()
                except ExNoWakeupNeeded:
                    msg = _('No wakeup scheduled.')
                else:
                    next_msg = Unicode(time.strftime( config.TV_DATETIME_FORMAT, time.localtime(next)))
                    next_min = int((next - time.time()) / 60)
                    msg = _('The next wakeup is scheduled at') + '\n' + next_msg
            else:
                msg = ''
        return msg


    def actions(self):
        logger.log( 9, 'actions()')
        if self.idletimer.ispaused():
            itemname = _('Resume automatic shutdown')
        else:
            itemname = _('Pause automatic shutdown')
        items = [
            (self.confirm_shutdown_wakeup,  _('Shutdown and wakeup')),
            (self.confirm_toggle_timer,     itemname),
            (self.confirm_restart_system,   _('Restart system')),
            (self.confirm_shutdown_system,  _('Shutdown system')),
            (self.confirm_shutdown_freevo,  _('Shutdown freevo')),
        ]
        return items


    def confirm_shutdown_wakeup(self, arg=None, menuw=None):
        logger.log( 9, 'confirm_shutdown_wakeup(arg=%r, menuw=%r)', arg, menuw)
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('SHUTDOWN SYSTEM?')
            info = self.message_check(wakeup=True)
            msg = title + '\n\n' + info
            ConfirmBox(text=msg, handler=self.shutdown_wakeup, default_choice=1).show()
        else:
            self.shutdown_wakeup(arg, menuw)


    def confirm_toggle_timer(self, arg=None, menuw=None):
        logger.log( 9, 'confirm_toggle_timer(arg=%r, menuw=%r)', arg, menuw)
        self.toggle_timer(arg, menuw)


    def confirm_restart_system(self, arg=None, menuw=None):
        logger.log( 9, 'confirm_restart_system(arg=%r, menuw=%r)', arg, menuw)
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('RESTART SYSTEM?')
            info = self.message_check(wakeup=False)
            info = '' if info is None else '\n\n' + info
            msg =  title + '\n' + _('(wakeup disabled)') + info
            ConfirmBox(text=msg, handler=self.restart_system, default_choice=1).show()
        else:
            self.restart_system(arg, menuw)


    def confirm_shutdown_system(self, arg=None, menuw=None):
        logger.log( 9, 'confirm_shutdown_system(arg=%r, menuw=%r)', arg, menuw)
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('SHUTDOWN SYSTEM?')
            info = self.message_check(wakeup=False)
            info = '' if info is None else '\n\n' + info
            msg =  title + '\n' + _('(wakeup disabled)') + info
            ConfirmBox(text=msg, handler=self.shutdown_system, default_choice=1).show()
        else:
            self.shutdown_system(arg, menuw)


    def confirm_shutdown_freevo(self, arg=None, menuw=None):
        logger.log( 9, 'confirm_shutdown_freevo(arg=%r, menuw=%r)', arg, menuw)
        if config.AUTOSHUTDOWN_CONFIRM:
            title = _('SHUTDOWN FREEVO?')
            info = self.message_check(wakeup=False)
            info = '' if info is None else '\n\n' + info
            msg =  title + '\n' + _('(wakeup disabled)') + info
            ConfirmBox(text=msg, handler=self.shutdown_freevo, default_choice=1).show()
        else:
            self.shutdown_freevo(arg, menuw)


    def shutdown_wakeup(self, arg=None, menuw=None):
        logger.log( 9, 'shutdown_wakeup(arg=%r, menuw=%r)', arg, menuw)
        shutdown_action(action=Shutdown.SHUTDOWN_WAKEUP)


    def toggle_timer(self, arg=None, menuw=None):
        logger.log( 9, 'toggle_timer(arg=%r, menuw=%r)', arg, menuw)
        if (self.idletimer.ispaused()):
            newname = _('Pause automatic shutdown')
            self.idletimer.resume()
        else:
            newname = _('Resume automatic shutdown')
            self.idletimer.pause()
        old = menuw.menustack[-1].selected
        pos = menuw.menustack[-1].choices.index(menuw.menustack[-1].selected)
        new = menu.MenuItem(newname, old.function, old.arg, old.type)
        menuw.menustack[-1].choices[pos] = new
        menuw.menustack[-1].selected = menuw.menustack[-1].choices[pos]
        menuw.init_page()
        menuw.refresh()


    def restart_system(self, arg=None, menuw=None):
        logger.log( 9, 'restart_system(arg=%r, menuw=%r)', arg, menuw)
        shutdown_action(action=Shutdown.RESTART_SYSTEM)


    def shutdown_system(self, arg=None, menuw=None):
        logger.log( 9, 'shutdown_system(arg=%r, menuw=%r)', arg, menuw)
        shutdown_action(action=Shutdown.SHUTDOWN_SYSTEM)


    def shutdown_freevo(self, arg=None, menuw=None):
        logger.log( 9, 'shutdown_freevo(arg=%r, menuw=%r)', arg, menuw)
        shutdown_action(action=Shutdown.SHUTDOWN_FREEVO)



class autoshutdowntimer(plugin.DaemonPlugin):
    """
    Plugin to shutdown Freevo automatically with a timer

    This plugin provides a timer which causes a shutdown of the system
    after a certain idle time has passed.

    Activate the companion main menu plugin (optional):
    | plugin.remove('shutdown')
    | plugin.activate('autoshutdown',level=90)

    Activate the timer plugin with:
    | plugin.activate('autoshutdown.autoshutdowntimer')

    In short, after AUTOSHUTDOWN_TIMER_TIMEOUT minutes of idle time the
    system goes down, unless the time until the next recording is less
    than AUTOSHUTDOWN_ALLOWED_IDLE_TIME, or, one of the processed listed
    in AUTOSHUTDOWN_PROCESS_LIST is running.

    In the shutdown menu there is a item to pause/resume the automatic
    shutdown timer. The actual shutdown behaviour (e.g. whether to use
    acpi or nvram) is defined in the autoshutdown plugin.

    """


    def __init__(self):
        logger.log( 9, 'autoshutdowntimer.__init__()')
        plugin.DaemonPlugin.__init__(self)
        self.plugin_name = 'autoshutdowntimer'
        self.event_listener = True
        self.poll_interval = 20
        self.reset()
        self.resume()
        logger.debug('autoshutdown timer initialized')


    def ispaused(self):
        logger.log( 9, 'ispaused()')
        return self.lock


    def pause(self):
        logger.log( 9, 'pause()')
        self.lock = True
        logger.debug('autoshutdown timer paused')


    def resume(self):
        logger.log( 9, 'resume()')
        self.lock = False
        self.reset()
        logger.debug('autoshutdown timer resumed')


    def reset(self):
        logger.log( 9, 'reset()')
        self.idle_base = time.time()
        self.delay = 0
        logger.log( 9, 'autoshutdown timer reset')


    def eventhandler(self, event=None, menuw=None, arg=None):
        logger.log( 9, 'eventhandler(event=%r, menuw=%r, arg=%r)', event, menuw, arg)
        if not self.lock:
            if plugin.isevent(event) != 'IDENTIFY_MEDIA' and event.name != 'SCREENSAVER_START':
                self.reset()
                logger.log( 9, 'timer reset, received event %s', event.name)
        return FALSE


    def poll(self):
        logger.log( 9, 'poll()')
        if not self.lock:
            # calculate passed and remaining time
            tdif = (time.time() - self.idle_base)
            trem = (config.AUTOSHUTDOWN_TIMER_TIMEOUT + self.delay - (tdif/60))

            if not config.AUTOSHUTDOWN_WHILE_USER_LOGGED:
                if len(os.popen('/usr/bin/who').read()) > 4:
                    logger.debug('not shuttng down, someone is logged in')
                    logger.debug('retry in 1 minute')
                    self.delay += 1
                    return

            if (tdif > ((config.AUTOSHUTDOWN_TIMER_TIMEOUT + self.delay) * 60) ):
                try:
                    is_shutdown_allowed()
                except ExRecordingInProgress:
                    logger.debug('not shuttng down, a recording is in progress')
                    logger.debug('retry in 5 minutes')
                    self.delay += 5;
                except ExNextWakeupSoon:
                    logger.debug('not shuttng down, next wakeup is nearby')
                    self.reset();
                except ExProcessRunning:
                    logger.debug('not shuttng down, an external process is running')
                    logger.debug('retry in 5 minutes')
                    self.delay += 5;
                else:
                    logger.debug('Shutdown issued by autoshutdown timer!')
                    shutdown_action(action=Shutdown.SHUTDOWN_WAKEUP)
            else:
                logger.log( 9, 'idle for %d seconds, %d minutes remaining', tdif, trem)



class Shutdown:

    SHUTDOWN_WAKEUP, RESTART_SYSTEM, SHUTDOWN_SYSTEM, SHUTDOWN_FREEVO, IGNORE = range(5)


# ***************************************************************
# PUBLIC HELPER FUNTIONS
# ***************************************************************

def is_shutdown_allowed():
    """
    checks if a shutdown is allowed

    @returns: True or excetion
    @raises ExRecordingInProgress: if there is a recording
    @raises ExNextWakeupSoon: if the next wakeup is nearby
    @raises ExProcessRunning: if there is an important process
    """
    logger.log( 9, 'is_shutdown_allowed()')
    now = time.time()
    try:
        t = __get_scheduled_recording(0)
    except ExIndexNotAvailable:
        t = now + (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60) + 1
    except ExNoRecordServer:
        t = now + (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60) + 1
    except ExRecordServerRemote:
        t = now + (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60) + 1
    if (t - now < 0):
        raise ExRecordingInProgress
    if ((t - now) <= (config.AUTOSHUTDOWN_ALLOWED_IDLE_TIME*60)):
        raise ExNextWakeupSoon
    if (__check_processes()):
        raise ExProcessRunning
    return True


def get_next_wakeup():
    """
    Calculate the next wakeup time in seconds UTC

    @returns: UTC time of next wakeup
    @raises ExNoWakeupNeeded: if no wakeup needed
    """
    logger.log( 9, 'get_next_wakeup()')
    scheduled_utc_s = 0
    default_utc_s = 0
    now = time.time()
    i = 0
    # find first scheduled recording in the future
    while scheduled_utc_s < now:
        try:
            scheduled_utc_s = __get_scheduled_recording(i)
        except ExNoRecordServer:
            logger.debug('Record server is down')
            break
        except ExRecordServerRemote:
            logger.debug('Record server is remote')
            break
        except ExIndexNotAvailable:
            logger.debug('No more recordings available')
            break
        i = i + 1
    # find next default wakeup
    try:
        default_utc_s = __get_next_default_wakeup()
    except ExNoDefaultWakeup:
        logger.debug('Default wakeup is disabled')
    # test which wakeup time applies
    if (default_utc_s == 0) and (scheduled_utc_s == 0):
        # no default and scheduled wakeups available
        logger.debug('No wakeup time available')
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
        logger.debug('Picked wakeup at %s', time.ctime(wakeup))
    return wakeup


def shutdown_action(action=None):
    """
    schedules a wakeup and shuts down

    @param action: (type Shutdown)
    """
    logger.debug('shutdown_action(action=%r)', action)
    if (action == Shutdown.SHUTDOWN_WAKEUP):
        action = __schedule_wakeup_and_shutdown()

    if config.AUTOSHUTDOWN_PRETEND:
        action = Shutdown.IGNORE

    if (action == Shutdown.RESTART_SYSTEM):
        shutdown(menuw=None, mode=ShutdownModes.SYSTEM_RESTART)
    elif (action == Shutdown.SHUTDOWN_SYSTEM):
        shutdown(menuw=None, mode=ShutdownModes.SYSTEM_SHUTDOWN)
    elif (action == Shutdown.SHUTDOWN_FREEVO):
        shutdown(menuw=None, mode=ShutdownModes.FREEVO_SHUTDOWN)
    elif (action == Shutdown.IGNORE):
        pass
    else:
        raise ExInternalError
    return


# ***************************************************************
# PRIVATE HELPER FUNTIONS
# ***************************************************************

def __schedule_wakeup_and_shutdown():
    """
    Schedules a wakeup in the bios

    @returns: next action (shutdown or reboot)
    """
    logger.log( 9, '__schedule_wakeup_and_shutdown()')
    try:
        wakeup_utc_s = get_next_wakeup()
    except ExNoWakeupNeeded:
        logger.debug('No wakeup needed, shutting down')
        next_action = Shutdown.SHUTDOWN_SYSTEM
    else:
        # wake up a little earlier because of the time the booting takes
        # set in local_conf.py, freevo_config.py or defaults to 180 seconds (3 minutes)
        wakeup_utc_s = wakeup_utc_s - int(config.AUTOSHUTDOWN_WAKEUP_TIME_PAD)

        # let's see which methode we should use for wakeup
        if config.AUTOSHUTDOWN_METHOD is None:
            logger.debug('No wakeup method set, just shutting down')
            next_action = Shutdown.SHUTDOWN_SYSTEM
        elif config.AUTOSHUTDOWN_METHOD.upper() == 'ACPI':
            cmd = '%s %r' % (config.AUTOSHUTDOWN_ACPI_CMD, time.strftime('%F %H:%M', time.localtime(wakeup_utc_s)))
            logger.debug('Wakeup-command %s', cmd)
            __syscall(cmd, config.AUTOSHUTDOWN_PRETEND)
            next_action = Shutdown.SHUTDOWN_SYSTEM
        elif config.AUTOSHUTDOWN_METHOD.upper() == 'NVRAM':
            cmd = '%s --settime %d' % \
                (config.AUTOSHUTDOWN_NVRAM_CMD, int(wakeup_utc_s))
            ec = __syscall(cmd, config.AUTOSHUTDOWN_PRETEND)
            if ec != 256 and ec != 0:
                logger.error('Wakeup-command command %r failed!', cmd)
                raise ExInternalError
            elif ec == 256 or config.AUTOSHUTDOWN_BIOS_NEEDS_REBOOT:
                # needs a reboot
                if config.AUTOSHUTDOWN_BOOT_LOADER is None:
                    logger.debug('No boot loader set, not shutting down')
                    next_action = Shutdown.IGNORE
                elif config.AUTOSHUTDOWN_BOOT_LOADER.upper() == 'GRUB':
                    if config.AUTOSHUTDOWN_REMOUNT_BOOT_CMD:
                        cmd = config.AUTOSHUTDOWN_REMOUNT_BOOT_CMD
                        __syscall(cmd, config.AUTOSHUTDOWN_PRETEND)
                    cmd = config.AUTOSHUTDOWN_GRUB_CMD
                    __syscall(cmd, config.AUTOSHUTDOWN_PRETEND)
                    logger.debug('Wakeup set, reboot needed')
                    next_action = Shutdown.RESTART_SYSTEM
                elif config.AUTOSHUTDOWN_BOOT_LOADER.upper() == 'LILO':
                    cmd = config.AUTOSHUTDOWN_LILO_CMD
                    __syscall(cmd, config.AUTOSHUTDOWN_PRETEND)
                    logger.debug('Wakeup set, reboot needed')
                    next_action = Shutdown.RESTART_SYSTEM
                else:
                    raise ExInternalError
            else:
                logger.debug('Wakeup set, shutdown needed')
                next_action =  Shutdown.SHUTDOWN_SYSTEM
        else:
            raise ExInternalError

    return next_action


def __is_recordserver_remote():
    """
    See if the recordserver is on this local machine

    @returns: True/False
    """
    logger.log( 9, '__is_recordserver_remote()')
    if len(glob.glob('/var/run/recordserver*.pid')) > 0:
        return False
    elif len(glob.glob('/tmp/recordserver*.pid')) > 0:
        return False
    else:
        return True


updatedFavoritesSchedule = False
def __get_scheduled_recording(index):
    """
    Get the start time of a recording from the reordserver

    @param index: 0..n
    @returns: UTC time of next recording
    @raises ExNoRecordServer: if the recordserver is down
    @raises ExRecordServerRemote: if the recordserver is on a different machine
    @raises ExIndexNotAvailable:
    """
    logger.log( 9, '__get_scheduled_recording(index=%r)', index)
    if __is_recordserver_remote():
        raise ExRecordServerRemote
    try:
        # updateFavoritesScheduleNow is very expensive
        if hasattr(config, 'AUTOSHUTDOWN_UPDATE_FAVORITES') and config.AUTOSHUTDOWN_UPDATE_FAVORITES:
            global updatedFavoritesSchedule
            if not updatedFavoritesSchedule:
                updatedFavoritesSchedule = True
                recordclient.updateFavoritesScheduleNow()
        (status, schedule) = recordclient.getScheduledRecordingsNow()
    except:
        raise ExNoRecordServer
    else:
        if status and schedule != []:
            proglist = schedule

            if (index + 1) > len(proglist):
                raise ExIndexNotAvailable
            else:
                f = lambda a, b: cmp(a.start, b.start)
                proglist.sort(f)
                wakeup = proglist[index].start
                logger.debug('Scheduled recording %d at %s is %s', index, time.ctime(wakeup), proglist[index])
        else:
            raise ExIndexNotAvailable

    # we must take in consideration the TV_RECORD_PADDING_PRE here,
    # otherwise we are to late for the recording
    # and substract it from the next wakeup time
    wakeup -= config.TV_RECORD_PADDING_PRE
    return wakeup


def __get_next_default_wakeup():
    """
    Calculate the next default wakeup time in seconds UTC

    @returns: UTC time of next default wakeup
    @raises ExNoDefaultWakeup: if default wakeup not available
    """
    logger.log( 9, '__get_next_default_wakeup()')
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
        logger.debug('Default wakeup at %s', time.ctime(wakeup))
    return wakeup


def __check_processes():
    """
    checks if important processes are running

    @returns: True/False
    """
    logger.log( 9, '__check_processes()')
    if not config.AUTOSHUTDOWN_PROCESS_LIST and not config.AUTOSHUTDOWN_PROCESS_CHECK:
        return False
    else:
        delimiter='|'
        searchstring = delimiter.join(config.AUTOSHUTDOWN_PROCESS_LIST)
        cmd = 'ps -eo cmd | egrep -v "grep" | egrep "(/|[[:space:]]|^)(%s)($|[[:space:]])" >/dev/null' % searchstring
        result = __syscall(cmd)
        if result == 0:
            logger.debug('external process(es) running')
            return True
        else:
            logger.debug('no external process(es) running')

            if config.AUTOSHUTDOWN_PROCESS_CHECK is not None:
                result = __syscall(config.AUTOSHUTDOWN_PROCESS_CHECK)
                if result == 0:
                    logger.debug('AUTOSHUTDOWN_PROCESS_CHECK: external process(es) running')
                    return True
                else:
                    logger.debug('AUTOSHUTDOWN_PROCESS_CHECK: no external process(es) running')
                    return False


def __syscall(cmd, pretend=False):
    """
    Calls system command and logs it

    @param cmd: command to run
    @param pretend: pretend to run the command
    @returns: result from the system command
    """
    logger.debug('__syscall(cmd=%r, pretend=%r)', cmd, pretend)
    result = 0
    if pretend:
        logger.debug('Pretending syscall: %s', cmd)
    else:
        logger.debug('Executing syscall: %s', cmd)
        result = os.system(cmd)
    return result
