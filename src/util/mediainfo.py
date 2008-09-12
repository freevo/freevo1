# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# media information for storage/parsing
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


import os, stat
import sys
import copy
from pprint import pformat

import kaa.metadata as mmpython
import kaa.metadata

import config
import util

class FileOutdatedException(Exception):
    pass


class Cache:
    """
    Class to cache objects
    """
    def __init__(self, filename):
        self.filename = filename

        self.current_objects    = {}
        self.current_cachefile  = None
        self.current_cachedir   = None
        self.cache_modified     = False
        self.uncachable_keys    = {}

        # file database
        self.all_directories  = {}


    def __get_filename__(self, dirname):
        """
        return the cache filename for that directory/device
        """
        cachefile = vfs.getoverlay(dirname)
        if not os.path.exists(cachefile):
            os.makedirs(cachefile)
        return os.path.join(cachefile, self.filename)


    def __need_update__(self, dirname):
        """
        check if the cache needs an update
        """
        cachefile = self.__get_filename__(dirname)
        if os.path.isfile(cachefile) and \
               os.stat(cachefile)[stat.ST_MTIME] > os.stat(dirname)[stat.ST_MTIME]:
            return 0
        return 1


    def save_cache(self):
        """
        save a modified cache file
        """
        if self.cache_modified:
            _debug_('save cache %s' % self.current_cachefile, 2)
            util.save_pickle(self.current_objects, self.current_cachefile)
            self.cache_modified = False
            if config.MEDIAINFO_USE_MEMORY:
                self.all_directories[self.current_cachefile] = self.current_objects


    def load_cache(self, dirname):
        """
        load a new cachefile
        """
        if dirname == self.current_cachedir:
            return

        if self.cache_modified:
            self.save_cache()

        cachefile = self.__get_filename__(dirname)
        _debug_('load cache %s' % cachefile, 2)

        if config.MEDIAINFO_USE_MEMORY and self.all_directories.has_key(cachefile):
            self.current_objects = self.all_directories[cachefile]
        else:
            if os.path.isfile(cachefile):
                self.current_objects = util.read_pickle(cachefile)
                # maybe the cache file is broken and read_pickle returns None
                if not self.current_objects:
                    self.current_objects = {}
            else:
                self.current_objects = {}
            if config.MEDIAINFO_USE_MEMORY:
                self.all_directories[cachefile] = self.current_objects

        self.current_cachefile = cachefile
        self.current_cachedir  = dirname
        self.cache_modified    = False


    def check_cache(self, directory):
        """
        Return how many files in this directory are not in the cache. It's
        possible to guess how much time the update will need.
        """
        if not self.__need_update__(directory):
            return 0

        new = 0
        try:
            for filename in os.listdir(directory):
                fullname  = os.path.join(directory, filename)
                try:
                    info = self.find(filename, directory, fullname)
                except (KeyError, FileOutdatedException):
                    new += 1
                except (OSError, IOError):
                    pass
        except OSError, e:
            print 'Cannot list directory: %s' % (e)
        return new



    def cache_dir(self, directory, callback):
        """
        cache every file in the directory for future use
        """
        if not self.__need_update__(directory):
            return 0

        self.load_cache(directory)

        objects = {}
        for filename in os.listdir(directory):
            try:
                key       = filename
                fullname  = os.path.join(directory, filename)
                timestamp = os.stat(fullname)[stat.ST_MTIME]

                info = self.find(filename, directory, fullname)
            except KeyError:
                info = self.create(fullname)
                if callback:
                    callback()
            except FileOutdatedException:
                info = self.find(filename, directory, fullname, update_check=False)
                info = self.update(fullname, info)
                if callback:
                    callback()
            except (IOError, OSError):
                try:
                    timestamp
                except:
                    timestamp = 0
                info = {}

            objects[key] = (info, timestamp)

        self.current_objects   = objects
        self.cache_modified    = True
        self.save_cache()
        return objects


    def set(self, filename, dirname, fullname, info):
        """
        set a variable
        """
        if dirname != self.current_cachedir:
            self.load_cache(dirname)
        try:
            self.current_objects[filename] = (info, os.stat(fullname)[stat.ST_MTIME])
            self.cache_modified = True
        except OSError:
            # key, the file is gone now
            pass


    def get(self, filename, create=True):
        """
        get info about a file
        """
        fullname = filename

        # we know this are absolute paths, so we speed up
        # by not using the os.path functions.
        dirname  = filename[:filename.rfind('/')]
        filename = filename[filename.rfind('/')+1:]

        if dirname != self.current_cachedir:
            self.load_cache(dirname)

        if create:
            try:
                obj, t = self.current_objects[filename]
                if not self.update_needed(fullname, t):
                    return obj
                else:
                    info = self.update(fullname, obj)
            except KeyError:
                info = self.create(fullname)
            except (IOError, OSError):
                return {}
            self.set(filename, dirname, fullname, info)
            return info

        try:
            return self.current_objects[filename][0]
        except:
            return {}


    def find(self, filename, dirname, fullname, update_check=True):
        """
        Search the cache for information about that file. The functions
        returns that information. Because the information can be 'None',
        the function raises a KeyError if the cache has
        no or out-dated information.
        """
        if dirname != self.current_cachedir:
            self.load_cache(dirname)

        obj, t = self.current_objects[filename]
        if update_check:
            if self.update_needed(fullname, t):
                raise FileOutdatedException
        return obj



