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

__author__           = 'Maciej Mike Urbaniak (maciej@urbaniak.org)'
__maintainer__       = 'Maciej Mike Urbaniak'
__maintainer_email__ = 'maciej@urbaniak.org'
__version__          = 'Revision 0.1'
__license__          = 'GPL' 

# Module Imports
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

from subtitles import SubsHandler, SubsError, Subtitles

# User agent is essential to request opensubtitles
# be sure to update it before any change

class PluginInterface(plugin.Plugin):
    """
    This is a handler plugin for http://opensubtitles.org subtitle provider
    and is used by main subtitle plugin.
    

    Activate with:
    | plugin.activate('video.opensubtitles')
    
    and make sure the SUBS_AVAILABLE_HANDLERS = [ ('opensubtitles'), ]
    is set for the main subtitles plugin to be able to use this plugin.
    Even if this plugin is not explicitly activated in the local_config.py, main
    video.subtitles plugin will activate it automagically, providing that 
    SUBS_HANDLERS variable is properly initialised with 'video.opensubtitles' 
    plugin name.
    
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
            self.reason = 'Plugin "video.subtitles" not active, activate it first in your local_config.py!'
            return

        self.handler = OpenSubtitlesHandler()
        
        plugin.Plugin.__init__(self)

        plugin.register(self, 'video.opensubtitles')
        

    def config(self):
        """returns the config variables used by this plugin"""
        return [
            (OSUBS_USER_AGENT, 'OS Test User Agent', 
                'Opensubtitles User Agent String'),
            (OSUBS_DOMAIN,     'http://api.opensubtitles.org/xml-rpc', 
                'Opensubtitles domain'), 
        ]


    def __getitem__(self, key):
        """
        Get the item's attribute.

        @returns: the specific attribute
        """
        if key == 'name': 
            return 'video.opensubtitles'
            
        if key == 'id': 
            return self.handler.id

        if key == 'handler': 
            return self.handler

        return plugin.Plugin.__getitem__(self, key)     
        

class OpenSubtitles(Subtitles):
    def __init__(self, handler, vfile, lang, hash, info):
        Subtitles.__init__(self, handler, vfile, lang)

        self.hash = hash
        self.info = info
        # default format from opensubtitles is srt
        self.fmt  = 'srt'


    def download(self):
        _debug_("Downloading subtitles for %s in %s" % (self.vfile, self.lang), DINFO)

        refs = self.handler.search(self._build_query())

        if refs:
            if refs['data'] != False:
                # we narrow down to one only but best match
                fltd = self._filter(refs['data'])
                id = fltd['IDSubtitleFile']
                _debug_( "Sub id to download: %s" % (id))

                # we get the sub file from opensubtitles
                res = self.handler.download(id)

                if res and res['data'] != 'False':
                    for sub in res['data']:
                        # we get the first result
                        self.data = sub['data']
                        self.fmt  = fltd['SubFormat']
                        self.compressed = True
                        _debug_( "Downloaded subtitles id %s, lang %s, format %s" % \
                                (id, self.lang, self.fmt), DINFO)

            else:
                _debug_("No subtitles found: %s" % str(refs), DINFO)
                return False

        else:
            _debug_("Failed to download subtitles: %s" % str(refs), DWARNING)
            return False

        _debug_("Downloaded subtitles for %s in %s" % (self.vfile, self.lang), DINFO)

        return True
        
        
    def save(self):
        """
        Saves downloaded subtitles
        """
        _debug_("Saving subtitles for %s in %s" % (self.vfile, self.lang), DINFO)

        if self.compressed:
            self._decompress()
            
        # we need to back up old subs if exist before we actually overwrite the old subs
        self.backup()

        _debug_("Writing file %s" % (self.sfile))

        fp = codecs.open(self.sfile,'wb')
        fp.write(self.data)
        fp.close()

        return True

    """
    Class' private methods below
    """

    def _decompress(self):
        sub_d = base64.standard_b64decode(self.data)
        sub_d = zlib.decompress(sub_d, 47)
        self.data = sub_d
        _debug_("Decompressed subs for %s" % (self.lang))


    def _build_query(self):
        """
        build a useful info dictionary and the list of queries
        to be passed as argument to SearchSubtitles XMLRPC call
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

        _debug_("Built query %s" % str(query))
        return query


    def _filter(self, subs):
    # filters subs (list result of SearchSubtitles call)
    # best found subtitles (hash match) or most downloaded subtitles
    # @param subs: result['data'] of a SearchSubtitles XMLRPC call

        keep = [ s for s in subs if s['MovieHash'] == self.hash ]

        if len(keep) == 0:
            keep = [ s for s in subs if s['IDMovieImdb'] == str(int(self.info['MovieImdbID']))]

        if len(keep) > 0:
            keep.sort( key=lambda k: k['SubDownloadsCnt'], reverse=True )

            return keep[0]

        return None


