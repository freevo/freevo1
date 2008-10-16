# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Make a Media RSS feed
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


import os, sys
import urllib, urllib2

if sys.hexversion >= 0x2050000:
    import xml.etree.ElementTree as ET
    from xml.etree.cElementTree import ElementTree, Element, SubElement, Comment, iterparse, dump, tostring
else:
    import elementtree.ElementTree as ET
    try:
        import cElementTree
        from cElementTree import ElementTree, Element, SubElement, Comment, iterparse, dump, tostring
    except ImportError:
        from elementtree.ElementTree import ElementTree, Element, SubElement, Comment, iterparse, dump, tostring


import config
import util

NS_MEDIA='http://search.yahoo.com/mrss'
NS_ATOM='http://www.w3.org/2005/Atom'


try:
    register_namespace = ET.register_namespace
except AttributeError:
    def register_namespace(prefix, uri):
        ET._namespace_map[uri] = prefix

register_namespace('media', NS_MEDIA)
register_namespace('atom', NS_ATOM)


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def convert_entities(contents):
    s = contents.strip()
    s = s.replace('\n', ' ')
    s = s.replace('  ', ' ')
    s = s.replace('&', '&amp;')
    s = s.replace('&amp;#', '&#')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    s = s.replace('"', '&quot;')
    return s


def makerss(top, root, files):
    print 'Building %s' % os.path.join(root, 'photos.rss')
    dirlen = len(top)+len(os.path.sep)
    rootpath = root[dirlen:]
    rootlen = len(rootpath)+len(os.path.sep)
    rss = Element('rss', version='2.0')
    rss.attrib['xmlns:atom'] = NS_ATOM
    rss.attrib['xmlns:media'] = NS_MEDIA
    channel = SubElement(rss, 'channel')
    title = SubElement(channel, 'title')
    title.text = os.path.basename(root)
    channel.append(Comment('must have a link for rss'))
    link = SubElement(channel, 'link')
    link.text = 'http://localhost/'
    result = []
    for image in files:
        print rootpath, rootlen, image[rootlen:]
        result.append(os.path.join(rootpath, image))
        image = image[rootlen:]
        thumb = util.www_thumbnail_path(image)
        item = SubElement(channel, 'item')
        title = SubElement(item, 'title')
        title.text = convert_entities(image)
        link = SubElement(item, 'link')
        link.text = urllib.quote(image)
        description = SubElement(item, 'media:description')
        description.text = convert_entities(os.path.splitext(os.path.basename(image))[0])
        if os.path.exists(os.path.join(top, thumb)):
            #thumbnail = SubElement(item, 'media:thumbnail', url=thumb)
            #thumbnail = SubElement(item, 'media:thumbnail', url=urllib.quote_plus(thumb))
            thumbnail = SubElement(item, 'media:thumbnail', url=urllib.quote(thumb))
        else:
            print 'thumbnail %s is missing' % (os.path.join(top, thumb),)
            thumbnail = SubElement(item, 'media:thumbnail', url=urllib.quote(image))
        #content = SubElement(item, 'media:content', url=image)
        #content = SubElement(item, 'media:content', url=urllib.quote_plus(image))
        content = SubElement(item, 'media:content', url=urllib.quote(image))

    indent(rss)
    file = open(os.path.join(root, 'photos.rss'), 'w')
    print >>file, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    print >>file, tostring(rss)
    file.close()
    return result


def imagefiles(top, subdir):
    images = []
    image_root = subdir[len(top)+1:]
    for name in os.listdir(subdir):
        if name.startswith('.'):
            continue
        path = os.path.join(subdir, name)
        if os.path.isdir(path):
            images += imagefiles(top, path)
        else:
            extn = os.path.splitext(path)[1][1:].lower()
            if extn in config.IMAGE_SUFFIX:
                images.append(os.path.join(image_root, name))
    #print top, subdir, images
    makerss(top, subdir, images)
    return images


if __name__ == '__main__':
    for d in config.IMAGE_ITEMS:
        top = d[1]
        imagefiles(top, top)
