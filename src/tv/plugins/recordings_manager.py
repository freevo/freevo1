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
import os.path
import datetime
import traceback
import re
import stat
import copy
import rc
import util.mediainfo as mediainfo

import config
import util


import plugin
import fxditem

from item import Item
from playlist import Playlist
from directory import DirItem
from event import *
from gui import ConfirmBox, AlertBox, ProgressBox
from menu import MenuItem, Menu
from video import VideoItem

disk_manager = None


SORTING_DATE_NAME        = 0
SORTING_STATUS_NAME      = 1
SORTING_STATUS_DATE_NAME = 2
SORTING_NAME             = 4

sorting_methods = [_('Date then Name'),
                   _('Status then Name'),
                   _('Status, Date then Name'),
                   _('Name')
                   ]
series_sorting_methods = sorting_methods

status_order_methods = ['Unwatched, Keep, Watched',
                        'Unwatched, Watched, Keep',
                        'Keep, Unwatched, Watched']

STATUS_ORDERS = [ ('3', '2', '0', '1'),
                  ('3', '0', '1', '2'),
                  ('1', '3', '0', '2')]

STATUS_ORDER_UNWATCHED    = 0
STATUS_ORDER_KEEP         = 1
STATUS_ORDER_WATCHED      = 2
STATUS_ORDER_KEEP_WATCHED = 3

sorting = 0
sorting_reversed = False
series_sorting = 0
series_sorting_reversed = False
status_order = 0


