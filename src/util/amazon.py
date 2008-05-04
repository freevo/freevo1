# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# This is the Freevo module for processing Amazon data
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:
#
# -----------------------------------------------------------------------
# Freevo - A Home Theater PC framework
# Copyright (C) 2002 Mark Pilgrim"
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

"""Python wrapper for Amazon web APIs

This module allows you to access Amazon's web APIs, to do things like search
Amazon and get the results programmatically.  Described here:
http://www.amazon.com/webservices

You need a Amazon-provided license key to use these services.  Follow the link
above to get one.  These functions will look in several places (in this order)
for the license key:
    - the "license_key" argument of each function
    - the module-level LICENSE_KEY variable (call setLicense once to set it)
    - an environment variable called AMAZON_LICENSE_KEY
    - a file called ".amazonkey" in the current directory
    - a file called "amazonkey.txt" in the current directory
    - a file called ".amazonkey" in your home directory
    - a file called "amazonkey.txt" in your home directory
    - a file called ".amazonkey" in the same directory as amazon.py
    - a file called "amazonkey.txt" in the same directory as amazon.py

Sample usage::

    >>> import amazon
    >>> amazon.setLicense('...') # must get your own key!
    >>> pythonBooks = amazon.searchByKeyword('Python')
    >>> pythonBooks[0].ProductName
    u'Learning Python (Help for Programmers)'
    >>> pythonBooks[0].URL
    ...
    >>> pythonBooks[0].OurPrice
    ...

Other available functions:
    - browseBestSellers
    - searchByASIN
    - searchByUPC
    - searchByAuthor
    - searchByArtist
    - searchByActor
    - searchByDirector
    - searchByManufacturer
    - searchByListMania
    - searchSimilar
    - searchByWishlist

Other usage notes:
    - Most functions can take product_line as well, see source for possible values
    - All functions can take ResponseGroup="Medium" to get less detail in results
    - All functions can take page=N to get second, third, fourth page of results
    - All functions can take license_key="XYZ", instead of setting it globally
    - All functions can take http_proxy="http://x/y/z" which overrides your system setting
"""

__author__ = "Mark Pilgrim (f8dy@diveintomark.org)"
__version__ = "0.62"
__cvsversion__ = "$Revision$"[11:-2]
__date__ = "$Date$"[7:-2]
__copyright__ = "Copyright (c) 2002 Mark Pilgrim"
__license__ = "Python"
# Powersearch and return object type fix by Joseph Reagle <geek@goatee.net>
# Locale support by Michael Josephson <mike@josephson.org>

from xml.dom import minidom
from xml.dom.ext import PrettyPrint
from xml.parsers import expat
import os, sys, getopt, cgi, urllib, string
try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(10)
except ImportError:
    pass

LICENSE_KEY = None
HTTP_PROXY = None
LOCALE = "us"

# don't touch the rest of these constants
class AmazonError(Exception): pass
class NoLicenseKey(Exception): pass
_amazonfile1 = ".amazonkey"
_amazonfile2 = "amazonkey.txt"
_licenseLocations = (
    (lambda key: key, 'passed to the function in license_key variable'),
    (lambda key: LICENSE_KEY, 'module-level LICENSE_KEY variable (call setLicense to set it)'),
    (lambda key: os.environ.get('AMAZON_LICENSE_KEY', None), 'an environment variable called AMAZON_LICENSE_KEY'),
    (lambda key: _contentsOf(os.getcwd(), _amazonfile1), '%s in the current directory' % _amazonfile1),
    (lambda key: _contentsOf(os.getcwd(), _amazonfile2), '%s in the current directory' % _amazonfile2),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _amazonfile1), '%s in your home directory' % _amazonfile1),
    (lambda key: _contentsOf(os.environ.get('HOME', ''), _amazonfile2), '%s in your home directory' % _amazonfile2),
    (lambda key: _contentsOf(_getScriptDir(), _amazonfile1), '%s in the amazon.py directory' % _amazonfile1),
    (lambda key: _contentsOf(_getScriptDir(), _amazonfile2), '%s in the amazon.py directory' % _amazonfile2)
    )