# ======================================================================


class MMCache(Cache):
    """
    cache for kaa metadata information
    """
    def __init__(self):
        Cache.__init__(self, 'mmpython.cache')
        self.uncachable_keys = [ 'thumbnail', 'url' ]


    def simplify(self, object, debug=0):
        """
        kaa metadata has huge objects to cache, we don't need them.
        This function simplifies them to be only string, intger, dict or
        list of one of those above. This makes the caching much faster

        kaa metadata has changed the definition of chapters and subtitles
        """
        ret = {}
        for k in object.keys():
            if debug:
                print 'object[%s] = %r' % (k, getattr(object, k))
            if not k in self.uncachable_keys and getattr(object,k) != None:
                value = getattr(object,k)
                if isstring(value):
                    value = Unicode(value.replace('\0', '').strip())
                if value:
                    ret[k] = value

        for k in  ( 'video', 'audio', 'chapters', 'subtitles', 'tracks' ):
            # if it's an AVCORE object, also simplify video and audio
            # lists to string and it
            if hasattr(object, k) and getattr(object, k):
                ret[k] = []
                for o in getattr(object, k):
                    ret[k].append(self.simplify(o))

        for k in ( 'mime', 'name', 'pos', 'title', 'comment', 'media', 'image' ):
            if hasattr(object, k) and getattr(object, k) != None:
                ret[k] = getattr(object, k)

        if debug:
            print ret
        return ret


    def create(self, filename):
        """
        create mmpython information about the given file
        """
        data = os.path.split(filename)
        if len(data) == 2:
            if data[1] == '.directory':
                filename = data[0]

        info = mmpython.parse(filename)

        if info:
            thumbnail = None
            if info.has_key('thumbnail'):
                thumbnail = info.thumbnail

            info = self.simplify(info)

            name = util.getname(filename)
            if name == name.upper() and info.has_key('type') and \
                   info['type'] in ('DVD', 'VCD'):
                name = util.getname(filename.lower())
            info['title:filename'] = name

            if info.has_key('video'):
                for video in info['video']:
                    for variable in ('width', 'height', 'length', 'aspect'):
                        if video.has_key(variable) and not \
                           (info.has_key(variable) and info[variable]):
                            info[variable] = video[variable]

            if thumbnail and config.IMAGE_USE_EXIF_THUMBNAIL and config.CACHE_IMAGES:
                util.cache_image(filename, thumbnail)
            elif config.CACHE_IMAGES and info.has_key('mime') and info['mime'] and \
                     info['mime'].startswith('image'):
                util.cache_image(filename)
            if info.has_key('media') and info['media'] == 'MEDIA_DIRECTORY':
                pass

            return info
        return {}


    def update_needed(self, filename, timestamp):
        """
        return true if the information needs an update
        """
        return timestamp < os.stat(filename)[stat.ST_MTIME]


    def update(self, filename, info):
        """
        update kaa metadata cache information
        """
        return self.create(filename)


