# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# Plugin for FILMAFFINITY support
# -----------------------------------------------------------------------
# $Id$
# Version: 080607_01
#
# Notes: FilmAffinity plugin. You can add FilmAffinity.com informations for video items
#        with the plugin
#        Activate with: plugin.activate('video.filmaffinity')
#        And add the following lines to your configuration file:
#          FILMAFFINITY_AUTOACCEPT_SINGLE_HIT = True
#          It uses also directly the variables:
#              - FILMAFFINITY_REMOVE_FROM_LABEL
#              - FILMAFFINITY_REMOVE_FROM_SEARCHSTRING
#          as the same words shall be removed also for FilmAffinity.
#        You can also set filmaffinity_search on a key (e.g. '1') by setting
#        EVENTS['menu']['1'] = Event(MENU_CALL_ITEM_ACTION, arg='filmaffinity_search_or_cover_search')
#
# Todo:  - Update existing FXD file
#        - DVD/VCD support (discset ??)
#
# Author: S. FABRE for Biboobox, http://www.lahiette.com/biboobox
# RE-Author: Jose Maria Franco Fraiz
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
# ----------------------------------------------------------------------- */
import logging
logger = logging.getLogger("freevo.video.plugins.filmaffinity")

import re
import socket
socket.setdefaulttimeout(30.0)
import urllib2, urlparse, commands
import sys
import os
import traceback

import menu
import config
import plugin
import time
from util import htmlenties2txt
from util import fxdparser
from gui.PopupBox import PopupBox
from util.fxdimdb import makeVideo, point_maker

#beautifulsoup module
from BeautifulSoup import BeautifulSoup

# headers for urllib2
txdata = None
txheaders = {
    'User-Agent': 'freevo (%s)' % sys.platform,
    'Accept-Language': 'es-es',
}

