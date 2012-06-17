# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in for opensubtitles.org support
# -----------------------------------------------------------------------
# $Id: $
#
# Notes: opensubtitles plugin. 
#        You can donwload subtitles from the http://opensubtitles.org
#        Check out the video.subtitles plugin for configuration options 
#
#        This code is partially based on lm.py that can be found on 
#        https://github.com/RedRise/lm
#        Copyright (C) 2012 Guillaume Garchery (polluxxx@gmail.com)
#        Copyright (C) 2010 Jérôme Poisson (goffi@goffi.org)
#
# Todo:  none
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
logger = logging.getLogger('freevo.video.plugins.opensubtitles')

import os

import zlib
import struct
import codecs
import base64
import xmlrpclib
from difflib import SequenceMatcher

import config
import plugin
import time

from video.plugins.subtitles import SubtitlesPlugin, SubtitlesError, Subtitles

class PluginInterface(SubtitlesPlugin):
    """
    This is a handler plugin for http://opensubtitles.org subtitle provider
    and is used by main subtitle plugin.

    Activate with:
    | plugin.activate('video.subtitles.opensubtitles')
    and of course make sure the main subtitles plugin is activated too:
    | plugin.activate('video.subtitles')

    OpenSubtitles.org supports so many different languages that it's impossible 
    to list all available language codes here.
    See http://en.wikipedia.org/wiki/List_of_ISO_639-2_codes for the codes and 
    names, and http://opensubtitles.org for supported languages.
    """

    def __init__(self):
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        
        if not plugin.is_active('video.subtitles'):
            self.reason = 'Plugin \'video.subtitles\' not active, activate it first in your local_config.py!'
            return

        # opensubtitles XMLRPC server and token
        self.server = None
        self.token  = None
        
        SubtitlesPlugin.__init__(self, 'os', 'opensubtitles.org', [])
        plugin.register(self, 'video.subtitles.opensubtitles')
        

    def config(self):
        """
        Returns the config variables used by this plugin
        User agent is essential to request opensubtitles
        be sure to update it before any change
        """
        return [
            ('OSUBS_USER_AGENT', 'Freevo v1.9', 
                'Opensubtitles User Agent String'),
            ('OSUBS_DOMAIN',     'http://api.opensubtitles.org/xml-rpc', 
                'Opensubtitles domain'), 
        ]


    def get_subs(self, vfile_, langs_):
        """
        Get all available subtitles for the item
        @returns: the collection of subtitles keyed by the subtitle id
        """
        subs  = {}
        langs = langs_

        hash  = self._hash(vfile_)

        if not hash:
            logger.warning('Hashing of %s failed, aborting...', vfile_)
            return subs 

        info  = self._get_info(hash)

        if not info:
            logger.warning('Retrieving of the movie info for %s failed, aborting...', vfile_)
            return subs

        for lang in langs:
            sub = OpenSubtitles(self, vfile_, lang, hash, info)
            if not sub.download():
                continue
                
            subs[sub['id']] = sub

        return subs
       

    def search(self, query):
        """
        search the opensubtitles given the query
        @param id; opensubtitles sub id
        """
        if self._login():

            refs = self.server.SearchSubtitles(self.token, query)

            if self._status_ok(refs):
                self._logout()
                logger.debug('Retrieved available subs details')
                return refs

            logger.warning('Failed to retrieved subs details')
            self._logout()

        return None


    def download(self, id):
        """
        Based on requested languages, downloads subtitles from the remote server
        @param id:  opensubtitle sub id
        @return:    downloaded subtiltle data    
        """
        if self._login():
            try:
                # we pass a list of ids because opensubtitles expect this
                res = self.server.DownloadSubtitles(self.token, [id])
            except Exception, e:
                logger.warning("Error downloading: %s" % (e), DWARNING)
                self._logout()
                return None 

            if self._status_ok(res):
                return res

            # if we ever get here, something went seriously wrong
            logger.warning('Error downloading: empty result set')
            self._logout()

        return None


    #
    # Class' private methods below
    #
    def _hash(self, vfile_):
        """
        Calculates the hash of chunk of of the video file
        used in subsequent lookup at the remote server
        """
        try:
            longlongformat = 'q'  # long long
            bytesize = struct.calcsize(longlongformat)

            f = open(vfile_, "rb")

            filesize = os.path.getsize(vfile_)
            hash = filesize

            if filesize < 65536 * 2:
                logger.warning('Hashing of %s failed: file size too small %d', vfile_, filesize)
                return None

            for x in range(65536/bytesize):
                buffer = f.read(bytesize)
                (l_value,) = struct.unpack(longlongformat, buffer)
                hash += l_value
                hash = hash & 0xFFFFFFFFFFFFFFFF #to remain as 64bit number

            f.seek(max(0,filesize-65536),0)

            for x in range(65536/bytesize):
                buffer = f.read(bytesize)
                (l_value,)= struct.unpack(longlongformat, buffer)
                hash += l_value
                hash = hash & 0xFFFFFFFFFFFFFFFF

            f.close()

            hash = "%016x" % hash
            return hash

        except (IOError, OSError), e:
            logger.warning('Hashing of %s failed: %s', vfile_, e)
            return None


    def _status_ok(self, ans):
        """
        Verify the connetion status
        """
        status = False
        try:
            if ans.has_key('status') and ans['status'] == '200 OK':
                logger.debug('opensubtitles answer status OK')
                status = True
            else:
                logger.warning('opensubtitles answer status DOWN')

        except Exception, e:
            logger.warning('Error %s', e)

        finally:
            return status


    def _login(self, user='', password=''):
        """
        Login to the remote server
        """
        try:
            server = xmlrpclib.ServerProxy(config.OSUBS_DOMAIN)
            log    = server.LogIn(user,password, 'en', config.OSUBS_USER_AGENT)

            if self._status_ok(log):
                logger.debug('opensubtitles login OK')
                self.server = server
                self.token  = log['token']
            else:
                raise SubtitlesError(str(log))

        except Exception, e:
            logger.warning('Failed to login to opensubtitles: %s', e)
            return False

        return True

    
    def _logout(self):
        """
        Logout from the remote server
        """
        if self.token:
            try:
                self.server.LogOut(self.token)
                logger.debug('opensubtitles logout OK')
            except Exception, e:
                logger.warning('Failed to logout gracefully from opensubtitles: %s', e)
                return False
        
        return True

    
    def _get_info(self, hash):
        """
        Retrive general info for a list of movie hash
        """
        data = None
        
        logger.debug('Requesting opensubtitle info for hash %s', hash)

        try:
            self._login()
            res = self.server.CheckMovieHash(self.token, [hash])
            data = res['data'][hash]
            self._logout()

        except Exception, e:
            logger.warning('Error when retrieving hash from opensubtitles %s', e)
            pass

        return data


