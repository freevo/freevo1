# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# idlebar.py - IdleBar plugin
# -----------------------------------------------------------------------
# $Id$
#
# Documentation moved to the corresponding classes, so that the help
# interface returns something usefull.
# Available plugins:
#       idlebar
#       idlebar.clock
#       idlebar.cdstatus
#       idlebar.mail
#       idlebar.tv
#       idlebar.weather
#       idlebar.holidays
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the Licestringnse, or
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

# python modules
import time
import os
import locale

# freevo modules
import config
import plugin
import skin
from pygame import image, transform



class PluginInterface(plugin.DaemonPlugin):
    """
    global idlebar plugin.
    """

    def __init__(self):
        """
        init the idlebar
        """
        plugin.DaemonPlugin.__init__(self)
        self.poll_interval  = 3000
        self.poll_menu_only = False
        self.plugins = None
        plugin.register(self, 'idlebar')
        self.visible = True
        self.bar     = None
        self.barfile = ''
        self.free_space = -1
        self.used_space = 0

        # Getting current LOCALE
        try:
            locale.resetlocale()
        except:
            pass


    def take_space(self, space):
        '''
        reserve some space from the idlebar, this is for DaemonPlugins
        '''
        self.used_space = space


    def draw(self, (type, object), osd):
        """
        draw a background and all idlebar plugins
        """
        w = osd.width + 2 * osd.x
        h = osd.y + 60

        f = skin.get_image('idlebar')

        if self.barfile != f:
            self.barfile = f
            try:
                self.bar = transform.scale(image.load(f).convert_alpha(), (w, h))
            except:
                self.bar = None

        # draw the cached barimage
        if self.bar:
            osd.drawimage(self.bar, (0, 0, w, h), background=True)

        if not self.plugins:
            self.plugins = plugin.get('idlebar')

        x = osd.x + 10
        for p in self.plugins:
            add_x = p.draw((type, object), x, osd)
            if add_x:
                x += add_x + 20
        self.free_space = x - self.used_space


    def eventhandler(self, event, menuw=None):
        """
        catch the IDENTIFY_MEDIA event to redraw the skin (maybe the cd status
        plugin wants to redraw)
        """
        if plugin.isevent(event) == 'IDENTIFY_MEDIA' and skin.active():
            skin.redraw()
        return False


    def poll(self):
        """
        update the idlebar every 30 secs even if nothing happens
        """
        if skin.active():
            skin.redraw()



class IdleBarPlugin(plugin.Plugin):
    """
    To activate the idle bar, put the following in your local_conf.py:
    | plugin.activate('idlebar')

    You can then add various plugins. Plugins inside the idlebar are
    sorted based on the level (except the clock, it's always on the
    right side). Use "freevo plugins -l" to see all available plugins,
    and "freevo plugins -i idlebar.<plugin>" for a specific plugin.
    """
    def __init__(self):
        plugin.Plugin.__init__(self)
        self._type = 'idlebar'

    def draw(self, (type, object), x, osd):
        return



class clock(IdleBarPlugin):
    """
    Shows the current time.

    Activate with:
    plugin.activate('idlebar.clock', level=50)
    Note: The clock will always be displayed on the right side of
    the idlebar.
    """
    def __init__(self, format=''):
        IdleBarPlugin.__init__(self)
        if config.CLOCK_FORMAT:
            format = config.CLOCK_FORMAT
        # No overiding of the default value
        elif not format:
            if time.strftime('%P') == '':
                format ='%a %H:%M'
            else:
                format ='%a %I:%M %P'
        self.timeformat = format

    def draw(self, (type, object), x, osd):
        clock = Unicode(time.strftime(self.timeformat))
        font  = osd.get_font('clock')
        pad_x = 10
        idlebar_height = 60

        w = font.stringsize(clock)
        h = font.font.height
        if h > idlebar_height:
            h = idlebar_height
        osd.write_text(clock, font, None, (osd.x + osd.width - w -pad_x), (osd.y + (idlebar_height - h) / 2),
            (w + 1), h , 'right', 'center')
        self.clock_left_position = osd.x + osd.width - w - pad_x
        return 0



class logo(IdleBarPlugin):
    """
    Display the freevo logo in the idlebar
    """
    def __init__(self, image=None):
        IdleBarPlugin.__init__(self)
        self.image = image

    def draw(self, (type, object), x, osd):
        if not self.image:
            image = osd.settings.images['logo']
        else:
            image = os.path.join(config.IMAGE_DIR, self.image)
        return osd.drawimage(image, (x, osd.y + 5, -1, 75))[0]