# ======================================================================


class MetaCache(Cache):
    """
    cache for other freevo metadata
    """
    def __init__(self):
        Cache.__init__(self, 'freevo.cache')

    def save_cache(self):
        """
        Save a modified cache file. This version removed all entries having
        no information and removes to cachefile if no object has information
        anymore. This speeds up searching.
        """
        for key in copy.copy(self.current_objects):
            # delete all empty objects
            if not self.current_objects[key][0]:
                del self.current_objects[key]
                self.cache_modified = True
        if not self.current_objects:
            # delete cache file is no object has any infos
            if self.current_cachefile and os.path.isfile(self.current_cachefile):
                os.unlink(self.current_cachefile)
            self.cache_modified = False
            if config.MEDIAINFO_USE_MEMORY:
                self.all_directories[self.current_cachefile] = self.current_objects
            return
        # call save_file from 'Cache'
        Cache.save_cache(self)

    def create(self, filename):
        return {}

    def update_needed(self, filename, timestamp):
        return False

    def update(self, filename, info):
        return info


# ======================================================================

# info values in metacache that should not be returned
bad_info = [ '__various__', ]

# the two cache objects
mmpython_cache  = MMCache()
meta_cache      = MetaCache()

# ======================================================================

class Info:
    """
    Container for all kind of information. This information includes
    kaa.metadata parsed information and some user stored stuff.
    """
    def __init__(self, filename, discinfo, metadata):
        self.filename  = filename
        self.discinfo  = discinfo or {}
        self.metadata  = metadata or {}
        self.variables = {}
        self.disc      = False
        self.dicts = ( self.discinfo, self.variables, self.metadata )


    def __str__(self):
        l = [self.filename]
        if self.disc:
            if hasattr(self, 'disc'):
                l.append(self.disc)
            if hasattr(self, 'discinfo'):
                if hasattr(self.discinfo, 'id'):
                    l.append(self.discinfo.id)
                if hasattr(self.discinfo, 'type'):
                    l.append(self.discinfo.type)
        s = ', '.join(l)
        return s


    def __repr__(self):
        #if hasattr(self, 'filename') and self.filename:
        if self.filename:
            s = '%s: %r' % (self.filename, self.__class__)
        else:
            s = '%r' % (self.__class__)
        return s


    def __getitem__(self, key):
        """
        get the value of 'key'
        """
        result = ''
        if key == 'year':
            key = 'userdate'
        #DJW
        if key == 'userdate':
            import traceback
            #traceback.print_stack()
        #DJW
        for var in self.dicts:
            if var and var.has_key(key):
                val = var[key]
                if not var == self.metadata or not val in bad_info:
                    result = val
                if result is not None and result != '':
                    _debug_('__getitem__(key=%r)=%r' % (key, result), 3)
                    return result
        _debug_('__getitem__(key=%r)=%r' % (key, result), 3)
        return result


    def __setitem__(self, key, val):
        """
        set the value of 'key' to 'val'
        """
        self.variables[key] = val


    def has_key(self, key):
        """
        check if the object has a key 'key'
        """
        for var in self.dicts:
            if var and var.has_key(key):
                return True
        return False


    def store(self, key, value):
        """
        store the key/value in metadata and save the cache
        """
        self.metadata[key] = value
        if self.disc:
            self.metadata[key] = value
            util.save_pickle(self.metadata, self.filename)
            return True
        elif not self.filename:
            return False
        else:
            meta_cache.set(os.path.basename(self.filename), os.path.dirname(self.filename),
                self.filename, self.metadata)
            return True


    def delete(self, key):
        """
        delete the key in metadata and save the cache
        """
        if self.disc:
            if self.metadata.has_key(key):
                del self.metadata[key]
                util.save_pickle(self.metadata, self.filename)
            return True
        elif not self.filename:
            return False
        if self.metadata.has_key(key):
            del self.metadata[key]
            meta_cache.set(os.path.basename(self.filename), os.path.dirname(self.filename),
                self.filename, self.metadata)
            return True


    def set_variables(self, variables):
        """
        set personal user variables (not to storage) to 'variables'
        """
        self.variables = variables
        self.dicts     = ( self.discinfo, self.variables, self.metadata )


    def get_variables(self):
        """
        return the personal variables
        """
        return self.variables



