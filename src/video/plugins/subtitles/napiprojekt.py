# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in for napiprojekt support
# -----------------------------------------------------------------------
# $Id: $
#
# Notes: napiprojekt plugin. 
#        You can donwload subtitles from the http://napiprojekt.pl
#        with this plugin. Only two langauges supported, Polish and English.
#        Check out the video.subtitles plugin for more configuration options 
#
#        This code is partially based on some anonymous code found in the depths
#        of the www :-)
#
# Todo:  none
#
# BTW:   napi is short in polish for napisy or subtitles in english :-)
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

# Module Imports
import logging
logger = logging.getLogger('freevo.video.plugins.napiprojekt')

import os
import urllib
import tempfile
import subprocess
import codecs

import config
import plugin
import time

try:
    from hashlib import md5 as md5
except ImportError:
    from md5 import md5

NAPI_LANGS = [ 'pol', 'eng' ]

from video.plugins.subtitles import SubtitlesPlugin, SubtitlesError, Subtitles

class PluginInterface(SubtitlesPlugin):
    """
    This is a handler plugin for http://napiprojekt.pl subtitle provider
    and is used by main subtitle plugin.
    Only polish and english subtitles are supported by napiprojekt.pl

    Activate with:
    | plugin.activate('video.subtitles.napiprojekt')
    and of course make sure the main subtitles plugin is activated too:
    | plugin.activate('video.subtitles')
    """
    def __init__(self):
        """
        Constructor
        """
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        
        if not plugin.is_active('video.subtitles'):
            self.reason = 'Plugin \'video.subtitles\' not active, activate it first in your local_config.py!'
            return

        langs = []

        try:
            langs = config.NAPI_LANGS
        except:
            langs = NAPI_LANGS

        SubtitlesPlugin.__init__(self, 'np', 'napiprojekt.pl', langs)
        plugin.register(self, 'video.subtitles.napiprojekt')


    def config(self):
        """
        Returns the config variables used by this plugin
        """
        return [
            ('NAPI_LANGS', NAPI_LANGS, 
                'All Supported by napiprojekt.pl ISO 639-2 subtitles language codes'),
            ('NAPI_LANG_MAP', { 'pol': ('PL'), 'eng': ('ENG') },
                'Maps ISO 639-2 lang code to the one used by napiprojekt.pl'), 
            ('NAPI_PWD', 'iBlm8NTigvru0Jr0',
                'Password for the compressed file'), 
            ('NAPI_URL', 'http://napiprojekt.pl/unit_napisy/dl.php?l=%s&f=%s&t=%s&v=other&kolejka=false&nick=&pass=&napios=%s',
                'Napiprojekt fetch URL'),
        ]


    def get_subs(self, vfile, langs_):
        """
        Get all available subtitles for the item
        @returns: the collection of subtitles keyed by the subtitle id
        """
        # based on requested languages, create intersect of capabilites vs. request
        langs = filter(lambda x: x in langs_, self.langs)
        subs  = {}
        hash  = self._hash(vfile)

        if not hash:
            logger.warning('Hashing of %s failed, aborting...', vfile)
            return subs

        for lang in langs:
            sub = NapiSubtitles(self, vfile, lang, hash)
            if not sub.download():
                continue
                
            subs[sub['id']] = sub

        return subs
        

    #
    # Class' private methods below
    #
    def _hash(self, vfile):
        """
        Calculates the hash of chunk of of the video file
        used in subsequent lookup at the remote server
        """
        hash  = md5()

        try:
            hash.update(open(vfile).read(10485760))
        except (IOError, OSError), e:
            logger.warning('Hashing failed: %s', e)
            return None

        return hash    


class NapiSubtitles(Subtitles):
    """
    Specialised napiprojekt class that knows how to download, decompress 
    and write subtitles from napiprojekt.pl
    """
    def __init__(self, handler, vfile, lang, hash):
        """
        Constructor
        """
        self.hash = hash
        Subtitles.__init__(self, handler, vfile, lang)


    def download(self):
        """
        Based on requested languages, downloads subtitles from the remote server
        @return:    True if successful
        """
        logger.debug('Downloading subtitles for %s in %s', self.vfile, self.lang)

        if not self.hash:
            return False
            
        data = None
        url = config.NAPI_URL % \
            (config.NAPI_LANG_MAP[self.lang], self.hash.hexdigest(), self._f(self.hash.hexdigest()), os.name)

        http_code = 200
        try:
            data = urllib.urlopen(url)
            if hasattr(data, 'getcode'):
                http_code = data.getcode() 
            data = data.read()
        except (IOError, OSError), e:
            logger.warning('Fetching subtitles failed: %s', e)
            return False

        if http_code != 200:
            logger.warning('Fetching subtitles failed, HTTP code: %s', str(http_code))
            return False

        if data.startswith('NPc'):
            logger.warning('Subtitles for %s in %s not found', self.vfile, self.lang)
            return False
            
        self.data = data
        self.compressed = True
       
        logger.info('Downloaded subtitles for %s in %s', self.vfile, self.lang)

        return True


    def save(self):
        """
        Saves downloaded subtitles
        """
        logger.info('Saving subtitles for %s in %s', self.vfile, self.lang)
       
        if self.compressed:
            self._decompress()
            
        # we need to back up old subs if exist before we actually overwrite the old subs
        self.backup()

        logger.info('Writing file %s', self.sfile)

        fp = codecs.open(self.sfile,'wb')
        fp.write(self.data)
        fp.close()

        logger.info('Subtitle file %s written (%d bytes)', self.sfile, len(self.data))
        
        return True


    #
    # Class' private methods below
    #
    def _decompress(self):
        """
        Decompresses download data (napiprojekt uses 7Zip compression)
        """
        fp = tempfile.NamedTemporaryFile('wb', suffix=".7z")
        tfp = fp.name
        fp.write(self.data)
        fp.flush()

        try:
            cmd = ['/usr/bin/7z', 'x', '-y', '-so', '-p' + config.NAPI_PWD, tfp]
            sa = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
            (so, se) = sa.communicate(self.data)
            self.data = so
            retcode = sa.returncode
            logger.debug('Executing cmd %s', ' '.join(cmd))

        except OSError, e:
            fp.close()
            msg = 'Skipping, subtitle decompression failed: %s' % (e)
            logger.warning(msg)
            raise SubtitlesError(msg)

        fp.close()

        logger.debug("Decompressed subtitles for %s" % (self.lang))


    def _f(self, z):
        """
        Magic number calculation
        """
        idx = [ 0xe, 0x3,  0x6, 0x8, 0x2 ]
        mul = [   2,   2,    5,   4,   3 ]
        add = [   0, 0xd, 0x10, 0xb, 0x5 ]

        b = []
        for i in xrange(len(idx)):
            a = add[i]
            m = mul[i]
            i = idx[i]

            t = a + int(z[i], 16)
            v = int(z[t:t+2], 16)
            b.append( ("%x" % (v*m))[-1] )

        return ''.join(b)
