# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# viewer.py - Freevo image viewer
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        Change the signal stuff for slideshows
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


import os

import config
import osd
import plugin
import util
import rc

from gui import GUIObject
from event import *

import time
from animation import render, Transition

# Module variable that contains an initialized ImageViewer() object
_singleton = None

def get_singleton():
    _debug_('get_singleton()', 2)
    global _singleton

    # One-time init
    if _singleton == None:
        _singleton = ImageViewer()

    return _singleton


class ImageViewer(GUIObject):

    def __init__(self):
        _debug_('ImageViewer.__init__()', 2)
        GUIObject.__init__(self)
        self.osd_mode = 0    # Draw file info on the image
        self.zoom = 0   # Image zoom
        self.zoom_btns = { str(IMAGE_NO_ZOOM):0, str(IMAGE_ZOOM_GRID1):1,
                           str(IMAGE_ZOOM_GRID2):2, str(IMAGE_ZOOM_GRID3):3,
                           str(IMAGE_ZOOM_GRID4):4, str(IMAGE_ZOOM_GRID5):5,
                           str(IMAGE_ZOOM_GRID6):6, str(IMAGE_ZOOM_GRID7):7,
                           str(IMAGE_ZOOM_GRID8):8, str(IMAGE_ZOOM_GRID9):9 }

        self.slideshow   = True
        self.app_mode    = 'image'
        self.last_image  = (None, None)
        self.osd         = osd.get_singleton()
        self.osd_height  = self.osd.height
        self.osd_width   = self.osd.width * float(config.IMAGEVIEWER_ASPECT)

        self.signal_registered = False

        self.free_cache()


    def free_cache(self):
        """
        free the current cache to save memory
        """
        _debug_('free_cache()', 2)
        self.bitmapcache = util.objectcache.ObjectCache(3, desc='viewer')
        if self.parent and self.free_cache in self.parent.show_callbacks:
            self.parent.show_callbacks.remove(self.free_cache)


    def view(self, item, zoom=0, rotation=0):
        '''
        view an image
        '''
        _debug_('view(item, zoom=%s, rotation=%s)' % (zoom, rotation), 2)
        if zoom:
            self.app_mode    = 'image_zoom'
        else:
            self.app_mode    = 'image'

        filename = item.filename

        self.fileitem = item
        self.parent   = item.menuw

        if not self.free_cache in item.menuw.show_callbacks:
            item.menuw.show_callbacks.append(self.free_cache)

        self.filename = filename
        if config.IMAGEVIEWER_REVERSED_IMAGES:
            self.rotation = (360 - rotation) % 360
        else:
            self.rotation = rotation

        if filename and len(filename) > 0:
            image = self.osd.loadbitmap(filename, cache=self.bitmapcache)
        else:
            # Using Container-Image
            image = item.loadimage()

        rc.app(self)

        if not image:
            self.osd.clearscreen(color=self.osd.COL_BLACK)
            self.osd.drawstringframed(_('Can\'t Open Image\n\'%s\'') % Unicode(filename),
                config.OSD_OVERSCAN_LEFT + 20, config.OSD_OVERSCAN_TOP + 20,
                self.osd.width - (config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT) - 40,
                self.osd.height - (config.OSD_OVERSCAN_TOP+config.OSD_OVERSCAN_BOTTOM) - 40,
                self.osd.getfont(config.OSD_DEFAULT_FONTNAME, config.OSD_DEFAULT_FONTSIZE),
                fgcolor=self.osd.COL_ORANGE, align_h='center', align_v='center', mode='soft')
            self.osd.update()
            return

        width, height = image.get_size()

        # Bounding box default values
        bbx = bby = bbw = bbh = 0

        if zoom:
            # Translate the 9-element grid to bounding boxes
            if self.rotation == 90:
                bb = { 1:(2,0), 2:(2,1), 3:(2,2),
                       4:(1,0), 5:(1,1), 6:(1,2),
                       7:(0,0), 8:(0,1), 9:(0,2) }
            elif self.rotation == 180:
                bb = { 1:(2,2), 2:(1,2), 3:(0,2),
                       4:(2,1), 5:(1,1), 6:(0,1),
                       7:(2,0), 8:(1,0), 9:(0,0) }
            elif self.rotation == 270:
                bb = { 1:(0,2), 2:(0,1), 3:(0,0),
                       4:(1,2), 5:(1,1), 6:(1,0),
                       7:(2,2), 8:(2,1), 9:(2,0) }
            else:
                bb = { 1:(0,0), 2:(1,0), 3:(2,0),
                       4:(0,1), 5:(1,1), 6:(2,1),
                       7:(0,2), 8:(1,2), 9:(2,2) }

            if isinstance(zoom, int):
                h, v = bb[zoom]
            else:
                h, v = bb[zoom[0]]

            # Bounding box center
            bbcx = ([1, 3, 5][h]) * width / 6
            bbcy = ([1, 3, 5][v]) * height / 6

            if self.rotation % 180:
                # different calculations because image width is screen height
                scale_x = float(self.osd_width) / (height / 3)
                scale_y = float(self.osd_height) / (width / 3)
                scale = min(scale_x, scale_y)

                # read comment for the bbw and bbh calculations below
                bbw = min(max((width / 3) * scale, self.osd_height), width) / scale
                bbh = min(max((height / 3) * scale, self.osd_width), height) / scale

            else:
                scale_x = float(self.osd_width) / (width / 3)
                scale_y = float(self.osd_height) / (height / 3)
                scale = min(scale_x, scale_y)

                # the bb width is the width / 3 * scale, to avoid black bars left
                # and right exapand it to the osd_width but not if this is more than the
                # image width (same for height)
                bbw = min(max((width / 3) * scale, self.osd_width), width) / scale
                bbh = min(max((height / 3) * scale, self.osd_height), height) / scale

            # calculate the beginning of the bounding box
            bbx = max(0, bbcx - bbw/2)
            bby = max(0, bbcy - bbh/2)

            if bbx + bbw > width:  bbx = width - bbw
            if bby + bbh > height: bby = height - bbh

            if self.rotation % 180:
                new_h, new_w = bbw * scale, bbh * scale
            else:
                new_w, new_h = bbw * scale, bbh * scale

        else:
            if self.rotation % 180:
                height, width = width, height

            # scale_x = scale_y = 1.0
            # if width > osd_width: scale_x = float(osd_width) / width
            # if height > osd_height: scale_y = float(osd_height) / height
            scale_x = float(self.osd_width) / width
            scale_y = float(self.osd_height) / height

            scale = min(scale_x, scale_y)

            new_w, new_h = int(scale*width), int(scale*height)


        # Now we have all necessary information about zoom yes/no and
        # the kind of rotation

        x = (self.osd_width - new_w) / 2
        y = (self.osd_height - new_h) / 2

        last_image = self.last_image[1]


        if not isinstance(zoom, int):
            # change zoom based on rotation
            if self.rotation == 90:
                zoom = zoom[0], -zoom[2], zoom[1]
            if self.rotation == 180:
                zoom = zoom[0], -zoom[1], -zoom[2]
            if self.rotation == 270:
                zoom = zoom[0], zoom[2], -zoom[1]

            # don't move outside the image
            if bbx + zoom[1] < 0:
                zoom = zoom[0], -bbx, zoom[2]
            if bbx + zoom[1] > width - bbw:
                zoom = zoom[0], width - (bbw + bbx), zoom[2]
            if bby + zoom[2] < 0:
                zoom = zoom[0], zoom[1], -bby
            if bby + zoom[2] > height - bbh:
                zoom = zoom[0], zoom[1], height - (bbh + bby)

            # change bbx
            bbx += zoom[1]
            bby += zoom[2]

        if (last_image and self.last_image[0] != item and config.IMAGEVIEWER_BLEND_MODE):
            screen = self.osd.screen.convert()
            screen.fill((0,0,0,0))
            screen.blit(self.osd.zoomsurface(image, scale, bbx, bby, bbw, bbh,
                                        rotation=self.rotation).convert(), (x, y))
            # update the OSD
            self.drawosd(layer=screen)

            blend = Transition(self.osd.screen, screen, config.IMAGEVIEWER_BLEND_MODE)
            blend.start()
            while not blend.finished:
                rc.poll()
            blend.remove()

        else:
            self.osd.clearscreen(color=self.osd.COL_BLACK)
            self.osd.drawsurface(image, x, y, scale, bbx, bby, bbw, bbh,
                                 rotation=self.rotation)

            # update the OSD
            self.drawosd()


        if plugin.getbyname('osd'):
            plugin.getbyname('osd').draw(('osd', None), self.osd)

        # draw
        self.osd.update()

        # start timer
        if self.fileitem.duration and self.slideshow and not self.signal_registered:
            rc.register(self.signalhandler, False, self.fileitem.duration*100)
            self.signal_registered = True

        self.last_image  = (item, (image, x, y, scale, bbx, bby, bbw, bbh,
                                   self.rotation))


        # XXX Hack to move the selected item to the current showing image
        # XXX TODO: find a way to add it to directory.py or playlist.py
        if item.parent and hasattr(item.parent, 'menu') and item.parent.menu and \
               item in item.parent.menu.choices:
            item.parent.menu.selected = item
            item.menuw.force_page_rebuild = True

        # save zoom, but revert the rotation mix up
        if not isinstance(zoom, int) and self.rotation:
            if self.rotation == 90:
                zoom = zoom[0], zoom[2], -zoom[1]
            if self.rotation == 180:
                zoom = zoom[0], -zoom[1], -zoom[2]
            if self.rotation == 270:
                zoom = zoom[0], -zoom[2], zoom[1]
        self.zoom = zoom
        return None


    def redraw(self):
        _debug_('redraw()', 2)
        self.view(self.fileitem, zoom=self.zoom, rotation=self.rotation)


    def cache(self, fileitem):
        _debug_('cache(fileitem.filename=%s)' % (fileitem.filename), 2)
        # cache the next image (most likely we need this)
        self.osd.loadbitmap(fileitem.filename, cache=self.bitmapcache)


    def signalhandler(self):
        _debug_('signalhandler()', 2)
        self.signal_registered = False
        self.eventhandler(PLAY_END)


    def eventhandler(self, event, menuw=None):
        _debug_('eventhandler(event=%s, menuw=%s)' % (event, menuw), 2)
        if event == PAUSE or event == PLAY:
            if self.slideshow:
                rc.post_event(Event(OSD_MESSAGE, arg=_('pause')))
                self.slideshow = False
                rc.unregister(self.signalhandler)
                self.signal_registered = False
            else:
                rc.post_event(Event(OSD_MESSAGE, arg=_('play')))
                self.slideshow = True
                rc.register(self.signalhandler, False, 100)
                self.signal_registered = True
            return True

        elif event == STOP:
            self.last_image  = None, None
            self.signal_registered = False
            rc.unregister(self.signalhandler)
            rc.app(None)
            self.fileitem.eventhandler(event)
            return True

        # up and down will stop the slideshow and pass the
        # event to the playlist
        elif event == PLAYLIST_NEXT or event == PLAYLIST_PREV:
            self.signal_registered = False
            rc.unregister(self.signalhandler)
            self.fileitem.eventhandler(event)
            return True

        # rotate image
        elif event == IMAGE_ROTATE:
            if event.arg == 'left':
                self.rotation = (self.rotation - 90) % 360
            else:
                self.rotation = (self.rotation + 90) % 360
            self.fileitem['rotation'] = self.rotation
            self.view(self.fileitem, zoom=self.zoom, rotation=self.rotation)
            return True

        # print image information
        elif event == TOGGLE_OSD:
            self.osd_mode = (self.osd_mode + 1) % (len(config.IMAGEVIEWER_OSD) + 1)
            # Redraw
            self.view(self.fileitem, zoom=self.zoom, rotation = self.rotation)
            return True

        # zoom to one third of the image
        # 1 is upper left, 9 is lower right, 0 zoom off
        elif str(event) in self.zoom_btns:
            self.zoom = self.zoom_btns[str(event)]

            if self.zoom:
                # Zoom one third of the image, don't load the next
                # image in the list
                self.view(self.fileitem, zoom=self.zoom, rotation = self.rotation)
            else:
                # Display entire picture, don't load next image in case
                # the user wants to zoom around some more.
                self.view(self.fileitem, zoom=0, rotation=self.rotation)
            return True

        elif event == IMAGE_MOVE:
            coord = event.arg
            if isinstance(self.zoom, int):
                self.zoom = self.zoom, coord[0], coord[1]
            else:
                self.zoom = self.zoom[0], self.zoom[1] + coord[0], self.zoom[2] + coord[1]
            self.view(self.fileitem, zoom=self.zoom, rotation=self.rotation)
            return True

        # save the image with the current rotation
        elif event == IMAGE_SAVE:
            if self.rotation and os.path.splitext(self.filename)[1] == ".jpg":
                cmd = 'jpegtran -copy all -rotate %s -outfile /tmp/freevo-iview %s' \
                      % ((self.rotation + 180) % 360, self.filename)
                os.system(cmd)
                os.system('mv /tmp/freevo-iview %s' % self.filename)
                self.rotation = 0
                self.osd.bitmapcache.__delitem__(self.filename)
                return True

        # append the image filename to shoppingcart list
        elif event == IMAGE_TAG:
            if plugin.is_active('shoppingcart'):
                try:
                    plugin.get('item')[0].shuntItemInCart(self.fileitem)
                    return True
                except Exception, e:
                    print 'getbyname(\'shoppingcart\')', e

        else:
            return self.fileitem.eventhandler(event)


    def drawosd(self, layer=None):
        _debug_('drawosd(layer=%s)' % (layer), 2)

        if not self.osd_mode:
            return

        osdstring = []

        for strtag in config.IMAGEVIEWER_OSD[self.osd_mode-1]:
            i = self.fileitem.getattr(strtag[1])
            if i:
                osdstring.append('%s %s' % (strtag[0], i))

        # If after all that there is nothing then tell the users that
        if osdstring == []:
            osdstring = [_('No information available')]

        # Now sort the text into lines of length line_length
        line = 0
        if config.OSD_OVERSCAN_LEFT or config.OSD_OVERSCAN_RIGHT:
            line_length = 35
        else:
            line_length = 60
        prt_line = ['']

        for textstr in osdstring:
            if len(textstr) > line_length:
                # This is to big so just print it for now but wrap later
                if prt_line[line] == '':
                    prt_line[line] = textstr
                else:
                    prt_line.append(textstr)
                    line += 1
            elif len(textstr + '   ' + prt_line[line] )  > line_length:
                # Too long for one line so print the last and then new
                line += 1
                prt_line.append(textstr)
            else:
                if prt_line[line] == '':
                    prt_line[line] = textstr
                else:
                    prt_line[line] += '   ' + textstr

        # Create a black box for text
        self.osd.drawbox(config.OSD_OVERSCAN_LEFT, self.osd_height - \
                         (config.OSD_OVERSCAN_LEFT + 25 + (len(prt_line) * 30)),
                         self.osd_width, self.osd_height, width=-1,
                         color=((60 << 24) | self.osd.COL_BLACK), layer=layer)

        # Now print the Text
        for line in range(len(prt_line)):
            h=self.osd_height - (40 + config.OSD_OVERSCAN_TOP + \
                                 ((len(prt_line) - line - 1) * 30))
            self.osd.drawstring(prt_line[line], 15 + config.OSD_OVERSCAN_LEFT, h,
                                fgcolor=self.osd.COL_ORANGE, layer=layer)
