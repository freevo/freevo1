# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Base class of a media item
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
Base class of a media item
"""

import os
import gettext
import shutil
import pygame
from pprint import pformat

import config
from event import *
import plugin
import util

from util import mediainfo, vfs, Unicode
from gui import AlertBox


class FileInformation:
    """
    file operations for an item
    """
    def __init__(self):
        """
        Create an instance of a FileInformation object.

        @ivar files: a list of files.
        @ivar fxd_file: the FXD (freevo extended data) file.
        @ivar edl_file: the EDL (edit decision list) file.
        @ivar image: the image for the item.
        @ivar read_only: Is the item read only.
        """
        self.files     = []
        self.fxd_file  = ''
        self.edl_file  = ''
        self.image     = ''
        self.read_only = False


    def __str__(self):
        s = pformat(self, depth=2)
        return s


    def __repr__(self):
        if hasattr(self, 'name'):
            s = '%s: %r' % (self.name, self.__class__)
        else:
            s = '%r' % (self.__class__)
        return s


    def append(self, filename):
        self.files.append(filename)


    def get(self):
        return self.files


    def copy_possible(self):
        return self.files != []


    def copy(self, destdir):
        for f in self.files + [ self.fxd_file, self.image, self.edl_file ]:
            if f:
                error_msg=''
                if vfs.isoverlay(f):
                    d = vfs.getoverlay(destdir)
                else:
                    d = destdir

                if not os.path.isdir(d):
                    os.makedirs(d)

                if os.path.isdir(f):
                    dst = os.path.join(d, os.path.split(f)[1])
                    shutil.copytree(f, dst)
                else:
                    dst = os.path.join(d, os.path.split(f)[1])
                    if os.path.exists(dst):
                        if config.SHOPPINGCART_CLOBBER:
                            try:
                                os.unlink(dst)
                            except IOError, e:
                                error_msg='Can\'t delete "%s": %s' % (dst, e)

                        else:
                            error_msg='Can\'t copy "%s", destination exists' % dst
                    else:
                        try:
                            shutil.copy2(f, d)
                        except IOError, e:
                            error_msg='Can\'t copy "%s": %s' % (f, e)

                if error_msg:
                    _debug_(error_msg, DWARNING)
                    #AlertBox(text=_(Unicode(error_msg))).show()


    def move_possible(self):
        return self.files and not self.read_only


    def move(self, destdir):
        for f in self.files + [ self.fxd_file, self.image, self.edl_file ]:
            if f:
                if vfs.isoverlay(f):
                    d = vfs.getoverlay(destdir)
                else:
                    d = destdir
                if not os.path.isdir(d):
                    os.makedirs(d)
                os.system('mv "%s" "%s"' % (f, d))


    def delete_possible(self):
        return self.files and not self.read_only


    def delete(self):
        for f in self.files + [ self.fxd_file, self.image, self.edl_file ]:
            if not f:
                continue
            if os.path.isdir(f) and not os.path.islink(f):
                shutil.rmtree(f, ignore_errors=1)
            else:
                try:
                    os.unlink(f)
                except:
                    _debug_('can\'t delete %r' % (f,), DWARNING)


class Item:
    """
    Item class. This is the base class for all items in the menu.

    It's a template for MenuItem and for other info items like VideoItem,
    AudioItem and ImageItem

    @ivar type: the type of the media item.
    @ivar name: the name of the media item.
    @ivar parent: the parent of the media item.
    @ivar icon: the icon of the media item.
    @ivar info: get the information of the media item.
    @ivar menuw: the menu widget of the media item.
    @ivar description: the description of the media item.
    @ivar image: the image of the media item.
    @ivar skin_fxd: the skin FXD for the media item.
    @ivar media: the media of the item.
    @ivar fxd_file: the FXD file for the media item.
    @ivar network_play: is the item on the network?
    @ivar filename: the file name of the media item.
    @ivar mode: the type of the URL: file, http, dvd, etc.
    @ivar files: list of files for the media item.
    @ivar mimetype: the mime-type of the mdeia item.
    @ivar eventhandler_plugins: the event handler for the media item.
    """
    def __init__(self, parent=None, info=None, skin_type=None):
        """
        Create an instance of an Item.
        @param parent: parent of the Item.
        @param info: info item of the Item.
        @param skin_type: skin type of the Item.
        """
        if not hasattr(self, 'type'):
            self.type     = None            # e.g. video, audio, dir, playlist

        self.name         = u''             # name in menu
        self.parent       = parent          # parent item to pass unmapped event
        self.icon         = None
        if info and isinstance(info, mediainfo.Info):
            self.info     = copy.copy(info)
        else:
            self.info     = mediainfo.Info(None, None, info)
        self.menuw        = None
        self.description  = ''
        self.rect         = pygame.Rect(0,0,0,0)
        self.image        = None            # imagefile
        self.skin_fxd     = None            # skin information etc.
        self.media        = None
        self.fxd_file     = None
        self.network_play = True            # network url, like http
        self.filename     = ''              # filename if it's a file:// url
        self.mode         = ''              # the type of the url (file, http, dvd...)
        self.files        = None            # FileInformation
        self.mimetype     = ''              # extention or mode

        self.eventhandler_plugins = []

        if not hasattr(self, 'autovars'):
            self.autovars = []

        if info and parent and hasattr(parent, 'DIRECTORY_USE_MEDIAID_TAG_NAMES') and \
               parent.DIRECTORY_USE_MEDIAID_TAG_NAMES and self.info.has_key('title'):
            self.name = self.info['title']

        if parent:
            self.image = parent.image
            if hasattr(parent, 'is_mainmenu_item'):
                self.image = None
            self.skin_fxd    = parent.skin_fxd
            self.media       = parent.media
            if hasattr(parent, '_'):
                self._ = parent._

        if skin_type:
            import skin
            settings  = skin.get_settings()
            skin_info = settings.mainmenu.items
            imagedir  = settings.mainmenu.imagedir
            if skin_info.has_key(skin_type):
                skin_info  = skin_info[skin_type]
                self.name  = _(skin_info.name)
                self.image = skin_info.image
                if skin_info.icon:
                    self.icon = os.path.join(settings.icon_dir, skin_info.icon)
                if skin_info.outicon:
                    self.outicon = os.path.join(settings.icon_dir, skin_info.outicon)
            if not self.image and imagedir:
                self.image = util.getimage(os.path.join(imagedir, skin_type))


    def __str__(self):
        """
        Create a string representation of an Item
        @returns: a string
        """
        s = pformat(self, depth=2)
        return s


    def __repr__(self):
        """
        Create a raw string representation of an Item
        @returns: a string
        """
        if hasattr(self, 'name'):
            s = '%s: %r' % (self.name, self.__class__)
        else:
            s = '%r' % (self.__class__)
        return s


    def __setattr__(self, key, value):
        """
        Set the attribute of an Item.
        @param key: name of attribute
        @param value: new value of the attribute
        """
        # force the setting of the url item through the function set_url
        if key=='url':
            self.set_url(value)
        else:
            # use all other values as they are
            self.__dict__[key] = value


    def set_url(self, url, info=True, search_image=True):
        """
        Set a new url to the item and adjust all attributes depending
        on the url.
        WARNING: This is called whenever self.url is set, therefor it is
        strictly forbidden to set self.url directly in this function,
        (infinit recursion!). Use self.__dict__['url'] instead!
        """
        # set the url itself
        if url and url.find('://') == -1:
            # local url
            self.__dict__['url'] = 'file://' + url
        else:
            # some other kind of url
            self.__dict__['url'] = url

        if self.url==None:
            # reset everything to default values
            self.network_play = True
            self.filename     = ''
            self.mode         = ''
            self.files        = None
            self.mimetype     = ''
            return

        # add additional info files
        self.files = FileInformation()
        if self.media:
            self.files.read_only = True

        # determine the mode of this item
        self.mode = self.url[:self.url.find('://')]

        if self.mode == 'file':
            self.network_play = False
            self.filename     = self.url[7:]
            self.files.append(self.filename)
            self.mimetype = os.path.splitext(self.filename)[1][1:].lower()

            if search_image:
                image = util.getimage(self.filename[:self.filename.rfind('.')])
                if image:
                    self.image = image
                    self.files.image = image
                elif self.parent and self.parent.type != 'dir':
                    imagepath= os.path.dirname(self.filename)
                    imagepath= os.path.join(imagepath, 'cover')
                    self.image = util.getimage(imagepath, self.image)
            # TODO: is this the right place for this?
            if config.TV_RECORD_REMOVE_COMMERCIALS:
                edlBase=self.filename[:self.filename.rfind('.')]
                edlFile=edlBase+".edl"
                self.edl_file=edlFile
                if os.path.exists(edlFile):
                    self.files.edl_file=edlFile
                else:
                    self.files.edl_file=None

            if info:
                self.info = mediainfo.get(self.filename)
                try:
                    if self.parent.DIRECTORY_USE_MEDIAID_TAG_NAMES:
                        self.name = self.info['title'] or self.name
                except:
                    pass
                if not self.name:
                    self.name = self.info['title:filename']

            if not self.name:
                self.name = util.getname(self.filename)
        else:
            # some defaults for other url types
            self.network_play = True
            self.filename     = ''
            self.mimetype     = self.type
            if not self.name:
                self.name     = Unicode(self.url)

    def __setitem__(self, key, value):
        """
        set the value of 'key' to 'val'
        """
        for var, val in self.autovars:
            if key == var:
                if val == value:
                    if self.info[key]:
                        if not self.delete_info(key):
                            _debug_('unable to store \'%s\':\'%s\' info for \'%s\'' % \
                                (key, value, self.filename), DINFO)
                else:
                    self.store_info(key, value)
                return
        self.info[key] = value


    def store_info(self, key, value):
        """
        store the key/value in metadata
        """
        _debug_('key=%s value=%s info-class=%s' % (key, value, self.info.__class__), 2)
        if hasattr(self, 'filename'): _debug_('filename=%s' % (self.filename), 2)

        if isinstance(self.info, mediainfo.Info):
            if not self.info.store(key, value):
                _debug_('cannot store \'%s\':\'%s\' for \'%s\'' % \
                    (key, value, self.filename), DINFO)
        else:
            _debug_('cannot store \'%s\':\'%s\' for \'%s\' item, not mediainfo' % \
                (key, value, self.filename), DINFO)


    def delete_info(self, key):
        """
        delete entry for metadata
        """
        if isinstance(self.info, mediainfo.Info):
            return self.info.delete(key)
        else:
            print 'unable to delete info for that kind of item'


    def id(self):
        """
        Return a unique id of the item. This id should be the same when the
        item is rebuild later with the same information
        """
        if hasattr(self, 'url'):
            return self.url
        return self.name


    def sort(self, mode=None):
        """
        Returns the string how to sort this item
        """
        return u'0%s' % self.name


    def translation(self, application):
        """
        Loads the gettext translation for this item (and all it's children).
        This can be used in plugins who are not inside the Freevo distribution.
        After loading the translation, gettext can be used by self._() instead
        of the global _().
        """
        try:
            self._ = gettext.translation(application, os.environ['FREEVO_LOCALE'],
                                         fallback=1).gettext
        except:
            self._ = lambda m: m


    def actions(self):
        """
        returns a list of possible actions on this item. The first
        one is autoselected by pressing SELECT
        """
        return None


    def __call__(self, arg=None, menuw=None):
        """
        call first action in the actions() list
        """
        if self.actions():
            return self.actions()[0][0](arg=arg, menuw=menuw)


    def eventhandler(self, event, menuw=None):
        """
        simple eventhandler for an item
        """
        if not menuw:
            menuw = self.menuw

        for p in self.eventhandler_plugins:
            if p(event, self, menuw):
                return True

        # give the event to the next eventhandler in the list
        if self.parent:
            return self.parent.eventhandler(event, menuw)
        else:
            if event in (STOP, PLAY_END, USER_END) and menuw:
                if menuw.visible:
                    menuw.refresh()
                else:
                    menuw.show()
                return True

        return False


    def plugin_eventhandler(self, event, menuw=None):
        """
        eventhandler for special plug-ins for this item
        """
        print 'DJW:plugin_eventhandler(event=%s, menuw=%r)' % (event, menuw)
        if not hasattr(self, '__plugin_eventhandler__'):
            self.__plugin_eventhandler__ = []
            for p in plugin.get('item') + plugin.get('item_%s' % self.type):
                if hasattr(p, 'eventhandler'):
                    self.__plugin_eventhandler__.append(p.eventhandler)
        for e in self.__plugin_eventhandler__:
            if e(self, event, menuw):
                return True
        return False


    def __getitem__(self, attr):
        """
        return the specific attribute
        """
        if attr == 'length':
            try:
                length = int(self.info['length'])
            except ValueError:
                return self.info['length']
            except:
                try:
                    length = int(self.length)
                except:
                    return ''
            if length == 0:
                return ''
            if length / 3600:
                return '%d:%02d:%02d' % ( length / 3600, (length % 3600) / 60, length % 60)
            else:
                return '%d:%02d' % (length / 60, length % 60)

        if attr == 'length:min':
            try:
                length = int(self.info['length'])
            except ValueError:
                return self.info['length']
            except:
                try:
                    length = int(self.length)
                except:
                    return ''
            if length == 0:
                return ''
            return '%d min' % (length / 60)

        if attr[:7] == 'parent(' and attr[-1] == ')' and self.parent:
            return self.parent[attr[7:-1]]

        if attr[:4] == 'len(' and attr[-1] == ')':
            r = None
            if self.info.has_key(attr[4:-1]):
                r = self.info[attr[4:-1]]

            if (r == None or r == '') and hasattr(self, attr[4:-1]):
                r = getattr(self,attr[4:-1])
            if r != None:
                return len(r)
            return 0

        else:
            r = None
            if self.info and self.info.has_key(attr):
                r = self.info[attr]
            if (r == None or r == '') and hasattr(self, attr):
                r = getattr(self,attr)
            if r != None:
                return r
            if hasattr(self, 'autovars'):
                for var, val in self.autovars:
                    if var == attr:
                        return val
        return ''


    def getattr(self, attr):
        """
        wrapper for __getitem__ to return the attribute as string or
        an empty string if the value is 'None'
        """
        if attr[:4] == 'len(' and attr[-1] == ')':
            return self.__getitem__(attr)
        else:
            if self and self.__getitem__:
                r = self.__getitem__(attr)
                return Unicode(r)
            return attr
