# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Some utils for the skin
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
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

"""
Some utils for the skin
"""
import logging
logger = logging.getLogger("freevo.skins.main.skin_utils")

import config
import pygame
from pygame.locals import *
import kaa.imlib2 as imlib2

import osd
import os
import util
try:
    import cStringIO as StringIO
except:
    import StringIO

from kaa.metadata.image import EXIF as exif

import kaa
thread_pool = kaa.ThreadPool()


osd = osd.get_singleton()

format_imagecache = util.objectcache.ObjectCache(300, desc='format_image')
load_imagecache   = util.objectcache.ObjectCache(20, desc='load_image')


def pygamesurface_imlib2_scale(image, newsize):

    buf = pygame.image.tostring(image, 'RGBA')
    im2 = imlib2.new(image.get_size(), buf)
    scaled_im2 = im2.scale(newsize)

    buf = str(scaled_im2.get_raw_data('BGRA'))

    return pygame.image.frombuffer(buf, newsize, 'RGBA')


def generate_cache_key(settings, item, width, height, force=0):
    try:
        type = item.display_type
    except AttributeError:
        try:
            type = item.info['mime'].replace('/', '_')
        except:
            type = item.type
    if type is None:
        type = ''


    item_image = Unicode(item.image)

    cname = '%s-%s-%s-%s-%s-%s-%s' % (settings.icon_dir, item_image, type, item.type, width, height, force)

    if hasattr(item, 'rotation') and item['rotation']:
        cname = '%s-%s' % (cname, item['rotation'])

    if item.media and item.media.item == item:
        cname = '%s-%s' % (cname, item.media)

    return cname


def format_image(settings, item, width, height, force=False, anamorphic=False, flush_large_image=False):
    logger.log( 9, 'format_image(settings=%r, item=%r, width=%r, height=%r, force=%r, anamorphic=%r, flush_large_image=%r)', settings, item, width, height, force, anamorphic, flush_large_image)


    cname = generate_cache_key(settings, item, width, height, force)
    cimage = format_imagecache[cname]

    if cimage:
        return cimage

    try:
        type = item.display_type
    except AttributeError:
        try:
            type = item.info['mime'].replace('/', '_')
        except:
            type = item.type
    if type is None:
        type = ''

    image     = None
    imagefile = None

    if item.image:
        if isinstance(item.image, imlib2.Image):
            image = osd.loadbitmap(item.image)
        else:
            if not (item.image.startswith('http://') or item.image.startswith('https://')):
                if not os.path.exists(str(item.image)):
                    return None, 0, 0
        
        image = load_imagecache[item.image]
        if not image:
            image = load_imagecache['thumb://%s' % item.image]

        if not image:
            if item.image.startswith('http://') or item.image.startswith('https://'):
                image = osd.loadbitmap(item.image)
                load_imagecache[imagefile] = image
            else:
                for folder in ('.thumbs', '.images'):
                    image_parts = os.path.split(str(item.image))
                    ifile = os.path.join(image_parts[0], folder, image_parts[1])
                    if os.path.exists(ifile):
                        imagefile = ifile
                        break

                if imagefile:
                    image = osd.loadbitmap(imagefile)
                    imagefile = 'thumb://%s' % item.image
                    load_imagecache[imagefile] = image
                else:
                    imagefile = item.image
                    f = open(imagefile, 'rb')
                    tags = exif.process_file(f)
                    f.close()
                    if 'JPEGThumbnail' in tags:
                        sio = StringIO.StringIO(tags['JPEGThumbnail'])
                        image = pygame.image.load(sio)
                        sio.close()
                        imagefile = 'thumb://%s' % item.image
                        load_imagecache[imagefile] = image
                    else:
                        image = osd.loadbitmap(imagefile)
                        load_imagecache[imagefile] = image
                    


            # DJW need to skip this code if the image is from .thumbs or .images as
            # the image has already been rotated in the cache.
            if not item['rotation']:
                try:
                    f = open(imagefile, 'rb')
                    tags = exif.process_file(f)
                    f.close()
                    if tags.has_key('Image Orientation'):
                        orientation = tags['Image Orientation']
                        logger.debug('%s orientation=%s', item['name'], tags['Image Orientation'])
                        if str(orientation) == "Rotated 90 CCW":
                            item['rotation'] = 270
                        elif str(orientation) == "Rotated 180":
                            item['rotation'] = 180
                        elif str(orientation) == "Rotated 90 CW":
                            item['rotation'] = 90
                except Exception, e:
                    logger.info('%s', e)

            if image and item['rotation']:
                # pygame reverses the image rotation
                if config.IMAGEVIEWER_REVERSED_IMAGES:
                    rotation = item['rotation']
                else:
                    rotation = (360 - item['rotation']) % 360
                image = pygame.transform.rotate(image, rotation)
                load_imagecache[imagefile] = image

    if not image:
        if not force:
            return None, 0, 0

        if hasattr(item, 'media') and item.media and item.media.item == item and \
                os.path.isfile('%s/mimetypes/%s.png' % (settings.icon_dir, item.media.type)):
            imagefile = '%s/mimetypes/%s.png' % (settings.icon_dir, item.media.type)

        elif item.type == 'dir':
            if os.path.isfile('%s/mimetypes/folder_%s.png' % (settings.icon_dir, item.display_type)):
                imagefile = '%s/mimetypes/folder_%s.png' % (settings.icon_dir, item.display_type)
            else:
                imagefile = '%s/mimetypes/folder.png' % settings.icon_dir

        elif item.type == 'playlist':
            if item.parent and os.path.isfile('%s/mimetypes/playlist_%s.png' % \
                                              (settings.icon_dir, item.parent.display_type)):
                imagefile = '%s/mimetypes/playlist_%s.png' % (settings.icon_dir, item.parent.display_type)
            else:
                imagefile = '%s/mimetypes/playlist.png' % settings.icon_dir

        elif os.path.isfile('%s/mimetypes/%s.png' % (settings.icon_dir, type)):
            imagefile = '%s/mimetypes/%s.png' % (settings.icon_dir, type)

        elif os.path.isfile('%s/mimetypes/%s.png' % (settings.icon_dir, item.type)):
            imagefile = '%s/mimetypes/%s.png' % (settings.icon_dir, item.type)

        elif os.path.isfile('%s/mimetypes/unknown.png' % settings.icon_dir):
            imagefile = '%s/mimetypes/unknown.png' % settings.icon_dir

        if not imagefile:
            return None, 0, 0

        imagefile = 'thumb://%s' % imagefile
        image = load_imagecache[imagefile]
        if not image:
            image = osd.loadbitmap(imagefile)
            load_imagecache[imagefile] = image

        if not image:
            return None, 0, 0

    else:
        force = 0

    if type and len(type) > 4:
        type = type[:5]

    i_w, i_h = image.get_size()
    # this was the original anamorphic code
    #if anamorphic:
    #    i_w  = i_w * 0.75
    i_w = float(i_w) / config.OSD_PIXEL_ASPECT
    aspect = float(i_h)/i_w

    if type == 'audio' and aspect < 1.3 and aspect > 0.8:
        # this is an audio cover
        m = min(height, width)
        i_w = m
        i_h = m

    elif type == 'video' and aspect > 1.3 and aspect < 1.6:
        # video cover, set aspect 7:5
        i_w = 5
        i_h = 7

    if int(float(width * i_h) / i_w) > height:
        width =  int(float(height * i_w) / i_h)
    else:
        height = int(float(width * i_h) / i_w)

    cimage = pygamesurface_imlib2_scale(image, (width, height))

    if flush_large_image:
        s = i_w * i_h
        if s > 1000000:
            del load_imagecache[imagefile]
            image = None

    format_imagecache[cname] = cimage, width, height
    return cimage, width, height


