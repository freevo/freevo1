#!/usr/bin/python

# -----------------------------------------------------------------------
# library.rpy - a script to display and modify your video library
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
# Todo: -allow for an imdb popup
#       -stream tv, video and music somehow
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

import sys, os, string, urllib, re, types


# needed to put these here to suppress its output
import config, util
import util.tv_util as tv_util
import util.fxdparser as fxdparser
import util.mediainfo
import tv.record_client as ri
import kaa.imlib2 as Image

from www.web_types import HTMLResource, FreevoResource
from twisted.web import static

TRUE = 1
FALSE = 0


class LibraryResource(FreevoResource):
    isLeaf=1
    def is_access_allowed(self, dir_str):
        allowed_dirs = []
        allowed_dirs.extend(config.VIDEO_ITEMS)
        allowed_dirs.extend(config.AUDIO_ITEMS)
        allowed_dirs.extend( [ ('Recorded TV', config.TV_RECORD_DIR) ])
        allowed_dirs.extend(config.IMAGE_ITEMS)
        for i in range(len(allowed_dirs)):
            val = allowed_dirs[i][1]
            if dir_str.startswith(val):
                return TRUE
        return FALSE

    def get_suffixes (self, media):
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
        dirs2 = []
        dirs2 = self.get_dirlist(media)
        for d in dirs2:
            (title, tdir) = d
            if re.match(tdir, dir):
                return TRUE
        return FALSE

    def _render(self, request):
        fv = HTMLResource()
        messages = []
        form = request.args

        action           = fv.formValue(form, 'action')
        action_file      = Unicode(fv.formValue(form, 'file'))
        if isinstance( action_file, str ):
            action_file = Unicode( action_file, 'latin-1' )
            
        action_newfile   = Unicode(fv.formValue(form, 'newfile'))
        if isinstance( action_newfile, str ):
            action_newfile = Unicode( action_newfile, 'latin-1' )
            
        action_dir       = Unicode(fv.formValue(form, 'dir'))
        dir_str = fv.formValue(form, 'dir')
        if isinstance(dir_str, str):
            if not self.is_access_allowed(dir_str):
                action_dir = ""
        if isinstance( action_dir, str ):
            action_dir = Unicode( action_dir, 'latin-1' )
            
        action_mediatype = fv.formValue(form, 'media')
        action_script = os.path.basename(request.path)        
        #use request.postpath array to set action to download
        if not action and len(request.postpath) > 0:
            action = "download"
            action_file = Unicode(request.postpath[-1])
            action_dir = Unicode(os.sep + string.join(request.postpath[0:-1], os.sep))
            action_mediatype = "download"
        elif not action:
            action = "view"


        #check to make sure no bad chars in action_file
        fs_result = 0
        bs_result = 0
        if len(action_file):
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
                        file_loc_fxd = os.path.splitext(file_loc)[0] + '.fxd'
                        if os.path.exists(file_loc_fxd): 
                            os.unlink(file_loc_fxd)
                            messages += [ _('Delete %s.') % ('<b>'+file_loc_fxd+'</b>') ]
                    except OSError, e:
                        messages += [ _( '<h2>%s</h2>' ) % str(e) ]
                        messages += [ _( 'Delete %s, failed.' ) % ('<b>'+file_loc+'</b>') ]

                elif action == 'download':
                    sys.stderr.write('download %s\n' % String(file_loc))
                    sys.stderr.flush()
                    return static.File(file_loc).render(request)
                    #request.finish()

            else:
                messages += [ '<b>'+_('ERROR') + '</b>: ' + _( '%s does not exist. No action taken.') % ('<b>'+file_loc+'</b>') ]
        elif action_file and action != 'view':
            messages += [ '<b>'+_('ERROR')+'</b>: ' +_( 'I do not process names (%s) with slashes for security reasons.') % action_file ]

        directories = []
        if action_mediatype:
            directories = self.get_dirlist(action_mediatype)


        if action and action != "download":
            fv.printHeader(_('Media Library'), 'styles/main.css',script='scripts/display_info-head.js', selected=_("Media Library"))
            fv.res += '<script language="JavaScript"><!--' + "\n"

            fv.res += 'function deleteFile(basedir, file, mediatype) {' + "\n"
            fv.res += '   okdelete=window.confirm("Do you wish to delete "+file+" and its fxd?");' + "\n"
            fv.res += '   if(!okdelete) return;' + "\n"
            fv.res += '   document.location="' + action_script +'?action=delete&file=" + escape(file) + "&dir=" + basedir + "&media=" + mediatype;' + "\n"
            fv.res += '}' + "\n"

            fv.res += 'function renameFile(basedir, file, mediatype) {' + "\n"
            fv.res += '   newfile=window.prompt("New name please.", file);' + "\n"
            fv.res += '   if(newfile == "" || newfile == null) return;' + "\n"
            fv.res += '   document.location="' + action_script +'?action=rename&file=" + escape(file) + "&newfile=" + escape(newfile) + "&dir=" + basedir + "&media=" + mediatype;' + "\n"
            fv.res += '}' + "\n"

            fv.res += '//--></script>' + "\n"

            #check if the dir is password protected
            if os.path.exists(String(action_dir) + "/.password"):
                f = open(String(action_dir) + "/.password", "r")
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
            fv.tableCell('<img src=\"images/library/library-movies.jpg\" class=\"right\">')
            fv.tableCell(movmuslink % (action_script, "movies",_("Movies")), '')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/library-tv.jpg\" class=\"right\">')
            fv.tableCell(rectvlink % (action_script, "rectv", config.TV_RECORD_DIR, _("Recorded TV")), '')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/library-music.jpg\" class=\"right\">')
            fv.tableCell(movmuslink % (action_script,"music",_("Music")), '')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<img src=\"images/library/library-images.jpg\" class=\"right\">')
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
            fv.tableCell('<a href="library.rpy">Home</a>: <a href="library.rpy?media='+action_mediatype+'&dir=">'+action_mediatype+'</a>', 'class="guidehead" colspan="1"')
            fv.tableRowClose()
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell('<a href="' + action_script + '">&laquo; '+_('Back')+'</a>', 'class="basic" colspan="1"')
            fv.tableRowClose()
            for d in directories:
                (title, dir) = d
                link = '<a href="' + action_script +'?media='+action_mediatype+'&dir='+urllib.quote(dir)+'">'+title+'</a>'
                fv.tableRowOpen('class="chanrow"')
                fv.tableCell(link, 'class="basic" colspan="1"')
                fv.tableRowClose()
            fv.tableClose()
            fv.printSearchForm()
            fv.printLinks()
            fv.printFooter()
        elif action_mediatype and len(action_dir) and action != "download":
            if not self.check_dir(action_mediatype,action_dir) and action != 'view':
                sys.exit(1)

            fv.tableOpen('class="library"')
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(fv.printBreadcrumb(action_mediatype,self.get_dirlist(action_mediatype), action_dir), 'class="guidehead" colspan="3"')
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
                            if prog.isRecording == TRUE:
                                recordingprogram = os.path.basename(tv_util.getProgFilename(prog))
                                recordingprogram = string.replace(recordingprogram, ' ', '_')
                                break
                        except:
                            # sorry, have to pass without doing anything.
                            pass
                else:
                    fv.res += '<h4>The recording server is down, recording information is unavailable.</h4>'
            
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
            if actiondir_is_root == TRUE and action_mediatype == 'rectv':
                backlink = '<a href="'+ action_script +'">&laquo; '+_('Back')+'</a>'
            elif actiondir_is_root == TRUE:
                backlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir=">&laquo; '+_('Back')+'</a>'
            else:
                backdir = os.path.dirname(action_dir)
                backlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir='+urllib.quote(backdir)+'">&laquo; '+_('Back')+'</a>'
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(backlink, 'class="basic" colspan="3"')
            fv.tableRowClose()

            # get me the directories to output
            directorylist = util.getdirnames(String(action_dir))
            i = 0
            for mydir in directorylist:
                if i == 0:
                    fv.tableRowOpen('class="chanrow"')
                mydir = Unicode(mydir)
                mydispdir = os.path.basename(mydir)
                mydirlink = ""
                ### show music cover
                if action_mediatype == "music":
                    y = self.cover_filter(mydir)
                    if y:
                        image_link = self.get_images(mydir + str(y))
                    else:
                        image_link = "images/library/music.png"
                    mydirlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'"><img src="' + image_link + '" height="200px" width="200px" /><br />'+mydispdir+'</a>'
                ### show movie cover
                elif action_mediatype == "movies":
                    y = self.cover_filter(mydir)
                    if y:
                        image_link = self.get_images(mydir + str(y))
                    else:
                        image_link = "images/library/movies.png"
                    mydirlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'"><img src="' + image_link + '" height="200px" width="200px" /><br />'+mydispdir+'</a>'
                ### show image cover
                elif action_mediatype == "images":
                    image_link = "images/library/images.png"
                    mydirlink = '<a href="'+ action_script +'?media='+action_mediatype+'&dir='+urllib.quote(mydir)+'"><img src="' + image_link + '" height="200px" width="200px" /><br />'+mydispdir+'</a>'
                
                fv.tableCell(mydirlink, 'class="basic" colspan="1"')
                if i == 2:
                    fv.tableRowClose()
                    i = 0
                else:
                    i += 1
            while i < 3 and i !=0:
                fv.tableCell('&nbsp;', 'class="basic" colspan="1"')
                if i == 2:
                    fv.tableRowClose()
                i +=1

            suffixes = self.get_suffixes(action_mediatype)

            # loop over directory here
            items = util.match_files(String(action_dir), suffixes)
            i=0
            image = ""
            for file in items:
                #check for fxd file
                fxd_file = file[:file.rindex('.')] + ".fxd"
                if os.path.exists(fxd_file):
                    image = self.get_fxd_cover(fxd_file)
                    
                if i == 0:
                    fv.tableRowOpen('class="chanrow"')
                status = 'basic'
                suppressaction = FALSE
                #find size
                len_file = os.stat(file)[6]
                #chop dir from in front of file
                (basedir, file) = os.path.split(file)
                if recordingprogram and re.match(recordingprogram, file):
                    status = 'recording'
                    suppressaction = TRUE
                elif favs and re.match(favre, file):
                    status = 'favorite'
                ### show image
                if action_mediatype == "images":
                    image_link = self.get_images(basedir + "/" + file)
                    size = Image.open(basedir+"/"+file).size
                    new_size = self.resize_image(image_link, size)
                    fv.tableCell('<a href="javascript:openfoto(\''+image_link+'\','+str(size[0])+','+str(size[1])+')"><img src="' + image_link + '" height="'+str(new_size[1])+'px" width="'+str(new_size[0])+'px" /><br />' + Unicode(file) + '</a>', 'class="'+status+'" colspan="1"')
                ### show movie
                elif action_mediatype == "movies":
                    fv.tableCell('<a onclick="info_click(this, event)" id="'+basedir+'/'+file+'"><img src="'+image+'" height="200px" width="200px" /><br />' + Unicode(file) + '</a>' , 'class="'+status+'" colspan="1"')                   
                ### show music
                elif action_mediatype== "music":
                    info =  util.mediainfo.get(basedir +"/"+ file)
                    fv.tableCell('<a onclick="info_click(this, event)" id="'+basedir+'/'+file+'">'+Unicode(info['trackno'] + "-" + info['artist']+"-"+info['title'])+'</a>' , 'class="'+status+'" colspan="1"')                   
                else:
                    fv.tableCell(Unicode(file), 'class="'+status+'" colspan="1"')
                if suppressaction == TRUE:
                    fv.tableCell('&nbsp;', 'class="'+status+'" colspan="1"')
                else:
                    file_esc = urllib.quote(String(file))
                    dllink = ('<a href="'+action_script+'%s">'+_('Download')+'</a>') %  Unicode(os.path.join(basedir,file))
                    delete = ('<a href="javascript:deleteFile(\'%s\',\'%s\',\'%s\')">'+_("Delete")+'</a>') % (basedir, file_esc, action_mediatype)
                    rename = ('<a href="javascript:renameFile(\'%s\',\'%s\',\'%s\')">'+_("Rename")+'</a>') % (basedir, file_esc, action_mediatype)                
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
            u"                        <td id=\"program-favorites-button\">\n"\
            u"                        "+_('Play file on host')+u"\n"\
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

        return String( fv.res )
    
    def get_images(self, myfile):
        current_path = "%s/share/freevo/htdocs/" % sys.prefix
        image_cache_link = "image_cache/" + myfile.replace("/", "_")
        if not os.path.exists("%s/share/freevo/htdocs/" % sys.prefix + image_cache_link): 
            os.symlink(myfile , current_path + image_cache_link)
        return image_cache_link
    
    def cover_filter(self, x):
        for i in os.listdir(x):
            cover = re.search(config.AUDIO_COVER_REGEXP, i, re.IGNORECASE)
            if cover:
                return "/" + i
    
    def get_fxd_cover(self, fxd_file):
        cover = ""
        fxd_info = {}
        parser = util.fxdparser.FXD(fxd_file)
        parser.parse()
        for a in parser.tree.tree.children:
            for b in a.children:
                if b.name == 'cover-img':
                    cover = str(b.attrs.values()[0])
        return cover
    
    def resize_image(self, image, size):
        new_size = []
        new_size.append(size[0])
        new_size.append(size[1])
        while new_size[0] > 200:
            new_size[0] -= (new_size[0] * 10)/100
            new_size[1] -= (new_size[1] * 10)/100
        return new_size

    
resource = LibraryResource()

