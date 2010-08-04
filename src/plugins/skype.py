# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# skype.py - a simple plugin to use Skype
# -----------------------------------------------------------------------
# Author: Grzegorz Szostak (szostak.grzegorz@gmail.com)
# Author Skype: grzegorz_szostak_mob
# Author WWW: http://www.szostak.eu/
#
# Notes:
# Todo:
# activate:
# plugin.activate('skype', level=45)
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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



#python modules
import os, time, stat, re, copy
#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui.PopupBox import PopupBox
from item import Item
from skin.widgets import ScrollableTextScreen
#skype module
import Skype4Py

#get the singletons so we get skin info and access the osd
skin_object = skin.get_singleton()
osd  = osd.get_singleton()

skin_object.register('skype', ('screen', 'title', 'scrollabletext', 'plugin'))

class PluginInterface(plugin.MainMenuPlugin):
    """
    A plugin to make and receive skype calls.
    How to configure skype on your board:
    First, install and configure skype in normal X11 environment on your HTPC.
    While running skype in normal X11 session, run python script with
    this lines:
    ------------------------------------------------------------------
    from Skype4Py import *
    skype = Skype()
    skype.Attach()
    skype.PlaceCall('echo123')
    ------------------------------------------------------------------
    Look at skype client interface, it will ask you for permission
    for Skype4Py to use skype API. Allow it to use skype.
    After this, you should connect to skype test account (echo123 user).
    You should full test sound, mic. Call will be automaticaly dropped
    from skype side.
    Close skype.
    After that, you must copy all contents of ~/.Skype director form
    home of the user which was running skype to /home/freevo user
    As freevo user cd to home directory and run command:
        cp -a /home/$user/.Skype /, where $user is name of the user you ware
    logged in while using skype as described above. Then change ownership
    of coppied files:
        chown -R root /.Skype
    Set skype client to start at boot time within Xvfb (install it if you don't have it).
    Now you have configured skype for user freevo to use it with Freevo.

    To activate, put the following lines in local_conf.py:

    | plugin.activate('skype', level=45)
    | SKYPE_DISPLAY=':2' # May be any display name but must be the same as it is for skype
    | SKYPE_AVATAR_CACHE = '/dir' # Path where we store avatars for our contacts from skype
    """

    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)
    def config(self):
        return [('Skype',
                [ ("Contacts", "") ],
                'Contacts')]

    def items(self, parent):
        return [ SkypeMainMenuItem(parent) ]

