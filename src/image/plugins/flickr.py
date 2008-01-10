# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for download and watch pictures of flickr
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    You need to install python-json from http://sourceforge.net/projects/json-py/
#    You also need a FLICKR KEY API from http://www.flickr.com/services/api/keys/
#
#    To activate, put the following line in local_conf.py:
#       plugin.activate('image.flickr')
#       FLICKR_PICTURES = [
#           ('id1', 'description1'),
#           ('id2', 'description2'),
#           ...
#       ]
#       FLICKR_DIR = '/tmp/'
#       FLICKR_KEY = 'your flickr key'
#       FLICKR_LIMIT = 20
#
# ToDo:
#
# -----------------------------------------------------------------------
#
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

__author__           = 'Alberto González Rodríguez'
__author_email__     = 'alberto@pesadilla.org'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '0.1b'


import os
import kaa.imlib2
import plugin
import gdata.service
import urllib
import re
import traceback
import menu
import config
import string, os, subprocess
import json
import tempfile
import image.viewer
from image.imageitem import ImageItem
from subprocess import Popen
from item import Item
from gui.PopupBox import PopupBox

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    try:
        import cElementTree as ElementTree
    except ImportError:
        from elementtree import ElementTree


class PluginInterface(plugin.MainMenuPlugin):
    """
    Watch image of flickr

    You need to install:
    U{python-json <http://sourceforge.net/projects/json-py/>}
    U{FLICKR KEY API <http://www.flickr.com/services/api/keys/>}

    Activate:
    | plugin.activate('image.flickr')

    Config:
    id likes "11378227@N06"
    | FLICKR_PICTURES = [
    |   ("id1", "description1"),
    |   ("id2", "description2"),
    |    ...
    | ]
    | FLICKR_DIR = "/tmp/"
    | FLICKR_KEY = "your flickr key"
    | FLICKR_LIMIT = 20
    """
    def __init__(self):
        if not config.USE_NETWORK:
            self.reason = 'USE_NETWORK not enabled'
            return
        if not config.FLICKR_PICTURES:
            self.reason = 'FLICKR_PICTURES not defined'
            return
        if not config.FLICKR_KEY:
            self.reason = 'FLICKR_KEY not defined'
            return
        if not config.FLICKR_DIR:
            config.FLICKR_DIR = "/tmp/"

        if not os.path.isdir(config.FLICKR_DIR):
            os.mkdir(config.FLICKR_DIR, stat.S_IMODE(os.stat(config.FREEVO_CACHEDIR)[stat.ST_MODE]))

        plugin.MainMenuPlugin.__init__(self)

    def config(self):
        """returns the config variables used by this plugin"""
        return [
            ('FLICKR_PICTURES', None, 'id and description to get pictures'),
            ('FLICKR_DIR', config.FREEVO_CACHEDIR + '/flickr', 'directory to save flickr pictures'),
            ('FLICKR_KEY', None, 'Your flickr key api to access www.flickr.com'),
            ('FLICKR_LIMIT', 20, 'Max number of pictures to show'),
        ]

    def items(self, parent):
        return [ FlickImage(parent) ]

class FlickImage(Item):
    """Main Class"""

    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='image')
        self.name = _('Flickr pictures')
        self.title = _('Flickr pictures')
        self.type = 'flickr'
        self.info = { 'name' : 'Flickr', 'description' : 'Flickr pictures', 'title' : 'Flickr' }

    # Only one action, return user list
    def actions(self):
        """Only one action, return user list"""
        return [ (self.userlist, 'Flickr pictures') ]

    def userlist(self, arg=None, menuw=None):
        """Menu for choose user"""
        users = []
        for id,description in config.FLICKR_PICTURES:
            users.append(menu.MenuItem(description, self.imagelist, (id, description)))
        menuw.pushmenu(menu.Menu(_("Choose please"), users))

    def imagelist(self, arg=None, menuw=None):
        """Menu for choose image"""
        items = image_list(self, _("Retrieving image list"), arg[0])
        menuw.pushmenu(menu.Menu(_('Images available'), items))

    # Save in file and watch it
    def showimage(self, arg=None, menuw=None):
        file = config.FLICKR_DIR + "/" + arg[2].replace("-","_") + ".jpg"
        if not os.path.exists(file):
            box = PopupBox(_("Downloading picture \"") + arg[0] + '"', width=600)
            box.show()
            urllib.urlretrieve(arg[1],file)
            box.destroy()
        imgitem = ImageItem(file, self, arg[0])
        imgitem.menuw=menuw
        imgitem.view(menuw=menuw)
        #imagen = image.viewer.ImageViewer()
        #image.viewer.ImageViewer.view(imagen,imgitem)

def image_list(parent, title, user):
    """Get the image list for a specific user"""
    items = []
    web = 'http://www.flickr.com/services/rest/?method=flickr.people.getPublicPhotos&user_id=' + user + '&format=json&api_key=' + config.FLICKR_KEY + '&per_page=' + str(config.FLICKR_LIMIT) + '&page=1&extras=original_format'
    url=urllib.urlopen(web)
    flickr=url.read()
    flickr=flickr.replace("jsonFlickrApi(","");
    data = json.read(flickr[:-1])
    for foto in data['photos']['photo']:
            #items.append(ImageItem(y[1],parent,foto["title"]))

        mi = menu.MenuItem(foto["title"], parent.showimage, 0)
        mi.arg = (foto["title"],"http://farm3.static.flickr.com/" + foto["server"] + "/" + foto["id"] + "_" + foto["originalsecret"] +  "_o.jpg",foto["id"])
        imagen = "http://farm3.static.flickr.com/" + foto["server"] + "/" + foto["id"] + "_" + foto["secret"] +  "_m.jpg"
        file = config.FLICKR_DIR + "/" + foto["id"].replace("-","_") + "_t.jpg"
        if not os.path.exists(file):
            box = PopupBox(_("Downloading thumbnail for picture \"") + foto["title"] + '"', width=800)
            box.show()
            urllib.urlretrieve(imagen,file)
            box.destroy()
        mi.image = file
        items.append(mi)
    return items
