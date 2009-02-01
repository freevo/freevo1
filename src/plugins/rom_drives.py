# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo identify media/automount removable media plugin
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


import time, os
from fcntl import ioctl
import re
import threading
import thread
import string
import copy
import traceback
from struct import *
import array

import config
import util.mediainfo
import rc
#from util.misc import print_upper_execution_stack

from benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL


try:
    from CDROM import *
    # test if CDROM_DRIVE_STATUS is there
    # (for some strange reason, this is missing sometimes)
    CDROM_DRIVE_STATUS
except:
    if os.uname()[0] == 'FreeBSD':
        # FreeBSD ioctls - there is no CDROM.py...
        CDIOCEJECT = 0x20006318
        CDIOCCLOSE = 0x2000631c
        CDIOREADTOCENTRYS = 0xc0086305
        CD_LBA_FORMAT = 1
        CD_MSF_FORMAT = 2
        CDS_NO_DISC = 1
        CDS_DISC_OK = 4
    else:
        # see linux/cdrom.h and Documentation/ioctl/cdrom.txt
        CDROMEJECT           = 0x5309
        CDROM_GET_CAPABILITY = 0x5331
        CDROMCLOSETRAY       = 0x5319  # pendant of CDROMEJECT
        CDROM_SET_OPTIONS    = 0x5320  # Set behavior options
        CDROM_CLEAR_OPTIONS  = 0x5321  # Clear behavior options
        CDROM_SELECT_SPEED   = 0x5322  # Set the CD-ROM speed
        CDROM_SELECT_DISC    = 0x5323  # Select disc (for juke-boxes)
        CDROM_MEDIA_CHANGED  = 0x5325  # Check is media changed
        CDROM_DRIVE_STATUS   = 0x5326  # Get tray position, etc.
        CDROM_DISC_STATUS    = 0x5327  # Get disc type, etc.
        CDROM_CHANGER_NSLOTS = 0x5328  # Get number of slots
        CDROM_LOCKDOOR       = 0x5329  # lock or unlock door
        CDROM_DEBUG          = 0x5330  # Turn debug messages on/off
        CDROM_GET_CAPABILITY = 0x5331  # get capabilities
        # CDROM_DRIVE_STATUS
        CDS_NO_INFO = 0
        CDS_NO_DISC = 1
        CDS_TRAY_OPEN = 2
        CDS_DRIVE_NOT_READY = 3
        CDS_DISC_OK = 4
        # capability flags
        CDC_CLOSE_TRAY       = 0x1     # caddy systems _can't_ close
        CDC_OPEN_TRAY        = 0x2     # but _can_ eject.
        CDC_LOCK             = 0x4     # disable manual eject
        CDC_SELECT_SPEED     = 0x8     # programmable speed
        CDC_SELECT_DISC      = 0x10    # select disc from juke-box
CDC_MO_DRIVE         = 0x40000
CDC_MRW              = 0x80000
CDC_MRW_W            = 0x100000
CDC_RAM              = 0x200000
# CDROM_DISC_STATUS
CDS_AUDIO = 100
CDS_DATA_1 = 101
CDS_DATA_2 = 102
CDS_XA_2_1 = 103
CDS_XA_2_2 = 104
CDS_MIXED = 105


import config
import util
import rc
import plugin
import video

from event import *
from directory import DirItem
from gui import PopupBox
from item import Item
from audio import AudioDiskItem
from audio import AudioItem
from video import VideoItem

LABEL_REGEXP = re.compile("^(.*[^ ]) *$").match


# Identify_Thread
im_thread = None


@benchmark(benchmarking, benchmarkcall)
def init():
    """
    create a list of media objects and start the Identify_Thread
    """
    # Add the drives to the config.removable_media list. There doesn't have
    # to be any drives defined.
    if config.ROM_DRIVES is not None:
        for i in range(len(config.ROM_DRIVES)):
            (dir, device, name) = config.ROM_DRIVES[i]
            media = RemovableMedia(mountdir=dir, devicename=device, drivename=name)
            cdc = media.get_capabilities()
            media.log_capabilities(cdc)
            media.get_drive_status()
            media.log_drive_status(media.cds)
            media.log_disc_status(media.cis)
            # close the tray without popup message
            media.close_tray()
            config.REMOVABLE_MEDIA.append(media)

    # Remove the ROM_DRIVES member to make sure it is not used by legacy code!
    del config.ROM_DRIVES

    # Start identifymedia thread
    global im_thread
    im_thread = Identify_Thread()
    im_thread.setDaemon(1)
    im_thread.start()


