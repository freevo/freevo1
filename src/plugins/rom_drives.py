# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# rom_drives.py - the Freevo identifymedia/automount plugin
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
import util.mediainfo
from struct import *
import array
import rc


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
        CDROMEJECT = 0x5309
        CDROMCLOSETRAY = 0x5319
        CDROM_DRIVE_STATUS = 0x5326
        CDROM_SELECT_SPEED = 0x5322
        CDROM_LOCKDOOR = 0x5329  # lock or unlock door
        CDROM_GET_CAPABILITY = 0x5331
        CDS_NO_INFO = 0
        CDS_NO_DISC = 1
        CDS_TRAY_OPEN = 2
        CDS_DRIVE_NOT_READY = 3
        CDS_DISC_OK = 4
        CDS_AUDIO = 100
        CDS_DATA_1 = 101
        CDS_DATA_2 = 102
        CDS_XA_2_1 = 103
        CDS_XA_2_2 = 104
        CDS_MIXED = 105
        CDC_CLOSE_TRAY = 0x1
        CDC_OPEN_TRAY = 0x2
        CDC_SELECT_SPEED = 0x8
CDC_MO_DRIVE = 0x40000
CDC_MRW = 0x80000
CDC_MRW_W = 0x100000
CDC_RAM = 0x200000


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
from video import VideoItem

LABEL_REGEXP = re.compile("^(.*[^ ]) *$").match


# Identify_Thread
im_thread = None


def init():
    """
    create a list of media objects and start the Identify_Thread
    """
    print 'init()'
    # Add the drives to the config.removable_media list. There doesn't have
    # to be any drives defined.
    if config.ROM_DRIVES != None:
        for i in range(len(config.ROM_DRIVES)):
            (dir, device, name) = config.ROM_DRIVES[i]
            media = RemovableMedia(mountdir=dir, devicename=device,
                                   drivename=name)
            media.get_capabilities()
            # close the tray without popup message
            media.move_tray(dir='close', notify=0)
            config.REMOVABLE_MEDIA.append(media)

    # Remove the ROM_DRIVES member to make sure it is not used by
    # legacy code!
    del config.ROM_DRIVES

    # Start identifymedia thread
    global im_thread
    im_thread = Identify_Thread()
    im_thread.setDaemon(1)
    im_thread.start()


def shutdown():
    """
    shut down the Identify_Thread
    """
    global im_thread
    if im_thread.isAlive():
        _debug_('stopping Identify_Thread', 2)
        im_thread.stop = True
        while im_thread.isAlive():
            time.sleep(0.1)


class autostart(plugin.DaemonPlugin):
    """
    Plugin to autostart if a new medium is inserted while Freevo shows
    the main menu
    """
    def __init__(self):
        """
        load the plugin and start the thread
        """
        print 'autostart:__init__()'
        plugin.DaemonPlugin.__init__(self)
        global im_thread
        if not im_thread:
            init()


    def eventhandler(self, event=None, menuw=None, arg=None):
        """
        eventhandler to handle the IDENTIFY_MEDIA plugin event and the
        EJECT event
        """
        global im_thread

        # if we are at the main menu and there is an IDENTIFY_MEDIA event,
        # try to autorun the media
        if plugin.isevent(event) == 'IDENTIFY_MEDIA' and menuw and \
               len(menuw.menustack) == 1 and not event.arg[1]:
            media = event.arg[0]
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
                media.move_tray(dir='toggle')
                return True

    def shutdown(self):
        shutdown()


class rom_items(plugin.MainMenuPlugin):
    """
    Plugin to add the rom drives to a main menu. This can be the global main menu
    or most likely the video/audio/image/games main menu
    """
    def __init__(self):
        """
        load the plugin and start the thread
        """
        plugin.MainMenuPlugin.__init__(self)
        global im_thread
        if not im_thread:
            init()

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


    def items_eventhandler(self, event, item, menuw):
        """
        handle EJECT for the rom drives
        """
        if event == EJECT and item.media and menuw and \
           menuw.menustack[1] == menuw.menustack[-1]:
            item.media.move_tray(dir='toggle')
            return True
        return False


