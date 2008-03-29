# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# players.py - the Freevo DVBStreamer module for tv
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

import re
import threading

import config
import childapp
import rc

def get_player():
    """
    Returns the best Player object available.

    This is based the following criteria in order of precedence:
    1. LIVE_PAUSE2_PREFERRED_PLAYER if not None
    2. Vlc if available
    3. Xine if available
    4. Mplayer
    """
    player = config.LIVE_PAUSE2_PREFERRED_PLAYER
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
    def __init__(self, supports_text, supports_graphics):
        """
        Initialise a new Player class.
        @param supports_text:  Set to True if the player supports a text rendering OSD.
        @param supports_graphics: Set to True If the player supports a graphics OSD.
        """
        self.supports_text = supports_text
        self.supports_graphics = supports_graphics

    def start(self, port):
        """
        Start the player to play from the specified TCP port.
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
        """
        return None

    def set_subtitles(self, index):
        """
        Set displayed subtitles.
        -1 Disables
        Any other index selects a subtitle language.
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


    def display_message(self, message):
        """
        Display using the players text rendering OSD the specified message text.
        It is assumed that the player will display the message for an
        player-specific time before it is removed.

        NOTE: Only supported if supports_text is True.
        """
        pass

    def show_graphics(self, surface, x, y):
        """
        Show the graphics on the specified surface using the players graphics
        OSD.
        NOTE: Only supported if supports_graphics is True.

        surface - pygame.Surface to display.
        x,y - Position on screen to display the graphics.
        """
        pass

    def hide_graphics(self):
        """
        Hide the players graphics OSD.
        NOTE: Only supported if supports_graphics is True.
        """
        pass

    def set_graphics_alpha(self, alpha):
        """
        Set the alpha/transparency of the OSD layer.
        alpha - 0=Transparent, 255=Opaque.
        """
        pass

class Xine(Player):
    """
    the main class to control xine
    """
    def __init__(self):
        Player.__init__(self, True, False)
        self.app       = None
        self.mrl_index = 0
        self.subtitles = False
        self.paused = False

        # Create the command used to start xine.

        self.command = [ '--prio=%s' % config.MPLAYER_NICE ] + \
                       config.XINE_COMMAND.split(' ') + \
                       [ '--stdctl',
                         '-V', config.XINE_VO_DEV,
                         '-A', config.XINE_AO_DEV ] + \
                       config.XINE_ARGS_DEF.split(' ')


        if not rc.PYLIRC and '--no-lirc' in self.command:
            self.command.remove('--no-lirc')


    def start(self, port):
        """
        Start the player to play from the specified TCP port.
        """
        self.mrl_index = 0
        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset Xine rendering pipeline and
        # make it possible to seek quickly.
        mrl = 'http://localhost:%d' % port
        self.app = childapp.ChildApp2(self.command + \
                       [mrl, mrl])


    def stop(self):
        """
        Stop the player.
        """
        if self.app:
            self.app.stop('quit\n')
            self.app = None


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
        Player.__init__(self, True, False)
        self.app       = None
        self.mrl_index = 0
        self.subtitles = False
        self.paused = False

        # Build the MPlayer command
        command = ['--prio=%s' % config.MPLAYER_NICE, config.MPLAYER_CMD]
        command += ['-slave']
        command += config.MPLAYER_ARGS_DEF.split(' ')

        if config.DEBUG_CHILDAPP:
            command += ['-v']

        # Set audio out device
        command += ['-ao'] + config.MPLAYER_AO_DEV.split(' ')

        # Set video out device
        command += ['-vo', config.MPLAYER_VO_DEV + config.MPLAYER_VO_DEV_OPTS]

        # mode specific args
        mode = 'default'
        command += config.MPLAYER_ARGS[mode].split(' ')

        # add any additional arguments
        if config.MPLAYER_VF_INTERLACED:
            command += ['-vf', config.MPLAYER_VF_INTERLACED]
        elif config.MPLAYER_VF_PROGRESSIVE:
            command += ['-vf', config.MPLAYER_VF_PROGRESSIVE]

        self.command = command


    def start(self, port):
        """
        Start the player to play from the specified TCP port.
        """
        self.mrl_index = 0
        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset mplayer's rendering pipeline and
        # make it possible to seek quickly.
        mrl = 'http://localhost:%d' % port
        self.app = childapp.ChildApp2(self.command + \
                       [mrl, mrl])


    def stop(self):
        """
        Stop the player.
        """
        if self.app:
            self.app.stop('quit\n')
            self.app = None


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
    """
    def __init__(self):
        Player.__init__(self, True, False)
        self.app = None
        self.paused = False
        command = ['--prio=%s' % config.MPLAYER_NICE, config.CONF.vlc]
        command += ['-I', 'rc', '--rc-fake-tty',
                    '--width', str(config.CONF.width),
                    '--height', str(config.CONF.height),
                    '--sub-filter', 'marq', '--marq-marquee', 'Playing', '--marq-timeout', '3000'
                   ]
        command += config.VLC_OPTIONS.split(' ')
        self.command = command
        self.current_sub_index = -1
        self.sub_pids = []


    def start(self, port):
        """
        Start the player to play from the specified TCP port.
        """
        self.paused = False
        # NOTE: We add the slave server MRL twice so that we can toggle between
        # them, this allows use to effectively reset mplayer's rendering pipeline and
        # make it possible to seek quickly.
        mrl = 'http://@localhost:%d' % port
        self.app = VlcApp(self.command + [mrl])


    def stop(self):
        """
        Stop the player.
        """
        if self.app:
            self.app.send_command('quit')
            self.app = None


    def restart(self):
        """
        Restart playing the mrl, this is to allow the rendering pipeline to be
        restarted after a seek in the ringbuffer.
        """
        self.app.send_command('goto 0')
        # If subtitles where enable make sure we reenable them!
        if self.current_sub_index > 0:
            self.set_subtitles(self.current_sub_index)


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

    def display_message(self, message):
        """
        Function to tell mplayer to display the specified text.
        """
        if self.app:
            _debug_('display %s' % message)
            self.app.send_command('marq-marquee %s' % message)


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