class PluginInterface(plugin.ItemPlugin):
    """
       This plugin obtains movie information in Spanish from the FilmAffinity
       website

       Configuration::

           plugin.activate('video.filmaffinity')
           FILMAFFINITY_REMOVE_FROM_LABEL = ('\(.*?\)', '\[.*?\]', 'cd[0-9]+(-[0-9])?', 'title[0-9]+', 'by .*$')
           FILMAFFINITY_REMOVE_FROM_SEARCHSTRING = ('spanish','xvid','dvdrip','parte','[0-9]*','dvdscreener','mp3')
           FILMAFFINITY_AUTOACCEPT_SINGLE_HIT = True
    """

    def __init__(self, license=None):
        """Initialise class instance"""

        # these are considered as private variables - don't mess with them unless
        # no other choise is given
        # fyi, the other choice always exists: add a subroutine or ask :)
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        plugin.ItemPlugin.__init__(self)

    def config(self):
        return [
            ('FILMAFFINITY_REMOVE_FROM_LABEL', ('\(.*?\)', '\[.*?\]', 'cd[0-9]+(-[0-9])?', 'title[0-9]+', 'by .*$'), _('Remove matching of this regexps from item name')),
            ('FILMAFFINITY_REMOVE_FROM_SEARCHSTRING', ('spanish','xvid','dvdrip','parte','[0-9]*','dvdscreener','mp3'), _('Remove matching of this regexps from search string')),
            ('FILMAFFINITY_AUTOACCEPT_SINGLE_HIT', True, _('Accept search automatically if it has only one result'))
            ]

    def initmyself(self):
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

        #image_url_handler stuff
        self.image_url_handler = {}

    def searchFilmAffinity(self, name):
        """name (string), returns id list

        Search for name and returns an id list with tuples:
        (id , name, year)"""
        # Clean internal variables
        self.initmyself()
        self.filmaffinity_id_list = []

        quoted_name = urllib2.quote(name.strip())

        regexp_tag = re.compile('<[^>]+>', re.I)
        logger.debug('Request with: %s', quoted_name)
        url = 'http://www.filmaffinity.com/es/search.php?stext=%s&stype=title' % quoted_name
        req = urllib2.Request(url, txdata, txheaders)
        searchstring = name

        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, error:
            raise FxdFilmaffinity_Net_Error(_('Connection error: ') + error)
            exit

        regexp_getmultiple = re.compile('.*<b><a href="(/es/film.*\.html)">(.*?)</a></b>\s*\(([0-9]{4})\)\s*', re.I)
        regexp_getsingle = re.compile('^<meta name="keywords" content="movie', re.I)
        regexp_geturl = re.compile('.*<a href="/es/.*\.php\?movie_id=([0-9]*)',re.I)
        multiple = True

        for line in response.read().split("\n"):
            #print line
            if multiple:
                mm = regexp_getmultiple.match(line)
                if mm:
                    #print "Found film in line: %s" % line
                    link = mm.group(1)
                    name = mm.group(2)
                    year = mm.group(3)
                    self.filmaffinity_id_list += [ (link, name, year) ]
                ms = regexp_getsingle.match(line)
                if ms: multiple = False
            else:
                mu = regexp_geturl.match(line)
                if mu:
                    link = "/es/film" + mu.group(1) + ".html"
                    self.filmaffinity_id_list += [ (link, name, '') ]
                    break

        return self.filmaffinity_id_list

    def guessFilmAffinity(self, filename, label=False):
        """Guess possible movies from filename. Same return as searchFilmAffinity"""
        name = filename

        for r in config.FILMAFFINITY_REMOVE_FROM_LABEL:
            name = re.sub(r, '', name.lower())

        name = vfs.basename(vfs.splitext(name)[0])
        name = re.sub('([a-z])([A-Z])', point_maker, name)
        name = re.sub('([a-zA-Z])([0-9])', point_maker, name)
        name = re.sub('([0-9])([a-zA-Z])', point_maker, name.lower())
        name = re.sub(',', ' ', name)

        parts = re.split("[\._' -]", name)
        name = ''

        for p in parts:
            if not p.lower() in config.FILMAFFINITY_REMOVE_FROM_SEARCHSTRING and \
                not re.search('[^0-9A-Za-z]', p):
                # originally: not re.search(p, '[A-Za-z]'):
                # not sure what's meant with that
                name += '%s ' % p

        return self.searchFilmAffinity(name)

    def getFilmAffinityPage(self, url):
        """url
        Set an filmaffinity number for object, and fetch data"""

        self.myurl = 'http://www.filmaffinity.com/' + urllib2.quote(urllib2.unquote(url))
        logger.debug("Now trying to get %s", self.myurl)
        req = urllib2.Request(self.myurl, txdata, txheaders)

        try:
            idpage = urllib2.urlopen(req)
        except urllib2.HTTPError, error:
            raise FxdAllocine_Net_Error(_('Connection error: ') + error)
            return None

        #print "Response: %s" % idpage.read()
        self.parsedata(idpage, id)
        idpage.close()


    def setFxdFile(self, fxdfilename=None, overwrite=False):
        """
        setFxdFile (string, full path)
        Set fxd file to write to, may be omitted, may be an existing file
        (data will be added) unless overwrite = True
        """

        if fxdfilename:
            if vfs.splitext(fxdfilename)[1] == '.fxd':
                self.fxdfile = vfs.splitext(fxdfilename)[0]
            else: self.fxdfile = fxdfilename

        else:
            if self.isdiscset:
                self.fxdfile = vfs.join(config.OVERLAY_DIR, 'disc-set', self.getmedia_id(self.device))
            else:
                self.fxdfile = vfs.splitext(file)[0]

        if not overwrite:
            try:
                vfs.open(self.fxdfile + '.fxd')
                self.append = True
            except:
                pass
        else:
            self.append = False

        # XXX: add this back in without using parseMovieFile
        # if self.append and \
        #    parseMovieFile(self.fxdfile + '.fxd', None, []) == []:
        #     raise FxdAllocine_XML_Error("FXD file to be updated is invalid, please correct it.")

        if not vfs.isdir(vfs.dirname(self.fxdfile)):
            if vfs.dirname(self.fxdfile):
                os.makedirs(vfs.dirname(self.fxdfile))

    def filmaffinity_get_disc_searchstring(self, item):
        name = item.media.label
        name = re.sub('([a-z])([A-Z])', point_maker, name)
        name = re.sub('([a-zA-Z])([0-9])', point_maker, name)
        name = re.sub('([0-9])([a-zA-Z])', point_maker, name.lower())
        parts = re.split("[\._' -]", name)

        name = ''
        for p in parts:
            if p:
                name += '%s ' % p
        if name:
            return name[:-1]
        else:
            return ''


    def actions(self, item):
        self.item = item

        if item.type == 'video' and (not item.files or not item.files.fxd_file):
            if item.mode == 'file' or (item.mode in ('dvd', 'vcd') and item.info.has_key('tracks')
                    and not item.media):
                self.disc_set = False
                return [ (self.filmaffinity_search , _('Search in FilmAffinity'),
                    'filmaffinity_search_or_cover_search') ]

            elif item.mode in ('dvd', 'vcd') and item.info.has_key('tracks'):
                self.disc_set = True
                s = self.filmaffinity_get_disc_searchstring(self.item)
                if s:
                    return [ (self.filmaffinity_search , _('Search in FilmAffinity [%s]') % s,
                        'filmaffinity_search_or_cover_search') ]

        if item.type == 'dir' and item.media and item.media.mountdir.find(item.dir) == 0:
            self.disc_set = True
            s = self.filmaffinity_get_disc_searchstring(self.item)
            if s:
                return [ (self.filmaffinity_search , _('Search in FilmAffinity [%s]') % s,
                    'filmaffinity_search_or_cover_search') ]
        return []


    def filmaffinity_search(self, arg=None, menuw=None):
        """
        search filmaffinity for this item
        """
        box = PopupBox(text=_('Searching in FilmAffinity...'))
        box.show()

        items = []

        try:
            duplicates = []
            if self.disc_set:
                self.searchstring = self.item.media.label
            else:
                self.searchstring = self.item.name

            for id, name, year in self.guessFilmAffinity(self.searchstring, self.disc_set):
                try:
                    uname = Unicode(name)
                    for i in self.item.parent.play_items:
                        if i.name == uname:
                            if not i in duplicates:
                                duplicates.append(i)
                except:
                    pass
                items.append(menu.MenuItem('%s (%s)' % (htmlenties2txt(name), year),
                    self.filmaffinity_create_fxd, (id, year)))
        except:
            box.destroy()
            box = PopupBox(text=_('Connection error: Probably connection timeout, try again'))
            box.show()
            time.sleep(2)
            box.destroy()
            traceback.print_exc()
            return

        box.destroy()
        if config.FILMAFFINITY_AUTOACCEPT_SINGLE_HIT and len(items) == 1:
            self.filmaffinity_create_fxd(arg=items[0].arg, menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('FILMAFFINITY Query'), items)
            menuw.pushmenu(moviemenu)
            return

        box = PopupBox(text=_('No info available'))
        box.show()
        time.sleep(2)
        box.destroy()
        return


    def filmaffinity_menu_back(self, menuw):
        """
        check how many menus we have to go back to see the item
        """
        import directory

        # check if we have to go one menu back (called directly) or
        # two (called from the item menu)
        back = 1
        if menuw.menustack[-2].selected != self.item:
            back = 2

        # maybe we called the function directly because there was only one
        # entry and we called it with an event
        if menuw.menustack[-1].selected == self.item:
            back = 0

        # update the directory
        if directory.dirwatcher:
            directory.dirwatcher.scan()

        # go back in menustack
        for i in range(back):
            menuw.delete_menu()


    def filmaffinity_create_fxd(self, arg=None, menuw=None):
        """
        create fxd file for the item
        """
        box = PopupBox(text=_('Fetching movie information'))
        box.show()

        #if this exists we got a cdrom/dvdrom
        if self.item.media and self.item.media.devicename:
            devicename = self.item.media.devicename
        else:
            devicename = None

        self.getFilmAffinityPage(arg[0])

        if self.disc_set:
            self.setDiscset(devicename, None)
        else:
            if self.item.subitems:
                for i in range(len(self.item.subitems)):
                    video = makeVideo('file', 'f%s' % i,
                                      os.path.basename(self.item.subitems[i].filename),
                                      device=devicename)
                    self.setVideo(video)
            else:
                video = makeVideo('file', 'f1', os.path.basename(self.item.filename),
                                  device=devicename)
                self.setVideo(video)
            self.setFxdFile(os.path.splitext(self.item.filename)[0])

        self.writeFxd()
        self.filmaffinity_menu_back(menuw)
        box.destroy()

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
                else: self.update_movie()
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

        except (IOError, FxdFilmaffinity_IO_Error), error:
            raise FxdFilmaffinity_IO_Error('error saving the file: %s' % str(error))


    def setDiscset(self, device, regexp, *file_opts, **mpl_global_opt):
        """
        device (string), regexp (string), file_opts (tuple (mplayer-opts,file)),
        mpl_global_opt (string)
        Set media is dvd/vcd,
        """
        if len(self.video) != 0 or len(self.variant) != 0:
            raise FxdFilmaffinity_XML_Error("<movie> already used, can't use both "+
                                    "<movie> and <disc-set>")

        self.isdiscset = True
        if (not device and not regexp) or (device and regexp):
            raise FxdFilmaffinity_XML_Error("Can't use both media-id and regexp")

        self.device = device
        self.regexp = regexp

        for opts in file_opts:
            self.file_opts += [ opts ]

        if mpl_global_opt and 'mplayer_opt' in mpl_global_opt:
            self.mpl_global_opt = (mpl_global_opt['mplayer_opt'])


    def isDiscset(self):
        """Check if fxd file describes a disc-set, returns 1 for true, 0 for false
        None for invalid file"""
        try:
            file = vfs.open(self.fxdfile + '.fxd')
        except IOError:
            return None

        content = file.read()
        file.close()
        if content.find('</disc-set>') != -1: return 1
        return 0

