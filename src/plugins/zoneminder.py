#!/usr/bin/env python
# -----------------------------------------------------------------------
# Zoneminder plugin for Freevo
# Written by Christophe 'CSCMEU' Nowicki
# -----------------------------------------------------------------------
# -*- coding: utf-8 -*-
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('zondminder')
#
# -----------------------------------------------------------------------
# Zoneminder plugin for Freevo
# Copyright (C) 2008 Christophe Nowicki
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

__author__           = "Christophe 'CSCMEU' Nowicki"
__author_email__     = 'cscm@csquad.org'
__maintainer__       = __author__
__maintainer_email__ = __author_email__
__version__          = '0.1a'


# System
import os
import md5
import sys
import base64
import socket
import httplib
from string import strip
from time import localtime
from math import sqrt
from time import sleep
import urllib
import pygame
import MySQLdb
import threading
import ImageFile

# Freevo
import config
import plugin
import skin
import osd
from gui import PopupBox
from item import Item
from menu import Menu, MenuItem

osd = osd.get_singleton()
skin = skin.get_singleton()

montage_surface_lock = threading.Lock()
montage_surfaces = {}
montage_waiting = True
montage_waiting_lock = threading.Lock()
montage_flip_lock = threading.Lock()


class ZoneMinderCommon():
    def __init__(self, id):
        self.id = id
        self.conn = None
        self.stream_file = None
        self.stop_display = False

    def build_auth(self):
        auth = ''
        if config.ZONEMINDER_SERVER_AUTH_TYPE == 'builtin':
            if config.ZONEMINDER_SERVER_AUTH_RELAY == 'plain':
                auth = '&user=%s&pass=%s' % ( config.ZONEMINDER_SERVER_USERNAME, config.ZONEMINDER_SERVER_PASSWORD)
            if config.ZONEMINDER_SERVER_AUTH_RELAY == 'hashed':
                # $time = localtime();
                # $auth_key = ZM_AUTH_HASH_SECRET.$_SESSION['username'].$_SESSION['password_hash'].$_SESSION['remote_addr'].$time[2].$time[3].$time[4].$time[5];
                # $auth = md5( $auth_key );
                lt = localtime()
                auth_key = md5.new()
                auth_key.update(config.ZONEMINDER_SERVER_AUTH_HASH_SECRET)
                auth_key.update(config.ZONEMINDER_SERVER_USERNAME)
                auth_key.update(config.ZONEMINDER_SERVER_PASSWORD_HASH)
                if config.ZONEMINDER_CLIENT_IPV4_ADDRESS != '':
                    auth_key.update(config.ZONEMINDER_CLIENT_IPV4_ADDRESS)
                else:
                    my_ipv4_address = socket.gethostbyname(socket.gethostname())
                    if (my_ipv4_address == '127.0.0.1'):
                        log.warning("gethostbyname has return '127.0.0.1' as you ip address, streaming or events display should not work, please check you hosts file or use ZONEMINDER_CLIENT_IPV4_ADDRESS.")
                    auth_key.update(socket.gethostbyname(socket.gethostname())) # should return my ip

                auth_key.update("%d%d%d%d" % (lt[3], lt[2], lt[1] - 1, lt[0] - 1900))
                auth = '&auth=' + auth_key.hexdigest()
        return auth


    def start_stream(self):
        if config.ZONEMINDER_SERVER_USE_SSL == True:
            self.conn = httplib.HTTPSConnection(config.ZONEMINDER_SERVER_HOST,
                    port=int(config.ZONEMINDER_SERVER_PORT),
                    key_file=config.ZONEMINDER_SERVER_SSL_KEY,
                    cert_file=config.ZONEMINDER_SERVER_SSL_CERT,
            )
        else:
            self.conn = httplib.HTTPConnection(config.ZONEMINDER_SERVER_HOST,
                    port=int(config.ZONEMINDER_SERVER_PORT) )
        self.conn.connect()
        try:
            self.conn.putrequest('GET', self.build_request())
            self.conn.endheaders()
        except socket.error,e:
            self.stream_file = None
            PopupBox(text=_('Error: %s') % e[1]).show()
            return
        except httplib.HTTPException,e:
            self.stream_file = None
            PopupBox(text=_('Error: %s') % e.message).show()
            return
        response = self.conn.getresponse()
        if response.status != 200:
            self.stream_file = None
            PopupBox(text=_('HTTP Status %d:%s') % (response.status, response.reason ) ).show()
            return
        ct = response.getheader('content-type')
        boundary = ct[ct.find('=') + 1:]
        self.stream_file = response.fp

    def get_picture(self):
        if self.stream_file == None:
            return None

        image_parser = ImageFile.Parser()
        self.stream_file.readline() # skip boundary
        self.stream_file.readline() # Content-type
        p = self.stream_file.readline() # Content-Length
        try:
            cl = int(p[p.find(' ') + 1:-2])
        except ValueError:
            self.stream_file = None
            return None

        self.stream_file.readline() # Empty

        image_parser.feed(self.stream_file.read(cl))
        image = image_parser.close()
        surface = pygame.image.fromstring(
                image.tostring(),
                image.size,
                image.mode)
        self.stream_file.readline() # skip eol
        self.stream_file.readline() # skip eol
        return surface

    def display_montage(self, x, y, width, height, surface):
        global montage_waiting, montage_surfaces
        if self.stream_file == None:
            return
        while montage_waiting:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        try:
                            montage_waiting_lock.acquire()
                            montage_waiting = False
                        finally:
                            montage_waiting_lock.release()
                            return
            picture = self.get_picture()
            try:
                montage_surface_lock.acquire()
                if picture == None:
                    del(montage_surfaces[self.id])
                    return
                surface.screen.blit(pygame.transform.scale(picture, (width, height)), (x,y))
                montage_surfaces[self.id] = True
                if montage_surfaces.values().count(False) == 0:
                    pygame.display.flip()
                    for id in montage_surfaces.keys():
                        montage_surfaces[id] = False
            finally:
                montage_surface_lock.release()


    def display(self, surface = osd):
        if self.stream_file == None:
            return
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        waiting = False
            picture = self.get_picture()
            if picture == None:
                continue
            surface.screen.blit(
                    pygame.transform.scale(picture, surface.screen.get_size()),
                    (0,0))
            pygame.display.flip()
        skin.redraw()


