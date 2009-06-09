# -*- coding: utf-8 -*-
import os
import xmlrpclib

import config
import plugin

from item import Item
import menu, rc, skin, osd, util
import event as em
import directory
from gui.GUIObject import *
from gui.PopupBox import *
from gui.Button import *
from skin.widgets import ScrollableTextScreen

class ChangeState(PopupBox):
    """
    """
    globalHash = ''
    def __init__(self, text, Thash, handler=None, handler_message=None, default_choice=0,
                 x=None, y=None, width=0, height=0, icon=None, vertical_expansion=1,
                 text_prop=None, parent='osd'):

        PopupBox.__init__(self, text, handler, x, y, width, height, icon, vertical_expansion, text_prop, parent)
        self.globalHash = Thash
        self.handler_message = handler_message

        # XXX: It may be nice if we could choose between
        #      OK/CANCEL and YES/NO
        s = xmlrpclib.ServerProxy(config.RPCHOST)
        if (s.d.is_active(self.globalHash) == 1) ^ (s.d.is_hash_checking(self.globalHash) == 1):
            self.b0 = Button(_('Stop'), width=(self.width-60)/2)
        else:
            self.b0 = Button(_('Start'), width=(self.width-60)/2)
        self.b0.set_h_align(Align.NONE)
        self.add_child(self.b0)

        self.b1 = Button(_('Erase'), width=(self.width-60)/2)
        self.b1.set_h_align(Align.NONE)
        self.add_child(self.b1)

        self.b2 = Button(_('Cancel'), width=(self.width-60)/2)
        self.b2.set_h_align(Align.NONE)
        self.add_child(self.b2)

        select = 'self.b%s.toggle_selected()' % default_choice
        eval(select)


    def send_enter_event(self):
        self.eventhandler(INPUT_ENTER)


    def eventhandler(self, event):
        if event in (INPUT_LEFT, INPUT_UP):
            if self.b0.selected:
                self.b0.toggle_selected()
                self.b2.toggle_selected()
            elif self.b1.selected:
                self.b1.toggle_selected()
                self.b0.toggle_selected()
            else:
                self.b1.toggle_selected()
                self.b2.toggle_selected()
            self.draw()
            return

        elif event in (INPUT_RIGHT, INPUT_DOWN):
            if self.b0.selected:
                self.b1.toggle_selected()
                self.b0.toggle_selected()
            elif self.b1.selected:
                self.b1.toggle_selected()
                self.b2.toggle_selected()
            else:
                self.b0.toggle_selected()
                self.b2.toggle_selected()
            self.draw()
            return

        elif event == INPUT_EXIT:
            self.destroy()

        elif event == INPUT_ENTER:
            if self.b0.selected:
                s = xmlrpclib.ServerProxy(config.RPCHOST)
                if (s.d.is_active(self.globalHash) == 1) ^ (s.d.is_hash_checking(self.globalHash) == 1):
                    s.d.stop(self.globalHash)
                else:
                    s.d.start(self.globalHash)
                rc.post_event(em.MENU_BACK_ONE_MENU)
                self.destroy()

            elif self.b1.selected:
                s = xmlrpclib.ServerProxy(config.RPCHOST)
                s.d.erase(self.globalHash)
                self.destroy()
                rc.post_event(em.MENU_BACK_ONE_MENU)

            else:
                self.destroy()

        else:
            return self.parent.eventhandler(event)



class TorrentBrowser(Item):
    """
    Show a list of all the torrents
    """
    def __init__(self, parent, dir):
        self.torrentdir = dir
        Item.__init__(self, parent, skin_type='torrents')
        self.name = _('Torrent browser')


    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ (self.create_torrents_menu , 'torrents') ]
        return items


    def start_torrent(self, arg=None, menuw=None):
        fullpath = self.torrentdir + "/" + arg.filename
        s = xmlrpclib.ServerProxy(config.RPCHOST)
        s.load_start(fullpath)
        rc.post_event(em.MENU_GOTO_MAINMENU)


    def create_torrents_menu(self, arg=None, menuw=None):
        """
        create a list with torrents
        """
        torrents = []
        for filename in os.listdir(self.torrentdir):
            if filename[0] == '.':
                continue
            if os.path.isdir(self.torrentdir + "/" + filename):
                browser = TorrentBrowser(self, self.torrentdir + "/" + filename)
                browser.name = '['+ filename + ']'
                torrents.append(browser)
            elif os.path.splitext(filename)[1]==".torrent":
                title = filename
                mi = menu.MenuItem('%s' % title, self.start_torrent, 0)
                mi.filename = filename
                mi.arg = mi
                torrents.append(mi)
            else:
                continue

        torrents.sort(lambda l, o: cmp(l.name.upper(), o.name.upper()))
        torrent_menu = menu.Menu("Torrents", torrents)
        menuw.pushmenu(torrent_menu)
        menuw.refresh()



