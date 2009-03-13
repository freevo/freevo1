# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# class and helpers for fxd/imdb generation
# -----------------------------------------------------------------------
# $Id$
#
# Notes: see http://pintje.servebeer.com/fxdimdb.html for documentation,
# Todo:
# - add support making fxds without imdb (or documenting it)
# - webradio support?
#
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


# python has no data hiding, but this is the intended use...
# subroutines completely in lowercase are regarded as more "private" functions
# sub-routines are regarded as public

#some data
__author__ = "den_RDC (rdc@kokosnoot.com)"
__version__ = "Revision 0.1"
__copyright__ = "Copyright (C) 2003 den_RDC"
__license__ = "GPL"

#Module Imports
import re
import urllib, urllib2, urlparse
import sys
import codecs
import os
import traceback
from BeautifulSoup import BeautifulSoup, NavigableString
import HTMLParser

import config
import util
from benchmark import benchmark
benchmarking = config.DEBUG_BENCHMARKING
benchmarkcall = config.DEBUG_BENCHMARKCALL

import kaa.metadata as mmpython
#Constants

try:
    import freevo.version as version
    import freevo.revision as revision
except:
    import version
    import revision

imdb_title_list = '/tmp/imdb-movies.list'
imdb_title_list_url = 'ftp://ftp.funet.fi/pub/mirrors/ftp.imdb.com/pub/movies.list.gz'
imdb_titles = None
imdb_info_tags = ('year', 'genre', 'tagline', 'plot', 'rating', 'runtime');


# headers for urllib2
txdata = None
txheaders = {
    'User-Agent': 'freevo %s (%s)' % (version, sys.platform),
    'Accept-Language': 'en-us',
}

#Begin class

