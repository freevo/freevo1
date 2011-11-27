# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Delete old cache files and update the cache
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
Delete old cache files and update the cache
"""
import logging
logger = logging.getLogger("freevo.helpers.cache")

import sys
import os
from stat import *
import time
import copy
import traceback
import pprint
from optparse import Option, OptionValueError, OptionParser, IndentedHelpFormatter

import config
import util
import util.mediainfo
import plugin
import directory
import playlist
import fxditem

# use this number to keep track of changes in
# this helper. Check this against util/mediainfo
VERSION = 3

def checking(msg):
    str = '.' * 60
    str = msg + str[len(msg):]
    return str


def delete_old_files_1():
    """
    delete old files from previous versions of freevo which are not
    needed anymore
    """
    #TODO Add WWW_LINK_CACHE and WWW_IMAGE_CACNE

    print checking('deleting old cache files from older freevo version'),
    sys.__stdout__.flush()
    del_list = []

    #for name in ('image-viewer-thumb.jpg', 'thumbnails', 'audio', 'mmpython', 'disc', 'image_cache', 'link_cache'):
    for name in ('image-viewer-thumb.jpg', 'thumbnails', 'audio', 'mmpython', 'disc'):
        if os.path.exists(os.path.join(config.FREEVO_CACHEDIR, name)):
            del_list.append(os.path.join(config.FREEVO_CACHEDIR, name))

    del_list += util.recursefolders(config.OVERLAY_DIR, 1, 'mmpython', 1)
    del_list += util.match_files(os.path.join(config.OVERLAY_DIR, 'disc'), ['mmpython', 'freevo'])

    for file in util.match_files_recursively(config.OVERLAY_DIR, ['png']):
        if file.endswith('.fvt.png'):
            del_list.append(file)

    for f in del_list:
        if os.path.isdir(f):
            util.rmrf(f)
        else:
            os.unlink(f)
    print 'deleted %s file%s' % (len(del_list), len(del_list) != 1 and 's' or '')


def delete_old_files_2():
    """
    delete cachfiles/entries for files which don't exists anymore
    """
    print checking('deleting old web-server thumbnails'),
    sys.__stdout__.flush()
    num = 0
    for file in util.match_files_recursively(vfs.www_image_cachedir(), config.IMAGE_SUFFIX):
        if not vfs.isfile(file[len(vfs.www_image_cachedir()):file.rindex('.')]):
            os.unlink(file)
            num += 1
    print 'deleted %s file%s' % (num, num != 1 and 's' or '')

    print checking('deleting old cache files'),
    sys.__stdout__.flush()
    num = 0
    for file in util.match_files_recursively(config.OVERLAY_DIR, ['raw']):
        if file.startswith(os.path.join(config.OVERLAY_DIR, 'disc')):
            continue
        if not vfs.isfile(file[len(config.OVERLAY_DIR):-4]):
            os.unlink(file)
            num += 1
    print 'deleted %s file%s' % (num, num != 1 and 's' or '')

    print checking('deleting cache for directories not existing anymore'),
    subdirs = util.get_subdirs_recursively(config.OVERLAY_DIR)
    subdirs.reverse()
    for file in subdirs:
        if not os.path.isdir(file[len(config.OVERLAY_DIR):]) and not \
                file.startswith(os.path.join(config.OVERLAY_DIR, 'disc')):
            for metafile in ('cover.png', 'cover.png.raw', 'cover.jpg', 'cover.jpg.raw', 'mmpython.cache',
                    'freevo.cache'):
                if os.path.isfile(os.path.join(file, metafile)):
                    os.unlink(os.path.join(file, metafile))
            if not os.listdir(file):
                os.rmdir(file)
    print 'done'

    print checking('deleting old entries in meta-info'),
    sys.__stdout__.flush()
    for filename in util.recursefolders(config.OVERLAY_DIR, 1, 'freevo.cache', 1):
        if filename.startswith(os.path.join(config.OVERLAY_DIR, 'disc')):
            continue
        sinfo = os.stat(filename)
        if not sinfo[ST_SIZE]:
            #print '%s is empty' % filename
            continue
        dirname = os.path.dirname(filename)[len(config.OVERLAY_DIR):]
        data    = util.read_pickle(filename)
        for key in copy.copy(data):
            if not os.path.exists(os.path.join(dirname, str(key))):
                del data[key]
        util.save_pickle(data, filename)
    print 'done'


def cache_directories(rebuild):
    """
    cache all directories with mmpython
    rebuild:
    0   no rebuild
    1   rebuild all files on disc
    2   like 1, but also delete disc info data
    """
    if rebuild:
        print checking('deleting cache files'),
        sys.__stdout__.flush()
        util.mediainfo.del_cache()
        print 'done'

    all_dirs = []
    print checking('checking mmpython cache files'),
    sys.__stdout__.flush()
    for d in config.VIDEO_ITEMS + config.AUDIO_ITEMS + config.IMAGE_ITEMS:
        if os.path.isdir(d[1]):
            all_dirs.append(d[1])
    util.mediainfo.cache_recursive(all_dirs, verbose=True)


def cache_thumbnails():
    """
    cache all image files by creating thumbnails
    """
    import cStringIO

    print checking('checking thumbnails'),
    sys.__stdout__.flush()

    files = []
    for d in config.VIDEO_ITEMS + config.AUDIO_ITEMS + config.IMAGE_ITEMS:
        try:
            d = d[1]
        except:
            pass
        if not os.path.isdir(d):
            continue
        files += util.match_files_recursively(d, config.IMAGE_SUFFIX) + \
                 util.match_files_recursively(vfs.getoverlay(d), config.IMAGE_SUFFIX)

    files = util.misc.unique(files)
    for filename in copy.copy(files):
        thumb = vfs.getoverlay(filename + '.raw')
        try:
            sinfo = os.stat(filename)
            if os.stat(thumb)[ST_MTIME] > sinfo[ST_MTIME]:
                files.remove(filename)
        except OSError:
            pass

        for bad_dir in ('.svn', '.xvpics', '.thumbnails', '.pics'):
            if filename.find(os.path.join(os.path.sep, bad_dir + '')) > 0:
                try:
                    files.remove(filename)
                except:
                    pass

    print '%s file%s' % (len(files), len(files) != 1 and 's' or '')

    for filename in files:
        fname = filename
        if len(fname) > 65:
            fname = fname[:20] + ' [...] ' + fname[-40:]
        print '  %4d/%-4d %s' % (files.index(filename)+1, len(files), Unicode(fname))

        util.cache_image(filename)

    if files:
        print


def cache_www_thumbnails(defaults):
    """
    cache all image files for web server by creating thumbnails
    """
    import cStringIO
    import stat

    print checking('checking web-server thumbnails'),
    print
    sys.__stdout__.flush()

    files = []
    for dirname in defaults['directory']:
        if defaults['dry_run']:
            print dirname
        if os.path.isdir(dirname):
            if defaults['recursive']:
                files += util.match_files_recursively(dirname, config.IMAGE_SUFFIX)
            else:
                files += util.match_files(dirname, config.IMAGE_SUFFIX)
        else:
            files += [ os.path.abspath(dirname) ]

    files = util.misc.unique(files)
    for filename in files[:]:
        thumb = util.www_image_path(filename, '.thumbs')
        try:
            sinfo = os.stat(filename)
            if os.stat(thumb)[ST_MTIME] > sinfo[ST_MTIME]:
                files.remove(filename)
        except OSError:
            pass

        for bad_dir in ('.svn', '.xvpics', '.thumbnails', '.pics'):
            if filename.find(os.path.join(os.path.sep, bad_dir + '')) > 0:
                try:
                    files.remove(filename)
                except:
                    pass

    print '%s file%s' % (len(files), len(files) != 1 and 's' or '')

    for filename in files:
        fname = filename
        if len(fname) > 65:
            fname = fname[:20] + ' [...] ' + fname[-40:]
        print '  %4d/%-4d %s' % (files.index(filename)+1, len(files), Unicode(fname))
        if defaults['dry_run']:
            continue

        util.www_thumb_create(filename)

    if files:
        print


def cache_cropdetect(defaults):
    """
    cache all video files for crop detection
    """
    import encodingcore
    import kaa.metadata
    # load the fxd part of video
    import fxditem
    import video.fxdhandler as fxdhandler
    from util import fxdparser
    from video import VideoItem

    global encjob

    def fxd_movie_read(fxd, node):
        logger.log( 9, 'fxd_movie_read=%r', fxd.user_data['filename'])
        fileinfo = fxd.user_data['fileinfo']
        for filename in fileinfo.files:
            try:
                if fxd.user_data['defaults']['dry_run']:
                    print filename,
                    continue
                if not os.path.exists(filename):
                    raise encodingcore.EncodingError('file %r does not exist' % filename)
                encjob = encodingcore.EncodingJob(None, None, None, None)
                encjob.source = filename
                fileext = os.path.splitext(filename)[1]
                if not fileext or fileext == '.iso':
                    data = kaa.metadata.parse(filename)
                    titlenum = 0
                    longest = 0
                    for track in data.tracks:
                        if track.length > longest:
                            longest = track.length
                            titlenum = track.trackno
                    if titlenum == 0:
                        raise encodingcore.EncodingError('longest track not found')
                    encjob.titlenum = titlenum
                encjob._identify()
                encjob._wait(5)
                if 'ID_LENGTH' not in encjob.id_info:
                    raise encodingcore.EncodingError('no length')
                encjob.length = float(encjob.id_info['ID_LENGTH'])
                if encjob.length < 5 or encjob.length > 5 * 60 * 60:
                    raise encodingcore.EncodingError('invalid length of %s' % (encjob.length))
                encjob._cropdetect()
                encjob._wait(10)
                fxd.user_data['encjob'] = encjob
                fxd.user_data['crop'] = encjob.crop
                #print '%r: crop=%s' % (fileinfo.files.fxd_file, encjob.crop)
            except encodingcore.EncodingError, why:
                print '%s' % why
            except Exception, why:
                print traceback.print_exc()


    def fxd_movie_write(fxd, node):
        logger.log( 9, 'fxd_movie_write')
        encjob = fxd.user_data['encjob']
        if encjob is None:
            #print 'encjob failed'
            return
        if encjob.crop is None:
            #print 'no crop result'
            return
        videos = fxd.get_children(node, 'video', 0)
        for video in videos:
            #print video.__dict__
            files = fxd.get_children(video, 'file', 0)
            for file in files:
                #print file.__dict__
                fxd.setattr(file, 'mplayer-options', '-vf crop=%s' % encjob.crop)


    plugin.register_callback('fxditem', ['video'], 'movie', fxdhandler.parse_movie)
    plugin.register_callback('fxditem', ['video'], 'disc-set', fxdhandler.parse_disc_set)

    print checking('checking cropdetect'),
    sys.__stdout__.flush()

    fxdfiles = []
    for dirname in defaults['directory']:
        if os.path.isdir(dirname):
            if defaults['recursive']:
                fxdfiles += util.match_files_recursively(dirname, fxditem.mimetype.suffix())
            else:
                fxdfiles += util.match_files(dirname, fxditem.mimetype.suffix())
        else:
            fxdfiles += [ os.path.abspath(dirname) ]

    fxdfiles.sort(lambda l, o: cmp(l.lower(), o.lower()))
    fxdfiles = util.misc.unique(fxdfiles)
    files = []
    for info in fxditem.mimetype.parse(None, fxdfiles, display_type='video'):
        if defaults['rebuild'] or (hasattr(info, 'mplayer_options') and not info.mplayer_options):
            files.append(info.files)

    for fileinfo in copy.copy(files):
        filename = fileinfo.fxd_file
        print
        print '  %4d/%-4d %s' % (files.index(fileinfo)+1, len(files), Unicode(os.path.basename(filename))),
        sys.__stdout__.flush()
        try:
            ctime = os.stat(filename)[ST_CTIME]
            mtime = os.stat(filename)[ST_MTIME]
            atime = os.stat(filename)[ST_ATIME]
            parser = fxdparser.FXD(filename)
            parser.set_handler('movie', fxd_movie_read)
            parser.set_handler('movie', fxd_movie_write, 'w', True)
            parser.user_data = {
                'defaults': defaults,
                'fileinfo' : fileinfo,
                'filename': filename,
                'encjob': None,
                'crop': None,
            }
            parser.parse()
            parser.save()
            if not defaults['dry_run']:
                print parser.user_data['crop'],
            parser = None
            sinfo = os.utime(filename, (atime, mtime))
        except encodingcore.EncodingError, why:
            print 'ERROR: "%s" failed: %s' % (filename, why)
        except Exception, why:
            print 'ERROR: "%s" failed: %s' % (filename, why)
            #traceback.print_exc()
    if len(files) > 0:
        print
    print 'done'


def create_metadata():
    """
    scan files and create metadata
    """
    import util.extendedmeta
    print checking('creating audio metadata'),
    sys.__stdout__.flush()
    for dir in config.AUDIO_ITEMS:
        if os.path.isdir(dir[1]):
            util.extendedmeta.AudioParser(dir[1], rescan=True)
    print 'done'

    print checking('creating playlist metadata'),
    sys.__stdout__.flush()
    pl  = []
    fxd = []
    for dir in config.AUDIO_ITEMS:
        if os.path.isdir(dir[1]):
            pl  += util.match_files_recursively(dir[1], playlist.mimetype.suffix())
            fxd += util.match_files_recursively(dir[1], fxditem.mimetype.suffix())
        elif isinstance(dir, list) or isinstance(dir, tuple):
            print
            print 'bad path: %s   ' % dir[1],
            sys.__stdout__.flush()
        elif util.match_suffix(dir, playlist.mimetype.suffix()):
            pl.append(dir)
        elif util.match_suffix(dir, fxditem.mimetype.suffix()):
            fxd.append(dir)
        elif util.match_suffix(dir[1], playlist.mimetype.suffix()):
            pl.append(dir[1])
        elif util.match_suffix(dir[1], fxditem.mimetype.suffix()):
            fxd.append(dir[1])


    try:
        items = playlist.mimetype.get(None, util.misc.unique(pl))

        # ignore fxd files for now, they can't store meta-info
        # for f in fxditem.mimetype.get(None, util.misc.unique(fxd)):
        #     if f.type == 'playlist':
        #         items.append(f)

        for i in items:
            util.extendedmeta.PlaylistParser(i)
    except:
        pass
    print 'done'

    print checking('checking database'),
    sys.__stdout__.flush()
    try:
        # The DB stuff
        import sqlite

        for dir in config.AUDIO_ITEMS:
            if os.path.isdir(dir[1]):
                util.extendedmeta.addPathDB(dir[1], dir[0], verbose=False)
        print 'done'
    except ImportError:
        print 'skipping'
        pass


    print checking('creating directory metadata'),
    sys.__stdout__.flush()

    subdirs = { 'all': [] }

    # get all subdirs for each type
    for type in activate_plugins:
        subdirs[type] = []
        for d in getattr(config, '%s_ITEMS' % type.upper()):
            try:
                d = d[1]
                if d == os.path.sep:
                    print 'ERROR: %s_ITEMS contains root directory, skipped.' % type
                    continue

            except:
                pass
            if not os.path.isdir(d):
                continue
            rec = util.get_subdirs_recursively(d)
            subdirs['all'] += rec
            subdirs[type]  += rec

    subdirs['all'] = util.misc.unique(subdirs['all'])
    subdirs['all'].sort(lambda l, o: cmp(l.upper(), o.upper()))

    # walk though each directory
    for s in subdirs['all']:
        if s.find(os.path.join(os.path.sep, '.')) > 0:
            continue

        # create the DirItems
        d = directory.DirItem(s, None)

        # rebuild meta-info
        d.create_metainfo()
        for type in activate_plugins:
            if subdirs.has_key(type) and s in subdirs[type]:
                d.display_type = type
                # scan again with display_type
                d.create_metainfo()

    print 'done'


def create_tv_pickle():
    print checking('caching xmltv database'),
    sys.__stdout__.flush()

    import tv.epg_xmltv
    tv.epg_xmltv.get_guide()
    print 'done'


def parse_options(defaults):
    """
    Parse command line options
    """
    formatter=IndentedHelpFormatter(indent_increment=2, max_help_position=32, width=100, short_first=0)
    parser = OptionParser(conflict_handler='resolve', formatter=formatter, usage="""

