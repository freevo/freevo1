#if 0 /*
# -----------------------------------------------------------------------
# mplayer.py - Temporary implementation of a TV function using MPlayer
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
#
# -----------------------------------------------------------------------
# $Log$
# Revision 1.14  2003/08/06 19:32:40  dischi
# removed freevo_xwin support. Most users have problems with it and it works without it
#
# Revision 1.13  2003/08/05 18:37:02  dischi
# fix mplayer plugin to work with dfbmga, too
#
# Revision 1.12  2003/07/13 19:35:44  rshortt
# Change osd.focused_app to a function that returns the last object in
# app_list.  Maintaining this list is helpfull for managing 'toplevel'
# GUIObject based apps (popup types).
#
# Revision 1.11  2003/07/11 19:47:09  dischi
# close file after parsing
#
# Revision 1.10  2003/07/01 21:47:35  outlyer
# Made a check to see if file exists before unlinking.
#
# Revision 1.9  2003/07/01 20:35:58  outlyer
# Replaced the os.system('rm ...') calls with os.unlink()
#
# Revision 1.8  2003/06/23 20:15:25  the_krow
# Trivial Fix for mplayer command line with the new runtime. Thanks to
# mikeruelle in irc for the bugfix.
#
# Revision 1.7  2003/06/13 01:06:46  outlyer
# Now using the URL format for channel specification in mplayer...
#
# tv://
#
# Revision 1.6  2003/06/04 23:01:44  rshortt
# Some event fixes but I can't test them with my card.
#
# Revision 1.5  2003/05/27 17:53:35  dischi
# Added new event handler module
#
# Revision 1.4  2003/04/29 20:59:04  outlyer
# Fixed a crash caused here, because this code was trying to append a str to a
# tuple; the proper way to do it (apparently) is to treat the string as a single
# item tuple, which is accomplished by adding a single comma after the str.
#
# Since I was using a virgin checkout from CVS, wasn't this breaking for everyone
# else?
#
# Revision 1.3  2003/04/26 20:55:44  dischi
# Removed MPLAYER_ARGS_* and added a hash MPLAYER_ARGS to set args for
# all different kinds of files. Also added MPLAYER_SOFTWARE_SCALER to use
# the software scaler for fast CPUs. Also fixed a small bug in mplayer.py
# for video.
#
# Revision 1.2  2003/04/24 11:51:46  dischi
# removed debug
#
# Revision 1.1  2003/04/22 19:34:16  dischi
# mplayer and tvtime are now plugins
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
#endif


# Configuration file. Determines where to look for AVI/MP3 files, etc
import config

import time, os
import threading
import signal

import util    # Various utilities
import osd     # The OSD class, used to communicate with the OSD daemon
import rc      # The RemoteControl class.
import event as em
import childapp # Handle child applications
import tv.epg_xmltv as epg # The Electronic Program Guide

import plugin

# Set to 1 for debug output
DEBUG = config.DEBUG

TRUE = 1
FALSE = 0


# Create the OSD object
osd = osd.get_singleton()

