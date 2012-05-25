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
#        SUBS_LANGS = { 'pol': ('Polish'), 'eng': ('English') }
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

__author__           = 'Maciej Urbaniak'
__author_email__     = 'maciej@urbaniak.org'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '$Revision$'
__license__          = 'GPL'

# Module Imports
import logging
logger = logging.getLogger('freevo.video.plugins.subtitles')

import os
import glob
from operator import itemgetter, attrgetter

import menu
import config
import plugin
import re
import time
import util
import dialog
import dialog.utils 

HEAD = 'head'
TAIL = 'tail'

def trunc(what, cnt, where=HEAD, ellipsis='...'):
    if where == HEAD:
        return (ellipsis + what[len(what) - (cnt - len(ellipsis)):]) if len(what) > cnt else what
    return (what[:len(what) - (cnt + len(ellipsis))] + ellipsis) if len(what) > cnt else what


class Error(Exception):
    """
    Base class for exceptions in Subs
    """
    def __str__(self):
        return self.message
    def __init__(self, message):
        self.message = message


class SubtitlesError(Error):
    """
    used to raise Subtitle specific exceptions
    """
    pass


class SubtitlesPlugin(plugin.Plugin):
    """
    Base Subtitles Plugin handler class definition including all methods that subclasses 
    shall overwrite
    """
    def __init__(self, id, name, langs):
        plugin.Plugin.__init__(self)
        self.id    = id
        self.name  = name
        self.langs = langs
        self._type = 'subtitles'

    
    def __getitem__(self, key):
        """
        Get the item's attribute.
        @returns: the specific attribute
        """
        if key == 'name':
            return self.name

        if key == 'id': 
            return self.id
        
        return ''

    
    def get_subs(self, vfile_, langs_):
        """
        Derived class must overwrite this method
        Get all available subtitles for the item
        @param vfile_ :   filename of the video file
        @param langs_ :   requested languages
        @returns:         the collection of subtitles keyed by the subtitle id
        """
        return {}
        

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
        @param key:  key
        @returns:    the specific attribute
        """
        if key == 'id': 
            return hash((self.handler['id'], self.lang, self.vfile))
            

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
            self.sfile = '%s.%s.%s.%s' % (self.vbase, self.handler['id'], self.lang, self.fmt)
        else:
            self.sfile = '%s.%s.%s' % (self.vbase, self.handler['id'], self.fmt)

        if not config.SUBS_FORCE_UPDATE and os.path.exists(self.sfile):
            msg = 'Skipping, subtitles %s aready exist and forced update is disabled' % (self.sfile)
            logger.warning(msg)
            raise SubtitlesError(msg)

        if config.SUBS_FORCE_BACKUP and os.path.exists(self.sfile):
            vfile_bkp = self.sfile + '.bkp'
            try:
                if os.path.exists(vfile_bkp):
                    os.remove(vfile_bkp)

                os.rename(self.sfile, vfile_bkp)

            except (IOError, OSError), e:
                msg = 'Skipping due to backup of \'%s\' as \'%s\' failure: %s' % (self.sfile, vfile_bkp, e)
                logger.warning(msg)
                raise SubtitlesError(msg)
            else:
                logger.info('Old subtitle backed up as \'%s\'', vfile_bkp)

        return True

    
class PluginInterface(plugin.ItemPlugin):
    """
    You can add subtitles for video items with the plugin.

    Activate with:
    | plugin.activate('video.subtitles')
    Make sure the suitable subtitles handler plugin is activated too:
    | plugin.activate('video.subtitles.napiprojekt')
    and/or
    | plugin.activate('video.subtitles.opensubtitles')
    etc.

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

        plugin.ItemPlugin.__init__(self)
        
        self.handlers = self.get_handlers()


    def config(self):
        """
        Returns the config variables used by this plugin
        """
        return [
            ('SUBS_LANGS',          { 'eng': ('English') },
                'Subtitles to download'),
            ('SUBS_EXTS',           [ '.srt', '.sub', '.txt', '.ssa', '.smi', '.ass', '.mpl'], 
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
        return len(self.get_existing_subs(file))



    def get_existing_subs(self, file):
        """
        Get all existing subitle files that match the pattern 
        into the collection and return it.
        """
        # if there are literal chars like '[' or ']' in the filename then glob will 
        # not match filenames. Need to replace them with '?'. Most likely it confuses
        # regex inside glob
        base = re.sub('[\]\[]+', '?', os.path.splitext(file)[0])

        return [n for n in glob.glob(base + '*') \
            if os.path.splitext(n)[1] in config.SUBS_EXTS]


    def get_handlers(self):
        """
        Get all regitered subtitle plugins into the local dictionary
        @return:    Hanlders dictionary keyed by the handler ID.
        """
        if self.handlers is None or len(self.handlers) < 1:
            handlers = plugin.get('subtitles')
            logger.info('Available subtitles handlers : %s', handlers)

            for handler in handlers:
                self.handlers[handler['id']] = handler
                logger.info('Successfuly loaded subtitle handler %s', handler.name)

        return self.handlers             
        
        

    def subs_search(self, arg=None, menuw=None):
        """
        Search subtitle website for subtitles for this item
        """
        self.subs = {}
        items     = []
        dlg       = None
    
        try:
            #get the subtitles from each active handler
            for handler in self.get_handlers().values():
                dlg = dialog.utils.show_message(_('Searching %s...' % (handler['name'])), 'status', 0)

                if self.item.subitems:
                    for i in range(len(self.item.subitems)):
                        self.subs.update(handler.get_subs(self.item.subitems[i].filename, config.SUBS_LANGS.keys()))
                else:
                    self.subs.update(handler.get_subs(self.item.filename, config.SUBS_LANGS.keys()))

                dialog.utils.hide_message(dlg)

            for subs in sorted(self.subs.values(), key=attrgetter('handler.id', 'lang', 'vfile')):
                try:
                    lang = config.SUBS_LANGS[subs.lang]
                    if self.item.subitems:
                        items.append(menu.MenuItem(_('%s subtitles for "%s" (%s from %s)' % \
                                     (lang, trunc(os.path.basename(subs.vfile), 20), subs.fmt, subs.handler['name'])),
                                     self.subs_create_subs, (subs['id'])))
                    else:
                        items.append(menu.MenuItem(_('%s subtitles (%s from %s)' % \
                                     (lang, subs.fmt, subs.handler['name'])),
                                     self.subs_create_subs, (subs['id'])))
                    
                except (Unicode) as err:
                    logger.warning(err)

            # if we have more then 1 set of subs, we give user an option to save all
            if len(self.subs) > 1:
                items.insert(0, menu.MenuItem(_('Get all available subtitles listed below'),
                             self.subs_create_subs, ('all')))

        except (Exception), err:
            dialog.utils.hide_message(dlg)
            logger.error('%s' % (err))
            dialog.utils.show_message(_('Connection to subtitle service failed'))
            return

        if config.SUBS_AUTOACCEPT and len(items) > 0:
            self.subs_create_subs(arg=('all'), menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('Subtitles Query'), items)
            menuw.pushmenu(moviemenu)
            return

        dialog.utils.show_message(_('No subtitles available'))
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

        if config.SUBS_AUTOACCEPT and len(items) > 0:
            self.subs_delete_subs(arg='all', menuw=menuw)
            return

        if items:
            moviemenu = menu.Menu(_('Subtitles Query'), items)
            menuw.pushmenu(moviemenu)
            return

        dialog.utils.show_message(_('No subtitles to be deleted'))
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
        dlg = dialog.utils.show_message(_('Saving subtitles...'), 'status', 0)
 
        try:
            if arg == None or arg == 'all':
                # we write all available subs
                for subs in self.subs.values():
                    subs.save()

            else:
                # we write only chosen subs
                subs = self.subs[arg]
                logger.debug('Writing subs from %s for lang %s', subs.handler['name'], subs.lang)
                subs.save()
                        
        except (Exception), err:
            logger.error('%s' % (err))
            dialog.utils.hide_message(dlg)
            dlg = dialog.utils.show_message(_('Error while saving subtitles'))
            
        # reset subs
        self.subs = {}
        self.subs_menu_back(menuw)
        dialog.utils.hide_message(dlg)
 

    def subs_delete_subs(self, arg=None, menuw=None):
        """
        delete subtitle file(s) for the item
        """
        dlg = dialog.utils.show_message(_('Deleting subtitles...'), 'status', 0)

        try:
            if arg == None or arg == 'all':
                # we delete all available subtitle files
                for subs in self.subfiles:
                    os.remove(subs)

            else:
                # we delete only chosen subtitle file
                logger.debug('Deleting subtitle file %s', arg)
                os.remove(arg)

        except (Exception), error:
            logger.error('%s' % (err))
            dialog.utils.hide_message(dlg)
            dlg = dialog.utils.show_message(_('Error while deleting subtitles'))
            
        self.subfiles = []
        self.subs_menu_back(menuw)
        dialog.utils.hide_message(dlg)
 