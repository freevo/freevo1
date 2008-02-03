#!/usr/bin/env python

__author__="Andrew Pennebaker (andrew.pennebaker@gmail.com)"
__date__="3 Nov 2005 - 14 Feb 2007"
__copyright__="Copyright 2006 2007 Andrew Pennebaker"
__license__="GPL"
__version__="0.5"
__URL__="http://snippets.dzone.com/posts/show/2887"

from urllib import urlopen
import os
import math
import time
import sys
from getopt import getopt

def optimum_k_exp(num_bytes):
    const_1k = 1024
    if num_bytes == 0:
        return 0
    return long(math.log(num_bytes, const_1k))

def format_bytes(num_bytes):
    const_1k = 1024
    try:
        exp = optimum_k_exp(num_bytes)
        suffix = 'bkMGTPEZY'[exp]
        if exp == 0:
            return '%s%s' % (num_bytes, suffix)
        converted = float(num_bytes) / float(const_1k**exp)
        return '%.2f%s' % (converted, suffix)
    except IndexError:
        sys.exit('Error: internal error formatting number of bytes.')


# Calculate ETA and return it in string format as MM:SS
def calc_eta(start, now, total, current):
    if current == 0:
        return '--:--'
    rate = float(current) / (now - start)
    eta = long((total - current) / rate)
    eta_mins = eta / 60
    eta_secs = eta % 60
    if eta_mins > 99:
        return '--:--'
    return '%02d:%02d' % (eta_mins, eta_secs)

# Calculate speed and return it in string format
def calc_speed(start, now, bytes):
    if bytes == 0:
        return 'N/A b'
    return format_bytes(float(bytes) / (now - start))

def cond_print(str):
    sys.stdout.write(str)
    sys.stdout.flush()

def getURLName(url):
    name = url.split("/")[-1]
    return name

def createDownload(url, proxy=None):
    instream=urlopen(url, None, proxy)

    filename=instream.info().getheader("Content-Length")
    if filename==None:
        filename="temp"

    return (instream, filename)

def download(instream, outstream):
    outstream.write(instream.read())

    outstream.close()

def usage():
    print "Usage: %s [options] <url1 url2 url3 ...>" % (sys.argv[0])
    print "\n--httpproxy <proxy>"
    print "--ftpproxy <proxy>"
    print "--gopherproxy <proxy>"
    print "\n--help (usage)"

    sys.exit()

def main():
    systemArgs=sys.argv[1:] # ignore program name
    start_time = time.time()

    urls=[]
    proxies={}

    optlist=[]
    args=[]

    try:
        optlist, args=getopt(systemArgs, None, ["url=", "httpproxy=", "ftpproxy=", "gopherproxy=", "help"])
    except Exception, e:
        usage()

    if len(args)<1:
        usage()

    for option, value in optlist:
        if option=="--help":
            usage()

        elif option=="--httpproxy":
            proxies["http"]=value
        elif option=="--ftpproxy":
            proxies["ftp"]=value
        elif options=="--gopherproxy":
            proxies["gopher"]=value

    urls=args

    for url in urls:

        outfile = getURLName(url)
        print outfile
        fileName= outfile.split(os.sep)[-1]
        fName = fileName
        fileName= "partfile" + fileName
        print "fName - " + fName
        print "fileName - " + fileName

#               try:

        outfile=open(fileName, "wb")
        url, length=createDownload(url, proxies)
        if not length:
            length="?"

        print "Downloading %s (%s bytes) ..." % (url.url, length)
        if length!="?":
            length=float(length)
        bytesRead=0.0

        for line in url:
            bytesRead+=len(line)

            if length!="?":
                status = "%s: %.02f/%.02f kb (%d%%)" % (
                        fileName,
                        bytesRead/1024.0,
                        length/1024.0,
                        100*bytesRead/length
                )
                percent = (100*bytesRead/length)
                percent_str = '%.1f' % percent
                counter = format_bytes(bytesRead)
                video_len_str = format_bytes(length)
                speed = calc_speed(start_time,time.time(),bytesRead)
                eta = calc_eta(start_time, time.time(), length, bytesRead)
                cond_print('\rRetrieving video data: %5s%% (%8s of %s) at %s ETA %s ' % (percent_str, counter, video_len_str,speed,eta))
#                               print status

            outfile.write(line)

        url.close()
        outfile.close()

#               except Exception, e:
#                       print "Error downloading %s: %s" % (url, e)
        os.rename(fileName,fName)



if __name__=="__main__":
    main()