class FxdImdb:
    """Class for creating fxd files and fetching imdb information"""

    @benchmark(benchmarking & 0x40, benchmarkcall)
    def __init__(self):
        """Initialise class instance"""

        # these are considered as private variables - don't mess with them unless
        # no other choice is given
        # FYI, the other choice always exists : add a subroutine or ask :)

        self.id_list = []
        self.id = None
        self.isdiscset = False
        self.title = ''
        self.info = {}

        self.image = None # full path image filename
        self.image_urls = [] # possible image url list
        self.image_url = None # final image url

        self.fxdfile = None # filename, full path, WITHOUT extension

        self.append = False
        self.device = None
        self.regexp = None
        self.mpl_global_opt = None
        self.media_id = None
        self.file_opts = []
        self.video = []
        self.variant = []
        self.parts = []
        self.var_mplopt = []
        self.var_names = []

        #initialize self.info
        for t in imdb_info_tags:
            self.info[t] = ""

        #image_url_handler stuff
        self.image_url_handler = {}
        self.image_url_handler['www.impawards.com'] = self.impawards


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def guessImdb(self, filename, label=False):
        """Guess possible imdb movies from file name. Same return as searchImdb"""
        _debug_('guessImdb(filename=%r, label=%r)' % (filename, label))

        # Special name rule for the encoding server
        m = re.compile('DVD \[([^]]*).*')
        res = m.search(filename)
        if res:
            name = res.group(1)
        else:
            name = filename

        # is this a series with season and episode number?
        # if so we will remember season and episode but will take it off from name

        # find <season>X<episode>
        season = ''
        episode = ''
        m = re.compile('([0-9]+)[xX]([0-9]+)')
        res = m.search(name)
        if res:
            name = re.sub('%s.*' % res.group(0), '', name)
            season = str(int(res.group(1)))
            episode = str(int(res.group(2)))

        # find S<season>E<episode>
        m = re.compile('[sS]([0-9]+)[eE]([0-9]+)')
        res = m.search(name)
        if res:
            name = re.sub('%s.*' % res.group(0), '', name)
            season = str(int(res.group(1)))
            episode = str(int(res.group(2)))

        name = vfs.basename(vfs.splitext(name)[0])
        name = re.sub('([a-z])([A-Z])', point_maker, name)
        name = re.sub('([a-zA-Z])([0-9])', point_maker, name)
        name = re.sub('([0-9])([a-zA-Z])', point_maker, name.lower())
        name = re.sub(',', ' ', name)

        _debug_('name=%s season=%s episode=%s' % (name, season, episode))
        if label:
            for r in config.IMDB_REMOVE_FROM_LABEL:
                try:
                    name = re.sub(r, '', name)
                except Exception, e:
                    print e
        else:
            for r in config.IMDB_REMOVE_FROM_NAME:
                try:
                    name = re.sub(r, '', name)
                except Exception, e:
                    print e

        parts = re.split('[\._ -]', name)
        name = ''
        for p in parts:
            if not p.lower() in config.IMDB_REMOVE_FROM_SEARCHSTRING and not re.search('[^0-9A-Za-z]', p):
                # originally: not re.search(p, '[A-Za-z]'):
                # not sure what's meant with that
                name += '%s ' % p
        return self.searchImdb(name, season, episode)


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def searchImdb(self, name, season=None, episode=None):
        """
        Search IMDB for the name

        @param name: name to search for
        @type name: string
        @returns: id list with tuples (id, name, year, type)
        """
        _debug_('searchImdb(name=%r, season=%r, episode=%r)' % (name, season, episode))
        tv_marker = (season and episode) and '"' or ''
        name = tv_marker+name.strip().strip(tv_marker)+tv_marker
        _debug_('searching imdb for "%s"' % (name))
        url = 'http://us.imdb.com/Tsearch?title=%s&restrict=Movies+and+TV' % urllib.quote(str(name))
        url = 'http://www.imdb.com/find?s=tt;site=aka;q=%s' % urllib.quote(str(name))
        _debug_('url="%s"' % (url,))

        req = urllib2.Request(url, txdata, txheaders)
        searchstring = name

        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, error:
            raise FxdImdb_Net_Error("IMDB unreachable : " + error)

        response_url = response.geturl()
        _debug_('response.url="%s"' % (response_url,))

        m = re.compile('/title/tt([0-9]*)/')
        idm = m.search(response_url)
        if idm: # Direct Hit
            id = idm.group(1)
            if season and episode:
                id = self.getIMDBid(id, season, episode)
            response.close()
            return [(id, name.title(), u'', '' )]

        if config.DEBUG >= 2:
            tmpfilename = '/tmp/%s.html' % name.replace(' ', '_').lower()
            tmp = open(tmpfilename, 'w')
            tmp.write(response.read())
            tmp.close()
            response.close()
            response = open(tmpfilename, 'r')

        data = self.parsesearchdata(response, url=response_url)
        response.close()

        _debug_('id_list has %s items' % (len(self.id_list)))
        if len(self.id_list) > 20:
            # too many results, check if there are stupid results in the list
            words = []

            # make a list of all words (no numbers) in the search string
            for p in re.split('[\._ -]', searchstring):
                #XXX this is incorrect for number only searches
                #if p and not p[0] in '0123456789':
                #    words.append(p)
                words.append(p)

            # at least one word has to be in the result
            new_list = []
            for result in self.id_list:
                appended = False
                for search_word in words:
                    if not appended and result[1] and result[1].lower().find(search_word.lower()) != -1:
                        new_list.append(result)
                        appended = True
            self.id_list = new_list
            _debug_('id_list has now %s items' % (len(self.id_list)))
        return self.id_list


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def getIMDBid(self, id, season=None, episode=None):
        """id (number)
        Set an imdb_id number for object, and fetch data"""

        self.id = id

        _debug_('id=%s season=%s episode=%s' % (id, season, episode))
        if season is None or episode is None:
            episodeid = id
        else:
            # This is a TV series, lets use a special search
            url = 'http://www.imdb.com/title/tt%s/episodes' % id
            _debug_('url=%r' % (url,))
            req = urllib2.Request(url, txdata, txheaders)

            try:
                idpage = urllib2.urlopen(req)
            except urllib2.HTTPError, why:
                raise FxdImdb_Net_Error('IMDB unreachable' + str(why))

            episodeid = self.find_episode(idpage, id, season, episode)
            idpage.close()

        # do the standard search
        url = 'http://www.imdb.com/title/tt%s' % episodeid
        _debug_('url=%r' % (url,))
        req = urllib2.Request(url, txdata, txheaders)

        try:
            idpage = urllib2.urlopen(req)
        except urllib2.HTTPError, why:
            raise FxdImdb_Net_Error('IMDB unreachable' + str(why))

        if config.DEBUG >= 2:
            tmpfilename = '/tmp/%s.html' % id
            tmp = open(tmpfilename, 'w')
            tmp.write(idpage.read())
            tmp.close()
            idpage.close()
            idpage = open(tmpfilename, 'r')

        self.parse_data(idpage, id, episodeid, season, episode)
        idpage.close()

        _debug_('episodeid=%s' % (episodeid,))
        return episodeid


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def parse_data(self, results, id, episodeid, season, episode):
        """results (imdb html page), imdb_id
        Returns tuple of (title, info(dict), image_urls)"""

        dvd = 0

        try:
            soup = BeautifulSoup(results.read(), convertEntities='xml')
        except UnicodeDecodeError:
            print "Unicode error: check that /usr/lib/python2.x/site.py has the correct default encoding"
            traceback.print_exc()
            return (None, None, None)

        # The parse tree can be now reduced by, everything outside this is not required:
        main = soup.find('div', {'id': 'tn15main'})
        #title = soup.title
        title = soup.find('h1')
        #this no longer works
        #image = soup.find('img', { 'title':title.next.strip() })
        #if image:
        #    self.info['image'] = image['src']

        self.title = title.next.strip()

        #is this a series? series pages a little different
        try:
            self.title = "%s - S%sE%02d - %s" % (self.title, season, int(episode), title.find('em').string.strip())
            self.info['title'] = self.title
            y = title.find('em').next.next.string.strip()
            self.info['year'] = y[1:-1]
        except (AttributeError, TypeError, ValueError):
            self.info['title'] = self.title
            self.info['year'] = title.find('a').string.strip()

        # Find the <div> with class info, each <h5> under this provides info
        for info in main.findAll('div', {'class' : 'info'}):
            infoh5 = info.find('h5')
            if not infoh5:
                continue
            try:
                infostr = infoh5.next
                key = infostr.string.strip(':').lower().replace(' ', '_')
                nextsibling = nextsibling = infoh5.nextSibling.strip()
                sections = info.findAll('a', { 'href' : re.compile('/Sections') })
                lists = info.findAll('a', { 'href' : re.compile('/List') })
                if len(nextsibling) > 0:
                    self.info[key] = nextsibling
                elif len(sections) > 0:
                    items = []
                    for item in sections:
                        items.append(item.string)
                    self.info[key] = ' / '.join(items)
                elif len(lists) > 0:
                    items = []
                    for item in lists:
                        items.append(item.string)
                    self.info[key] = ' / '.join(items)
            except:
                pass

        # Find Plot Outline/Summary:
        # Normally the tag is named "Plot Outline:" - however sometimes
        # the tag is "Plot Summary:" or just "Plot:". Search for all strings.
        imdb_result = soup.find(text='Plot Outline:')
        if not imdb_result:
            imdb_result = soup.find(text='Plot Summary:')
        if not imdb_result:
            imdb_result = soup.find(text='Plot:')
        if imdb_result:
            self.info['plot'] = imdb_result.next.strip()
        else:
            self.info['plot'] = u''

        # Find tagline - sometimes the tagline is missing.
        # Use an empty string if no tagline could be found.
        imdb_result = soup.find(text='Tagline:')
        if imdb_result:
            self.info['tagline'] = imdb_result.next.strip()
        else:
            self.info['tagline'] = u''

        rating = soup.find(text='User Rating:').findNext(text=re.compile('/10'))
        if rating:
            votes = rating.findNext('a')
            self.info['rating'] = rating.strip() + ' (' + votes.string.strip() + ')'
        else:
            self.info['rating'] = ''

        runtime = soup.find(text='Runtime:')
        if runtime and runtime.next:
            self.info['runtime'] = runtime.next.strip()
        else:
            self.info['runtime'] = ''

        # Replace special characters in the items
        for (k,v) in self.info.items():
            self.info[k] = self.convert_entities(v)

        if config.DEBUG >= 2:
            for (k,v) in self.info.items():
                _debug_('items=%s:%s' % (k, v))
            _debug_('id="%s", dvd="%s"' % (id, dvd))
            _debug_(self.info, 2)

        # Add impawards.com poster URLs.
        self.impawardsimages(self.info['title'], self.info['year'])

        # Add images from IMDB database. These images are much smaller than
        # the impawards ones.
        if not id:
            return (self.title, self.info, self.image_urls)

        if not dvd:
            url = 'http://us.imdb.com/title/tt%s/dvd' % id
            _debug_('url="%s"' % (url))
            req = urllib2.Request(url, txdata, txheaders)

            try:
                r = urllib2.urlopen(req)
                soup.feed(r.read())
                r.close()
                divs = soup.findAll('table', { 'class' : 'dvd_section' })
                for div in divs:
                    image = div.find('img')
                    if image['src'].find('http') < 0:
                        continue
                    self.image_urls += [ image['src'] ]
            except urllib2.HTTPError, error:
                pass
            except UnicodeDecodeError:
                # FIXME:
                # This is a bad hack. Some character could not be converted to ascii.
                # We ignore these errors as it does not really affect the FXD output.
                pass
        _debug_('image_urls=%s' % (self.image_urls))

        return (self.title, self.info, self.image_urls)


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def setFxdFile(self, fxdfilename=None, overwrite=False):
        """
        fxdfilename (string, full path)
        Set fxd file to write to, may be omitted, may be an existing file
        (data will be added) unless overwrite = True
        """

        if fxdfilename:
            if vfs.splitext(fxdfilename)[1] == '.fxd':
                self.fxdfile = vfs.splitext(fxdfilename)[0]
            else: self.fxdfile = fxdfilename

        else:
            if self.isdiscset == True:
                self.fxdfile = vfs.join(config.OVERLAY_DIR, 'disc-set', self.getmedia_id(self.device))
            else:
                self.fxdfile = vfs.splitext(file)[0]

        if overwrite == False:
            try:
                vfs.open(self.fxdfile + '.fxd')
                self.append = True
            except:
                pass
        else:
            self.append = False

        # XXX: add this back in without using parseMovieFile
        # if self.append == True and parseMovieFile(self.fxdfile + '.fxd', None, []) == []:
        #     raise FxdImdb_XML_Error("FXD file to be updated is invalid, please correct it.")

        if not vfs.isdir(vfs.dirname(self.fxdfile)):
            if vfs.dirname(self.fxdfile):
                os.makedirs(vfs.dirname(self.fxdfile))


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def setVideo(self, *videos, **mplayer_opt):
        """
        videos (tuple (type, id-ref, device, mplayer-opts, file/param) (multiple allowed),
        global_mplayer_opts
        Set media file(s) for fxd
        """
        if self.isdiscset == True:
            raise FxdImdb_XML_Error("<disc-set> already used, can't use both "+
                                    "<movie> and <disc-set>")

        if videos:
            for video in videos:
                self.video += [ video ]
        if mplayer_opt and 'mplayer_opt' in mpl_global_opt:
            self.mpl_global_opt = mplayer_opt['mplayer_opt']

    @benchmark(benchmarking & 0x40, benchmarkcall)
    def setVariants(self, *parts, **mplayer_opt):
        """
        variants/parts (tuple (name, ref, mpl_opts, sub, s_dev, audio, a_dev)),
        var_mplayer_opts
        Set Variants & parts
        """
        if self.isdiscset == True:
            raise FxdImdb_XML_Error("<disc-set> already used, can't use both "+
                                    "<movie> and <disc-set>")

        if mplayer_opt and 'mplayer_opt' in mpl_global_opt:
            self.varmpl_opt = (mplayer_opt['mplayer_opt'])
        for part in parts:
            self.variant += [ part ]


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def writeFxd(self):
        """Write fxd file"""
        #if fxdfile is empty, set it yourself
        if not self.fxdfile:
            self.setFxdFile()

        try:
            #should we add to an existing file?
            if self.append:
                if self.isdiscset:
                    self.update_discset()
                else:
                    self.update_movie()
            else:
                #fetch images
                self.fetch_image()
                #should we write a disc-set ?
                if self.isdiscset:
                    self.write_discset()
                else:
                    self.write_movie()

            #check fxd
            # XXX: add this back in without using parseMovieFile
            # if parseMovieFile(self.fxdfile + '.fxd', None, []) == []:
            #     raise FxdImdb_XML_Error("""FXD file generated is invalid, please "+
            #                             "post bugreport, tracebacks and fxd file.""")

        except (IOError, FxdImdb_IO_Error), error:
            raise FxdImdb_IO_Error('error saving the file: %s' % str(error))


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def setDiscset(self, device, regexp, *file_opts, **mpl_global_opt):
        """
        device (string), regexp (string), file_opts (tuple (mplayer-opts,file)),
        mpl_global_opt (string)
        Set media is dvd/vcd,
        """
        if len(self.video) != 0 or len(self.variant) != 0:
            raise FxdImdb_XML_Error("<movie> already used, can't use both "+
                                    "<movie> and <disc-set>")

        self.isdiscset = True
        if (not device and not regexp) or (device and regexp):
            raise FxdImdb_XML_Error("Can't use both media-id and regexp")

        self.device = device
        self.regexp = regexp

        for opts in file_opts:
            self.file_opts += [ opts ]

        if mpl_global_opt and 'mplayer_opt' in mpl_global_opt:
            self.mpl_global_opt = (mpl_global_opt['mplayer_opt'])


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def isDiscset(self):
        """Check if fxd file describes a disc-set, returns 1 for true, 0 for false
        None for invalid file"""
        try:
            file = vfs.open(self.fxdfile + '.fxd')
        except IOError:
            return None

        content = file.read()
        file.close()
        if content.find('</disc-set>') != -1:
            return 1
        return 0



