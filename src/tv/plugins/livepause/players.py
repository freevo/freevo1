# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo DVBStreamer module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
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
# ----------------------------------------------------------------------- */
"""
This module contains the classes to control different player application used
to display the video.

Xine    - Controls Xine via its stdctrl interface. (Supports OSD Text)
MPlayer - Controls MPlayer via its rc interface. (Supports OSD Text)
Vlc     - Controls Vlc via its rc interface. (Supports OSD Text)
"""
import logging
logger = logging.getLogger("freevo.tv.plugins.livepause.players")

import re
import threading

import config
import childapp
import rc

import dialog
import dialog.display

import osd
osd = osd.get_singleton()

def get_player():
    """
    Find the best Player object available.

    This is based the following criteria in order of precedence:
        1. LIVE_PAUSE2_PREFERRED_PLAYER if not None
        2. Vlc if available
        3. Xine if available
        4. Mplayer

    @returns: the best Player object available.
    """
    player = config.LIVE_PAUSE2_PREFERRED_PLAYER
    if player == 'null':
        return Player('raw')

    if not player in ['vlc', 'xine', 'mplayer']:
        player = None
    if not player:
        if config.CONF.vlc:
            player = 'vlc'
        elif config.CONF.xine:
            player = 'xine'
        else:
            player = 'mplayer'

    return eval('%s()' % player.capitalize())



class Player(object):
    """
    Class representing an application to display video/audio stream from the ringbuffer.
    @ivar mode: The mode the media server should be in when this application connects to it.
    @ivar paused: Whether playback is currently paused (True) or playing (False)
    """
    def __init__(self, mode):
        """
        Initialise a new Player class.
        @param mode: Mode to supply the TS via, either raw or http.
        """
        self.mode = mode
        self.paused = False

    def start(self, socket_address):
        """
        Start the player to play from the specified address/port.
        @param socket_address: Tuple containing an IP address and port to connect to.
        """
        pass


    def stop(self):
        """
        Stop the player.
        """
        pass


    def restart(self):
        """
        Restart playing the mrl, this is to allow the rendering pipeline to be
        restarted after a seek in the ringbuffer.
        """
        pass

    def get_subtitles(self):
        """
        Return the available subtitles.
        @return: An array of subtitle options or None if not supported.
        """
        return None

    def set_subtitles(self, index):
        """
        Set displayed subtitles.
        @param index: The index of the subtitle options to select, based on
        the array returned by get_subtitles() or -1 to disable subtitles.
        """
        pass

    def get_audio_modes(self):
        """
        Return the available audio modes.
        @return: An array of audio modes or None if not supported.
        """
        return None

    def set_audio_mode(self, index):
        """
        Set the audio mode.
        @param index: The index of the audio mode to select based on the array
        returned by get_audio_modes.
        """
        pass

    def get_audio_langs(self):
        """
        Return the available audio languages.
        @return: An array of available audio languages or None if not supported.
        """
        return None

    def set_audio_lang(self, index):
        """
        Set the audio language to play.
        @param index: The index of the audio language to select based on the array
        returned by get_audio_langs.
        """
        pass

    def get_video_fill_modes(self):
        """
        Returns a list of video fill modes.
        @return: An array of available video fill mode options or None if not supported.
        """
        return None

    def set_video_fill_mode(self, index):
        """
        Set the video fill mode.
        @param index: The index of the video fill mode to select based on the array
        returned by get_video_fill_modes.
        """
        pass

    def pause(self):
        """
        Pause Playback.
        """
        pass


    def resume(self):
        """
        Resume Playback.
        """
        pass

    def get_display(self):
        """
        Returns a Display subclass to be passed to the dialog subsystem
        when the player is active.
        """
        return dialog.display.AppTextDisplay(self.display_message)

    def display_message(self, message):
        """
        Display using the players text rendering OSD the specified message text.
        It is assumed that the player will display the message for an
        player-specific time before it is removed.
        """
        print 'display_message: ', message



