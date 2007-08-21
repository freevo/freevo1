# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# mplayer.py - the Freevo MPlayer module for video
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


import os, re
import threading
import popen2
import kaa.metadata as mmpython

import config     # Configuration handler. reads config file.
import util       # Various utilities
import childapp   # Handle child applications
import rc         # The RemoteControl class.
import plugin

from event import *


class PluginInterface(plugin.Plugin):
    """
    Mplayer plugin for the video player.

    With this plugin Freevo can play all video files defined in
    VIDEO_MPLAYER_SUFFIX. This is the default video player for Freevo.
    """
    def __init__(self):
        # create plugin structure
        plugin.Plugin.__init__(self)
        # register mplayer as the object to play video
        plugin.register(MPlayer(), plugin.VIDEO_PLAYER, True)



class MPlayer:
    """
    the main class to control mplayer
    """
    def __init__(self):
        """
        init the mplayer object
        """
        self.name       = 'mplayer'

        self.app_mode   = 'video'
        self.seek       = 0
        self.seek_timer = threading.Timer(0, self.reset_seek)
        self.app        = None
        self.plugins    = []


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        # this seems strange that it is 'possible' for dvd:// and 'good' for dvd
        if item.url[:6] in ('dvd://', 'vcd://') and item.url.endswith('/'):
            return 1
        if item.mode in ('dvd', 'vcd'):
            return 2
        if item.mimetype in config.VIDEO_MPLAYER_SUFFIX:
            if config.DEBUG >= 4:
                for d in dir(item):
                    print '%s: %s' % (d, eval('item.%s' % d))
                for d in dir(item.info):
                    print '%s: %s' % (d, eval('item.info.%s' % d))
            return 2
        if item.network_play:
            return 1
        return 0


    def play(self, options, item):
        """
        play a videoitem with mplayer
        """
        self.options = options
        self.item    = item

        mode         = item.mode
        url          = item.url

        self.item_info    = None
        self.item_length  = -1
        self.item.elapsed = 0

        if mode == 'file':
            url = item.url[6:]
            self.item_info = mmpython.parse(url)
            if hasattr(self.item_info, 'get_length'):
                self.item_length = self.item_info.get_endpos()
                self.dynamic_seek_control = True

        if url.startswith('dvd://') and url[-1] == '/':
            url += '1'

        if url == 'vcd://':
            c_len = 0
            for i in range(len(item.info.tracks)):
                if item.info.tracks[i].length > c_len:
                    c_len = item.info.tracks[i].length
                    url = item.url + str(i+1)

        try:
            _debug_('MPlayer.play(): mode=%s, url=%s' % (mode, url))
        except UnicodeError:
            _debug_('MPlayer.play(): [non-ASCII data]')

        if mode == 'file' and not os.path.isfile(url):
            # This event allows the videoitem which contains subitems to
            # try to play the next subitem
            return '%s\nnot found' % os.path.basename(url)

        set_vcodec = False
        if item['xvmc'] and item['type'][:6] in ['MPEG-1','MPEG-2','MPEG-T']:
            set_vcodec = True

        # Build the MPlayer command
        command = ['--prio=%s' % config.MPLAYER_NICE, config.MPLAYER_CMD]
        command += ['-slave']
        command += config.MPLAYER_ARGS_DEF.split(' ')
        command += ['-ao'] + config.MPLAYER_AO_DEV.split(' ')

        additional_args = []

        if mode == 'dvd':
            if config.DVD_LANG_PREF:
                # There are some bad mastered DVDs out there. E.g. the specials on
                # the German Babylon 5 Season 2 disc claim they have more than one
                # audio track, even more then on en. But only the second en works,
                # mplayer needs to be started without -alang to find the track
                if hasattr(item, 'mplayer_audio_broken') and item.mplayer_audio_broken:
                    print '*** dvd audio broken, try without alang ***'
                else:
                    additional_args += ['-alang', config.DVD_LANG_PREF]

            if config.DVD_SUBTITLE_PREF:
                # Only use if defined since it will always turn on subtitles
                # if defined
                additional_args += ['-slang', config.DVD_SUBTITLE_PREF]

        if hasattr(item.media, 'devicename') and mode != 'file':
            additional_args += ['-dvd-device', item.media.devicename]
        elif mode == 'dvd':
            # dvd on harddisc
            additional_args += ['-dvd-device', item.filename]
            url = url[:6] + url[url.rfind('/')+1:]

        if item.media and hasattr(item.media,'devicename'):
            additional_args += ['-cdrom-device', item.media.devicename]

        if item.selected_subtitle == -1:
            additional_args += ['-noautosub']
        elif item.selected_subtitle != None:
            if mode == 'file':
                if os.path.isfile(os.path.splitext(item.filename)[0]+'.idx'):
                    additional_args += ['-vobsubid', str(item.selected_subtitle)]
                else:
                    additional_args += ['-sid', str(item.selected_subtitle)]
            else:
                additional_args += ['-sid', str(item.selected_subtitle)]

        if item.selected_audio != None:
            additional_args += ['-aid', str(item.selected_audio)]

        # This comes from the bilingual language selection menu
        if hasattr(item, 'selected_language') and item.selected_language:
            if item.selected_language == 'left':
                additional_args += ['-af', 'pan=2:1:1:0:0']
            elif item.selected_language == 'right':
                additional_args += ['-af', 'pan=2:0:0:1:1']

        if not set_vcodec:
            if item['deinterlace'] and config.MPLAYER_VF_INTERLACED:
                additional_args += ['-vf', config.MPLAYER_VF_INTERLACED]
            elif config.MPLAYER_VF_PROGRESSIVE:
                additional_args += ['-vf', config.MPLAYER_VF_PROGRESSIVE]

        if hasattr(config, 'VIDEO_FIELD_DOMINANCE') and config.VIDEO_FIELD_DOMINANCE != None:
            additional_args += ['-field-dominance', '%d' % int(item['field-dominance'])]

        if os.path.isfile(os.path.splitext(item.filename)[0]+'.edl'):
            additional_args += ['-edl', str(os.path.splitext(item.filename)[0]+'.edl')]

        mode = item.mimetype
        if not config.MPLAYER_ARGS.has_key(mode):
            mode = 'default'

        if config.CHILDAPP_DEBUG:
            command += ['-v']

        # Mplayer command and standard arguments
        if set_vcodec:
            if item['deinterlace']:
                bobdeint='bobdeint'
            else:
                bobdeint='nobobdeint'
            command += ['-vo', 'xvmc:%s' % bobdeint, '-vc', 'ffmpeg12mc']
        else:
            command += ['-vo', config.MPLAYER_VO_DEV + config.MPLAYER_VO_DEV_OPTS]

        # mode specific args
        command += config.MPLAYER_ARGS[mode].split(' ')

        # make the options a list
        command += additional_args

        if hasattr(item, 'is_playlist') and item.is_playlist:
            command.append('-playlist')

        # add the file to play
        command.append(url)

        if options:
            command += options

        # use software scaler?
        if '-nosws' in command:
            command.remove('-nosws')

        elif not '-framedrop' in command:
            command += config.MPLAYER_SOFTWARE_SCALER.split(' ')

        # correct avi delay based on kaa.metadata settings
        if config.MPLAYER_SET_AUDIO_DELAY and item.info.has_key('delay') and \
               item.info['delay'] > 0:
            command += ['-mc', str(int(item.info['delay'])+1), '-delay',
                         '-' + str(item.info['delay'])]

        while '' in command:
            command.remove('')

        # autocrop
        if config.MPLAYER_AUTOCROP and not item.network_play and str(' ').join(command).find('crop=') == -1:
            _debug_('starting autocrop')
            (x1, y1, x2, y2) = (1000, 1000, 0, 0)
            crop_points = config.MPLAYER_AUTOCROP_START
            if not isinstance(crop_points, list):
                crop_points = [crop_points]

            for crop_point in crop_points:
                (x1, y1, x2, y2) = self.get_crop(crop_point, x1, y1, x2, y2)

            if x1 < 1000 and x2 < 1000:
                command = command + ['-vf' , 'crop=%s:%s:%s:%s' % (x2-x1, y2-y1, x1, y1)]
                _debug_('crop=%s:%s:%s:%s' % (x2-x1, y2-y1, x1, y1))


        if item.subtitle_file:
            d, f = util.resolve_media_mountdir(item.subtitle_file)
            util.mount(d)
            command += ['-sub', f]

        if item.audio_file:
            d, f = util.resolve_media_mountdir(item.audio_file)
            util.mount(d)
            command += ['-audiofile', f]

        self.plugins = plugin.get('mplayer_video')

        for p in self.plugins:
            command = p.play(command, self)

        command=self.sort_filter(command)

        #_debug_(' '.join(command))

        #if plugin.getbyname('MIXER'):
            #plugin.getbyname('MIXER').reset()

        rc.app(self)

        self.app = MPlayerApp(command, self)
        return None


    def stop(self):
        """
        Stop mplayer
        """
        for p in self.plugins:
            command = p.stop()

        if not self.app:
            return

        self.app.stop('quit\n')
        rc.app(None)
        self.app = None


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for mplayer control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        if not self.app:
            return self.item.eventhandler(event)

        for p in self.plugins:
            if p.eventhandler(event):
                return True

        if event == VIDEO_MANUAL_SEEK:
            self.seek = 0
            rc.set_context('input')
            self.app.write('osd_show_text "input"\n')
            return True

        if event.context == 'input':
            if event in INPUT_ALL_NUMBERS:
                self.reset_seek_timeout()
                self.seek = self.seek * 10 + int(event);
                return True

            elif event == INPUT_ENTER:
                self.seek_timer.cancel()
                self.seek *= 60
                self.app.write('seek ' + str(self.seek) + ' 2\n')
                _debug_("seek "+str(self.seek)+" 2\n")
                self.seek = 0
                rc.set_context('video')
                return True

            elif event == INPUT_EXIT:
                _debug_('seek stopped')
                #self.app.write('seek stopped\n')
                self.seek_timer.cancel()
                self.seek = 0
                rc.set_context('video')
                return True

        if event == STOP:
            self.stop()
            return self.item.eventhandler(event)

        if event == 'AUDIO_ERROR_START_AGAIN':
            self.stop()
            self.play(self.options, self.item)
            return True

        if event in (PLAY_END, USER_END):
            self.stop()
            return self.item.eventhandler(event)

        if event == VIDEO_SEND_MPLAYER_CMD:
            self.app.write('%s\n' % event.arg)
            return True

        if event == TOGGLE_OSD:
            self.app.write('osd\n')
            return True

        if event == PAUSE or event == PLAY:
            self.app.write('pause\n')
            return True

        if event == SEEK:
            if event.arg > 0 and self.item_length != -1 and self.dynamic_seek_control:
                # check if the file is growing
                if self.item_info.get_endpos() == self.item_length:
                    # not growing, deactivate this
                    self.item_length = -1

                self.dynamic_seek_control = False

            if event.arg > 0 and self.item_length != -1:
                # safety time for bad mplayer seeking
                seek_safety_time = 20
                if self.item_info['type'] in ('MPEG-PES', 'MPEG-TS'):
                    seek_safety_time = 500

                # check if seek is allowed
                if self.item_length <= self.item.elapsed + event.arg + seek_safety_time:
                    # get new length
                    self.item_length = self.item_info.get_endpos()

                # check again if seek is allowed
                if self.item_length <= self.item.elapsed + event.arg + seek_safety_time:
                    _debug_('unable to seek %s secs at time %s, length %s' % \
                            (event.arg, self.item.elapsed, self.item_length))
                    self.app.write('osd_show_text "%s"\n' % _('Seeking not possible'))
                    return False

            self.app.write('seek %s\n' % event.arg)
            return True

        if event == VIDEO_AVSYNC:
            self.app.write('audio_delay %g\n' % event.arg);
            return True

        if event == OSD_MESSAGE:
            self.app.write('osd_show_text "%s"\n' % event.arg);
            return True

        # nothing found? Try the eventhandler of the object who called us
        return self.item.eventhandler(event)


    def reset_seek(self):
        _debug_('seek timeout')
        self.seek = 0
        rc.set_context('video')


    def reset_seek_timeout(self):
        self.seek_timer.cancel()
        self.seek_timer = threading.Timer(config.MPLAYER_SEEK_TIMEOUT, self.reset_seek)
        self.seek_timer.start()


    def sort_filter(self, command):
        """
        Change a mplayer command to support more than one -vf
        parameter. This function will grep all -vf parameter from
        the command and add it at the end as one vf argument
        """
        ret = []
        vf = ''
        next_is_vf = False

        for arg in command:
            if next_is_vf:
                vf += ',%s' % arg
                next_is_vf = False
            elif (arg == '-vf'):
                next_is_vf=True
            else:
                ret += [arg]

        if vf:
            return ret + ['-vf', vf[1:]]
        return ret

    def get_crop(self, pos, x1, y1, x2, y2):
        crop_cmd = [config.MPLAYER_CMD, '-ao', 'null', '-vo', 'null', '-slave', '-nolirc',
            '-ss', '%s' % pos, '-frames', '10', '-vf', 'cropdetect']
        crop_cmd.append(self.item.url)
        child = popen2.Popen3(self.sort_filter(crop_cmd), 1, 100)
        exp = re.compile('^.*-vf crop=([0-9]*):([0-9]*):([0-9]*):([0-9]*).*')
        while(1):
            data = child.fromchild.readline()
            if not data:
                break
            m = exp.match(data)
            if m:
                x1 = min(x1, int(m.group(3)))
                y1 = min(y1, int(m.group(4)))
                x2 = max(x2, int(m.group(1)) + int(m.group(3)))
                y2 = max(y2, int(m.group(2)) + int(m.group(4)))
                _debug_('x1=%s x2=%s y1=%s y2=%s' % (x1, x2, y1, y2))

        child.wait()
        return (x1, y1, x2, y2)




