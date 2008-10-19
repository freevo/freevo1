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
from optparse import Option, OptionValueError, OptionParser, IndentedHelpFormatter

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

options = None

NS_MEDIA='http://search.yahoo.com/mrss'
NS_ATOM='http://www.w3.org/2005/Atom'
try:
    register_namespace = ET.register_namespace
except AttributeError:
    def register_namespace(prefix, uri):
        ET._namespace_map[uri] = prefix
register_namespace('media', NS_MEDIA)
register_namespace('atom', NS_ATOM)


def maketitle(pathname):
    title = os.path.basename(pathname)
    title = title.replace('_', ' ')
    titlewords = title.split()
    for i in range(len(titlewords)):
        titlewords[i] = titlewords[i].capitalize()
    title = ' '.join(titlewords)
    return title


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


def makerss(titletext, top, root, files):
    print 'Building %s' % os.path.join(root, 'photos.rss')
    dirlen = len(top)+len(os.path.sep)
    rootpath = root[dirlen:]
    rootlen = len(rootpath)+len(os.path.sep)
    rss = Element('rss', version='2.0')
    rss.attrib['xmlns:atom'] = NS_ATOM
    rss.attrib['xmlns:media'] = NS_MEDIA
    channel = SubElement(rss, 'channel')
    title = SubElement(channel, 'title')
    title.text = titletext
    description = SubElement(channel, 'description')
    description.text = _('This feed enables cooliris http://www.cooliris.com/ in your web browser')
    channel.append(Comment('must have a link for rss'))
    link = SubElement(channel, 'link')
    link.text = 'http://localhost/'
    result = []
    for image in files:
        imagepath = util.www_image_path(image, '.images')
        if not options.noimages:
            util.www_image_create(os.path.join(top, image), force=options.force, verbose=options.verbose)
        thumbpath = util.www_image_path(image, '.thumbs')
        if not options.nothumbs:
            util.www_thumb_create(os.path.join(top, image), force=options.force, verbose=options.verbose)
        if options.verbose >= 3:
            print 'rootpath:', rootpath, 'image:', image, 'imagepath:', imagepath, 'thumbpath:', thumbpath
            print 'imagepath[rootlen:]:', imagepath[rootlen:], 'thumbpath[rootlen:]:', thumbpath[rootlen:]
        result.append(os.path.join(rootpath, image))
        image = image[rootlen:]
        item = SubElement(channel, 'item')
        title = SubElement(item, 'title')
        title.text = convert_entities(image)
        link = SubElement(item, 'link')
        link.text = urllib.quote(imagepath)
        description = SubElement(item, 'media:description')
        description.text = convert_entities(os.path.splitext(os.path.basename(image))[0])
        #thumbnail = SubElement(item, 'media:thumbnail', url=imagepath[rootlen:])
        #thumbnail = SubElement(item, 'media:thumbnail', url=urllib.quote_plus(os.path.join('.thumbs', image)))
        thumbnail = SubElement(item, 'media:thumbnail', url=urllib.quote(thumbpath[rootlen:]))
        #content = SubElement(item, 'media:content', url=os.path.join('.images', image))
        #content = SubElement(item, 'media:content', url=urllib.quote_plus(os.path.join('.images', image)))
        content = SubElement(item, 'media:content', url=urllib.quote(imagepath[rootlen:]))

    indent(rss)
    file = open(os.path.join(root, 'photos.rss'), 'w')
    print >>file, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    print >>file, tostring(rss)
    file.close()
    return result


def imagefiles(title, top, subdir):
    images = []
    image_root = subdir[len(top)+1:]
    for pathname in os.listdir(subdir):
        if pathname.startswith('.'):
            continue
        path = os.path.join(subdir, pathname)
        if os.path.isdir(path):
            images += imagefiles(maketitle(path), top, path)
        else:
            extn = os.path.splitext(path)[1][1:].lower()
            if extn in config.IMAGE_SUFFIX:
                images.append(os.path.join(image_root, pathname))
    if options.verbose >= 3:
        print 'title:', title, 'top:', top, 'subdir:', subdir, 'images:', images
    makerss(title, top, subdir, images)
    return images


def parse_options():
    """
    Parse command line options
    """
    import version, revision
    _version = version.__version__
    if _version.endswith('-svn'):
        _version = _version.split('-svn')[0] + ' r%s' % revision.__revision__
    thumbsize = config.WWW_IMAGE_THUMBNAIL_SIZE
    imagesize = config.WWW_IMAGE_SIZE
    formatter=IndentedHelpFormatter(indent_increment=2, max_help_position=36, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="""
Make image MRSS feed for CoolIris (http://www.cooliris.com/site/support/download-all-products.php)

Usage: %prog [options]""", version='%prog ' + _version)
    parser.add_option('-v', '--verbose', action='count', default=0,
        help='set the level of verbosity')
    parser.add_option('-r', '--rebuild', action='store_true', dest='force', default=False,
        help='rebuild the thumbnails and images [default:%default]')
    parser.add_option('-t', '--thumb-size', action='store', dest='thumbsize', default=thumbsize, metavar='SIZE',
        help='size of thumbnail images [default:%default]')
    parser.add_option('-i', '--image-size', action='store', dest='imagesize', default=imagesize, metavar='SIZE',
        help='size of images [default:%default]')
    parser.add_option('-T', '--no-thumbs', action='store_true', dest='nothumbs', default=False,
        help='do not build thumbnail images [default:%default]')
    parser.add_option('-I', '--no-images', action='store_true', dest='noimages', default=False,
        help='Do not build images [default:%default]')
    return parser.parse_args()

if __name__ == '__main__':
    (options, args) = parse_options()
    for d in config.IMAGE_ITEMS:
        title, top = d
        imagefiles(title, top, top)