@benchmark(benchmarking, benchmarkcall)
def shutdown():
    """
    shut down the Identify_Thread
    """
    print 'shutdown()'
    global im_thread
    if im_thread.isAlive():
        _debug_('stopping Identify_Thread', 2)
        print 'stopping Identify_Thread'
        im_thread.stop = True
        while im_thread.isAlive():
            time.sleep(0.1)
        print 'stopped Identify_Thread'


class autostart(plugin.DaemonPlugin):
    """
    Plugin to autostart if a new medium is inserted while Freevo shows
    the main menu
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        """
        load the plugin and start the thread
        """
        plugin.DaemonPlugin.__init__(self)
        global im_thread
        if not im_thread:
            init()


    @benchmark(benchmarking, benchmarkcall)
    def eventhandler(self, event=None, menuw=None, arg=None):
        """
        eventhandler to handle the IDENTIFY_MEDIA plugin event and the
        EJECT event
        """
        global im_thread

        # if we are at the main menu and there is an IDENTIFY_MEDIA event,
        # try to autorun the media
        if plugin.isevent(event) == 'IDENTIFY_MEDIA':
            (media, state) = event.arg
            if not menuw:
                return False
            if len(menuw.menustack) != 1:
                return False
            if state != CDS_DISC_OK:
                return False

            if media.item:
                media.item.parent = menuw.menustack[0].selected
            if media.item and media.item.actions():
                if media.type == 'audio':
                    # disc marked as audio, play everything
                    if media.item.type == 'dir':
                        media.item.play_recursive(menuw=menuw)
                    elif media.item.type == 'audiocd':
                        media.item.play(menuw=menuw)
                    else:
                        media.item.actions()[0][0](menuw=menuw)
                elif media.videoitem:
                    # disc has one video file, play it
                    media.videoitem.actions()[0][0](menuw=menuw)
                else:
                    # ok, do whatever this item has to offer
                    media.item.actions()[0][0](menuw=menuw)
            else:
                menuw.refresh()
            return True

        # Handle the EJECT key for the main menu
        elif event == EJECT and len(menuw.menustack) == 1:

            # Are there any drives defined?
            if config.REMOVABLE_MEDIA:
                # The default is the first drive in the list
                media = config.REMOVABLE_MEDIA[0]
                media.move_tray(direction='toggle')
                return True

    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        shutdown()


class rom_items(plugin.MainMenuPlugin):
    """
    Plugin to add the rom drives to a main menu. This can be the global main menu
    or most likely the video/audio/image/games main menu
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        """
        load the plugin and start the thread
        """
        plugin.MainMenuPlugin.__init__(self)
        global im_thread
        if not im_thread:
            init()

    @benchmark(benchmarking, benchmarkcall)
    def items(self, parent):
        """
        return the list of rom drives
        """
        items = []
        for media in config.REMOVABLE_MEDIA:
            if media.item:
                if parent.display_type == 'video' and media.videoitem:
                    m = media.videoitem
                    # FIXME: how to play video is maybe subdirs?

                else:
                    if media.item.type == 'dir':
                        media.item.display_type = parent.display_type
                        media.item.skin_display_type = parent.display_type
                        media.item.create_metainfo()
                    m = media.item

            else:
                m = Item(parent)
                m.name = _('Drive %s (no disc)') % media.drivename
                m.type = media.type
                m.media = media
                media.item = m

            m.parent = parent
            m.eventhandler_plugins.append(self.items_eventhandler)
            items.append(m)

        return items


    @benchmark(benchmarking, benchmarkcall)
    def items_eventhandler(self, event, item, menuw):
        """
        handle EJECT for the rom drives
        """
        if event == EJECT and item.media and menuw and \
           menuw.menustack[1] == menuw.menustack[-1]:
            item.media.move_tray(direction='toggle')
            return True
        return False


