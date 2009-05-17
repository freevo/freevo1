# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# util/misc.py - Some Misc Utilities
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

import string
import glob
import os, sys
import string, re
import copy
import htmlentitydefs
from stat import *


# Configuration file. Determines where to look for AVI/MP3 files, etc
import config
from vfs import abspath as vfs_abspath


def uniquify_filename(filename,directory=None,extensions=None):
    """Returns a filename so that there is no other file by
    the same name in the directory (ignoring extensions); to achieve
    this, it alters the given 'filename' possibly adding a '(N)' snippet
    to the filename (before the extension) where N is a progressive
    integer.  The provided 'filename' should have an extension.
    If the provided filename is already unique, then it will be
    unaltered.
    If 'extensions' contains a list of extensions, then only files in
    the directory with those extensions are considered (note that the
    extensions must have a 'dot' in front). If 'filename' is not an
    absolute path, the directory is specified in 'directory'.
    Example usage: uniquify_filename('/sbin/mkfs')
    """
    assert type(extensions) == tuple or type(extensions) == list or \
        extensions == None
    if directory == None:
        directory, filename = os.path.split(filename)
    filename, ext = os.path.splitext(filename)
    N=0
    uniquifier = ''
    # check if the uniquification scheme is already part of this filename;
    # in case, strip it and use it as a base
    if filename[-1] == ')':
        j=string.rfind(filename,'(')
        if j>=0:
            try:
                N = int(filename[j+1:-1])
            except ValueError:
                j = None
            if j != None:
                filename = filename[:j]
                uniquifier = filename[j:]
    files = []
    for i in os.listdir(directory):
        a,b=os.path.splitext(i)
        if extensions == None or b in extensions:
            files.append(a)
    while (filename+uniquifier) in files:
        N = N + 1
        uniquifier = '(%d)' % N
    return directory+os.path.sep+filename+uniquifier+ext


# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52560
def unique(s):
    """Return a list of the elements in s, but without duplicates.

    For example, unique([1,2,3,1,2,3]) is some permutation of [1,2,3],
    unique("abcabc") some permutation of ["a", "b", "c"], and
    unique(([1, 2], [2, 3], [1, 2])) some permutation of
    [[2, 3], [1, 2]].

    For best speed, all sequence elements should be hashable.  Then
    unique() will usually work in linear time.

    If not possible, the sequence elements should enjoy a total
    ordering, and if list(s).sort() doesn't raise TypeError it's
    assumed that they do enjoy a total ordering.  Then unique() will
    usually work in O(N*log2(N)) time.

    If that's not possible either, the sequence elements must support
    equality-testing.  Then unique() will usually work in quadratic
    time.
    """

    n = len(s)
    if n == 0:
        return []

    # Try using a dict first, as that's the fastest and will usually
    # work.  If it doesn't work, it will usually fail quickly, so it
    # usually doesn't cost much to *try* it.  It requires that all the
    # sequence elements be hashable, and support equality comparison.
    u = {}
    try:
        for x in s:
            u[x] = 1
    except TypeError:
        del u  # move on to the next method
    else:
        return u.keys()

    # We can't hash all the elements.  Second fastest is to sort,
    # which brings the equal elements together; then duplicates are
    # easy to weed out in a single pass.
    # NOTE:  Python's list.sort() was designed to be efficient in the
    # presence of many duplicate elements.  This isn't true of all
    # sort functions in all languages or libraries, so this approach
    # is more effective in Python than it may be elsewhere.
    try:
        t = list(s)
        t.sort()
    except TypeError:
        del t  # move on to the next method
    else:
        assert n > 0
        last = t[0]
        lasti = i = 1
        while i < n:
            if t[i] != last:
                t[lasti] = last = t[i]
                lasti += 1
            i += 1
        return t[:lasti]

    # Brute force is all that's left.
    u = []
    for x in s:
        if x not in u:
            u.append(x)
    return u


# Helper function for the md5 routine; we don't want to
# write filenames that aren't in lower ascii so we uhm,
# hexify them.
def hexify(str):
    """
    return the string 'str' as hex string
    """
    hexStr = string.hexdigits
    r = ''
    for ch in str:
        i = ord(ch)
        r = r + hexStr[(i >> 4) & 0xF] + hexStr[i & 0xF]
    return r


