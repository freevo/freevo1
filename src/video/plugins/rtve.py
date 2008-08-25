# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in for streaming programs from rtve.es
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#   Add "plugin.activate('video.rtve')" in local_conf.py
#   to activate
# Todo:
#
# -----------------------------------------------------------------------
# Copyright (C) 2008 Krister Lagerstrom, et al.
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

import os
import urllib

import config
import plugin
import menu
import stat
import time
import string
import util.fileops
import util.misc

from item import Item
from video.videoitem import VideoItem
from gui.ProgressBox import ProgressBox
from gui.PopupBox import PopupBox

import rtvelib

MAX_CACHE_AGE = (5*5*60) # 5 minutos

cachedir = os.path.join(config.FREEVO_CACHEDIR, 'rtve')
if not os.path.isdir(cachedir):
    os.mkdir(cachedir,
            stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))

def _fetch_image(url):
    idx = url.rfind('/')
    if idx == -1:
        return None

    fn = url[(idx+1):]
    fn = os.path.join(cachedir, fn)

    if not os.path.exists(fn):
        urllib.urlretrieve(url, fn)

    return fn

class PluginInterface(plugin.MainMenuPlugin):
    """
    A freevo interface to http://www.rtve.es
    plugin.activate('video.rtve')
    OPTIONAL: RTVE_BLACKLIST = ['berni','identity']
    """
    def __init__(self):
        plugin.MainMenuPlugin.__init__(self)

    def items(self, parent):
        return [ BrowseBy(parent) ]

class RtveItem(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.type = 'dir'
        self.skin_display_type = 'video'
        self.__load()

    def __progress(self, percent):
        if percent > self.__last_perc:
            for i in xrange(percent - self.__last_perc):
                self.__pop.tick()
            self.__last_perc = percent

    def __load(self):
        
        if hasattr(config, 'RTVE_BLACKLIST'):
            blackList = config.RTVE_BLACKLIST
        else:
            blackList = None
                    
        pfile = os.path.join(cachedir, 'data')

        if (os.path.isfile(pfile) == 0):
            self.programacion = rtvelib.Programacion()
            self.__pop = ProgressBox(text=_('Escaneando la web de RTVE...'), full=100)
            self.__pop.show()
            self.__last_perc = -1
            self.programacion.parse(self.__progress,blackList)
            self.__pop.destroy()
            util.fileops.save_pickle(self.programacion, pfile)
        else:
            if abs(time.time() - os.path.getmtime(pfile)) > MAX_CACHE_AGE:
                self.programacion = rtvelib.Programacion()
                self.__pop = ProgressBox(text=_('Escaneando la web de RTVE...'), full=100)
                self.__pop.show()
                self.__last_perc = -1
                self.programacion.parse(self.__progress,blackList)
                self.__pop.destroy()
                util.fileops.save_pickle(self.programacion, pfile)
            else:
                self.programacion = util.fileops.read_pickle(pfile)
        

class ProgramaVideoItem(VideoItem):
    def __init__(self, menu_entry, programa, parent):
        VideoItem.__init__(self, programa["flv"], parent)
        
        self.mode = ''
        self.files = ''
        self.image = _fetch_image(programa['image'])
        
        if menu_entry == _("Reproducir a pantalla completa (16:9)"):
            self.mplayer_options = "-vf crop=624:351:0:58"
        
        self.name = menu_entry
        

class MenuPrograma(Item):
    def __init__(self, programa, parent):
        Item.__init__(self, parent)
        self.name = programa["nombre"]
        self.type = 'video'

        self.mode = ''
        self.files = ''
        self.image = _fetch_image(programa['image'])
        self.description = 'Canal: ' + programa['canal']
        self.description += '\nFecha de emision: ' + programa['fecha']
        self.description += '\nDescripcion: ' + programa['descripcion']

        self._programa = programa

    def actions(self):
        return [ (self.make_menu, 'Streams') ]

    def download_play(self, arg=None, menuw=None):
        pop = PopupBox("Descargando programa")
        pop.show()
        video = VideoItem(_fetch_image(arg['flv']), self)
        pop.destroy()
        video.image = _fetch_image(arg['image'])
        video.menuw = menuw
        video.play()

    def make_menu(self, arg=None, menuw=None):
        entries = []
        entries.append(ProgramaVideoItem(_("Reproducir"),self._programa,self))
        entries.append(ProgramaVideoItem(_("Reproducir a pantalla completa"),self._programa,self))
        #entries.append(menu.MenuItem('Descargar y reproducir', self.download_play, self._programa, self))
        menuw.pushmenu(menu.Menu(self.name, entries))

class Title(Item):
    def __init__(self, name, programa, parent):
        Item.__init__(self, parent)
        self.name = name
        self.image = _fetch_image(programa['image'])
        self._programa = programa

    def actions(self):
        return [ (self.make_menu, 'Programas') ]

    def make_menu(self, arg=None, menuw=None):
        entries = []
        i = 1
        for programa in self._programa["programas"]:
            name = "Programa %d" % i
            entries.append(Programa(name, self._programa, self))
            i += 1
        menuw.pushmenu(menu.Menu(self.name, entries))

class BrowseByTitle(RtveItem):
    def __init__(self, parent):
        RtveItem.__init__(self, parent)
        self.name = _('Elegir por Nombre del Programa')
        self.programa = _('Programas')

    def actions(self):
        return [ (self.make_menu, 'Nombres') ]

    def make_menu(self, arg=None, menuw=None):
        entries = []
        for name in self.programacion.sort_by_title():
            programa = self.programacion.programas[name]

            #makes a menu for each item
            entries.append(MenuPrograma(programa, self))

            #plays directly
            #entries.append(ProgramaVideoItem(programa['nombre'],programa,self))

        menuw.pushmenu(menu.Menu(self.programa, entries))

class Canal(BrowseByTitle):
    def __init__(self, canal, parent):
        BrowseByTitle.__init__(self, parent)
        self.name = canal
        self.programa = canal
        self.programacion.only_canal(canal)

class BrowseByCanal(RtveItem):
    def __init__(self, parent):
        RtveItem.__init__(self, parent)
        self.name = _('Elegir por Canal')

    def actions(self):
        return [ (self.make_menu, 'Canales') ]

    def make_menu(self, arg=None, menuw=None):
        canales = []
        canales.append(Canal('La Primera',self))
        canales.append(Canal('La 2',self))
        menuw.pushmenu(menu.Menu(_('Elige un canal'), canales))

class BrowseBy(Item):
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.name = 'Programas de RTVE'
        self.type = 'programas'

    def actions(self):
        return [ (self.make_menu, 'Browse by') ]

    def make_menu(self, arg=None, menuw=None):
        menuw.pushmenu(menu.Menu('Programas RTVE',
                [ BrowseByCanal(self),
                  BrowseByTitle(self)  ]))
