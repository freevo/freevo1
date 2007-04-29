# encoding: utf-8

# Valere JEANTET RAMOS 2
# Copyright (c) 2006 Valère JEANTET RAMOS
# COOLLLO

import sys
import os
import codecs
import urllib

#regular expression
import re


#freevo modules
import config, menu, rc, plugin, skin, osd, util
from gui   import PopupBox, AlertBox, ConfirmBox
from item  import Item
from video import VideoItem

#get the singletons so we get skin info and access the osd
skin = skin.get_singleton()
osd  = osd.get_singleton()


class PluginInterface(plugin.MainMenuPlugin):
    """
    A plugin to obtain TV streams on Freevo

    To activate, put the following lines in local_conf.py:

    plugin.activate('freeboxtv', level=45)
    PLUGIN_FREEBOXTV_LOCATION = "http://mafreebox.freebox.fr/freeboxtv/playlist.m3u"
    plugin.activate('video.vlc')
    # ================
    # VLC Settings :
    # ================
    VLC_NICE    = -30
    VLC_CMD     = CONF.vlc

    dans /etc/freevo/freevo.conf
    rajouter
    vlc = /usr/bin/vlc
    """
    # make an init func that creates the cache dir if it don't exist
    def __init__(self):
        if not hasattr(config, 'PLUGIN_FREEBOXTV_LOCATION'):
            PLUGIN_FREEBOXTV_LOCATION = "http://mafreebox.freebox.fr/freeboxtv/playlist.m3u"
        plugin.MainMenuPlugin.__init__(self)


    def config(self):
        return [('PLUGIN_FREEBOXTV_LOCATION',\
            "http://mafreebox.freebox.fr/freeboxtv/playlist.m3u",\
            "Location url to grab streams list" )]


    def items(self, parent):
        return [ FreeboxTVMainMenu(parent) ]



class FreeboxTVMainMenu(Item):
    """
    this is the item for the main menu and creates the list
    of TV channels in a submenu.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='tv')
        self.parent = parent
        self.name   = _('Freebox TV')


    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.create_Streamslocation_menu , _('Freebox TV :: Les chaines') ) ]
        return items


    def __call__(self, arg=None, menuw=None):
        """
        call first action in the actions() list
        """
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)


    def create_Streamslocation_menu(self, arg=None, menuw=None):
        chaines_items  = []
        lesFlux = []
        autoselect = 0

        # recuperation des chaines dans le tableau lesFlux
        lesFlux = self.getChaines(config.PLUGIN_FREEBOXTV_LOCATION)
        keys = lesFlux.keys()
        keys.sort()

        for c_name in keys:
            chaine_item = ChaineItem(self, c_name,lesFlux[c_name])
            #chaine_item = VideoItem(self, lesFlux[location],self.parent)
            #chaine_item.name = location

            # Only display this entry if no errors were found
            chaines_items.append ( chaine_item )

        # if only 1 valid location, autoselect it and go right to the detail screen

        # if no locations were found, add a menu entry indicating that
        if not chaines_items:
            nolocation = menu.MenuItem(_('No locations specified'), menuw.goto_prev_page, 0)
            chaines_items.append( nolocation )

        # create menu
        freeboxtv_site_menu = menu.Menu(_('Freebox TV :: Les chaines Multiposte'), chaines_items)
        menuw.pushmenu(freeboxtv_site_menu)
        menuw.refresh()


    def getChaines(self,zeUrl):
        filehandle = urllib.urlopen(zeUrl)
        i = "o"
        d = {}
        while i <> "":
            if re.search ( '#EXTINF', i ):
                result = re.match('#EXTINF:.* - (.*)',i)
                i=filehandle.readline()
                d[result.group(1)] = i[0:len(i)-1]
            i=filehandle.readline()

        return d



class ChaineItem(VideoItem):
    """
    Item for the menu for one rss feed
    """
    def __init__(self, parent, flux_name,flux_location):
        VideoItem.__init__(self, flux_location, parent)
        self.network_play = True
        self.parent       = parent
        self.location     = flux_location
        self.name         = flux_name.decode('utf8')
        self.type = 'video'
        self.force_player = 'vlc'



if __name__ == '__main__':
    print "Plugin Freevo for Freebox :: http://www.sodadi.com/freevo/freebox"
