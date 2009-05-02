# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Classes useful for the web interface.
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
import base64
import crypt
import re

import os, sys, time

import config
import socket

from twisted.web.woven import page
from twisted.web.resource import Resource
from tv.record_client import RecordClient

TRUE = 1
FALSE = 0


_singleton = None

def RecordClientResource():
    global _singleton

    # One-time init
    if _singleton is None:
        _singleton = RecordClientActions()

    return _singleton



class RecordClientActions:
    """
    """
    def __init__(self):
        import kaa
        self.recordclient = RecordClient()
        kaa.inprogress(self.recordclient.channel).wait()


    def __call__(self):
        return RecordClientResource().recordclient



class FreevoPage(page.Page):
    """
    """
    def __init__(self, model=None, template=None):
        #print 'FreevoPage.__init__(model=%r, template=%r)' % (model, template)

        if not model:
            model = {'foo': 'bar'}
        if not template:
            template = '<html><head><title>ERROR</title></head>' + \
                       '<body>ERROR: no template</body></html>'

        page.Page.__init__(self, model, template=template)

        self.addSlash = 0


class FreevoResource(Resource):
    """
    Base class of webpages which handels the authentication.

    All webpages should be subclasses of this class.
    The subclasses must not have a render method
    but they need a _render method instead.
    When a webpage is opened by the user then first the render method
    of this base class is called and then if the authentication was successfull
    the _render method of the subclass is called.
    Otherwise a error messages is returned and shown to the user.
    """
    def render(self, request):
        """
        render method of this class.

        This method will be called when a user requests this page.
        It only handels the authentication but does not present any
        content.If authentication is successfull this method returns the
        _render method, which does the actuall work.
        """
        # get username and password from the user
        username = request.getUser()
        password = request.getPassword()

        if not self.auth_user(username, password):
            # authentication fails, thus we send 401 error
            request.setResponseCode(401, 'Authentication needed')
            # still we have to create a few things for the header
            request.setHeader('WWW-Authenticate', 'Basic realm="unknown"')
            request.setHeader('Content-Length', str(len('401: = Authorization needed.')))
            request.setHeader('Content-Type', 'text/html')
            # this is for the body of the html document
            return '<h1>401 Authentication required</h1>'
        else:
            # authentication was successfull
            # thus we return the self._render method
            # which hopefully will do something usefull
            self.session = request.getSession()
            return self._render(request)


    def auth_user(self, username, password):
        """
        Check of username and password

        This method validates username and password.
        If authentication is successfull it returns True otherwise False.
        """
        #print 'auth_user(username=%r, password=%r)' % (username, '******')
        cryptpass = config.WWW_USERS.get(username)
        if not cryptpass:
            return False
        m = re.match(r'^(\$1\$[a-zA-Z\d/.]{8}\$)', cryptpass)
        if m:
            # Password is in crypt()ed form.
            return cryptpass == crypt.crypt(password, m.group(1))
        # Assume password is stored as plaintext
        return cryptpass == password