class ZoneMinderEvent(ZoneMinderCommon):
    def build_request(self):
        # /cgi-bin/nph-zms?source=event&mode=jpeg&event=22105
        request = "/cgi-bin/nph-zms?source=event&mode=jpeg&event=%d" % self.id
        request += self.build_auth()
        return request


class ZoneMinderMonitor(ZoneMinderCommon):
    def build_request(self):
        # /cgi-bin/nph-zms?mode=jpeg&monitor=14&scale=100&maxfps=5
        request = "/cgi-bin/nph-zms?mode=jpeg&monitor=%d&scale=100&maxfps=5" % self.id
        request += self.build_auth()
        return request

class ZoneMinder():
    def __init__(self, filename):
        self.config = self.load_config_file(filename)
        self.db = self.connect_database()

    def hashPassword(self, password):
        sql = """SELECT PASSWORD('%s')""" % password
        c = self.db.cursor()
        c.execute(sql)
        r = c.fetchone()
        return r[0]

    def toDict(self, curs):
        """Convert a DBI result to a list of dictionaries."""
        cols = [column[0] for column in curs.description]
        return [dict(zip(cols, row)) for row in curs.fetchall()]

    def load_config_file(self, filename):
        config = {}
        f = open(filename, 'r')
        for l in f.readlines():
            l = l.rstrip()
            if len(l) == 0 or l[0] == '#':
                continue
            s = l.partition('=')
            config[s[0]] = s[2]
        return config

    def connect_database(self):
        db = MySQLdb.connect(
                host=self.config['ZM_DB_HOST'],
                user=self.config['ZM_DB_USER'],
                passwd=self.config['ZM_DB_PASS'],
                db=self.config['ZM_DB_NAME'])
        return db

    def list_monitor(self):
        sql = """SELECT id,name,width,height FROM Monitors WHERE Enabled=1 ORDER BY Name"""
        c = self.db.cursor()
        c.execute(sql)
        r = c.fetchall()
        names = []
        for m in r:
            names.append((m[0], m[1], m[2], m[3]))
        c.close()
        return names

    def list_events(self, where=None, orderby=None):
        sql = """SELECT E.Name AS Name,Cause,Length, StartTime, MonitorId, M.Name AS MonitorName, E.Id AS EventId, FrameId FROM Events AS E,Monitors AS M, (SELECT FrameId FROM Frames WHERE EventId=22105 AND Type='Alarm' ORDER BY FrameId LIMIT 1) AS F WHERE E.MonitorId=M.Id"""
        if where != None:
            sql += """ AND %s""" % where
        if orderby != None:
            sql += """ ORDER BY %s""" % orderby
        c = self.db.cursor()
        c.execute(sql)
        r = self.toDict(c)
        c.close()
        return r




