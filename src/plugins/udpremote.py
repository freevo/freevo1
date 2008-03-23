# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Interact with freevo over a udp connection
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#    To activate, put the following line in local_conf.py:
#       plugin.activate('udpremote')
#    You also have to add
#    UDPREMOTE_CLIENTS and UDPREMOTE_PORTS, too
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

from menu import MenuItem
import copy
import time
import plugin
from event import *
import config
import util
from util.tv_util import get_chan_displayname
from socket import socket,  AF_INET, SOCK_DGRAM

class PluginInterface( plugin.DaemonPlugin ):
    """
    Controls Freevo over a UDP Connection

    This is already done by the built-in functionality in rc.py, but
    this doesn't come with a connection back to the remote.

    With UDPRemote you can use any other computer who can create
    a udp connection to control freevo.

    In my case, I use a HP HX4700 to control my Freevo box.

    Now enjoy and have fun!
    """
    __author__           = 'Andreas Fuertig'
    __author_email__  = 'mail@andieh.de'
    __homepage__     = 'http://infolexikon.de'
    __maintainer__     = __author__
    __maintainer_email__ = __author_email__
    __version__          = '$Revision$'

    def __init__( self ):
        """
        init the remote
        """
        self.clients = []
        self.disable = 0
        self.playitem = None

        plugin.DaemonPlugin.__init__( self )
        # start the network connection
        # read address and port of the remote from the config file
        try:
            clients = config.UDPREMOTE_CLIENTS.split(" ")
            ports = config.UDPREMOTE_PORTS.split(" ")
            if len(clients) == len(ports):
                for client in clients:
                    self.clients.append((client, int(ports.pop())))
        except:
            print "can't get Host or Port from config file. Please set UDPREMOTE_CLIENTS and UDPREMOTE_PORTS!"
            self.disable = 1

        if not self.disable:
            self.create_network_connection()

        if not self.disable:
            plugin.register( self, "udpremote" )


    def config(self):
        return [ ('UDPREMOTE_CLIENTS', "192.168.0.10", 'IP Addresses strings are send to. You can define more than one IP, separated by spaces'),
                 ('UDPREMOTE_PORTS', '5555', 'PORT strings are send to. If you define more than one client IP, please define exactly the same number of ports here')
               ]


    def send(self, data):
        for client in self.clients:
            self.sock.sendto(data, client)


    def create_network_connection(self):
        """
        Creates network socket
        """
        try:
            self.sock = socket(AF_INET, SOCK_DGRAM)
        except:
            print "can't create network socket!"
            self.disable = 1
            return 0
        return 1


    def close(self):
        """
        to be called before the plug-in exists.
        It terminates the connection with the server
        """
        print "closing"
        self.sock.close()


    def draw( self, ( type, object ), osd ):
        """
        Prepare String to be send over socket.
        """
        if self.disable: return

        if plugin.getbyname('audio.detachbar'):
            if type == 'player' and plugin.getbyname('audio.detachbar').status != 0:
                return

        write = ""
        if type == "menu":
            # we definitely play no media...
            self.playitem = ""

            menu = object.menustack[ -1 ]
            spacer = "  "
            write = menu.heading + "\n"
            for a in range(len(object.menustack)):
                if a == len(object.menustack)-1:
                    now =object.menustack[a].selected.name
                    # show max 7 entries
                    count = len(object.menustack[a].choices)
                    index = 0
                    for tmp in object.menustack[a].choices:
                        if tmp.name == now:
                            break
                        index = index + 1
                    if count > 7:
                        if (index - 3) < 0:
                            start = 0
                            end = 7
                        elif (index + 3) >= count:
                            start = count - 7
                            end = count
                        else:
                            start = index - 3
                            end = index + 4
                    else:
                        start = 0
                        end = count

                    # display entries
                    for b in range(start, end):
                        cur_name = object.menustack[a].choices[b].name
                        if cur_name == now:
                            write += spacer + "->" + cur_name + "\n"
                        else:
                            write += spacer + cur_name + "\n"

        elif type == 'player':
            player = object

            if player != None:
                if player.type == "audio":
                    title  = player.getattr( 'title' )
                    if not title:
                        title = String(player.getattr( 'name' ))
                    write = "playing audio file:\n"
                    write += "Artist: %s\n" % (player.getattr( 'artist' ))
                    write += "Title: %s\n" % ( title )
                    write += "Length: %s" % (player.getattr( 'length' ))

                elif player.type == 'video':
                    write = "playing %s file:\n" % (player.getattr( 'type' ))
                    write += "%s\n" % (player.getattr( 'name'))
                    write += "Length: %s" % (player.getattr( 'length' ))
#                    length = player.getattr( 'length' )
#                    elapsed = player.elapsed
#                    if elapsed / 3600:
#                        elapsed ='%d:%02d:%02d' % ( elapsed / 3600, ( elapsed % 3600 ) / 60,
#                                                    elapsed % 60)
#                    else:
#                        elapsed = '%d:%02d' % ( elapsed / 60, elapsed % 60)
#                    try:
#                        percentage = float( player.elapsed / player.length )
#                    except:
#                        percentage = None

        if write:
            #print write
            self.send(write)


    def poll(self):
        if self.playitem:
            self.draw( ( 'player', self.playitem ), None )


    def eventhandler( self, event, menuw=None ):
        if event == PLAY_START:
            self.playitem = event.arg
            self.draw( ( 'player', self.playitem ), None )

        elif event == PLAY_END or event == STOP:
            self.playitem = None

        return 0