def escape(sql):
    """
    Escape a SQL query in a manner suitable for sqlite. Also convert
    Unicode to normal string object.
    """
    if sql:
        sql = sql.replace('\'','\'\'')
        return String(sql)
    else:
        return 'null'



FILENAME_REGEXP = re.compile("^(.*?)_(.)(.*)$")

def getimage(base, default=None):
    """
    return the image base+'.png' or base+'.jpg' if one of them exists.
    If not return the default
    """
    for suffix in ('.png', '.jpg', '.gif'):
        image = vfs_abspath(base+suffix)
        if image:
            return image
    return default


def getname(file, skip_ext=True):
    """
    make a nicer display name from file
    """
    if len(file) < 2:
        return Unicode(file)

    # basename without ext
    if file.rfind('/') < file.rfind('.') and skip_ext:
        name = file[file.rfind('/')+1:file.rfind('.')]
    else:
        name = file[file.rfind('/')+1:]
    if not name:
        # Strange, it is a dot file, return the complete
        # filename, I don't know what to do here. This should
        # never happen
        return Unicode(file)
    name = name[0].upper() + name[1:]

    while file.find('_') > 0 and FILENAME_REGEXP.match(name):
        m = FILENAME_REGEXP.match(name)
        if m:
            name = m.group(1) + ' ' + m.group(2).upper() + m.group(3)
    if name.endswith('_'):
        name = name[:-1]
    return Unicode(name)


def killall(appname, sig=9):
    """
    kills all applications with the string <appname> in their commandline.

    The <sig> parameter indicates the signal to use.
    This implementation uses the /proc filesystem, it might be Linux-dependent.
    """
    unify_name = re.compile('[^A-Za-z0-9]').sub
    appname = unify_name('', appname)

    cmdline_filenames = glob.glob('/proc/[0-9]*/cmdline')

    for cmdline_filename in cmdline_filenames:

        try:
            fd = vfs.open(cmdline_filename)
            cmdline = fd.read()
            fd.close()
        except IOError:
            continue

        if unify_name('', cmdline).find(appname) != -1:
            # Found one, kill it
            pid = int(cmdline_filename.split('/')[2])
            if config.DEBUG:
                a = sig, pid, ' '.join(cmdline.split('\x00'))
                print 'killall: Sending signal %s to pid %s ("%s")' % a
            try:
                os.kill(pid, sig)
            except:
                pass
    return


def title_case(phrase):
    """
    Return a text string (i.e. from CDDB) with
    the case normalized into title case.
    This is because people frequently put in ugly
    information, and we can avoid it here'
    """

    s = ''
    for letter in phrase:
        if s and s[-1] == ' ' or s == '' or s[-1] == '-' or s[-1] == '.':
            s += string.upper(letter)
        elif letter == '_':
            s += ' '
        else:
            s += string.lower(letter)
    return s




def get_bookmarkfile(filename):
    myfile = vfs.basename(filename)
    myfile = config.FREEVO_CACHEDIR + "/" + myfile + '.bookmark'
    return myfile



def format_text(text):
    if not text:
        return None
    while len(text) and text[0] in (u' ', u'\t', u'\n'):
        text = text[1:]
    if not text:
        return None
    text = re.sub(u'\n[\t *]', u' ', text)
    while len(text) and text[-1] in (u' ', u'\t', u'\n'):
        text = text[:-1]
    return text


def list_usb_devices():
    devices = []
    fd = open('/proc/bus/usb/devices', 'r')
    for line in fd.readlines():
        if line[:2] == 'P:':
            devices.append('%s:%s' % (line[11:15], line[23:27]))
    fd.close()
    return devices


def is_usb_storage_device():
    fd = open('/proc/bus/usb/devices', 'r')
    for line in fd.readlines():
        if line.lower().find('storage') != -1:
            fd.close()
            return 0
    fd.close()
    return -1