class PluginInterface(plugin.MainMenuPlugin):
    """
    A Freevo plugin for ZoneMinder: Linux Home CCTV and Video Camera Security with Motion Detection

    To activate, put the following lines in local_conf.py

    | plugin.activate('zoneminder', level=45)
    | ZONEMINDER_CONFIG = '/etc/zm.conf'
    | ZONEMINDER_EVENTS_DIR = '/var/www/events'
    | ZONEMINDER_CLIENT_IPV4_ADDRESS = None
    | ZONEMINDER_SERVER_AUTH_TYPE = 'builtin'
    | ZONEMINDER_SERVER_USERNAME = 'admin'
    | ZONEMINDER_SERVER_PASSWORD = 'admin'
    | ZONEMINDER_SERVER_AUTH_RELAY = 'hashed'
    | ZONEMINDER_SERVER_AUTH_HASH_SECRET = ''
    | ZONEMINDER_SERVER_HOST = 'localhost'
    | ZONEMINDER_SERVER_PORT = '80'
    | ZONEMINDER_SERVER_USE_SSL = False
    | ZONEMINDER_SERVER_SSL_KEY = None
    | ZONEMINDER_SERVER_SSL_CERT = None
    """
    def __init__(self):
        """
        """
        _debug_('PluginInterface.__init__()', 2)
        if not config.USE_NETWORK:
            self.reason = 'USE_NETWORK not enabled'
            return

        if not config.ZONEMINDER_CONFIG:
            filename = '/etc/zm.conf'
        else:
            filename = config.ZONEMINDER_CONFIG

        if not os.path.isfile(filename):
            self.reason = 'the file \'%s\' is not readable' % filename
            return

        if config.ZONEMINDER_SERVER_USE_SSL == True:
            if config.ZONEMINDER_SERVER_SSL_KEY != None:
                if not os.path.isfile(config.ZONEMINDER_SERVER_SSL_KEY):
                    self.reason = 'the ssl key file \'%s\' is not readable' % config.ZONEMINDER_SERVER_SSL_KEY
                    return
            if config.ZONEMINDER_SERVER_SSL_CERT != None:
                if not os.path.isfile(config.ZONEMINDER_SERVER_SSL_CERT):
                    self.reason = 'the ssl certificate file \'%s\' is not readable' % config.ZONEMINDER_SERVER_SSL_CERT
                    return

        try:
            self.zm = ZoneMinder(config.ZONEMINDER_CONFIG)
        except MySQLdb.Error, e:
            self.reason = 'mysql error %d:%s' % (e.args[0], e.args[1])
            return

        plugin.MainMenuPlugin.__init__(self)

    def config(self):
        """
        """
        _debug_('config()', 2)
        return [
            ('ZONEMINDER_CONFIG', '/etc/zm.config', 'Location of the Zonminder configuration file'),
            ('ZONEMINDER_EVENTS_DIR', '/var/www/events', 'Location of the events'),
            ('ZONEMINDER_CLIENT_IPV4_ADDRESS', None, 'Your IPv4 Address (optional)'),
            ('ZONEMINDER_SERVER_AUTH_TYPE', 'builtin', 'What is used to authenticate ZoneMinder users (builtin, none) '),
            ('ZONEMINDER_SERVER_USERNAME', 'admin', 'Username'),
            ('ZONEMINDER_SERVER_PASSWORD', 'admin', 'Password'),
            ('ZONEMINDER_SERVER_PASSWORD_HASH', '', 'MySQL Hashed Password (optional)'),
            ('ZONEMINDER_SERVER_AUTH_RELAY', 'hashed', 'Method used to relay authentication information (hashed, plain, none)'),
            ('ZONEMINDER_SERVER_AUTH_HASH_SECRET', '', 'Secret for encoding hashed authentication information'),
            ('ZONEMINDER_SERVER_HOST', 'localhost', 'The host running the Zoneminder server'),
            ('ZONEMINDER_SERVER_PORT', '80', 'The port the server is listening on'),
            ('ZONEMINDER_SERVER_USE_SSL', False, 'Use secure socket layer'),
            ('ZONEMINDER_SERVER_SSL_KEY', None, 'SSL Key file'),
            ('ZONEMINDER_SERVER_SSL_CERT', None, 'SSL Certificate file')
        ]

    def items(self, parent):
        """
        """
        _debug_('items(self, parent)', 2)
        config.ZONEMINDER_SERVER_PASSWORD_HASH = self.zm.hashPassword(config.ZONEMINDER_SERVER_PASSWORD)
        return [ ZoneMinderMainMenu(parent, self.zm) ]

