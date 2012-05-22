# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Freevo Archive file (zip, tar and rar) handling
# -----------------------------------------------------------------------
# $Id$
#
# Notes:  To use RAR file handling you must install both 'unrar' utility 
#         and python rar module. This plugin has been tested with version 
#         2.5 of python rarfile. It can be downloaded from:
#         http://pypi.python.org/pypi/rarfile/
#         This plugin is very useful to read the Comics in the 'cbz/cbr'
#         format. There is nothing special about those files besides the fact
#         that they are packaged with RAR or ZIP and renamed accordingly
#         to allow Comic Book readers like CDisplay or Comix Rack to associate
#         file extensions. Well, now Freevo got a Comic Book Reader and it 
#         works well too but this plugin is more than just that. It'll handle
#         archives with music albums, video files or any photo collection
#         and display the content if it was an ordinary directory/folder.
#         It does that by extracting files within the archive to temp direcory 
#         on your system. When Freevo exits or the object goes out of scope
#         the files created in the temp directory will be deleted.
#
# Todo:   Add listing of the archive content and extraction of just one item
#         In-memory file extraction, much faster but needs a lot of RAM and 
#         some major changes in Freevo.
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

__author__           = 'Maciej Urbaniak'
__author_email__     = 'maciej@urbaniak.org'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '$Revision$'
__license__          = 'GPL'


import logging
logger = logging.getLogger("freevo.plugins.archive")
 
import os
import stat
import copy
import shutil
from shutil import Error as ShutilError
import tempfile
import re

ZIP_SUFFIX = [ 'zip', 'cbz' ]
TAR_SUFFIX = [ 'tar', 'gz', 'tgz', 'bz2', 'tbz', 'tbz2', 'tb2' ]
RAR_SUFFIX = [ 'rar', 'cbr' ]

import zipfile
from zipfile import ZipInfo, ZipFile, BadZipfile as ZipError

ZIP_A_NORMAL = 0x00   
ZIP_A_RDONLY = 0x01   
ZIP_A_HIDDEN = 0x02   
ZIP_A_SYSTEM = 0x04   
ZIP_A_SUBDIR = 0x10   
ZIP_A_ARCH   = 0x20

import tarfile
from tarfile import TarInfo, TarFile

try:
    import rarfile
    from rarfile import RarFile, RarInfo, Error as RarError
    ARCHIVE_RAR_AVAILABLE = True
    ARCHIVE_SUFFIX = ZIP_SUFFIX + TAR_SUFFIX + RAR_SUFFIX
except:
    logger.error(_('You need python rar module installed. Also, make sure you have \'unrar\' utility installed'))
    ARCHIVE_RAR_AVAILABLE = False
    ARCHIVE_SUFFIX = ZIP_SUFFIX + TAR_SUFFIX

import config
import util

import menu
import skin
import plugin
import osd

from directory import DirItem, CacheProgressDialog
from util import vfs 


