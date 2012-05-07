# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in for subtitles download and support/maintenance
# -----------------------------------------------------------------------
# $Id: $
#
# Notes: subtitles plugin. 
#        You can donwload subtitles from the http://napiprojekt.pl
#        with this plugin. Only two langgauges supported, polish and english.
#        Add following to your local_conf.py
#        SUBS_LANGS = { 'pl': ('PL', 'Polish'), 'en': ('ENG', 'English') }
#        if you want both, polish and english subtitles, or just use the lang
#        of your choice, either polish or english.
#        SUBS_AUTOACCEPT = True
#        if you want to blindly download all subs available, otherwise the 
#        menu with available aubtitles will be presented and choice can be made
#        SUBS_FORCE_UPDATE = True
#        if you want to override existing subtitle file (if exists)
#        SUBS_FORCE_BACKUP = True
#        and backup old file if in update mode above
#        activate with plugin.activate('video.napi')
#        You can also set subs_search on a key (e.g. 't') by setting
#        EVENTS['menu']['t'] = Event(MENU_CALL_ITEM_ACTION, arg='subs_search')
#
# Todo:  none
#
# BTW:   napi is short in polish for napisy or subtitles in english :-)
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

__author__           = 'Maciej Mike Urbaniak (maciej@urbaniak.org)'
__maintainer__       = 'Maciej Mike Urbaniak'
__maintainer_email__ = 'maciej@urbaniak.org'
__version__          = 'Revision 0.1'
__license__          = 'GPL' 

# Module Imports
import os
from operator import itemgetter, attrgetter

import menu
import config
import plugin
import re
import time
import util

from gui.PopupBox import PopupBox

HEAD = 'head'
TAIL = 'tail'

def trunc(what, cnt, where=HEAD, ellipsis='...'):
    if where == HEAD:
        return (ellipsis + what[len(what) - (cnt - len(ellipsis)):]) if len(what) > cnt else what
    return (what[:len(what) - (cnt + len(ellipsis))] + ellipsis) if len(what) > cnt else what


class Error(Exception):
    """Base class for exceptions in Subs"""
    def __str__(self):
        return self.message
    def __init__(self, message):
        self.message = message


class SubsError(Error):
    """used to raise Subtitle specific exceptions"""
    pass


class SubsHandler():
    """
    Base Subtitles handler class definition including all methods that subclasses 
    shall overwrite
    """
    
    def __init__(self, id, name, langs):
        self.id    = id
        self.name  = name
        self.langs = langs

    
    def __getitem__(self, key):
        """
        Get the item's attribute.
        @returns: the specific attribute
        """
        if key == 'name':
            return self.name

        if key == 'id': 
            return self.id
        
        if key == 'langs': 
            return self.langs
            
        return ''

    
    def get_subs(self, vfile_, langs_):
        """
        Derived class must overwrite this method

        Get all available subtitles for the item
        @returns: the collection of subtitles keyed by the subtitle id
        """
        pass
        

