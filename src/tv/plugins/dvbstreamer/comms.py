# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# comms.py - the Freevo DVBStreamer module for tv
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
# Todo:        
#
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
from socket import *

PRIMARY_SERVICE_FILTER='<Primary>'

class Controller:
    def __init__(self, host, adapter, username=None, password=None):
        self.host = host
        self.adapter = adapter
        self.username = username
        self.password = password
    
    def execute_command(self, command, authenticate=False):
        """
        Send a command to the dvbstreamer instance to execute,
        first authorising if required.
        """
        ctrlcon = ControlConnection(self.host, self.adapter)
        ctrlcon.open()
        if authenticate:
            (ec, em, lines) = ctrlcon.send_command('auth %s %s' % (self.username, self.password))
            if ec != 0:
                raise RuntimeError, 'failed to authenticate'
        result = ctrlcon.send_command(command)
        ctrlcon.close()
        return result
    
    def select_service(self, service):
        """
        Select the primary service.
        """
        (errcode, errmsg, msg) = self.execute_command('select ' + service, True)
        if errcode != 0:
            raise RuntimeError, errmsg
        
    def set_servicefilter_mrl(self, service_filter, mrl):
        """
        Set the MRL (Media Resource Locator) for a given service filter.
        """
        (errcode, errmsg, msg) = self.execute_command('setsfmrl %s %s' % (service_filter, mrl), True)
        if errcode != 0:
            raise RuntimeError, errmsg

    def get_services(self, mux=''):
        """
        Get the list of services available on all or a specific multiplex.
        """
        (errcode, errmsg, services) = self.execute_command('lsservices %s' % mux)
        if errcode != 0:
            return None
        return services

    def get_multiplexes(self):
        """
        Get the list of known multiplexes.
        """
        (errcode, errmsg, muxes) = self.execute_command('lsmuxes')
        if errcode != 0:
            return None
        return muxes
    
    def get_stats(self):
        """
        Get statistics on the number of packets processed by different parts of 
        the dvbstreamer instance.
        """
        (errcode, errmsg, raw_stats) = self.execute_command('stats')
        if errcode != 0:
            return None
        
        index = 2
        processors=[]
        while raw_stats[index] != '':
            parts = raw_stats[index].split(':')
            name = parts[0].strip()
            packets = int(parts[1])
            processors.append((name, packets))
            index += 1
        
        index += 3
        
        service_filters=[]
        while raw_stats[index] != '':
            parts = raw_stats[index].split(':')
            name = parts[0].strip()
            packets = int(parts[1])
            service_filters.append((name, packets))
            index += 1
        
        index += 3
        manual_outputs=[]
        while raw_stats[index] != '':
            parts = raw_stats[index].split(':')
            name = parts[0].strip()
            packets = int(parts[1])
            manual_outputs.append((name, packets))
            index += 1

        index += 1
        parts = raw_stats[index].split(':')
        total_packets= int(parts[1])
        
        index += 1
        parts = raw_stats[index].split(':')
        
        mbps = float(parts[1][:-3])
            
        return (processors, service_filters, manual_outputs, total_packets, mbps)
    
    def get_frontend_status(self):
        """
        Get the frontend status of the set dvbstreamer instance.
        """
        (errcode, errmsg, status) = self.execute_command('festatus')
        if errcode != 0:
            return None

        locked = status[0].find('Lock,') != -1
        
        line = status[1]
        equalsindex = line.find('= ') + 2
        spaceindex = line.find(' ', equalsindex)
        ber = int(line[equalsindex:spaceindex])
        
        equalsindex = line.find('= ',spaceindex) + 2
        spaceindex = line.find(' ', equalsindex)
        signal = int(line[equalsindex:spaceindex])
        
        equalsindex = line.find('= ',spaceindex) + 2
        snr = int(line[equalsindex:])
        
        return (locked, ber, signal, snr)
       
class ControlConnection:
    def __init__(self, host, adapter):
        self.host = host
        self.adapter = adapter
        self.opened = False
        
    def open(self):
        if self.opened:
            return
        self.socket = socket(AF_INET,SOCK_STREAM)
        self.socket.connect((self.host, self.adapter + 54197))
        self.socket_file = self.socket.makefile('r+')
        self.opened = True
        (error_code, error_message, lines) = self.read_response()
        
        if error_code != 0:
            self.socket.close()
            self.opened = False
        else:
            self.welcome_message = error_message

        return self.opened

    def close(self):
        if self.opened:
            self.socket_file.close()
            self.socket.close()
            self.opened = False
    
    def send_command(self, command):
        if not self.opened:
            raise RuntimeError, 'not connected'

        self.socket_file.write(command + '\n')
        self.socket_file.flush()
        
        return self.read_response()

    def read_response(self):
        more_lines = True
        lines = []
        error_code = -1
        error_message = ''
        while more_lines:
            line = self.socket_file.readline()
        
            if line.startswith('DVBStreamer/'):
                more_lines = False
                sections = line.split('/')
                self.version = sections[1]
                error_sections = sections[2].split(' ', 1)
                error_code = int(error_sections[0])
                if len(error_sections) > 1:
                    error_message = error_sections[1].strip()
                else:
                    error_message = ''
            elif line == '':
                more_lines = False
            else:
                lines.append(line.strip('\n\r'))

        return (error_code, error_message, lines)
        
        
if __name__ == '__main__':
    ctrl = Controller('localhost',0, 'dvbstreamer', 'control')
    print 'Frontend : ', ctrl.get_frontend_status()
    print 'Stats    : ', ctrl.get_stats()
    services = ctrl.get_services()
    print '%d Services' % len(services)
    for service in services:
        print '\t"%s"' % service