# ======================================================================
# Interface to the rest of Freevo
# ======================================================================

def check_cache(dirname):
    """
    check the cache how many files need an update
    """
    return mmpython_cache.check_cache(dirname)


def cache_dir(dirname, callback=None):
    """
    cache the complete directory
    """
    mmpython_cache.cache_dir(dirname, callback)


class CacheStatus:
    def __init__(self, num_changes, txt):
        self.num_changes = num_changes
        self.txt         = txt
        self.pos         = 0
        self.callback()

    def callback(self):
        if self.num_changes != 0:
            progress = '%3d%%' % (self.pos * 100 / self.num_changes)
        else:
            progress = '??%%'
        print '\r%-70s %s' % (self.txt, progress),
        sys.__stdout__.flush()
        self.pos += 1


def cache_recursive(dirlist, verbose=False):
    """
    cache a list of directories recursive
    """
    all_dirs = []

    # create a list of all subdirs
    for dir in dirlist:
        for dirname in util.get_subdirs_recursively(dir):
            if not dirname in all_dirs and os.path.basename(dirname)[0] != '.':
                all_dirs.append(dirname)
        if not dir in all_dirs:
            all_dirs.append(dir)

    # if verbose, remove all dirs that need no caching
    if verbose:
        for d in copy.copy(all_dirs):
            if not check_cache(d):
                all_dirs.remove(d)

    print '%s changes' % len(all_dirs)

    # cache all dirs
    for d in all_dirs:
        if verbose:
            dname = d
            if len(dname) > 55:
                dname = dname[:15] + ' [...] ' + dname[-35:]
            cache_status = CacheStatus(check_cache(d), '  %4d/%-4d %s' % \
                                       (all_dirs.index(d)+1, len(all_dirs), dname))
            cache_dir(d, cache_status.callback)
            print
        else:
            cache_dir(d)
    if all_dirs:
        print


def disc_info(media, force=False):
    """
    return kaa metadata disc information for the media
    """
    discinfo = mmpython.parse(media.devicename)
    if not discinfo.id:
        # bad disc, e.g. blank disc
        return {}

    cachedir  = os.path.join(config.OVERLAY_DIR, 'disc/metadata')
    cachefile = os.path.join(cachedir, discinfo.id + '.freevo')

    if os.path.isfile(cachefile):
        metainfo = util.read_pickle(cachefile)
    else:
        metainfo = {}

    if force or discinfo.mime == 'unknown/unknown' and not metainfo.has_key('disc_num_video'):
        media.mount()
        for type in ('video', 'audio', 'image'):
            items = getattr(config, '%s_SUFFIX' % type.upper())
            files = util.match_files_recursively(media.mountdir, items)
            metainfo['disc_num_%s' % type] = len(files)
        media.umount()
        util.save_pickle(metainfo, cachefile)

    info = Info(cachefile, discinfo, metainfo)
    info.disc = True
    return info


def get(filename):
    """
    return an Info object with all the information Freevo has about
    the filename
    """
    return Info(filename, mmpython_cache.get(filename), meta_cache.get(filename, create=False))


def get_dir(dirname):
    """
    return an Info object with all the information Freevo has about
    the directory
    """
    return Info(dirname, {}, meta_cache.get(dirname, create=False))


def set(filename, key, value):
    """
    set a variable (key) in the meta_cache to value and saves the cache
    """
    info      = meta_cache.get(filename)
    info[key] = value
    fullname  = filename
    dirname   = os.path.dirname(filename)
    filename  = os.path.basename(filename)
    meta_cache.set(filename, dirname, fullname, info)


def sync():
    """
    sync database to disc (force writing)
    """
    mmpython_cache.save_cache()
    meta_cache.save_cache()


