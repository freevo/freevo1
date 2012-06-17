# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo image viewer
# -----------------------------------------------------------------------
# $Id: $
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
Freevo image viewer
"""
import logging
logger = logging.getLogger("freevo.image.viewer")

import os

import config
import osd
import plugin
import util
import rc

from gui import GUIObject
from event import *

import time
import datetime
from animation import render, Transition
import pygame
import kaa

#
# We define the best fit (fit the width of the screen), but this will have 
# to be selected explicitly. By default, increasing and decreasing zoom levels 
# via the IMAGE_ZOOM_LEVEL_UP and IMAGE_ZOOM_LEVEL_DOWN events will cycle 
# between ZOOM_MIN_LEVEL and ZOOM_MAX_LEVEL where ZOOM_MIN_LEVEL is defined 
# to be ZOOM_NO_ZOOM.
ZOOM_BEST_FIT  = 0
ZOOM_NO_ZOOM   = 1
ZOOM_MIN_LEVEL = ZOOM_NO_ZOOM
ZOOM_MAX_LEVEL = 9

# Module variable that contains an initialized ImageViewer() object
_singleton = None

def get_singleton():
    logger.log(9, 'get_singleton()')
    global _singleton

    # One-time init
    if _singleton == None:
        _singleton = ImageViewer()

    return _singleton


class ImageZoomPosition():
    def __init__(self, pos_x = 0, pos_y = 0):
        """
        Represents the current position/coordinates within the zoomed in image
        """
        logger.log(9, 'ImageZoomPosition.__init__()')
        self.pos_x = pos_x
        self.pos_y = pos_y

    
    def reposition(self, zoom):
        """
        Recalculates the zoomed image position by the offset
        """
        self.pos_x = max(min(zoom.off_x + self.pos_x, 100), 0)
        self.pos_y = max(min(zoom.off_y + self.pos_y, 100), 0)
        
        # offsets consumed, let's reset them
        zoom.reset_offsets()


    def reset(self):
        """
        Resets image coordinates
        """
        self.pos_x = 0
        self.pos_y = 0
        

class ImageZoom():
    def __init__(self, zoom = ZOOM_NO_ZOOM, off_x = 0, off_y = 0):
        """
        Represents the zoom level and the offsets from the 
        current position within the zoomed in image.
        """
        logger.log(9, 'ImageZoom.__init__()')
        # limit zoom range, allow setting explicitly the best fit zoom value of 0
        self.zoom  = max(min(zoom, ZOOM_MAX_LEVEL), ZOOM_BEST_FIT)
        self.off_x = off_x
        self.off_y = off_y
    
    
    def is_zoomed(self):
        """
        Returns True if images is zoomed in.
        """
        return self.zoom != 1


    def is_best_fit(self):
        """
        Returns True if zoom is at best fit, i.e. screen width
        """
        return self.zoom == 0


    def get_level(self):
        """
        Returns current zoom level        
        """
        return self.zoom


    def set_level(self, zoom, rotation = 0):
        """
        Sets zoom level and rotates if necessary
        """
        self.zoom = zoom
        self.rotate(rotation)


    def rotate(self, rotation = 0):
        """
        Adjusts offsets if image is rotated
        """
        rotation = rotation % 360
        
        if rotation == 90:
            self.off_x, self.off_y =  self.off_y, -self.off_x
        elif rotation == 180:
            self.off_x, self.off_y = -self.off_x, -self.off_y
        elif rotation == 270:
            self.off_x, self.off_y = -self.off_y,  self.off_x


    def up(self):
        """
        Adjusts offsets if zoomed image is moved up
        """
        self.off_y = min(self.off_y + config.IMAGEVIEWER_SCROLL_FACTOR, 100) 


    def down(self):
        """
        Adjusts offsets if zoomed image is moved down
        """
        self.off_y = max(self.off_y - config.IMAGEVIEWER_SCROLL_FACTOR, 100) 
            

    def right(self):
        """
        Adjusts offsets if zoomed image is moved to the right
        """
        self.off_x = min(self.off_x + config.IMAGEVIEWER_SCROLL_FACTOR, 100) 


    def left(self):
        """
        Adjusts offsets if zoomed image is moved to the left
        """
        self.off_x = max(self.off_x - config.IMAGEVIEWER_SCROLL_FACTOR, 100) 


    def inc(self):
        """
        Increments the zoom level up to highest zoom level of 9
        """
        self.zoom = min(self.zoom + 1, ZOOM_MAX_LEVEL)


    def dec(self):
        """
        Decrements the zoom level down to lowest zoom level of 1
        """
        self.zoom = max(self.zoom - 1, ZOOM_MIN_LEVEL)


    def reset_zoom(self):
        """
        Resets zoom to no zoom, i.e. zoom level 1
        """
        self.zoom = 1


    def reset_offsets(self):
        """
        Resets image offsets
        """
        self.off_x = 0
        self.off_y = 0


    def reset(self):
        """
        Resets the object
        """
        self.reset_zoom()
        self.reset_offsets()


class ImageViewer(GUIObject):

    def __init__(self):
        logger.log( 9, 'ImageViewer.__init__()')
        GUIObject.__init__(self)
        self.osd_mode      = 0   # Draw file info on the image
        self.rotation      = 0
        self.zoom          = ImageZoom()
        self.pos           = ImageZoomPosition()
        self.last_zoom     = 1
        self.slideshow     = config.IMAGEVIEWER_AUTOPLAY
        self.duration      = config.IMAGEVIEWER_DURATION
        self.event_context = 'image'
        self.last_image    = (None, None)
        self.render        = render.get_singleton()
        self.osd           = osd.get_singleton()
        self.osd_height    = self.osd.height
        self.osd_width     = self.osd.width * float(config.OSD_PIXEL_ASPECT)
        self.timer         = None
        self.blend         = None
        self.__added_app   = False
        self.zoom_btns     = { str(IMAGE_ZOOM_BEST_FIT):0, str(IMAGE_ZOOM_NO_ZOOM): 1,
                               str(IMAGE_ZOOM_LEVEL_2): 2, str(IMAGE_ZOOM_LEVEL_3): 3,
                               str(IMAGE_ZOOM_LEVEL_4): 4, str(IMAGE_ZOOM_LEVEL_5): 5,
                               str(IMAGE_ZOOM_LEVEL_6): 6, str(IMAGE_ZOOM_LEVEL_7): 7,
                               str(IMAGE_ZOOM_LEVEL_8): 8, str(IMAGE_ZOOM_LEVEL_9): 9 }

        self.free_cache()


    def free_cache(self):
        """
        free the current cache to save memory
        """
        logger.log(9, 'free_cache()')
        self.bitmapcache = util.objectcache.ObjectCache(3, desc='viewer')
        if self.parent and self.free_cache in self.parent.show_callbacks:
            self.parent.show_callbacks.remove(self.free_cache)


    def view(self, item, zoom=None, rotation=0):
        """
        view an image
        """
        logger.log(9, 'view(item, zoom=%r, rotation=%s)', zoom, rotation)

        if self.blend:
            self.blend.stop()
            self.blend.remove()
            self.blend = None
            
        if not self.free_cache in item.menuw.show_callbacks:
            item.menuw.show_callbacks.append(self.free_cache)

        self.item     = item
        self.filename = item.filename
        self.parent   = item.menuw

        if not zoom:
            # This is a new image being displayed. Need to initialise few things
            zoom = ImageZoom(zoom = self.last_zoom)
            if not config.IMAGEVIEWER_KEEP_ZOOM_POSITION:
                self.pos.reset()

        self.zoom     = zoom
        self.rotation = rotation

        if self.zoom.is_zoomed():
            self.zoom.rotate(self.rotation)
            self.pos.reposition(self.zoom)
            self.event_context = 'image_zoom'
        else:
            self.pos.reset()
            self.event_context = 'image'

        rc.set_context(self.event_context)

        if config.IMAGEVIEWER_KEEP_ZOOM_LEVEL:
            self.last_zoom = self.zoom.get_level()

        if not self.__added_app:
            rc.add_app(self)
            self.__added_app = True

        if self.filename and len(self.filename) > 0:
            image = self.osd.loadbitmap(self.filename, cache=self.bitmapcache)
        else:
            # Using Container-Image
            image, w, h = self.item.loadimage()

        if not image:
            self.osd.clearscreen(color=self.osd.COL_BLACK)
            self.osd.drawstringframed(_('Can\'t Open Image\n"%s"') % Unicode(self.filename),
                config.OSD_OVERSCAN_LEFT + 20, config.OSD_OVERSCAN_TOP + 20,
                self.osd.width - (config.OSD_OVERSCAN_LEFT+config.OSD_OVERSCAN_RIGHT) - 40,
                self.osd.height - (config.OSD_OVERSCAN_TOP+config.OSD_OVERSCAN_BOTTOM) - 40,
                self.osd.getfont(config.OSD_DEFAULT_FONTNAME, config.OSD_DEFAULT_FONTSIZE),
                fgcolor=self.osd.COL_ORANGE, align_h='center', align_v='center', mode='soft')
            self.osd.update()
            return

        # Bounding box default values
        bbx = bby = bbw = bbh = 0

        # get the image width and height
        width, height = image.get_size()
        
        # flip width and height for rotated images, we flip them back later on
        if self.rotation % 180:
            height, width = width, height

        scale_x = float(self.osd_width)  / width
        scale_y = float(self.osd_height) / height

        # we calc the zoom factor, either fit to width of the osd or straigh zoom level
        if zoom.is_best_fit():
            scale = max(scale_x, scale_y)
        else:
            scale = min(scale_x, scale_y) * zoom.get_level()

        # calculate bounding box width and height
        bbw = min(width  * scale, self.osd_width)  / scale
        bbh = min(height * scale, self.osd_height) / scale

        new_h, new_w = int(bbh * scale), int(bbw * scale)

        if self.rotation % 180:
            # we flip widths and heights, both image and bb back for rotated images
            bbw,    bbh   = bbh,   bbw
            height, width = width, height

        # calculate the beginning of the bounding box
        bbx = ((width  - bbw) * self.pos.pos_x) / 100
        bby = ((height - bbh) * self.pos.pos_y) / 100

        # now we have all necessary information to calc x and y
        x = (self.osd_width  - new_w) / 2
        y = (self.osd_height - new_h) / 2

        last_item, last_image = self.last_image
        self.last_image = (item, (image, x, y, scale, bbx, bby, bbw, bbh, self.rotation))

        logger.debug('x=%r, y=%r, scale=%.2f, bbx=%.2f, bby=%.2f, bbw=%.2f, bbh=%.2f, self.rotation=%r', 
            x, y, scale, bbx, bby, bbw, bbh, self.rotation)

        # pygame rotates counterclockwise, we want clockwise, let's fix it
        if self.rotation % 180:
            rotation = (self.rotation + 180) % 360

        # and finally draw an image on screen
        if (last_image and last_item != item and config.IMAGEVIEWER_BLEND_MODE != None):
            screen = self.osd.screen.convert()
            screen.fill((0,0,0,0))
            screen.blit(self.osd.zoomsurface(image, scale, bbx, bby, bbw, bbh,
                rotation=rotation).convert(), (x, y))
            # update the OSD
            self.drawosd(layer=screen)

            self.blend = Transition(self.osd.screen, screen, config.IMAGEVIEWER_BLEND_MODE)
            self.blend.start()
            self.blend.inprogress.connect(self.__blend_done, item)

        else:
            self.osd.clearscreen(color=self.osd.COL_BLACK)
            self.osd.drawsurface(image, x, y, scale, bbx, bby, bbw, bbh, rotation=rotation)

            # update the OSD
            self.drawosd()
            self.__drawn(item)


    def __drawn(self, item):

        if plugin.getbyname('osd'):
            plugin.getbyname('osd').draw(('osd', None), self.osd)

        # draw
        self.osd.update()

        # start timer
        if self.duration and self.slideshow and not self.timer:
            self.timer = kaa.OneShotTimer(self.signalhandler)
            self.timer.start(self.duration)

        # stop slideshow at the end if configured
        try:
            index = item.parent.play_items.index(item)+1
            length = len(item.parent.play_items)
            if index == length:
                self.slideshow = config.IMAGEVIEWER_AUTOPLAY

            # send information event to LCD2
            rc.post_event(Event('IMAGE_VIEW_INFO', arg=(index, length, item.name)))
        except Exception, why:
            logger.warning('Invalid parent item: %s', why)

        # XXX Hack to move the selected item to the current showing image
        # XXX TODO: find a way to add it to directory.py or playlist.py
        if item.parent and hasattr(item.parent, 'menu') and item.parent.menu and \
               item in item.parent.menu.choices:
            item.parent.menu.selected = item
            item.menuw.force_page_rebuild = True

        return None

    def __blend_done(self, result, item):
        self.blend.remove()
        self.blend = None
        self.__drawn(item)


    def redraw(self):
        logger.log(9, 'redraw()')
        self.view(self.item, zoom=self.zoom, rotation=self.rotation)


    def cache(self, item):
        logger.log(9, 'cache(item.filename=%s)', item.filename)
        # cache the next image (most likely we need this)
        self.osd.loadbitmap(item.filename, cache=self.bitmapcache)


    def signalhandler(self):
        logger.log(9, 'signalhandler()')
        self.timer = None
        self.eventhandler(PLAY_END)


    def eventhandler(self, event, menuw=None):
        logger.log(9, 'eventhandler(event=%s, menuw=%s)', event, menuw)
        # SELECT also should act as PLAY/PAUSE (-> could be done with event rerouting!?)
        if event == PAUSE or event == PLAY or (event == BUTTON and event.arg == 'SELECT'):
            if self.slideshow:
                rc.post_event(Event(OSD_MESSAGE, arg=_('pause')))
                rc.post_event(Event('IMAGE_PAUSE_INFO', arg=''))
                self.slideshow = False
                if self.timer:
                    self.timer.stop()
                    self.timer = None
            else:
                rc.post_event(Event(OSD_MESSAGE, arg=_('play')+(' %ss'%self.duration)))
                rc.post_event(Event('IMAGE_PLAY_INFO', arg='%s' % self.duration))
                self.slideshow = True
                self.timer = kaa.OneShotTimer(self.signalhandler)
                self.timer.start(self.duration)
            return True

        elif event == STOP:
            self.last_image  = None, None           
            self.slideshow = config.IMAGEVIEWER_AUTOPLAY
            if self.timer:
                self.timer.stop()
                self.timer = None
            if self.blend:
                self.blend.stop()
                self.blend.remove()
                self.blend = None
            rc.remove_app(self)
            self.__added_app = False
            self.last_zoom = ZOOM_NO_ZOOM
            self.item.eventhandler(event)
            return True

        # up and down will stop the slideshow and pass the
        # event to the playlist
        elif event == PLAYLIST_NEXT or event == PLAYLIST_PREV:
            if self.timer:
                self.timer.stop()
                self.timer = None
            self.item.eventhandler(event)
            return True

        elif event == IMAGE_MOVE:
            coord = event.arg
            self.zoom = ImageZoom(self.zoom.zoom, coord[0], coord[1])
            self.view(self.item, zoom=self.zoom, rotation=self.rotation)
            return True

        # rotate image
        elif event == IMAGE_ROTATE:
            if event.arg == 'left':
                self.rotation = (self.rotation - 90) % 360
                self.view(self.item, zoom=self.zoom, rotation=self.rotation)
            else:
                self.rotation = (self.rotation + 90) % 360
                self.view(self.item, zoom=self.zoom, rotation=self.rotation)
                
            if self.timer:
                self.timer.start(self.duration)
            return True

        # print image information
        elif event == TOGGLE_OSD:
            self.osd_mode = (self.osd_mode + 1) % (len(config.IMAGEVIEWER_OSD) + 1)
            # Redraw
            self.view(self.item, zoom=self.zoom, rotation = self.rotation)
            return True

        # increment zoom level to max
        elif event == IMAGE_ZOOM_LEVEL_UP:
            if self.zoom.get_level() == ZOOM_MAX_LEVEL:
                rc.post_event(Event(OSD_MESSAGE, arg=_('already at maximum zoom level'))) 
            else:
                self.zoom.inc()

            if self.timer:
                self.timer.stop()
                self.slideshow = False

            # Zoom the image, don't load the next image in the list
            self.view(self.item, zoom=self.zoom, rotation=self.rotation)
            return True

        # decrement zoom level to min
        elif event == IMAGE_ZOOM_LEVEL_DOWN:
            if self.zoom.get_level() == ZOOM_MIN_LEVEL:
                rc.post_event(Event(OSD_MESSAGE, arg=_('already at minimum zoom level'))) 
            else:
                self.zoom.dec()
        
            if self.timer:
                self.timer.stop()
                self.slideshow = False

            # Zoom the image, don't load the next image in the list
            self.view(self.item, zoom=self.zoom, rotation=self.rotation)
            return True

        # zoom to zoom level
        elif str(event) in self.zoom_btns:
            self.zoom.zoom = self.zoom_btns[str(event)]
            if self.timer:
                self.timer.stop()
                self.slideshow = False

            # Zoom the image, don't load the next image in the list
            self.view(self.item, zoom=self.zoom, rotation=self.rotation)
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
                    plugin.get('item')[0].shuntItemInCart(self.item)
                    return True
                except Exception, e:
                    print 'getbyname(\'shoppingcart\')', e

        # change slideshow duration and send event to OSD and LCD2
        elif (event == BUTTON) and (event.arg == 'REW'):
            if self.duration > 7: self.duration -= 2
            elif self.duration > 1: self.duration -= 1
            rc.post_event(Event(OSD_MESSAGE, arg="Timer %ss" % self.duration)) # not yet internationalised
            rc.post_event(Event('IMAGE_PLAY_INFO', arg='%s' % self.duration))
            return True
        elif (event == BUTTON) and (event.arg == 'FFWD'):
            if self.duration < 6: self.duration += 1
            elif self.duration < 11: self.duration += 2
            rc.post_event(Event(OSD_MESSAGE, arg="Timer %ss" % self.duration)) # not yet internationalised
            rc.post_event(Event('IMAGE_PLAY_INFO', arg='%s' % self.duration))
            return True

        else:
            return self.item.eventhandler(event)


    def drawosd(self, layer=None):
        logger.log(9, 'drawosd(layer=%s)', layer)

        if not self.osd_mode:
            return

        osdstring = []

        for strtag in config.IMAGEVIEWER_OSD[self.osd_mode-1]:
            i = self.item.getattr(strtag[1])
            if i:
                osdstring.append('%s %s' % (strtag[0], i))
            else:
                if strtag[1] == 'date' and self.item['timestamp']:
                    osdstring.append('%s %s' % (strtag[0], datetime.datetime.fromtimestamp(self.item['timestamp'])))

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

    