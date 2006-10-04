import config

import time, os
import threading
import signal
import skin


import util    # Various utilities
from event import *
import osd     # The OSD class, used to communicate with the OSD daemon
import rc      # The RemoteControl class.
import childapp # Handle child applications
import tv.epg_xmltv as epg # The Electronic Program Guide
import tv.ivtv as ivtv
import plugin

#import event as em 
from tv.channels import FreevoChannels


from event import *

import plugin

# Set to 1 for debug output
DEBUG = config.DEBUG

TRUE = 1
FALSE = 0


# Create the OSD object
osd = osd.get_singleton()

class PluginInterface(plugin.Plugin):
    """
    Plugin to watch tv with xine.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)

        plugin.register(IVTV_TV(), plugin.TV)


class IVTV_TV:

    __muted    = 0
    __igainvol = 0
    
    def __init__(self):
        self.thread = Xine_Thread()
        self.thread.setDaemon(1)
        self.thread.start()
        self.tuner_chidx = 0    # Current channel, index into config.TV_CHANNELS
        self.app_mode = 'tv'
        self.app       = None
        self.videodev = None
        self.fc = FreevoChannels() 
        self.current_vg = None 


        
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

        print 'PLAY CHAN: %s' % tuner_channel

        if tuner_channel != None:
            
            try:
                self.TunerSetChannel(tuner_channel)
            except ValueError:
                pass

        if not tuner_channel: 
            tuner_channel = self.fc.getChannel()
            print 'PLAY CHAN: %s' % tuner_channel

        vg = self.current_vg = self.fc.getVideoGroup(tuner_channel) 
        print 'PLAY GROUP: %s' % vg.desc

        if mode == 'tv':                
         if vg.group_type == 'ivtv':
            ivtv_dev = ivtv.IVTV(vg.vdev)
            ivtv_dev.init_settings()
            ivtv_dev.setinput(vg.input_num)
# CO by JM           ivtv_dev.print_settings()
            self.fc.chanSet(tuner_channel)

#            command = '%s -V --no-splash --no-lirc --stdctl pvr://' % config.XINE_COMMAND
            command = '%s -V --no-splash --no-lirc --stdctl %s pvr:///home/livetv' % (config.XINE_COMMAND, config.XINE_ARGS_DEF)
        else:
            print 'Mode "%s" is not implemented' % mode  # XXX ui.message()
            return


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
        #JM +PLAY_END
        rc.post_event(PLAY_END)
        if osd.focused_app():
           osd.focused_app().show() 
           
        while self.thread.mode == 'stop':
            time.sleep(0.05)
        print 'stopped %s app' % self.mode



    def eventhandler(self, event, menuw=None):
        print '%s: %s app got %s event' % (time.time(), self.mode, event)
        s_event = '%s' % event

# The following events need to be defined in events.py (check that) first

#        if event == FASTFORWARD:
#            self.thread.app.write('SpeedFaster\n')
#            return True

#        if event == REWIND:
#            self.thread.app.write('SpeedSlower\n')
#            return True
  
        if event == MIXER_VOLUP:
            self.thread.app.write('Volume+\n')
            return True

        if event == MIXER_VOLDOWN:
            self.thread.app.write('Volume-\n')
            return True
    
        if event == STOP or event == PLAY_END:
            self.Stop()
            rc.post_event(PLAY_END)
            return TRUE
        
        if event == PAUSE or event == PLAY:
            self.thread.app.write('pause\n')
            return True

#        if event == UP:
#            self.thread.app.write('EventUp\n')
#            return True

#        if event == DOWN:
#            self.thread.app.write('EventDown\n')
#            return True


        if event == MENU_GOTO_MAINMENU:
            self.thread.app.write('TitleMenu\n')
            return True

# Add to events.py
#        if event == SUBTITLE:
#            self.thread.app.write('SpuNext\n')
#            return True
    
        if event == STOP:
            self.thread.app.write('Quit\n')
            for i in range(10):
                if self.thread.mode == 'idle':
                    break
                time.sleep(0.3)
            else:
                # sometimes xine refuses to die
                self.Stop()
            return TRUE

#        if event == STOP:
#            self.stop()
#            return self.item.eventhandler(event)
     
        if event in [ TV_CHANNEL_UP, TV_CHANNEL_DOWN] or s_event.startswith('INPUT_'):
            if event == TV_CHANNEL_UP:
                nextchan = self.fc.getNextChannel()
            elif event == TV_CHANNEL_DOWN:
                nextchan = self.fc.getPrevChannel()
            else:
                chan = int( s_event[6] )
                nextchan = self.fc.getManChannel(chan)
                

           # tuner_id, chan_name, prog_info = self.fc.getChannelInfo()
           # now = time.strftime('%H:%M')
           # msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
           #cmd = 'osd_show_text "%s"\n' % msg 
            
            print 'NEXT CHAN: %s' % nextchan
            nextvg = self.fc.getVideoGroup(nextchan)
            print 'NEXT GROUP: %s' % nextvg.desc

            if self.current_vg != nextvg:
                self.Stop(channel_change=1)
                self.Play('tv', nextchan)
                return TRUE

            if self.mode == 'vcr':
                return   

            elif self.current_vg.group_type == 'ivtv':
                self.fc.chanSet(nextchan)
                self.thread.app.write('seek 999999 0\n')
            else:
                freq_khz = self.fc.chanSet(nextchan, app=self.thread.app)
                new_freq = '%1.3f' % (freq_khz / 1000.0)
                self.thread.app.write('tv_set_freq %s\n' % new_freq)
        
            self.current_vg = self.fc.getVideoGroup(self.fc.getChannel())
            
            # Display a channel changed message  (mplayer ?  api osd xine ?) 
            tuner_id, chan_name, prog_info = self.fc.getChannelInfo()
            now = time.strftime('%H:%M')
            msg = '%s %s (%s): %s' % (now, chan_name, tuner_id, prog_info)
            cmd = 'osd_show_text "%s"\n' % msg
            self.thread.app.write(cmd)
            return TRUE
            

        if event == SEEK:
            pos = int(event.arg)
            if pos < 0:
                action='SeekRelative-'
                pos = 0 - pos
            else:
                action='SeekRelative+'
            if pos <= 15:
                pos = 15
            elif pos <= 30:
                pos = 30
            else:
                pos = 30
            self.thread.app.write('%s%s\n' % (action, pos))
            return TRUE 
        
        if event == TOGGLE_OSD:
            self.thread.app.write('OSDStreamInfos\n')
            return True
                   
# ======================================================================

class XineApp(childapp.ChildApp):
    """
    class controlling the in and output from the xine process
    """

    def __init__(self, app, item):
        self.item = item
        childapp.ChildApp.__init__(self, app)
        self.exit_type = None
        
    def kill(self):
        # Use SIGINT instead of SIGKILL to make sure Xine shuts
        # down properly and releases all resources before it gets
        # reaped by childapp.kill().wait()
        #childapp.ChildApp.kill(self, signal.SIGINT)
        #JM change to SIGKILL to test resolution for freevo crash from df_xine crash
        childapp.ChildApp.kill(self, signal.SIGTERM)


# ======================================================================

class Xine_Thread(threading.Thread):
    """
    Thread to wait for a xine command to play
    """

    def __init__(self):
        threading.Thread.__init__(self)
        
        self.mode      = 'idle'
        self.mode_flag = threading.Event()
        self.command   = ''
        self.app       = None
        self.item  = None

        
    def run(self):
        while 1:
            if self.mode == 'idle':
                self.mode_flag.wait()
                self.mode_flag.clear()

            elif self.mode == 'play':
                if DEBUG:
                    print 'Xine_Thread.run(): Started, cmd=%s' % self.command
                    
                self.app = XineApp(self.command, self.item)

                while self.mode == 'play' and self.app.isAlive():
                    time.sleep(0.1)

                self.app.kill()

                if self.mode == 'play':
                    if DEBUG: print 'posting play_end'
                    rc.post_event(PLAY_END)
                        
                if DEBUG:
                    print 'Xine_Thread.run(): Stopped'

                self.mode = 'idle'
                
            else:
                self.mode = 'idle'