class HTMLResource:
    """
    HTML elements of a freevo webpage

    This class provides many usefull elements which can be used
    in a webpage. It provides a string called res which should be used to
    build up the html string that should form the content of a webpage.
    Usage: Create a instance of this class in the _render method of the
    subclass which represents the webpage, use all this methods to build
    the html string  and return HTMLResource.res in the end.
    """
    def __init__(self):
        # create empty result string which must be filled with life
        self.res =''


    def printContentType(self, content_type='text/html'):
        """Content"""
        # debug print
        #print 'printContentType(content_type=%r)' % (content_type)
        # adding new text
        self.res += 'Content-type: %s\n\n' % content_type


    def printHeader(self, title='unknown page', style=None, script=None, rss=None, selected='Help', prefix=0):
        """
        Header

        This produces the header of a freevo page with the navigation bar.

        @param title:    title of the webpage
        @param style:    style sheet to use for this page
        @param script:   java script to use  for this page
        @param selected: which tab in the tabline should be highlighed
        @param prefix:   how many directory levels is this file below the main level
            this is needed for the links in the navigation bar.
        """

        # debug print
        #print 'printHeader(title=%r, style=%r, script=%r, selected=%r, prefix=%r)' % \
        #    (title, style, script, selected, prefix)

        # we are prefix level below the main directory thus we must go prefix times up,
        # before we are in the same directory than those pages that are in the navigation bar.
        # This is needed for creating the links in the navigation bar.
        strprefix = '../' * prefix

        # now we can start to create the header:

        # doc type
        #self.res += '<?xml version="1.0" encoding="'+ config.encoding +'"?>\n'
        self.res += '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" '
        self.res += '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'

        # <html> and <head> tag
        self.res += '<html>\n\t<head>\n'
        # <title>
        self.res += '\t<title>Freevo | '+title+'</title>\n'
        # meta tags, encoding is taken from the users config
        self.res += '\t<meta http-equiv="Content-Type" content= "text/html; charset='+ config.encoding +'"/>\n'
        self.res += '\t<link rel="shortcut icon" href="/favicon.ico" />\n'
        # css style sheet
        if style != None:
            self.res += '\t<link rel="stylesheet" href="styles/main.css" type="text/css" media="screen" />\n'
        # java script
        if script != None:
            self.res += '\t<script language="JavaScript" type="text/JavaScript" src="'+script+'"></script>\n'
        # rss
        if rss is not None:
            self.res += '\t<link rel="alternate" href="'+rss+'" type="application/rss+xml" title="" id="gallery" />\n'
        # end of <head>
        self.res += '</head>\n'
        # here starts the body
        self.res += '\n\n\n\n<body>\n'
        # header of the page with tab bar
        self.res += '<!-- Header Logo and Status Line -->\n'
        # headline
        self.res += '<div id="titlebar"><span class="name">'\
            +'<a href="http://freevo.sourceforge.net/" target="_blank">Freevo</a></span></div>\n'
        # start the bar, it is build as a list
        self.res += '<div id="header">\n<ul>'
        # this items should be shown in the tab bar
        items = []
        for label, title, link in config.WWW_PAGES:
            items.append((label, title, os.path.join(str(strprefix), link)))
        # maybe also a personal web pages
        if hasattr(config, 'WWW_PERSONAL_PAGE'):
            for page in config.WWW_PERSONAL_PAGE:
                items.append((page[0], page[1], os.path.join(str(strprefix), page[2])))
        if hasattr(config, 'WWW_ICECAST_PAGE') and config.WWW_ICECAST_PAGE:
            items.append((_('Icecast List'),_('Change Icecast List'),'%siceslistchanger.rpy' % (strprefix)))
        # go through the items and create the bar
        for i in items:
            if selected == i[0]:
                # this item is selected, thus we highlight the tab
                self.res += '<li id="current">'
            else:
                self.res += '<li>'
            self.res += "<a href=\"%s\" title=\"%s\">%s</a></li>\n" % (i[2], i[1],i[0])
        # end of the bar list
        self.res += '</ul>\n</div>'
        # now we are ready for the main content
        self.res += '\n<!-- Main Content -->\n';


    def tableOpen(self, opts=''):
        """
        Opens a table

        opts are additional parameters for the <table> tag.
        """
        #print 'tableOpen(opts=%r)' % (opts)
        self.res += "<table "+opts+">\n"


    def tableClose(self):
        """
        Close a table
        """
        #print 'tableClose()'
        self.res += "</table>\n"


    def tableHeadOpen(self, opts=''):
        """
        Open a table header line

        opts are additional parameters for the <thead> tag.
        """
        #print 'tableHeadOpen(opts=%r)' % (opts)
        self.res += "  <thead "+opts+">\n"


    def tableHeadClose(self, opts=''):
        """
        Closes a table header line
        """
        #print 'tableHeadClose(opts=%r)' % (opts)
        self.res += "  </thead>\n"


    def tableBodyOpen(self, opts=''):
        """
        Opens a table body

        opts are additional parameter for the <tbody> tag
        """
        #print 'tableBodyOpen(opts=%r)' % (opts)
        self.res += "  <tbody "+opts+">\n"


    def tableBodyClose(self, opts=''):
        """
        Closes a table body
        """
        #print 'tableBodyClose(opts=%r)' % (opts)
        self.res += "  </tbody>\n"


    def tableFootOpen(self, opts=''):
        """
        Opens a table footer

        opts are additional parameters for the <tfoot> tag.
        """
        #print 'tableFootOpen(opts=%r)' % (opts)
        self.res += "  <tfoot "+opts+">\n"


    def tableFootClose(self, opts=''):
        """
        Closes a table footer.
        """
        #print 'tableFootClose(opts=%r)' % (opts)
        self.res += "  </tfoot>\n"


    def tableRowOpen(self, opts=''):
        """
        Opens a table row

        opts are additonal parameters for the <tr> tag
        """
        #print 'tableRowOpen(opts=%r)' % (opts)
        self.res += "     <tr "+opts+">\n"


    def tableRowClose(self):
        """
        Closes a table row
        """
        #print 'tableRowClose()'
        self.res += "     </tr>\n"


    def tableCell(self, data='', opts=''):
        """
        Creates a table cell

        opts are additonal parameters for the <td>.
        data is the content of this table cell.
        """
        #print 'tableCell(data=%r, opts=%r)' % (data, opts)
        self.res += "       <td "+opts+">"+data+"</td>\n"


    def formValue(self, form=None, key=None):
        #print 'formValue(form=%r, key=%r)' % (form, key)
        if not form or not key:
            return None
        try:
            val = form[key][0]
        except:
            val = None

        return val


    def printFooter(self):
        """
        Closes the html document
        """
        #print 'printFooter()'
        self.res += '</body>\n</html>\n'


    def printSearchForm(self):
        """
        Creates the simple search form"""

        #print 'printSearchForm()'
        self.res += """
    <form id="SearchForm" action="search.rpy" method="get">
    <div class="searchform"><b>"""+_('Search')+""":</b><input type="text" name="find" size="20" /></div>
    </form>
    """


    def printAdvancedSearchForm(self):
        """
        Creates the advanced search form.

        This search form has an additonal checkbox and a go button
        """

        #print 'printAdvancedSearchForm()'
        self.res += """
    <form id="SearchForm" action="search.rpy" method="get">
    <div class="searchform"><b>"""+_('Search')+""":</b><input type="text" name="find" size="20" />
    <input type="checkbox" selected=0 name="movies_only" />"""+_('Movies only')+"""
    <input type="submit" value=" """+_('Go!')+""" " />
    </div>
    </form>
    """


    def printMessages(self, messages):
        """
        Prints a message
        """
        #print 'printMessages(messages=%r)' % (messages)
        self.res += "<h4>"+_("Messages")+":</h4>\n"
        self.res += "<ul>\n"
        for m in messages:
            self.res += "   <li>%s</li>\n" % m
            self.res += "</ul>\n"


    def printMessagesFinish(self, messages):
        """
        Print messages and add the search form, links and footer.
        """
        #print 'printMessagesFinish(messages=%r)' % (messages)
        self.printMessages( messages )
        self.printSearchForm()
        self.printLinks()
        self.printFooter()


    def printLinks(self, prefix=0):
        """
        Print Link
        """
        # seems to do nothing at the moment ????
        #print 'printLinks(prefix=%r)' % (prefix)
        #
        #try:
        #    if config.WWW_ICECAST_PAGE:
        #        self.res += '<a href="%siceslistchanger.rpy">Change Icecast List</a>' % strprefix
        #except AttributeError:
        #    pass
        return


    def printBreadcrumb(self, media, mediadirs, dir):
        """
        ???
        """
        #print 'printBreadcrumb(media=%r, mediadirs=%r, dir=%r)' % (media, mediadirs, dir)
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
        """
        ???
        """
        #print 'printPassword(password=%r)' % (password)
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
        """
        Opens a Popup to display an image
        """
        #print 'printImagePopup()'
        self.res += """<script language="JavaScript" type="text/javascript" style="display:none;">
        var width = 0;
        var height = 0;
        var max_width = screen.availWidth;
        var max_height = screen.availHeight - 250;
        var client_width = 0;
        var client_height = 0;

        function openfoto(loc,width_img,height_img){
            width = width_img;
            height = height_img;

            if (width >= max_width || height >= max_height) {
                getNewSize();
            }
            var params="toolbar=no,location=no,status=no,menubar=yes,resizable=no,top=0,left=0,width="+width+",height="+height;
            foto = Lightbox.show(''+loc+'', '', 'width='+width+', height='+height+'');
         }

         function getNewSize(){
            // recalculate width / height maintaining aspect
            if (max_width / max_height > width / height) {
                width = Math.round(max_height * width / height);
                height = max_height;
            }
            else {
                height = Math.round(max_width * height / width);
                width = max_width;
            }
        }
        </script> """


    def printWebRemote(self):
        """
        Prints web remote

        If configured to do so,
        then this displays a remote to control freevo
        via the web browser
        """
        #print 'printWebRemote()'
        if not (config.ENABLE_NETWORK_REMOTE == 1 and config.REMOTE_CONTROL_PORT):
            self.res += "no remote enabled"

        self.res += u"""
           <style type="text/css" media="screen">
            table.remote { width: auto; }
            td.remote    { padding: 0px; }
            button.remote { width: 60px; height: 18px; background: #eee; font-size: 12px;
                text-align: center; padding: 0; }
            button.remote:hover { background: #fed; }
           </style>

           <script type="text/javascript">
           <!--
             // AJAX Functions
             var xmlHttp = false;
             var remoteWin = 0;

             function getXMLHttpObject () {
               if (window.XMLHttpRequest) {
                 xmlHttp=new XMLHttpRequest()
               }
               else if (window.ActiveXObject) {
                 xmlHttp=new ActiveXObject("Microsoft.XMLHTTP")
               }
               return xmlHttp
               try {
                 xmlHttp = new ActiveXObject("Msxml2.XMLHTTP");      // Internet Explorer 1st try
               } catch (e) {
                 try {
                   xmlHttp = new ActiveXObject("Microsoft.XMLHTTP"); // Internet Explorer 2nd try
                 } catch (e2) {
                   xmlHttp = false;
                 }
               }
               if (!xmlHttp && typeof XMLHttpRequest != 'undefined') {
                 xmlHttp = new XMLHttpRequest();                     // Mozilla, Firefox, Opera
               }
             }

             function send_code( code ) {
               if (! xmlHttp)
                 getXMLHttpObject();
               var url = 'webremote.rpy?code=' + code + '&sid=' + Math.random();
               xmlHttp.open('GET', url, true);
               xmlHttp.send(null);
             }

            function openremote(){
              if(remoteWin) {
                if(!remoteWin.closed) {remoteWin.focus();}
                }
              var params="toolbar=no,location=no,status=no,menubar=no,resizable=no,scrollbars=no,top=0,left=0";
              remoteWin = window.open("webremote.rpy","WebRemote",params);
              remoteWin.focus();
            }
           -->
           </script>
        <br />
        <table border="0" cellspacing="0" cellpadding="0" class="remote">
        <tr><td colspan="3" align="center"><a href="javascript:openremote()">Freevo WebRemote</a></td></tr>
        </table>
        """