class Subtitles():

    def __init__(self, handler, vfile, lang):
        self.id         = 0
        self.handler    = handler
        self.lang       = lang
        self.vfile      = vfile
        self.vbase      = os.path.splitext(self.vfile)[0]
        self.sfile      = ''
        self.compressed = False
        self.data       = None
        self.fmt        = 'txt'


    def __getitem__(self, key):
        """
        Get the item's attribute.

        @returns: the specific attribute
        """
        if key == 'id': 
            return hash((self.handler['id'], self.lang, self.vfile))
            
        if key == 'handler': 
            return self.handler
        
        if key == 'vfile': 
            return self.vfile

        if key == 'sfile': 
            return self.sfile

        if key == 'lang': 
            return self.lang

        if key == 'data': 
            return self.data


    def download(self):
        """
        Derived class must overwrite this method

        Physically download the subtitle files
        @returns: True or False
        """
        pass


    def save(self):
        """
        Derived class must overwrite this method

        Physically write subtitle file to the local storage
        """
        pass


    def backup(self):
        """
        Backs up existing subtitle files
        """
        if config.SUBS_FORCE_LANG_EXT == True:
            self.sfile = "%s.%s.%s.%s" % (self.vbase, self.handler['id'], self.lang, self.fmt)
        else:
            self.sfile = "%s.%s.%s" % (self.vbase, self.handler['id'], self.fmt)

        if not config.SUBS_FORCE_UPDATE and os.path.exists(self.sfile):
            msg = "Skipping, subtitles %s aready exist and forced update is disabled" % (self.sfile)
            _debug_(msg, DWARNING)
            raise SubsError(msg)

        if config.SUBS_FORCE_BACKUP and os.path.exists(self.sfile):
            vfile_bkp = self.sfile + '.bkp'
            try:
                if os.path.exists(vfile_bkp):
                    os.remove(vfile_bkp)

                os.rename(self.sfile, vfile_bkp)

            except (IOError, OSError), e:
                msg = "Skipping due to backup of `%s' as `%s' failure: %s" % (self.sfile, vfile_bkp, e)
                _debug_(msg, DWARNING)
                raise SubsError(msg)
            else:
                _debug_("Old subtitle backed up as `%s'" % (vfile_bkp), DINFO)

        return True

    