#------ private functions below .....

    @benchmark(benchmarking & 0x40, benchmarkcall)
    def convert_entities(self, contents):
        s = contents.strip()
        s = s.replace('\n',' ')
        s = s.replace('  ',' ')
        s = s.replace('&','&amp;')
        s = s.replace('&amp;#','&#')
        s = s.replace('<','&lt;')
        s = s.replace('>','&gt;')
        s = s.replace('"','&quot;')
        return s

    @benchmark(benchmarking & 0x40, benchmarkcall)
    def write_discset(self):
        """Write a <disc-set> to a fresh file"""

        try:
            i = vfs.codecs_open( (self.fxdfile + '.fxd') , 'wb', encoding='utf-8')
        except IOError, error:
            raise FxdImdb_IO_Error("Writing FXD file failed : " + str(error))
            return

        i.write("<?xml version=\"1.0\" ?>\n<freevo>\n")
        i.write("  <copyright>\n" +
                "    The information in this file are from the Internet Movie Database (IMDb).\n" +
                "    Please visit http://www.imdb.com for more information.\n")
        if self.id:
            i.write("    <source url=\"http://www.imdb.com/title/tt%s\"/>\n" % self.id)
        i.write("  </copyright>\n")

        i.write("  <disc-set title=\"%s\">\n" % self.str2XML(self.title))
        i.write("    <disc")
        if self.device:
            i.write(" media-id=\"%s\"" % self.str2XML(self.getmedia_id(self.device)))
        elif self.regexp:
            i.write(" label-regexp=\"%s\"" % self.str2XML(self.regexp))
        if self.mpl_global_opt:
            i.write(" mplayer-options=\"%s\"" % self.str2XML(self.mpl_global_opt))
        i.write(">")
        if self.file_opts:
            i.write("\n")
            for opts in self.file_opts:
                mplopts, fname = opts
                i.write("      <file-opt mplayer-options=\"%s\">" % self.str2XML(mplopts))
                i.write("%s</file-opt>\n" % self.str2XML(fname))
            i.write("    </disc>\n")
        else: i.write("    </disc>\n")

        if self.image:
            i.write("    <cover-img source=\"%s\">" % self.str2XML(self.image_url))
            i.write("%s</cover-img>\n" % self.str2XML(self.image))
        i.write(self.print_info())
        i.write("  </disc-set>\n")
        i.write("</freevo>\n")

        # now we need to rebuild the cache
        util.touch(os.path.join(config.FREEVO_CACHEDIR, 'freevo-rebuild-database'))


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def write_movie(self):
        """Write <movie> to fxd file"""

        try:
            i = vfs.codecs_open((self.fxdfile+'.fxd') , 'w', encoding='utf-8')
        except IOError, error:
            raise FxdImdb_IO_Error("Writing FXD file failed : " + str(error))
            return

        #header
        i.write("<?xml version=\"1.0\" ?>\n<freevo>\n")
        i.write("  <copyright>\n")
        i.write("    The information in this file are from the Internet Movie Database (IMDb).\n")
        i.write("    Please visit http://www.imdb.com for more information.\n")
        if self.id:
            i.write("    <source url=\"http://www.imdb.com/title/tt%s\"/>\n" % self.id)
        i.write("  </copyright>\n")
        # write movie
        i.write("  <movie title=\"%s\">\n" % self.str2XML(self.title))
        #image
        if self.image:
            i.write("    <cover-img source=\"%s\">" % self.str2XML(self.image_url))
            i.write("%s</cover-img>\n" % self.str2XML(self.image))
        #video
        if self.mpl_global_opt:
            i.write("    <video mplayer-options=\"%s\">\n" % self.str2XML(self.mpl_global_opt))
        else: i.write("    <video>\n")
        # videos
        i.write(self.print_video())
        i.write('    </video>\n')
        #variants <varinats !!
        if len(self.variant) != 0:
            i.write('    <variants>\n')
            i.write(self.print_variant())
            i.write('    </variants>\n')

        #info
        i.write(self.print_info())
        #close tags
        i.write('  </movie>\n')
        i.write('</freevo>\n')

        util.touch(os.path.join(config.FREEVO_CACHEDIR, 'freevo-rebuild-database'))


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def update_movie(self):
        """Updates an existing file, adds extra dvd|vcd|file and variant tags"""
        passedvid = False
        #read existing file in memory
        try:
            file = vfs.open(self.fxdfile + '.fxd')
        except IOError, error:
            raise FxdImdb_IO_Error("Updating FXD file failed : " + str(error))

        content = file.read()
        file.close()

        if content.find('</video>') == -1:
            raise FxdImdb_XML_Error("FXD cannot be updated, doesn't contain <video> tag")

        regexp_variant_start = re.compile('.*<variants>.*', re.I)
        regexp_variant_end = re.compile(' *</variants>', re.I)
        regexp_video_end  = re.compile(' *</video>', re.I)

        file = vfs.open(self.fxdfile + '.fxd', 'w')


        for line in content.split('\n'):
            if passedvid == True and content.find('<variants>') == -1:
                #there is no variants tag
                if len(self.variant) != 0:
                    file.write('    <variants>\n')
                    file.write(self.print_variant())
                    file.write('    </variants>\n')
                file.write(line + '\n')
                passedvid = False

            elif regexp_video_end.match(line):
                if len(self.video) != 0:
                    file.write(self.print_video())
                file.write(line + '\n')
                passedvid = True

            elif regexp_variant_end.match(line):
                if len(self.variant) != 0:
                    file.write(self.print_variant())
                file.write(line + '\n')

            else: file.write(line + '\n')

        file.close()
        util.touch(os.path.join(config.FREEVO_CACHEDIR, 'freevo-rebuild-database'))



    @benchmark(benchmarking & 0x40, benchmarkcall)
    def update_discset(self):
        """Updates an existing file, adds extra disc in discset"""

        #read existing file in memory
        try:
            file = vfs.open(self.fxdfile + '.fxd')
        except IOError, error:
            raise FxdImdb_IO_Error("Updating FXD file failed : " + str(error))
            return

        content = file.read()
        file.close()

        if content.find('</disc-set>') == -1:
            raise FxdImdb_XML_Error("FXD file cannot be updated, doesn't contain <disc-set>")

        regexp_discset_end  = re.compile(' *</disc-set>', re.I)

        file = vfs.open(self.fxdfile + '.fxd', 'w')

        for line in content.split('\n'):

            if regexp_discset_end.match(line):
                file.write("    <disc")
                if self.device:
                    file.write(" media-id=\"%s\"" % self.str2XML(self.getmedia_id(self.device)))
                elif self.regexp:
                    file.write(" label-regexp=\"%s\"" % self.str2XML(self.regexp))
                if self.mpl_global_opt:
                    file.write(" mplayer-options=\"%s\">" % self.str2XML(self.mpl_global_opt))
                else: file.write(">")
                #file-opts
                if self.file_opts:
                    file.write("\n")
                    for opts in self.file_opts:
                        mplopts, fname = opts
                        file.write("      <file-opt mplayer-options=\"%s\">" % self.str2XML(mplopts))
                        file.write("%s</file-opt>\n" % self.str2XML(fname))
                    file.write("    </disc>\n")
                else: file.write("    </disc>\n")
                file.write(line + '\n')

            else: file.write(line + '\n')

        file.close()
        util.touch(os.path.join(config.FREEVO_CACHEDIR, 'freevo-rebuild-database'))


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def parsesearchdata(self, results, url=None, id=0):
        """
        results (imdb html page), imdb_id

        @returns: tuple of (title, info(dict), image_urls)
        """
        _debug_('parsesearchdata(results=%r, url=%r, id=%r)' % (results, url, id))

        self.id_list = []
        m = re.compile('/title/tt([0-9]*)/')
        y = re.compile('\(([^)]+)\)')
        try:
            soup = BeautifulSoup(results.read(), convertEntities='xml')
        except HTMLParser.HTMLParseError, why:
            traceback.print_exc()
            _debug_('Cannot parse %r: %s' % (url, why), DWARNING)
            return self.id_list
        items = soup.findAll('a', href=re.compile('/title/tt'))
        ids = set([])
        for item in items:
            idm = m.search(item['href'])
            if not idm:
                continue
            if isinstance(item.next.next, NavigableString):
                yrm = y.findall(item.next.next)

            id = idm.group(1)
            name = item.string
            # skip empty names
            if not name:
                continue
            # skip duplicate ids
            if id in ids:
                continue
            ids.add(id)
            year = len(yrm) > 0 and yrm[0] or '0000'
            type = len(yrm) > 1 and yrm[1] or ''
            #print 'url', item['href']
            #print item.parent.findChildren(text=re.compile('[^ ]'))
            self.id_list += [ ( id, name, year, type ) ]

        for item in self.id_list:
            _debug_('%r' % (item,), 2)
        return self.id_list


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def find_episode(self, results, id, season, episode):
        """results (imdb html page)
        Returns a new id for getIMDBid with TV series episode data
        """
        try:
            soup = BeautifulSoup(results.read(), convertEntities='xml')
        except UnicodeDecodeError:
            print "Unicode error; check that /usr/lib/python2.x/site.py has the correct default encoding"
            pass

        m = re.compile('.*Season %s, Episode %s.*\/tt([0-9]+)' % (season, episode))

        for episode in soup.findAll('h3'):
            info = m.search(str(episode))
            if info:
                episodeid = info.group(1)
                _debug_('episodeid=%r' % (episodeid,))
                return episodeid

        _debug_('id=%r' % (id,))
        return id


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def impawardsimages(self, title, year):
        """Generate URLs to the impawards movie posters and add them to the
        global image_urls array."""

        # Format of an impawards.com image URL:
        #     http://www.impawards.com/<year>/posters/<title>.jpg
        #
        # Some special characters like: blanks, ticks, ':', ','... have to be replaced
        imp_image_name = title.lower()
        imp_image_name = imp_image_name.replace(u' ', u'_')
        imp_image_name = imp_image_name.replace(u"'", u'')
        imp_image_name = imp_image_name.replace(u':', u'')
        imp_image_name = imp_image_name.replace(u',', u'')
        imp_image_name = imp_image_name.replace(u';', u'')
        imp_image_name = imp_image_name.replace(u'.', u'')

        # build up an array with all kind of image urls
        imp_image_urls = [ ]
        imp_base_url   = 'http://www.impawards.com/%s/posters' % year

        # add the normal poster URL to image_urls
        imp_image_url   = '%s/%s.jpg' % (imp_base_url, imp_image_name)
        imp_image_urls += [ imp_image_url ]

        # add the xxl poster URL to image_urls
        imp_image_url   = '%s/%s_xlg.jpg' % (imp_base_url, imp_image_name)
        imp_image_urls += [ imp_image_url ]

        # add the ver1 poster URL in case no normal version exists
        imp_image_url   = '%s/%s_ver1.jpg' % (imp_base_url, imp_image_name)
        imp_image_urls += [ imp_image_url ]

        # add the xxl ver1 poster URL
        imp_image_url   = '%s/%s_ver1_xlg.jpg' % (imp_base_url, imp_image_name)
        imp_image_urls += [ imp_image_url ]

        # check for valid URLs and add them to self.image_urls
        for imp_image_url in imp_image_urls:

            #print "IMPAWARDS: Checking image URL %s" % imp_image_url
            try:
                imp_req = urllib2.Request(imp_image_url, txdata, txheaders)

                # an url is valid if the returned content-type is 'image/jpeg'
                imp_r     = urllib2.urlopen(imp_req)
                imp_ctype = imp_r.info()['Content-Type']
                imp_r.close()

                #print "IMPAWARDS: Found content-type %s for url %s" % (imp_ctype, imp_image_url)
                if (imp_ctype == 'image/jpeg'):
                    self.image_urls += [ imp_image_url ]

            except:
                pass


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def impawards(self, host, path):
        """parser for posters from www.impawards.com. TODO: check for licences
        of each poster and add all posters"""

        path = '%s/posters/%s.jpg' % (path[:path.rfind('/')], path[path.rfind('/')+1:path.rfind('.')])
        return [ 'http://%s%s' % (host, path) ]


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def fetch_image(self):
        """Fetch the best image"""
        _debug_('fetch_image=%s' % (self.image_urls))

        image_len = 0
        if len(self.image_urls) == 0: # No images
            return

        for image in self.image_urls:
            try:
                _debug_('image=%s' % (image))
                # get sizes of images
                req = urllib2.Request(image, txdata, txheaders)
                r = urllib2.urlopen(req)
                length = int(r.info()['Content-Length'])
                r.close()
                if length > image_len:
                    image_len = length
                    self.image_url = image
            except:
                pass
        if not self.image_url:
            print "Image downloading failed"
            return

        self.image = (self.fxdfile + '.jpg')

        req = urllib2.Request(self.image_url, txdata, txheaders)
        r = urllib2.urlopen(req)
        i = vfs.open(self.image, 'w')
        i.write(r.read())
        i.close()
        r.close()

        # try to crop the image to avoid borders by imdb
        try:
            import kaa.imlib2 as Image
            image = Image.open(filename)
            width, height = image.size
            image.crop((2,2,width-4, height-4)).save(filename)
        except:
            pass

        self.image = vfs.basename(self.image)

        _debug_('Downloaded cover image from %s' % (self.image_url))
        print "Freevo knows nothing about the copyright of this image, please"
        print "go to %s to check for more information about private." % self.image_url
        print "use of this image"


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def str2XML(self, line):
        """return a valid XML string"""
        try:
            s = Unicode(line)
            # remove leading and trailing spaces
            s = s.strip()
            # remove leading and trailing quotes
            #s = s.strip('\'"')
            # remove quotes
            s = re.sub('"', '', s)

            if s[:5] == u'&#34;':
                s = s[5:]
            if s[-5:] == u'&#34;':
                s = s[:-5]
            if s[:6] == u'&quot;':
                s = s[6:]
            if s[-6:] == u'&quot;':
                s = s[:-6]
            # replace all & to &amp; ...
            s = s.replace(u"&", u"&amp;")
            # ... but this is wrong for &#
            s = s.replace(u"&amp;#", u"&#")

            return s
        except:
            return Unicode(line)


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def getmedia_id(self, drive):
        """drive (device string)
        return a unique identifier for the disc"""

        if not vfs.exists(drive):
            return drive
        (type, id) = mmpython.cdrom.status(drive)
        return id


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def print_info(self):
        """return info part for FXD writing"""
        ret = u''
        if self.info:
            ret = u'    <info>\n'
            for k in self.info.keys():
                ret += u'      <%s>' % k + Unicode(self.info[k]) + '</%s>\n' % k
            ret += u'    </info>\n'
        return ret


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def print_video(self):
        """return info part for FXD writing"""
        ret = ''
        for vid in self.video:
            type, idref, device, mpl_opts, fname = vid
            ret += '      <%s' % self.str2XML(type)
            ret += ' id=\"%s\"' % self.str2XML(idref)
            if device: ret += ' media-id=\"%s\"' % self.str2XML(self.getmedia_id(device))
            if mpl_opts: ret += ' mplayer-options=\"%s\">' % self.str2XML(mpl_opts)
            else: ret += '>'
            ret += '%s' % self.str2XML(fname)
            ret += '</%s>\n' % self.str2XML(type)
        return ret


    @benchmark(benchmarking & 0x40, benchmarkcall)
    def print_variant(self):
        """return info part for FXD writing"""
        ret = ''
        for x in range(len(self.variant)):
            name, idref, mpl_opts, sub, s_dev, audio, a_dev = self.variant[x]

            ret += '      <variant name=\"%s\"' % self.str2XML(name)
            if self.varmpl_opt:
                ret += ' mplayer-options=\"%s\">\n' % self.str2XML(self.varmpl_opt)
            else: ret += '>\n'
            ret += '         <part ref=\"%s\"' % self.str2XML(idref)
            if mpl_opts: ret += ' mplayer-options=\"%s\">\n' % self.str2XML(mpl_opts)
            else: ret += ">\n"
            if sub:
                ret += '          <subtitle'
                if s_dev: ret += ' media-id=\"%s\">' % self.str2XML(self.getmedia_id(s_dev))
                else: ret += '>'
                ret += '%s</subtitle>\n' % self.str2XML(sub)
            if audio:
                ret += '          <audio'
                if a_dev: ret += ' media-id=\"%s\">' % self.str2XML(self.getmedia_id(a_dev))
                else: ret += '>'
                ret += '%s</audio>\n' % self.str2XML(audio)
            ret += '        </part>\n'
            ret += '      </variant>\n'

        return ret


