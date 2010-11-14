# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo video modules for Xine
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Activate this plugin by putting plugin.activate('video.xine') in your
# local_conf.py. Than xine will be used for DVDs when you SELECT the item.
# When you select a title directly in the menu, this plugin won't be used
# and the default player (mplayer) will be used. You need xine-ui >= 0.9.22
# to use this.
#
# Todo:
#
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


import time, os, re
import subprocess
import copy

import config     # Configuration handler. reads config file.
import childapp   # Handle child applications
import rc         # The RemoteControl class.
import util

from event import *
import plugin

import dialog
import dialog.utils
from dialog.display import AppTextDisplay
import telnetlib

import osd
osd = osd.get_singleton()

class PluginInterface(plugin.Plugin):
    """
    Xine plugin for the video player.

    Activate this plugin by putting in your local_conf.py:
    | plugin.activate('video.xine')

    Than xine will be used for DVDs when you SELECT the item.  When
    you select a title directly in the menu, this plugin won't be used and the
    default player (mplayer) will be used. You need xine-ui >= 0.9.22 to use this.
    """
    def __init__(self):
        _debug_('PluginInterface.__init__()', 2)
        try:
            config.XINE_COMMAND
        except:
            print _('\'XINE_COMMAND\' not defined, \'xine\' video plugin deactivated.\n' \
                           'please check the xine section in freevo_config.py')
            self.reason = '\'XINE_COMMAND\' not defined, \'xine\' video plugin deactivated'
            return

        plugin.Plugin.__init__(self)

        if config.XINE_COMMAND.find('fbxine') >= 0:
            type = 'fb'
        elif config.XINE_COMMAND.find('df_xine') >= 0:
            type = 'df'
        else:
            type = 'X'

        # register xine as the object to play
        plugin.register(Xine(type), plugin.VIDEO_PLAYER, True)

    def config(self):
        return (('XINE_USE_FREEVO_OSD', False, 'Use the skinnable freevo OSD (if available) rather than the inbuilt Xine OSD'),)