_supportedLocales = {
    'ca': ('ca', 'ecs.amazonaws.ca'),
    'de': ('de', 'ecs.amazonaws.de'),
    'fr': ('fr', 'ecs.amazonaws.fr'),
    'jp': ('jp', 'ecs.amazonaws.jp'),
    'uk': ('uk', 'ecs.amazonaws.co.uk'),
    'us': (None, 'ecs.amazonaws.com'),
}

## administrative functions
def version():
    print """PyAmazon %(__version__)s
%(__copyright__)s
released %(__date__)s
""" % globals()

## utility functions

def setLocale(locale):
    """set locale"""
    global LOCALE
    if _supportedLocales.has_key(locale):
        LOCALE = locale
    else:
        raise AmazonError, ("Unsupported locale. Locale must be one of: %s" %
            string.join(_supportedLocales, ", "))

def getLocale():
    """get locale"""
    return LOCALE

def setLicense(license_key):
    """set license key"""
    global LICENSE_KEY
    LICENSE_KEY = license_key

def getLicense(license_key = None):
    """get license key

    license key can come from any number of locations;
    see module docs for search order"""
    for get, location in _licenseLocations:
        rc = get(license_key)
        if rc: return rc
    raise NoLicenseKey, 'get a license key at http://www.amazon.com/webservices'

def setProxy(http_proxy):
    """set HTTP proxy"""
    global HTTP_PROXY
    HTTP_PROXY = http_proxy

def getProxy(http_proxy = None):
    """get HTTP proxy"""
    return http_proxy or HTTP_PROXY

def getProxies(http_proxy = None):
    http_proxy = getProxy(http_proxy)
    if http_proxy:
        proxies = {"http": http_proxy}
    else:
        proxies = None
    return proxies

def _contentsOf(dirname, filename):
    filename = os.path.join(dirname, filename)
    if not os.path.exists(filename): return None
    fsock = open(filename)
    contents = fsock.read()
    fsock.close()
    return contents

def _getScriptDir():
    if __name__ == '__main__':
        return os.path.abspath(os.path.dirname(sys.argv[0]))
    else:
        return os.path.abspath(os.path.dirname(sys.modules[__name__].__file__))

class Bag: pass

def unmarshal(element):
    rc = Bag()
    if isinstance(element, minidom.Element) and (element.tagName == 'Details'):
        rc.URL = element.attributes["url"].value
    childElements = [e for e in element.childNodes if isinstance(e, minidom.Element)]
    if childElements:
        for child in childElements:
            key = child.tagName
            if hasattr(rc, key):
                if type(getattr(rc, key)) <> type([]):
                    setattr(rc, key, [getattr(rc, key)])
                setattr(rc, key, getattr(rc, key) + [unmarshal(child)])
            elif isinstance(child, minidom.Element) and (child.tagName == 'Details'):
                # make the first Details element a key
                setattr(rc,key,[unmarshal(child)])
                #dbg: because otherwise 'hasattr' only tests
                #dbg: on the second occurence: if there's a
                #dbg: single return to a query, it's not a
                #dbg: list. This module should always
                #dbg: return a list of Details objects.
            else:
                setattr(rc, key, unmarshal(child))
    else:
        rc = "".join([e.data for e in element.childNodes if isinstance(e, minidom.Text)])
        if element.tagName == 'SalesRank':
            rc = int(rc.replace(',', ''))
    return rc

def buildURL(operation, search_type, keyword, product_line, type, page, license_key):
    url = 'http://' + _supportedLocales[LOCALE][1] + '/onca/xml?Service=AWSECommerceService'
    url += '&AWSAccessKeyId=%s' % license_key.strip()
    url += '&Operation=%s' % operation
    url += '&AssociateTag=%s' % 'devconn-20'
    url += '&ResponseGroup=%s' % type
    if _supportedLocales[LOCALE][0]:
        url += '&Locale=%s' % _supportedLocales[LOCALE][0]
    if page:
        url += '&page=%s' % page
    if product_line:
        url += '&SearchIndex=%s' % product_line
    url += '&%s=%s' % (search_type, urllib.quote(keyword))
    return url