class OpenSubtitles(Subtitles):
    """
    Specialised opnsubtitles class that knows how to download, decompress 
    and write subtitles from opensubtitles.org
    """

    def __init__(self, handler, vfile, lang, hash, info):
        Subtitles.__init__(self, handler, vfile, lang)

        self.hash = hash
        self.info = info
        # default format from opensubtitles is srt
        self.fmt  = 'srt'


    def download(self):
        """
        Based on requested languages, downloads subtitles from the remote server
        @return:    True if successful
        """
        logger.debug('Downloading subtitles for %s in %s', self.vfile, self.lang)

        refs = self.handler.search(self._build_query())

        if refs:
            if refs['data'] != False:
                # we narrow down to one only but best match
                fltd = self._filter(refs['data'])
                id = fltd['IDSubtitleFile']
                logger.debug('Sub id to download: %s', id)

                # we get the sub file from opensubtitles
                res = self.handler.download(id)

                if res and res['data'] != 'False':
                    for sub in res['data']:
                        # we get the first result
                        self.data = sub['data']
                        self.fmt  = fltd['SubFormat']
                        self.compressed = True
                        logger.info('Downloaded subtitles id %s, lang %s, format %s', 
                                     id, self.lang, self.fmt)

            else:
                logger.info('No subtitles found: %s', str(refs))
                return False

        else:
            logger.warning('Failed to download subtitles: %s', str(refs))
            return False

        logger.info('Downloaded subtitles for %s in %s', self.vfile, self.lang)

        return True
        
        
    def save(self):
        """
        Saves downloaded subtitles
        @return:      True if successful
        """
        logger.debug('Saving subtitles for %s in %s', self.vfile, self.lang)

        if self.compressed:
            self._decompress()
            
        # we need to back up old subs if exist before we actually overwrite the old subs
        self.backup()

        logger.debug('Writing file %s', self.sfile)

        fp = codecs.open(self.sfile,'wb')
        fp.write(self.data)
        fp.close()

        return True

    #
    # Class' private methods below
    #
    def _decompress(self):
        """
        Decompresses download data (napiprojekt uses 7Zip compression)
        """
        sub_d = base64.standard_b64decode(self.data)
        sub_d = zlib.decompress(sub_d, 47)
        self.data = sub_d
        logger.debug('Decompressed subs for %s', self.lang)


    def _build_query(self):
        """
        Build a useful info dictionary and the list of queries
        to be passed as argument to SearchSubtitles XMLRPC call
        @return:      constructed query
        """
        query = []

        imdbid = self.info['MovieImdbID']
        size   = os.path.getsize(self.vfile)
        vfile  = os.path.basename(self.vfile)

        if imdbid:
            query.append({ 'sublanguageid':self.lang,
                               'moviehash':str(self.hash),
                           'moviebytesize':str(size)})

            # even if hash is found in opensubtitles, we add
            # another query with imdbid
            query.append({'sublanguageid':self.lang,
                                 'imdbid':imdbid})

        logger.debug('Built query %s', str(query))
        return query


    def _filter(self, subs):
        """
        Filters subs (list result of SearchSubtitles call)
        best found subtitles (hash match) or most downloaded subtitles
        @param subs:  result['data'] of a SearchSubtitles XMLRPC call
        @return:      filtered subtitle list
        """

        keep = [ s for s in subs if s['MovieHash'] == self.hash ]

        if len(keep) == 0:
            keep = [ s for s in subs if s['IDMovieImdb'] == str(int(self.info['MovieImdbID']))]

        if len(keep) > 0:
            keep.sort( key=lambda k: k['SubDownloadsCnt'], reverse=True )

            return keep[0]

        return None
