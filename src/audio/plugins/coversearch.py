# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# coverserarch.py - Plugin for album cover support
# -----------------------------------------------------------------------
# $Id$
#
# Notes: This plugin will allow you to find album covers. At first, only
#        Amazon is supported. Someone could easily add allmusic.com support
#        which is more complete, but lacks a general interface like amazon's
#        web services.
#
#        You also need an Amazon developer key.
#
# Problem:
#     If a cover is not available, Amazon returns an 807b GIF file instead
#     of saying so
#
# Solution:
#     What we do now is check the content length of the file
#     before downloading and remove those entries from the list.
#
# I've also removed the example, since the plugin itself works better.
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

import menu
import plugin
import re
import urllib2
import time
import config
import kaa.imlib2 as Image
from xml.dom import minidom # ParseError used by amazon module

from gui.PopupBox import PopupBox
from gui.AlertBox import AlertBox

from util import amazon

try:
    amazon.setLocale(config.AMAZON_LOCALE)
except AttributeError:
    pass
query_encoding = config.AMAZON_QUERY_ENCODING

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin will allow you to search for CD Covers for your albums. To do that
    just go in an audio item and press 'e' (on your keyboard) or 'ENTER' on your
    remote control. That will present you a list of options with Find a cover for
    this music as one item, just select it press 'enter' (on your keyboard) or
    'SELECT' on your remote control and then it will search the cover in amazon.com.

    Please Notice that this plugin use the Amazon.com web services and you will need
    an Amazon developer key. You can get your at: http://www.amazon.com/webservices,
    get that key and put it in a file named ~/.amazonkey or passe it as an argument
    to this plugin.

    To activate this plugin, put the following in your local_conf.py.

    If you have the key in ~/.amazonkey
    | plugin.activate( 'audio.coversearch' )

    Or this one if you want to pass the key to the plugin directly:
    | plugin.activate( 'audio.coversearch', args=('YOUR_KEY',) )
    """

    def __init__(self, license=None):
        if not config.USE_NETWORK:
            self.reason = 'no network'
            return

        if license:
            amazon.setLicense(license)
        try:
            amazon.getLicense()
        except amazon.NoLicenseKey:
            print String(_( 'To search for covers you need an Amazon.com Web Services\n' \
                     'license key. You can get yours from:\n' ))
            print 'https://associates.amazon.com/exec/panama/associates/join/'\
                  'developer/application.html'
            self.reason = 'no amazon key'
            return

        plugin.ItemPlugin.__init__(self)


    def actions(self, item):
        self.item = item

        if not hasattr(item, 'name'):
            _debug_('cannot search for a cover as item has no name')
            return []

        # don't allow this for items on an audio cd, only on the disc itself
        if item.type == 'audio' and item.parent and item.parent.type == 'audiocd':
            _debug_('cannot search for a cover for a cd item "%s"', (item.name))
            return []

        # don't allow this for items in a playlist
        if item.type == 'audio' and item.parent and item.parent.type == 'playlist':
            _debug_('cannot search for a cover for a playlist item "%s"', (item.name))
            return []

        # do don't call this when we have an image
        if item.type == 'audiocd' and item.image:
            _debug_('already have a cover for this cd "%s"', (item.name))
            return []

        # do don't call this when we have an image
        if item.type == 'audio' and hasattr(item, 'filename') and item.filename and \
            vfs.isfile(os.path.join(os.path.join(os.path.dirname(item.filename), 'cover.jpg'))):
            _debug_('already has a cover "%s"', (item.name))
            return []

        if item.type in ('audio', 'audiocd', 'dir'):
            _debug_('type=\"%s\"' % item.type)
            _debug_('name=\"%s\"' % item['name'])
            _debug_(hasattr(item, 'artist') and 'artist="%s"' % item.getattr('artist') or 'NO artist')
            _debug_(hasattr(item, 'album')  and 'album="%s"'  % item.getattr('album')  or 'NO album')
            _debug_(hasattr(item, 'title')  and 'title="%s"'  % item.getattr('title')  or 'NO title')
            try:
                if not hasattr(item, 'artist'):
                    if item.type in ('audio', 'dir') and not hasattr(item, 'album'):
                        item.artist, item.album = item.name.split(' - ')
                    if item.type in ('audiocd',) and not hasattr(item, 'title'):
                        item.title = item.name
            except Exception, e:
                _debug_('%s: %s' % (item.name, e))

            try:
                # use title for audio cds and album for normal data
                if self.item.getattr('artist') and \
                   ((self.item.getattr('album') and item.type in ('audio', 'dir')) or \
                    (self.item.getattr('title') and item.type == 'audiocd')):
                    return [ (self.cover_search_file, _('Find a cover for this music'),
                               'imdb_search_or_cover_search') ]
                else:
                    if config.DEBUG > 1:
                        print String(_( "Plugin 'coversearch' was disabled for this item! " \
                                 "'coversearch' needs an item with " \
                                 "Artist and Album (if it's a mp3 or ogg) or " \
                                 "Title (if it's a cd track) to be able to search. "  \
                                 "So you need a file with a ID3 tag (mp3) or an Ogg Info. "  \
                                 "Maybe you must fix this file (%s) tag?" )) % item.filename
            except KeyError:
                if config.DEBUG > 1:
                    print String(_( "Plugin 'coversearch' was disabled for this item! " \
                             "'coversearch' needs an item with " \
                             "Artist and Album (if it's a mp3 or ogg) or " \
                             "Title (if it's a cd track) to be able to search. " \
                             "So you need a file with a ID3 tag (mp3) or an Ogg Info. " \
                             "Maybe you must fix this file (%s) tag?" )) % item.filename
            except AttributeError:
                if config.DEBUG > 1:
                    print String(_( "Unknown CD, cover searching is disabled" ))
        return []


    def cover_search_file(self, arg=None, menuw=None):
        """
        search imdb for this item
        """
        box = PopupBox(text=_( 'searching Amazon...' ) )
        box.show()

        album = self.item.getattr('album')
        if not album:
            album = self.item.getattr('title')

        artist = self.item.getattr('artist')

        # Maybe the search string need encoding to config.LOCALE
        search_string = '%s %s' % (artist.encode(query_encoding), album.encode(query_encoding))
        search_string = re.sub('[\(\[].*[\)\]]', '', search_string)
        if config.DEBUG > 1:
            print "search_string=%r" % search_string
        try:
            cover = amazon.searchByKeyword(search_string , product_line="music")
        except amazon.AmazonError:
            box.destroy()
            dict_tmp = { 'artist': artist, 'album': album }
            box = PopupBox(text=_( 'No matches for %(artist)s - %(album)s' ) % dict_tmp )
            box.show()
            time.sleep(2)
            box.destroy()
            return

        except:
            box.destroy()
            box = PopupBox(text=_( 'Unknown error while searching.' ) )
            box.show()
            time.sleep(2)
            box.destroy()
            return

        items = []

        # Check if they're valid before presenting the list to the user
        # Grrr I wish Amazon wouldn't return an empty gif (807b)

        for i in range(len(cover)):
            m = None
            imageFound = False
            try:
                if cover[i].ImageUrlLarge:
                    m = urllib2.urlopen(cover[i].ImageUrlLarge)
                    imageFound = True
            except urllib2.HTTPError:
                # Amazon returned a 404
                pass
            if imageFound and (m.info()['Content-Length'] != '807'):
                image = Image.open_from_memory(m.read())
                items += [ menu.MenuItem('%s' % cover[i].ProductName,
                    self.cover_create, cover[i].ImageUrlLarge, image=image) ]
            else:
                # see if a small one is available
                try:
                    if cover[i].ImageUrlMedium:
                        if m: m.close()
                        m = urllib2.urlopen(cover[i].ImageUrlMedium)
                        imageFound = True
                except urllib2.HTTPError:
                    pass
                if imageFound and (m.info()['Content-Length'] != '807'):
                    image = Image.open_from_memory(m.read())
                    items += [ menu.MenuItem( ('%s [' + _( 'small' ) + ']') % cover[i].ProductName,
                        self.cover_create, cover[i].ImageUrlMedium) ]
                else:
                    # maybe the url is wrong, try to change '.01.' to '.03.'
                    cover[i].ImageUrlLarge = cover[i].ImageUrlLarge.replace('.01.', '.03.')
                    try:
                        if cover[i].ImageUrlLarge:
                            if m: m.close()
                            m = urllib2.urlopen(cover[i].ImageUrlLarge)
                            imageFound = True

                        if imageFound and (m.info()['Content-Length'] != '807'):
                            image = Image.open_from_memory(m.read())
                            items += [ menu.MenuItem( ('%s [' + _( 'small' ) + ']' ) % cover[i].ProductName,
                                self.cover_create, cover[i].ImageUrlLarge) ]
                    except urllib2.HTTPError:
                        pass
            if m: m.close()

        box.destroy()
        if len(items) == 1:
            self.cover_create(arg=items[0].arg, menuw=menuw)
            return
        if items:
            moviemenu = menu.Menu( _( 'Cover Search Results' ), items)
            menuw.pushmenu(moviemenu)
            return

        box = PopupBox(text= _( 'No covers available from Amazon' ) )
        box.show()
        time.sleep(2)
        box.destroy()
        return


    def cover_create(self, arg=None, menuw=None):
        """
        create cover file for the item
        """
        import directory

        box = PopupBox(text= _( 'getting data...' ) )
        box.show()

        #filename = os.path.splitext(self.item.filename)[0]
        if self.item.type == 'audiocd':
            filename = '%s/disc/metadata/%s.jpg' % (config.OVERLAY_DIR,
                                                    self.item.info['id'])
        elif self.item.type == 'dir':
            filename = os.path.join(self.item.dir, 'cover.jpg')
        else:
            filename = '%s/cover.jpg' % (os.path.dirname(self.item.filename))

        fp = urllib2.urlopen(str(arg))
        m = vfs.open(filename,'wb')
        m.write(fp.read())
        m.close()
        fp.close()

        # try to crop the image to avoid ugly borders
        try:
            image = Image.open(filename)
            width, height = image.size
            image.crop((2,2,width-4, height-4)).save(filename)
        except:
            pass

        if self.item.type in ('audiocd', 'dir'):
            self.item.image = filename
        elif self.item.parent.type == 'dir':
            # set the new cover to all items
            self.item.parent.image = filename
            for i in self.item.parent.menu.choices:
                i.image = filename

        # check if we have to go one menu back (called directly) or
        # two (called from the item menu)
        back = 1
        if menuw.menustack[-2].selected != self.item:
            back = 2

        # maybe we called the function directly because there was only one
        # cover and we called it with an event
        if menuw.menustack[-1].selected == self.item:
            back = 0

        # update the directory
        if directory.dirwatcher:
            directory.dirwatcher.scan()

        # go back in menustack
        for i in range(back):
            menuw.delete_menu()

        if back == 0:
            menuw.refresh()
        box.destroy()
