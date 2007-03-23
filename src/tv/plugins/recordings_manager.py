# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# view_recordings.py - Directory handling
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
"""
Plugin to browse the TV recordings directory based on series rather than
just a flat view of the recordings.
Programs not in a series are placed at the top level, while programs that
are a member of a series are placed in a series menu and the menu placed 
at the top level.
"""

import os
import datetime
import traceback
import re
import stat
import copy
import rc
import util.mediainfo as mediainfo

import config
import util


import skin
import plugin
import osd
import fxditem

from item import Item, FileInformation
from playlist import Playlist
from event import *
from gui import ConfirmBox, AlertBox, ProgressBox
from menu import MenuItem, Menu
from video import VideoItem

disk_manager = None

class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin interface for the Manage Recordings TV menu and
    the disk space reclaiming feature.
    """
    def __init__(self):
        """
        normal plugin init, but sets _type to 'mainmenu_tv'
        """
        global disk_manager 
        plugin.MainMenuPlugin.__init__(self)
        
        self._type = 'mainmenu_tv'
        self.parent = None
        
        disk_manager = DiskManager(int(config.TVRM_MINIMUM_DISK_FREE) * 1024 * 1024)
        
        plugin.register(disk_manager, "DiskManager")
        plugin.activate(disk_manager)


    def config(self):
        return [
            ('TVRM_MINIMUM_DISK_FREE', 2048, 'Minimum amount of disk space that must be available at all times in MB'),
            ('TVRM_CONSIDER_UNWATCHED_AFTER', 45, 'Number of days after which to consider deleting unwatched shows if space is required'),
            ('TVRM_EPISODE_FROM_PLOT', None, 'Regular expression to extract the episode name from the plot'),
            ('TVRM_EPISODE_TIME_FORMAT', '%c', 'When the episode name cannot be found use timestamp'),
        ]

    
    def items(self, parent):
        self.parent = parent
        return [RecordingsDirectory(parent)]
    
# ======================================================================
# Recordings Directory Browsing Class
# ======================================================================
class RecordingsDirectory(Item):
    """
    class for browsing the TV Record directory
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='tv')
        self.name = _('Manage Recordings')
        self.dir = config.TV_RECORD_DIR

    # ======================================================================
    # actions
    # ======================================================================

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.browse, _('Browse directory')) ]

        return items
    

    def browse(self, arg=None, menuw=None):
        """
        build the items for the directory
        """
        if not os.path.exists(self.dir):
            AlertBox(text=_('Recordings Directory does not exist')).show()
            return

        if arg == 'update':
            if not self.menu.choices:
                selected_pos = -1
            else:
                # store the current selected item
                selected_id  = self.menu.selected.id()
                selected_pos = self.menu.choices.index(self.menu.selected)

            
        segregated_recordings.sort(lambda l, o: cmp(o.sort('date+name').upper(), l.sort('date+name').upper()))
        

        if arg == 'update':
            # update because of DiskManager            
            self.menu.choices = segregated_recordings
            if selected_pos != -1:
                for i in segregated_recordings:
                    if Unicode(i.id()) == Unicode(selected_id):                       
                        self.menu.selected = i                        
                        break                
                    else:
                        # item is gone now, try to the selection close
                        # to the old item
                        pos = max(0, min(selected_pos-1, len(segregated_recordings)-1))
                        if segregated_recordings:
                            self.menu.selected = segregated_recordings[pos]
                        else:
                            self.menu.selected = None
                if self.menu.selected and selected_pos != -1:
                    self.menuw.rebuild_page()            
                else:
                    self.menuw.init_page()            
                self.menuw.refresh()
        else:
            # normal menu build
            item_menu = Menu(self.name, segregated_recordings, reload_func=self.reload, item_types = 'tv')
            menuw.pushmenu(item_menu)
            
            self.menu  = item_menu
            self.menuw = menuw
            
        disk_manager.set_update_menu(self, menuw, None)
    
    # ======================================================================
    # Helper methods
    # ======================================================================

    def reload(self):
        """
        Rebuilds the menu.
        """
        self.browse(arg='update')
        return None


