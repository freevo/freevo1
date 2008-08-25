# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to display and modify your video library
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo: -allow for an imdb popup
#       -stream tv, video and music somehow
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

import sys, os, stat, string, urllib, re, types


# needed to put these here to suppress its output
import config, util
import util.tv_util as tv_util
import util.fxdparser as fxdparser
import util.mediainfo
import tv.record_client as ri
import kaa.imlib2 as imlib2
import kaa.metadata as metadata

from www.web_types import HTMLResource, FreevoResource
from twisted.web import static

TRUE = 1
FALSE = 0


class LibraryResource(FreevoResource):
    isLeaf=1

    def __init__(self):
        #print '__init__(self)'
        self.allowed_dirs = []
        self.allowed_dirs.extend(config.VIDEO_ITEMS)
        self.allowed_dirs.extend(config.AUDIO_ITEMS)
        self.allowed_dirs.extend( [ ('Recorded TV', config.TV_RECORD_DIR) ])
        self.allowed_dirs.extend(config.IMAGE_ITEMS)

    def is_access_allowed(self, dir_str):
        #print 'is_access_allowed(self, dir_str=%r)' % (dir_str)
        for i in range(len(self.allowed_dirs)):
            val = self.allowed_dirs[i][1]
            if dir_str.startswith(val):
                return TRUE
        return FALSE

    def convert_dir(self, dir_str):
        '''
        Converts a direct file location to a link that twisted can display.
        If the file exists in one of the child resources of twisted, then
        this method converts the file to a proper child resource link that
        twiseted knows about.
        If above case fails, the original file link will be returned.
        '''
        #print 'convert_dir(self, dir_str=%r)' % (dir_str)
        child_res = ""
        ### if the file starts with WEBSERVER_CACHEDIR return converted file
        if dir_str.startswith(config.WEBSERVER_CACHEDIR):
            child_res = config.WEBSERVER_CACHEDIR
        else:
            for i in range(len(self.allowed_dirs)):
                val = self.allowed_dirs[i][1]
                if dir_str.startswith(val):
                    child_res = val
                    break
        child_res = child_res.replace("/", "_")
        location = dir_str[len(child_res):]
        if not location[0] == "/":
            child_res += "/"
        return child_res + location

    def get_suffixes (self, media):
        #print 'get_suffixes (self, media=\"%s\")' % (media)
        suffixes = []
        if media == 'music':
            suffixes.extend(config.AUDIO_SUFFIX)
            suffixes.extend(config.PLAYLIST_SUFFIX)
        if media == 'images':
            suffixes.extend(config.IMAGE_SUFFIX)
        if media == 'movies':
            suffixes.extend(config.VIDEO_SUFFIX)
        if media == 'rectv':
            suffixes.extend(config.VIDEO_SUFFIX)
        return suffixes

    def get_dirlist(self, media):
        #print 'get_dirlist(self, media=\"%s\")' % (media)
        dirs = []
        dirs2 = []

        if media == 'movies':
            dirs2.extend(config.VIDEO_ITEMS)
        elif media == 'music':
            dirs2.extend(config.AUDIO_ITEMS)
        elif media == 'rectv':
            dirs2 = [ ('Recorded TV', config.TV_RECORD_DIR) ]
        elif media == 'images':
            dirs2.extend(config.IMAGE_ITEMS)
        elif media == 'download':
            dirs2.extend(config.VIDEO_ITEMS)
            dirs2.extend(config.AUDIO_ITEMS)
            dirs2.extend( [ ('Recorded TV', config.TV_RECORD_DIR) ])
            dirs2.extend(config.IMAGE_ITEMS)
        #strip out ssr and fxd files
        for d in dirs2:
            if isinstance(d, types.TupleType):
                (title, tdir) = d
                if os.path.isdir(tdir):
                    dirs.append(d)
        return dirs

    def check_dir(self, media, dir):
        #print 'check_dir(self, media=\"%s\", dir=%r)' % (media, dir)
        dirs2 = []
        dirs2 = self.get_dirlist(media)
        for d in dirs2:
            (title, tdir) = d
            if re.match(tdir, dir):
                return TRUE
        return FALSE

    def _render(self, request):
        #print '_render(self, request=\"%s\")' % (request)
        fv = HTMLResource()
        messages = []
        form = request.args

        action = fv.formValue(form, 'action')
        action_file = fv.formValue(form, 'file')
        action_newfile = fv.formValue(form, 'newfile')
        action_dir = fv.formValue(form, 'dir')
        dir_str = fv.formValue(form, 'dir')
        if isinstance(dir_str, str):
            if not self.is_access_allowed(dir_str):
                action_dir = ""

        action_mediatype = fv.formValue(form, 'media')
        action_script = os.path.basename(request.path)
        #use request.postpath array to set action to download
        if not action and len(request.postpath) > 0:
            action = "download"
            action_file = request.postpath[-1]
            action_dir = os.sep + string.join(request.postpath[0:-1], os.sep)
            action_mediatype = "download"
        elif not action:
            action = "view"

        #check to make sure no bad chars in action_file
        fs_result = 0
        bs_result = 0
        if action_file and len(action_file):
            fs_result = string.find(action_file, '/')
            bs_result = string.find(action_file, '\\')

        #do actions here
        if not action == 'view' and bs_result == -1 and fs_result == -1:
            file_loc = os.path.join(action_dir, action_file)
            if os.path.isfile(file_loc):
                if action == 'rename':
                    if action_newfile:
                        newfile_loc = os.path.join(action_dir, action_newfile)
                        if os.path.isfile(newfile_loc):
                            messages += [ _( '%s already exists! File not renamed.' ) % ('<b>'+newfile_loc+'</b>') ]
                        else:
                            try:
                                os.rename(file_loc, newfile_loc)
                                messages += [ _( 'Rename %s to %s.' ) % \
                                    ('<b>'+file_loc+'</b>', '<b>'+newfile_loc+'</b>') ]
                            except OSError, e:
                                messages += [ _( '<h2>%s</h2>' ) % str(e) ]
                                messages += [ _( 'Rename %s to %s, failed.' ) % \
                                    ('<b>'+file_loc+'</b>', '<b>'+newfile_loc+'</b>') ]
                    else:
                        messages += [ '<b>'+_('ERROR') + '</b>: ' +_('No new file specified.') ]

                elif action == 'delete':
                    try:
                        if os.path.exists(file_loc):
                            os.unlink(file_loc)
                            messages += [ _( 'Delete %s.' ) % ('<b>'+file_loc+'</b>') ]
                        file_loc_fxd = os.path.splitext(file_loc)[0]+'.fxd'
                        if os.path.exists(file_loc_fxd):
                            os.unlink(file_loc_fxd)
                            messages += [ _('Delete %s.') % ('<b>'+file_loc_fxd+'</b>') ]
                    except OSError, e:
                        messages += [ _( '<h2>%s</h2>' ) % str(e) ]
                        messages += [ _( 'Delete %s, failed.' ) % ('<b>'+file_loc+'</b>') ]

                elif action == 'download':
                    sys.stderr.write('download %s\n' % file_loc)
                    sys.stderr.flush()
                    return static.File(file_loc).render(request)
                    #request.finish()

            else:
                messages += [ '<b>'+_('ERROR')+'</b>: '+_( '%s does not exist. No action taken.') %
                    ('<b>'+file_loc+'</b>') ]
        elif action_file and action != 'view':
            messages += [ '<b>'+_('ERROR')+'</b>: '\
                +_( 'I do not process names (%s) with slashes for security reasons.') % action_file ]

        directories = []
        if action_mediatype:
            directories = self.get_dirlist(action_mediatype)

        if action and action != "download":
            fv.printHeader(_('Media Library'), 'styles/main.css', script='scripts/display_info-head.js',
                selected=_("Media Library"))
            fv.res += '<script language="JavaScript"><!--' + "\n"

            fv.res += 'function deleteFile(basedir, file, mediatype) {' + "\n"
            fv.res += '   okdelete=window.confirm("Do you wish to delete "+file+" and its fxd?");' + "\n"
            fv.res += '   if(!okdelete) return;' + "\n"
            fv.res += '   document.location="' + action_script +'?action=delete&file=" + escape(file) + "&dir="'\
                +'+ basedir + "&media=" + mediatype;' + "\n"
            fv.res += '}' + "\n"

            fv.res += 'function renameFile(basedir, file, mediatype) {' + "\n"
            fv.res += '   newfile=window.prompt("New name please.", file);' + "\n"
            fv.res += '   if(newfile == "" || newfile == null) return;' + "\n"
            fv.res += '   document.location="' + action_script +'?action=rename&file=" + escape(file) + "&newfile="'\
                +'+ escape(newfile) + "&dir=" + basedir + "&media=" + mediatype;' + "\n"
            fv.res += '}' + "\n"

            fv.res += '//--></script>' + "\n"

            #check if the dir is password protected
            if action_dir and os.path.exists(action_dir + "/.password"):
                f = open(action_dir + "/.password", "r")
                password = f.read()
                f.close()
                fv.printPassword(password)

            fv.printImagePopup()

            fv.res += '&nbsp;<br/>\n'

            if messages:
                fv.res += "<h4>"+_("Messages")+":</h4>\n"
                fv.res += "<ul>\n"
                for m in messages:
                    fv.res += "   <li>%s</li>\n" % m
                fv.res += "</ul>\n"

        if not action_mediatype:
            fv.tableOpen('class="library"')
            movmuslink = '<a href="%s?media=%s&dir=">%s</a>'
            rectvlink = '<a href="%s?media=%s&dir=%s">%s</a>'
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/movies_small.png\" class=\"right\" width=\"80\" height=\"80\">')
            fv.tableCell(movmuslink % (action_script, "movies",_("Movies")), '')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/recorded_small.png\" class=\"right\" width=\"80\" height=\"80\">')
            fv.tableCell(rectvlink % (action_script, "rectv", config.TV_RECORD_DIR, _("Recorded TV")), '')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/music_small.png\" class=\"right\" width=\"80\" height=\"80\">')
            fv.tableCell(movmuslink % (action_script,"music",_("Music")), '')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/images_small.png\" class=\"right\" width=\"80\" height=\"80\">')
            fv.tableCell(movmuslink % (action_script,"images",_("Images")), '')
            fv.tableRowClose()
            fv.tableClose()
            fv.printSearchForm()
            fv.printLinks()
            fv.printFooter()

        elif action_mediatype and len(action_dir) == 0:
            # show the appropriate dirs from config variables
            # make a back to pick music or movies
            # now make the list unique
            fv.tableOpen('class="library"')
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<a href="library.rpy">Home</a>: <a href="library.rpy?media='+action_mediatype+'&dir=">'\
                +Unicode(action_mediatype)+'</a>', 'class="guidehead" colspan="1"')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<a href="'+action_script+'">&laquo; '+_('Back')+'</a>', 'class="basic" colspan="1"')
            fv.tableRowClose()
            for d in directories:
                (title, dir) = d
                link = '<a href="'+action_script+'?media='+action_mediatype+'&dir='+urllib.quote(dir)+'">'\
                    +Unicode(title)+'</a>'
                fv.tableRowOpen('class="chanrow"')
                fv.tableCell(link, 'class="basic" colspan="1"')
                fv.tableRowClose()
            fv.tableClose()
            fv.printSearchForm()
            fv.printLinks()
            fv.printFooter()

        elif action_mediatype and len(action_dir) and action != "download":
            if not self.check_dir(action_mediatype,action_dir) and action != 'view':
                # why
                sys.exit(1)

            fv.tableOpen('class="library"')
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(fv.printBreadcrumb(action_mediatype,self.get_dirlist(action_mediatype), action_dir), \
                'class="guidehead" colspan="3"')
            fv.tableRowClose()

            # find out if anything is recording
            recordingprogram = ''
            favre = ''
            favs = []
            if action_mediatype == 'movies' or action_mediatype == 'rectv':
                (got_schedule, recordings) = ri.getScheduledRecordings()
                if got_schedule:
                    progs = recordings.getProgramList()
                    f = lambda a, b: cmp(a.start, b.start)
                    progl = progs.values()
                    progl.sort(f)
                    for prog in progl:
                        try:
                            if prog.isRecording:
                                recordingprogram = os.path.basename(tv_util.getProgFilename(prog))
                                recordingprogram = string.replace(recordingprogram, ' ', '_')
                                break
                        except:
                            # sorry, have to pass without doing anything.
                            pass
                else:
                    fv.res += '<h4>Recording server is not available, recording information is unavailable.</h4>'

                #generate our favorites regular expression
                favre = ''
                (result, favorites) = ri.getFavorites()
                if result:
                    favs = favorites.values()
                else:
                    favs = []

                if favs:
                    favtitles = [ fav.title for fav in favs ]
                    # no I am not a packers fan
                    favre = string.join(favtitles, '|')
                    favre = string.replace(favre, ' ', '_')

            #put in back up directory link
            #figure out if action_dir is in directories variable and change
            #back if it is
            actiondir_is_root = FALSE
            for d in directories:
                (title, dir) = d
                if dir == action_dir:
                    actiondir_is_root = TRUE
                    break
            backlink = ''
            if actiondir_is_root and action_mediatype == 'rectv':
                backlink = '<a href="'+ action_script +'">&laquo; '+_('Back')+'</a>'
            elif actiondir_is_root:
                backlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir=">&laquo; '+_('Back')+'</a>'
            else:
                backdir = os.path.dirname(action_dir)
                backlink = '<a href="'+action_script+'?media='+action_mediatype+'&dir='+urllib.quote(backdir)+'">'\
                    +'&laquo; '+_('Back')+'</a>'
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(backlink, 'class="basic" colspan="3"')
            fv.tableRowClose()

            # get me the directories to output
            i = 0
            directorylist = util.getdirnames(action_dir)
            for mydir in directorylist:
                #check for hidden dirs
                if mydir[mydir.rindex('/')+1] != '.':
                    if i == 0:
                        fv.tableRowOpen('class="chanrow"')
                    mydispdir = Unicode(os.path.basename(mydir))
                    mydirlink = ""
                    ### show music cover
                    if action_mediatype == "music":
                        y = self.cover_filter(mydir)
                        if y:
                            image_link = self.convert_dir(mydir + str(y))
                        else:
                            image_link = "images/library/www-mp-music.png"
                        mydirlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'">'\
                            +'<img src="' + image_link + '" class="folder" height="100px" width="100px" /><br />'+mydispdir+'</a>'
                    ### show movie cover
                    elif action_mediatype == "movies":
                        y = self.cover_filter(mydir)
                        if y:
                            image_link = self.convert_dir(mydir + str(y))
                        else:
                            image_link = "images/library/www-mp-movies.png"
                        mydirlink = '<a href="'+action_script+'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'">'\
                            +'<img src="' + image_link + '" class="folder" height="100px" width="100px" /><br />'+mydispdir+'</a>'
                    ### show recorded shows cover
                    elif action_mediatype == "rectv":
                        y = self.cover_filter(mydir)
                        if y:
                            image_link = self.convert_dir(mydir + str(y))
                        else:
                            image_link = "images/library/www-mp-tv.png"
                        mydirlink = '<a href="'+action_script+'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'">'\
                            +'<img src="' + image_link + '" class="folder" height="100px" width="100px" /><br />'+mydispdir+'</a>'
                    ### show image cover
                    elif action_mediatype == "images":
                        image_link = "images/library/www-mp-pictures.png"
                        mydirlink = '<a href="'+action_script+'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'">'\
                            +'<img src="'+image_link+'" class="folder" height="100px" width="100px" /><br />'+mydispdir+'</a>'

                    fv.tableCell(mydirlink, 'class="basic" colspan="1"')
                    if i == 2:
                        fv.tableRowClose()
                        i = 0
                    else:
                        i += 1
            while i < 3 and i != 0:
                fv.tableCell('&nbsp;', 'class="basic" colspan="1"')
                if i == 2:
                    fv.tableRowClose()
                i += 1

            suffixes = self.get_suffixes(action_mediatype)
            try:
                suffixes.remove("m3u")
            except:
                pass

            # loop over directory here
            i=0
            image = ""
            items = util.match_files(action_dir, suffixes)
            for item in items:
                #check for hidden files
                if item[item.rindex('/')+1] != '.':
                    #chop dir from in front of file
                    (basedir, file) = os.path.split(item)
                    filepath = urllib.quote(item)
                    #find info and size
                    info = metadata.parse(item)
                    len_file = os.stat(item)[6]
                    #check for fxd file and other info
                    fxd_file = item[:item.rindex('.')] + ".fxd"
                    jpg_file = item[:item.rindex('.')] + ".jpg"
                    if os.path.exists(fxd_file):
                        title = self.get_fxd_title(fxd_file)
                    else:
                        title = util.mediainfo.get(item)['title']
                    if not title:
                        title = file

                    if i == 0:
                        fv.tableRowOpen('class="chanrow"')
                    status = 'basic'
                    suppressaction = FALSE
                    if recordingprogram and re.match(recordingprogram, file):
                        status = 'recording'
                        suppressaction = TRUE
                    elif favs and re.match(favre, file):
                        status = 'favorite'
                    ### show image
                    if action_mediatype == "images":
                        scaled_image_path = util.www_thumbnail_path(item)
                        if not os.path.exists(scaled_image_path):
                            size = util.create_www_thumbnail(item)
                        else:
                            size = (info['width'], info['height'])
                        image_link = self.convert_dir(filepath)
                        scaled_image_link = self.convert_dir(scaled_image_path)
                        fv.tableCell('<div class="image"><a href="javascript:openfoto(\''+\
                            urllib.quote(image_link)+\
                            '\','+str(size[0])+','+str(size[1])+')">'+
                            '<img src="'+scaled_image_link+'" /><br />'+Unicode(title)+'</a></div>', \
                            'class="'+status+'" colspan="1"')
                    ### show movie
                    elif action_mediatype == "movies":
                        if os.path.exists(jpg_file):
                            image = jpg_file
                            image_link = self.convert_dir(image)
                            image_info = metadata.parse(image)
                            size = (image_info['width'], image_info['height'])
                            new_size = self.resize_image(image_link, size)
                            image = '<img src="'+image_link+'" height="'+str(new_size[1])+'px" width="'+str(new_size[0])+'px" /><br />'
                        else:
                            image = '<img src="images/library/movies.png" height="100px" width="100px" /><br />'
                        fv.tableCell('<a onclick="info_click(this, event)" id="'+filepath+'">'\
                            +image+Unicode(title)+'</a>',\
                            'class="'+status+'" colspan="1"')
                    ### show recorded shows
                    elif action_mediatype == "rectv":
                        if os.path.exists(jpg_file):
                            image = jpg_file
                            image_link = self.convert_dir(image)
                            image_info = metadata.parse(image)
                            size = (image_info['width'], image_info['height'])
                            new_size = self.resize_image(image_link, size)
                            image = '<img src="'+image_link+'" height="'+str(new_size[1])+'px" width="'+str(new_size[0])+'px" /><br />'
                        else:
                            image = '<img src="images/library/recorded_small.png" height="80px" width="80px" />'
                        fv.tableCell('<a onclick="info_click(this, event)" id="'+filepath+'">'\
                            +image+Unicode(title)+'</a>',\
                            'class="'+status+'" colspan="1"')
                    ### show music
                    elif action_mediatype == "music":
                        try:
                            title = Unicode(info['trackno']+" - "+info['artist']+" - "+info['title'])
                        except:
                            title = Unicode(file)
                        if len(title) > 45:
                            title = "%s[...]%s" % (title[:20], title[len(title)-20:])
                        image = '<img src="images/library/music_small.png" height="80px" width="80px" />'
                        fv.tableCell('<a onclick="info_click(this, event)" id="'+filepath+'">'\
                            +image+title+'</a>', 'class="'+status+'" colspan="1"')
                    else:
                        fv.tableCell(file, 'class="'+status+'" colspan="1"')
                    if suppressaction:
                        fv.tableCell('&nbsp;', 'class="'+status+'" colspan="1"')
                    else:
                        file_qu = urllib.quote(file)
                        basedir_qu = urllib.quote(basedir)
                        file_path_qu = urllib.quote(os.path.join(basedir, file))
                        dllink = ('<a href="'+action_script+'%s">'+_('Download')+'</a>') % file_path_qu
                        delete = ('<a href="javascript:deleteFile(\'%s\',\'%s\',\'%s\')">'+_("Delete")+'</a>') %\
                            (basedir_qu, file_qu, action_mediatype)
                        rename = ('<a href="javascript:renameFile(\'%s\',\'%s\',\'%s\')">'+_("Rename")+'</a>') %\
                            (basedir_qu, file_qu, action_mediatype)
                    if i == 2:
                        fv.tableRowClose()
                        i = 0
                    else:
                        i+=1
            while i < 3 and i != 0:
                fv.tableCell('&nbsp;', 'class="basic" colspan="1"')
                if i == 2:
                    fv.tableRowClose()
                i +=1
            fv.tableClose()

            fv.printSearchForm()
            fv.printLinks()
            fv.res += (
            u"<div id=\"popup\" class=\"proginfo\" style=\"display:none\">\n"\
            u"<div id=\"program-waiting\" style=\"background-color: #0B1C52; position: absolute\">\n"\
            u"  <br /><b>Fetching file information ...</b>\n"\
            u"</div>\n"\
            u"   <table id=\"program-info\" class=\"popup\">\n"\
            u"      <thead>\n"\
            u"         <tr>\n"\
            u"            <td id=\"file-head\">\n"\
            u"            </td>\n"\
            u"         </tr>\n"\
            u"      </thead>\n"\
            u"      <tbody>\n"\
            u"         <tr>\n"\
            u"            <td class=\"progdesc\"><span id=\"file-info\"> </span>"\
            u"            </td>"\
            u"         </tr>"\
            u"      </tbody>\n"\
            u"      <tfoot>\n"\
            u"         <tr>\n"\
            u"            <td>\n"\
            u"               <table class=\"popupbuttons\">\n"\
            u"                  <tbody>\n"\
            u"                     <tr>\n"\
            u"                        <td id=\"file-play-button\">\n"\
            u"                           "+_('Play file')+u"\n"\
            u"                        </td>\n"\
            u"                        <td id=\"file-play-using-vlc\">\n"\
            u"                        "+_('Play file using VLC')+u"\n"\
            u"                        "+''+u"\n"\
            u"                        </td>\n"\
            u"                        <td id=\"program-favorites-button\">\n"\
            #u"                        "+_('Play file on Freevo')+u"\n"\
            u"                        "+''+u"\n"\
            u"                        </td>\n"\
            u"                        <td onclick=\"program_popup_close();\">\n"\
            u"                        "+_('Close Window')+u"\n"\
            u"                        </td>\n"\
            u"                     </tr>\n"\
            u"                  </tbody>\n"\
            u"               </table>\n"\
            u"            </td>\n"\
            u"         </tr>\n"\
            u"      </tfoot>\n"\
            u"   </table>\n"\
            u"</div>\n" )
            fv.res += "<iframe id='hidden' style='visibility: hidden; width: 1px; height: 1px'></iframe>\n"
            fv.printFooter()

        return String(fv.res)


    def cover_filter(self, x):
        #print 'cover_filter(self, x=%r)' % (x)
        for i in os.listdir(x):
            cover = re.search(config.AUDIO_COVER_REGEXP, i, re.IGNORECASE)
            if cover:
                return "/" + i
            else:
                fname = x[x.rfind("/"):]
                fxd_file = fname + ".fxd"
                cover = self.get_fxd_cover(x + fxd_file)
                if cover != '':
                    return "/" + cover
                else:
                    jpg_file = fname + ".jpg"
                    if os.path.exists(x + jpg_file):
                        return jpg_file


    def get_fxd_cover(self, fxd_file):
        #print 'get_fxd_cover(self, fxd_file=\"%s\")' % (fxd_file)
        cover = ''
        fxd_info = {}
        parser = util.fxdparser.FXD(fxd_file)
        parser.parse()
        for a in parser.tree.tree.children:
            cover = parser.childcontent(a, "cover-img")
            if cover:
                break
        return cover

    def resize_image(self, image, size):
        #print 'resize_image(self, image=%r, size=%s)' % (image, size)
        (width, height) = size
        new_width = 200
        try:
            new_height = float(height) * (float(new_width) / float(width))
        except ZeroDivisionError:
            new_height = 200
        return (int(new_width), int(new_height + 0.5))

    def get_fxd_title(self, fxd_file):
        #print 'get_fxd_title(self, fxd_file=%r)', (fxd_file)
        fxd_info = ""
        parser = util.fxdparser.FXD(fxd_file)
        parser.parse()
        for a in parser.tree.tree.children:
            if a.name == 'movie' or a.name == 'image' or a.name == 'audio':
                fxd_info = str(a.attrs.values()[0])
        return fxd_info


resource = LibraryResource()