class PluginInterface(plugin.MimetypePlugin):
    """
    class to handle archive files, it'll extract the archive to the tmp dir
    thus making it a real dir item in the tree
    """
    def __init__(self):
        plugin.MimetypePlugin.__init__(self)
        self.display_type = [ 'video', 'audio', 'image' ]
        self.archives     = []


    def get(self, parent, files):
        """
        return a list of items based on the files
        """
        logger.log(9, '%s.get(parent=%r, files=%r)' % (self.__class__, parent, files))

        temp    = False
        cleanup = True
        items   = []
        
        # get the list of fxd files
        archives = util.find_matches(files, config.ARCHIVE_SUFFIX)

        # sort all files to make sure that we have them in sequence
        archives.sort(lambda l, o: cmp(l.upper(), o.upper()))

        for file in archives:
            if is_archive(file):
                # check if the extracted files should be deleted upon the exit/shutdown
                # This will always be done for System's temp directory though, regardless of 
                # the ARCHIVE_DELETE_ON_SHUTDOWN setting.
                if parent and parent.type == 'dir':
                    if hasattr(parent, 'ARCHIVE_DELETE_ON_SHUTDOWN') and not parent.ARCHIVE_DELETE_ON_SHUTDOWN:
                        cleanup = False
                        
                    if hasattr(parent, 'ARCHIVE_USE_SYSTEM_TEMP_DIR') and parent.ARCHIVE_USE_SYSTEM_TEMP_DIR:
                        cleanup = temp = True

                a = ArchiveItem(file, parent, display_type=parent.display_type, use_temp=temp, cleanup=cleanup)
                items.append(a)

        logger.debug('Found %d archive files', len(items)) 
        self.archives.extend(items)

        return items
        

    def shutdown(self):
        """
        called when shutting down the system
        """
        for i in range(len(self.archives)):
            self.archives[i].shutdown()


    def suffix(self):
        """
        return the list of suffixes this class handles
        """
        return config.ARCHIVE_SUFFIX
        
        
    def dirconfig(self, diritem):
        """
        adds configure variables to the directory
        """
        return [
            ('ARCHIVE_DELETE_ON_SHUTDOWN', _('Delete extracted Items on Shutdown '),
            _('Delete all extracted items on Freevo shutdown.'),
            True),
            ('ARCHIVE_USE_SYSTEM_TEMP_DIR', _('Use System\'s Temp Directory for extraction '),
            _('Use System\'s temp directory for extraction. Default is to use OVERLAY_DIR'),
            False)
        ]
       
        
    def config(self):
        """
        config is called automatically, for default settings run:
        freevo plugins -i archive
        """
        return [
                ('ARCHIVE_SUFFIX', ARCHIVE_SUFFIX, 'Supported Suffixes'),
            ] 
        

