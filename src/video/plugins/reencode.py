# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# re-encode recorded TV programmes
# -----------------------------------------------------------------------
# $Id: reencode.py $
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('video.reencode')
# ToDo:        
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


from os.path import join, split
import plugin
import menu
import config
from video.encodingclient import *
from gui.AlertBox import AlertBox
from gui.PopupBox import PopupBox

DEBUG = config.DEBUG
DEBUG = 9

print "DJW: reencode DEBUG=%s" % DEBUG

class PluginInterface(plugin.ItemPlugin):
    """
    Plug-in to archive recorded TV programmes using EncodingServer
    
    This plugin NEEDS a running encodingserver to work properly.
    You can start an encodingserver with "freevo encodingserver start".
    """

class PluginInterface(plugin.ItemPlugin):
    def __init__(self):
        _debug_('__init__')
        plugin.ItemPlugin.__init__(self)


    def actions(self, item):
        #testing stuff
        for d in dir(item):
            print '%s: %s' % (d, eval('item.%s' % d))
        for d in dir(item.info):
            print '%s: %s' % (d, eval('item.info.%s' % d))
        print 'type:', item.type
        if hasattr(item, 'mode'): print 'mode:', item.mode
        if hasattr(item, 'name'): print 'name:', type(item.name)
        if hasattr(item, 'name'): print 'name:', item.name.encode('utf-8')
        if hasattr(item, 'filename'): print 'filename:', item.filename
        if hasattr(item, 'parentname'):
            print item.parentname
        if hasattr(item, 'media'):
            print 'media:', item.media
            if hasattr(item.media, 'devicename'):
                print item.media.devicename
            
        if item.type == 'video' and item.mode == 'file':
                #for dvd on disc
                self.dvdsource = item.filename
                
                self.title = item.name
                self.source = item.filename
                self.filename = item.filename[0:item.filename.rfind('.')]+'.divx'

                self.item = item
                return [ (self.encoding_profile_menu, _('Re-encode this program...')) ]
        return []
        
    def encoding_profile_menu(self, menuw=None, arg=None):
        #create a menu with a few encoding options (1cd, 2cd, xvid, mpeg4)
        #args : tuple, (videocodec, size, multipass
        menu_items = [ menu.MenuItem("XViD, 700mb", self.create_job, (1,700,False)) ]
        menu_items.append( menu.MenuItem("XViD, 700mb, High Quality", self.create_job, (1,700,True)) )
        menu_items.append( menu.MenuItem("XViD, 1400mb", self.create_job, (1,1400,False)) )
        menu_items.append( menu.MenuItem("XViD, 1400mb, High Quality", self.create_job, (1,1400,True)) )
        menu_items.append( menu.MenuItem("DivX, 700mb", self.create_job, (0,700,False)) )
        menu_items.append( menu.MenuItem("DivX, 700mb, High Quality", self.create_job, (0,700,True)) )
        menu_items.append( menu.MenuItem("DivX, 1400mb", self.create_job, (0,1400,False)) )
        menu_items.append( menu.MenuItem("DivX, 1400mb, High Quality", self.create_job, (0,1400,True)) )
        
        encoding_menu = menu.Menu(_('Choose your encoding profile'), menu_items)
        menuw.pushmenu(encoding_menu)
        
    def create_job(self, menuw=None, arg=None):
        print 'arg:', arg
        #unwrap settings tupple
        vcodecnr, tgtsize, mpass = arg

        #we are going to create a job and send it to the encoding server, this can take some time while analyzing
        
        box = PopupBox(text=_('Please wait, analyzing video...'))
        box.show()

        (status, resp) = initEncodeJob(self.source, self.filename, self.title)
        print 'initEncodeJob:status:', status, ' resp:', resp
                
        box.destroy()
        
        if not status:
            self.error(resp)
            return
            
        idnr = resp
        
        #ask for possible containers and set the first one (should be avi), we will get a list
        (status, resp) = getContainerCAP(idnr)
        print 'getContainerCAP:status:', status, ' resp:', resp
            
        if not status:
            self.error(resp)
            return
        
        container = resp[0]
        
        (status, resp) = setContainer(idnr, container)
        print 'setContainer:status:', status, ' resp:', resp
        
        if not status:
            self.error(resp)
            return
            
        #ask for possible videocodec and set the first one (should be mpeg4), we will get a list
        (status, resp) = getVideoCodecCAP(idnr)
        print 'getVideoCodecCAP:status:', status, ' resp:', resp
            
        if not status:
            self.error(resp)
            return
        
        vcodec = resp[vcodecnr]
        
        (status, resp) = setVideoCodec(idnr, vcodec, tgtsize, mpass)
        print 'setVideoCodec:status:', status, ' resp:', resp
        
        if not status:
            self.error(resp)
            return
            
        #ask for possible audiocodec and set the first one (should be mp3), we will get a list
        #Audiocodec call isn't necessary atm, it defaults to 128 kbit mp3, but this might change in the future
        #so we play safe
        (status, resp) = getAudioCodecCAP(idnr)
        print 'getAudioCodecCAP:status:', status, ' resp:', resp
            
        if not status:
            self.error(resp)
            return
        
        acodec = resp[0]
        
        (status, resp) = setAudioCodec(idnr, acodec, 128)
        print 'setAudioCodec:status:', status, ' resp:', resp
        
        if not status:
            self.error(resp)
            return
        
        #And finally, qeue and start the job
        (status, resp) = queueIt(idnr, True)
        print 'queueIt:status:', status, ' resp:', resp
            
        if not status:
            self.error(resp)
            return
        
        self.menuw = menuw
        AlertBox(width=400, height=200, text=_("Encoding started"), handler=self.mopup).show()
        
        print "boe"
        #menuw.delete_menu()
        #menuw.delete_menu()       
        
        
        
    def error(self, text=""):
        AlertBox(width=400, height=200, text="ERROR: %s" % text).show()
        
    
    def mopup(self):
        self.menuw.delete_menu()
        self.menuw.back_one_menu()