Freevo Cache helper to delete unused cache entries and to cache all files in
your data directories.

If the --rebuild option is given, Freevo will delete the cache first to rebuild
the cache from start. Caches from discs won't be affected

--www-thumbs [ --recursive ] [ --directory=DIR ] will generate image thumbnails

--video-thumbs [ --recursive ] [ --directory=DIR ] will generate video thumbnails

--cropdetect [ --recursive ] [ --directory=DIR ] will generate mplayer crop options

The directory option can be specified more than once, one per directory of file.

WARNING:

Caching needs a lot free space in OVERLAY_DIR. The space is also needed when
Freevo generates the files during run time. Image caching is the worst. So make
sure you have several hundred MB free!
""" + 'OVERLAY_DIR is set to %s' % config.OVERLAY_DIR, version='%prog 1.0')
    parser.add_option('-v', '--verbose', action='count', default=0,
        help='set the level of verbosity [default:%default]')
    parser.add_option('-n', '--dry-run', action='store_true', default=False,
        help='run through the actions but don\'t perform them [default:%default]')
    parser.add_option('--rebuild', action='store_true', default=False,
        help='rebuild the cache [default:%default]')
    parser.add_option('-w', '--www-thumbs', action='store_true', default=False,
        help='generate missing www thumbnails for this directory [default:%default]')
    parser.add_option('-t', '--video-thumbs', action='store_true', default=False,
        help='generate missing video thumbnails [default:%default]')
    parser.add_option('-c', '--cropdetect', action='store_true', default=False,
        help='generate missing mplayer crop options [default:%default]')
    parser.add_option('-r', '--recursive', action='store_true', default=False,
        help='generate recursively the cache [default:%default]')
    parser.add_option('-f', '--directory', action='append', default=None, metavar='DIR',
        help='path name, one per directory or file [default:%default]')
    return parser.parse_args()


def cache_video_thumbs(defaults):
    import util.videothumb
    print checking('creating video thumbnails'),
    print
    sys.__stdout__.flush()

    files = []
    for dirname in defaults['directory']:
        if defaults['dry_run']:
            print dirname
        if os.path.isdir(dirname):
            if defaults['recursive']:
                files += util.match_files_recursively(dirname, config.VIDEO_MPLAYER_SUFFIX)
            else:
                files += util.match_files(dirname, config.VIDEO_MPLAYER_SUFFIX)
        else:
            files += [ os.path.abspath(dirname) ]

    files = util.misc.unique(files)
    for filename in files[:]:
        print '  %4d/%-4d %s' % (files.index(filename)+1, len(files), Unicode(os.path.basename(filename)))
        if defaults['dry_run']:
            continue
        util.videothumb.snapshot(filename, update=False)
    print



if __name__ == "__main__":
    os.umask(config.UMASK)
    defaults = { }
    (opts, args) = parse_options(defaults)
    defaults.update(opts.__dict__)

    if opts.verbose:
        pprint.pprint(defaults)

    if (opts.cropdetect and opts.video_thumbs) or \
       (opts.cropdetect and opts.www_thumbs) or \
       (opts.video_thumbs and opts.www_thumbs):
        sys.exit('--video-thumbs, --www-thumbs and --cropdetect are mutually exclusive')

    if opts.cropdetect:
        if opts.directory is None:
            defaults['directory'] = []
            for item in [('TV Recordings', config.TV_RECORD_DIR)] + config.VIDEO_ITEMS:
                if isinstance(item, tuple):
                    name, dir = item
                    defaults['directory'].append(dir)
        cache_cropdetect(defaults)
        sys.exit(0)

    if opts.video_thumbs:
        if opts.directory is None:
            defaults['directory'] = []
            defaults['directory'].append(config.TV_RECORD_DIR)
        cache_video_thumbs(defaults)
        sys.exit(0)

    if opts.www_thumbs:
        if opts.directory is None:
            defaults['directory'] = []
            for item in config.IMAGE_ITEMS:
                if isinstance(item, tuple):
                    name, dir = item
                    defaults['directory'].append(dir)
        cache_www_thumbnails(defaults)
        sys.exit(0)

    print 'Freevo cache'
    print
    print 'Freevo will now generate a metadata cache for all your files and'
    print 'create thumbnails from images for faster access.'
    print

    # check for current cache information
    if opts.rebuild:
        rebuild = 1
    else:
        rebuild = 0

    try:
        import kaa.metadata.version

        info = None
        cachefile = os.path.join(config.FREEVO_CACHEDIR, 'mediainfo')
        if os.path.isfile(cachefile):
            info = util.read_pickle(cachefile)
        if not info:
            print
            print 'Unable to detect last complete rebuild, forcing rebuild'
            rebuild = 2
            complete_update = int(time.time())
        else:
            if len(info) == 3:
                mmchanged, part_update, complete_update = info
                freevo_changed = 0
            else:
                mmchanged, freevo_changed, part_update, complete_update = info

            # let's warn about some updates
            if freevo_changed < VERSION or kaa.metadata.version.VERSION > mmchanged:
                print 'Cache too old, forcing rebuild'
                rebuild = 2
                complete_update = int(time.time())

    except ImportError:
        print
        print 'Error: unable to read kaa.metadata version information'
        print 'Please update kaa.metadata to the latest release or if you use'
        print 'Freevo SVN versions, please also use kaa.metadata SVN.'
        print
        print 'Some functions in Freevo may not work or even crash!'
        print
        print

    start = time.clock()

    activate_plugins = []
    for type in ('video', 'audio', 'image', 'games'):
        if plugin.is_active(type):
            # activate all mime-type plugins
            plugin.init_special_plugin(type)
            activate_plugins.append(type)

    for type in 'VIDEO', 'AUDIO', 'IMAGE':
        for d in copy.copy(getattr(config, '%s_ITEMS' % type)):
            if not isstring(d):
                d = d[1]
            if d == os.path.sep:
                print 'ERROR: %s_ITEMS contains root directory, skipped.' % type
                setattr(config, '%s_ITEMS' % type, [])

    if os.path.isdir(os.path.join(config.FREEVO_CACHEDIR, 'playlists')):
        config.AUDIO_ITEMS.append(('Playlists', os.path.join(config.FREEVO_CACHEDIR, 'playlists')))
    delete_old_files_1()
    delete_old_files_2()

    # we have time here, don't use exif thumbnails
    config.IMAGE_USE_EXIF_THUMBNAIL = 0

    cache_directories(rebuild)
    if config.CACHE_IMAGES:
        cache_thumbnails()
    create_metadata()
    create_tv_pickle()

# close db
util.mediainfo.sync()

# save cache info
try:
    import kaa.metadata.version
    util.save_pickle((kaa.metadata.version.VERSION, VERSION, int(time.time()), complete_update), cachefile)
except ImportError:
    print 'WARNING: please update kaa.metadata'

print
print 'caching complete after %s seconds' % (time.clock() - start)
