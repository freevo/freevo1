# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plugin for MOVIECOVERS support
# -----------------------------------------------------------------------
# $Id$
# Version: 080607_01
#
# Notes: Moviecovers plugin. You can add Moviecovers.com informations for video items
#        with the plugin
#        Activate with: plugin.activate('video.moviecovers')
#        And add the following lines to your configuration file:
#          MOVIECOVERS_AUTOACCEPT_SINGLE_HIT = True
#          It uses also directly the variables:
#              - ALLOCINE_REMOVE_FROM_LABEL
#              - ALLOCINE_REMOVE_FROM_SEARCHSTRING
#          as the same words shall be removed also for moviecovers. See allocine.py for a desription
#          of these variables.
#        You can also set allocine_search on a key (e.g. '1') by setting
#        EVENTS['menu']['1'] = Event(MENU_CALL_ITEM_ACTION, arg='moviecovers_search_or_cover_search')
#
# Todo:  - Update existing FXD file
#        - DVD/VCD support (discset ??)
#
# Author : S. FABRE for Biboobox, http://www.lahiette.com/biboobox
#          V. GIACOMINI for the forum searching feature
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

import re
import socket
socket.setdefaulttimeout(30.0)
import urllib, urllib2, urlparse, commands
import sys
import codecs
import os
import traceback

import menu
import config
import plugin
import time
from util import htmlenties2txt
from util import fxdparser
from gui.PopupBox import PopupBox

# headers for urllib2
txdata = None
txheaders = {
    'User-Agent': 'freevo (%s)' % sys.platform,
    'Accept-Language': 'fr-fr',
}