class PluginInterface(plugin.Plugin):
    """
    Plugin to watch tv with mplayer.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)

        # create the mplayer object and register it
        plugin.register(MPlayer(), plugin.TV)


class MPlayer:

    __muted    = 0
    __igainvol = 0
    
    def __init__(self):
        self.thread = MPlayer_Thread()
        self.thread.setDaemon(1)
        self.thread.start()
        self.tuner_chidx = 0    # Current channel, index into config.TV_CHANNELS
        self.app_mode = 'tv'


    def TunerSetChannel(self, tuner_channel):
        for pos in range(len(config.TV_CHANNELS)):
            channel = config.TV_CHANNELS[pos]
            if channel[2] == tuner_channel:
                self.tuner_chidx = pos
                return
        print 'ERROR: Cannot find tuner channel "%s" in the TV channel listing' % tuner_channel
        self.tuner_chidx = 0


    def TunerGetChannelInfo(self):
        '''Get program info for the current channel'''
        
        tuner_id = config.TV_CHANNELS[self.tuner_chidx][2]
        chan_name = config.TV_CHANNELS[self.tuner_chidx][1]
        chan_id = config.TV_CHANNELS[self.tuner_chidx][0]

        channels = epg.get_guide().GetPrograms(start=time.time(),
                                               stop=time.time(), chanids=[chan_id])

        if channels and channels[0] and channels[0].programs:
            start_s = time.strftime('%H:%M', time.localtime(channels[0].programs[0].start))
            stop_s = time.strftime('%H:%M', time.localtime(channels[0].programs[0].stop))
            ts = '(%s-%s)' % (start_s, stop_s)
            prog_info = '%s %s' % (ts, channels[0].programs[0].title)
        else:
            prog_info = 'No info'
            
        return tuner_id, chan_name, prog_info


    def TunerGetChannel(self):
        return config.TV_CHANNELS[self.tuner_chidx][2]


    def TunerNextChannel(self):
        self.tuner_chidx = (self.tuner_chidx+1) % len(config.TV_CHANNELS)


    def TunerPrevChannel(self):
        self.tuner_chidx = (self.tuner_chidx-1) % len(config.TV_CHANNELS)

        
    def Play(self, mode, tuner_channel=None, channel_change=0):

        if tuner_channel != None:
            
            try:
                self.TunerSetChannel(tuner_channel)
            except ValueError:
                pass

        if mode == 'tv':
            tuner_channel = self.TunerGetChannel()

            cf_norm, cf_input, cf_clist, cf_device = config.TV_SETTINGS.split()

            # Convert to MPlayer TV setting strings
            norm = 'norm=%s' % cf_norm.upper()
            tmp = { 'television':0, 'composite1':1, 'composite2':2,
                    's-video':3}[cf_input.lower()]
            input = 'input=%s' % tmp
            chanlist = 'chanlist=%s' % cf_clist
            device= 'device=%s' % cf_device
            
            w, h = config.TV_VIEW_SIZE
            outfmt = 'outfmt=%s' % config.TV_VIEW_OUTFMT

            tvcmd = ('tv://%s -tv driver=v4l:%s:%s:%s:'
                     '%s:width=%s:height=%s:%s' %
                     (tuner_channel, device, input, norm, chanlist, w, h, outfmt))
            
            # Build the MPlayer command
            args = (config.MPLAYER_NICE, config.MPLAYER_CMD, config.MPLAYER_VO_DEV,
                    config.MPLAYER_VO_DEV_OPTS, tvcmd)

            if config.MPLAYER_ARGS.has_key('tv'):
                args += (config.MPLAYER_ARGS['tv'],)

            mpl = '--prio=%s %s -vo %s%s -fs %s %s -slave' % args

        elif mode == 'vcr':
            cf_norm, cf_input, tmp, cf_device = config.VCR_SETTINGS.split()

            # Convert to MPlayer TV setting strings
            norm = 'norm=%s' % cf_norm.upper()
            tmp = { 'television':0, 'composite1':1, 'composite2':2,
                    's-video':3}[cf_input.lower()]
            input = 'input=%s' % tmp
            device= 'device=%s' % cf_device

            w, h = config.TV_VIEW_SIZE
            outfmt = 'outfmt=%s' % config.TV_VIEW_OUTFMT
            
            tvcmd = ('-tv on:driver=v4l:%s:%s:%s:channel=2:'
                     'chanlist=us-cable:width=%s:height=%s:%s' %
                     (device, input, norm, w, h, outfmt))

            args = (config.MPLAYER_CMD, config.MPLAYER_VO_DEV,
                    config.MPLAYER_VO_DEV_OPTS, tvcmd,
                    config.MPLAYER_ARGS_TVVIEW)
            mpl = '%s -vo %s%s -fs %s %s' % args

        else:
            print 'Mode "%s" is not implemented' % mode  # XXX ui.message()
            return

        command = mpl
        self.mode = mode


        # XXX Mixer manipulation code.
        # TV is on line in
        # VCR is mic in
        # btaudio (different dsp device) will be added later
        mixer = plugin.getbyname('MIXER')
        
        if mixer and config.MAJOR_AUDIO_CTRL == 'VOL':
            mixer_vol = mixer.getMainVolume()
            mixer.setMainVolume(0)
        elif mixer and config.MAJOR_AUDIO_CTRL == 'PCM':
            mixer_vol = mixer.getPcmVolume()
            mixer.setPcmVolume(0)

        # Start up the TV task
        self.thread.mode = 'play'
        self.thread.command = command
        self.thread.mode_flag.set()
        
        self.prev_app = rc.app()
        rc.app(self)

        if osd.focused_app():
            osd.focused_app().hide()

        # Suppress annoying audio clicks
        time.sleep(0.4)
        # XXX Hm.. This is hardcoded and very unflexible.
        if mixer and mode == 'vcr':
            mixer.setMicVolume(config.VCR_IN_VOLUME)
        elif mixer:
            mixer.setLineinVolume(config.TV_IN_VOLUME)
            mixer.setIgainVolume(config.TV_IN_VOLUME)
            
        if mixer and config.MAJOR_AUDIO_CTRL == 'VOL':
            mixer.setMainVolume(mixer_vol)
        elif mixer and config.MAJOR_AUDIO_CTRL == 'PCM':
            mixer.setPcmVolume(mixer_vol)

        if DEBUG: print '%s: started %s app' % (time.time(), self.mode)

        
        
    def Stop(self):
        mixer = plugin.getbyname('MIXER')
        mixer.setLineinVolume(0)
        mixer.setMicVolume(0)
        mixer.setIgainVolume(0) # Input on emu10k cards.

        self.thread.mode = 'stop'
        self.thread.mode_flag.set()

        rc.app(self.prev_app)
        if osd.focused_app():
            osd.focused_app().show()

        while self.thread.mode == 'stop':
            time.sleep(0.05)
        print 'stopped %s app' % self.mode
        if os.path.exists('/tmp/freevo.wid'): os.unlink('/tmp/freevo.wid')


    def eventhandler(self, event):
        print '%s: %s app got %s event' % (time.time(), self.mode, event)
        if event == em.STOP or event == em.PLAY_END:
            self.Stop()
            rc.post_event(em.PLAY_END)
            return TRUE
        
        elif event == em.TV_CHANNEL_UP or event == em.TV_CHANNEL_DOWN:
            if self.mode == 'vcr':
                return
            
            # Go to the prev/next channel in the list
            if event == em.TV_CHANNEL_UP:
                self.TunerNextChannel()
            else:
                self.TunerPrevChannel()

            new_channel = self.TunerGetChannel()
            self.thread.app.write('tv_set_channel %s\n' % new_channel)

            # Display a channel changed message
            # XXX Experimental, disabled for now
            #tuner_id, chan_name, prog_info = self.TunerGetChannelInfo()
            #now = time.strftime('%H:%M')
            #msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
            #cmd = 'show_osd_msg "%s" 4000\n' % msg
            #self.thread.app.write(cmd)
            return TRUE
            
        elif event == em.TOGGLE_OSD:
            return FALSE
        
            # Display the channel info message
            # XXX Experimental, disabled for now
            tuner_id, chan_name, prog_info = self.TunerGetChannelInfo()
            now = time.strftime('%H:%M')
            msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
            cmd = 'show_osd_msg "%s" 4000\n' % msg
            print 'msg = "%s" %s chars' % (msg, len(msg))
            self.thread.app.write(cmd)
            
        return FALSE
    

# ======================================================================
class MPlayerApp(childapp.ChildApp):
    """
    class controlling the in and output from the mplayer process
    """

    def __init__(self, app):
        if config.MPLAYER_DEBUG:
            startdir = os.environ['FREEVO_STARTDIR']
            fname_out = os.path.join(startdir, 'mplayer_stdout.log')
            fname_err = os.path.join(startdir, 'mplayer_stderr.log')
            try:
                self.log_stdout = open(fname_out, 'a')
                self.log_stderr = open(fname_err, 'a')
            except IOError:
                print
                print (('ERROR: Cannot open "%s" and "%s" for ' +
                        'MPlayer logging!') % (fname_out, fname_err))
                print 'Please set MPLAYER_DEBUG=0 in local_conf.py, or '
                print 'start Freevo from a directory that is writeable!'
                print
            else:
                print 'MPlayer logging to "%s" and "%s"' % (fname_out, fname_err)

        childapp.ChildApp.__init__(self, app)
        

    def kill(self):
        # Use SIGINT instead of SIGKILL to make sure MPlayer shuts
        # down properly and releases all resources before it gets
        # reaped by childapp.kill().wait()
        self.write('quit')
        childapp.ChildApp.kill(self, signal.SIGINT)

        # XXX Krister testcode for proper X11 video
        if DEBUG: print 'Killing mplayer'
        if config.MPLAYER_DEBUG:
            self.log_stdout.close()
            self.log_stderr.close()


    def stdout_cb(self, line):
        if config.MPLAYER_DEBUG:
            try:
                self.log_stdout.write(line + '\n')
            except ValueError:
                pass # File closed
                     

    def stderr_cb(self, line):
        if config.MPLAYER_DEBUG:
            try:
                self.log_stderr.write(line + '\n')
            except ValueError:
                pass # File closed


# ======================================================================
class MPlayer_Thread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        
        self.mode      = 'idle'
        self.mode_flag = threading.Event()
        self.command   = ''
        self.app       = None
        self.audioinfo = None              # Added to enable update of GUI

    def run(self):
        while 1:
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()
                
            elif self.mode == 'play':
                # The DXR3 device cannot be shared between our SDL session
                # and MPlayer.
                if (osd.sdl_driver == 'dxr3' or \
                    config.CONF.display == 'dfbmga'):
                    if DEBUG:
                        print "Stopping Display for Video Playback on DXR3"
                    osd.stopdisplay()			
                if DEBUG:
                    print 'MPlayer_Thread.run(): Started, cmd=%s' % self.command
                    
                self.app = MPlayerApp(self.command)
                
                while self.mode == 'play' and self.app.isAlive():
                    if self.audioinfo: 
                        if not self.audioinfo.pause:
                            self.audioinfo.draw()        
                    time.sleep(0.1)

                self.app.kill()

                # Ok, we can use the OSD again.
                if osd.sdl_driver == 'dxr3' or config.CONF.display == 'dfbmga':
                    osd.restartdisplay()
                    osd.update()
                    print "Display back online"

                if self.mode == 'play':
                    if DEBUG: print 'posting play_end'
                    rc.post_event(em.PLAY_END)

                self.mode = 'idle'
                
            else:
                self.mode = 'idle'

