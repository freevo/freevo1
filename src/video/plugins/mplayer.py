# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo video module for MPlayer
# -----------------------------------------------------------------------
# $Id$
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

"""
Freevo video module for MPlayer
"""

import os, re
import threading
import popen2
import kaa.metadata as mmpython

import config     # Configuration handler. reads config file.
import util       # Various utilities
import childapp   # Handle child applications
import rc         # The RemoteControl class.
import plugin
import dialog
from dialog.display import AppTextDisplay

import osd
osd = osd.get_singleton()

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

        self.event_context = 'video'
        self.seek       = 0
        self.seek_timer = threading.Timer(0, self.reset_seek)
        self.app        = None
        self.plugins    = []
        self.paused     = False
        self.stored_time_info = None


    def rate(self, item):
        """
        How good can this player play the file:
        2 = good
        1 = possible, but not good
        0 = unplayable
        """
        if not item.url:
            return 0
        # this seems strange that it is 'possible' for dvd:// and 'good' for dvd
        # possible because dvd:// should be played with xine when available!
        if item.url[:6] in ('dvd://', 'vcd://') and item.url.endswith('/'):
            _debug_('mplayer rating: %r possible' % (item.url), 2)
            return 1
        if item.mode in ('dvd', 'vcd'):
            _debug_('mplayer rating: %r good' % (item.url), 2)
            return 2
        if item.mode in ('http') and not item.filename and not item.media:
            _debug_('mplayer rating: %r good' % (item.url), 2)
            return 2
        if item.mimetype in config.VIDEO_MPLAYER_SUFFIX:
            _debug_('mplayer rating: %r good' % (item.url), 2)
            return 2
        if item.network_play:
            _debug_('mplayer rating: %r possible' % (item.url), 2)
            return 1
        _debug_('mplayer rating: %r unplayable' % (item.url), 2)
        return 0


    def play(self, options, item):
        """
        play a videoitem with mplayer
        """
        _debug_('options=%r' % (options,), 2)
        for k, v in item.__dict__.items():
            _debug_('item[%s]=%r' % (k, v), 2)

        mode         = item.mode
        url          = item.url

        self.options = options
        self.item    = item
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

        url=Unicode(url)
        try:
            _debug_('MPlayer.play(): mode=%s, url=%s' % (mode, url))
        except UnicodeError:
            _debug_('MPlayer.play(): [non-ASCII data]')

        if mode == 'file' and not os.path.isfile(url):
            # This event allows the videoitem which contains subitems to
            # try to play the next subitem
            return '%s\nnot found' % os.path.basename(url)

        set_vcodec = False
        if item['xvmc'] and item['type'][:6] in ['MPEG-1', 'MPEG-2', 'MPEG-T']:
            set_vcodec = True

        mode = item.mimetype
        if not config.MPLAYER_ARGS.has_key(mode):
            _debug_('MPLAYER_ARGS not defined for %r, using default' % mode, DINFO)
            mode = 'default'

        _debug_('mode=%s args=%s'% (mode, config.MPLAYER_ARGS[mode]))
        # Build the MPlayer command
        args = {
            'nice': config.MPLAYER_NICE,
            'cmd': config.MPLAYER_CMD,
            'vo': '-vo %s' % config.MPLAYER_VO_DEV,
            'vo_opts': config.MPLAYER_VO_DEV_OPTS,
            'vc': '',
            'ao': '-ao %s' % config.MPLAYER_AO_DEV,
            'ao_opts': config.MPLAYER_AO_DEV_OPTS,
            'default_args': config.MPLAYER_ARGS_DEF,
            'mode_args': config.MPLAYER_ARGS[mode],
            'fxd_args': ' '.join(options),
            'geometry': '',
            'verbose': '',
            'dvd-device': '',
            'cdrom-device': '',
            'alang': '',
            'aid': '',
            'slang': '',
            'sid': '',
            'playlist': '',
            'field-dominance': '',
            'edl': '',
            'mc': '',
            'delay': '',
            'sub': '',
            'audiofile': '',
            'af': [],
            'vf': [],
            'url': url,
            'disable_osd': False,
            'start_position': [],
        }

        if item['resume']:
            t = int(item['resume'])
            info = mmpython.parse(item.filename)
            if hasattr(info, 'seek') and t:
                args['start_position']=['-sb' , str(info.seek(t))]
            else:
                args['start_position']=['-ss', str(t)]

        if config.CONF.x or config.CONF.y:
            args['geometry'] = '-geometry %d:%d' % (config.CONF.x, config.CONF.y)

        if config.DEBUG_CHILDAPP:
            args['verbose'] = '-v'

        if mode == 'dvd':
            if config.DVD_LANG_PREF:
                # There are some bad mastered DVDs out there. E.g. the specials on
                # the German Babylon 5 Season 2 disc claim they have more than one
                # audio track, even more then on en. But only the second en works,
                # mplayer needs to be started without -alang to find the track
                if hasattr(item, 'mplayer_audio_broken') and item.mplayer_audio_broken:
                    print '*** dvd audio broken, try without alang ***'
                else:
                    args['alang'] = '-alang %s' % config.DVD_LANG_PREF

            if config.DVD_SUBTITLE_PREF:
                # Only use if defined since it will always turn on subtitles when defined
                args['slang'] = '-slang %s' % config.DVD_SUBTITLE_PREF

        if mode == 'dvd':
            # dvd on harddisc
            args['dvd-device'] = '%s' % item.filename
            args['url'] = url[:6] + url[url.rfind('/')+1:]
        elif mode != 'file' and hasattr(item.media, 'devicename'):
            args['dvd-device'] = '%s' % item.media.devicename

        if item.media and hasattr(item.media, 'devicename'):
            args['cdrom-device'] = '%s' % item.media.devicename

        if item.selected_subtitle == -1:
            args['sid'] = '-noautosub'
        elif item.selected_subtitle is not None:
            if mode == 'file':
                if os.path.isfile(os.path.splitext(item.filename)[0]+'.idx'):
                    args['sid'] = '-vobsubid %s' % str(item.selected_subtitle)
                else:
                    args['sid'] = '-sid %s' % str(item.selected_subtitle)
            else:
                args['sid'] = '-sid %s' % str(item.selected_subtitle)

        if item.selected_audio is not None:
            args['aid'] = '-aid %s' % str(item.selected_audio)

        # This comes from the bilingual language selection menu
        if hasattr(item, 'selected_language') and item.selected_language:
            if item.selected_language == 'left':
                args['af'].append('pan=2:1:1:0:0')
            elif item.selected_language == 'right':
                args['af'].append('pan=2:0:0:1:1')

        if not set_vcodec:
            if item['deinterlace'] and config.MPLAYER_VF_INTERLACED:
                args['vf'].append(config.MPLAYER_VF_INTERLACED)
            elif config.MPLAYER_VF_PROGRESSIVE:
                args['vf'].append(config.MPLAYER_VF_PROGRESSIVE)

        if config.VIDEO_FIELD_DOMINANCE is not None:
            args['field-dominance'] = '-field-dominance %d' % int(item['field-dominance'])

        if os.path.isfile(os.path.splitext(item.filename)[0]+'.edl'):
            args['edl'] = '-edl %s' % str(os.path.splitext(item.filename)[0]+'.edl')

        if dialog.overlay_display_supports_dialogs:
            # Disable the mplayer OSD if we have a better option.
            args['disable_osd'] = True

        # Mplayer command and standard arguments
        if set_vcodec:
            if item['deinterlace']:
                bobdeint='bobdeint'
            else:
                bobdeint='nobobdeint'
            args['vo'] = '-vo xvmc:%s' % bobdeint
            args['vc'] = '-vc ffmpeg12mc'

        if hasattr(item, 'is_playlist') and item.is_playlist:
            args['playlist'] = '-playlist'

        if args['fxd_args'].find('-playlist') > 0:
            args['fxd_args'] = args['fxd_args'].replace('-playlist', '')
            args['playlist'] = '-playlist'
       
        # correct avi delay based on kaa.metadata settings
        if config.MPLAYER_SET_AUDIO_DELAY and item.info.has_key('delay') and item.info['delay'] > 0:
            args['mc'] = '-mc %s' % str(int(item.info['delay'])+1)
            args['delay'] = '-delay -%s' % str(item.info['delay'])

        # autocrop
        if config.MPLAYER_AUTOCROP and not item.network_play and args['fxd_args'].find('crop=') == -1:
            _debug_('starting autocrop')
            (x1, y1, x2, y2) = (1000, 1000, 0, 0)
            crop_points = config.MPLAYER_AUTOCROP_START
            if not isinstance(crop_points, list):
                crop_points = [crop_points]

            for crop_point in crop_points:
                (x1, y1, x2, y2) = self.get_crop(crop_point, x1, y1, x2, y2)

            if x1 < 1000 and x2 < 1000:
                args['vf'].append('crop=%s:%s:%s:%s' % (x2-x1, y2-y1, x1, y1))
                _debug_('crop=%s:%s:%s:%s' % (x2-x1, y2-y1, x1, y1))

        if item.subtitle_file:
            d, f = util.resolve_media_mountdir(item.subtitle_file)
            util.mount(d)
            args['sub'] = '-sub %s' % f

        if item.audio_file:
            d, f = util.resolve_media_mountdir(item.audio_file)
            util.mount(d)
            args['audiofile'] = '-audiofile %s' % f

        self.plugins = plugin.get('mplayer_video')
        for p in self.plugins:
            command = p.play(command, self)

        vo = ['%(vo)s' % args, '%(vo_opts)s' % args]
        vo = filter(len, vo)
        vo = ':'.join(vo)

        ao = ['%(ao)s' % args, '%(ao_opts)s' % args]
        ao = filter(len, ao)
        ao = ':'.join(ao)

        # process the mplayer options extracting video and audio filters
        args['default_args'], args = self.find_filters(args['default_args'], args)
        args['mode_args'], args = self.find_filters(args['mode_args'], args)
        args['fxd_args'], args = self.find_filters(args['fxd_args'], args)

        command = ['--prio=%(nice)s' % args]
        command += ['%(cmd)s' % args]
        command += ['-slave']
        command += str('%(verbose)s' % args).split()
        command += str('%(geometry)s' % args).split()
        command += vo.split()
        command += str('%(vc)s' % args).split()
        command += ao.split()
        command += args['dvd-device'] and ['-dvd-device', '%(dvd-device)s' % args] or []
        command += args['cdrom-device'] and ['-cdrom-device', '%(cdrom-device)s' % args] or []
        command += str('%(alang)s' % args).split()
        command += str('%(aid)s' % args).split()
        command += str('%(audiofile)s' % args).split()
        command += str('%(slang)s' % args).split()
        command += str('%(sid)s' % args).split()
        command += str('%(sub)s' % args).split()
        command += str('%(field-dominance)s' % args).split()
        command += str('%(edl)s' % args).split()
        command += str('%(mc)s' % args).split()
        command += str('%(delay)s' % args).split()
        command += args['default_args'].split()
        command += args['mode_args'].split()
        command += args['fxd_args'].split()
        command += args['af'] and ['-af', '%s' % ','.join(args['af'])] or []
        command += args['vf'] and ['-vf', '%s' % ','.join(args['vf'])] or []
        command += args['disable_osd'] and ['-osdlevel', '0'] or []
        command += args['start_position']

        if config.OSD_SINGLE_WINDOW:
            command += ['-wid', str(osd.video_window.id)]
            

        # use software scaler?
        #XXX these need to be in the arg list as the scaler will add vf args
        if '-nosws' in command:
            command.remove('-nosws')
        elif '-framedrop' not in command:
            command += config.MPLAYER_SOFTWARE_SCALER.split()

        command = filter(len, command)

        command += str('%(playlist)s' % args).split()
        command += ['%(url)s' % args]

        _debug_(' '.join(command[1:]))

        #if plugin.getbyname('MIXER'):
            #plugin.getbyname('MIXER').reset()

        self.paused = False

        rc.add_app(self)
        self.app = MPlayerApp(command, self)
        dialog.enable_overlay_display(AppTextDisplay(self.show_message))
        return None


    def stop(self):
        """
        Stop mplayer
        """
        for p in self.plugins:
            command = p.stop()

        if not self.app:
            return
        
        if config.OSD_SINGLE_WINDOW:
            osd.video_window.hide()
            osd.video_window.set_geometry((0,0), (config.CONF.width,config.CONF.height))
        self.app.stop('quit\n')
        rc.remove_app(self)
        dialog.disable_overlay_display()
        self.app = None


    def eventhandler(self, event, menuw=None):
        """
        eventhandler for mplayer control. If an event is not bound in this
        function it will be passed over to the items eventhandler
        """
        _debug_('%s.eventhandler(event=%s)' % (self.__class__, event))
        if not self.app:
            return self.item.eventhandler(event)

        for p in self.plugins:
            if p.eventhandler(event):
                return True

        if event == VIDEO_MANUAL_SEEK:
            self.seek = 0
            rc.set_app_context(self, 'input')
            dialog.show_message("input")
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
                rc.set_app_context(self, 'video')
                return True

            elif event == INPUT_EXIT:
                _debug_('seek stopped')
                #self.app.write('seek stopped\n')
                self.seek_timer.cancel()
                self.seek = 0
                rc.set_app_context(self, 'video')
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
            if dialog.is_dialog_supported():
                if self.paused:
                    dialog.show_play_state(dialog.PLAY_STATE_INFO, self.item, self.get_stored_time_info)
                else:
                    dialog.show_play_state(dialog.PLAY_STATE_INFO, self.item, self.get_time_info)
            else:
                self.paused = False
                self.app.write('osd\n')
            return True

        if event == PAUSE or event == PLAY:
            self.paused = not self.paused
            # We have to store the current time before displaying the dialog
            # otherwise the act of requesting the current position resumes playback!
            if self.paused:
                self.stored_time_info = self.get_time_info()
                dialog.show_play_state(dialog.PLAY_STATE_PAUSE, self.item, self.get_stored_time_info)
                self.app.write('pause\n')
            else:
                self.app.write('speed_set 1.0\n')
                dialog.show_play_state(dialog.PLAY_STATE_PLAY, self.item, self.get_time_info)

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

                    dialog.show_message(_('Seeking not possible'))
                    return False
            
            self.paused = False
            self.app.write('seek %s\n' % event.arg)
            if event.arg > 0:
                dialog.show_play_state(dialog.PLAY_STATE_SEEK_FORWARD, self.item, self.get_time_info)
            else:
                dialog.show_play_state(dialog.PLAY_STATE_SEEK_BACK, self.item, self.get_time_info)
            return True

        if event == VIDEO_AVSYNC:
            self.app.write('audio_delay %g\n' % event.arg);
            return True

        if event == VIDEO_NEXT_AUDIOLANG:
            self.app.write('switch_audio\n')
            return True

        if event == VIDEO_NEXT_SUBTITLE:
            self.app.write('sub_select\n')
            return True

        if event == OSD_MESSAGE:
            self.show_message(event.arg)
            return True

        if event == 'MPLAYER_VO':
            if config.OSD_SINGLE_WINDOW:
                w_ratio = float(config.CONF.width) / float(event.arg[0])
                h_ratio = float(config.CONF.height) / float(event.arg[1])
                ratio = min(w_ratio, h_ratio)
                w = int(event.arg[0] * ratio)
                h = int(event.arg[1] * ratio)
                x = (config.CONF.width - w) / 2
                y = (config.CONF.height - h) / 2
                osd.video_window.set_geometry((x,y), (w,h))
                osd.video_window.show()
            return True

        # nothing found? Try the eventhandler of the object who called us
        return self.item.eventhandler(event)

    def show_message(self, message):
        self.app.write('osd_show_text "%s"\n' % message);

    def reset_seek(self):
        _debug_('seek timeout')
        self.seek = 0
        rc.set_app_context(self, 'video')


    def reset_seek_timeout(self):
        self.seek_timer.cancel()
        self.seek_timer = threading.Timer(config.MPLAYER_SEEK_TIMEOUT, self.reset_seek)
        self.seek_timer.start()


    def find_filters(self, arg, args):
        old_options = arg.split('-')
        new_options = []
        for i in range(len(old_options)):
            pair = old_options[i].split()
            if len(pair) == 2:
                if pair[0] == 'vf':
                    args['vf'].append(pair[1])
                    continue
                elif pair[0] == 'af':
                    args['af'].append(pair[1])
                    continue
            new_options.append(old_options[i])
        arg = '-'.join(new_options)
        return arg, args


    def sort_filter(self, command):
        """
        Change a mplayer command to support more than one -vf parameter. This
        function will grep all -vf parameter from the command and add it at the
        end as one vf argument
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

    def get_stored_time_info(self):
        return self.stored_time_info

    def get_time_info(self):
        time_pos = self.app.get_property('time_pos')
        length = self.app.get_property('length')
        percent_pos = self.app.get_property('percent_pos')
        if time_pos and length and percent_pos:
            return (int(float(time_pos)), int(float(length)), int(percent_pos) / 100.0)
        else:
            return None

# ======================================================================


class MPlayerApp(childapp.ChildApp2):
    """
    class controlling the in and output from the mplayer process
    """

    def __init__(self, command, mplayer):
        self.RE_TIME   = re.compile("^[AV]: *([0-9]+)").match
        self.RE_VO     = re.compile("^VO: \[.+\] \d+x\d+ => (\d+)x(\d+)").match
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
        self.osd     = osd.get_singleton()
        self.osdfont = self.osd.getfont(config.OSD_DEFAULT_FONTNAME, config.OSD_DEFAULT_FONTSIZE)

        # check for mplayer plugins
        self.stdout_plugins  = []
        self.elapsed_plugins = []
        for p in plugin.get('mplayer_video'):
            if hasattr(p, 'stdout'):
                self.stdout_plugins.append(p)
            if hasattr(p, 'elapsed'):
                self.elapsed_plugins.append(p)

        self.output_event = threading.Event()
        self.get_property_ans = None
        # init the child (== start the threads)
        childapp.ChildApp2.__init__(self, command, callback_use_rc=False)

    def get_property(self, property):
        self.get_property_ans = None
        self.output_event.clear()
        self.write('get_property %s\n' % property)
        self.output_event.wait(config.MPLAYER_PROPERTY_TIMEOUT)
        return self.get_property_ans

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
                self.osd.drawstringframed(line, config.OSD_OVERSCAN_LEFT+10, config.OSD_OVERSCAN_TOP+10,
                    self.osd.width - (config.OSD_OVERSCAN_LEFT+10 + config.OSD_OVERSCAN_RIGHT+10),
                    -1, self.osdfont, self.osd.COL_WHITE)
                self.osd.update()


        # current elapsed time
        if line.startswith("A:") or line.startswith("V:"):
            m = self.RE_TIME(line)
            if hasattr(m, 'group') and self.item.elapsed != int(m.group(1))+1:
                self.item.elapsed = int(m.group(1))+1
                for p in self.elapsed_plugins:
                    p.elapsed(self.item.elapsed)

        elif line.startswith('VO:'):
            m = self.RE_VO(line)
            if m:
                w = int(m.group(1))
                h = int(m.group(2))
                Event('MPLAYER_VO', (w,h)).post()
                
        # exit status
        elif line.find("Exiting...") == 0:
            m = self.RE_EXIT(line)
            if m:
                self.exit_type = m.group(1)
            if self.output_event.isSet():
                self.output_event.set()

        elif line.startswith('ANS_'):
            prop,ans = line.split('=')
            self.get_property_ans = ans.strip()
            self.output_event.set()

        # this is the first start of the movie, parse info
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
        if line.startswith('Failed to get value of property '):
            self.output_event.set()

        for p in self.stdout_plugins:
            p.stdout(line)