# ======================================================================
# Program Class
# ======================================================================

class RecordedProgramItem(Item):
    """
    Class to represent a recorded TV program.
    """
    def __init__(self, name, video_item):
        Item.__init__(self, None, skin_type = 'tv')
        self.set_url(None)
        self.type='video'
        self.name  = name
        self.video_item = video_item
        
        keep = self.video_item['keep']
        if not keep:
            keep = False
        else:
            keep = eval(keep)
        self.keep = keep
        
        watched = self.video_item['watched']
        if not watched:
            watched = False
        else:
            watched = eval(watched)
        self.watched =  watched
        
        try:
            self.timestamp = float(self.video_item['recording_timestamp'])
        except ValueError:
            self.timestamp = 0.0
        
        self.set_icon()

    # ======================================================================
    # actions
    # ======================================================================
    
    def actions(self):
        """
        return the default action
        """
        return [ ( self.play, _('Play') ), 
                  ( self.confirm_delete, _('Delete')),
                  ( self.mark_to_keep, _('(Un)Mark to Keep')),
                  ( self.mark_as_watched, _('(Un)Mark as Watched'))]


    def play(self, arg=None, menuw=None):
        """
        Play the recorded program, and then mark it as watched.
        """
        self.video_item.play(menuw=menuw)
        
        # Mark this programme as watched.
        self.update_fxd( True, self.keep)
        self.set_icon()



    def confirm_delete(self, arg=None, menuw=None):
        """
        Confirm whether the user really wants to delete this program.
        """
        self.menuw = menuw
        ConfirmBox(text=_('Do you wish to delete\n \'%s\'?') % self.name,
                   handler=self.delete, default_choice=1,
                   handler_message=_('Deleting...')).show()
    

    def delete(self):
        """
        Delete the recorded program.
        """
        # delete the file
        self.video_item.files.delete()
        if self.menuw:
            self.menuw.delete_submenu(True, True)


    def mark_to_keep(self, arg=None, menuw=None):
        """
        Toggle whether this program should be kept.
        """
        self.keep = not self.keep
        self.update_fxd(self.watched, self.keep)
        self.set_icon()
        if menuw:
            copy_and_replace_menu_item(menuw, self)


    def mark_as_watched(self, arg=None, menuw=None):
        """
        Toggle whether this program has been watched.
        """
        self.watched = not self.watched
        self.update_fxd(self.watched, self.keep)
        self.set_icon()
        if menuw:
            copy_and_replace_menu_item(menuw, self)


    def set_name_to_episode(self):
        """
        Set the name of this recorded program item to the name of
        the episode of this program.
        """
        episode_name = self.video_item['tagline']
        if not episode_name:
            episode_name = self.video_item['subtitle']
        if not episode_name:
            try:
                pat = re.compile(config.TVRM_EPISODE_FROM_PLOT)
                episode = pat.match(self.video_item['plot']).group(1)
                episode_name = episode.strip()
            except Exception, e:
                episode_name = None
        if not episode_name and (self.timestamp > 0.0):
            try:
                episode = datetime.datetime.fromtimestamp(self.timestamp)
                episode_name = episode.strftime(config.TVRM_EPISODE_TIME_FORMAT)
            except Exception, e:
                episode_name = None
        if not episode_name:
            try:
                episode = datetime.datetime.fromtimestamp(os.path.getctime(self.video_item['filename']))
                episode_name = episode.strftime(config.TVRM_EPISODE_TIME_FORMAT)
            except Exception, e:
                episode_name = None
        if not episode_name:
            episode_name = _('(Unnamed)')
        self.video_item['tagline'] = episode_name
        self.name = episode_name

    # ======================================================================
    # Helper methods
    # ======================================================================

    def update_fxd(self, watched=False, keep=False):
        """
        Update the programs fxd file.
        """
        from util.fxdimdb import FxdImdb, makeVideo
        fxd = FxdImdb()

        (filebase, fileext) = os.path.splitext(self.video_item.filename)
        fxd.setFxdFile(filebase, overwrite=TRUE)

        video = makeVideo('file', 'f1', self.video_item.filename)
        fxd.setVideo(video)
        fxd.info['tagline'] = fxd.str2XML(self.video_item['tagline'])
        fxd.info['plot'] = fxd.str2XML(self.video_item['plot'])
        fxd.info['runtime'] = self.video_item['length']
        fxd.info['recording_timestamp'] = self.timestamp
        fxd.info['year'] = self.video_item['year']
        fxd.info['watched'] = str(watched)
        fxd.info['keep'] = str(keep)
        fxd.title = self.video_item.name
        fxd.writeFxd()


    def set_icon(self):
        """
        Set the image displayed next to the menu item text, based on whether 
        the program is being kept or has been watched.
        """
        if self.keep:
            self.icon = config.ICON_DIR + '/status/television_keep.png'
        elif self.watched:
            self.icon = config.ICON_DIR + '/status/television_watched.png'
        else:
            self.icon = config.ICON_DIR + '/status/television_unwatched.png'
   

    def __getitem__(self, key):
        """
        Map through to the underlying VideoItem
        """
        return self.video_item[key]


    def sort(self, mode=None):
        """
        Return a string to use to sort this item.
        """
        if mode == 'date+name':
            return u'%010.0f%s' % (self.timestamp, self.name)
            
        return self.name
    
    def id(self):
        return self.sort('date+name')

