# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Allows selecting aspect ratio and cropping to fill screen with movie
# -----------------------------------------------------------------------
# $Id
#
# Notes: Allows selecting aspect ratio and cropping to fill screen
#
# Changelog
#
# 1.0
#
#     Initial release
#
# Todo
#
#   Make it work with Xine
#
# Activate by adding the following to local_conf.py:
#
# | plugin.activate('video.fillscreen')
# | MONITOR_ASPECT = '16:9'
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
# with self program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
#
# -----------------------------------------------------------------------
import logging
logger = logging.getLogger("freevo.video.plugins.fillscreen")

import menu
import config
import plugin
import event as em

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin allows selecting aspect ratio and calculates cropping to
    fill screen. Useful for watching videos with other aspect ratio than
    freevo's monitor, maximizing display size.
    To activate add this to your local_conf.py:

    plugin.activate('video.fillscreen')
    MONITOR_ASPECT = '16:9'

    Config parameters:

        - Required:

            - MONITOR_ASPECT: something like 16:9, 4:3, etc

        - Optional:

            - ASPECTS: list of aspects you want in the video submenu separated by
            comma; defaults to '16:9,4:3,14:9,16:10'

            - AUTOFILL_ASPECT: if current video's detected aspect matches this
            value it will be automatically changed to
            PREFERRED_ASPECT_FOR_AUTOFILL without entering the menu. Example:
            '4:3'

            - PREFERRED_ASPECT_FOR_AUTOFILL: See AUTOFILL_ASPECT. Example: '14:9'

            - KEEP_ASPECT: if set to True the video will be cropped but it won't
            be aspect changed. In other words, there could still be horizontal
            or vertical black bars, but the original aspect will be kept;
            defaults to False.
    """
    def __init__(self):
        """ Initialise the PluginInterface and set default values for config"""

        plugin.ItemPlugin.__init__(self)
        self.plugin_name = 'fillscreen'

        self.args_def = config.MPLAYER_ARGS_DEF

        # default configs

        if hasattr(config, 'ASPECTS'):
            self.aspects = config.ASPECTS
        else:
            self.aspects = '16:9,4:3,14:9,16:10'
        if hasattr(config, 'KEEP_ASPECT'):
            self.keep_aspect = config.KEEP_ASPECT
        else:
            self.keep_aspect = False


    def split_ratio(self, ratio):
        ratio_w = int(ratio[:ratio.find(':')])
        ratio_h = int(ratio[ratio.find(':')+1:])
        return (ratio_w,ratio_h)


    def mplayer_args(self, ratio):
        """ Calculates cropping based on passed ratio """

        w = int(self.item.info['width'])
        h = int(self.item.info['height'])
        logger.debug('original size %sx%s', w, h)

        new_w = w
        new_h = h
        offset_h = 0
        offset_w = 0

        (ratio_w,ratio_h) = self.split_ratio(ratio)

        # first we try to adjust height
        new_h = w*ratio_h/ratio_w
        offset_h = (h-new_h)/2

        # if new_h is greater than original height then adjust width
        if new_h > h:
            new_h = h
            offset_h = 0
            new_w = h*ratio_w/ratio_h
            offset_w = (w-new_w)/2

        return (new_w,new_h,offset_w,offset_h)


    def actions(self, item):
        """ Adds Fill Screen action menu and performs autofill if needed """

        if item['aspect'] == '':
            return []

        config.MPLAYER_ARGS_DEF = self.args_def

        logger.debug('aspect: "%s"', item['aspect'])
        logger.debug('mplayer aspect: "%s"', item['mplayer_aspect'])

        if item.type == 'video':
            self.item = item
            if hasattr(config,'AUTOFILL_ASPECT') and \
               hasattr(config,'PREFERRED_ASPECT_FOR_AUTOFILL') and \
               item['aspect']==config.AUTOFILL_ASPECT:
                logger.debug('Autofilling to ' + config.PREFERRED_ASPECT_FOR_AUTOFILL)
                self.fillscreen(['',config.PREFERRED_ASPECT_FOR_AUTOFILL])
            return [ (self.fillscreen_menu, _('Fill screen')) ]

        return []


    def fillscreen_menu(self, arg=None, menuw=None):
        """ Adds submenu items """

        #_debug_('fillscreen_menu(self, menuw=%r, arg=%r)' % (menuw, arg), 2)

        aspects = self.aspects.split(',')
        (mW,mH) = self.split_ratio(config.MONITOR_ASPECT)
        monitorRatio = float(mW)/float(mH)

        menu_items = []

        for aspect in aspects:

            (new_w,new_h,offset_w,offset_h) = self.mplayer_args(aspect)
            if offset_h > 0:
                loss = str(offset_h) + ' ' + _('pixels cropped up and down')
            if offset_w > 0:
                loss = str(offset_w) + ' ' + _('pixels cropped left and right')
            if offset_w == 0 and offset_h == 0:
                loss = _('no loss')
            (rW,rH) = self.split_ratio(aspect)

            if not self.keep_aspect:
                ratio = float(rW)/float(rH)
                if ratio < monitorRatio:
                    unfit = ', ' + _('widens')
                if ratio > monitorRatio:
                    unfit = ', ' + _('narrows')
                if ratio == monitorRatio:
                    unfit = ', ' + _('ratio unchanged')
            else:
                unfit = ''

            menu_items += [ menu.MenuItem(_('Fill at') + ' %s (%s%s)' % \
              (aspect,loss,unfit), self.fillscreen, (self.item,aspect)) ]

        menu_items += [menu.MenuItem(_("Dont't fill (keep original ratio)"), self.fillscreen, (self.item,'original')) ]

        moviemenu = menu.Menu(_('Fill Screen Menu'), menu_items)

        menuw.pushmenu(moviemenu)


    def fillscreen(self, arg=None, menuw=None):
        """ Builds mplayer args """

        #_debug_('fillscreen(self, menuw=%r, arg=%r)' % (menuw, arg))
        logger.debug('selected ratio: %r', arg[1])

        if arg[1]=='original':
            config.MPLAYER_ARGS_DEF = self.args_def
            logger.debug('Keeping original ratio')
        else:
            (new_w,new_h,offset_w,offset_h) = self.mplayer_args(arg[1])
            if self.keep_aspect:
                ratio = config.MONITOR_ASPECT
            else:
                ratio = arg[1]

            config.MPLAYER_ARGS_DEF = self.args_def + \
                ' -monitoraspect %s -vf crop=%s:%s:%s:%s' % (ratio,new_w,new_h,offset_w,offset_h)
            logger.debug('Setting movie aspect to %s and crop to %s:%s:%s:%s', ratio, new_w, new_h, offset_w, offset_h)

        if arg[0]:
            menuw.back_one_menu()
