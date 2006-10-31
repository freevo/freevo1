# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# rssPeriodic.py - This is the Freevo RSS feed module
# -----------------------------------------------------------------------
# $Id: rssPeriodic.py 8441 2006-10-21 11:15:52Z duncan $
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

import re,os,glob,urllib,datetime,pickle
import config
import rssFeed

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
    itemDate = datetime.date(year,month,day)
    return itemDate

def checkForDup(string):
    cacheFile=config.FREEVO_CACHEDIR+"/rss.pickle"
    try:
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
       downloadedUrls = pickle.load(open(cacheFile,"r"))
    except IOError:
       pass
    downloadedUrls.append(string)
    pickle.dump(downloadedUrls, open(cacheFile,"w"))

def createFxd(item,filename):
    if "audio" in item.type:
        fullFilename=config.RSS_AUDIO+filename
    else:
        fullFilename=config.RSS_VIDEO+filename
    tempList=re.split("\.",filename)
    ofile=tempList[0]
    for line in tempList[1:-1]:
        ofile=ofile+"."+line
    ofile=ofile+".fxd"
    try:
       file = open(ofile, 'w')
       file.write('<freevo>\n')
       file.write('   <movie title="%s">\n'%item.title)
       file.write('      <video>\n')
       file.write('         <file id="f1">%s</file>\n'%fullFilename)
       file.write('      </video>\n')
       file.write('      <info>\n')
       file.write('         <plot>%s</plot>\n'%item.description)
       file.write('      </info>\n')
       file.write('   </movie>\n')
       file.write('</freevo>\n')
       file.close()
    except IOError:
       print "ERROR: Could not open %s"%(ofile)

def checkForUpdates():
    try:
       file = open(config.RSS_FEEDS,"r")
       for line in file:
           if not re.search("^#",line):
              (url,numberOfDays)=re.split(",", line)
              sock = urllib.urlopen(url)
              feedSource = sock.read()
              sock.close()
              for item in rssFeed.Feed(feedSource).items:
                  diff = datetime.date.today() - convertDate(item.date)
                  if int(diff.days)<=int(numberOfDays) and not re.search("None",item.url):
                     if "audio" in item.type:
                        os.chdir(config.RSS_AUDIO)
                     else:
                        os.chdir(config.RSS_VIDEO)
                     filename=re.split("/",item.url).pop()
                     if (len(glob.glob(filename))==0) and not checkForDup(item.url):
                        if re.search("torrent",item.url):
                           exitStatus=os.popen("bittorrent-console %s"%(item.url)).close()
                           filename=re.sub("\.torrent","",filename)
                        else:
                           exitStatus=os.popen("wget %s" %(item.url)).close()
                        if not exitStatus:
                           createFxd(item,filename)
                           addFileToCache(item.url)
                        else:
                           os.popen("rm %s" %(filename))
    except IOError:
       print "ERROR: Could not open %s"%(config.RSS_FEEDS)
