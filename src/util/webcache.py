# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Simple web cache
# -----------------------------------------------------------------------
# $Id: osd.py 11732 2010-11-14 22:26:54Z adam $
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
Simple thread-safe web cache.
"""

import os
import os.path
import urllib2
import sqlite3
import time
import hashlib
import traceback
import threading

SCHEMA_VERSION=1
SCHEMA="""
DROP TABLE IF EXISTS Metadata;
DROP TABLE IF EXISTS Entries;

CREATE TABLE Metadata (key PRIMARY KEY, value);
CREATE TABLE Entries(url PRIMARY KEY, expires, filename);
INSERT INTO Metadata (key, value) values('version', %d);
""" % SCHEMA_VERSION

class WebCache:
    """
    A class that implements a simple web cache allowing a URL to be retrieve 
    from the network or from a local copy if available.
    Local copies can be expired and removed from disk by calling the clean
    method. The entire cache can be flushed using the empty method.

    Currently this only checks against the URL and use max-age to determine how
    long to cache the results for.
    """
    
    def __init__(self, cache_dir, user_agent=None):
        """Creates a new web cache object.

        @param cache_dir: The directory to use to store the cache in.

        @param user_agent: (Optional) User agent string to use when making requests.
        """
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.cache_dir = cache_dir
        self.user_agent = user_agent
        self.cache_db = os.path.join(cache_dir, 'webcache.db')
        self.lock = threading.Lock()
        self.in_progress = {}
        self.__setup_db()


    def get(self, url, headers={}):
        """Downloads the contents of the URL or uses a local copy if available.

        @param url: The URL to get the contents of.

        @param headers: Optional additional headers to use when making the request.

        @returns: Returns a file like object from which the contents can be read.
        """
        self.lock.acquire()
        if url in self.in_progress:
            e = self.in_progress[url]
            self.lock.release()
            e.wait()
            self.lock.acquire()


        entry = self.__get_entry(url)
        if entry:
            filename = os.path.join(self.cache_dir, entry[2])
            if time.time() < entry[1]:
                fp = open(filename, 'rb')
                self.lock.release()
                return fp
            else:
                os.unlink(filename)

        e = threading.Event()
        self.in_progress[url] = e
        self.lock.release()
        
        request = urllib2.Request(url)
        if self.user_agent:
            request.add_header('User-Agent', self.user_agent)
        for key,value in headers.items():
            request.add_header(key, value)

        fp = urllib2.urlopen(request)

        self.lock.acquire()
        try:
            expires = 0
            headers = fp.info()
            if 'pragma' in headers:
                if headers['pragma'].lower().find('no-cache'):
                    expires = 0

            if 'cache-control' in headers:
                cc = _parse_cache_control(headers)
                if 'max-age' in cc:
                    expires = time.time() + int(cc['max-age'])
                elif 'no-cache' in cc:
                    expires = 0
                else:
                    expires = 0

            # If we can cache the resource download it to a local file and
            # return an open file handle to that file.
            if expires:
                # Generate a unique filename for the cache file.
                m = hashlib.md5()
                m.update(url)
                m.update(time.ctime())
                base_filename = m.hexdigest()

                # Download the resource
                filename = os.path.join(self.cache_dir, base_filename)
                new_fp = open(filename, 'wb')
                buf = fp.read(4096)
                while buf:
                    new_fp.write(buf)
                    buf = fp.read(4096)
                new_fp.close()
                fp.close()
                self.__add_entry(url, expires, base_filename)

                # Open the cache file so we can return a file handle
                fp = open(filename, 'rb')
                
            e.set()
            del self.in_progress[url]
        finally:
            self.lock.release()

        return fp


    def expire(self, url):
        """If the url exists in the cache remove it.
        
        @param url: The url to expire and remove any local copy of.
        """
        self.lock.acquire()
        try:
            entry = self.__get_entry(url)
            if entry:
                os.unlink(os.path.join(self.cache_dir, entry[2]))
                self.__remove_entry(url)
        finally:
            self.lock.release()

    
    def clean(self):
        """Remove all contents from the cache that have expired."""
        self.lock.acquire()
        try:
            con,cur = self.__get_db_cursor()
            now = int(time.time())
            cur.execute('SELECT filename FROM Entries WHERE expires<=?;', (now,))
            for (filename,) in cur:
                try:
                    os.unlink(os.path.join(self.cache_dir, filename))
                except:
                    traceback.print_exc()
            cur.execute('DELETE FROM Entries WHERE expires<=?;', (now,))
            con.commit()
            con.close()
        finally:
            self.lock.release()

    
    def empty(self):
        """Remove all contents from the cache."""
        self.lock.acquire()
        try:
            con,cur = self.__get_db_cursor()
            cur.execute('SELECT filename FROM Entries;')
            for (filename,) in cur:
                try:
                    os.unlink(os.path.join(self.cache_dir, filename))
                except:
                    traceback.print_exc()
            cur.execute('DELETE FROM Entries;')
            con.commit()
            con.close()
        finally:
            self.lock.release()
    
    
    def get_entries(self):
        """Returns all the non-expired URLs stored in the cache.
        @returns: A list of tuples containing the URL, expiry time and cache
        filename."""
        
        self.lock.acquire()
        try:
            con,cur = self.__get_db_cursor()
            cur.execute('SELECT * FROM Entries where expires>?;', (int(time.time()),))
            r = cur.fetchall()
            con.close()
        finally:
            self.lock.release()
        return r


    def __add_entry(self, url, expires, filename):
        con,cur = self.__get_db_cursor()
        cur.execute('INSERT OR REPLACE INTO Entries(url, expires, filename) values(?,?,?);',
            (url, int(expires), filename))
        con.commit()
        con.close()

    
    def __remove_entry(self, url):
        con,cur = self.__get_db_cursor()
        cur.execute('DELETE FROM Entries WHERE url=?;', (url,))
        con.commit()
        con.close()

    
    def __get_entry(self, url):
        con,cur = self.__get_db_cursor()
        cur.execute('SELECT * FROM Entries WHERE url=?;', (url,))
        r = cur.fetchone()
        con.close()
        return r


    def __get_db_cursor(self):
        con = sqlite3.connect(self.cache_db)
        cur = con.cursor()
        return con,cur


    def __setup_db(self):
        con,cur = self.__get_db_cursor()
        try:
            cur.execute('SELECT value FROM Metadata WHERE key="version";')
            r = cur.fetchone()
            if r:
                create = r[0] != SCHEMA_VERSION
        except:
            create = True

        if create:
            cur.executescript(SCHEMA)
            con.commit()
        con.close()


# Credit for the following function goes to httplib2
def _parse_cache_control(headers):
    retval = {}
    if headers.has_key('cache-control'):
        parts =  headers['cache-control'].split(',')
        parts_with_args = [tuple([x.strip().lower() for x in part.split("=", 1)]) for part in parts if -1 != part.find("=")]
        parts_wo_args = [(name.strip().lower(), 1) for name in parts if -1 == name.find("=")]
        retval = dict(parts_with_args + parts_wo_args)
    return retval


__default_cache = None

def get_default_cache():
    """Get the default cache to use for Freevo"""
    global __default_cache
    if __default_cache is None:
        import config
        import version
        import kaa
        __default_cache = WebCache(os.path.join(config.FREEVO_CACHEDIR, 'web'), 'Freevo/'+version.__version__)

        # Remove expired items from the cache.
        __default_cache.clean()
        
        # Set a timer for every 30 minutes to clean the cache.
        t = kaa.Timer(__default_cache.clean)
        t.start(1800)

    return __default_cache

def test():
    wc = WebCache('/tmp/webcache')
    def download(wc):
        wc.get('http://news.bbcimg.co.uk/media/images/50769000/jpg/_50769124_010996695-1.jpg')
        print 'Thread %s finished' % threading.currentThread().name

    threads = []
    for i in range(0,10):
        threads.append(threading.Thread(target=download,args=(wc,), name='Thread-%d'%i))

    for t in threads:
        t.start()

if __name__ == '__main__':
    test()