class RemovableMedia:
    """
    Object about one drive
    """
    def __init__(self, mountdir='', devicename='', drivename=''):
        # This is read-only stuff for the drive itself
        self.mountdir = mountdir
        self.devicename = devicename
        self.drivename = drivename

        # Dynamic stuff
        self.tray_open = 0
        self.drive_status = None  # return code from ioctl for DRIVE_STATUS

        self.id        = ''
        self.label     = ''
        self.item      = None
        self.videoitem = None
        self.type      = 'empty_cdrom'
        self.cached    = False

        self.can_close = False
        self.can_eject = False
        self.can_select_speed = False


    def is_tray_open(self):
        """
        return tray status
        """
        return self.tray_open

    def get_capabilities(self):
        """
        """
        print 'get_capabilities(self)'
        _debug_('Getting capabilities of drive %s' % self.drivename, DINFO)
        try:
            fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
            try:
                if os.uname()[0] == 'FreeBSD':
                    self.can_close = True
                    self.can_eject = True
                else:
                    s = ioctl(fd, CDROM_GET_CAPABILITY)

                    if s & CDC_CLOSE_TRAY:
                        self.can_close = True
                        _debug_('Drive %s can close' % self.drivename, DINFO)

                    if s & CDC_OPEN_TRAY:
                        self.can_eject = True
                        _debug_('Drive %s can open' % self.drivename, DINFO)

                    if s & CDC_SELECT_SPEED:
                        self.can_select_speed = True
                        _debug_('Drive %s can select speed' % self.drivename, DINFO)

                    if config.DEBUG:
                        # some code to view the capabilities
                        print 's=%r 0x%08x' % (s, s)
                        print s & CDC_CLOSE_TRAY      and 'CDC_CLOSE_TRAY'      or 'not CDC_CLOSE_TRAY'
                        print s & CDC_OPEN_TRAY       and 'CDC_OPEN_TRAY'       or 'not CDC_OPEN_TRAY' 
                        print s & CDC_LOCK            and 'CDC_LOCK'            or 'not CDC_LOCK'
                        print s & CDC_SELECT_SPEED    and 'CDC_SELECT_SPEED'    or 'not CDC_SELECT_SPEED'
                        print s & CDC_SELECT_DISC     and 'CDC_SELECT_DISC'     or 'not CDC_SELECT_DISC'
                        print s & CDC_MULTI_SESSION   and 'CDC_MULTI_SESSION'   or 'not CDC_MULTI_SESSION'
                        print s & CDC_MCN             and 'CDC_MCN'             or 'not CDC_MCN'
                        print s & CDC_MEDIA_CHANGED   and 'CDC_MEDIA_CHANGED'   or 'not CDC_MEDIA_CHANGED'
                        print s & CDC_PLAY_AUDIO      and 'CDC_PLAY_AUDIO'      or 'not CDC_PLAY_AUDIO'
                        print s & CDC_RESET           and 'CDC_RESET'           or 'not CDC_RESET'
                        print s & CDC_DRIVE_STATUS    and 'CDC_DRIVE_STATUS'    or 'not CDC_DRIVE_STATUS'
                        print s & CDC_GENERIC_PACKET  and 'CDC_GENERIC_PACKET'  or 'not CDC_GENERIC_PACKET'
                        print s & CDC_CD_R            and 'CDC_CD_R'            or 'not CDC_CD_R'
                        print s & CDC_CD_RW           and 'CDC_CD_RW'           or 'not CDC_CD_RW'
                        print s & CDC_DVD             and 'CDC_DVD'             or 'not CDC_DVD'
                        print s & CDC_DVD_R           and 'CDC_DVD_R'           or 'not CDC_DVD_R'
                        print s & CDC_DVD_RAM         and 'CDC_DVD_RAM'         or 'not CDC_DVD_RAM'
                        print s & CDC_MO_DRIVE        and 'CDC_MO_DRIVE'        or 'not CDC_MO_DRIVE'
                        print s & CDC_MRW             and 'CDC_MRW'             or 'not CDC_MRW'
                        print s & CDC_MRW_W           and 'CDC_MRW_W'           or 'not CDC_MRW_W'
                        print s & CDC_RAM             and 'CDC_RAM'             or 'not CDC_RAM'
                        if s & CDC_DRIVE_STATUS:
                            t = ioctl(fd, CDROM_DRIVE_STATUS)
                            print 't=%r 0x%08x' % (t, t)
                            print t == CDS_NO_INFO         and 'CDS_NO_INFO'         or 'not CDS_NO_INFO'
                            print t == CDS_NO_DISC         and 'CDS_NO_DISC'         or 'not CDS_NO_DISC'
                            print t == CDS_TRAY_OPEN       and 'CDS_TRAY_OPEN'       or 'not CDS_TRAY_OPEN'
                            print t == CDS_DRIVE_NOT_READY and 'CDS_DRIVE_NOT_READY' or 'not CDS_DRIVE_NOT_READY'
                            print t == CDS_DISC_OK         and 'CDS_DISC_OK'         or 'not CDS_DISC_OK'

            finally:
                os.close(fd)
        except Exception, e:
            _debug_('Cannot open "%s": %s"' % (self.devicename, e), DWARNING)


    def move_tray(self, dir='toggle', notify=1):
        """
        Move the tray. dir can be toggle/open/close
        """
        if dir == 'toggle':
            if self.is_tray_open():
                dir = 'close'
            else:
                dir = 'open'

        if dir == 'open' and self.can_eject:
            _debug_('Ejecting disc in drive %s' % self.drivename, 1)

            if notify:
                pop = PopupBox(text=_('Ejecting disc in drive %s') % self.drivename)
                pop.show()

            try:
                fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
                try:
                    if os.uname()[0] == 'FreeBSD':
                        s = ioctl(fd, CDIOCEJECT, 0)
                    else:
                        s = ioctl(fd, CDROMEJECT)
                    self.tray_open = 1
                finally:
                    os.close(fd)
            except Exception, e:
                _debug_('Cannot open "%s": %s"' % (self.devicename, e), DWARNING)

            if notify:
                pop.destroy()


        elif dir == 'close' and self.can_close:
            _debug_('Inserting disc in drive %s' % self.drivename, 1)

            if notify:
                pop = PopupBox(text=_('Reading disc in drive %s') % self.drivename)
                pop.show()

            # close the tray, identifymedia does the rest,
            # including refresh screen
            try:
                fd = os.open(self.devicename, os.O_RDONLY | os.O_NONBLOCK)
                try:
                    if os.uname()[0] == 'FreeBSD':
                        s = ioctl(fd, CDIOCCLOSE, 0)
                    else:
                        s = ioctl(fd, CDROMCLOSETRAY)
                    self.tray_open = 0
                finally:
                    os.close(fd)
            except Exception, e:
                _debug_('Cannot open "%s": %s"' % (self.devicename, e), DWARNING)

            global im_thread
            if im_thread:
                im_thread.check_all()
            if notify:
                pop.destroy()


    def mount(self):
        """
        Mount the media
        """
        _debug_('Mounting disc in drive %s' % self.drivename, 2)
        util.mount(self.mountdir, force=True)
        return


    def umount(self):
        """
        Mount the media
        """
        _debug_('Unmounting disc in drive %s' % self.drivename, 2)
        util.umount(self.mountdir)
        return


    def is_mounted(self):
        """
        Check if the media is mounted
        """
        return util.is_mounted(self.mountdir)


    def shutdown(self):
        shutdown()