class Xine(Player):
    """
    the main class to control xine
    """
    def __init__(self):
        Player.__init__(self, 'raw')
        self.app       = None
        self.mrl_index = 0
        self.subtitles = False
        self.paused = False

        self.command = None


    def start(self, socket_address):
        """
        Start the player to play from the specified TCP port.
        """
        self.mrl_index = 0
        if self.command is None:
            config_file_opt = []
            config_file = dialog.utils.get_xine_config_file()
            print 'Config file: ', config_file
            if config_file:
                config_file_opt = ['--config', config_file]

            # Create the command used to start xine.

            self.command = [ '--prio=%s' % config.MPLAYER_NICE ] + \
                           config.XINE_COMMAND.split(' ') + \
                           [ '--stdctl',
                             '-V', config.XINE_VO_DEV,
                             '-A', config.XINE_AO_DEV ] + \
                           config.XINE_ARGS_DEF.split(' ') + \
                           config_file_opt
            
            if config.OSD_SINGLE_WINDOW:
                self.command += ['-W', str(osd.video_window.id), '--no-mouse']
                osd.video_window.show()

            if not rc.PYLIRC and '--no-lirc' in self.command:
                self.command.remove('--no-lirc')
        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset Xine rendering pipeline and
        # make it possible to seek quickly.
        mrl = 'slave://%s:%d' % socket_address
        self.app = childapp.ChildApp2(self.command + \
                       [mrl, mrl])


    def stop(self):
        """
        Stop the player.
        """
        if self.app:
            self.app.stop('quit\n')
            self.app = None
            if config.OSD_SINGLE_WINDOW:
                osd.video_window.hide()


    def restart(self):
        """
        Restart playing the mrl, this is to allow the rendering pipeline to be
        restarted after a seek in the ringbuffer.
        """
        if self.app:
            if self.mrl_index == 0:
                self.mrl_index = 1
                self.app.write('NextMrl\n')
            else:
                self.mrl_index = 0
                self.app.write('PriorMrl\n')

            # If subtitles where enable make sure we reenable them!
            if self.subtitles:
                self.subtitles = False
                self.set_subtitles(0)


    def get_subtitles(self):
        """
        Return the available subtitles.
        """
        return [_('Enabled')]


    def set_subtitles(self, index):
        """
        Set displayed subtitles.
        -1 Disables
        0  Enables subtitles
        """
        if self.app:
            if self.subtitles and index == -1:
                cmd = 'SpuPrior\n'
                self.subtitles = False
            elif not self.subtitles and index == 0:
                cmd = 'SpuNext\n'
                self.subtitles = True
            else:
                cmd = None

            if cmd:
                self.app.write(cmd)


    def pause(self):
        """
        Pause Playback.
        """
        if self.app and not self.paused:
            _debug_('Pausing')
            self.app.write('pause\n')
            self.paused = True


    def resume(self):
        """
        Resume Playback.
        """
        if self.app and self.paused:
            _debug_('Resuming')
            self.app.write('pause\n')
            self.paused = False

    def display_message(self, message):
        """
        Function to tell xine to display the specified text.
        """
        if self.app:
            self.app.write('OSDWriteText$    %s\n' % message)



class Mplayer(Player):
    """
    The main class to control MPlayer
    """
    def __init__(self):
        Player.__init__(self, 'http')
        self.app       = None
        self.mrl_index = 0
        self.subtitles = False
        self.paused = False

        self.command = None


    def start(self, socket_address):
        """
        Start the player to play from the specified TCP port.
        """
        self.mrl_index = 0
        if self.command is None:
            # Build the MPlayer command
            self.command = ['--prio=%s' % config.MPLAYER_NICE, config.MPLAYER_CMD]
            self.command += ['-slave']
            self.command += config.MPLAYER_ARGS_DEF.split(' ')

            if dialog.overlay_display_supports_dialogs:
                self.command += ['-osdlevel','0']

            if config.DEBUG_CHILDAPP:
                self.command += ['-v']

            # Set audio out device
            self.command += ['-ao'] + config.MPLAYER_AO_DEV.split(' ')

            # Set video out device
            self.command += ['-vo', config.MPLAYER_VO_DEV + config.MPLAYER_VO_DEV_OPTS]

            # mode specific args
            mode = 'default'
            self.command += config.MPLAYER_ARGS[mode].split(' ')

            # add any additional arguments
            if config.MPLAYER_VF_INTERLACED:
                self.command += ['-vf', config.MPLAYER_VF_INTERLACED]
            elif config.MPLAYER_VF_PROGRESSIVE:
                self.command += ['-vf', config.MPLAYER_VF_PROGRESSIVE]

            if config.OSD_SINGLE_WINDOW:
                self.command += ['-wid', str(osd.video_window.id)]
                osd.video_window.show()
        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset mplayer's rendering pipeline and
        # make it possible to seek quickly.
        mrl = 'http://%s:%d' % socket_address
        self.app = childapp.ChildApp2(self.command + [mrl, mrl])


    def stop(self):
        """
        Stop the player.
        """
        if self.app:
            self.app.stop('quit\n')
            self.app = None
            if config.OSD_SINGLE_WINDOW:
                osd.video_window.hide()



    def restart(self):
        """
        Restart playing the mrl, this is to allow the rendering pipeline to be
        restarted after a seek in the ringbuffer.
        """
        if self.app:
            if self.mrl_index == 0:
                self.mrl_index = 1
                self.app.write('pt_step 1\n')
            else:
                self.mrl_index = 0
                self.app.write('pt_step -1\n')


    def pause(self):
        """
        Pause Playback.
        """
        if self.app and not self.paused:
            _debug_('Pausing')
            self.app.write('pause\n')
            self.paused = True


    def resume(self):
        """
        Resume Playback.
        """
        if self.app and self.paused:
            _debug_('Resuming')
            self.app.write('pause\n')
            self.paused = False

    def display_message(self, message):
        """
        Function to tell mplayer to display the specified text.
        """
        if self.app:
            self.app.write('osd_show_text "%s"\n' % message)



