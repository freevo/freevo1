# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# web_types.py - Classes useful for the web interface.
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo:        
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


import os, sys, time

import config

from twisted.web.woven import page
from twisted.web.resource import Resource

DEBUG = config.DEBUG
TRUE = 1
FALSE = 0


class FreevoPage(page.Page):
    
    def __init__(self, model=None, template=None):
        print '__init__(self, model=\"%s\", template=\"%s\")' % (model, template)

        if not model:
            model = {'foo': 'bar'}
        if not template:
            template = '<html><head><title>ERROR</title></head>' + \
                       '<body>ERROR: no template</body></html>'

        page.Page.__init__(self, model, template=template)

        self.addSlash = 0


class FreevoResource(Resource):

    def render(self, request):
        print 'render(self, request=\"%s\")' % (request)
        username = request.getUser()
        password = request.getPassword()

        if not self.auth_user(username, password):
            request.setResponseCode(401, 'Authentication needed')
            # request.setHeader('Connection', 'close')
            request.setHeader('WWW-Authenticate', 'Basic realm="unknown"')
            request.setHeader('Content-Length', str(len('401: = Authorization needed.')))
            request.setHeader('Content-Type', 'text/html')
            return '<h1>401 Authentication required</h1>'
        else:
            return self._render(request)


    def auth_user(self, username, password):
        print 'auth_user(self, username=\"%s\", password=\"%s\")' % (username, password)
        realpass = config.WWW_USERS.get(username)
        if password == realpass:
            return TRUE
        else:
            return FALSE