class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to browse the TV recordings directory based on series rather than
    just a flat view of the recordings.

    Programs not in a series are placed at the top level, while programs that
    are a member of a series are placed in a series menu and the menu placed
    at the top level.

    Activate with:
    | plugin.activate('tv.recordings_manager',level=5)
    This also automatically activates tv.recordings_manager.DiscManager.

    You probably want also to deactivate the generic view_recordings plugin,
    which is kind of redundant if you use the recordings_manager plugin:
    | plugin.remove('tv.view_recordings')
    """

    def __init__(self):
        """
        normal plugin init, but sets _type to 'mainmenu_tv'
        """
        if not config.TV_RECORD_DIR:
            self.reason = 'TV_RECORD_DIR is not set'
            return
        if not os.path.isdir(config.TV_RECORD_DIR):
            self.reason = 'TV_RECORD_DIR "%s" is not a directory' % (config.TV_RECORD_DIR)
            return

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
            ('TVRM_EPISODE_TIME_FORMAT', '%c', 'When the episode name cannot be found use timestamp in this format'),
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
        self.settings_fxd = os.path.join(self.dir, 'folder.fxd')
        self.load_settings()

        self.blue_action = (self.configure, _('Configure directory'))

    # ======================================================================
    # actions
    # ======================================================================

    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, _('Browse directory')) , self.blue_action]
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

        items = segregated_recordings
        items.sort(lambda l, o: cmp(o.sort(sorting).upper(), l.sort(sorting).upper()))
        if sorting_reversed:
            items.reverse()

        if arg == 'update':
            # update because of DiskManager
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
            item_menu = Menu(self.name, items, reload_func=self.reload, item_types='tv')
            menuw.pushmenu(item_menu)

            self.menu  = item_menu
            self.menuw = menuw

        disk_manager.set_update_menu(self, self.menu, self.menuw)


    # ======================================================================
    # Configure methods
    # ======================================================================

    def configure_sorting(self, arg=None, menuw=None):
        '''
        document me
        '''
        exec('%s += 1' % arg, globals())

        if eval('%s >= len(%s_methods)' %(arg, arg), globals()):
            exec('%s = 0' % arg, globals())

        self.save_settings()

        item = menuw.menustack[-1].selected
        item.name = item.name[:item.name.find(u'\t') + 1]  + _(eval('%s_methods[%s]' % (arg,arg), globals()))

        copy_and_replace_menu_item(menuw, item)
        menuw.init_page()
        menuw.refresh()


    def configure_sorting_reversed(self, arg=None, menuw=None):
        '''
        document me
        '''
        exec('%s = not %s' % (arg,arg), globals())
        self.save_settings()

        item = menuw.menustack[-1].selected
        item.name = item.name[:item.name.find(u'\t') + 1]  + self.configure_get_icon(eval(arg, globals()))

        copy_and_replace_menu_item(menuw, item)
        menuw.init_page()
        menuw.refresh()


    def configure_get_icon(self, value):
        '''
        document me
        '''
        if value:
            icon = u'ICON_LEFT_ON_' + _('on')
        else:
            icon = u'ICON_LEFT_OFF_' + _('off')
        return icon


    def configure(self, arg=None, menuw=None):
        '''
        document me
        '''
        items = [
            MenuItem(_('Sort by') + u'\t' + _(sorting_methods[sorting]),
                self.configure_sorting, 'sorting'),
            MenuItem(_('Reverse sort')+ u'\t' + self.configure_get_icon(sorting_reversed),
                self.configure_sorting_reversed, 'sorting_reversed'),
            MenuItem(_('Sort series by') + u'\t' + _(series_sorting_methods[series_sorting]),
                self.configure_sorting, 'series_sorting'),
            MenuItem(_('Reverse series sort')+  u'\t' + self.configure_get_icon(series_sorting_reversed),
                self.configure_sorting_reversed, 'series_sorting_reversed'),
            MenuItem(_('Status order') + u'\t' + _(status_order_methods[status_order]),
                self.configure_sorting, 'status_order')
        ]
        m = Menu(_('Configure'), items)
        m.table = (50, 50)
        menuw.pushmenu(m)

    # ======================================================================
    # Helper methods
    # ======================================================================

    def reload(self):
        """
        Rebuilds the menu.
        """
        self.browse(arg='update')
        return None

    def load_settings(self):
        '''
        document me
        '''
        if vfs.isfile(self.settings_fxd):
            try:
                parser = util.fxdparser.FXD(self.settings_fxd)
                parser.set_handler('tvrmsettings', self.read_settings_fxd)
                parser.parse()
            except:
                print "fxd file %s corrupt" % self.settings_fxd
                traceback.print_exc()

    def save_settings(self):
        '''
        document me
        '''
        try:
            parser = util.fxdparser.FXD(self.settings_fxd)
            parser.set_handler('tvrmsettings', self.write_settings_fxd, 'w', True)
            parser.save()
        except:
            print "fxd file %s corrupt" % self.settings_fxd
            traceback.print_exc()

    def read_settings_fxd(self, fxd, node):
        '''
        parse the xml file for directory settings

        <?xml version="1.0" ?>
        <freevo>
          <tvrmsettings>
            <setvar name="sorting" val="0"/>
          </tvrmsettings>
        </freevo>
        '''

        for child in fxd.get_children(node, 'setvar', 1):
            name = child.attrs[('', 'name')]
            val = child.attrs[('', 'val')]
            exec('%s = %s' % (name, val), globals())


    def write_settings_fxd(self, fxd, node):
        """
        callback to save the modified fxd file
        """
        # remove old setvar
        for child in copy.copy(node.children):
            if child.name == 'setvar':
                node.children.remove(child)

        # add current vars as setvar
        fxd.add(fxd.XMLnode('setvar', (('name', 'sorting'),                 ('val', sorting))),          node, None)
        fxd.add(fxd.XMLnode('setvar', (('name', 'sorting_reversed'),        ('val', sorting_reversed))), node, None)
        fxd.add(fxd.XMLnode('setvar', (('name', 'series_sorting'),          ('val', series_sorting))),   node, None)
        fxd.add(fxd.XMLnode('setvar', (('name', 'series_sorting_reversed'), ('val', series_sorting_reversed))), node, None)
        fxd.add(fxd.XMLnode('setvar', (('name', 'status_order'),            ('val', status_order))),     node, None)


# ======================================================================
# Program Class
# ======================================================================

class RecordedProgramItem(VideoItem):
    """
    Class to represent a recorded TV program.
    """
    def __init__(self, name, video_item):
        VideoItem.__init__(self, url=video_item.url, parent=video_item.parent)
        self.video_item = video_item
        self.name = name
        self.files = video_item.files
        self.parent = DirItem(config.TV_RECORD_DIR, None)

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
        actions = VideoItem.actions(self)
        items = actions[0:2]
        items.append((self.mark_to_keep, self.keep and _('Unmark to Keep') or _('Mark to Keep')))
        items.append((self.mark_as_watched, self.watched and _('Unmark as Watched') or _('Mark as Watched')))
        items = items + actions[2:]
        return items


    def play(self, arg=None, menuw=None, alternateplayer=False):
        """
        Play the recorded program, and then mark it as watched.
        """
        self.video_item.play(menuw=menuw, arg=arg, alternateplayer=alternateplayer)

        # Mark this programme as watched.
        self.update_fxd(True, self.keep)
        self.set_icon()


    def mark_to_keep(self, arg=None, menuw=None):
        """
        Toggle whether this program should be kept.
        """
        self.keep = not self.keep
        self.update_fxd(self.watched, self.keep)
        self.set_icon()
        if menuw:
            copy_and_replace_menu_item(menuw, self)
            menuw.refresh(reload=True)


    def mark_as_watched(self, arg=None, menuw=None):
        """
        Toggle whether this program has been watched.
        """
        self.watched = not self.watched
        self.update_fxd(self.watched, self.keep)
        self.set_icon()
        if menuw:
            copy_and_replace_menu_item(menuw, self)
            menuw.refresh(reload=True)


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
        self.name = Unicode(episode_name)

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

        self.watched = watched
        self.keep = keep


    def set_icon(self):
        """
        Set the image displayed next to the menu item text, based on whether
        the program is being kept or has been watched.
        """
        if self.keep and self.watched:
            self.icon = config.ICON_DIR + '/status/television_keep_watched.png'
        elif self.keep:
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
        if mode == SORTING_DATE_NAME:
            return u'%010.0f%s' % (self.timestamp, self.name)
        elif mode == SORTING_STATUS_NAME:
            return get_status_sort_order(self.watched, self.keep) + self.name
        elif mode == SORTING_STATUS_DATE_NAME:
            return get_status_sort_order(self.watched, self.keep) + self.sort(SORTING_DATE_NAME)

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
        self.playlist = None
        self.update(items)


    # ======================================================================
    # actions
    # ======================================================================

    def actions(self):
        """
        return the default action
        """
        return [
            (self.browse, _('Browse episodes')),
            (self.confirm_delete, _('Delete all episodes')),
            (self.mark_all_to_keep, _('Keep all episodes')),
            (self.play_all, _('Play all episodes'))
        ]


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
                # Update the icon just incase we were called because a series item updated its watched/keep state.
                self.set_icon()
        else:
            # normal menu build
            item_menu = Menu(self.name, self.items,reload_func=self.reload, item_types = 'tv')
            menuw.pushmenu(item_menu)

            self.menu  = item_menu
            self.menuw = menuw

        disk_manager.set_update_menu(self, self.menu, self.menuw)


    def play_all(self, arg=None, menuw=None):
        """
        Play all programs in a series.
        """
        self.playlist = Playlist(playlist=self.items)
        self.playlist.play(menuw=menuw)


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
            item.files.delete()
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
            menuw.refresh(reload=True)


    def update(self, items):
        """
        Update the list of programs that make up this series.
        """
        self.items = items
        for item in self.items:
            item.set_name_to_episode()

        self.items.sort(lambda l, o: cmp(o.sort(series_sorting), l.sort(series_sorting)))
        if series_sorting_reversed:
            self.items.reverse()

        self.set_icon()


    # ======================================================================
    # Helper methods
    # ======================================================================
    def reload(self):
        """
        Rebuilds the menu.
        """
        self.browse(arg='update')
        return None


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
        if keep and watched:
            self.icon = config.ICON_DIR + '/status/series_keep_watched.png'
        elif keep:
            self.icon = config.ICON_DIR + '/status/series_keep.png'
        elif watched:
            self.icon = config.ICON_DIR + '/status/series_watched.png'
        else:
            self.icon = config.ICON_DIR + '/status/series_unwatched.png'

        self.watched = watched
        self.keep = keep

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
        if mode == SORTING_DATE_NAME:
            latest_timestamp = 0.0
            for item in self.items:
                if item.timestamp > latest_timestamp:
                    latest_timestamp = item.timestamp
            return u'%10d%s' % (int(latest_timestamp), self.name)

        elif mode == SORTING_STATUS_NAME:
            return get_status_sort_order(self.watched, self.keep) + self.name
        elif mode == SORTING_STATUS_DATE_NAME:
            return get_status_sort_order(self.watched, self.keep) + self.sort(SORTING_DATE_NAME)

        return self.name

    def id(self):
        return 'series:' + self.name

    def eventhandler(self, event, menuw=None):
        """
        Handle playlist specific events
        """
        if self.playlist:
            return self.playlist.eventhandler(event, menuw)
        return False


# ======================================================================
# Disk Management Class
# ======================================================================

series_table = {}
segregated_recordings = []
all_recordings = []

class DiskManager(plugin.DaemonPlugin):
    """
    This plugin automatically removes recordings
    when disc space is getting low.

    It is automatically activated by the tv.recordings_manager plugin,
    and should not be used standalone.
    For more information read the details for tv.recordings_manager.

    freevo plugins -i tv.recordings_manager
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

    def set_update_menu(self, obj, menu, menuw):
        """
        Set the menu to update when the recordings directory changes.
        When an update is required, obj.browse(menuw=menuw,arg='update') will be called.
        menu is used to check that the menu is currently being displayed (ie its at the top of the stack).
        menuw is passed to obj.browse method.
        """
        self.menuw = menuw
        self.obj = obj
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
            # Only call update if the menu is on the top of the menu stack and we are in the menu's context
            if self.menu and (self.menuw.menustack[-1] == self.menu) and \
                self.menuw.event_context == rc.get_singleton().context:
                self.obj.browse(menuw=self.menuw, arg='update')


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
            candidates = self.generate_candidates()
            while (util.freespace(config.TV_RECORD_DIR) < self.required_space) and (len(candidates) > 0):
                # Delete a candidate
                candidate = candidates.pop(0)
                if (not candidate):
                    break
                candidate.delete()


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
    '''
    document me
    '''
    menu = menuw.menustack[-1]
    # rebuild menu
    try:
        idx = menu.choices.index(item)
        cloned_item = copy.copy(item)
        menu.choices[idx] = cloned_item
        if menu.selected is item:
            menu.selected = cloned_item
    except ValueError, e:
        menuw.delete_submenu(True, True)


def get_status_sort_order(watched, keep):
    '''
    document me
    '''
    orders = STATUS_ORDERS[status_order]

    order = orders[STATUS_ORDER_UNWATCHED]
    if keep and watched:
        order = orders[STATUS_ORDER_KEEP_WATCHED]
    elif keep:
        order = orders[STATUS_ORDER_KEEP]
    elif watched:
        order = orders[STATUS_ORDER_WATCHED]
    return order
