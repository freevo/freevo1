# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# fxdarchive - a plugin to archive fxd movie files from a removable media
# -----------------------------------------------------------------------
# activate:
# plugin.activate('reminders', level=45)
# REMINDERS = [ ("cmd", "name", <wrap 0|N >, "string") ]
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2003 Krister Lagerstrom, et al.
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

__author__ = "Christian Lyra"
__version__ = "0.1"
__copyright__ = "Copyright (c) 2007 Christian Lyra"
__license__ = "GPL"
__doc__ = '''This plugins create a entry in the context menu of cd/dvd
to let you copy fxd files from cd/dvd to a configured directory on HD. So you can see
what you have on dvd without the need go from dvd to dvd. the plugin modify the fxd
inserting a media-id attribute, so when you select the fxd file freevo will ask you to
insert the right media.

To activate, put the following lines in local_conf.py:
plugin.activate('fxdarchive')
ARCHIVES = '/dir/to/archive'
'''


import os
import plugin
import config
import shutil
import time
import util.fileops
import util.fxdparser
from gui import PopupBox, AlertBox
import rc
import menu

class PluginInterface(plugin.ItemPlugin):
    """
    Plugin to archive fxd files

    Activate:
    plugin.activate('video.fxdarchive')
    ARCHIVES = '/where/files/should/go'

    This plugin creates additional entries in the context menu for cd/dvd
    for copy all fxd files to a configured directory.
    """

    def __init__(self):
        plugin.ItemPlugin.__init__(self)
        self.archives = config.ARCHIVES
        self.coverimg = None
        self.mediaid = None
        self.ismovie = False
        self.cwd = None
        self.nfiles = 0


    def config(self):
        ''' Defines local configuration variable that can be overridden in local_conf.py
        '''
        return [
            ('ARCHIVES', os.path.join(config.FREEVO_CACHEDIR, 'fxdarchive'), 'Path to archived fxd directory'),
        ]


    def actions(self, item):
        self.item = item
        ret = [ ]
        if hasattr(self.item, 'type') and self.item.type == 'dir' and hasattr(self.item.media, 'id'):
            #for name, to in self.archives:
            #   ret.append( (lambda **kwargs: self.copy_fxd(dst=to, **kwargs), _('Copy FXD files to %s') % name) )
            self.mediaid = item.media.id
            return [ (self.copy_fxd, _('Archive FXD files')) ]
        return []


    def copy_fxd(self, arg=None, menuw=None):
        '''
        Find all fxd files inside a given folder, and copy them to the configured
        destination folder
        '''
        self.item.media.mount()
        box = PopupBox(text=_('Finding and copying FXD files...'))
        box.show()
        time.sleep(1)
        fxds = util.fileops.match_files_recursively( self.item.dir , [ 'fxd' ])
        msg=''
        for i in fxds:
            _debug_('file: %r' % i)
            self.cwd = os.path.dirname(i)
            parser = util.fxdparser.FXD(i)
            parser.set_handler('movie', self.fxdparser)
            parser.set_handler('movie', self.fxdparsew, mode='w')
            parser.parse()
            if self.ismovie:
                parser.tree.filename= '%s/%s' % (self.archives, os.path.basename(parser.filename) )
                try:
                    parser.save()
                    self.nfiles += 1
                except:
                    print "Error while trying to write ", parser.tree.filename
                    msg = _("There was a error while trying to write the fxd file")
                if self.coverimg:
                    coverfrom = os.path.join(self.cwd, self.coverimg)
                    coverto = os.path.join(self.archives, self.coverimg)
                    try:
                        shutil.copy(coverfrom, coverto)
                        # is there a better way to do this?
                        os.chmod(coverto, 0644)
                    except:
                        print "Error while trying to copy %s to %s" % (coverfrom, coverto)
                        msg = _("But I couldn't copy a cover image file.")
            self.ismovie = False
        box.destroy()
        box = PopupBox(text=_('%d fxd files archived. %s') % (self.nfiles, msg))
        box.show()
        time.sleep(3)
        box.destroy()

        self.item.media.umount()

        #reset a few variables
        self.nfiles = 0
        msg = ''


    def fxdparser(self, fxd, node):
        '''
        Parse the fxd file, and discover the cover image file,
        also, discover if this is a movie fxd or not
        '''

        coverimg = fxd.childcontent(node, 'cover-img')
        if coverimg:
            self.coverimg = coverimg
        else:
            self.coverimg = None
        self.ismovie = True


    def fxdparsew(self, fxd, node):
        '''
        Change a few things inside the fxd file while writing it.
        add <cdrom>/path/ information and media-id attribute
        '''
        files = fxd.get_children(node, 'file', 0)
        for file in files:
            fxd.setcdata(file, '%s/%s' % (self.cwd, fxd.gettext(file)))
            fxd.setattr(file, 'media-id', self.mediaid)