class SkypeMainMenuItem(Item):
    """
    This is class for the main menu and creates of skype contacts
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='skype')
        self.name = _('Skype')
        self.skype = SkypeApi()
        self.parent = parent
        self.arg = ('Skype', 0)
        self.type='main'

    def actions(self):
        items = [ (self.createSkypeContactList, _('Skype Contacts')) ]
        return items

    def createSkypeContactList(self, arg=None, menuw=None):
        skype_contacts = []
        for user in self.skype.GetContacts():
            skype_contact_item = SkypeContactItem(self)
            skype_contact_item.name = user[0]
            skype_contact_item.user_handle = user[1].Handle
            skype_contact_item.location_index = 1
            skype_contact_item.arg = arg
            skype_contact_item.menuw = menuw
            skype_contacts.append(skype_contact_item)

        skype_menu = menu.Menu(_('Skype Contact List'), skype_contacts)
        menuw.pushmenu(skype_menu)
        menuw.refresh()

class SkypeContactItem(Item):
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='skype')
        self.user_handle = ''
        self.location_index = None
        self.name = ''
        self.arg = None
        self.menuw = None
        self.parent = parent
        self.active_call = None

    def actions(self):
        if not self.parent.skype.IsCallActive():
            items = [ (self.PlaceCall, _('Make Call')) ]
        else:
            items = [ (self.JoinCall, _('Join Call')) ]
        return items

    def PlaceCall(self, arg, menuw):
        self.active_call = self.parent.skype.PlaceCall(self.user_handle)
        # TODO add end call
        items = []
        items.append(menu.MenuItem(_('End Call'), parent=self, action=self.EndCall, arg=self.active_call))
        menuw.pushmenu(menu.Menu(_('Active Call'), items))
        menuw.refresh()
        self.DrawCallInfo()
        return

    def EndCall(self, arg, menuw):
        popup = PopupBox(text=_('Ending conversation..'))
        popup.show()
        try:
            #arg.Finish()
            self.parent.skype.GetCallObject().Finish()
            while not (self.parent.skype.IsTerminated()):
                pass
        finally:
            popup.destroy()
        menuw.back_one_menu(arg='reload')
        return

    def JoinCall(self, arg, menuw):
        items = []
        items.append(menu.MenuItem(_('End Call'), parent=self, action=self.EndCall, arg=self.active_call))
        menuw.pushmenu(menu.Menu(_('Active Call'), items))
        menuw.refresh()
        self.DrawCallInfo()
        return

    def DrawCallInfo(self):
        skin.draw()

class MySkypeEvents:
    """
    This class is for callback which are called when some events
    on skype client occures. It is designed to retrieve info about
    connection status to Freevo plugin interface.
    """
# Constructor, it takes one argument which is callable function which
# must take only one argument, where call back function will send status
# retrieved from skype.
    def __init__(self, callback):
        self.statusCall = callback


# Called when Call Status has changed
    def CallStatus(self, call, status):
        self.statusCall(status)
        print 'Call status: ' + self.CallStatusText(status)


# Called whern Attach to Skype status has changed
    def AttachmentStatus(self, status):
        self.statusCall(status)
        print 'Attach status: ' + self.AttachmentStatusText(status)
        if status == Skype4Py.apiAttachAvailable:
            self.skype.Attach();


# Convert status into human redable text
    def AttachmentStatusText(self,status):
        return Skype4Py.Skype().Convert.AttachmentStatusToText(status)


# Convert status into human redable text
    def CallStatusText(self,status):
        return Skype4Py.Skype().Convert.CallStatusToText(status)

class SkypeApi:
    """
    This class encapsulates Skype API. It is called from inside
    Freevo plugin to manage connections, get contacts, make calls
    """
    def __init__(self):
# Link beetween skype client and Skype4Py is configured to use dbus transport
# which is not default setting (default is to use x11). This because
# Freevo and its plugins are not run in skype X11 server environment
        self.oryginal_display = os.environ['DISPLAY']
        self.virtual_display = config.SKYPE_DISPLAY
        self.SetVirtualDisplay(True)
        self.api = Skype4Py.Skype(Events=MySkypeEvents(self.SetCallStatus), Transport='x11') # TODO Move it to configuration
        self.api.Attach()
        self.SetVirtualDisplay(False)
# In this variable (self.CallStatus) we will store all status information
# refering to skype status
        self.CallStatus = 0
        self.CallIsFinished = set ([Skype4Py.clsFailed, Skype4Py.clsFinished, Skype4Py.clsMissed, Skype4Py.clsRefused, Skype4Py.clsBusy, Skype4Py.clsCancelled])

    def SetVirtualDisplay(self, set=True):
        if set:
            os.environ['DISPLAY'] = self.virtual_display
        else:
            os.environ['DISPLAY'] = self.oryginal_display

# This makes call to skype user name or full phone number.
# Full phone number means +CTNNNNNNNNN where CT means country code.
    def PlaceCall(self, user_handler):
        return self.api.PlaceCall(user_handler)

# This is our interface for call back class to get status from inside skype
    def SetCallStatus(self, status):
        self.CallStatus = status

# Returns true if call is terminated regarding the reason
    def IsTerminated(self):
        if self.CallStatus in self.CallIsFinished:
            return True
        return False

    def GetContacts(self):
        items = []
        for user in self.api.Friends:
            name = ''
            for display_name in (user.FullName, user.DisplayName, user.Handle):
                if len(display_name) != 0:
                    name = display_name
                    break
            self.SaveAvatar(user)
            items.append( (name, user) )
        return items

    def GetCallStatus(self):
        return self.CallStatus

    def IsCallActive(self):
        if self.CallStatus in [ Skype4Py.clsInProgress, Skype4Py.clsRinging, Skype4Py.clsEarlyMedia ]:
            return True
        return False

    def GetCallObject(self):
        if(len(self.api.ActiveCalls)):
            return self.api.ActiveCalls[0]
        return None

    def SaveAvatar(self, user_object, dir=config.SKYPE_AVATAR_CACHE):
        return # does not work on linux
        path = dir + '/' + user_object.Handle + '.jpg'
        user_object.SaveAvatarToFile(path)