def text_or_icon(settings, string, x, width, font):
    l = string.split('_')
    if len(l) != 4:
        return string
    try:
        height = font.h
        image = os.path.join(settings.icon_dir, l[2].lower())
        if os.path.isfile(image + '.jpg'):
            image += '.jpg'
        if os.path.isfile(image + '.png'):
            image += '.png'
        else:
            image = None
        if image:
            cname = '%s-%s-%s-%s-%s' % (image, x, l[2], width, height)
            cimage = format_imagecache[cname]
            if cimage:
                return cimage

            image = osd.loadbitmap(image)
            if not image:
                raise KeyError
            i_w, i_h = image.get_size()
            original_width = width
            if int(float(width * i_h) / i_w) > height:
                width =  int(float(height * i_w) / i_h)
            else:
                height = int(float(width * i_h) / i_w)

            cimage = pygamesurface_imlib2_scale(image, (width, height))
            cimage.set_alpha(cimage.get_alpha(), RLEACCEL)
            x_mod = 0
            if l[1] == 'CENTER':
                x_mod = (original_width - width) / 2
            if l[1] == 'RIGHT':
                x_mod = original_width - width
            format_imagecache[cname] = x_mod, cimage
            return x_mod, cimage
    except KeyError:
        logger.debug('no image %s', l[2])
        pass

    mod_x = width - font.stringsize(l[3])
    if mod_x < 0:
        mod_x = 0
    if l[1] == 'CENTER':
        return mod_x / 2, l[3]
    if l[1] == 'RIGHT':
        return mod_x, l[3]
    return 0, l[3]



class AsyncImageFormatter(object):
    def __init__(self, settings, item, width, height, force, anamorphic,
                    high_priority=False, flush_large_image=False):
        self.args = (settings, item, width, height, force, anamorphic, flush_large_image)
        self.cancelled = False
        if high_priority:
            pool_info = (thread_pool, 1)
        else:
            pool_info = (thread_pool, 0)
        self.inprogress = kaa.ThreadPoolCallable(pool_info, self.__do_format)()
        self.inprogress.connect(self.__do_callback)
        self.__cb = None
        self.__arg = None

    
    @property
    def finished(self):
        return self.inprogress.finished


    @property
    def result(self):
        return self.inprogress.result


    def connect(self, cb, arg):
        self.__cb = cb
        self.__arg = arg


    def __do_callback(self, result):
        if result is not None and self.__cb is not None:
            self.__cb(result, self.__arg)


    def __do_format(self):
        if self.cancelled:
            return
        return format_image(*self.args)
