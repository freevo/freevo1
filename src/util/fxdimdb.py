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
import logging
logger = logging.getLogger("freevo.util.fxdimdb")


# python has no data hiding, but this is the intended use...
# subroutines completely in lowercase are regarded as more "private" functions
# sub-routines are regarded as public

# based on original implementation by 'den_RDC (rdc@kokosnoot.com)'
__author__           = 'den_RDC (rdc@kokosnoot.com)'
__maintainer__       = 'Maciej Mike Urbaniak'
__maintainer_email__ = 'maciej@urbaniak.org'
__version__          = 'Revision 0.2'
__license__          = 'GPL' 

# Module Imports
import re
import urllib, urllib2, urlparse
import sys
import codecs
import os
import traceback

try:
    import imdb
except:
    logger.error('It seems that you do not have imdbpy installed!')

import config
import util

import kaa.metadata as mmpython

try:
    import freevo.version as version
except:
    import version


imdb_ctitle     = '/tmp/imdb-movies.list'
imdb_ctitle_url = 'ftp://ftp.funet.fi/pub/mirrors/ftp.imdb.com/pub/movies.list.gz'
imdb_titles     = None
imdb_info_tags  = ('year', 'genre', 'tagline', 'plot', 'rating', 'runtime', 'mpaa');

# headers for urllib2
txdata    = None
txheaders = {
    'User-Agent': 'freevo %s (%s)' % (version, sys.platform),
    'Accept-Language': 'en-us',
}