#------ private functions below .....

    def write_discset(self):
        """Write a <disc-set> to a fresh file"""
        print "Discset not supported for the moment... Sorry"

    def write_fxd_copyright(self, fxd, node):
        fxd.setcdata(node, "The information in this file are from Filmaffinity.com.\n"+
                           "Please visit http://www.filmaffinity.com for more informations.\n")
        fxd.add(fxd.XMLnode('source', [('url', "%s" % self.myurl)]), node, None)

    def write_fxd_video(self, fxd, node):
        fxd.setattr(node, 'title', self.title)
        fxd.add(fxd.XMLnode('cover-img', (('source', self.image_url), ("test", "test")), self.image), node, None)
        videonode = fxd.XMLnode('video')
        fxd.add(videonode, node)
        if self.item.subitems:
            for i in range(len(self.item.subitems)):
                fxd.add(fxd.XMLnode('file', [('id', 'f%s' % i)], os.path.basename(self.item.subitems[i].filename)), videonode, None)
        else:
            fxd.add(fxd.XMLnode('file', [('id', 'f1')], os.path.basename(self.item.filename)), videonode, None)
        infonode = fxd.XMLnode('info')
        fxd.add(infonode, node)
        if self.info:
            for k in self.info.keys():
                fxd.add(fxd.XMLnode(k, [], self.info[k]), infonode, None)

    def write_movie(self):
        """Write <movie> to fxd file"""
        try:
            parser = fxdparser.FXD(self.fxdfile + '.fxd')
            parser.set_handler('copyright', self.write_fxd_copyright, 'w', True)
            parser.set_handler('movie', self.write_fxd_video, 'w', True)
            parser.save()
        except:
            print "fxd file %s corrupt" % self.fxdfile
            traceback.print_exc()

    def update_movie(self):
        """Updates an existing file, adds exftra dvd|vcd|file and variant tags"""
        print "Update not supported for the moment... Sorry"

    def update_discset(self):
        """Updates an existing file, adds extra disc in discset"""
        print "Update not supported for the moment... Sorry"

    def parsedata(self, results, id=0):
        """results (filmaffinity html page), filmaffinity_id
        Returns tuple of (title, info(dict), image_url)"""

        dvd = 0
        inside_plot = None
        self.image_url = ''

        soup = BeautifulSoup(results.read(), convertEntities='html')
        results.close()

        img = soup.find('img',src=re.compile('.*-full\.jpg$'))
        if img:
            trs = img.findParent('table').findAll('tr')
            img_ratings = soup.find('img',src=re.compile('imgs/ratings'))
        else:
            trs = None
            img_ratings = None