class ZoneMinderLiveStreamMenu(Item):
    def __init__(self, parent, Zm):
        Item.__init__(self, parent)
        self.zm = Zm
        self.name   = _('Stream')
        self.menus = [
                MenuItem(_('Montage'), self.montage)
        ]

        names = Zm.list_monitor()
        for (id, name, width, height) in names :
            self.menus.append(MenuItem(name.capitalize(), self.live, id))

    def actions(self):
        items = [ ( self.create_mainmenu , _('Stream') ) ]
        return items

    def create_mainmenu(self, arg=None, menuw=None):
        sane_menu = Menu(_('Stream'), self.menus)
        menuw.pushmenu(sane_menu)
        menuw.refresh()

    def live_montage(self, id, x, y, width, height):
        global montage_waiting, montage_surfaces
        montage_surfaces[id] = False
        montage_waiting  = True
        mon = ZoneMinderMonitor(id)
        mon.start_stream()
        mon.display_montage(x, y, width, height, osd)

    def montage(self, arg=None, menuw=None):
        skin.clear()
        monitors = self.zm.list_monitor()
        l = len(monitors)
        w = int(sqrt(l))
        if w != sqrt(l):
            w = w + 1
        mon_w = osd.width / w
        if ((w*w) - l) >= w :
            mon_h = osd.height / (w - 1)
        else:
            mon_h = osd.height / w
        x = 0
        y = 0
        threads = []
        for (id, name, width, height) in monitors:
            t = threading.Thread(target=self.live_montage, args=(id, x, y, mon_w, mon_h))
            t.start()
            threads.append(t)
            x += mon_w
            if (x + (osd.width % w)) == osd.width:
                y += mon_h
            x = (x %  osd.width)

        for t in threads:
            t.join()
        skin.redraw()

    def live(self, arg=None, menuw=None):
        skin.clear()
        mon = ZoneMinderMonitor(arg)
        mon.start_stream()
        mon.stop_display = False
        mon.display()

class ZoneMinderEventsMenu(Item):
    def __init__(self, parent, Zm):
        Item.__init__(self, parent)
        self.name   = _('Events')
        self.menus = [
                ZoneMinderEventsByMonitorMenu(parent, Zm),
                ZoneMinderEventsByTimeMenu(parent, Zm)
        ]

    def actions(self):
        items = [ ( self.create_mainmenu , _('Stream') ) ]
        return items

    def create_mainmenu(self, arg=None, menuw=None):
        sane_menu = Menu(_('Events'), self.menus)
        menuw.pushmenu(sane_menu)
        menuw.refresh()