class PluginInterface(plugin.ItemPlugin):
    def __init__(self, license=None):
        """Initialise class instance"""

        # these are considered as private variables - don't mess with them unless
        # no other choise is given
        # fyi, the other choice always exists : add a subroutine or ask :)
        if not config.USE_NETWORK:
            self.reason = 'no network'
            return
        if not config.CONF.unzip:
            self.reason = 'unzip is not installed'
            return
        plugin.ItemPlugin.__init__(self)

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

    def searchMoviecovers(self, name):
        """name (string), returns id list

        Search for name and returns an id list with tuples:
        (id , name, year, type)"""
        # Clean internal variables
        self.initmyself()
        self.moviecovers_id_list = []

        regexp_tag = re.compile('<[^>]+>', re.I)
        #print "Request with: %s" % urllib.quote(name)
        url = 'http://www.moviecovers.com/multicrit.html?titre=%s&slow=1&listes=1' % (urllib.quote(name))
        req = urllib2.Request(url, txdata, txheaders)
        searchstring = name

        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, error:
            raise FxdMoviecovers_Net_Error("Moviecovers unreachable : " + error)
            exit

        regexp_getall = re.compile('.*<LI><A href="(/film/titre_.*)">(.*?)</A>.*([0-9]{4}).*', re.I)

        for line in response.read().split("\n"):
            #print line
            m = regexp_getall.match(line)
            if m:
                #print "Found film in line : %s" % line
                link = m.group(1)
                name = m.group(2)
                year = m.group(3)
                self.moviecovers_id_list += [ (link, name, year, 'Movies', 'main') ]

        if self.moviecovers_id_list:
            return self.moviecovers_id_list

        print 'no data for main request, try forum request'
        url = 'http://www.moviecovers.com/forum/search-mysql.html?forum=MovieCovers&query=%s' % (urllib.quote(name))
        req = urllib2.Request(url, txdata, txheaders)

        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, error:
            raise FxdMoviecovers_Net_Error("Moviecovers unreachable : " + error)
            exit

        regexp_getall = re.compile('.*<TD><A href="(fil.html\?query=.*)">(.*?)</A>.*', re.I)

        for line in response.read().split("\n"):
            #print ">>>%s" % line
            m = regexp_getall.match(line)
            if m:
                #print "Found film in line : %s" % line
                link = m.group(1)
                name = m.group(2)
                year = 'unknown'
                self.moviecovers_id_list += [ (link, name, year, 'Movies', 'forum') ]


        return self.moviecovers_id_list

    def guessMoviecovers(self, filename, label=False):
        """Guess possible Moviecovers movies from filename. Same return as searchMoviecovers"""
        name = filename

        for r in config.ALLOCINE_REMOVE_FROM_LABEL:
            name = re.sub(r, '', name.lower())

        name = vfs.basename(vfs.splitext(name)[0])
        name = re.sub('([a-z])([A-Z])', point_maker, name)
        name = re.sub('([a-zA-Z])([0-9])', point_maker, name)
        name = re.sub('([0-9])([a-zA-Z])', point_maker, name.lower())
        name = re.sub(',', ' ', name)

        parts = re.split("[\._' -]", name)
        name = ''

        for p in parts:
            if not p.lower() in config.ALLOCINE_REMOVE_FROM_SEARCHSTRING and \
                not re.search('[^0-9A-Za-z]', p):
                # originally: not re.search(p, '[A-Za-z]'):
                # not sure what's meant with that
                name += '%s ' % p

        return self.searchMoviecovers(name)

    def getMoviecoversPage(self, url, origin):
        """url
        Set an moviecovers number for object, and fetch data"""
        if origin == 'main':
            self.myurl = 'http://www.moviecovers.com/' + urllib.quote(urllib.unquote(url))
            id=""
        else:
            p = re.compile('.*#mid([0-9]*)')
            m = p.match(url)
            id = m.group(1)
            print "film id is %s" % id
            self.myurl = 'http://www.moviecovers.com/forum/' + url

        #print "Now trying to get %s" % self.myurl
        req = urllib2.Request(self.myurl, txdata, txheaders)

        try:
            idpage = urllib2.urlopen(req)
        except urllib2.HTTPError, error:
            raise FxdAllocine_Net_Error("Moviecovers.com unreachable" + error)
            return None

        #print "Response : %s" % idpage.read()
        self.parsedata(idpage, id)
        idpage.close()


    def setFxdFile(self, fxdfilename = None, overwrite = False):
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
            if self.isdiscset == True:
                self.fxdfile = vfs.join(config.OVERLAY_DIR, 'disc-set',
                                        self.getmedia_id(self.device))
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
        # if self.append == True and \
        #    parseMovieFile(self.fxdfile + '.fxd', None, []) == []:
        #     raise FxdAllocine_XML_Error("FXD file to be updated is invalid, please correct it.")

        if not vfs.isdir(vfs.dirname(self.fxdfile)):
            if vfs.dirname(self.fxdfile):
                os.makedirs(vfs.dirname(self.fxdfile))

    def moviecovers_get_disc_searchstring(self, item):
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
                return [ (self.moviecovers_search , _('Search Moviecovers.com for this file'),
                    'moviecovers_search_or_cover_search') ]

            elif item.mode in ('dvd', 'vcd') and item.info.has_key('tracks'):
                self.disc_set = True
                s = self.moviecovers_get_disc_searchstring(self.item)
                if s:
                    return [ (self.moviecovers_search , _('Search Moviecovers.com for [%s]') % s,
                        'moviecovers_search_or_cover_search') ]

        if item.type == 'dir' and item.media and item.media.mountdir.find(item.dir) == 0:
            self.disc_set = True
            s = self.moviecovers_get_disc_searchstring(self.item)
            if s:
                return [ (self.moviecovers_search , _('Search Moviecovers.com for [%s]') % s,
                    'moviecovers_search_or_cover_search') ]
        return []


    def moviecovers_search(self, arg=None, menuw=None):
        """
        search moviecovers for this item
        """
        box = PopupBox(text=_('Searching Moviecovers.com...'))
        box.show()

        items = []

        try:
            duplicates = []
            if self.disc_set:
                self.searchstring = self.item.media.label
            else:
                self.searchstring = self.item.name

            for id,name,year,type,origin in self.guessMoviecovers(self.searchstring, self.disc_set):
                try:
                    for i in self.item.parent.play_items:
                        if i.name == name:
                            if not i in duplicates:
                                duplicates.append(i)
                except:
                    pass
                items.append(menu.MenuItem('%s (%s, %s)' % (htmlenties2txt(name), year, type),
                    self.moviecovers_create_fxd, (id, origin)))
        except:
            box.destroy()
            box = PopupBox(text=_('Connection error : Probably connection timeout, try again'))
            box.show()
            time.sleep(2)
            box.destroy()
            traceback.print_exc()
            return

        box.destroy()
        if config.MOVIECOVERS_AUTOACCEPT_SINGLE_HIT and len(items) == 1:
            self.moviecovers_create_fxd(arg=items[0].arg, menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('MOVIECOVERS Query'), items)
            menuw.pushmenu(moviemenu)
            return

        box = PopupBox(text=_('No information available from Moviecovers.com'))
        box.show()
        time.sleep(2)
        box.destroy()
        return


    def moviecovers_menu_back(self, menuw):
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


    def moviecovers_create_fxd(self, arg=None, menuw=None):
        """
        create fxd file for the item
        """
        box = PopupBox(text=_('Getting data, it can be long as we download a ZIP file'))
        box.show()

        #if this exists we got a cdrom/dvdrom
        if self.item.media and self.item.media.devicename:
            devicename = self.item.media.devicename
        else:
            devicename = None

        self.getMoviecoversPage(arg[0],arg[1])

        if self.disc_set:
            self.setDiscset(devicename, None)
        else:
            self.setFxdFile(os.path.splitext(self.item.filename)[0])

        self.writeFxd()
        self.moviecovers_menu_back(menuw)
        box.destroy()


    def moviecovers_add_to_fxd(self, arg=None, menuw=None):
        """
        add item to fxd file
        BROKEN, PLEASE FIX
        """

        #if this exists we got a cdrom/dvdrom
        if self.item.media and self.item.media.devicename:
            devicename = self.item.media.devicename
        else: devicename = None

        self.setFxdFile(arg[0].fxd_file)

        if self.item.mode in ('dvd', 'vcd'):
            self.setDiscset(devicename, None)
        else:
            num = len(self.video) + 1
            if arg[1] == 'variant':
                part = makePart('Variant %d' % num, 'f%s' % num)

                if self.variant:
                    part = [ makePart('Variant 1', 'f1'), part ]

                self.setVariants(part)

        self.writeFxd()
        self.moviecovers_menu_back(menuw)

    def writeFxd(self):
        """Write fxd file"""
        #if fxdfile is empty, set it yourself
        if not self.fxdfile:
            self.setFxdFile()

        try:
            #should we add to an existing file?
            if self.append == True :
                if self.isdiscset == True:
                    self.update_discset()
                else: self.update_movie()
            else:
                #fetch images
                self.fetch_image()
                #should we write a disc-set ?
                if self.isdiscset == True:
                    self.write_discset()
                else:
                    self.write_movie()

            #check fxd
            # XXX: add this back in without using parseMovieFile
            # if parseMovieFile(self.fxdfile + '.fxd', None, []) == []:
            #     raise FxdImdb_XML_Error("""FXD file generated is invalid, please "+
            #                             "post bugreport, tracebacks and fxd file.""")

        except (IOError, FxdMoviecovers_IO_Error), error:
            raise FxdMoviecovers_IO_Error('error saving the file: %s' % str(error))


    def setDiscset(self, device, regexp, *file_opts, **mpl_global_opt):
        """
        device (string), regexp (string), file_opts (tuple (mplayer-opts,file)),
        mpl_global_opt (string)
        Set media is dvd/vcd,
        """
        if len(self.video) != 0 or len(self.variant) != 0:
            raise FxdMoviecovers_XML_Error("<movie> already used, can't use both "+
                                    "<movie> and <disc-set>")

        self.isdiscset = True
        if (not device and not regexp) or (device and regexp):
            raise FxdMoviecovers_XML_Error("Can't use both media-id and regexp")

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
        fxd.setcdata(node, "The information in this file are from Moviecovers.com.\n"+
                           "Please visit http://www.moviecovers.com for more informations.\n")
        fxd.add(fxd.XMLnode('source', [('url', "%s" % self.myurl)]), node, 0)

    def write_fxd_video(self, fxd, node):
        fxd.setattr(node, 'title', self.title)
        fxd.add(fxd.XMLnode('cover-img', (('source', self.image_url), ("test", "test")), self.image), node, 0)
        videonode = fxd.XMLnode('video')
        fxd.add(videonode, node)
        fxd.add(fxd.XMLnode('file', [('id', 'f1')], os.path.basename(self.item.filename)), videonode, 0)
        infonode = fxd.XMLnode('info')
        fxd.add(infonode, node)
        if self.info:
            for k in self.info.keys():
                fxd.add(fxd.XMLnode(k, [], self.info[k]), infonode, 0)

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

    def parsedata(self, results, id=""):
        """results (moviecovers html page), allocine_id
        Returns tuple of (title, info(dict), image_urls)"""

        dvd = 0
        inside_plot = None

        if id:
            regexp_zipfile = re.compile('.*<A href="(/getzip.html/.*-%s-.*?)">.*' % id, re.I)
        else:
            regexp_zipfile = re.compile('.*<A href="(/getzip.html/.*?)">.*', re.I)

        for line in results.read().split("\n"):
            m = regexp_zipfile.match(line)
            if m:
                myurl2 = 'www.moviecovers.com' + m.group(1)
                break

        # Chain shell commands to get the zip file for data
        self.tmppath = '/tmp/moviecovers/'
        self.tmpfile = self.tmppath + 'file.zip'
        commands.getstatusoutput('rm -r -f ' + self.tmppath)
        commands.getstatusoutput('mkdir '+ self.tmppath)
        #print "Get : %s " % urllib.quote(urllib.unquote(myurl2))
        commands.getstatusoutput('wget '+urllib.quote(urllib.unquote(myurl2))+' -O '+self.tmpfile)
        (status, output) = commands.getstatusoutput('cd '+self.tmppath+'; '+config.CONF.unzip+' -o '+self.tmpfile)

        # Now copy
        regexp_jpegfile = re.compile('.*jpg', re.I)
        regexp_filmfile = re.compile('.*film', re.I)
        for file in os.listdir(self.tmppath):
            #print "File found : " + file
            m = regexp_jpegfile.match(file)
            if m:
                #print "Found JPEG file : %s" % file
                self.imagefile = self.tmppath + vfs.basename(file)
            else:
                m = regexp_filmfile.match(file)
                if m:
                    #print "Found FILM file : %s" % file
                    self.filmfile = self.tmppath + vfs.basename(file)

        # Now parse the film file
        #print "filmfile is %s" % self.filmfile
        file = open(self.filmfile)
        # File format is :
            #Title
            #Real
            #Year
            #Pays
            #Genre
            #Dur?e
            #Acteurs
            #Synopsis
        lineno = 0
        self.info['plot'] = ''
        for line in file.read().split("\n"):
            #print line
            if lineno == 0: self.title = line
            if lineno == 1: self.info['director'] = line
            if lineno == 2: self.info['year'] = line
            if lineno == 3: self.info['country'] = line
            if lineno == 4: self.info['genre'] = line
            if lineno == 5: self.info['runtime'] = line
            if lineno == 6: self.info['actor']= line
            if lineno > 6:
                self.info['plot'] += line
            lineno += 1

        #print self.info
        return (self.title, self.info, self.imagefile)

    def fetch_image(self):
        """Fetch the best image"""
        image_len = 0

        if (len(self.imagefile) == 0): # No images
            return

        self.image = (self.fxdfile + '.jpg')
        commands.getstatusoutput('cp -f "' + self.imagefile + '" "'+ self.image + '"')

        self.image = vfs.basename(self.image)

        print "Downloaded cover image from Moviecovers.com"
        print "Freevo knows nothing about the copyright of this image, please"
        print "go to Moviecovers.com to check for more informations about private."
        print "use of this image"

class Error(Exception):
    """Base class for exceptions in Allocine_Fxd"""
    def __str__(self):
        return self.message
    def __init__(self, message):
        self.message = message

class FxdMoviecovers_Error(Error):
    """used to raise exceptions"""
    pass

class FxdMoviecovers_XML_Error(Error):
    """used to raise exceptions"""
    pass

class FxdMoviecovers_IO_Error(Error):
    """used to raise exceptions"""
    pass

class FxdMoviecovers_Net_Error(Error):
    """used to raise exceptions"""
    pass

def point_maker(matching):
    return '%s.%s' % (matching.groups()[0], matching.groups()[1])