#       _debug_("Tag %s" % trs)

        self.title = soup.find('img', src=re.compile('movie.gif$')).nextSibling.string.strip().encode('latin-1')
        self.info['director'] = stripTags(soup.find(text='DIRECTOR').findParent('table').td.nextSibling.nextSibling.contents).strip()
        self.info['year'] = soup.find(text='AÑO').parent.parent.parent.table.td.string.strip()
        self.info['country'] = soup.find('img', src=re.compile('^\/imgs\/countries\/'))['title'].strip()

        if img_ratings:
            self.info['rating'] = img_ratings['alt'] + ' (' + trs[1].td.string + '/' + trs[4].td.string.strip('(')

        self.info['tagline'] = soup.find(text='TÍTULO ORIGINAL').findParent('table').td.nextSibling.nextSibling.b.string.strip().encode('latin-1')
        self.info['actor']= stripTags(soup.find(text='REPARTO').parent.parent.nextSibling.nextSibling.contents).strip()

        sinopsis = soup.find(text='SINOPSIS')
        if sinopsis:
            td = sinopsis.findNext('td')
            logger.debug('PLOT: %s', td.contents)
            self.info['plot'] = '\n'.join([td.string for td in td.findAll(text=True)]).strip().encode('latin-1')

        genero = soup.find(text='GÉNERO')
        if genero:
            td = genero.findNext('td')

            logger.debug('GENRE: %s', td.contents)
            
            self.info['genre'] = '/'.join([td.string for td in td.findAll('a')]).strip().encode('latin-1')

        #self.imagefile = self.tmppath + vfs.basename(self.title)
        # filmaffinity renders two types of html code. The new one
        #  with an <a> tag to show a big image and the old one without it
        #
        if img:
            if img.parent.has_key('href'):
                self.image_url = img.parent['href']
            else:
                self.image_url = img['src']

        return (self.title, self.info, self.image_url)

    def fetch_image(self):
        """Fetch the best image"""

        if (len(self.image_url) == 0): # No images
            return

        self.image = (self.fxdfile + '.jpg')

        req = urllib2.Request(self.image_url, txdata, txheaders)
        r = urllib2.urlopen(req)
        i = vfs.open(self.image, 'w')
        i.write(r.read())
        i.close()
        r.close()

        print "Downloaded cover image from Filmaffinity.com"
        print "Freevo knows nothing about the copyright of this image, please"
        print "go to Filmaffinity.com to check for more informations about private."
        print "use of this image"

    def setVideo(self, *videos, **mplayer_opt):
        """
        videos (tuple (type, id-ref, device, mplayer-opts, file/param) (multiple allowed),
        global_mplayer_opts
        Set media file(s) for fxd
        """
        if self.isdiscset:
            raise FxdFilmaffinity_XML_Error("<disc-set> already used, can't use both "+
                                    "<movie> and <disc-set>")

        if videos:
            for video in videos:
                self.video += [ video ]
        if mplayer_opt and 'mplayer_opt' in mpl_global_opt:
            self.mpl_global_opt = mplayer_opt['mplayer_opt']


class Error(Exception):
    """Base class for exceptions in Filmaffinity_Fxd"""
    def __str__(self):
        return self.message
    def __init__(self, message):
        self.message = message

class FxdFilmaffinity_Error(Error):
    """used to raise exceptions"""
    pass

class FxdFilmaffinity_XML_Error(Error):
    """used to raise exceptions"""
    pass

class FxdFilmaffinity_IO_Error(Error):
    """used to raise exceptions"""
    pass

class FxdFilmaffinity_Net_Error(Error):
    """used to raise exceptions"""
    pass

def stripTags(c):
    str_list = []
    for num in xrange(len(c)):
        str_list.append(c[num].string)
    return ''.join(str_list)