class RemovableMedia:
    """
    Object about one drive
    """
    @benchmark(benchmarking, benchmarkcall)
    def __init__(self, mountdir='', devicename='', drivename=''):
        # This is read-only stuff for the drive itself
        _debug_('RemovableMedia.__init__(mountdir=%r, devicename=%r, drivename=%r)' % \
            (mountdir, devicename, drivename),2)
        self.mountdir = mountdir
        self.devicename = devicename
        self.drivename = drivename
        self.mount_ref_count = 0

        # Dynamic stuff
        self.cdc       = 0
        self.cis       = CDS_NO_INFO
        self.cds       = CDS_NO_INFO
        self.cds_changed = False

        self.tray_open = False
        self.drive_status = self.get_drive_status()
        self.disc_status = self.cis

        self.id        = ''
        self.label     = ''
        self.item      = None
        self.videoitem = None
        self.type      = 'empty_cdrom'
        self.cached    = False

        self.can_close = False
        self.can_eject = False
        self.can_select_speed = False


    @benchmark(benchmarking, benchmarkcall)
    def is_tray_open(self):
        """
        return tray status
        """
        return self.get_drive_status() == CDS_TRAY_OPEN


    @benchmark(benchmarking, benchmarkcall)
    def capabilities_text(self, cdc):
        """ the drive capabilities as text"""
        result = []
        result.append('%s CDC_CLOSE_TRAY'     % (cdc & CDC_CLOSE_TRAY     and 'can' or 'can\'t'))
        result.append('%s CDC_OPEN_TRAY'      % (cdc & CDC_OPEN_TRAY      and 'can' or 'can\'t'))
        result.append('%s CDC_LOCK'           % (cdc & CDC_LOCK           and 'can' or 'can\'t'))
        result.append('%s CDC_SELECT_SPEED'   % (cdc & CDC_SELECT_SPEED   and 'can' or 'can\'t'))
        result.append('%s CDC_SELECT_DISC'    % (cdc & CDC_SELECT_DISC    and 'can' or 'can\'t'))
        result.append('%s CDC_MULTI_SESSION'  % (cdc & CDC_MULTI_SESSION  and 'can' or 'can\'t'))
        result.append('%s CDC_MCN'            % (cdc & CDC_MCN            and 'can' or 'can\'t'))
        result.append('%s CDC_MEDIA_CHANGED'  % (cdc & CDC_MEDIA_CHANGED  and 'can' or 'can\'t'))
        result.append('%s CDC_PLAY_AUDIO'     % (cdc & CDC_PLAY_AUDIO     and 'can' or 'can\'t'))
        result.append('%s CDC_RESET'          % (cdc & CDC_RESET          and 'can' or 'can\'t'))
        result.append('%s CDC_DRIVE_STATUS'   % (cdc & CDC_DRIVE_STATUS   and 'can' or 'can\'t'))
        result.append('%s CDC_GENERIC_PACKET' % (cdc & CDC_GENERIC_PACKET and 'can' or 'can\'t'))
        result.append('%s CDC_CD_R'           % (cdc & CDC_CD_R           and 'can' or 'can\'t'))
        result.append('%s CDC_CD_RW'          % (cdc & CDC_CD_RW          and 'can' or 'can\'t'))
        result.append('%s CDC_DVD'            % (cdc & CDC_DVD            and 'can' or 'can\'t'))
        result.append('%s CDC_DVD_R'          % (cdc & CDC_DVD_R          and 'can' or 'can\'t'))
        result.append('%s CDC_DVD_RAM'        % (cdc & CDC_DVD_RAM        and 'can' or 'can\'t'))
        result.append('%s CDC_MO_DRIVE'       % (cdc & CDC_MO_DRIVE       and 'can' or 'can\'t'))
        result.append('%s CDC_MRW'            % (cdc & CDC_MRW            and 'can' or 'can\'t'))
        result.append('%s CDC_MRW_W'          % (cdc & CDC_MRW_W          and 'can' or 'can\'t'))
        result.append('%s CDC_RAM'            % (cdc & CDC_RAM            and 'can' or 'can\'t'))
        return result


    @benchmark(benchmarking, benchmarkcall)
    def log_capabilities(self, cdc):
        """ Write the drive capabilities to the debug log """
        for capability in self.capabilities_text(cdc):
            _debug_('%r %s' % (self.devicename, capability), DINFO)


    @benchmark(benchmarking, benchmarkcall)
    def get_capabilities(self):
        """ Open the CD/DVD drive and read its capabilities """
        _debug_('Getting capabilities for %s (%s)' % (self.drivename, self.devicename), DINFO)
        cdc = 0
        try:
            fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if os.uname()[0] == 'FreeBSD':
                    self.can_close = True
                    self.can_eject = True
                    self.can_select_speed = True
                else:
                    cdc = ioctl(fd, CDROM_GET_CAPABILITY)

                    if cdc & CDC_CLOSE_TRAY:
                        self.can_close = True
                        _debug_('%s can close' % self.drivename, DINFO)

                    if cdc & CDC_OPEN_TRAY:
                        self.can_eject = True
                        _debug_('%s can open' % self.drivename, DINFO)

                    if cdc & CDC_SELECT_SPEED:
                        self.can_select_speed = True
                        _debug_('%s can select speed' % self.drivename, DINFO)
            finally:
                os.close(fd)
        except Exception, e:
            _debug_('opening %r failed: %s"' % (self.devicename, e), DWARNING)
        self.cdc = cdc
        return cdc


    @benchmark(benchmarking, benchmarkcall)
    def drive_status_text(self, cds):
        """ the drive status as text"""
        if   cds == CDS_NO_INFO:         return 'CDS_NO_INFO'
        elif cds == CDS_NO_DISC:         return 'CDS_NO_DISC'
        elif cds == CDS_TRAY_OPEN:       return 'CDS_TRAY_OPEN'
        elif cds == CDS_DRIVE_NOT_READY: return 'CDS_DRIVE_NOT_READY'
        elif cds == CDS_DISC_OK:         return 'CDS_DISC_OK'
        return 'CDS_UNKNOWN %r' % (cds)


    @benchmark(benchmarking, benchmarkcall)
    def disc_status_text(self, cds):
        """ the disc status as text"""
        if   cds == CDS_NO_INFO:         return 'CDS_NO_INFO'
        elif cds == CDS_AUDIO:           return 'CDS_NO_DISC'
        elif cds == CDS_DATA_1:          return 'CDS_DATA_1'
        elif cds == CDS_DATA_2:          return 'CDS_DATA_2'
        elif cds == CDS_XA_2_1:          return 'CDS_XA_2_1'
        elif cds == CDS_XA_2_2:          return 'CDS_XA_2_2'
        elif cds == CDS_MIXED:           return 'CDS_MIXED'
        return 'CDS_UNKNOWN %r' % (cds)


    @benchmark(benchmarking, benchmarkcall)
    def log_disc_status(self, status):
        """ Log the disc status """
        _debug_('%r %s' % (self.devicename, self.disc_status_text(status)), DINFO)


    @benchmark(benchmarking, benchmarkcall)
    def log_drive_status(self, status):
        """ Log the drive status """
        _debug_('%r %s' % (self.devicename, self.drive_status_text(status)), DINFO)


    @benchmark(benchmarking, benchmarkcall)
    def get_drive_status(self):
        """ Open the CD/DVD drive and read its drive status """
        cds = CDS_NO_INFO
        cis = CDS_NO_INFO
        try:
            fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if os.uname()[0] == 'FreeBSD':
                    try:
                        data = array.array('c', '\000'*4096)
                        (address, length) = data.buffer_info()
                        buf = pack('BBHP', CD_MSF_FORMAT, 0, length, address)
                        s = ioctl(fd, CDIOREADTOCENTRYS, buf)
                        cds = CDS_DISC_OK
                    except Exception, e:
                        cds = CDS_NO_DISC
                else:
                    try:
                        if self.cdc & CDC_DRIVE_STATUS:
                            cds = ioctl(fd, CDROM_DRIVE_STATUS)
                            if cds == CDS_DISC_OK:
                                cis = ioctl(fd, CDROM_DISC_STATUS)
                    except Exception, e:
                        _debug_('getting drive status for %r failed: %s' % (self.devicename, e), DWARNING)
                _debug_('drive status for %s (%r:%s) is %s' % \
                    (self.drivename, self.devicename, fd, self.drive_status_text(cds)), 3)
            finally:
                os.close(fd)
        except Exception, e:
            _debug_('opening %r failed: %s"' % (self.devicename, e), DWARNING)
        self.cds_changed = self.cds != cds
        self.cds = cds
        self.cis = cis
        return cds


    @benchmark(benchmarking, benchmarkcall)
    def get_drive_status_changed(self):
        """ has the drive status changed """
        return self.cds_changed


    @benchmark(benchmarking, benchmarkcall)
    def open_tray(self):
        """ Open the drive tray """
        _debug_('Ejecting disc in drive %s' % self.drivename)

        try:
            fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if os.uname()[0] == 'FreeBSD':
                    s = ioctl(fd, CDIOCEJECT, 0)
                else:
                    s = ioctl(fd, CDROMEJECT)
                self.tray_open = True
            finally:
                os.close(fd)
        except Exception, e:
            _debug_('opening %r failed: %s"' % (self.devicename, e), DWARNING)


    @benchmark(benchmarking, benchmarkcall)
    def close_tray(self):
        """ Close the drive tray """
        _debug_('Inserting disc in drive %s' % self.drivename)

        try:
            fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if os.uname()[0] == 'FreeBSD':
                    s = ioctl(fd, CDIOCCLOSE, 0)
                else:
                    s = ioctl(fd, CDROMCLOSETRAY)
                self.tray_open = False
            finally:
                os.close(fd)
        except Exception, e:
            _debug_('opening %r failed: %s"' % (self.devicename, e), DWARNING)


    @benchmark(benchmarking, benchmarkcall)
    def move_tray(self, direction='toggle'):
        """ Move the tray. direction can be toggle/open/close """
        global im_thread
        if direction == 'toggle':
            if self.is_tray_open():
                direction = 'close'
            else:
                direction = 'open'

        if direction == 'open' and self.can_eject:
            pop = PopupBox(text=_('Ejecting disc in drive %s') % self.drivename)
            pop.show()
            if util.is_mounted(self.mountdir):
                self.umount()
                self.mount_ref_count = 0
            self.open_tray()
            pop.destroy()
        elif direction == 'close' and self.can_close:
            pop = PopupBox(text=_('Reading disc in drive %s') % self.drivename)
            pop.show()
            self.close_tray()
            if im_thread:
                im_thread.check_all()
            pop.destroy()


    @benchmark(benchmarking, benchmarkcall)
    def mount(self):
        """ Mount the media """
        _debug_('Mounting disc in drive %s' % self.drivename, 2)
        if self.mount_ref_count == 0:
            util.mount(self.mountdir, force=True)
        self.mount_ref_count += 1
        #print '-----------mount ', self.mountdir, ' ref count ', self.mount_ref_count
        #print_upper_execution_stack()


    @benchmark(benchmarking, benchmarkcall)
    def umount(self):
        """ Mount the media """
        _debug_('Unmounting disc in drive %s' % self.drivename, 2)
        self.mount_ref_count -= 1
        if self.mount_ref_count == 0:
            util.umount(self.mountdir)
        #print '-----------umount ',self.mountdir,' ref count ',self.mount_ref_count
        #print_upper_execution_stack()


    @benchmark(benchmarking, benchmarkcall)
    def is_mounted(self):
        """ Check if the media is mounted (and the consistency of internal data) """
        r = util.is_mounted(self.mountdir)
        o = os.path.ismount(self.mountdir)
        if not o and self.mount_ref_count > 0:
            _debug_('Drive was unmounted out of rom_drives.py: ' + self.mountdir, DWARNING)
            self.mount_ref_count = 0
        if o and self.mount_ref_count == 0:
            _debug_('Drive was mounted out of rom_drives.py: ' + self.mountdir, DWARNING)
            self.mount_ref_count = 1
        if (o and not r) or (not o and r):
            _debug_('Inconsistency regarding the mount status of: ' + self.mountdir, DWARNING)
        return r


    @benchmark(benchmarking, benchmarkcall)
    def shutdown(self):
        shutdown()