#--------- Exception class

class Error(Exception):
    """Base class for exceptions in Imdb_Fxd"""
    @benchmark(benchmarking & 0x40, benchmarkcall)
    def __str__(self):
        return self.message
    @benchmark(benchmarking & 0x40, benchmarkcall)
    def __init__(self, message):
        self.message = message

class FxdImdb_Error(Error):
    """used to raise exceptions"""
    pass

class FxdImdb_XML_Error(Error):
    """used to raise exceptions"""
    pass

class FxdImdb_IO_Error(Error):
    """used to raise exceptions"""
    pass

class FxdImdb_Net_Error(Error):
    """used to raise exceptions"""
    pass

#------- Helper functions for creating tuples - these functions are classless

@benchmark(benchmarking & 0x40, benchmarkcall)
def makeVideo(type, id_ref, file, **values):
    """Create a video tuple"""
    device = mplayer_opt = None
    types = ['dvd', 'file', 'vcd']
    if type == None or id_ref == None or file == None:
        raise FxdImdb_XML_Error("Required values missing for tuple creation")

    if type not in types:
        raise FxdImdb_XML_Error("Invalid type passed to makeVideo")

    if values:
        #print values
        if 'device' in values: device = values['device']
        if 'mplayer_opt' in values: mplayer_opt = values['mplayer_opt']

    file = relative_path(file)
    t = type, id_ref, device, mplayer_opt, file
    return t