## main functions


def search(operation, search_type, keyword, product_line, type="Large", page=None,
           license_key = None, http_proxy = None):
    """search Amazon

    You need a license key to call this function; see
    http://www.amazon.com/webservices
    to get one.  Then you can either pass it to
    this function every time, or set it globally; see the module docs for details.

    Parameters:

    @param operation: in (TagLookup, ListLookup, CartGet, SellerListingLookup,
        CustomerContentLookup, ItemLookup, SimilarityLookup, SellerLookup,
        ItemSearch, VehiclePartLookup, BrowseNodeLookup, CartModify, ListSearch,
        CartClear, VehiclePartSearch, CustomerContentSearch, CartCreate,
        TransactionLookup, VehicleSearch, SellerListingSearch, CartAdd, Help)

    @param keyword: keyword to search

    @param search_type: in (KeywordSearch, BrowseNodeSearch, AsinSearch,
        UpcSearch, AuthorSearch, ArtistSearch, ActorSearch, DirectorSearch,
        ManufacturerSearch, ListManiaSearch, SimilaritySearch)

    @param product_line: type of product to search for.  restrictions based on search_type
        UpcSearch - in (music, classical)
        AuthorSearch - must be "Books"
        ArtistSearch - in (Music, classical)
        ActorSearch - in (dvd, vhs, video)
        DirectorSearch - in (dvd, vhs, video)
        ManufacturerSearch - in (electronics, kitchen, videogames, software, photo, pc-hardware)

    @param http_proxy: (optional) - address of HTTP proxy to use for sending and receiving REST messages

    @returns: list of Bags, each Bag may contain the following attributes:
        Asin - Amazon ID ("ASIN" number) of this item
        Authors - list of authors
        Availability - "available", etc.
        BrowseList - list of related categories
        Catalog - catalog type ("Book", etc)
        CollectiblePrice - ?, format "$34.95"
        ImageUrlLarge - URL of large image of this item
        ImageUrlMedium - URL of medium image of this item
        ImageUrlSmall - URL of small image of this item
        Isbn - ISBN number
        ListPrice - list price, format "$34.95"
        Lists - list of ListMania lists that include this item
        Manufacturer - manufacturer
        Media - media ("Paperback", "Audio CD", etc)
        NumMedia - number of different media types in which this item is available
        OurPrice - Amazon price, format "$24.47"
        ProductName - name of this item
        ReleaseDate - release date, format "09 April, 1999"
        Reviews - reviews (AvgCustomerRating, plus list of CustomerReview with Rating, Summary, Content)
        SalesRank - sales rank (integer)
        SimilarProducts - list of Product, which is ASIN number
        ThirdPartyNewPrice - ?, format "$34.95"
        URL - URL of this item
    """
    license_key = getLicense(license_key)
    url = buildURL(operation, search_type, keyword, product_line, type, page, license_key)
    print 'url=%r ' % (url,)
    print 'buildURL(operation=%r, search_type=%r, keyword=%r, product_line=%r, type=%r, page=%r, license_key=%r)' % \
        (operation, search_type, keyword, product_line, type, page, license_key)
    proxies = getProxies(http_proxy)
    print 'proxies=%r = getProxies(http_proxy=%r)' % (proxies, http_proxy)
    u = urllib.FancyURLopener(proxies)
    usock = u.open(url)
    reply = usock.read()
    usock.close()

    # remove
    open(os.path.join('/tmp', 'amazon.reply'), 'w').write(reply)

    try:
        #xmldoc = minidom.parse(usock)
        xmldoc = minidom.parseString(reply)
    except expat.ExpatError, why:
        print why
        raise AmazonError, why

    PrettyPrint(xmldoc)

    usock.close()
    data = unmarshal(xmldoc)
    if hasattr(data, 'Errors'):
        raise AmazonError, data.Errors.Error.Message
    if hasattr(data, 'ItemSearchResponse.Items.Request.Errors'):
        raise AmazonError, data.Items.Request.Errors.Message
    return data.ItemSearchResponse.Items