class HTMLResource:

    def __init__(self):
        print '__init__(self)'
        self.res = ''


    def printContentType(self, content_type='text/html'):
        print 'printContentType(self, content_type=\"%s\")' % (content_type)
        self.res += 'Content-type: %s\n\n' % content_type


    def printHeader(self, title='unknown page', style=None, script=None, selected='Help', prefix=0):
        print 'printHeader(self, title=\"%s\", style=\"%s\", script=\"%s\", selected=\"%s\", prefix=\"%s\")' % \
            (title, style, script, selected, prefix)

        strprefix = '../' * prefix

        self.res += '<?xml version="1.0" encoding="'+ config.encoding +'"?>\n'
        self.res += '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        self.res += '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        #self.res += '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\n'
        #self.res += '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
        self.res += '<html>\n\t<head>\n'
        self.res += '\t<title>Freevo | '+title+'</title>\n'
        self.res += '\t<meta http-equiv="Content-Type" content= "text/html; charset='+ config.encoding +'"/>\n'
        if style != None:
            self.res += '\t<link rel="stylesheet" href="styles/main.css" type="text/css" />\n'
        if script != None:
            self.res += '\t<script language="JavaScript" type="text/JavaScript" src="'+script+'"></script>\n'
        self.res += '</head>\n'
        self.res += '\n\n\n\n<body>\n'
        # Header
        self.res += '<!-- Header Logo and Status Line -->\n'
        self.res += '<div id="titlebar"><span class="name">'\
            +'<a href="http://freevo.sourceforge.net/" target="_blank">Freevo</a></span></div>\n'
     
        items = [(_('Home'),_('Home'),'%sindex.rpy' % str(strprefix)),
                 (_('TV Guide'),_('View TV Listings'),'%sguide.rpy' % str(strprefix)),
                 (_('Scheduled Recordings'),_('View Scheduled Recordings'),'%srecord.rpy' % str(strprefix)),
                 (_('Favorites'),_('View Favorites'),'%sfavorites.rpy' % str(strprefix)),
                 (_('Media Library'),_('View Media Library'),'%slibrary.rpy' % str(strprefix)),
                 (_('Manual Recording'),_('Schedule a Manual Recording'),'%smanualrecord.rpy' % str(strprefix)),
                 (_('Search'),_('Advanced Search Page'),'%ssearch.rpy' % str(strprefix)),
                 (_('Help'),_('View Online Help and Documentation'),'%shelp/' % str(strprefix))]

        try:
            if config.ICECAST_WWW_PAGE:
                items.append((_('Icecast List'),_('Change Icecast List'),'%siceslistchanger.rpy' % (strprefix)))
        except AttributeError:
            pass

        self.res += '<div id="header">\n<ul>'

        for i in items:
            if selected == i[0]:
                self.res += '<li id="current">'
            else:
                self.res += '<li>'
            self.res += "<a href=\"%s\" title=\"%s\">%s</a></li>\n" % (i[2], i[1],i[0])
        self.res += '</ul>\n</div>'
        self.res += '\n<!-- Main Content -->\n';


    def tableOpen(self, opts=''):
        print 'tableOpen(self, opts=\"%s\")' % (opts)
        self.res += "<table "+opts+">\n"


    def tableClose(self):
        print 'tableClose(self)'
        self.res += "</table>\n"


    def tableHeadOpen(self, opts=''):
        print 'tableHeadOpen(self, opts=\"%s\")' % (opts)
        self.res += "  <thead "+opts+">\n"


    def tableHeadClose(self, opts=''):
        print 'tableHeadClose(self, opts=\"%s\")' % (opts)
        self.res += "  </thead>\n"


    def tableBodyOpen(self, opts=''):
        print 'tableBodyOpen(self, opts=\"%s\")' % (opts)
        self.res += "  <tbody "+opts+">\n"


    def tableBodyClose(self, opts=''):
        print 'tableBodyClose(self, opts=\"%s\")' % (opts)
        self.res += "  </tbody>\n"


    def tableFootOpen(self, opts=''):
        print 'tableFootOpen(self, opts=\"%s\")' % (opts)
        self.res += "  <tfoot "+opts+">\n"


    def tableFootClose(self, opts=''):
        print 'tableFootClose(self, opts=\"%s\")' % (opts)
        self.res += "  </tfoot>\n"


    def tableRowOpen(self, opts=''):
        print 'tableRowOpen(self, opts=\"%s\")' % (opts)
        self.res += "     <tr "+opts+">\n"


    def tableRowClose(self):
        print 'tableRowClose(self)'
        self.res += "     </tr>\n"


    def tableCell(self, data='', opts=''):
        print 'tableCell(self, data=\"%s\", opts=\"%s\")' % (data, opts)
        self.res += "       <td "+opts+">"+data+"</td>\n"


    def formValue(self, form=None, key=None):
        print 'formValue(self, form=\"%s\", key=\"%s\")' % (form, key)
        if not form or not key:
            return None

        try: 
            val = form[key][0]
        except: 
            val = None
    
        return val


    def printFooter(self):
        print 'printFooter(self)'
        self.res += '</body>\n</html>\n'
    
    
    def printSearchForm(self):
        print 'printSearchForm(self)'
        self.res += """
    <form id="SearchForm" action="search.rpy" method="get">
    <div class="searchform"><b>"""+_('Search')+""":</b><input type="text" name="find" size="20" /></div>
    </form>
    """

    def printAdvancedSearchForm(self):
        print 'printAdvancedSearchForm(self)'
        self.res += """
    <form id="SearchForm" action="search.rpy" method="get">
    <div class="searchform"><b>"""+_('Search')+""":</b><input type="text" name="find" size="20" />
    <input type="checkbox" selected=0 name="movies_only" />"""+_('Movies only')+"""
    <input type="submit" value=" """+_('Go!')+""" " />
    </div>
    </form>
    """

    def printMessages(self, messages):
        print 'printMessages(self, messages=\"%s\")' % (messages)
        self.res += "<h4>"+_("Messages")+":</h4>\n"
        self.res += "<ul>\n"
        for m in messages:
            self.res += "   <li>%s</li>\n" % m
            self.res += "</ul>\n"

    def printMessagesFinish(self, messages):
        """
        Print messages and add the search form, links and footer.
        """
        print 'printMessagesFinish(self, messages=\"%s\")' % (messages)
        self.printMessages( messages )
        self.printSearchForm()
        self.printLinks()
        self.printFooter()
        
    def printLinks(self, prefix=0):
        print 'printLinks(self, prefix=\"%s\")' % (prefix)
        #   
        #try:
        #    if config.ICECAST_WWW_PAGE:
        #        self.res += '<a href="%siceslistchanger.rpy">Change Icecast List</a>' % strprefix
        #except AttributeError:
        #    pass
        return

    def printBreadcrumb(self, media, mediadirs, dir):
        print 'printBreadcrumb(self, media=\"%s\", mediadirs=\"%s\", dir=%r)' % (media, mediadirs, dir)
        breadcrumb='<a href="library.rpy">Home: </a><a href="library.rpy?media='+media+'&dir=">'+media+'</a>'
        _url = ""
        url = dir.split("/")
        _mediadir = mediadirs[0][1].split("/")
        for i in url:
            _url += i + "/"
            if i not in _mediadir or i == _mediadir[len(_mediadir)-1]:
                breadcrumb += '/<a href="library.rpy?media='+media+'&dir='+_url+'">'+Unicode(i)+'</a>'

        return breadcrumb
    
    def printPassword(self, password):
        print 'printPassword(self, password=\"%s\")' % (password)
        self.res += """<script language="JavaScript"> <!--

        var password;

        var pass1=""" + password + """;

        password=prompt('Please enter your password to view this page!',' ');

        if (password!=pass1){
            alert('Password Incorrect, redirected...');
            window.location="library.rpy";
        }
        //-->
        </script>"""
        
    def printImagePopup(self):
        print 'printImagePopup(self)'
        self.res += """<script language="JavaScript" type="text/javascript" style="display:none;">
        function openfoto(loc,width,height){
            var params="toolbar=no,location=no,status=no,menubar=no,resizable=no,scrollbars=no,top=0,left=0,width="+width+",height="+height;
            foto = window.open("fileinfo.rpy?img="+loc,"Images",params);
        }
        </script> """