# ======================================================================
# Series Menu Class
# ======================================================================

class Series(Item):
    """
    Class representing a set of programs with the same name, but (probably) 
    different taglines.
    """
    def __init__(self, name, items):
        Item.__init__(self, None, skin_type = 'tv')
        
        self.set_url(None)
        self.type = 'dir'
        self.name = name
        self.update(items)


    # ======================================================================
    # actions
    # ======================================================================

    def actions(self):
        """
        return the default action
        """
        return [ ( self.browse, _('Browse episodes')),
                  ( self.confirm_delete, _('Delete all episodes')),
                  ( self.mark_all_to_keep, _('Keep all episodes')),
                  ( self.play_all, _('Play all episodes') )]


    def browse(self, arg=None, menuw=None):
        """
        Browse the recorded programs in a series.
        """
        if arg == 'update':
            # series has been deleted!
            if not self.items:
                rc.post_event(MENU_BACK_ONE_MENU)
                return
                
            if not self.menu.choices:
                selected_pos = -1
            else:
                # store the current selected item
                selected_id  = self.menu.selected.id()
                selected_pos = self.menu.choices.index(self.menu.selected)

            # update because of DiskManager
            self.menu.choices = self.items
            if selected_pos != -1:
                for i in self.items:
                    if Unicode(i.id()) == Unicode(selected_id):                       
                        self.menu.selected = i                        
                        break                
                    else:
                        # item is gone now, try to the selection close
                        # to the old item
                        pos = max(0, min(selected_pos-1, len(self.items)-1))
                        if self.items:
                            self.menu.selected = self.items[pos]
                        else:
                            self.menu.selected = None
                if self.menu.selected and selected_pos != -1:
                    self.menuw.rebuild_page()            
                else:
                    self.menuw.init_page()            
                self.menuw.refresh()
        else:
            # normal menu build
            item_menu = Menu(self.name, self.items, item_types = 'tv')
            menuw.pushmenu(item_menu)
            
            self.menu  = item_menu
            self.menuw = menuw
            
        disk_manager.set_update_menu(self, menuw, None)


    def play_all(self, arg=None, menuw=None):
        """
        Play all programs in a series.
        """
        # TODO: Implement!
        pass

    
    def confirm_delete(self, arg=None, menuw=None):
        """
        Confirm the user wants to delete an entire series.
        """
        self.menuw = menuw
        ConfirmBox(text=_('Do you wish to delete the series\n \'%s\'?') % self.name,
                   handler=self.delete_all, default_choice=1,
                   handler_message=_('Deleting...')).show()


    def delete_all(self):
        """
        Delete all programs in a series.
        """
        for item in self.items:
            item.delete()
        if self.menuw:
            self.menuw.delete_submenu(True, True)


    def mark_all_to_keep(self, arg=None, menuw=None):
        """
        Mark all programs in a series to keep.
        """
        for item in self.items:
            if not item.keep:
                item.mark_to_keep()
        self.set_icon()
        if menuw:
            copy_and_replace_menu_item(menuw, self)


    def update(self, items):
        """
        Update the list of programs that make up this series.
        """
        self.items = items
        for item in self.items:
            item.set_name_to_episode()
            
        # TODO: Replace with smart sort that knows about 'n/m <subtitle>' style names
        self.items.sort(lambda l, o: cmp(l.sort().upper(), o.sort().upper()))            
        self.set_icon()


    # ======================================================================
    # Helper methods
    # ======================================================================
    
    def set_icon(self):
        """
        Set the image displayed next to the menu item text, based on whether 
        the series is being kept or has been watched.
        """
        keep = True
        watched = True
        
        for item in self.items:
            if not item.keep:
                keep = False
            if not item.watched:
                watched = False
        if keep:
            self.icon = config.ICON_DIR + '/status/series_keep.png'
        elif watched:
            self.icon = config.ICON_DIR + '/status/series_watched.png'
        else:
            self.icon = config.ICON_DIR + '/status/series_unwatched.png'


    def __getitem__(self, key):
        """
        Returns the number of episodes when
        """
        if key == 'tagline':
            return unicode('%d ' % len(self.items)) + _('episodes')
        if key == 'content':
            content = ''
            for i in range(0, len(self.items)):
                content += self.items[i].name
                if i < (len(self.items) - 1):
                    content += ', '
            return content
                
        return Item.__getitem__(self,key)


    def sort(self, mode=None):
        """
        Return a string to use to sort this item.
        """
        if mode == 'date+name':
            latest_timestamp = 0.0
            for item in self.items:
                if item.timestamp > latest_timestamp:
                    latest_timestamp = item.timestamp
            return u'%10d%s' % (int(latest_timestamp), self.name)
            
        return self.name
        
    def id(self):
        return 'series:' + self.name


