# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# rssperiodic.py - This is the Freevo RSS feed module
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

import re,os,sys,glob,urllib,datetime,time,shutil
from subprocess import Popen
import cPickle, pickle
import config
import rssfeed
import kaa.metadata as metadata

appname = os.path.splitext(os.path.basename(sys.argv[0]))[0]
appconf = appname.upper()
DEBUG = hasattr(config, appconf+'_DEBUG') and eval('config.'+appconf+'_DEBUG') or config.DEBUG

def _debug_(text, level=1):
    if DEBUG >= level:
        try:
            log.debug(str(text))
        except:
            print str(text)

def convertDate(string):
    if not re.search("\d+\s+\S+\s+\d+",string):
        return datetime.date.today()
    itemDateList = re.split(" ", re.search("\d+\s+\S+\s+\d+",string).group())
    day=int(itemDateList[0])
    if itemDateList[1] == "Jan":
        month=1
    elif itemDateList[1] == "Feb":
        month=2
    elif itemDateList[1] == "Mar":
        month=3
    elif itemDateList[1] == "Apr":
        month=4
    elif itemDateList[1] == "May":
        month=5
    elif itemDateList[1] == "Jun":
        month=6
    elif itemDateList[1] == "Jul":
        month=7
    elif itemDateList[1] == "Aug":
        month=8
    elif itemDateList[1] == "Sep":
        month=9
    elif itemDateList[1] == "Oct":
        month=10
    elif itemDateList[1] == "Nov":
        month=11
    else:
        month=12
    year=int(itemDateList[2])
    try:
        itemDate = datetime.date(year,month,day)
    except ValueError:
        '''There is some incorrect data out there, ie. 31 Apr 2006'''
        newmonth = month + 1
        year += month / 12
        month = (month+1) % 12
        day = 1
        itemDate = datetime.date(year,month,day)+datetime.timedelta(-1)
    return itemDate

def checkForDup(string):
    cacheFile=config.FREEVO_CACHEDIR+"/rss.pickle"
    try:
        try:
            downloadedUrls=cPickle.load(open(cacheFile,"r"))
        except:
            downloadedUrls=pickle.load(open(cacheFile,"r"))
    except IOError:
        return False
    except EOFError:
        return False
    foundFile=False
    for line in downloadedUrls:
        if string in line:
            foundFile=True
    return foundFile

def addFileToCache(string):
    cacheFile=config.FREEVO_CACHEDIR+"/rss.pickle"
    downloadedUrls=[]
    try:
        try:
            downloadedUrls = cPickle.load(open(cacheFile,"r"))
        except:
            downloadedUrls = pickle.load(open(cacheFile,"r"))
    except IOError:
        pass
    downloadedUrls.append(string)
    try:
        cPickle.dump(downloadedUrls, open(cacheFile,"w"))
    except:
        pickle.dump(downloadedUrls, open(cacheFile,"w"))

def addFileToExpiration(string,goodUntil):
    ''' the new file gets added with the expiration date to the expiration file '''
    cacheFile=config.FREEVO_CACHEDIR+"/rss.expiration"
    downloadedFiles=[]
    try:
        try:
            downloadedFiles = cPickle.load(open(cacheFile,"r"))
        except:
            downloadedFiles = pickle.load(open(cacheFile,"r"))
    except IOError:
        pass
    downloadedFiles.append(string + ";" + goodUntil.__str__())
    try:
        cPickle.dump(downloadedFiles, open(cacheFile,"w"))
    except:
        pickle.dump(downloadedFiles, open(cacheFile,"w"))

def checkForExpiration():
    ''' checking for expired files by reading the rss.expiration file the file
    contains the expiration date. once a file is expired it and its fxd gets
    deleted at the end the file gets removed from the rss.expiration file '''
    cacheFile=config.FREEVO_CACHEDIR+"/rss.expiration"
    try:
        try:
            downloadedFiles=cPickle.load(open(cacheFile,"r"))
        except:
            downloadedFiles=pickle.load(open(cacheFile,"r"))
    except IOError:
        return
    deletedItems = []
    for line in downloadedFiles:
        (filename,goodUntil)=re.split(";", line)
        expirationdate = datetime.datetime(*time.strptime(goodUntil, "%Y-%m-%d")[0:5])
        diff = expirationdate - datetime.datetime.today()
        if int(diff.days)<=0:
            deletedItems.append(line)
            tempList=re.split("\.",filename)
            fxdfile=tempList[0]
            for line in tempList[1:-1]:
                fxdfile=fxdfile+"."+line
            fxdfile=fxdfile+".fxd"
            try:
                os.remove(config.RSS_VIDEO+fxdfile)
            except OSError:
                _debug_("removing the file %s failed" % (fxdfile))
            try:
                os.remove(config.RSS_VIDEO+filename)
            except OSError:
                _debug_("removing the file %s failed" % (filename))
    for line in deletedItems:
#      try:
        downloadedFiles.remove(line)
#      except ValueError:
#          _debug_("removing the line %s failed" % (line))
    try:
        cPickle.dump(downloadedFiles, open(cacheFile,"w"))
    except:
        pickle.dump(downloadedFiles, open(cacheFile,"w"))

def createFxd(item, filename):
    ofile = os.path.splitext(filename)[0]+'.fxd'
    try:
        file = open(ofile, 'w')
        file.write('<?xml version="1.0" encoding="iso-8859-1"?>\n')
        file.write('<freevo>\n')
        file.write('   <movie title="%s">\n' % item.title)
        file.write('      <video>\n')
        file.write('         <file id="f1">%s</file>\n' % filename)
        file.write('      </video>\n')
        file.write('      <info>\n')
        file.write('         <plot>%s</plot>\n' % item.description)
        file.write('      </info>\n')
        file.write('   </movie>\n')
        file.write('</freevo>\n')
        file.close()
    except IOError:
        _debug_("ERROR: Unable to write FXD file %s" % (ofile))
    return ofile

def checkForUpdates():
    try:
        file = open(config.RSS_FEEDS,"r")
    except IOError:
        _debug_("ERROR: Could not open configuration file %s" % (config.RSS_FEEDS))
        return

    for line in file:
        if line == '\n':
            continue
        if re.search("^#",line):
            continue
        try:
            (url,numberOfDays)=re.split(";", line)
        except ValueError:
            continue
        _debug_("Check %s for updates" % url)
        try:
            sock = urllib.urlopen(url)
            feedSource = sock.read()
            sock.close()
            for item in rssfeed.Feed(feedSource).items:
                diff = datetime.date.today() - convertDate(item.date)
                goodUntil = datetime.date.today() + datetime.timedelta(days=int(numberOfDays))
                if int(diff.days) <= int(numberOfDays) and not re.search("None",item.url):
                    os.chdir(config.RSS_DOWNLOAD)
                    filename = os.path.basename(item.url)
                    _debug_('"%s" -> %s' % (item.title, filename), 2)
                    if len(glob.glob(filename)) == 0 and not checkForDup(item.url):
                        if re.search("torrent", item.url):
                            _debug_("Running bittorrent download from %s" % item.url)
                            cmdlog=open(os.path.join(config.LOGDIR, 'rss-bittorrent.out'), 'a')
                            p = Popen('bittorrent-console %s' % (item.url), shell=True, stderr=cmdlog, stdout=cmdlog)
                            exitStatus = p.wait()
                            filename=re.sub("\.torrent","",filename)
                        else:
                            _debug_("Running wget download from %s" % (item.url))
                            cmdlog=open(os.path.join(config.LOGDIR, 'rss-wget.out'), 'a')
                            p = Popen('wget -O %s %s' % (filename, item.url), shell=True, stderr=cmdlog, stdout=cmdlog)
                            exitStatus = p.wait()
                        if exitStatus:
                            _debug_("Download failed - exit status %s." % exitStatus)
                            os.remove(filename)
                        else:
                            _debug_("Download completed (%s bytes)" % os.path.getsize(filename))
                            meta = metadata.parse(filename)
                            if meta and meta.has_key('media'):
                                if meta.media == 'MEDIA_AUDIO':
                                    try:
                                        fxdpath = createFxd(item, filename)
                                        shutil.move(filename, config.RSS_AUDIO)
                                        shutil.move(fxdpath, config.RSS_AUDIO)
                                    except:
                                        _debug_('failed to move %s to %s' % (filename, newpath))
                                elif meta.media == 'MEDIA_VIDEO':
                                    try:
                                        fxdpath = createFxd(item, filename)
                                        shutil.move(filename, config.RSS_VIDEO)
                                        shutil.move(fxdpath, config.RSS_VIDEO)
                                    except:
                                        _debug_('failed to move %s to %s' % (filename, newpath))
                                else:
                                    _debug_('Cannot move %s as it media type is %s', (filename, meta.media))
                                    fxdpath = createFxd(item,filename)
                            else:
                                _debug_('Cannot move %s as cannot determine its media type', (filename))
                            addFileToCache(item.url)
                            addFileToExpiration(filename,goodUntil)
        except IOError:
            _debug_("ERROR: Unable to download %s. Connection may be down." % (url))
