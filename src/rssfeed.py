# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo RSS Feed module
# -----------------------------------------------------------------------
# $Id$
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
RSS Feed module
"""

import re
import sys
if sys.hexversion >= 0x2050000:
    import xml.etree.cElementTree as ET
else:
    try:
        import cElementTree as ET
    except ImportError:
        import elementtree.ElementTree as ET

import config

__all__ = ["Feed"]

class Feed:
    def __init__(self, inputSource):
        "Feed"
        self.title="None"
        self.description="None"
        self.items=[]
        self.parseFeed(inputSource)

    class Item:
        "Feed Item"
        title="None"
        description="None"
        date="None"
        url="None"
        type="None"
        length="None"

        def __str__(self):
            return '%r @ %r' % (self.title, self.url)

        def __repr__(self):
            return '%r @ %r' % (self.title, self.url)

    def parseFeed(self, feed):
        root = ET.parse(feed)
        channel = root.find('.//channel')
        if channel:
            title = channel.find('title')
            self.title = ET.iselement(title) and title.text or 'None'
            description = channel.find('description')
            self.description = ET.iselement(description) and description.text or 'None'
            pubDate = channel.find('pubDate')
            self.pubDate = ET.iselement(pubDate) and pubDate.text or 'None'
            items = channel.findall('item')
            for item in items:
                newItem = self.Item()
                element = item.find('title')
                newItem.title = element.text or 'None'
                element = item.find('description')
                newItem.description = element.text or 'None'
                element = item.find('pubDate')
                if element is not None:
                    newItem.date = element.text or 'None'
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    newItem.url = 'url' in enclosure.attrib and enclosure.attrib['url'] or 'None'
                    newItem.type = 'type' in enclosure.attrib and enclosure.attrib['type'] or 'None'
                    newItem.length = 'length' in enclosure.attrib and enclosure.attrib['length'] or 'None'
                self.items.append(newItem)


if __name__ == '__main__':
    import urllib

    feed = Feed(urllib.urlopen('http://www.la7.it/rss/barbariche.xml'))
    print feed.__dict__