class Identify_Thread(threading.Thread):
    """
    Thread to watch the rom drives for changes
    """
    def identify(self, media, force_rebuild=False):
        """
        magic!
        Try to find out as much as possible about the disc in the
        rom drive: title, image, play options, ...
        """
        # Check drive status (tray pos, disc ready)
        try:
            CDSL_CURRENT = ( (int ) ( ~ 0 >> 1 ) )
            fd = os.open(media.devicename, os.O_RDONLY | os.O_NONBLOCK)
            if os.uname()[0] == 'FreeBSD':
                try:
                    data = array.array('c', '\000'*4096)
                    (address, length) = data.buffer_info()
                    buf = pack('BBHP', CD_MSF_FORMAT, 0, length, address)
                    s = ioctl(fd, CDIOREADTOCENTRYS, buf)
                    s = CDS_DISC_OK
                except:
                    s = CDS_NO_DISC
            else:
                s = ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
        except:
            # maybe we need to close the fd if ioctl fails, maybe
            # open fails and there is no fd
            try:
                os.close(fd)
            except:
                pass
            media.drive_status = None
            return

        # Same as last time? If so we're done
        if s == media.drive_status:
            os.close(fd)
            return

        media.drive_status = s

        media.id        = ''
        media.label     = ''
        media.type      = 'empty_cdrom'
        media.item      = None
        media.videoitem = None
        media.cached    = False

        # Is there a disc present?
        if s != CDS_DISC_OK:
            os.close(fd)
            return

        # if there is a disc, the tray can't be open
        media.tray_open = False
        disc_info = util.mediainfo.disc_info(media, force_rebuild)
        if not disc_info:
            # bad disc, e.g. blank disc.
            os.close(fd)
            return

        data = disc_info.mmdata

        # try to set the speed
        if media.can_select_speed and config.ROM_SPEED and data and not data['mime'] == 'video/dvd':
            try:
                ioctl(fd, CDROM_SELECT_SPEED, config.ROM_SPEED)
            except:
                pass

        if data and data['mime'] == 'audio/cd':
            os.close(fd)
            disc_id = data['id']
            media.item = AudioDiskItem(disc_id, parent=None,
                                       devicename=media.devicename,
                                       display_type='audio')
            media.type = media.item.type
            media.item.media = media
            if data['title']:
                media.item.name = data['title']
            media.item.info = disc_info
            return

        os.close(fd)
        image = title = movie_info = more_info = fxd_file = None

        media.id    = data['id']
        media.label = data['label']
        media.type  = 'cdrom'

        label = data['label']

        # is the id in the database?
        if media.id in video.fxd_database['id']:
            movie_info = video.fxd_database['id'][media.id]
            if movie_info:
                title = movie_info.name

        # no? Maybe we can find a label regexp match
        else:
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
        # There is data from mmpython for these three types
        if data['mime'] in ('video/vcd', 'video/dvd'):
            if not title:
                title = media.label.replace('_', ' ').lstrip().rstrip()
                title = '%s [%s]' % (data['mime'][6:].upper(), title)

            if movie_info:
                media.item = copy.copy(movie_info)
            else:
                media.item = VideoItem('', None)
                media.item.image = util.getimage(os.path.join(config.OVERLAY_DIR,
                                                              'disc-set', media.id))
            variables = media.item.info.variables
            media.item.info = disc_info
            media.item.info.set_variables(variables)

            media.item.name  = title
            media.item.set_url(data['mime'][6:] + '://')
            media.item.media = media

            media.type  = data['mime'][6:]

            media.item.info.mmdata = data
            return

        # Disc is data of some sort. Mount it to get the file info
        util.mount(media.mountdir, force=True)
        if os.path.isdir(os.path.join(media.mountdir, 'VIDEO_TS')) or \
               os.path.isdir(os.path.join(media.mountdir, 'video_ts')):
            if force_rebuild:
                _debug_('Double check without success')
            else:
                _debug_('Undetected DVD, checking again')
                media.drive_status = CDS_NO_DISC
                util.umount(media.mountdir)
                return self.identify(media, True)

        # Check for movies/audio/images on the disc
        num_video = disc_info['disc_num_video']
        num_audio = disc_info['disc_num_audio']
        num_image = disc_info['disc_num_image']

        video_files = util.match_files(media.mountdir, config.VIDEO_SUFFIX)

        _debug_('identifymedia: mplayer = "%s"' % video_files, level = 2)

        media.item = DirItem(media.mountdir, None, create_metainfo=False)
        media.item.info = disc_info
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


        # set the infos we have now
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
            if movie_info:
                media.videoitem = copy.deepcopy(movie_info)
            else:
                media.videoitem = VideoItem(video_files[0], None)
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


    def check_all(self):
        """
        check all drives
        """
        if rc.app():
            # Some app is running, do not scan, it's not necessary
            return

        self.lock.acquire()
        try:
            for media in config.REMOVABLE_MEDIA:
                last_status = media.drive_status
                self.identify(media)

                if last_status != media.drive_status:
                    _debug_('MEDIA: Status=%s' % media.drive_status,2)
                    _debug_('Posting IDENTIFY_MEDIA event',2)
                    if last_status == None:
                        rc.post_event(plugin.event('IDENTIFY_MEDIA', arg=(media, True)))
                    else:
                        rc.post_event(plugin.event('IDENTIFY_MEDIA', arg=(media, False)))
        finally:
            self.lock.release()


    def __init__(self):
        """
        init the thread
        """
        threading.Thread.__init__(self)
        self.lock = thread.allocate_lock()


    def run(self):
        """
        thread main function
        """
        rebuild_file = os.path.join(config.FREEVO_CACHEDIR, 'freevo-rebuild-database')
        # Make sure the movie database is rebuilt at startup
        util.touch(rebuild_file)
        while 1:
            # Check if we need to update the database
            # This is a simple way for external apps to signal changes
            if os.path.exists(rebuild_file):
                if video.hash_fxd_movie_database() == 0:
                    # something is wrong, deactivate this feature
                    rebuild_file = '/this/file/should/not/exist'

                for media in config.REMOVABLE_MEDIA:
                    media.drive_status = None

            if not rc.app():
                # check only in the menu
                self.check_all()

            for i in range(4):
                # wait some time
                time.sleep(0.5)

                # check if we need to stop
                if hasattr(self, 'stop'):
                    return