#Begin class
class FxdImdb:
    """Class for creating fxd files and fetching imdb information"""

    def __init__(self):
        """Initialise class instance"""

        # these are considered as private variables - don't mess with them unless
        # no other choice is given
        # FYI, the other choice always exists : add a subroutine or ask :)

        self.imdb = imdb.IMDb()
        self.title = ''    # Full title that will be written to the FXD file
        self.ctitle         = []    # Contains parsed from filename title, and if exist season, episode
        self.id             = None  # IMDB ID of the movie
        self.isdiscset      = False
        self.info           = {}    # Full movie info

        self.image          = None  # full path image filename
        self.image_urls     = []    # possible image url list
        self.image_url      = None  # final image url

        self.fxdfile        = None  # filename, full path, WITHOUT extension

        self.append         = False
        self.device         = None
        self.regexp         = None
        self.mpl_global_opt = None
        self.media_id       = None
        self.file_opts      = []
        self.video          = []
        self.variant        = []
        self.parts          = []

        #initialize self.info
        for t in imdb_info_tags:
            self.info[t] = ""

        #image_url_handler stuff
        self.image_url_handler = {}
        self.image_url_handler['www.impawards.com'] = self.impawards


    def parseTitle(self, filename, label=False):
        """
        Parse the title
        Return tuple of title, season and episode (if exist)
        """
        logger.debug('parseTitle(filename=%r, label=%r)', filename, label)

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
        season  = ''
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

        logger.debug('name=%s season=%s episode=%s', name, season, episode)

        if label:
            for r in config.IMDB_REMOVE_FROM_LABEL:
                try:
                    name = re.sub(r, '', name)
                except Exception, exc:
                    logger.warning('Exception', exc_info=True)
        else:
            for r in config.IMDB_REMOVE_FROM_NAME:
                try:
                    name = re.sub(r, '', name)
                except Exception, exc:
                    logger.warning('Exception', exc_info=True)

        parts = re.split('[\._ -]', name)
        name = ''
        for p in parts:
            if not p.lower() in config.IMDB_REMOVE_FROM_SEARCHSTRING and not re.search('[^0-9A-Za-z]', p):
                # originally: not re.search(p, '[A-Za-z]'):
                # not sure what's meant with that
                name += '%s ' % p

        return tuple([name, season, episode])


    def guessImdb(self, filename, label=False):
        """
        Guess possible titles from file name
        Return tuple of title, season and episode (if exist)
        """
        logger.debug('guessImdb(filename=%r, label=%r)', filename, label)

        self.ctitle = self.parseTitle(filename, label)

        return self.searchImdb(self.ctitle[0], self.ctitle[1], self.ctitle[2])

    def searchImdb(self, title, season=None, episode=None):
        """
        Search IMBD for a title
        """

        try:
            # Look up possible movie matches directly at IMDB.
            # NOTE:
            # imdb does support advanced search for titles of the series but unfortunately 
            # imdbpy does not so we have do this the hard way, present the user with a list
            # to choose from. If we could search for a series title directly we'd have a great 
            # propability for a unique hit and thus would not need to present the selection menu.
            # We try to reduce the search result by filtering initial result for tv (mini) series only.
            
            results = self.imdb.search_movie(title)
            logger.debug('Searched IMDB for %s, found %s items', title, len(results))
            
            # if series we remove all non series objects to narrow down the search results
            if season and episode:
                for item in results[:]:
                    if len(item.keys()) == 0 or  item['kind'] == 'video game' or \
                                                (item['kind'] != 'tv series' and 
                                                 item['kind'] != 'tv mini series'):
                        results.remove(item)
            # else if not series we remove all series objects to narrow down the search results
            else:
                for item in results[:]:
                    if len(item.keys()) == 0 or (item['kind'] == 'video game' or 
                                                 item['kind'] == 'tv series' or 
                                                 item['kind'] == 'tv mini series'):
                        results.remove(item)

        except imdb.IMDbError, error:
            logger.warning('Exception', exc_info=True)
            raise FxdImdb_Error(str(error))

        return results


    def retrieveImdbData(self, id, season=None, episode=None):
        """
        Given IMDB ID retrieves full info about the Title directly from IMDB via HTTP
        using imdbpy.
        """

        try:
            # Get a Movie object with the data about the movie identified by the given movieID.
            movie = self.imdb.get_movie(id)

            if not movie:
                logger.warning('It seems that there\'s no movie with MovieId "%s"', arg[0])
                raise FxdImdb_Error('No movie with MovieId "%s"' % arg[0])

            self.ctitle = tuple([movie['title'], season, episode])

            # check if we have a series episode
            if self.ctitle[2] and (movie['kind'] == 'tv series' or movie['kind'] == 'tv mini series'):
                # retrieve episode info
                self.imdb.update(movie, 'taglines')
                self.imdb.update(movie, 'episodes')
                episode = movie['episodes'][int(self.ctitle[1])][int(self.ctitle[2])]
                self.imdb.update(episode)
                self.imdb_retrieve_movie_data(movie, episode)
                return episode.movieID
            else:
                self.imdb.update(movie, 'taglines')
                self.imdb_retrieve_movie_data(movie)
                return movie.movieID

        except imdb.IMDbError, error:
            logger.warning('Exception', exc_info=True)
            raise FxdImdb_Error(str(error))


    def retrieveImdbBulkSeriesData(self, id, items):
        """
        Given IMDB ID retrieves full info about the series and episodes 
        directly from IMDB via HTTP using imdbpy. Used by imbdpy helper.
        """

        fxds = []

        try:
            # Get a Movie object with the data about the movie identified by the given movieID.
            movie = self.imdb.get_movie(id)

            if not movie:
                logger.warning('It seems that there\'s no movie with MovieId "%s"', id)
                raise FxdImdb_Error('No movie with MovieId "%s"' % id)

            if (movie['kind'] != 'tv series' and movie['kind'] != 'tv mini series'):
                logger.warning('It seems that supplied MovieId "%s" is not a TV Series ID. Aborting.', id)
                raise FxdImdb_Error('No a TV Series. MovieId "%s"' % id)
                
            self.imdb.update(movie, 'episodes')
            self.imdb.update(movie, 'taglines')

            for item in items:
            
                fxd = FxdImdb()

                try:
                    # parse the name to get title, season and episode numbers
                    fxd.ctitle = fxd.parseTitle(item[2])
                    episode = movie['episodes'][int(fxd.ctitle[1])][int(fxd.ctitle[2])]
                    self.imdb.update(episode)
                    fxd.imdb_retrieve_movie_data(movie, episode)

                except FxdImdb_Error, error:
                    logger.warning('Exception', exc_info=True)
                    return

                video = makeVideo('file', 'f1', os.path.basename(item[0]), device=None)
                fxd.setVideo(video)
                fxd.setFxdFile(os.path.splitext(item[0])[0])

                fxds.append(fxd)

        except imdb.IMDbError, error:
            logger.warning('Exception', exc_info=True)
            raise FxdImdb_Error(str(error))

        return fxds


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


    def isDiscset(self):
        """
        Check if fxd file describes a disc-set, returns 1 for true, 0 for false
        None for invalid file
        """
        
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

    def imdb_retrieve_movie_data(self, movie, episode=None):
        """
        Retrives all movie data (including Episode's if TV Series)
        """

        self.id = self.imdb.get_imdbID(movie)
        logger.info('Retrieved movie data:\n "%s"', movie.summary())

        self.title = self.get_title(movie, episode)
        self.info['genre'] = self.get_genre(movie)
        self.info['tagline'] = self.get_tagline(movie)
        self.info['year'] = self.get_year(movie, episode)
        self.info['rating'] = self.get_rating(movie, episode)
        self.info['plot'] = self.get_plot(movie, episode)
        self.info['mpaa'] = self.get_mpaa(movie)

        if config.IMDB_USE_IMDB_RUNTIME:
            self.info['runtime'] = self.get_runtimes(movie, episode)

        # try to retrieve movie poster urls, first from impawards.com, then from IMDB
        self.impawardsimages(movie['title'], self.info['year'], episode)

        if movie.has_key('full-size cover url'):
            self.image_urls += [ movie['full-size cover url'] ]


    def get_tagline(self, movie):
        """
        Returns first tagline of the movie
        """
        if movie.has_key('taglines'):
            return movie.get('taglines')[0]

        return ''


    def get_genre(self, movie):
        """
        Returns concatenated string of movie genres
        """
        if movie.has_key('genres'):
            return '%s' % ' '.join(movie.get('genres'))

        return ''
    

    def get_title(self, movie, episode):
        """
        Builds a movie/episode title
        """
        if episode and episode.has_key('title'):
            ep = config.IMDB_SEASON_EPISODE_FORMAT % (int(self.ctitle[1]), int(self.ctitle[2]))
            return '%s %s %s' % (movie['title'], ep, episode['title'])
      
        return movie.get('title')


    def get_year(self, movie, episode):
        """
        Returns the year of the movie or the original air date of the series episode
        """
        if episode and episode.has_key('original air date'):
            return episode['original air date']
        
        return movie.get('year')


    def get_mpaa(self, movie):
        """
        Retrieves MPAA rating or formatted certificate data
        """
        if movie.has_key('mpaa'):
            #If it exists, this key from imdbpy is the best way to get MPAA movie rating
            #rating_match = re.search(r"Rated (?P<rating>[a-zA-Z0-9-]+)", movie['mpaa'])
            #if rating_match:
            #    rating = rating_match.group('rating')
            #    return rating
            return movie['mpaa']
            
        if movie.has_key('certificates'):
            #IMDB lists all the certifications a movie has gotten the world over.
            #Each movie often has multiple certifications per country since it
            #will often get re-rated for different releases (theater and
            #then DVD for example).
 
            #for movies with multiple certificates, we pick the 'lowest' one since
            #MPAA ratings are more permissive the more recent they were given.
            #A movie that was rated R in the 70s may be rated PG-13 now but will
            #probably never be rerated NC-17 .
            ratings_list_ordered = ['TV-Y', 'G', 'TV-Y7', 'TV-Y7-FV', 'TV-G', 'PG', 'TV-PG', 'PG-13', 'TV-14', 'TV-MA', 'R', 'NC-17', 'Unrated']
            ratings_list_extinfo = ['All children ages 2-5',
                                    'General Audiences',
                                    'Directed to children 7 and older',
                                    'Directed to children 7 and older with fantasy violence in shows',
                                    'General audience',
                                    'Parental Guidance Suggested',
                                    'Parental guidance suggested',
                                    'Parents Strongly Cautioned',
                                    'Parents strongly cautioned/May be unsuitable for children under 14 years of age',
                                    'Mature audience - unsuitable for audiences under 17',
                                    'Restricted',
                                    'No One 17 and under admitted',
                                    'Not rated']
                       
            #Map older rating types to their modern equivalents
            ratings_mappings = {'M':'NC-17',
                                'X':'NC-17',
                                'GP':'PG',
                                'Approved': 'PG',
                                'Open': 'PG',
                                'Not Rated': 'Unrated'
                                }
 
            certs = movie['certificates']
            good_ratings = []
            for cert in certs:
                if 'usa' in cert.lower():
                    rating_match = re.match(r"USA:(?P<rating>[ a-zA-Z0-9-]+)", cert)
                    if rating_match:
                        rating = rating_match.group('rating')
                        if rating in ratings_list_ordered:
                            index = ratings_list_ordered.index(rating)
                            if index not in good_ratings:
                                good_ratings.append(index)
                        elif rating in ratings_mappings:
                            index = ratings_list_ordered.index(ratings_mappings[rating])
                            if index not in good_ratings:
                                good_ratings.append(index)

            if good_ratings:
                best_rating = ratings_list_ordered[min(good_ratings)]
                best_rating_extinfo = ratings_list_extinfo[min(good_ratings)]
                return '%s (%s)' % (best_rating, best_rating_extinfo)

        return 'MPAA or Certification information not available'


    def get_runtimes(self, movie, episode=None):
        """
        Returns a formatted string listing all runtimes 
        """
        runtimes = []

        if episode and episode.has_key('runtimes'):
            runtimes = episode['runtimes']

        elif movie.has_key('runtimes'):
            runtimes = movie['runtimes']

        times = []
        for runtime in runtimes:
            try:
                #imdbpy usually returns a runtime with no country or notes, so we'll catch that instance
                time = int(runtime)
                times.append('%s min' % time)
            except ValueError:
                splitted = [x for x in runtime.split(":") if x != '']
                val = None
                notes = None
                country = None
                for split in splitted:
                    try:
                        time = int(split)
                        continue
                    except:
                        if split[0] == "(" and split[-1] == ")":
                            notes = split[1:-1]
                            continue
                        if re.match("\w+", split):
                            country = split
                if country and notes:
                    val = '%s: %s min (%s)' % (country, time, notes)
                elif country:
                    val = '%s: %s min' % (country, time)
                elif notes:
                    val = '%s min (%s)' % (time, notes)
                else:
                    val = '%s min' % (time)

                times.append(val)
 
        return ', '.join(times)


    def get_rating(self, movie, episode=None):
        """ 
        Retrieves user ratings for given movie or if available, for individual episodes
        """
        if episode and (episode.has_key('rating') and episode.has_key('votes')):
            return '%s (%s votes)' % (episode['rating'], episode['votes'])
        elif movie.has_key('rating') and movie.has_key('votes'):
            return '%s (%s votes)' % (movie['rating'], movie['votes'])

        return 'Awaiting 5 votes'


    def get_plot(self, movie, episode=None):
        """
        Retrieves the plot or or if not available, plot outline
        """
        # need a hack here to check if plot is a list or a string.
        # this is a buggy implementation of imdbpy as it should always return list.
        if episode and episode.has_key('plot'):
            plot = episode['plot']
        elif movie.has_key('plot'): 
            plot = movie['plot']
        elif movie.has_key('plot outline'):
            plot = movie['plot outline']
        else: 
            return ''
        
        if isinstance(plot, list):
            return plot[0].split("::")[0]
        else:
            return plot.split("::")[0]


    def write_discset(self):
        """Write a <disc-set> to a fresh file"""

        try:
            i = vfs.codecs_open( (self.fxdfile + '.fxd') , 'wb', encoding='utf-8')
        except IOError, error:
            raise FxdImdb_IO_Error("Writing FXD file failed : " + str(error))
            return

        i.write("<?xml version=\"1.0\" ?>\n<freevo>\n")
        if self.id:
            i.write("  <copyright>\n" +
                "    The information in this file are from the Internet Movie Database (IMDb).\n" +
                "    Please visit http://www.imdb.com for more information.\n")
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


    def write_movie(self):
        """Write <movie> to fxd file"""

        try:
            i = vfs.codecs_open((self.fxdfile+'.fxd') , 'w', encoding='utf-8')
        except IOError, error:
            raise FxdImdb_IO_Error("Writing FXD file failed : " + str(error))
            return

        #header
        i.write("<?xml version=\"1.0\" ?>\n<freevo>\n")
        if self.id:
            i.write("  <copyright>\n")
            i.write("    The information in this file are from the Internet Movie Database (IMDb).\n")
            i.write("    Please visit http://www.imdb.com for more information.\n")
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


    def impawardsimages(self, title, year, series=None):
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

        imp_image_urls = [ ]
        
        if series:
            # build up an array with all kind of image urls
            imp_base_url    = 'http://www.impawards.com/tv/posters'

        else:
            # build up an array with all kind of image urls
            imp_base_url    = 'http://www.impawards.com/%s/posters' % year

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

            logger.debug('IMPAWARDS: Checking image URL %s', imp_image_url)
            try:
                imp_req = urllib2.Request(imp_image_url, txdata, txheaders)

                # an url is valid if the returned content-type is 'image/jpeg'
                imp_r     = urllib2.urlopen(imp_req)
                imp_ctype = imp_r.info()['Content-Type']
                imp_r.close()

                logger.debug('IMPAWARDS: Found content-type %s for url %s', imp_ctype, imp_image_url)
                if (imp_ctype == 'image/jpeg'):
                    self.image_urls += [ imp_image_url ]

            except:
                pass


    def impawards(self, host, path):
        """ parser for posters from www.impawards.com. 
            TODO: check for licences of each poster and add all posters
        """

        path = '%s/posters/%s.jpg' % (path[:path.rfind('/')], path[path.rfind('/')+1:path.rfind('.')])
        return [ 'http://%s%s' % (host, path) ]


    def fetch_image(self):
        """Fetch the best image"""
        
        logger.debug('fetch_image=%s', self.image_urls)

        image_len = 0
        if len(self.image_urls) == 0: # No images
            return

        for image in self.image_urls:
            try:
                logger.debug('image=%s', image)
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

        logger.debug('Downloaded cover image from %s', self.image_url)
        print "Freevo knows nothing about the copyright of this image, please go to"
        print "%s to check for more information about private use of this image." % self.image_url


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


    def getmedia_id(self, drive):
        """drive (device string)
        return a unique identifier for the disc"""

        if not vfs.exists(drive):
            return drive
        (type, id) = mmpython.cdrom.status(drive)
        return id


    def print_info(self):
        """return info part for FXD writing"""
        ret = u''
        if self.info:
            ret = u'    <info>\n'
            for k in self.info.keys():
                ret += u'      <%s>' % k + Unicode(self.str2XML(self.info[k])) + '</%s>\n' % k
            ret += u'    </info>\n'
        return ret


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
    def __str__(self):
        return self.message
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

def makeFile_opt(mplayer_opt, file):
    """Create a file_opt tuple"""
    if mplayer_opt == None or file == None:
        raise FxdImdb_XML_Error("Required values missing for tuple creation")
    file = relative_path(file)
    t = mplayer_opt, file

    return t

#--------- classless private functions

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


def point_maker(matching):
    return '%s.%s' % (matching.groups()[0], matching.groups()[1])