@benchmark(benchmarking & 0x40, benchmarkcall)
def makePart(name, id_ref, **values):
    """Create a part tuple"""
    mplayer_opt = sub = s_dev = audio = a_dev = None

    if id_ref == None or name == None:
        raise FxdImdb_XML_Error("Required values missing for tuple creation")

    if values:
        if 'mplayer_opt' in values: mplayer_opt = values['mplayer_opt']
        if 'sub' in values: sub = values['sub']
        if 's_dev' in values: s_dev = values['s_dev']
        if 'audio' in values: audio = values['audio']
        if 'a_dev' in values: a_dev = values['a_dev']
    if a_dev: audio = relative_path(audio)
    if s_dev: sub = relative_path(sub)
    t = name, id_ref, mplayer_opt, sub, s_dev, audio, a_dev
    return t

@benchmark(benchmarking & 0x40, benchmarkcall)
def makeFile_opt(mplayer_opt, file):
    """Create a file_opt tuple"""
    if mplayer_opt == None or file == None:
        raise FxdImdb_XML_Error("Required values missing for tuple creation")
    file = relative_path(file)
    t = mplayer_opt, file

    return t

#--------- classless private functions

@benchmark(benchmarking & 0x40, benchmarkcall)
def relative_path(filename):
    """return the relative path to a mount point for a file on a removable disc"""
    from os.path import isabs, ismount, split, join

    if not isabs(filename) and not ismount(filename): return filename
    drivepaths = []
    for item in config.REMOVABLE_MEDIA:
        drivepaths.append(item.mountdir)
    for path in drivepaths:
        if filename.find(path) != -1:
            head = filename
            tail = ''
            while (head != path):
                x = split(head)
                head = x[0]
                if x[0] == '/' and x[1] == '' : return filename
                elif tail == '': tail = x[1]
                else: tail = join(x[1], tail)

            if head == path: return tail

    return filename


@benchmark(benchmarking & 0x40, benchmarkcall)
def point_maker(matching):
    return '%s.%s' % (matching.groups()[0], matching.groups()[1])