class OpenSubtitlesHandler(SubsHandler):
    """
    friend class OpenSubtitles
    """
    def __init__(self):
        # opensubtitles XMLRPC server and token
        self.server = None
        self.token  = None
        
        SubsHandler.__init__(self, 'os', 'opensubtitles.org', [])


    def __getitem__(self, key):
        """
        Get the item's attribute.

        @returns: the specific attribute
        """
        return SubsHandler.__getitem__(self, key)


    def get_subs(self, vfile_, langs_):
        subs  = {}
        # based on requested languages, create intersect of capabilites vs. request
        # langs = filter(lambda x: x in langs_, self.langs)
        langs = langs_

        hash  = self._hash(vfile_)

        if not hash:
            _debug_("Hashing of %s failed, aborting..." % (vfile_), DWARNING)
            return subs 

        info  = self._get_info(hash)

        if not info:
            _debug_("Retrieving of the movie info for %s failed, aborting..." % (vfile_), DWARNING)
            return subs

        for lang in langs:
            sub = OpenSubtitles(self, vfile_, lang, hash, info)
            if not sub.download():
                continue
                
            subs[sub['id']] = sub

        return subs
        
        #return [map(lambda x: x['lang'], self.subs)]
        

    def search(self, query):
        if self._login():

            refs = self.server.SearchSubtitles(self.token, query)

            if self._status_ok(refs):
                self._logout()
                _debug_("Retrieved available subs details")
                return refs

            _debug_("Failed to retrieved subs details")
            self._logout()

        return None


    def download(self, id):
    # download a subtitles for a given id
    # @param id; opensubtitle sub id
        if self._login():
            try:
                # we pass a list of ids because opensubtitles expect this
                res = self.server.DownloadSubtitles(self.token, [id])
            except Exception, e:
                _debug_("Error downloading: %s" % (e), DWARNING)
                self._logout()
                return None 

            if self._status_ok(res):
                return res

            # if we ever get here, something went seriously wrong
            _debug_("Error downloading: empty result set", DWARNING)
            self._logout()

        return None


    """
    Class' private methods below
    """
    def _hash(self, vfile_):
        try:
            longlongformat = 'q'  # long long
            bytesize = struct.calcsize(longlongformat)

            f = open(vfile_, "rb")

            filesize = os.path.getsize(vfile_)
            hash = filesize

            if filesize < 65536 * 2:
                _debug_("Hashing of %s failed: file size too small %d" % (vfile_, filesize), DWARNING)
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
            _debug_("Hashing of %s failed: %s" % (vfile_, e), DWARNING)
            return None


    def _status_ok(self, ans):
        status = False
        try:
            if ans.has_key("status") and ans["status"] == "200 OK":
                _debug_("opensubtitles answer status OK")
                status = True
            else:
                _debug_("opensubtitles answer status DOWN", DWARNING)

        except Exception, e:
            _debug_("Error %s" % e, DWARNING)

        finally:
            return status


    def _login(self, user="", password=""):
        try:
            server = xmlrpclib.ServerProxy(OSUBS_DOMAIN)
            log    = server.LogIn(user,password, 'en', OSUBS_USER_AGENT)

            if self._status_ok(log):
                _debug_("opensubtitles login OK")
                self.server = server
                self.token  = log['token']
            else:
                raise SubsError(str(log))

        except Exception, e:
            _debug_("Failed to login to opensubtitles: %s" % (e), DWARNING)
            return False

        return True

    
    def _logout(self):
        if self.token:
            try:
                self.server.LogOut(self.token)
                _debug_("opensubtitles logout OK")
            except Exception, e:
                _debug_("Failed to logout gracefully from opensubtitles: %s" % (e), DWARNING)
                return False
        
        return True

    
    # retrive general info for a list of movie hash
    def _get_info(self, hash):
        data = None
        
        _debug_("Requesting opensubtitle info for hash %s" % (hash))

        try:
            self._login()
            res = self.server.CheckMovieHash(self.token, [hash])
            data = res['data'][hash]
            self._logout()

        except Exception, e:
            _debug_("Error when retrieving hash from opensubtitles %s" % (e), DWARNING)
            pass

        return data