def searchByKeyword(keyword, product_line="Books", type="Large", page=1, license_key=None, http_proxy=None):
    return search('ItemSearch', 'Keywords', keyword, product_line, type, page, license_key, http_proxy)

def browseBestSellers(browse_node, product_line="Books", type="Large", page=1, license_key=None, http_proxy=None):
    return search('ItemLookup', 'BrowseNode', browse_node, product_line, type, page, license_key, http_proxy)

def searchByASIN(ASIN, type="Large", license_key=None, http_proxy=None):
    return search('AsinSearch', ASIN, None, type, None, license_key, http_proxy)

def searchByUPC(UPC, type="Large", license_key=None, http_proxy=None):
    return search('UpcSearch', UPC, None, type, None, license_key, http_proxy)

def searchByAuthor(author, type="Large", page=1, license_key=None, http_proxy=None):
    return search('AuthorSearch', author, 'Books', type, page, license_key, http_proxy)

def searchByArtist(artist, product_line="Music", type="Large", page=1, license_key=None, http_proxy=None):
    if product_line not in ('Music', 'classical'):
        raise AmazonError, 'product_line must be in ("Music", "classical")'
    return search('ArtistSearch', artist, product_line, type, page, license_key, http_proxy)

def searchByActor(actor, product_line='dvd', type='Large', page=1, license_key=None, http_proxy=None):
    if product_line not in ('dvd', 'vhs', 'video'):
        raise AmazonError, 'product_line must be in ("dvd", "vhs", "video")'
    return search('ActorSearch', actor, product_line, type, page, license_key, http_proxy)

def searchByDirector(director, product_line='dvd', type='Large', page=1, license_key=None, http_proxy=None):
    if product_line not in ('dvd', 'vhs', 'video'):
        raise AmazonError, 'product_line must be in ("dvd", "vhs", "video")'
    return search('DirectorSearch', director, product_line, type, page, license_key, http_proxy)

def searchByManufacturer(manufacturer, product_line='pc-hardware', type='Large', page=1, license_key=None, http_proxy=None):
    if product_line not in ('electronics', 'kitchen', 'videogames', 'software', 'photo', 'pc-hardware'):
        raise AmazonError, 'product_line must be in ("electronics", "kitchen", "videogames", "software", "photo", "pc-hardware")'
    return search('ManufacturerSearch', manufacturer, product_line, type, page, license_key, http_proxy)

def searchByListMania(listManiaID, type='Large', page=1, license_key=None, http_proxy=None):
    return search('ListManiaSearch', listManiaID, None, type, page, license_key, http_proxy)

def searchSimilar(ASIN, type='Large', page=1, license_key=None, http_proxy=None):
    return search('SimilaritySearch', ASIN, None, type, page, license_key, http_proxy)

def searchByWishlist(wishlistID, type='Large', page=1, license_key=None, http_proxy=None):
    return search('WishlistSearch', wishlistID, None, type, page, license_key, http_proxy)

def searchByPower(keyword, product_line='Books', type='Large', page=1, license_key=None, http_proxy=None):
    return search('PowerSearch', keyword, product_line, type, page, license_key, http_proxy)
    # >>> RecentKing = amazon.searchByPower('author:Stephen King and pubdate:2003')
    # >>> SnowCrash = amazon.searchByPower('title:Snow Crash')


if __name__ == '__main__':
    #covers = searchByKeyword('The Who', product_line='Music', type='Images')
    covers = searchByKeyword('The Who', product_line='Music', type='Medium')
    print covers.__dict__
    if hasattr(covers, 'Item'):
        for item in covers.Item:
            print item.__dict__
            if hasattr(item, 'LargeImage'):
                print item.LargeImage.__dict__
