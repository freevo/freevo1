# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for album cover support
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
import logging
logger = logging.getLogger("freevo.audio.plugins.coversearch")


import os

import menu
import plugin
import re
import urllib2
import time
import traceback
import config
import kaa.imlib2 as imlib2
from xml.dom import minidom # ParseError used by amazon module

from gui.PopupBox import PopupBox
from gui.AlertBox import AlertBox

import dialog

import util
from util import amazon

try:
    amazon.setLocale(config.AMAZON_LOCALE)
except AttributeError:
    pass
config.AMAZON_QUERY_ENCODING = config.AMAZON_QUERY_ENCODING

class PluginInterface(plugin.ItemPlugin):
    """
    This plugin will allow you to search for CD Covers for your albums. To do that
    just go in an audio item and press 'e' (on your keyboard) or 'ENTER' on your
    remote control. That will present you a list of options with Find a cover for
    this music as one item, just select it press 'enter' (on your keyboard) or
    'SELECT' on your remote control and then it will search the cover in amazon.com.

    Please Notice that this plugin use the Amazon.com web services and you will need
    an Amazon developer key. You can get your at: http://aws.amazon.com/,

    To activate this plugin, put the following in your local_conf.py.

    Or this one if you want to pass the key to the plugin directly:
    | plugin.activate('audio.coversearch', args=('YOUR_ACCESS_KEY','YOUR_SECRET_KEY'))
    """

    def __init__(self, license=None, secret=None):
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return

        if license and secret:
            amazon.setLicenseKey(license)
            amazon.setSecretKey(secret)
        else:
            print String(_('To search for covers you need an Amazon.com Web Services\n' \
                     'license key. You can get yours from:\n'))
            print 'http://aws.amazon.com/'
            self.reason = "No amazon access/secret key"
            return

        plugin.ItemPlugin.__init__(self)


    def config(self):
        return [
            ('AMAZON_LOCALE', 'us', 'The location is one of: de, jp, uk, us'),
            ('AMAZON_QUERY_ENCODING', 'utf-8', 'The character encoding of web pages'),
        ]


    def actions(self, item):
        self.item = item

        if not hasattr(item, 'name'):
            logger.debug('cannot search for a cover as item has no name')
            return []

        # don't allow this for items on an audio cd, only on the disc itself
        if item.type == 'audio' and item.parent and item.parent.type == 'audiocd':
            logger.debug('cannot search for a cover for a cd item "%s"', item.name)
            return []

        # don't allow this for items in a playlist
        if item.type == 'audio' and item.parent and item.parent.type == 'playlist':
            logger.debug('cannot search for a cover for a playlist item "%s"', item.name)
            return []

        # do don't call this when we have an image
        if item.type == 'audiocd' and item.image:
            logger.debug('already have a cover for this cd "%s"', item.name)
            return []

        # do don't call this when we have an image
        if item.type == 'audio' and hasattr(item, 'filename') and item.filename and \
            vfs.isfile(os.path.join(os.path.join(os.path.dirname(item.filename), 'cover.jpg'))):
            logger.debug('already has a cover "%s"', item.name)
            return []

        if item.type in ('audio', 'audiocd', 'dir'):
            logger.debug('type=%r', item.type)
            logger.debug('name=%r', item['name'])
            logger.debug(hasattr(item, 'artist') and 'artist=%r', item.getattr('artist') or 'NO artist')
            logger.debug(hasattr(item, 'album') and 'album=%r', item.getattr('album') or 'NO album')
            logger.debug(hasattr(item, 'title') and 'title=%r', item.getattr('title') or 'NO title')
            try:
                if not hasattr(item, 'artist'):
                    if item.type in ('audio', 'dir') and not hasattr(item, 'album'):
                        # This is very iffy code
                        split_name = item.name.split(' - ')
                        if len(split_name) < 2:
                            split_name.append('')
                        item.artist, item.album = split_name
                        #else:
                        #    import util, kaa.metadata
                        #    files = util.match_files_recursively(item.dir, ['mp3', 'ogg', 'flac'])
                        #    for file in files:
                        #        metadata = kaa.metadata.parse(file)
                        #        item.artist = metadata.artist
                        #        item.album = metadata.album
                        #        item.title = metadata.title
                        #        if item.artist and item.album:
                        #            logger.debug('%r - %r', item.artist, item.album)
                        #            break
                        #    else:
                        #        logger.info('No files in %r', item.dir)
                    if item.type in ('audiocd',) and not hasattr(item, 'title'):
                        item.title = item.name
            except Exception, why:
                logger.debug('%s: %s', item.name, why)
                traceback.print_exc()

            try:
                # use title for audio cds and album for normal data
                if self.item.getattr('artist') and (
                    (item.type in ('audio', 'dir')) or #and self.item.getattr('album') or
                    (item.type in ('audiocd',) and self.item.getattr('title'))):
                    return [ (self.cover_search_file, _('Find a cover for this music'),
                               'imdb_search_or_cover_search') ]
                else:
                    logger.debug(_("'coversearch' was disabled for this item! ""'coversearch' needs an item with ""Artist and Album (if it's a mp3 or ogg) or ""Title (if it's a cd track) to be able to search. ""So you need a file with a ID3 tag (mp3) or an Ogg Info. ""Maybe you must fix this file (%s) tag?"), item.filename)





            except KeyError:
                logger.debug(_("Plugin 'coversearch' was disabled for this item! ""'coversearch' needs an item with ""Artist and Album (if it's a mp3 or ogg) or ""Title (if it's a cd track) to be able to search. ""So you need a file with a ID3 tag (mp3) or an Ogg Info. ""Maybe you must fix this file (%s) tag?"), item.filename)





            except AttributeError:
                logger.debug(_("Unknown CD, cover searching is disabled"))
        return []


    def cover_search_file(self, arg=None, menuw=None):
        """
        search Amazon for this item
        """
        logger.debug('cover_search_file(arg=%r, menuw=%r)', arg, menuw)
        box = PopupBox(text=_('searching Amazon...'))
        box.show()

        album = self.item.getattr('album')
        if not album:
            album = self.item.getattr('title')

        artist = self.item.getattr('artist')

        # Maybe the search string need encoding to config.LOCALE
        search_string = '%s %s' % (artist.encode(config.AMAZON_QUERY_ENCODING),
                                   album.encode(config.AMAZON_QUERY_ENCODING))
        search_string = re.sub('[\(\[].*[\)\]]', '', search_string)
        logger.debug('search_string=%r', search_string)
        try:
            cover = amazon.ItemSearch(search_string, SearchIndex='Music', ResponseGroup='Images,ItemAttributes')
        except amazon.AWSException, why:
            box.destroy()
            title = '\n'.join([artist, album])
            dict_tmp = { 'artist': artist, 'album': album }
            print '%(artist)s - %(album)s' % (dict_tmp)
            print '%r' % why
            box = PopupBox(text=artist+'\n'+album+'\n'+why[:40])
            box.show()
            time.sleep(2)
            box.destroy()
            return
        except Exception, why:
            box.destroy()
            box = PopupBox(text=_('Unknown error while searching, please check the log file for details.'))
            import traceback
            traceback.print_exc()
            box.show()
            time.sleep(2)
            box.destroy()
            return

        items = []

        # Check if they're valid before presenting the list to the user
        # Grrr I wish Amazon wouldn't return an empty gif (807b)
        if cover:
            try:
                for item in cover:
                    title = 'Unknown'
                    if hasattr(item, 'Title'):
                        title = item.Title
                    url = None
                    width = 0
                    height = 0
                    if hasattr(item, 'LargeImage'):
                        url = item.LargeImage.URL
                        width = item.LargeImage.Width
                        height = item.LargeImage.Height
                    elif hasattr(item, 'MediumImage'):
                        url = item.MediumImage.URL
                        width = item.LargeImage.Width
                        height = item.LargeImage.Height
                    if url is not None:
                        imageFound = False
                        m = None
                        try:
                            m = urllib2.urlopen(item.LargeImage.URL)
                            imageFound = True
                        except urllib2.URLError, e:
                            logger.info('URLError: %s', e)
                        except urllib2.HTTPError, e:
                            # Amazon returned a 404
                            logger.info('HTTPError: %s', e)
                        if imageFound and (m.info()['Content-Length'] != '807'):
                            image = imlib2.open_from_memory(m.read())
                            items += [ menu.MenuItem('%s (%sx%s)' % (title, width, height), self.cover_create, url,
                                image=image) ]
                        else:
                            # maybe the url is wrong, try to change '.01.' to '.03.'
                            url = url.replace('.01.', '.03.')
                            try:
                                m = urllib2.urlopen(item.LargeImage.URL)
                                imageFound = True
                            except urllib2.URLError, e:
                                logger.info('URLError: %s', e)
                            except urllib2.HTTPError, e:
                                # Amazon returned a 404
                                logger.info('HTTPError: %s', e)
                            if imageFound and (m.info()['Content-Length'] != '807'):
                                image = imlib2.open_from_memory(m.read())
                                items += [ menu.MenuItem('%s (%sx%s)' % (title, width, height), self.cover_create, url,
                                    image=image) ]
                        if m is not None:
                            m.close()

                box.destroy()
                if len(items) == 1:
                    self.cover_create(arg=items[0].arg, menuw=menuw)
                    return
                if items:
                    moviemenu = menu.Menu(_('Cover Search Results'), items)
                    menuw.pushmenu(moviemenu)
                    return

            except Exception, why:
                print traceback.print_exc()
                box = PopupBox(text= _('No covers available from Amazon'))
                box.show()
                time.sleep(2)
                box.destroy()


    def cover_create(self, arg=None, menuw=None):
        """
        create cover file for the item
        """
        import directory

        box = PopupBox(text= _('getting data...'))
        box.show()

        #filename = os.path.splitext(self.item.filename)[0]
        if self.item.type == 'audiocd':
            filename = '%s/disc/metadata/%s.jpg' % (config.OVERLAY_DIR, self.item.info['id'])
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
            image = imlib2.open(filename)
            width, height = image.size
            image.crop((2, 2), (width-4, height-4)).save(filename)
            util.cache_image(filename)
        except Exception, why:
            logger.warning(why)

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