class Identify_Thread(threading.Thread):
    """
    Thread to watch the rom drives for changes
    """
    @benchmark(benchmarking, benchmarkcall)
    def identify(self, media, force_rebuild=False):
        """
        Try to find out as much as possible about the disc in the rom drive: title,
        image, play options, ...
        """
        cds = media.get_drive_status()
        #media.log_drive_status(cds)

        # Same as last time? If so we're done
        if media.drive_status == cds:
            #_debug_('status not changed for drive %r' % (media.devicename))
            return

        _debug_('drive_status changed %s -> %s' % (media.drive_status, cds))
        media.drive_status = cds
        media.id           = ''
        media.label        = ''
        media.type         = 'empty_cdrom'
        media.item         = None
        media.videoitem    = None
        media.cached       = False

        # Is there a disc information?
        if media.drive_status == CDS_NO_INFO:
            _debug_('cannot get the drive status for drive %r' % (media.devicename))
            return

        # Is there a disc present?
        if media.drive_status != CDS_DISC_OK:
            _debug_('disc not ready for drive %r' % (media.devicename))
            return

        # try to set the speed
        try:
            fd = os.open(media.devicename, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if media.can_select_speed and config.ROM_SPEED:
                    try:
                        ioctl(fd, CDROM_SELECT_SPEED, config.ROM_SPEED)
                    except Exception, e:
                        _debug_('setting rom speed for %r failed: %s' % (media.devicename, e))

            finally:
                #_debug_('closing %r drive %r' % (fd, media.devicename))
                try:
                    os.close(fd)
                except Exception, e:
                    _debug_('closing %r failed: %s' % (media.devicename, e))
        except Exception, e:
            _debug_('opening %r failed: %s' % (media.devicename, e))
            return


        # if there is a disc, the tray can't be open
        media.tray_open = False
        disc_info = util.mediainfo.disc_info(media, force_rebuild)
        if not disc_info:
            _debug_('no disc information for drive %r' % (media.devicename))
            return

        info = disc_info.discinfo
        if not info:
            _debug_('no info for drive %r' % (media.devicename))
            return

        if info['mime'] == 'audio/cd':
            media.id = disc_id = info['id']
            media.item = AudioDiskItem(disc_id, parent=None, devicename=media.devicename, display_type='audio')
            media.type = 'audio'
            media.item.media = media
            if info['title']:
                media.item.name = info['title']
            media.item.info = disc_info
            _debug_('playing audio in drive %r' % (media.devicename))
            return

        image = title = movie_info = more_info = fxd_file = None

        media.id    = info['id']
        media.label = info['label']
        media.type  = 'cdrom'

        label = info['label']

        # is the id in the database?
        if media.id in video.fxd_database['id']:
            movie_info = video.fxd_database['id'][media.id]
            if movie_info:
                title = movie_info.name
        else: # no? Maybe we can find a label regexp match
            for (re_label, movie_info_t) in video.fxd_database['label']:
                if re_label.match(media.label):
                    movie_info = movie_info_t
                    if movie_info_t.name:
                        title = movie_info.name
                        m = re_label.match(media.label).groups()
                        re_count = 1

                        # found, now change the title with the regexp. E.g.:
                        # label is "bla_2", the label regexp "bla_[0-9]" and the title
                        # is "Something \1", the \1 will be replaced with the first item
                        # in the regexp group, here 2. The title is now "Something 2"
                        for g in m:
                            title=string.replace(title, '\\%s' % re_count, g)
                            re_count += 1
                        break

        if movie_info:
            image = movie_info.image


        # DVD/VCD/SVCD:
        if info['mime'] in ('video/vcd', 'video/dvd'):
            if not title:
                title = media.label.replace('_', ' ').lstrip().rstrip()
                title = '%s [%s]' % (info['mime'][6:].upper(), title)

            if movie_info:
                media.item = copy.copy(movie_info)
            else:
                media.item = VideoItem('', None)
                media.item.image = util.getimage(os.path.join(config.OVERLAY_DIR, 'disc-set', media.id))
            variables = media.item.info.variables
            media.item.info = disc_info
            media.item.info.set_variables(variables)

            media.item.name = title
            media.item.url = info['mime'][6:] + '://'
            media.item.media = media

            media.type = info['mime'][6:]

            media.item.info.mmdata = info
            _debug_('playing video in drive %r' % (media.devicename))
            return

        # Disc is data of some sort. Mount it to get the file info
        util.mount(media.mountdir, force=True)
        try:
            if os.path.isdir(os.path.join(media.mountdir, 'VIDEO_TS')) or \
                   os.path.isdir(os.path.join(media.mountdir, 'video_ts')):
                if force_rebuild:
                    _debug_('Double check without success')
                else:
                    _debug_('Undetected DVD, checking again')
                    media.drive_status = CDS_NO_DISC
                    return self.identify(media, True)

            # Check for movies/audio/images on the disc
            num_video = disc_info['disc_num_video']
            num_audio = disc_info['disc_num_audio']
            num_image = disc_info['disc_num_image']

            video_files = util.match_files(media.mountdir, config.VIDEO_SUFFIX)

            _debug_('video_files=%r' % (video_files,))

            media.item = DirItem(media.mountdir, None, create_metainfo=False)
            media.item.info = disc_info
        finally:
            util.umount(media.mountdir)

        # if there is a video file on the root dir of the disc, we guess
        # it's a video disc. There may also be audio files and images, but
        # they only belong to the movie
        if video_files:
            media.type = 'video'

            # try to find out if it is a series cd
            if not title:
                show_name = ""
                the_same  = 1
                volumes   = ''
                start_ep  = 0
                end_ep    = 0

                video_files.sort(lambda l, o: cmp(l.upper(), o.upper()))

                for movie in video_files:
                    if config.VIDEO_SHOW_REGEXP_MATCH(movie):
                        show = config.VIDEO_SHOW_REGEXP_SPLIT(os.path.basename(movie))

                        if show_name and show_name != show[0]:
                            the_same = 0
                        if not show_name:
                            show_name = show[0]
                        if volumes:
                            volumes += ', '
                        current_ep = int(show[1]) * 100 + int(show[2])
                        if end_ep and current_ep == end_ep + 1:
                            end_ep = current_ep
                        elif not end_ep:
                            end_ep = current_ep
                        else:
                            end_ep = -1
                        if not start_ep:
                            start_ep = end_ep
                        volumes += show[1] + "x" + show[2]

                if show_name and the_same and config.VIDEO_SHOW_DATA_DIR:
                    if end_ep > 0:
                        volumes = '%dx%02d - %dx%02d' % (start_ep / 100, start_ep % 100,
                                                         end_ep / 100, end_ep % 100)
                    k = config.VIDEO_SHOW_DATA_DIR + show_name
                    if os.path.isfile((k + ".png").lower()):
                        image = (k + ".png").lower()
                    elif os.path.isfile((k + ".jpg").lower()):
                        image = (k + ".jpg").lower()
                    title = show_name + ' ('+ volumes + ')'
                    if video.tv_show_information.has_key(show_name.lower()):
                        tvinfo = video.tv_show_information[show_name.lower()]
                        more_info = tvinfo[1]
                        if not image:
                            image = tvinfo[0]
                        if not fxd_file:
                            fxd_file = tvinfo[3]

                elif (not show_name) and len(video_files) == 1:
                    movie = video_files[0]
                    title = os.path.splitext(os.path.basename(movie))[0]

            # nothing found, give up: return the label
            if not title:
                title = label


        # If there are no videos and only audio files (and maybe images)
        # it is an audio disc (autostart will auto play everything)
        elif not num_video and num_audio:
            media.type = 'audio'
            title = '%s [%s]' % (media.drivename, label)

        # Only images? OK than, make it an image disc
        elif not num_video and not num_audio and num_image:
            media.type = 'image'
            title = '%s [%s]' % (media.drivename, label)

        # Mixed media?
        elif num_video or num_audio or num_image:
            media.type = None
            title = '%s [%s]' % (media.drivename, label)

        # Strange, no useable files
        else:
            media.type = None
            title = '%s [%s]' % (media.drivename, label)

        # set the info we have now
        if title:
            media.item.name = title

        if image:
            media.item.image = image

        if more_info:
            media.item.info.set_variables(more_info)

        if fxd_file and not media.item.fxd_file:
            media.item.set_fxd_file(fxd_file)

        # One video in the root dir. This sounds like a disc with one
        # movie on it. Save the information about it and autostart will
        # play this.
        if len(video_files) == 1 and media.item['num_dir_items'] == 0:
            util.mount(media.mountdir)
            try:
                if movie_info:
                    media.videoitem = copy.deepcopy(movie_info)
                else:
                    media.videoitem = VideoItem(video_files[0], None)
            finally:
                util.umount(media.mountdir)
            media.videoitem.media    = media
            media.videoitem.media_id = media.id

            # set the infos we have
            if title:
                media.videoitem.name = title

            if image:
                media.videoitem.image = image

            if more_info:
                media.videoitem.set_variables(more_info)

            if fxd_file:
                media.videoitem.fxd_file = fxd_file

        media.item.media = media
        return


    @benchmark(benchmarking, benchmarkcall)
    def check_all(self):
        """ Check all drives """
        if rc.app():
            # Some app is running, do not scan, it's not necessary
            return

        self.lock.acquire()
        try:
            for media in config.REMOVABLE_MEDIA:
                self.identify(media)
                if media.get_drive_status_changed():
                    _debug_('posting IDENTIFY_MEDIA event %r' % (media.drive_status_text(media.drive_status)))
                    rc.post_event(plugin.event('IDENTIFY_MEDIA', arg=(media, media.drive_status)))
        finally:
            self.lock.release()


    @benchmark(benchmarking, benchmarkcall)
    def __init__(self):
        """ Initialize the identify thread """
        threading.Thread.__init__(self)
        self.lock = thread.allocate_lock()


    @benchmark(benchmarking & 0x1, benchmarkcall)
    def run(self):
        """
        thread main function
        """
        rebuild_file = os.path.join(config.FREEVO_CACHEDIR, 'freevo-rebuild-database')
        # Make sure the movie database is rebuilt at startup
        util.touch(rebuild_file)
        while 1:
            try:
                # Check if we need to update the database
                # This is a simple way for external apps to signal changes
                if os.path.exists(rebuild_file):
                    if video.hash_fxd_movie_database() == 0:
                        # something is wrong, deactivate this feature
                        rebuild_file = '/this/file/should/not/exist'

                    for media in config.REMOVABLE_MEDIA:
                        media.drive_status = CDS_NO_INFO #media.get_drive_status()

                if not rc.app():
                    # check only in the menu
                    self.check_all()

                for i in range(4):
                    # wait some time
                    time.sleep(0.5)

                    # check if we need to stop
                    if hasattr(self, 'stop'):
                        return
            except SystemExit:
                break


if __name__ == '__main__':
    if config.ROM_DRIVES is not None:
        for i in range(len(config.ROM_DRIVES)):
            (dir, device, name) = config.ROM_DRIVES[i]
            media = RemovableMedia(mountdir=dir, devicename=device, drivename=name)
            print '-' * len('%r' % (media.devicename,))
            print '%r' % (media.devicename,)
            print '-' * len('%r' % (media.devicename,))
            cdc = media.get_capabilities()
            for capability in media.capabilities_text(media.cdc):
                print '%s' % (capability)
            media.get_drive_status()
            print '%s' % (media.drive_status_text(media.cds))
            print '%s' % (media.disc_status_text(media.cis))
            print '%s is %s' % (name, media.is_tray_open() and 'OPEN' or 'CLOSED')