class ArchiveItem(DirItem):
    """
    class for handling archives
    """
    def __init__(self, directory, parent, name='', display_type=None, add_args=None, create_metainfo=True, use_temp=False, cleanup=True):
        
        logger.log(9, '%s.__init__(directory=%r, parent=%r, name=%r, display_type=%r, add_args=%r, create_metainfo=%r, use_temp=%r, cleanup=%r)', 
            self.__class__, directory, parent, name, display_type, add_args, create_metainfo, use_temp, cleanup)

        self.archive = os.path.abspath(directory)
        self.cleanup = cleanup
        self.valid   = False

        fname = os.path.splitext(os.path.basename(self.archive))[0]

        # create the tmp directory that we will extract the content of the archive to
        if use_temp:
            dir = os.path.join(tempfile.gettempdir(), fname)
        else:
            dir = vfs.getoverlay(self.archive)

        try:
            if not os.path.exists(dir):
                os.makedirs(dir)
        except (OSError) as exc:
            logger.error('OS Error %s creating dir %s, skipping this archive...', exc, dir) 
            return

        self.valid = True
        self.cover = self.set_cover_image(dir)

        # now we substitute the original dir/file name with the tmp dir location
        DirItem.__init__(self, dir, parent=parent, name=fname, display_type=display_type)


    def __del__(self):
        """
        class' destructor
        """
        logger.log(9, '%s.__del__()', self.__class__)
        self.shutdown()


    def shutdown(self):
        """
        here we delete the temp dir
        """
        logger.log(9, 'shutdown()')
        if self.valid and self.cleanup and os.path.exists(self.dir):
            shutil.rmtree(self.dir)


    def set_cover_image(self, dir):
        """
        we search for images within the archive, sort the result and get the first
        that matches and extract it to the tmp directory
        """
        logger.log(9, 'set_cover_image(dir=%r)', dir)
        cover = util.getimage(os.path.join(dir, 'cover'))

        if cover:
            # nothing to do, image already exist
            logger.debug('Nothing to do, archive cover already exist, skipping...') 
            return cover

        files  = []
        images = []

        try:        
            if zipfile.is_zipfile(self.archive):
                archive = zipfile.ZipFile(self.archive, 'r')
                files   = archive.namelist()

            elif tarfile.is_tarfile(self.archive):
                archive = tarfile.open(self.archive, 'r')
                files   = archive.getnames()

            elif ARCHIVE_RAR_AVAILABLE and rarfile.is_rarfile(self.archive):
                archive = rarfile.RarFile(self.archive, 'r')
                files   = archive.namelist()

        except (ZipError, RarError, TarError) as exc:
            logger.warning('Archive %s error: %s', self.archive, exc)
            self.valid = False
            return None

        if len(files):
            # get the image plugin matches on image files stored in the archive
            logger.debug('Found %d items in the archive %s', len(files), self.archive)
            for p in plugin.mimetype('image'):
                logger.debug('Found mime plugin for type \'image\', querying now...') 
                images.extend(util.find_matches(files, p.suffix()))
                logger.debug('Plugin reports %d images matches the suffix rule', len(images))
                
            if len(images):
                logger.debug('Found %d images in the archive %s', len(images), self.archive) 
                excl = re.compile('cover')
                for image in images:
                    if re.search(excl, image):
                        # there is a cover image in the archive already
                        logger.debug('Found cover image %s in the archive', images[0])
                        try:
                            archive.extract(image, dir)
                            logger.debug('Cover image %s extracted to %s', image, dir)
                            return os.path.join(dir, image)
                        except (ZipError, RarError, TarError) as exc:
                            # we tried to extract the cover but there is an error, 
                            # we will try another approach later on
                            logger.warning('Archive extract %s error: %s', self.archive, exc)
                            
                # no cover image in the archive, let's try to guess which one we could use as such
                # extract first image on the list, most likely it'll represet
                # a useful cover. This is definitely the case with cbz/cbr comics covers
                # first, we need sort all files to make sure that we have them in sequence
                images.sort(lambda l, o: cmp(l.upper(), o.upper()))

                # just for cleaner code
                image = images[0]
                logger.debug('Found suitable cover image %s in the archive', image)

                try:
                    archive.extract(image, dir)
                    ext = os.path.splitext(image)[1].lower().replace('jpeg', 'jpg')
                except (ZipError, RarError, TarError) as exc:
                    # we tried to extract the image but there was an error, we give up
                    logger.warning('Archive %s extract error: %s', self.archive, exc)
                    return None                    

                try:
                    # FIX ME It's more efficient to use symlinks but only on Windows. It's to complicated
                    # to detect the system type and then make a decision if use symlinks or copy (for now)
                    # maybe in the future ???
                    # os.symlink(os.path.join(dir, normalize(image), os.path.join(dir, ('cover' + ext)))
                    shutil.copy(os.path.join(dir, normalize(image)), os.path.join(dir, ('cover' + ext)))
                    logger.debug('Cover image %s, copied to %s', normalize(image), dir)
                except (OSError, ShutilError) as exc:
                    logger.warning('Error while getting cover image for archive %s, %s', self.archive, exc)
                    return None

                return os.path.join(dir, ('cover.' + ext))

        logger.debug('Unable to find a suitable cover image for archive %s', self.archive)
        return None


    def build(self, arg=None, menuw=None):
        """
        build the items for the archive
        """
        logger.log(9, 'build(arg=%r, menuw=%r)', arg, menuw)
        osd.get_singleton().busyicon.wait(config.OSD_BUSYICON_TIMER[0])
        archive = None
        
        try:
            if zipfile.is_zipfile(self.archive):
                archive = zipfile.ZipFile(self.archive, 'r')
                files   = archive.infolist()

            elif tarfile.is_tarfile(self.archive):
                archive = tarfile.open(self.archive, 'r')
                files   = archive.getmembers()
                
            elif ARCHIVE_RAR_AVAILABLE and rarfile.is_rarfile(self.archive):
                archive = rarfile.RarFile(self.archive, 'r')
                files   = archive.infolist()

            else:
                # fallback, nothing to do, not an archive
                super(DirItem, self).build(arg, menuw)
                return

        except (ZipError, RarError, TarError) as exc:
            _debug_('Archive %s error: %s' % (self.archive, exc), 1)
            self.valid = False
            osd.get_singleton().busyicon.stop()
            DirItem.build(self, arg, menuw)
            return

        # display the msg box
        pop = None
        to_extract = 0
        
        xfiles = []
        for f in files:
            logger.debug('testing for %s', os.path.join(self.dir, get_filename(f)))
            if not os.path.exists(os.path.join(self.dir, get_filename(f))):
                logger.debug('%s not found, will extract', os.path.join(self.dir, get_filename(f)))
                xfiles.append(f)
        
        if len(xfiles) > 8 and skin.active():
            pop = CacheProgressDialog(_('Extracting from archive, be patient...'), len(xfiles))
            pop.show()

        elif len(xfiles) > config.OSD_BUSYICON_TIMER[1]:
            # many files, just show the busy icon now
            osd.get_singleton().busyicon.wait(0)

        # extract one file at the time, bump the progress bar for each file extracted
        for f in xfiles:
            archive.extract(f, self.dir)
            if pop:
                pop.processed_file()
        
        # get rid of the msg box
        if pop:
            pop.hide()

        # stop the timer. If the icons is drawn, it will stay there
        # until the osd is redrawn, if not, we don't need it to pop
        # up the next milliseconds
        osd.get_singleton().busyicon.stop()

        exclude = ''
        
        if self.cover:
            # we do not want to include the cover img we just created
            # we store original config.IMAGE_EXCLUDE first, then set it to cover
            exclude = config.IMAGE_EXCLUDE
            config.IMAGE_EXCLUDE = ['cover']
        
        # now we let the base class handle the tmp directory
        DirItem.build(self, arg, menuw)
        
        if self.cover:
            # and now we restore original cover.IMAGE_RESTORE
            config.IMAGE_EXCLUDE = exclude
                
        
    # ======================================================================
    # metainfo
    # ======================================================================
    def create_metainfo(self):
        """
        create some metainfo for the archive
        """
        logger.log(9, 'create_metainfo()')

        display_type = self.display_type
        name = display_type or 'all'

        # check autovars
        for var, val in self.autovars:
            if var == 'num_%s_timestamp' % name:
                break
        else:
            self.autovars += [ ('num_%s_timestamp' % name, 0), ('num_%s_items' % name, 0) ]

        try:
            timestamp = os.stat(self.dir)[stat.ST_MTIME]
        except OSError:
            return

        num_timestamp = self.info['num_%s_timestamp' % name]

        if not num_timestamp or num_timestamp < timestamp:
            logger.debug('Create metainfo for %s, display_type=%s', self.archive, self.display_type)

            if self.media:
                self.media.mount()

            num_dir_items  = 0
            num_play_items = 0
            files = []

            try:            
                if zipfile.is_zipfile(self.archive):
                    archive = zipfile.ZipFile(self.archive, 'r')
                    files   = archive.infolist()
                    names   = archive.namelist()

                elif tarfile.is_tarfile(self.archive):
                    archive = tarfile.open(self.archive, 'r')
                    files   = archive.getmembers()
                    names   = archive.getnames()

                elif ARCHIVE_RAR_AVAILABLE and rarfile.is_rarfile(self.archive):
                    archive = rarfile.RarFile(self.archive, 'r')
                    files   = archive.infolist()
                    names   = archive.namelist()

            except (ZipError, RarError, TarError) as exc:
               logger.warning('Archive %s error: %s', self.archive, exc)
               self.valid = False

            # play items and playlists
            for p in plugin.mimetype(display_type):
                num_play_items += p.count(self, names)

            # normal DirItems
            for file in files:
                if is_dir(file): num_dir_items += 1

            # store info
            self['num_dir_items'] = num_dir_items
            self['num_%s_items' % name] = num_play_items
            self['num_%s_timestamp' % name] = timestamp

            if self.media:
                self.media.umount()

# ======================================================================
def is_archive(filename):
    """
    test if file is a valid archive (zip, tar or rar)
    """
    return tarfile.is_tarfile(filename) or \
           zipfile.is_zipfile(filename) or \
           (ARCHIVE_RAR_AVAILABLE and rarfile.is_rarfile(filename))


def is_dir(fileinfo):
    """
    test if file in the archive is a directory
    """
    if isinstance(fileinfo, ZipInfo):
        # return fileinfo.filename.endswith('/'):
        return (fileinfo.external_attr & ZIP_A_SUBDIR)
    return fileinfo.isdir()    

  
def get_filename(fileinfo):
    """
    get archive member's filename
    """
    if isinstance(fileinfo, TarInfo):
        return normalize(fileinfo.name)
    return normalize(fileinfo.filename)
    

def normalize(filename):
    """
    normalizes filename
    just in case this comes from Windows env and contains backslashes instead of fwdslashes
    """
    return filename.replace('\\', '/')