def smartsort(x, y): # A compare function for use in list.sort()
    """
    Compares strings after stripping off 'The' and 'A' to be 'smarter'
    Also obviously ignores the full path when looking for 'The' and 'A'
    """
    m = os.path.basename(x)
    n = os.path.basename(y)

    for word in ('The', 'A'):
        word += ' '
        if m.find(word) == 0:
            m = m.replace(word, '', 1)
        if n.find(word) == 0:
            n = n.replace(word, '', 1)

    return cmp(m.upper(), n.upper()) # be case insensitive


def find_start_string(s1, s2):
    """
    Find similar start in both strings
    """
    ret = ''
    tmp = ''
    while True:
        if len(s1) < 2 or len(s2) < 2:
            return ret
        if s1[0] == s2[0]:
            tmp += s2[0]
            if s1[1] in (u' ', u'-', u'_', u',', u':', '.') and \
               s2[1] in (u' ', u'-', u'_', u',', u':', '.'):
                ret += tmp + u' '
                tmp = ''
            s1 = s1[1:].lstrip(u' -_,:.')
            s2 = s2[1:].lstrip(u' -_,:.')
        else:
            return ret

def remove_start_string(string, start):
    """
    remove start from the beginning of string.
    """
    start = start.replace(u' ', '')
    for i in range(len(start)):
        string = string[1:].lstrip(' -_,:.')

    return string[0].upper() + string[1:]


def tagmp3 (filename, title=None, artist=None, album=None, track=None,
            tracktotal=None, year=None):
    """
    use eyeD3 directly from inside kaa.metadata to
    set the tag. We default to 2.3 since even
    though 2.4 is the accepted standard now, more
    players support 2.3
    """
    import kaa.metadata.audio.eyeD3 as eyeD3

    try:
        tag = eyeD3.Tag()
        tag.link(String(filename))
        tag.header.setVersion(eyeD3.ID3_V2_3)
        if artist: tag.setArtist(String(artist))
        if album:  tag.setAlbum(String(album))
        if title:  tag.setTitle(String(title))
        if track:  tag.setTrackNum((track, tracktotal))   # eyed3 accepts None for tracktotal
        if year:   tag.setDate(year)
        tag.update()
    except:
        print 'Cannot tag \"%s\"' % (String(filename))
    return


def htmlenties2txt(string):
    """
    Converts a string to a string with all html entities resolved.
    Returns the result as Unicode object (that may conatin chars outside 256.
    """
    e = copy.deepcopy(htmlentitydefs.entitydefs)
    e['ndash'] = "-";
    e['bull'] = "-";
    e['rsquo'] = "'";
    e['lsquo'] = "`";
    e['hellip'] = '...'

    string = Unicode(string).replace("&#039", "'").replace("&#146;", "'")

    i = 0
    while i < len(string):
        amp = string.find("&", i) # find & as start of entity
        if amp == -1: # not found
            break
        i = amp + 1

        semicolon = string.find(";", amp) # find ; as end of entity
        if string[amp + 1] == "#": # numerical entity like "&#039;"
            entity = string[amp:semicolon+1]
            try:
                replacement = Unicode(unichr(int(entity[2:-1])))
            except UnicodeError:
                replacement = unichr(int(entity[2:-1]))
        else:
            entity = string[amp:semicolon + 1]
            if semicolon - amp > 7:
                continue
            try:
                # the array has mappings like "Uuml" -> "ü"
                replacement = e[entity[1:-1]]
            except KeyError:
                continue
        try:
            string = string.replace(entity, replacement.decode("latin-1"))
        except UnicodeError:
            string = string.replace(entity, replacement)
    return string


