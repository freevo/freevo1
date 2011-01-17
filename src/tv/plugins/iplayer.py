# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Plug-in to browse and view content using get_iplayer
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
Plugin to browse and view content from BBC IPlayer/Listen again website using
the get_iplayer script.
See http://www.infradead.org/get_iplayer/html/get_iplayer.html for details of
get_iplayer.
"""
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

import copy
import os
import os.path
import re
import subprocess
import threading
import traceback
import time
import urllib
import tarfile
import stat

import config
import dialog.dialogs
import plugin
import rc
import skin

from item import Item
from menu import Menu, MenuItem, MenuWidget
from video import VideoItem
from skin.widgets import TextEntryScreen
import kaa

GIP_MAPPINGS = {
    'bbc tv': ('tv', _('BBC IPlayer')),
    'bbc radio': ('radio', _('BBC Radio listen again')),
    'bbc podcast': ('podcast', _('BBC Podcasts')),
    }

IPLAYER_WEB_PORT = 0
GET_IPLAYER = ''
version_last_checked = 0

class PluginInterface(plugin.MainMenuPlugin):
    """
    Plugin to browse and view content from BBC IPlayer/Listen again website using
    the get_iplayer script.
    See http://www.infradead.org/get_iplayer/html/get_iplayer.html for details
    of get_iplayer.

    Activate with:
    | plugin.activate('tv.iplayer',level=5)

    """

    def __init__(self):
        """
        normal plugin init, but sets _type to 'mainmenu_tv'
        """
        global IPLAYER_WEB_PORT
        plugin.MainMenuPlugin.__init__(self)
        self._type = 'mainmenu_tv'
        self.parent = None
        self.http_server = HTTPServer(('', 0), IPlayerRequestHandler)
        IPLAYER_WEB_PORT = self.http_server.server_address[1]

        self.stop = False
        thread = threading.Thread(target=self.serve_forever)
        thread.setDaemon(True)
        thread.start()
        


    def serve_forever(self):
        """
        Start HTTP server and wait for connections.
        """
        while not self.stop:
            try:
                self.http_server.handle_request()
            except:
                traceback.print_exc()
        
    def config(self):
        return  [('IPLAYER_TYPES', ['bbc tv'],
                        'A list of types of content to show for. Options are: bbc tv, bbc radio, bbc podcast'),
                 ('IPLAYER_DOWNLOAD_DIR', '.', 'Directory to store the downloads in.'),
                 ('IPLAYER_DOWNLOAD_MODE_VIDEO', '',
                    'Try to download content in the specified type order. (see get_iplayer --tvmode parameter for details)'),
                 ('IPLAYER_GET_IPLAYER', '',
                    'The get_iplayer application path. Set this to None (or not defined in your local_conf.py) to allow automatic downloading and update.'),
                 ('IPLAYER_RTMPDUMP_PATH', '/usr/local/bin/rtmpdump', 'Path to rtmpdump utility for downloading flash content')]

    def shutdown(self):
        self.stop = True
        self.http_server.socket.close()
        

    def items(self, parent):
        items = []
        for t in config.IPLAYER_TYPES:
            if t in GIP_MAPPINGS:
                items.append(IPlayerServiceItem(parent, t))

        items.append(IPlayerDownloadQueueItem(parent))

        return items


def update_get_iplayer():
    """
    Attempt to download/update get_iplayer.
    """
    global GET_IPLAYER, version_last_checked

    if config.IPLAYER_GET_IPLAYER or (time.time() - version_last_checked) < 360:
        # Don't attempt to update a manually configure downloader or
        # if we've already checked for an update in the last hour.
        return

    GET_IPLAYER = os.path.join(config.FREEVO_STATICDIR, 'get_iplayer')

    version_file_path = GET_IPLAYER + '.version'
    current_version = None
    try:
        f = open(version_file_path)
        current_version = f.read()
        f.close()
    except:
        pass

    version_url = 'http://www.infradead.org/get_iplayer/VERSION-get_iplayer'
    get_iplayer_base_url = 'ftp://ftp.infradead.org/pub/get_iplayer/'
    # Work out the latest version of get_iplayer
    latest_version = ''
    try:
        u = urllib.urlopen(version_url)
        latest_version = u.read().strip()
        u.close()
    except:
        return

    _debug_('get_iplayer: Current Version: %s Latest Version: %s' % (current_version, latest_version))

    if latest_version == current_version:
        # No need to update as we already have the latest version
        return

    try:
        if os.path.exists(GET_IPLAYER):
            # Use get_iplayer itself to update.
            os.system(GET_IPLAYER + ' -u')
        else:
            # We don't have a copy yet so do a manual download.
            manifest_url = 'http://www.infradead.org/get_iplayer/MANIFEST.v' + latest_version
            u = urllib.urlopen(manifest_url)
            download_url = ''
            for line in u:
                ftype, url = line.strip().split(' ', 2)
                if ftype == 'bin':
                    download_url = url
                    break
            u.close()
            if download_url:
                urllib.urlretrieve(download_url, GET_IPLAYER)
                os.chmod(GET_IPLAYER, stat.S_IRWXU)
                # Force the download of the plugins etc.
                if 'http_proxy' in os.environ:
                    proxy = ' -p ' + os.environ['http_proxy']
                else:
                    proxy = ''
                os.system(GET_IPLAYER + proxy)
            else:
                return

        # Update the version file
        f = open(version_file_path, 'w')
        f.write(latest_version)
        f.close()
    except:
        traceback.print_exc()
        return
    version_last_checked = time.time()


class IPlayerServiceItem(Item):
    """
    Class representing a download service.
    """
    def __init__(self, parent, gip_type):
        """
        Create a new instance of a download service
        @param parent: Parent item.
        @param gip_type: get_iplayer type.
        """
        Item.__init__(self, parent, skin_type='tv')
        self.gip_type = GIP_MAPPINGS[gip_type][0]
        self.name = GIP_MAPPINGS[gip_type][1]
        
    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name)]
        return items


    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        update_get_iplayer()

        items = [IPlayerProgramListItem(self, self.gip_type, _('Browse all'), 0, ''),
                 IPlayerListItem(self, self.gip_type,_('Browse by Channel'), 'channel'),
                 IPlayerListItem(self, self.gip_type,_('Browse by Category'), 'categories'),
                 MenuItem(_('Search'), self.search)
                 ]

        # normal menu build
        item_menu = Menu(self.name, items, item_types='tv')
        menuw.pushmenu(item_menu)

        self.menu  = item_menu
        self.menuw = menuw

    def search(self, arg=None, menuw=None):
        text_entry = TextEntryScreen((_('Search'), self.search_for_programs), self.name)
        text_entry.show(menuw)

    def search_for_programs(self, menuw, text):
        item = IPlayerProgramListItem(self, self.gip_type, _('Search results'), 0, text)
        item.browse(None, menuw)


RE_LIST = re.compile('^(.*) \(([0-9]+)\)$') # For Channels or Categories
RE_ITEM = re.compile('^([0-9]+)\|\|(.+?)\|\|(.+?)\|\|(.+?)\|\|(.+?)\|\|(.+)$')
ITEM_FORMAT = '<index>||<pid>||<name>||<episode>||<desc>||<thumbnail>'

LIST_TYPE_TO_FILTER = {
    'channel' : '--channel "^%s$"',
    'categories' : '--category "^%s$"'
    }
    
class IPlayerListItem(Item):
    """
    Class representing a list of categories/channels used to browse the available
    programs.
    """
    def __init__(self, parent, gip_type, name, list_type):
        """
        Create a new List instance.
        @param parent: Parent item.
        @param gip_type: get_iplayer type.
        @param name: Name of the list (displayed in the menu).
        @param list_type: List type as passed to get_iplayer to retrieve the list items.
        """
        Item.__init__(self, parent, skin_type='tv')
        self.gip_type = gip_type
        self.name = name
        self.list_type = list_type

    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name)]
        return items

    def __getiplayer_line_cb(self, items, line):
        """
        Callback from query_get_iplayer.
        @param items: The current list of program items.
        @param line: The line
        """
        mobj = RE_LIST.match(line)
        if mobj:
            name, count = mobj.groups()
            filter = LIST_TYPE_TO_FILTER[self.list_type]
            items.append(IPlayerProgramListItem(self, self.gip_type, _(name), int(count), filter % name))
            self.progress.update_progress(str(len(items)), 0.0)

    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        items = []
        self.progress = dialog.dialogs.ProgressDialog(_('Retrieving details...'), indeterminate=True)
        self.progress.show()
        query_get_iplayer('--list %s' % self.list_type, self.gip_type, self.__getiplayer_line_cb, items)
        self.progress.hide()

        # normal menu build
        item_menu = Menu(self.name, items, item_types='tv')
        menuw.pushmenu(item_menu)

        self.menu  = item_menu
        self.menuw = menuw

class IPlayerProgramListItem(Item):
    """
    Class representing a list of programs.
    """
    def __init__(self, parent, gip_type, name, prog_count, filter=''):
        """
        Create a new program list instance.
        @param parent: Parent item.
        @param gip_type: get_iplayer type.
        @param name: Name of the list (displayed in the menu).
        @param prog_count: Approximate number of programs in the list.
        @param filter: Filter passed to get_iplayer to retrieve the list.
        """
        Item.__init__(self, parent, skin_type='tv')
        self.gip_type = gip_type
        self.name = name
        self.prog_count = prog_count
        self.filter = filter
        

    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name)]
        return items

    def __getiplayer_line_cb(self, items, line):
        """
        Callback from query_get_iplayer.
        @param items: The current list of program items.
        @param line: The line
        """
        mobj = RE_ITEM.match(line)
        if mobj:
            if self.prog_count:
                self.progress.set_indeterminate(False)
            items.append(IPlayerProgramItem(self, self.gip_type, mobj.group(1),
                                            mobj.group(2), mobj.group(3), mobj.group(4),
                                            mobj.group(5),mobj.group(6)))
            items_len = len(items)
            if self.prog_count:
                self.progress.update_progress('%d/%d' % (items_len, self.prog_count), float(items_len) / float(self.prog_count))
            else:
                self.progress.update_progress('%d' % items_len, 0.0)


    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        items = []
        self.progress = dialog.dialogs.ProgressDialog(_('Retrieving details...'), self.prog_count and '0/%d' % self.prog_count or '', 0.0, True)
        self.progress.show()
        query_get_iplayer('%s --listformat "%s"' % (self.filter, ITEM_FORMAT), self.gip_type, self.__getiplayer_line_cb, items)
        self.progress.hide()

        menu_items = []
        series = {}
        for item in items:
            if item.name in series:
                series[item.name].append(item)
            else:
                series[item.name] = [item]

        for name in sorted(series.keys()):
            series_items = series[name]
            if len(series_items) > 1:
                menu_items.append(IPlayerSeriesItem(self, name, series_items))
            else:
                menu_items.append(series_items[0])
        # normal menu build
        item_menu = Menu(self.name, menu_items, item_types='video')
        menuw.pushmenu(item_menu)

        self.menu  = item_menu
        self.menuw = menuw
        self.items = items


class IPlayerSeriesItem(Item):
    """
    Class representing a list of programs with the same name.
    """
    def __init__(self, parent, name, items):
        """
        Create a new series object.
        @param parent: Parent item.
        @param name: Name of the series.
        @param items: Items that share the same name.
        """
        Item.__init__(self, parent, skin_type='tv')
        self.name = Unicode(name)
        self.items = items
        for item in items:
            item.name = item.info['tagline']
            item.parent = self
        self.info['description'] = _('%d Episodes') % len(items)
        
    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name),
                 (self.download, _('Download all'))]
        return items

    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        # normal menu build
        item_menu = Menu(self.name, self.items, item_types='video')
        menuw.pushmenu(item_menu)

        self.menu  = item_menu
        self.menuw = menuw

    def download(self, arg=None, menuw=None):
        """
        Confirm whether the user wants to download the entire series.
        """
        confirm_dialog = dialog.dialogs.ButtonDialog(((_('Yes'), self.start_download),
                                              (_('No'), None)),
                                              _('Do you want to download all episodes of %s?') %self.name)
        confirm_dialog.show()

    def start_download(self):
        """
        Start downloading all items in the series.
        """
        for item in self.items:
            item.start_download()
            
class IPlayerProgramItem(VideoItem):
    """
    Class representing an downloadable program.
    """
    def __init__(self, parent, gip_type, index, pid, name, episode, desc, thumbnail):
        """
        Create a new program instance.
        @param parent: Parent item.
        @param gip_type: get_iplayer type.
        @param index: get_iplayer index.
        @param pid: get_iplayter pid.
        @param name: Name of the program.
        @param epsiode: Name of the episode.
        @param desc: Description of the program.
        @param thumbnail: URL for the thumbnail.
        """
        VideoItem.__init__(self, 'http://127.0.0.1:%d/%s/%s/video.mov' % (IPLAYER_WEB_PORT, gip_type, pid), parent)
        self.gip_type = gip_type
        self.pid = pid
        self.index = index
        self.name = Unicode(name)
        self.info['title'] = self.name
        self.info['tagline'] = episode
        self.info['plot'] = desc
        self.image = thumbnail


    def actions(self):
        """
        return a list of actions for this item
        """
        dq = get_download_queue()
        if self.gip_type == 'itv':
            if  dq.is_downloading(self.gip_type, self.pid) or \
                    dq.is_queued(self.gip_type, self.pid):
                return [(self.cancel_download, _('Cancel Download')), (self.show_details, _('Full description'))]
            else:
                return [(self.download, _('Download')), (self.show_details, _('Full description'))]

        actions =  VideoItem.actions(self)
        if  dq.is_downloading(self.gip_type, self.pid) or \
                dq.is_queued(self.gip_type, self.pid):
            actions.append((self.cancel_download, _('Cancel Download')))
        else:
            actions.append((self.download, _('Download')))

        return actions

    def download(self, arg=None, menuw=None):
        """
        Confirm whether the user wants to download the program.
        """
        confirm_dialog = dialog.dialogs.ButtonDialog(((_('Yes'), self.start_download),
                                              (_('No'), None)),
                                              _('Do you want to download %s - %s?') %(self.name, self.info['tagline']))
        confirm_dialog.show()

    def cancel_download(self, arg=None, menuw=None):
        """
        Confirm whether the user wants to cancel downloading of the program.
        """
        confirm_dialog = dialog.dialogs.ButtonDialog(((_('Yes'), self.stop_download),
                                              (_('No'), None)),
                                              _('Do you want to cancel downloading of %s - %s?') % (self.name, self.info['tagline']))
        confirm_dialog.show()

    def start_download(self):
        """
        Queue the program for download.
        """
        dq = get_download_queue()
        dq.add(self.gip_type, self.pid, self.info['title'], self.info['tagline'])
        status_dialog = dialog.dialogs.MessageDialog(_('Queued %s - %s for download') % (self.info['title'], self.info['tagline']))
        status_dialog.name = 'status'
        status_dialog.show()

    def stop_download(self):
        """
        Remove the program from the download queue.
        """
        dq = get_download_queue()
        dq.remove(self.gip_type, self.pid)
    
    def show_details(self, arg=None, menuw=None):
        query_get_iplayer('-i %s' % self.index, self.gip_type, self.__getiplayer_line_cb, None)
        VideoItem.show_details(self, arg, menuw)

    
    def __getiplayer_line_cb(self, details, line):
        if line.startswith('desc:'):
            self.info['plot'] = line[5:].strip()
        if line.startswith('duration:'):
            self.info['length'] = int(line[9:])


    def id(self):
        return self.gip_type+self.pid

class IPlayerDownloadQueueItem(Item):
    """
    Class representing the Download Queue as a menu item.
    """
    def __init__(self, parent):
        Item.__init__(self, parent)
        self.name = _('Downloads Queue')

    # ======================================================================
    # actions
    # ======================================================================
    def actions(self):
        """
        return a list of actions for this item
        """
        items = [(self.browse, self.name),
                 (self.clear_history, _('Clear history'))]
        return items

    def browse(self, arg=None, menuw=None):
        """
        build the items for the menu
        """
        # normal menu build
        items = []
        dq = get_download_queue()

        if dq.current_download:
            if dq.cancel_download and dq.current_download[0] == dq.cancel_download[0] and \
                dq.current_download[1] == dq.cancel_download[1]:
                status = _('Cancelling')
            else:
                status = _('Downloading')
            item = MenuItem((u'%s - %s' % dq.current_download[2:]) + u'\t' + status,
                            action=self.cancel_download, arg=dq.current_download)
            items.append(item)

        for download in dq.queue:
            item = MenuItem((u'%s - %s' % download[2:]) + u'\t' + _('Queued'),
                                action=self.cancel_download, arg=download)
            items.append(item)

        for download in dq.history:
            if download[4] == 'success':
                status = _('Success')
            elif download[4] == 'failed':
                status = _('Failed')
            elif download[4] == 'cancelled':
                status = _('Cancelled')
            else:
                status = _('Unknown')

            item = MenuItem((u'%s - %s' % download[2:4]) + u'\t' + status)
            items.append(item)
        
        if arg == 'update':
            selected = self.menu.selected.arg

            self.menu.choices = items
            self.menu.selected = None

            for item in items:
                if item.arg == selected:
                    self.menu.selected = item
                    break
                    
            self.menuw.init_page()
            self.menuw.refresh()

        else:
            item_menu = Menu(self.name, items, reload_func=self.reload, item_types='default no image')
            item_menu.table = (70, 30)
            menuw.pushmenu(item_menu)

            self.menu  = item_menu
            self.menuw = menuw
            dq.set_finished_callback(self.__download_finished)

    def clear_history(self, arg=None, menuw=None):
        dq = get_download_queue()
        dq.clear_history()
        
    def cancel_download(self, arg=None, menuw=None):
        if arg:
            self.download = arg
            confirm_dialog = dialog.dialogs.ButtonDialog(((_('Yes'), self.stop_download),
                                              (_('No'), None)),
                                              _('Do you want to cancel downloading of %s - %s?') % arg[2:])
            confirm_dialog.show()

    def stop_download(self):
        dq = get_download_queue()
        dq.remove(self.download[0], self.download[1])
        self.menuw.refresh(True)
        
    # ======================================================================
    # Helper methods
    # ======================================================================

    def reload(self):
        """
        Rebuilds the menu.
        """
        self.browse(arg='update')
        return None

    def __download_finished(self, download, status):
        import event
        if self.menuw.menustack[-1] == self.menu:
            event.MENU_RELOAD.post()
        else:
            dq = get_download_queue()
            dq.set_finished_callback(None)

#-------------------------------------------------------------------------------
# HTTP Server
#-------------------------------------------------------------------------------
class IPlayerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        elements = self.path[1:].split('/')
        if len(elements) < 2:
            self.send_error(404, 'Unknown request')
            return
        
        gip_type = elements[0]
        pid = elements[1]
        
        cmd = (config.CONF.get_iplayer,
                '--pid', pid,
                '--type', gip_type,
                '--file-prefix', 'tmp_stream',
                '-x', '-n',
                '-o', config.IPLAYER_DOWNLOAD_DIR,               
                '--force-download')
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process:
            thread = threading.Thread(target=self.output, args=(process.stderr,))
            thread.setName('IPlayer-stderr')
            thread.start()
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            more_data = True
            try:
                while more_data:
                    data = process.stdout.read(2048)
                    if data:
                        self.wfile.write(data)
                    else:
                        more_data = False
            except:
                os.kill(process.pid, 15)
        else:
            self.send_error(500, 'Failed to start get_iplayer')

    def log_message(self, format, *args):
        _debug_(format % args, 2)

    def output(self, out):
        buf = 'a'
        line = ''
        while buf:
            buf = out.read(1)
            if buf =='\n' or buf == '\r':
                print 'DOWNLOAD: %r' % line
                line = ''
            else:
                line += buf

#-------------------------------------------------------------------------------
# Download Queue
#-------------------------------------------------------------------------------
class DownloadQueue:
    def __init__(self):
        self.current_download = None
        self.cancel_download = None
        self.event = threading.Event()
        self.queue = []
        self.history = []
        self.paused = False
        self.thread = threading.Thread(target=self.run_download)
        self.thread.setDaemon(True)
        self.thread.setName('IPlayer-DwnldQ')
        self.thread.start()
        self.finished_callback = None

    def set_finished_callback(self, callback):
        self.finished_callback = callback

    def add(self, type, pid, name, episode):
        _debug_('Adding %s - %s (type %s pid %s) to the queue.' % (name, episode, type, pid))
        self.queue.append((type, pid, name, episode))
        if len(self.queue) == 1:
            self.event.set()

    def remove(self, type, pid):
        if self.current_download and \
            self.current_download[0] == type and \
            self.current_download[1] == pid:
            _debug_('Cancelling current download (type %s pid %s)' % (type, pid))
            self.cancel_download = (type, pid)
            return
        else:
            for download in self.queue:
                if download[0] == type and download[1] == pid:
                    _debug_('Removing download (type %s pid %s)' % (type, pid))
                    self.queue.remove(download)
                    return
        _debug_('Failed to remove download not in queue (type %s pid %s)' % (type, pid))

    def is_downloading(self, type, pid):
        if self.current_download and \
            self.current_download[0] == type and \
            self.current_download[1] == pid:
            return True
        return False

    def is_queued(self, type, pid):
        for download in self.queue:
            if download[0] == type and download[1] == pid:
                return True
        return False

    def downloads_pending(self):
        return self.current_download or self.queue

    def pause(self):
        _debug_('Pausing downloads')
        self.paused = True

    def resume(self):
        _debug_('Resuming downloads')
        self.paused = False
        self.event.set()

    def clear_history(self):
        self.history = []

    def run_download(self):
        while True:
            if len(self.queue) == 0:
                self.event.wait()
                self.event.clear()
    
            while self.paused:
                _debug_('Downloads paused')
                self.event.wait()
                self.event.clear()
    
            if len(self.queue) > 0:
                self.current_download = self.queue.pop()
                _debug_('Starting download %s - %s (type %s pid %s)' % (self.current_download[2:] + self.current_download[:2]))
                status = self.download()
                _debug_('Download status: %s' % status)
                download = self.current_download
                self.current_download = None
                self.history.append(download + (status,))
                if self.finished_callback:
                    self.finished_callback(download, status)

    def download(self):
        basename = get_item_basename(*self.current_download[1:])
        fxd_file = basename + '.fxd'
        fxd_file = fxd_file.replace('/', '_')
        cmd = [config.CONF.get_iplayer,
                '--type', self.current_download[0],
                '--pid', self.current_download[1],
                '-o', config.IPLAYER_DOWNLOAD_DIR,
                '--file-prefix', basename,
                '--fxd', fxd_file]

        if config.IPLAYER_DOWNLOAD_MODE_VIDEO:
            cmd += ['--tvmode', config.IPLAYER_DOWNLOAD_MODE_VIDEO]
        if config.IPLAYER_RTMPDUMP_PATH:
            cmd += ['--flvstreamer', config.IPLAYER_RTMPDUMP_PATH]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE, preexec_fn=self.setupprocess)


        if process:
            self.status = ''
            thread = threading.Thread(target=self.parse_output, args=(process.stdout,))
            thread.setName('IPlayer-DwnldSO')
            thread.start()
            while process.poll() is None:
                time.sleep(0.5)
                if self.cancel_download and \
                     self.cancel_download[0] == self.current_download[0] and \
                     self.cancel_download[1] == self.current_download[1]:
                    os.killpg(process.pid, 15)
                    self.status = 'cancelled'
            if not self.status:
                self.status = 'success'

        else:
            self.status = 'process failed'

        return self.status

    def setupprocess(self):
        print 'Setting pgrp'
        os.setpgrp()
        print 'Done'

    def parse_output(self, out):
        line = ''
        buf = 'a'
        while buf:
            buf = out.read(1)
            if buf in ('\n','\r'):

                _debug_('%r' % line, 2)
                if line == 'INFO: skipping this programme':
                    self.status = 'failed'
                    _debug_('Download FAILED')
                if line == 'ERROR: aborting get_iplayer':
                    self.status = 'failed'
                    _debug_('Download FAILED')
                print 'DOWNLOAD: %r' % line
                line = ''
            else:
                line += buf

download_queue = None

def get_download_queue():
    global download_queue
    if download_queue is None:
        download_queue = DownloadQueue()
    return download_queue

#-------------------------------------------------------------------------------
# Helper functions
#-------------------------------------------------------------------------------
gpl_line_count = 0

def query_get_iplayer(cmd, gip_type, line_cb, arg):
    global gpl_line_count
    update_get_iplayer()
    gpl_line_count = 0
    
    def line_callback(line):
        global gpl_line_count
        #print gpl_line_count,line
        if gpl_line_count < 5:
            gpl_line_count += 1
        else:
            line_cb(arg, line[:-1])

    process = kaa.Process('%s %s --type %s' % (GET_IPLAYER, cmd, gip_type))
    process.signals['readline'].connect(line_callback)
    ip = process.start()
    process.stdin.write('n\n')
    ip.wait()
    return process.exitcode

def get_item_basename(pid, name, episode):
    item_basename = '%s - %s-%s' % (name, episode, pid)
    item_basename = item_basename.replace('\\', '_')
    item_basename = item_basename.replace('/', '_')
    item_basename = item_basename.replace("'", '')
    item_basename = item_basename.replace(":", '')
    item_basename = item_basename.replace(' ', '_')
    return item_basename