class ZoneMinderEventsByTimeMenu(Item):
    def __init__(self, parent, Zm):
        Item.__init__(self, parent)
        self.name   = _('Events by time')
        self.Zm = Zm
        self.menus = [
                MenuItem(_('Last minute'), self.events, '1 MINUTE', skin_type='image'),
                MenuItem(_('Last 5 minutes'), self.events, '5 MINUTE', skin_type='image'),
                MenuItem(_('Last 15 minutes'), self.events, '15 MINUTE', skin_type='image'),
                MenuItem(_('Last 30 minutes'), self.events, '30 MINUTE', skin_type='image'),
                MenuItem(_('Last hour'), self.events, '1 HOUR', skin_type='image'),
                MenuItem(_('Last day'), self.events, '1 DAY', skin_type='image')
        ]

    def actions(self):
        items = [ ( self.create_mainmenu , _('Stream') ) ]
        return items

    def create_mainmenu(self, arg=None, menuw=None):
        sane_menu = Menu(_('Events by time'), self.menus)
        menuw.pushmenu(sane_menu)
        menuw.refresh()

    def events(self, arg=None, menuw=None):
        events = self.Zm.list_events(where = "DATE_SUB(CURDATE(),INTERVAL %s) <= StartTime" % arg)
        events_menu_items = []
        for e in events:
            item = MenuItem(e['Name'], self.event, e['EventId'], skin_type='image')
            image_path = '%s/%d/%d/%03d-%s' % (config.ZONEMINDER_EVENTS_DIR, e['MonitorId'], e['EventId'], e['FrameId'], 'analyse.jpg')
            description = 'Monitor: %s\nCause: %s\nTime: %s\nDuration: %s' %  (e['MonitorName'], e['Cause'], e['StartTime'], e['Length'])
            item.info = { 'description' : description }
            item.image = image_path
            events_menu_items.append(item)
        if menuw:
            menuw.refresh()

        events_menu = Menu(_('Events'), events_menu_items)
        menuw.pushmenu(events_menu)
        menuw.refresh()

    def event(self, arg=None, menuw=None):
        skin.clear()
        ev = ZoneMinderEvent(arg)
        ev.start_stream()
        ev.stop_display = False
        ev.display()

class ZoneMinderEventsByMonitorMenu(Item):
    def __init__(self, parent, Zm):
        Item.__init__(self, parent)
        self.name   = _('Events by monitor')
        self.Zm = Zm
        self.menus = [ ]

        names = Zm.list_monitor()
        for (id, name, width, height) in names :
            self.menus.append(MenuItem(name.capitalize(), self.events, id))

    def actions(self):
        items = [ ( self.create_mainmenu , _('Stream') ) ]
        return items

    def create_mainmenu(self, arg=None, menuw=None):
        sane_menu = Menu(_('Events by monitor'), self.menus)
        menuw.pushmenu(sane_menu)
        menuw.refresh()

    def events(self, arg=None, menuw=None):
        events = self.Zm.list_events(where = "MonitorId = %d" % arg, orderby = " EventId DESC")
        events_menu_items = []
        for e in events:
            item = MenuItem(e['Name'], self.event, e['EventId'], skin_type='image')
            image_path = '%s/%d/%d/%03d-%s' % (config.ZONEMINDER_EVENTS_DIR, e['MonitorId'], e['EventId'], e['FrameId'], 'analyse.jpg')
            description = 'Monitor: %s\nCause: %s\nTime: %s\nDuration: %s' %  (e['MonitorName'], e['Cause'], e['StartTime'], e['Length'])
            item.info = { 'description' : description }
            item.image = image_path
            events_menu_items.append(item)
        if menuw:
            menuw.refresh()

        events_menu = Menu(_('Events'), events_menu_items)
        menuw.pushmenu(events_menu)
        menuw.refresh()

    def event(self, arg=None, menuw=None):
        skin.clear()
        ev = ZoneMinderEvent(arg)
        ev.start_stream()
        ev.stop_display = False
        ev.display()


class ZoneMinderMainMenu(Item):
    def __init__(self, parent, Zm):
        Item.__init__(self, parent)
        self.name   = _('CCTV')
        self.menus = [
                ZoneMinderLiveStreamMenu(parent, Zm),
                ZoneMinderEventsMenu(parent, Zm)
        ]

    def actions(self):
        items = [ ( self.create_mainmenu , _('CCTV') ) ]
        return items

    def create_mainmenu(self, arg=None, menuw=None):
        sane_menu = Menu(_('CCTV'), self.menus)
        menuw.pushmenu(sane_menu)
        menuw.refresh()