# ======================================================================
# Disk Management Class
# ======================================================================
 
series_table = {}
segregated_recordings = []
all_recordings = []
 
class DiskManager(plugin.DaemonPlugin):
    """
    Class to ensure a minimum amount of disk space is always available.
    """
    def __init__(self, required_space):
        plugin.DaemonPlugin.__init__(self)
        self.poll_interval = 5 # half a second
        self.poll_menu_only = False
        self.required_space = required_space
        self.last_time = 0;
        self.menu = None
        self.menuw = None
        self.interested_series = None
        
        self.update_recordings()


    def poll(self):
        """
        Check that the available disk space is greater than TVRM_MINIMUM_DISK_FREE
        """
        # Check space first so that any removals are picked up straight away.
        self.check_space()
        
        self.check_recordings()
    
    def set_update_menu(self, menu, menuw, interested_series):
        """
        Set the menu to update when the recordings directory changes.
        """
        self.menuw = menuw
        self.interested_series = interested_series
        self.menu = menu
        
        
    def check_recordings(self):
        """
        Check the TV recordings directory to determine if the contents have changed,
        and if they have update the list of recordings and the currently registered 
        menu.
        """
        changed = False
        try:
            if vfs.mtime(config.TV_RECORD_DIR) > self.last_time:
                changed = True
        except (OSError, IOError):
            # the directory is gone
            _debug_('DiskManager: unable to read recordings directory')
            return
            
        if changed:
            self.last_time = vfs.mtime(config.TV_RECORD_DIR)
            self.update_recordings()
            if self.menu:
                self.menu.browse(menuw=self.menuw, arg='update')
    
    def update_recordings(self):
        """
        Update the list of recordings.
        """
        global all_recordings, segregated_recordings, series_table
        files       = vfs.listdir(config.TV_RECORD_DIR, include_overlay=True)
        num_changes = mediainfo.check_cache(config.TV_RECORD_DIR)

        if num_changes > 0:
            mediainfo.cache_dir(config.TV_RECORD_DIR, callback=None)

        series = {}

        recordings = fxditem.mimetype.get(None, files)       
        for recorded_item in recordings:
            rpitem = RecordedProgramItem(recorded_item.name, recorded_item)
            
            if series.has_key(recorded_item.name):
                series_items = series[recorded_item.name]
            else:
                series_items = []
                series[recorded_item.name] = series_items
            series_items.append(rpitem)

        items = []
        all_items = []
        for name,programs in series.iteritems():
            if len(programs) == 1:
                # Just one program in so don't bother to add it to a series menu.
                item = programs[0]
                if name in series_table:
                    series_item = series_table[name]
                    series_item.items = None
                    del series_table[name]
            else:
                if name in series_table:
                    item = series_table[name]
                    item.update(programs)
                else:
                    # Create a series menu and add all the programs in order.
                    item = Series(name, programs)
                    series_table[name] = item
                
            items.append(item)
            all_items += programs
        
        # Clean the series table of series that no longer exist
        for name,series_item in series_table.items():
            if not series_item in items:
                series_item.items = None
                del series_table[name]
        
        segregated_recordings = items
        all_recordings = all_items
        
        self.last_time = vfs.mtime(config.TV_RECORD_DIR)

 
    def check_space(self):
        """
        Check the amount of disk space has not dropped below the minimum required.
        If it has attempt to remove some recordings.
        """
        if util.freespace(config.TV_RECORD_DIR) < self.required_space:
            print 'Need to free up some space now!'
            candidates = self.generate_candidates()
            
            while (util.freespace(config.TV_RECORD_DIR) < self.required_space) and (len(candidates) > 0):
                # Delete a candidate
                candidate = candidates.pop(0)
                watched, keep = self.candidate_status(candidate)
                candidates.files.delete()
        
    
    def generate_candidates(self):
        watched_candidates = []
        unwatched_candidates = []
        
        today = datetime.date.today()
        
        for recorded_item in all_recordings:
            if recorded_item.watched and not recorded_item.keep:
                watched_candidates.append(recorded_item)
                
            elif not recorded_item.watched and not recorded_item.keep:    
                recorded_date = datetime.date.fromtimestamp(recorded_item.timestamp)
                timediff = today - recorded_date
                
                if (timediff.days >  config.TVRM_CONSIDER_UNWATCHED_AFTER):
                    unwatched_candidates.append(recorded_item)

        # Now sort the recordings so the oldest one is first.
        watched_candidates.sort(lambda l, o: cmp(l.timestamp, o.timestamp))
        unwatched_candidates.sort(lambda l, o: cmp(l.timestamp, o.timestamp))
        
        return watched_candidates + unwatched_candidates


# ======================================================================
# Helper functions
# ======================================================================
def copy_and_replace_menu_item(menuw, item):
    menu = menuw.menustack[-1]
    # rebuild menu
    try:
        idx = menu.choices.index(item)
        cloned_item = copy.copy(item)
        menu.choices[idx] = cloned_item
        if menu.selected is item:
            menu.selected = cloned_item
        menuw.init_page()
        menuw.refresh()
    except ValueError, e:
        menuw.delete_submenu(True, True)