class Vlc(Player):
    """
    The main class to control VLC
    if you plan to use GraphicOSD : logo sub-filter works in vlc 0.8.6i or older
    """
    def __init__(self):
        Player.__init__(self, 'http')
        self.app = None
        self.paused = False
        self.command = None
        self.current_sub_index = -1
        self.sub_pids = []
        self.current_audio_index = -1
        self.audio_pids = []


    def start(self, socket_address):
        """
        Start the player to play from the specified TCP port.
        """
        self.paused = False
        if self.command is None:
            self.command = ['--prio=%s' % config.MPLAYER_NICE, config.CONF.vlc]
            self.command += ['-I', 'rc', '--rc-fake-tty',
                        '--width', str(config.CONF.width),
                        '--height', str(config.CONF.height),
                        '--sub-filter', 'marq:logo', '--marq-timeout', '3000', '--marq-marquee', 'Playing', '--logo-file', 'dummy'
                       ]
            if hasattr(config, 'VLC_OPTIONS'):
                self.command += config.VLC_OPTIONS.split(' ')

            if dialog.overlay_display_supports_dialogs:
                self.command += ['--no-osd']

            if config.OSD_SINGLE_WINDOW:
                self.command += ['--drawable-xid', str(osd.video_window.id)]
                osd.video_window.show()

        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset mplayer's rendering pipeline and
        # make it possible to seek quickly.
        mrl = 'http://%s:%d' % socket_address
        self.app = VlcApp(self.command + [mrl])


    def stop(self):
        """
        Stop the player.
        """
        if self.app:
            self.app.send_command('quit')
            self.app = None
            if config.OSD_SINGLE_WINDOW:
                osd.video_window.hide()


    def restart(self):
        """
        Restart playing the mrl, this is to allow the rendering pipeline to be
        restarted after a seek in the ringbuffer.
        """
        self.app.send_command('goto 0')
        # If subtitles where enable make sure we reenable them!
        if self.current_sub_index > 0:
            self.set_subtitles(self.current_sub_index)

        if self.current_audio_index > 0:
            self.set_audio_lang(self.current_audio_index)


    def get_subtitles(self):
        """
        Return list of available subtitles
        """
        subtitles = []

        if self.app:
            self.app.send_command_wait_for_output('strack')
            self.sub_pids = []
            for pid, lang in self.app.sub_tracks:
                subtitles.append(lang)
                self.sub_pids.append(pid)
        return subtitles


    def set_subtitles(self, index):
        """
        Enable subtitles.
        """
        if not self.app:
            return

        if index >= 0 and index <= len(self.sub_pids):
            sub_pid = self.sub_pids[index]
        else:
            sub_pid = index
        _debug_('Setting subtitle track %d (pid %s)' % (index, sub_pid))
        self.app.send_command('strack %s' % sub_pid)
        self.current_sub_index = index


    def get_audio_modes(self):
        """
        Return the available audio modes.
        @return: An array of audio modes or None if not supported.
        """
        return None


    def set_audio_mode(self, index):
        """
        Set the audio mode.
        @param index: The index of the audio mode to select based on the array
        returned by get_audio_mode.
        """
        pass


    def get_audio_langs(self):
        """
        Return the available audio languages.
        @return: An array of available audio languages or None if not supported.
        """
        audio_tracks = []

        if self.app:
            self.app.send_command_wait_for_output('atrack')
            self.audio_pids = []
            for pid, lang in self.app.audio_tracks:
                audio_tracks.append(lang)
                self.audio_pids.append(pid)
        return audio_tracks


    def set_audio_lang(self, index):
        """
        Set the audio language to play.
        @param index: The index of the audio language to select based on the array
        returned by get_audio_lang.
        """
        if not self.app:
            return

        if index >= 0 and index <= len(self.audio_pids):
            audio_pid = self.audio_pids[index]
        else:
            audio_pid = index
        _debug_('Setting audio track %d (pid %s)' % (index, audio_pid))
        self.app.send_command('atrack %s' % audio_pid)
        self.current_audio_index = index


    def get_video_fill_modes(self):
        """
        Returns a list of video fill modes.
        @return: An array of available video fill mode options or None if not supported.
        """
        return None


    def set_video_fill_mode(self, index):
        """
        Set the video fill mode.
        @param index: The index of the video fill mode to select based on the array
        returned by get_video_fill_modes.
        """
        pass


    def pause(self):
        """
        Pause Playback.
        """
        if self.app and not self.paused:
            _debug_('Pausing')
            self.app.send_command('pause 0')
            self.paused = True


    def resume(self):
        """
        Resume Playback.
        """
        if self.app and self.paused:
            _debug_('Resuming')
            self.app.send_command('pause 0')
            self.paused = False

    def get_display(self):
        """
        Returns a Display subclass to be passed to the dialog subsystem
        when the player is active.
        """
        return dialog.display.AppTextDisplay(self.display_message)

    def display_message(self, message):
        """
        Function to tell mplayer to display the specified text.
        """
        if self.app:
            _debug_('display %s' % message)
            self.app.send_command('marq-marquee %s' % message)


    def show_graphics(self, surface, position):
        """
        Show the graphics on the specified surface using the players graphics
        OSD.
        NOTE: Only supported if supports_graphics is True.

        surface - pygame.Surface to display
        position - (x,y) position to display the image.
        """
        if self.app:
            surface.save ('/tmp/vlcosd.png')
            self.app.send_command('logo-file /tmp/vlcosd.png')
            self.app.send_command('logo-transparency 220')
            self.app.send_command('logo-position %d' % position[0])
            self.app.send_command('logo-position %d' % position[1])
            #self.app.send_command('logo-position 8')   # to use built-in smart positioning of vlc (8 = bottom center)


    def hide_graphics(self):
        """
        Hide the players graphics OSD.
        NOTE: Only supported if supports_graphics is True.
        """

        if self.app:
            self.app.send_command('logo-file dummy')