def load_cache(dirname):
    """
    load the cache for dirname
    """
    mmpython_cache.load_cache(dirname)
    meta_cache.load_cache(dirname)


def del_cache():
    """
    delete all cache files because kaa metadata got updated
    """
    for f in util.recursefolders(config.OVERLAY_DIR,1,'mmpython.cache',1):
        os.unlink(f)
    for f in util.match_files(config.OVERLAY_DIR + '/disc/metadata', ['mmpython']):
        os.unlink(f)
    cachefile = os.path.join(config.FREEVO_CACHEDIR, 'mediainfo')
    util.save_pickle((mmpython.version.VERSION, 0, 0, 0), cachefile)


__last_status_check__ = 0

def check_cache_status():
    """
    check if cache got updated with helper while freevo is running
    """
    global __last_status_check__
    if rc.app():
        return
    try:
        cachefile = os.path.join(config.FREEVO_CACHEDIR, 'mediainfo')
        if os.stat(cachefile)[stat.ST_MTIME] <= __last_status_check__:
            return
        if not __last_status_check__:
            __last_status_check__ = os.stat(cachefile)[stat.ST_MTIME]
            return
    except:
        __last_status_check__ = 1
        return

    __last_status_check__ = os.stat(cachefile)[stat.ST_MTIME]
    open_cache_files = []

    for cache in mmpython_cache, meta_cache:
        # save current cache
        cache.save_cache()
        # delete all info about loaded objects
        cache.current_objects    = {}
        cache.current_cachefile  = None
        cache.current_cachedir   = None
        cache.cache_modified     = False

        # file database
        for d in cache.all_directories:
            if d and not os.path.dirname(vfs.normalize(d)) in open_cache_files:
                open_cache_files.append(os.path.dirname(vfs.normalize(d)))
        cache.all_directories  = {}

    # create ProgressBox for reloading
    from gui import ProgressBox
    box = ProgressBox(text=_('Reloading cache files, be patient...'), full=len(open_cache_files))
    box.show()

    # reload already open cache files
    for d in open_cache_files:
        load_cache(d)
        box.tick()
    box.destroy()


#
# setup kaa metadata
#

if config.DEBUG > 2:
    mmpython.factory.DEBUG = config.DEBUG
else:
    mmpython.factory.DEBUG = 0

mmpython.USE_NETWORK = config.SYS_USE_NETWORK
mmpython.cdrom.CREATE_MD5_ID = config.MMPYTHON_CREATE_MD5_ID



# some checking when starting Freevo
if __freevo_app__ == 'main':
    try:
        import kaa.metadata.version
        import time

        cachefile = os.path.join(config.FREEVO_CACHEDIR, 'mediainfo')
        info = util.read_pickle(cachefile)
        if not info:
            print
            print 'Error: can\'t detect last cache rebuild'
            print 'Please run \'freevo cache\''
            print
            del_cache()
        else:
            if len(info) == 3:
                mmchanged, part_update, complete_update = info
                freevo_changed = 0
            else:
                mmchanged, freevo_changed, part_update, complete_update = info
            # let's warn about some updates
            if freevo_changed == 0:
                print
                print 'Please run \'freevo cache\''
                print
            elif freevo_changed < 3:
                print
                print 'Warning: Freevo cache helper/information updated.'
                print 'Please rerun \'freevo cache\' to speed up Freevo'
                print
                del_cache()

            elif kaa.metadata.version.VERSION > mmchanged:
                print
                print 'Warning: kaa metadata as changed.'
                print 'Please rerun \'freevo cache\' to get the latest updates'
                print
                del_cache()

            elif (int(time.time()) - part_update) / (3600 * 24) > 7:
                print
                print 'Warning: cache is older than 7 days'
                print 'Running \'freevo cache\' is recommended.'
                print
    except:
        print
        print 'Error: unable to read kaa metadata version information'
        print 'Please update kaa.metadata to the latest release or if you use'
        print 'Freevo svn versions, please also use kaa.metadata svn.'
        print
        print 'Some functions in Freevo may not work or even crash!'
        print
        print

    import rc
    rc.register(check_cache_status, True, 100)