class PluginInterface(plugin.ItemPlugin):
    """
    You can add subtitles for video items with the plugin.

    Activate with:
    | plugin.activate('video.subtitles')
    
    Make sure the suitable subtitles handler plugin is activated too:
    | plugin.activate('video.napiprojekt')
    
    and/or
    | plugin.activate('video.opensubtitles')
    
    etc.

    Make sure the 
    | SUBS_AVAILABLE_HANDLERS = [ ('video.napiprojekt'), ('video.opensubtitles') ]
    is set in your local_config.py for the this subtitles plugin 
    to be able to use the available handlers

    You can also set subs_search on a key (e.g. 't') by setting
    | EVENTS['menu']['t'] = Event(MENU_CALL_ITEM_ACTION, arg='subs_search')
    """

    def __init__(self):
        if not config.SYS_USE_NETWORK:
            self.reason = 'SYS_USE_NETWORK not enabled'
            return
        
        self.handlers = {}
        self.subs     = {}
        self.subfiles = []

        _debug_('Available Handlers : %s' % (config.SUBS_AVAILABLE_HANDLERS), DINFO)

        for item in config.SUBS_AVAILABLE_HANDLERS:
            if not plugin.is_active(item):
                _debug_('Plugin %s listed as available but not activated, activating now!' % (item), DWARNING)
                plugin.activate(item)

            handler = plugin.getbyname(item)['handler']
            self.handlers[handler['id']] = handler
            _debug_('Successfuly loaded subtitle handler %s' % (handler.name), DINFO)

        plugin.ItemPlugin.__init__(self)


    def config(self):
        """
        Returns the config variables used by this plugin
        """
        return [
            ('SUBS_LANGS',          { 'pol': ('Polish'), 'eng': ('English'), 'ger': ('German') },
                'Subtitles to download'),
            ('SUBS_EXTS',           [ 'srt', 'sub', 'txt', 'ssa', 'smi', 'ass', 'mpl'], 
                'Known subtitles file extensions'),
            ('SUBS_AUTOACCEPT',     False, 
                'Autoaccept all found subtitles, language coded filenames'),
            ('SUBS_FORCE_UPDATE',   True,  
                'Force update of existing subtitles'),
            ('SUBS_FORCE_BACKUP',   True,  
                'Force backup of existing subtitles'),
            ('SUBS_FORCE_LANG_EXT', True,
                'Force use of the subtitle lagnguage code in the filename i.e. xxx.eng.txt'),
        ]


    def actions(self, item):
        """
        Actions this item supports
        """
        self.item = item
        subs      = False

        if hasattr(self.item, 'subitems') and self.item.subitems:
            for i in range(len(self.item.subitems)):
                subs = self.check_existing_subs(self.item.subitems[i].filename)
        else:
            subs = self.check_existing_subs(self.item.filename)

        if item.type == 'video' and item.mode == 'file':
            if subs and not config.SUBS_FORCE_BACKUP:
                return [ ( self.subs_delete , _('Delete Subtitles'),   'subs_delete') ]
            elif subs and config.SUBS_FORCE_BACKUP:
                return [ ( self.subs_delete , _('Delete Subtitles'),   'subs_delete'),
                         ( self.subs_search , _('Download Subtitles'), 'subs_search') ]
            else:
                return [ ( self.subs_search , _('Download Subtitles'), 'subs_search') ]
      
        return []

    
    def check_existing_subs(self, file):
        """
        Check if any existing subitle files that match the pattern 
        """
        base    = os.path.splitext(file)[0]
        
        for ext in config.SUBS_EXTS:
            for handler in self.handlers.values():
                # check the simple filename first movie.txt etc.
                vfile = "%s.%s" % (base, ext)
                if os.path.exists(vfile):
                    return True

                # now bit more chalanging, filename  with the handler name, movie.os.txt
                vfile = "%s.%s.%s" % (base, handler['id'], ext)
                if os.path.exists(vfile):
                    return True

                for lang in config.SUBS_LANGS.keys():
                    # yet another case, filename  with the lang, movie.en.txt
                    vfile = "%s.%s.%s" % (base, lang, ext)
                    if os.path.exists(vfile):
                        return True

                    # and finally, filename  with the handler name and lang, movie.os.en.txt
                    vfile = "%s.%s.%s.%s" % (base, handler['id'], lang, ext)
                    if os.path.exists(vfile):
                        return True
     
        return False


    def get_existing_subs(self, file):
        """
        Get all existing subitle files that match the pattern 
        into the collection and return it.
        """
        results = []
        base    = os.path.splitext(file)[0]
        
        for ext in config.SUBS_EXTS:
            for handler in self.handlers.values():
                # check the simple filename first movie.txt etc.
                vfile = "%s.%s" % (base, ext)
                if os.path.exists(vfile):
                    results.append(vfile)

                # now bit more chalanging, filename  with the handler name, movie.os.txt
                vfile = "%s.%s.%s" % (base, handler['id'], ext)
                if os.path.exists(vfile):
                    results.append(vfile)

                for lang in config.SUBS_LANGS.keys():
                    # yet another case, filename  with the lang, movie.en.txt
                    vfile = "%s.%s.%s" % (base, lang, ext)
                    if os.path.exists(vfile):
                        results.append(vfile)

                    # and finally, filename  with the handler name and lang, movie.os.en.txt
                    vfile = "%s.%s.%s.%s" % (base, handler['id'], lang, ext)
                    if os.path.exists(vfile):
                        results.append(vfile)
                    
        return results


    def subs_search(self, arg=None, menuw=None):
        """
        Search subtitle website for subtitles for this item
        """
        self.subs = {}
        items     = []
    
        try:
            #get the subtitles from each active handler
            for handler in self.handlers.values():
                box = PopupBox(text=_('Searching %s for subtitles...' % (handler['name'])))
                box.show()

                if self.item.subitems:
                    for i in range(len(self.item.subitems)):
                        self.subs.update(handler.get_subs(self.item.subitems[i].filename, config.SUBS_LANGS.keys()))
                else:
                    self.subs.update(handler.get_subs(self.item.filename, config.SUBS_LANGS.keys()))

                box.destroy()
            
            for subs in sorted(self.subs.values(), key=attrgetter('handler.id', 'lang', 'vfile')):
                try:
                    lang = config.SUBS_LANGS[subs['lang']]
                    if self.item.subitems:
                        items.append(menu.MenuItem(_('%s subtitles for "%s" (from %s)' % \
                                     (lang, trunc(os.path.basename(subs['vfile']), 20), subs.handler['name'])),
                                     self.subs_create_subs, (subs['id'])))
                    else:
                        items.append(menu.MenuItem(_('%s subtitles (from %s)' % \
                                     (lang, subs.handler['name'])),
                                     self.subs_create_subs, (subs['id'])))
                    
                except Unicode, e:
                    print e

            # if we have more then 1 set of subs, we give user an option to save all
            if len(self.subs) > 1:
                items.insert(0, menu.MenuItem(_('Get all available subtitles listed below'),
                             self.subs_create_subs, ('all')))

        except (Exception), error:
            _debug_('%s' % (error,), DERROR)
            box.destroy()
            box = PopupBox(text=_('Connection to service failed: ') + str(error))
            box.show()
            time.sleep(2)
            box.destroy()
            return

        if config.SUBS_AUTOACCEPT and len(items > 0):
            self.subs_create_subs(arg=('all'), menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('Subtitles Query'), items)
            menuw.pushmenu(moviemenu)
            return

        box = PopupBox(text=_('No subtitles available'))
        box.show()
        time.sleep(2)
        box.destroy()
        return


    def subs_delete(self, arg=None, menuw=None):
        """
        Delete subtitles for this item
        """
        items         = []
        self.subfiles = []

        # loop through the results and create menu
        # first we need to see if there are existing subs that need to be maintained 
        # (potentially deleted so to speak)
        if hasattr(self.item, 'subitems') and self.item.subitems:
            for i in range(len(self.item.subitems)):
                self.subfiles.extend(self.get_existing_subs(self.item.subitems[i].filename))
        else:
            self.subfiles = self.get_existing_subs(self.item.filename)

        for subfile in self.subfiles:
            try:
                items.append(menu.MenuItem(_('%s' % (os.path.split(subfile)[1])),
                             self.subs_delete_subs, (subfile)))
            except Unicode, e:
                print e

        # if we have more then 1 set of subs, we give user an option to save all
        if len(self.subfiles) > 1:
            items.insert(0, menu.MenuItem(_('Delete all subtitle files listed below'),
                         self.subs_delete_subs, ('all')))

        if config.SUBS_AUTOACCEPT and len(items > 0):
            self.subs_delete_subs(arg='all', menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('Subtitles Query'), items)
            menuw.pushmenu(moviemenu)
            return

        box = PopupBox(text=_('No subtitles to be deleted for %s' % (os.path.base(self.item.filename))))
        box.show()
        time.sleep(2)
        box.destroy()
        return


    def subs_menu_back(self, menuw):
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
        menuw.refresh()


    def subs_create_subs(self, arg=None, menuw=None):
        """
        create subs for the item
        """
        box = PopupBox(text=_('Saving subtitles...'))
        box.show()

        try:
            if arg == None or arg == 'all':
                # we write all available subs
                for subs in self.subs.values():
                    subs.save()
            else:
                # we write only chosen subs
                subs = self.subs[arg]
                _debug_("Writing subs from %s for lang %s" % (subs.handler['name'], subs['lang']))
                subs.save()
                        
        except (Exception), error:
            _debug_('%s' % (error,), DERROR)
            box.destroy()
            box = PopupBox(text=_(error))
            box.show()
            time.sleep(2)
            
        # reset subs
        self.subs = {}

        self.subs_menu_back(menuw)
        box.destroy()
 

    def subs_delete_subs(self, arg=None, menuw=None):
        """
        delete subtitle file(s) for the item
        """
        box = PopupBox(text=_('Deleting subtitles...'))
        box.show()

        try:
            if arg == None or arg == 'all':
                # we delete all available subtitle files
                for subs in self.subfiles:
                    os.remove(subs)
            else:
                # we delete only chosen subtitle file
                _debug_("Deleting subtitle file %s" % (arg))
                os.remove(arg)

        except (Exception), error:
            _debug_('%s' % (error,), DERROR)
            box.destroy()
            box = PopupBox(text=_(error))
            box.show()
            time.sleep(2)
            
        self.subfiles = []

        self.subs_menu_back(menuw)
        box.destroy()
 
