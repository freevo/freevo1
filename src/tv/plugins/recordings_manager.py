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
# $Log$
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
# ----------------------------------------------------------------------- */


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
from gui import InputBox, AlertBox, ProgressBox
from menu import MenuItem, Menu
from video import VideoItem

class PluginInterface(plugin.MainMenuPlugin):
    """
    """
    def __init__(self):
        """
        normal plugin init, but sets _type to 'mainmenu_tv'
        """
        plugin.MainMenuPlugin.__init__(self)
        
        self._type = 'mainmenu_tv'
        self.parent = None
        
        self.disk_manager = DiskManager(int(config.TVRM_MINIMUM_DISK_FREE) * 1024 * 1024)
        
        plugin.register(self.disk_manager, "DiskManager")
        plugin.activate(self.disk_manager)


    def config(self):
        return [
            ('TVRM_MINIMUM_DISK_FREE', 2048, 'Minimum amount of disk space that must be available at all times in MB'),
            ('TVRM_CONSIDER_UNWATCHED_AFTER', 45, 'Number of days after which to consider deleting unwatched shows if space is required'),
            ('TVRM_EPISODE_FROM_PLOT', None, 'Regular expression to extract the episode name from the plot'),
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

        if config.OSD_BUSYICON_TIMER:
            osd.get_singleton().busyicon.wait(config.OSD_BUSYICON_TIMER[0])
        
        files       = vfs.listdir(self.dir, include_overlay=True)
        num_changes = mediainfo.check_cache(self.dir)

        pop = None
        callback=None
        if num_changes > 10:
            pop = ProgressBox(text=_('Scanning recordings, be patient...'),
                              full=num_changes)
            pop.show()
            callback=pop.tick


        elif config.OSD_BUSYICON_TIMER and len(files) > config.OSD_BUSYICON_TIMER[1]:
            # many files, just show the busy icon now
            osd.get_singleton().busyicon.wait(0)
        

        if num_changes > 0:
            mediainfo.cache_dir(self.dir, callback=callback)

        series = {}

        recordings = fxditem.mimetype.get(self, files)       
        for recorded_item in recordings:
            if series.has_key(recorded_item.name):
                series_items = series[recorded_item.name]
            else:
                series_items = []
                series[recorded_item.name] = series_items
            series_items.append(recorded_item)

        items = []
        
        for name,programs in series.iteritems():
            if len(programs) == 1:
                # Just one program in so don't bother to add it to a series menu.
                items.append(RecordedProgramItem(programs[0].name, programs[0]))
            else:
                # Create a series menu and add all the programs in order.
                items.append(Series(name, programs))
            
        items.sort(lambda l, o: cmp(o.sort('date+name').upper(), l.sort('date+name').upper()))
        
        if pop:
            pop.destroy()
            # closing the poup will rebuild the menu which may umount
            # the drive

        if config.OSD_BUSYICON_TIMER:
            # stop the timer. If the icons is drawn, it will stay there
            # until the osd is redrawn, if not, we don't need it to pop
            # up the next milliseconds
            osd.get_singleton().busyicon.stop()

        if arg == 'update':
            # update because of dirwatcher changes            
            self.menu.choices = items
            if selected_pos != -1:
                for i in items:
                    if Unicode(i.id()) == Unicode(selected_id):                       
                        self.menu.selected = i                        
                        break                
                    else:
                        # item is gone now, try to the selection close
                        # to the old item
                        pos = max(0, min(selected_pos-1, len(items)-1))
                        if items:
                            self.menu.selected = items[pos]
                        else:
                            self.menu.selected = None
                if self.menu.selected and selected_pos != -1:
                    self.menuw.rebuild_page()            
                else:
                    self.menuw.init_page()            
                    self.menuw.refresh()
        else:
            # normal menu build
            item_menu = Menu(self.name, items, reload_func=self.reload, item_types = 'tv')
            menuw.pushmenu(item_menu)
            
            self.menu  = item_menu
            self.menuw = menuw

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
        fxd.info['recording_timestamp'] = self.video_item['recording_timestamp']
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
            try:
                return u'%010.0f%s' % (float(self.video_item['recording_timestamp']), self.name)
            except ValueError:
                return u'%010.0f%s' % (0.0, self.name)
            
        return self.name

# ======================================================================
# Series Menu Class
# ======================================================================
class Series(Item):
    """
    Class representing a set of programs with the same name, but (probably) 
    different taglines.
    """
    def __init__(self, name, programs):
        Item.__init__(self, None, skin_type = 'tv')
        
        self.set_url(None)
        self.type = 'dir'
        self.name = name
        self.programs = programs
        self.items = []
        for program in self.programs:
            self.items.append(RecordedProgramItem(program['tagline'], program))
        # TODO: Replace with smart sort that knows about 'n/m <subtitle>' style names
        self.items.sort(lambda l, o: cmp(l.sort().upper(), o.sort().upper()))
        self.set_icon()



    # ======================================================================
    # actions
    # ======================================================================

    def actions(self):
        """
        return the default action
        """
        return [ ( self.browse, _('Browse episodes')),
                  ( self.delete_all, _('Delete all episodes')),
                  ( self.mark_all_to_keep, _('Keep all episodes')),
                  ( self.play_all, _('Play all episodes') )]


    def browse(self, arg=None, menuw=None):
        """
        Browse the recorded programs in a series.
        """
        # normal menu build
        item_menu = Menu(self.name, self.items, item_types = 'tv')
        menuw.pushmenu(item_menu)
        
        self.menu  = item_menu
        self.menuw = menuw


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
            return unicode('%d ' % len(self.programs)) + _('episodes')
        if key == 'content':
            content = ''
            for i in range(0, len(self.programs)):
                episode_name = self.programs[i]['tagline']
                if not episode_name:
                    episode_name = self.programs[i]['subtitle']
                    self.programs[i]['tagline'] = episode_name
                    if not episode_name:
                        try:
                            pat = re.compile(config.TVRM_EPISODE_FROM_PLOT)
                            episode_name = pat.match(self.programs[i]['plot']).group(1)
                            self.programs[i]['tagline'] = episode_name.strip()
                        except Exception, e:
                            print self.programs[i]['name'], e
                        if not episode_name:
                            episode_name = _('(Unnamed)')
                            self.programs[i]['tagline'] = episode_name
                content += episode_name
                if i < (len(self.programs) - 1):
                    content += ', '
            return content
                
        return Item.__getitem__(self,key)


    def sort(self, mode=None):
        """
        Return a string to use to sort this item.
        """
        if mode == 'date+name':
            latest_timestamp = 0.0
            for program in self.programs:
                timestamp = float(program['recording_timestamp'])
                if timestamp > latest_timestamp:
                    latest_timestamp = timestamp
            return u'%10d%s' % (int(latest_timestamp), self.name)
            
        return self.name


# ======================================================================
# Disk Management Class
# ======================================================================
 
class DiskManager(plugin.DaemonPlugin):
    """
    Class to ensure a minimum amount of disk space is always available.
    """
    def __init__(self, required_space):
        plugin.DaemonPlugin.__init__(self)
        self.poll_interval = 10 # Once a second
        self.poll_menu_only = False
        self.required_space = required_space


    def poll(self):
        """
        Check that the available disk space is greater than TVRM_MINIMUM_DISK_FREE
        """
        if util.freespace(config.TV_RECORD_DIR) < self.required_space:
            print 'Need to free up some space now!'
            candidates = self.generate_candidates()
            
            while (util.freespace(config.TV_RECORD_DIR) < self.required_space) and (len(candidates) > 0):
                # Delete a candidate
                candidate = candidates.pop(0)
                watched, keep = self.candidate_status(candidate)
                print 'Deleting %s (watched %s, keep %s timestamp %s)' % (candidate.name, watched, keep, candidate['recording_timestamp'])
                #candidates.files.delete()
        
    
    def generate_candidates(self):
        files       = vfs.listdir(config.TV_RECORD_DIR, include_overlay=True)
        num_changes = mediainfo.check_cache(config.TV_RECORD_DIR)

        watched_candidates = []
        unwatched_candidates = []
        
        today = datetime.date.today()
        
        recordings = fxditem.mimetype.get(None, files)       
        for recorded_item in recordings:
            watched, keep = self.candidate_status(recorded_item)
            if watched and not keep:
                watched_candidates.append(recorded_item)
            if not watched and not keep:    
                recorded_date = datetime.date.fromtimestamp(float(recorded_item['recording_timestamp']))
                timediff = today - recorded_date
                if (timediff.days >  config.TVRM_CONSIDER_UNWATCHED_AFTER):
                    unwatched_candidates.append(recorded_item)

        # Now sort the recordings so the oldest one is first.
        watched_candidates.sort(lambda l, o: cmp(float(l['recording_timestamp']), float(o['recording_timestamp'])))
        unwatched_candidates.sort(lambda l, o: cmp(float(l['recording_timestamp']), float(o['recording_timestamp'])))
        
        return watched_candidates + unwatched_candidates
    
    def candidate_status(self, candidate):
        keep = candidate['keep']
        if not keep:
            keep = False
        else:
            keep = eval(keep)
        
        watched = candidate['watched']
        if not watched:
            watched = False
        else:
            watched = eval(watched)
            
        return (watched, keep)
        
        
        
# ======================================================================
# Helper functions
# ======================================================================
def copy_and_replace_menu_item(menuw, item):
    cloned_item = copy.copy(item)
    menu = menuw.menustack[-1]
    # rebuild menu
    menu.choices[menu.choices.index(item)] = cloned_item
    if menu.selected is item:
        menu.selected = cloned_item

    menuw.init_page()
    menuw.refresh()