# ======================================================================


class MPlayerApp(childapp.ChildApp2):
    """
    class controlling the in and output from the mplayer process
    """

    def __init__(self, command, mplayer):
        self.RE_TIME   = re.compile("^A: *([0-9]+)").match
        self.RE_START  = re.compile("^Starting playback\.\.\.").match
        self.RE_EXIT   = re.compile("^Exiting\.\.\. \((.*)\)$").match
        self.item      = mplayer.item
        self.mplayer   = mplayer
        self.exit_type = None

        # DVD items also store mplayer_audio_broken to check if you can
        # start them with -alang or not
        if hasattr(self.item, 'mplayer_audio_broken') or self.item.mode != 'dvd':
            self.check_audio = 0
        else:
            self.check_audio = 1

        import osd
        self.osd       = osd.get_singleton()
        self.osdfont   = self.osd.getfont(config.OSD_DEFAULT_FONTNAME,
                                          config.OSD_DEFAULT_FONTSIZE)

        # check for mplayer plugins
        self.stdout_plugins  = []
        self.elapsed_plugins = []
        for p in plugin.get('mplayer_video'):
            if hasattr(p, 'stdout'):
                self.stdout_plugins.append(p)
            if hasattr(p, 'elapsed'):
                self.elapsed_plugins.append(p)

        # init the child (== start the threads)
        childapp.ChildApp2.__init__(self, command)


    def stop_event(self):
        """
        return the stop event send through the eventhandler
        """
        if self.exit_type == "End of file":
            return PLAY_END
        elif self.exit_type == "Quit":
            return USER_END
        else:
            return PLAY_END


    def stdout_cb(self, line):
        """
        parse the stdout of the mplayer process
        """
        # show connection status for network play
        if self.item.network_play:
            if line.find('Opening audio decoder') == 0:
                self.osd.clearscreen(self.osd.COL_BLACK)
                self.osd.update()
            elif (line.startswith('Resolving ') or \
                  line.startswith('Connecting to server') or \
                  line.startswith('Cache fill:')) and \
                  line.find('Resolving reference to') == -1:

                if line.startswith('Connecting to server'):
                    line = 'Connecting to server'
                self.osd.clearscreen(self.osd.COL_BLACK)
                self.osd.drawstringframed(line, config.OSD_OVERSCAN_X+10,
                                          config.OSD_OVERSCAN_Y+10,
                                          self.osd.width - 2 * (config.OSD_OVERSCAN_X+10),
                                          -1, self.osdfont, self.osd.COL_WHITE)
                self.osd.update()


        # current elapsed time
        if line.find("A:") == 0:
            m = self.RE_TIME(line)
            if hasattr(m,'group') and self.item.elapsed != int(m.group(1))+1:
                self.item.elapsed = int(m.group(1))+1
                for p in self.elapsed_plugins:
                    p.elapsed(self.item.elapsed)


        # exit status
        elif line.find("Exiting...") == 0:
            m = self.RE_EXIT(line)
            if m:
                self.exit_type = m.group(1)


        # this is the first start of the movie, parse infos
        elif not self.item.elapsed:
            for p in self.stdout_plugins:
                p.stdout(line)

            if self.check_audio:
                if line.find('MPEG: No audio stream found -> no sound') == 0:
                    # OK, audio is broken, restart without -alang
                    self.check_audio = 2
                    self.item.mplayer_audio_broken = True
                    rc.post_event(Event('AUDIO_ERROR_START_AGAIN'))

                if self.RE_START(line):
                    if self.check_audio == 1:
                        # audio seems to be ok
                        self.item.mplayer_audio_broken = False
                    self.check_audio = 0



    def stderr_cb(self, line):
        """
        parse the stderr of the mplayer process
        """
        for p in self.stdout_plugins:
            p.stdout(line)