# Regular Expression for parsing VLC output
VLC_RE_EXIT              = re.compile("status change: \( quit \)")
VLC_RE_PARSE_HEAD_AUDIO  = re.compile('^\+----\[ Audio Track \]')
VLC_RE_PARSE_HEAD_SUB    = re.compile('^\+----\[ Subtitles Track \]')
VLC_RE_PARSE_HEAD_ACHAN  = re.compile('^\+----\[ Audio Device \]')
VLC_RE_PARSE_FOOT        = re.compile('^\+----\[ end of')
VLC_RE_PARSE_ACHAN       = re.compile('^\| ([0-9]+) - (.*?)')
VLC_RE_PARSE_TRACK       = re.compile('^\| ([0-9]+) - .*? - \[(.*?)\]')



class VlcApp(childapp.ChildApp2):
    """
    Class used to process output from vlc.
    """

    def __init__ (self, command):
        self.exit_type = None
        self.audio_tracks = []
        self.sub_tracks   = []
        self.audio_chans  = []
        self.stat = {
            'none'  : '0',
            'audio' : '1',
            'subs'  : '2',
            'achan' : '3',
        }
        self.parsecur     = None
        self.output_event = threading.Event()
        childapp.ChildApp2.__init__(self, command, callback_use_rc=False)


    def send_command(self, cmd):
        """
        Send a command to vlc.
        """
        self.write('%s\n' % cmd)


    def send_command_wait_for_output(self, cmd):
        """
        Send a command to vlc and then wait until output has been received.
        """
        self.output_event.clear()
        self.send_command(cmd)
        self.output_event.wait()


    def stdout_cb(self, line):
        """
        Process output from vlc sent to stdout.
        """
        if VLC_RE_EXIT.search(line):
            self.exit_type = 'Quit'

        elif VLC_RE_PARSE_HEAD_AUDIO.search(line):
            self.parsecur = self.stat['audio']
            self.audio_tracks = []

        elif VLC_RE_PARSE_HEAD_SUB.search(line):
            self.parsecur = self.stat['subs']
            self.sub_tracks = []

        elif VLC_RE_PARSE_HEAD_ACHAN.search(line):
            self.parsecur = self.stat['achan']
            self.audio_chans = []

        elif VLC_RE_PARSE_FOOT.search(line):
            self.parsecur = self.stat['none']
            self.output_event.set()

        else:
            match = VLC_RE_PARSE_TRACK.search(line)
            if match:
                if self.parsecur == self.stat['audio']:
                    self.audio_tracks.append( (match.group(1), match.group(2)))

                elif self.parsecur == self.stat['subs']:
                    self.sub_tracks.append((match.group(1), match.group(2)))

            elif self.parsecur == self.stat['achan']:
                match = VLC_RE_PARSE_HEAD_ACHAN.search(line)
                if match:
                    self.audio_chans.append( (match.group(1), match.group(2)))


    def stop_event(self):
        """
        return the stop event send through the eventhandler
        """
        import event
        return event.PLAY_END