def comingup(scheduledRecordings=None, write=False):
    """
    What's coming up in the TV recording schedule
    """
    _debug_('comingup(scheduledRecordings=%r, write=%r)' % (scheduledRecordings, write), 2)
    import time
    import codecs
    from tv.record_client import RecordClient

    result = u''

    #XXX this is bad as the cachefile is not updated on a write operation
    cachefile = os.path.join(config.FREEVO_CACHEDIR, 'upsoon')
    if scheduledRecordings is None:
        # if the cached file exists and is younger than 10 mins
        if os.path.exists(cachefile) and os.stat(cachefile)[ST_MTIME] >= time.time() - 600:
            cache = codecs.open(cachefile, 'r', config.encoding)
            for a in cache.readlines():
                result = result + a
            cache.close()
            #print 'comingup:1:result=%r' % (result,)
            return result

        (status, schedule) = RecordClient().getScheduledRecordingsNow()
        if status is None:
            result = RecordClient().recordserverdown
            return result
        elif status is False:
            result = _('No recordings are scheduled')
            return result
    else:
        schedule = scheduledRecordings

    progs = schedule.getProgramList()

    f = lambda a, b: cmp(a.start, b.start)
    progl = progs.values()
    progl.sort(f)

    today = []
    tomorrow = []
    later = []

    for what in progl:
        if time.localtime(what.start)[2] == time.localtime()[2]:
            today.append(what)
        if time.localtime(what.start)[2] == (time.localtime()[2] + 1):
            tomorrow.append(what)
        if time.localtime(what.start)[2] > (time.localtime()[2] + 1):
            later.append(what)

    if len(today) > 0:
        result = result + _('Today') + u':\n'
        for m in today:
            sub_title = ''
            if hasattr(m, 'sub_title') and m.sub_title:
                sub_title = u' "' + Unicode(m.sub_title) + u'" '
            result = result + u"- %s%s " % \
                     ( Unicode(m.title), Unicode(sub_title) ) \
                     + _('at') + u" %s\n" % \
                     Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(m.start)))

    if len(tomorrow) > 0:
        result = result + _('Tomorrow') + u':\n'
        for m in tomorrow:
            sub_title = ''
            if hasattr(m, 'sub_title') and m.sub_title:
                sub_title = ' "' + m.sub_title + '" '
            result = result + u"- %s%s " % \
                     ( Unicode(m.title), Unicode(sub_title) ) \
                     + _('at') + u" %s\n" % \
                     Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(m.start)))

    if len(later) > 0:
        result = result + _('This Week') + u':\n'
        for m in later:
            sub_title = ''
            if hasattr(m, 'sub_title') and m.sub_title:
                sub_title = ' "' + m.sub_title + '" '
            result = result + u"- %s%s " % ( Unicode(m.title), Unicode(sub_title) ) \
                    + _('at') + u" %s\n" % Unicode(time.strftime(config.TV_DATE_FORMAT, time.localtime(m.start)))

    if not result:
        result = _('No recordings are scheduled')

    if os.path.isfile(cachefile):
        os.unlink(cachefile)
    cache = codecs.open(cachefile, 'w', config.encoding)
    cache.write(result)
    cache.close()

    return result



#
# synchronized objects and methods.
# By André Bjärby
# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/65202
#
from types import *
def _get_method_names (obj):
    if type(obj) == InstanceType:
        return _get_method_names(obj.__class__)

    elif type(obj) == ClassType:
        result = []
        for name, func in obj.__dict__.items():
            if type(func) == FunctionType:
                result.append((name, func))

        for base in obj.__bases__:
            result.extend(_get_method_names(base))

        return result

def human_aspect_ratio (width, height):
    try:
        ratio = str(round(float(width)/float(height), 2))
        if ratio[:3] == '1.3':
            ratio = '4:3'
        elif ratio[:3] == '1.7':
            ratio = '16:9'
        elif ratio[:3] == '2.3':
            ratio = _('Widescreen')
    except ValueError:
        ratio = None

    return ratio



class _SynchronizedMethod:

    def __init__ (self, method, obj, lock):
        self.__method = method
        self.__obj = obj
        self.__lock = lock

    def __call__ (self, *args, **kwargs):
        self.__lock.acquire()
        try:
            #print 'Calling method %s from obj %s' % (self.__method, self.__obj)
            return self.__method(self.__obj, *args, **kwargs)
        finally:
            self.__lock.release()


class SynchronizedObject:

    def __init__ (self, obj, ignore=None, lock=None):
        import threading

        self.__methods = {}
        self.__obj = obj
        ignore = ignore or []
        lock = lock and lock or threading.RLock()
        for name, method in _get_method_names(obj):
            if not name in ignore:
                self.__methods[name] = _SynchronizedMethod(method, obj, lock)

    def __getattr__ (self, name):
        try:
            return self.__methods[name]
        except KeyError:
            return getattr(self.__obj, name)
