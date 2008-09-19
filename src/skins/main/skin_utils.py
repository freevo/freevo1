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

import config
import pygame
from pygame.locals import *
import kaa.imlib2 as imlib2

import osd
import os
import util
from kaa.metadata.image import EXIF as exif

from util.benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING

osd = osd.get_singleton()

format_imagecache = util.objectcache.ObjectCache(30, desc='format_image')
load_imagecache   = util.objectcache.ObjectCache(20, desc='load_image')


@benchmark(benchmarking)
def pygamesurface_imlib2_scale(image, newsize):

    buf = pygame.image.tostring(image, 'RGBA')
    im2 = imlib2.new(image.get_size(), buf)
    scaled_im2 = im2.scale(newsize)

    buf = str(scaled_im2.get_raw_data('BGRA'))

    return pygame.image.frombuffer(buf, newsize, 'RGBA')


@benchmark(benchmarking)
def format_image(settings, item, width, height, force=0, anamorphic=0):
    #print 'format_image(settings=%r, item=%r, width=%r, height=%r, force=%r, anamorphic=%r)' % (settings, item, width, height, force, anamorphic)

    try:
        type = item.display_type
    except AttributeError:
        try:
            type = item.info['mime'].replace('/', '_')
        except:
            type = item.type
    if type is None:
        type = ''


    item_image=Unicode(item.image)

    cname = '%s-%s-%s-%s-%s-%s-%s' % (settings.icon_dir, item_image, type, item.type, width, height, force)

    if hasattr(item, 'rotation') and item['rotation']:
        cname = '%s-%s' % (cname, item['rotation'])

    if item.media and item.media.item == item:
        cname = '%s-%s' % (cname, item.media)

    cimage = format_imagecache[cname]

    if cimage:
        return cimage

    image     = None
    imagefile = None

    if item.image:
        if isinstance(item.image, imlib2.Image):
            image = osd.loadbitmap(item.image)
        else:
            if not os.path.exists(item.image):
                return None, 0, 0

        image = load_imagecache['thumb://%s' % item.image]
        if not image:
            image = osd.loadbitmap(item.image)
            load_imagecache['thumb://%s' % item.image] = image

        if not item['rotation']:
            try:
                f=open(item.image, 'rb')
                tags=exif.process_file(f)
                f.close()
                if tags.has_key('Image Orientation'):
                    orientation = tags['Image Orientation']
                    _debug_('%s orientation=%s' % (item['name'], tags['Image Orientation']))
                    if str(orientation) == "Rotated 90 CCW":
                        item['rotation'] = 270
                    elif str(orientation) == "Rotated 180":
                        item['rotation'] = 180
                    elif str(orientation) == "Rotated 90 CW":
                        item['rotation'] = 90
            except Exception, e:
                _debug_('%s' % (e), DINFO)

        if image and item['rotation']:
            # pygame reverses the image rotation
            if config.IMAGEVIEWER_REVERSED_IMAGES:
                rotation = (360 - item['rotation']) % 360
            else:
                rotation = item['rotation']
            image = pygame.transform.rotate(image, rotation)

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

        image = load_imagecache['thumb://%s' % imagefile]
        if not image:
            image = osd.loadbitmap('thumb://%s' % imagefile)
            load_imagecache['thumb://%s' % imagefile] = image

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
    i_w  = float(i_w) / config.IMAGEVIEWER_ASPECT
    aspect   = float(i_h)/i_w

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

    format_imagecache[cname] = cimage, width, height
    return cimage, width, height


@benchmark(benchmarking)
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
        _debug_('no image %s' % l[2])
        pass

    mod_x = width - font.stringsize(l[3])
    if mod_x < 0:
        mod_x = 0
    if l[1] == 'CENTER':
        return mod_x / 2, l[3]
    if l[1] == 'RIGHT':
        return mod_x, l[3]
    return 0, l[3]