class Xine:
    """
    the main class to control xine
    """
    def __init__(self, type):
        """ Xine contructor """
        _debug_('Xine.__init__(type=%r)' % (type,), 2)
        self.name      = 'xine'
        self.event_context  = 'video'
        self.xine_type = type
        self.app       = None
        self.plugins   = []
        self.paused    = False
        self.command   = None
        self.tmp_playlist = None


    def ShowMessage(self, msg):
        """ Show a message on the OSD """
        _debug_('ShowMessage(msg=%r)' % (msg,), 2)
        self.app.write("OSDWriteText$     %s\n" % msg)


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        if not item.url:
            return 0
        # dvd with menu
        if item.url.startswith('dvd://'):
            _debug_('xine rating: %r good' % (item.url), 2)
            return 2
        # vcd
        if item.url.startswith('vcd://'):
            if item.url == 'vcd://':
                _debug_('xine rating: %r good' % (item.url), 2)
                return 2
            _debug_('xine rating: %r unplayable' % (item.url), 2)
            return 0
        # mimetypes from config (user's wishes!)
        if item.mimetype in config.VIDEO_XINE_SUFFIX:
            _debug_('xine rating: %r good' % (item.url), 2)
            return 2
        if item.mode in ('http') and not item.filename and not item.media:
            _debug_('xine rating: %r unplayable' % (item.url), 2)
            return 0
        if item.network_play:
            _debug_('xine rating: %r possible' % (item.url), 2)
            return 1
        _debug_('xine rating: %r unplayable' % (item.url), 2)
        return 0


    def play(self, options, item):
        """ play video media with xine """
        _debug_('play(options=%r, item=%r)' % (options, item), 2)
        self.item = item
        self.options = options
        self.item.elapsed = 0
        
        if config.EVENTS.has_key(item.mode):
            self.event_context = item.mode
        else:
            self.event_context = 'video'

        if self.command is None:
            config_file_opt = []
            network_opt = []
            if config.XINE_USE_FREEVO_OSD:
                config_file = dialog.utils.get_xine_config_file()
                if config_file:
                    config_file_opt = ['--config', config_file]


            if config.XINE_USE_FREEVO_OSD and dialog.overlay_display_supports_dialogs:
                xine_cmd_line = config.XINE_COMMAND + config.XINE_ARGS_DEF
                if xine_cmd_line.find('--network') == -1 or xine_cmd_line.find(' -n') == -1:
                    network_opt = ['--network']

                passwd_file = '%s/.xine/passwd' % os.environ['HOME']
                if not os.path.exists(passwd_file):
                    out = open(passwd_file, 'w')
                    out.write('ALL:ALLOW\n')
                    out.close()
                    print _('!WARNING! created a xine passwd file with ALL:ALLOW')

            self.command = [ '--prio=%s' % config.MPLAYER_NICE ] + \
                config.XINE_COMMAND.split(' ') +  \
                network_opt + \
                [ '--stdctl', '-V', config.XINE_VO_DEV, '-A', config.XINE_AO_DEV ] + \
                config.XINE_ARGS_DEF.split(' ') + config_file_opt

        command = copy.copy(self.command)

        if item['deinterlace']:
            command.append('-D')

        if not config.XINE_HAS_NO_LIRC and '--no-lirc' in command:
            command.remove('--no-lirc')

        if config.OSD_SINGLE_WINDOW:
            command += ['-W', str(osd.video_window.id), '--no-mouse']
            osd.video_window.show()

        self.max_audio        = 0
        self.current_audio    = -1
        self.max_subtitle     = 0
        self.current_subtitle = -1

        if item.mode == 'dvd':
            for track in item.info['tracks']:
                if track.has_key('audio'):
                    self.max_audio = max(self.max_audio, len(track['audio']))

            for track in item.info['tracks']:
                if track.has_key('subtitles'):
                    self.max_subtitle = max(self.max_subtitle, len(track['subtitles']))

        if item.mode == 'dvd' and hasattr(item, 'filename') and item.filename and \
               item.filename.endswith('.iso'):
            # dvd:///full/path/to/image.iso/
            command.append('dvd://%s/' % item.filename)

        elif item.mode == 'dvd' and hasattr(item.media, 'devicename'):
            # dvd:///dev/dvd/2
            command.append('dvd://%s/%s' % (item.media.devicename, item.url[6:]))

        elif item.mode == 'dvd': # no devicename? Probably a mirror image on the HD
            command.append(item.url)

        elif item.mode == 'vcd':
            # vcd:///dev/cdrom -- NO track support (?)
            command.append('vcd://%s' % item.media.devicename)

        elif item.mimetype == 'cue':
            command.append('vcd://%s' % item.filename)
            self.event_context = 'vcd'

        else:
            if (len(options) > 1):
                if (options[1] == '--playlist'):
                    #command.append('%s %s' % (options[1],options[2]))
                    command.append(options[1])
                    command.append(options[2])
            else:
                if item['resume']:
                    self.item.elapsed = int(item['resume'])
                    self.tmp_playlist = self.write_playlist(item, self.item.elapsed)
                    command.append('--playlist')
                    command.append(self.tmp_playlist)
                else:
                    command.append(item.url)

        self.stdout_plugins = []
        self.paused    = False
        rc.add_app(self)

        self.app = XineApp(command, self)
        dialog.enable_overlay_display(AppTextDisplay(self.ShowMessage))
        return None


    def stop(self, event=None):
        """ Stop xine """
        _debug_('stop(event=%r)' % (event,), 2)
        if not self.app:
            return

        if config.OSD_SINGLE_WINDOW:
            osd.video_window.hide()

        if self.tmp_playlist:
            try:
                os.remove(self.tmp_playlist)
            except:
                pass
            self.tmp_playlist = None

        if config.XINE_BOOKMARK:
            # if the file ends do nothing, else get elapsed time
            if event in (STOP, USER_END):
                command = "%s -S get_time --stdctl --no-splash --hide-gui" % config.CONF.xine
                handle = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE )
                (cin, cout) = (handle.stdin, handle.stdout)
                try:
                    position = cout.read();
                    _debug_("Elapsed = %s" % position)
                    if position:
                        self.item.elapsed = int(position)
                finally:
                    #xine should exit nicely, but if the first xine is already closed this xine will hang
                    exit_code = handle.poll()
                    if not exit_code and not cin.closed:
                        cin.write('quit\n')

        self.app.stop('quit\n')
        rc.remove_app(self)
        dialog.disable_overlay_display()
        self.app = None


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for xine control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        _debug_('eventhandler(event=%r, menuw=%r)' % (event.name, menuw), 2)
        if not self.app:
            return self.item.eventhandler(event)

        if event in (PLAY_END, USER_END):
            self.stop(event)
            return self.item.eventhandler(event)

        if event == PAUSE or event == PLAY:
            self.paused = not self.paused
            if config.XINE_USE_FREEVO_OSD:
                dialog.show_play_state(self.paused and dialog.PLAY_STATE_PAUSE or dialog.PLAY_STATE_PLAY, self.item, self.get_time_info)
            self.app.write('pause\n')
            return True

        if event == STOP:
            self.stop(event)
            return self.item.eventhandler(event)

        if event == SEEK:
            pos = int(event.arg)
            if pos < 0:
                action='SeekRelative-'
                pos = 0 - pos
                if config.XINE_USE_FREEVO_OSD and dialog.is_dialog_supported():
                    dialog.show_play_state(dialog.PLAY_STATE_SEEK_BACK, self.item, self.get_time_info)
            else:
                action='SeekRelative+'
                if config.XINE_USE_FREEVO_OSD and dialog.is_dialog_supported():
                    dialog.show_play_state(dialog.PLAY_STATE_SEEK_FORWARD, self.item, self.get_time_info)
            if pos <= 15:
                pos = 15
            elif pos <= 30:
                pos = 30
            else:
                pos = 30
            self.app.write('%s%s\n' % (action, pos))
            return True

        if event == TOGGLE_OSD:
            if config.XINE_USE_FREEVO_OSD and dialog.is_dialog_supported():
                dialog.show_play_state(dialog.PLAY_STATE_INFO, self.item, self.get_time_info)
            else:
                self.app.write('OSDStreamInfos\n')
            return True

        if event == VIDEO_TOGGLE_INTERLACE:

            self.app.write('ToggleInterleave\n')
            self.item['deinterlace'] = not self.item['deinterlace']
            return True

        if event == NEXT:
            self.app.write('EventNext\n')
            return True

        if event == PREV:
            self.app.write('EventPrior\n')
            return True

        if event == VIDEO_SEND_XINE_CMD:
            self.app.write('%s\n' % event.arg)
            return True

        # DVD NAVIGATION
        if event == DVDNAV_LEFT:
            self.app.write('EventLeft\n')
            return True

        if event == DVDNAV_RIGHT:
            self.app.write('EventRight\n')
            return True

        if event == DVDNAV_UP:
            self.app.write('EventUp\n')
            return True

        if event == DVDNAV_DOWN:
            self.app.write('EventDown\n')
            return True

        if event == DVDNAV_SELECT:
            self.app.write('EventSelect\n')
            return True

        if event == DVDNAV_TITLEMENU:
            self.app.write('TitleMenu\n')
            return True

        if event == DVDNAV_MENU:
            self.app.write('Menu\n')
            return True

        # VCD NAVIGATION
        if event in INPUT_ALL_NUMBERS:
            self.app.write('Number%s\n' % event.arg)
            time.sleep(0.1)
            self.app.write('EventSelect\n')
            return True

        if event == MENU:
            self.app.write('TitleMenu\n')
            return True

        # DVD/VCD language settings
        if event == VIDEO_NEXT_AUDIOLANG and self.max_audio:
            if self.current_audio < self.max_audio - 1:
                self.app.write('AudioChannelNext\n')
                self.current_audio += 1
                # wait until the stream is changed
                time.sleep(0.1)
            else:
                # bad hack to warp around
                if self.xine_type == 'fb':
                    self.app.write('AudioChannelDefault\n')
                    time.sleep(0.1)
                for i in range(self.max_audio):
                    self.app.write('AudioChannelPrior\n')
                    time.sleep(0.1)
                self.current_audio = -1
            return True

        if event == VIDEO_NEXT_SUBTITLE and self.max_subtitle:
            if self.current_subtitle < self.max_subtitle - 1:
                self.app.write('SpuNext\n')
                self.current_subtitle += 1
                # wait until the stream is changed
                time.sleep(0.1)
            else:
                # bad hack to warp around
                if self.xine_type == 'fb':
                    self.app.write('SpuDefault\n')
                    time.sleep(0.1)
                for i in range(self.max_subtitle):
                    self.app.write('SpuPrior\n')
                    time.sleep(0.1)
                self.current_subtitle = -1
            return True

        if event == VIDEO_NEXT_ANGLE:
            self.app.write('EventAngleNext\n')
            time.sleep(0.1)
            return True

        # nothing found? Try the eventhandler of the object who called us
        return self.item.eventhandler(event)

    def get_time_info(self):
        handle = None
        result = None
        try:
            handle = telnetlib.Telnet('127.0.0.1', 6789)
            out = handle.read_until('\n', 0.1)
            if out[-1] == '\n':
                position = self.item.elapsed
                if position == -1:
                    position = self._get_time(handle, 'position')
                length = self._get_time(handle, 'length')
                result = (position, length)
        except:
            _debug_('Failed to retrieve time info from xine')

        if handle:
            handle.close()

        return result

    def _get_time(self, handle, arg):
        """
        get time info from running xine
        """
        try:
            handle.write('get %s\n' % arg)
            out = handle.read_until('\n', 0.05).split()
            if out[1] == ('%s:'%arg):
                time = int(int(out[2])/1000)
                return time
        except:
            pass
        return 0

    def write_playlist(self, item, start_time):
        """
        Create a playlist file to start the specified item at the time supplied.
        Returns the file name of the playlist created.
        """
        name = '%s/playlist_xine_%s.tox' % (config.FREEVO_CACHEDIR,start_time)

        # this file has a companion subtitle file?
        subtitle = None
        try:
            import glob
            
            for file in glob.glob('%s.*' % os.path.splitext(item.filename)[0]):
                if os.path.splitext(file)[1].lower() in ['.srt', '.sub', '.ssa']:
                    subtitle = file
                    break
        except:
            pass

        playlist = open(name,'w')
        playlist.write ("# toxine playlist\n")
        playlist.write ("entry {\n")
        playlist.write ("       identifier = %s;\n" % item.filename)
        playlist.write ("       mrl = %s;\n" % item.filename)
        if subtitle:
            playlist.write("       subtitle = %s;\n" % subtitle)
        playlist.write ("       start = %s;\n" % start_time)
        playlist.write ("};\n")
        playlist.write ("# END\n")
        playlist.close()
        return name


class XineApp(childapp.ChildApp2):
    """
    class controlling the in and output from the xine process
    """
    def __init__(self, command, player):
        _debug_('XineApp.__init__(command=%r, player=%r)' % (command, player), 2)
        self.item = player.item
        self.player = player
        childapp.ChildApp2.__init__(self, command)


    def stdout_cb(self, line):
        """
        parse the stdout of the xine process
        """
        _debug_('stdout_cb(line=%r)' % (line,), 2)
        if line.startswith('time: '):
            self.item.elapsed = int(line[6:])
        # show connection status for network play
        if self.item.network_play:
            pass



    def stderr_cb(self, line):
        """
        parse the stderr of the xine process
        """
        _debug_('stderr_cb(line=%r)' % (line,), 2)
        # Has it started?
        if line.find('playing mrl') >= 0:
            _debug_('playback started')
        # Has it finished?
        if line.find('playback finished for mrl') >= 0 or line.find('xine_exit: bye!') > 0:
            _debug_('playback finished')
            if self.player:
                self.player.stop()
