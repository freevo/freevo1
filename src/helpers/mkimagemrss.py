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

if sys.hexversion >= 0x2050000:
    import xml.etree.ElementTree as ET
    from xml.etree.cElementTree import ElementTree, Element, SubElement, iterparse, dump
else:
    import elementtree.ElementTree as ET
    try:
        import cElementTree
        from cElementTree import ElementTree, Element, SubElement, iterparse, dump
    except ImportError:
        from elementtree.ElementTree import ElementTree, Element, SubElement, iterparse, dump


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


def makerss(d, files):
    root = Element('xml', version='1.0', encoding='utf-8', standalone='yes')
    rss = SubElement(root, 'rss')
    rss.attrib['xmlns:atom'] = NS_ATOM
    rss.attrib['xmlns:media'] = NS_MEDIA
    channel = SubElement(rss, 'channel')
    dirlen = len(d)+len(os.path.sep)
    for image in files:
        thumb = util.www_thumbnail_path(image)
        item = SubElement(channel, 'item')
        title = SubElement(item, 'title')
        title.text = os.path.basename(image[dirlen:])
        link = SubElement(item, 'link')
        link.text = image[dirlen:]
        description = SubElement(item, 'media:description')
        description.text = os.path.basename(image)
        thumbnail = SubElement(item, 'media:thumbnail', url=thumb[dirlen:])
        content = SubElement(item, 'media:content', url=image[dirlen:])

    indent(root)
    ElementTree(root).write(os.path.join(d, 'photos.rss'))


def imagefiles():
    files = []
    for d in config.IMAGE_ITEMS:
        try:
            d = d[1]
        except:
            pass
        if not os.path.isdir(d):
            continue
        print 'Building photos.rss for %s' % d
        files = util.match_files_recursively(d, config.IMAGE_SUFFIX)
        makerss(d, files)
    return files


if __name__ == '__main__':
    imagefiles()