class PluginInterface(plugin.MainMenuPlugin):
    """
    rTorrent interface

    Define RPCHOST and TORRENTDIR in local_conf.py. Default would be http://localhost
    Configure rtorrent as in
    http://libtorrent.rakshasa.no/wiki/RTorrentXMLRPCGuide

    Add plugin with
    plugin.activate("reminders", level=45)
    RPCHOST = 'http://localhost:5000'
    TORRENTDIR = '/home/user/'
    """

    __author__           = 'Jesper Smith'
    __author_email__     = 'jakster@gmx.net'
    __maintainer__       = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'

    def __init__(self):
        if not hasattr(config, 'RPCHOST'):
            self.reason = 'RPCHOST not defined'
            return
        plugin.MainMenuPlugin.__init__(self)


    def items(self, parent):
        return [ TorrentMainMenu(parent) ]


class TorrentMainMenu(Item):
    """
    this is the item for the main menu.
    """
    def __init__(self, parent):
        Item.__init__(self, parent, skin_type='torrent')
        self.name = _('Torrents')


    def actions(self):
        """
        return a list of actions for this item
        """
        items = [ ( self.create_torrents_items_menu , _('Torrents' )) ]
        return items


    def show_details(self, arg=None, menuw=None):
        what = _('What do you want to do with this torrent?')
        ChangeState(text=what, Thash=arg.hash).show()


    def add_torrent(self, arg=None, menuw=None):
        return


    def create_torrents_items_menu(self, arg=None, menuw=None):
        torrents = []
        s = xmlrpclib.ServerProxy(config.RPCHOST)
        for d in s.d.multicall('main', 'd.get_hash=', 'd.get_name=', 'd.get_size_chunks=', 'd.get_chunk_size=',
            'd.get_completed_chunks=', 'd.get_bytes_done=', 'd.is_active=', 'd.is_hash_checking=', 'd.get_up_rate=',
            'd.get_down_rate=', 'd.get_up_total=', 'd.get_ratio=', 'd.get_peers_accounted=', 'd.get_peers_complete='):
            # Use chunks for total because get_completed_bytes didn't work correctly on my system
            completed = int(round((float(d[4])/float(d[2]))*100));
            up = round(d[10]/1048576.0, 1)
            down = round((d[5])/(1048576.0), 1)
            set = Button(_('Settings'))
            total = round((d[2]*d[3])/(1048576.0), 1)
            # Get the status
            if d[7] == 1:
                status = "Checking hash"
            elif d[6] == 1:
                status = "Active"
            else:
                status = "Stopped"
            # Create title and description
            title = status+": " + d[1] + ' (' + str(completed) + "%)"
            drate = round(d[9]/1000.0, 1)
            urate = round(d[8]/1000.0, 1)
            desc = "\nDownloaded/Total size: " + str(down) + "MiB/" + str(total) + "MiB\nUploaded (Ratio): " + str(up) \
                + "MiB (" +  str(d[11]/1000.0) + ")\nDown/Up (Leechers/Seeders): " + str(drate) \
                + "KiB/s / " + str(urate)  + " KiB/s (" + str(d[12]) + "/" + str(d[13]) + ")"
            mi = menu.MenuItem('%s' % title, self.show_details, 0)
            mi.hash = d[0]
            mi.arg = mi
            mi.description = desc
            torrents.append(mi)

        mi = menu.MenuItem(' ', None, 0)
        torrents.append(mi)
        self.display_type = None
        browser = TorrentBrowser(self, config.TORRENTDIR)
        browser.name = '[' + _('Add a new torrent') + ']'
        torrents.append(browser)
        torrents_menu = menu.Menu(_('Torrents'), torrents)
        menuw.pushmenu(torrents_menu)

        menuw.refresh()
