# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Types for the Freevo Electronic Program Guide module.
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


import sys
import copy
import time, os, string
import config

# The file format version number. It must be updated when incompatible
# changes are made to the file format.
EPG_VERSION = 7

class TvProgram:
    """
    Holds information about a TV programme
    """
    def __init__(self, channel_id='', start=0, pdc_start=0, stop=2147483647, title='', sub_title='', desc='',
            categories=None, ratings=None):
        _debug_('TvProgram.__init__(channel_id=%r, start=%r, stop=%r, title=%r)' % (channel_id, start, stop, title), 2)
        self.channel_id = channel_id
        self.start      = start
        self.pdc_start  = pdc_start
        self.stop       = stop
        self.title      = title
        self.desc       = desc
        self.sub_title  = sub_title
        self.ratings    = ratings or {}
        self.advisories = []
        self.categories = categories or []
        self.date       = None

        # this information is added by the recordserver
        self.scheduled  = 0
        self.overlap    = 0
        self.previouslyRecorded = 0
        self.allowDuplicates = 1
        self.onlyNew = 0


    def __str__(self):
        st = time.localtime(self.pdc_start) # PDC start time
        bt = time.localtime(self.start)   # Beginning time tuple
        et = time.localtime(self.stop)    # End time tuple
        begins = time.strftime('%a %b %d %H:%M', bt)
        starts = time.strftime('%H:%M', st)
        ends = time.strftime('%H:%M', et)
        overlaps = self.overlap and '*' or ' '
        try:
            channel_id = String(self.channel_id)
            title = String(self.title)
            s = '%s->%s (%s)%s %3s %s' % (begins, ends, starts, overlaps, channel_id, title)
        except UnicodeEncodeError: #just in case
            s = '%s->%s [%s]%s %3s %s' % (begins, ends, starts, overlaps, self.channel_id, self.title)
        return s


    def __repr__(self):
        bt = time.localtime(self.start)
        et = time.localtime(self.stop)
        return '<TvProgram %r %s->%s>' % (self.channel_id, time.strftime('%a %H:%M', bt), time.strftime('%H:%M', et))


    def __eq__(self, other):
        """ equality method """
        if not isinstance(other, TvProgram):
            return False
        return self.start == other.start \
            and self.stop == other.stop \
            and self.title == other.title \
            and self.channel_id == other.channel_id


    def __cmp__(self, other):
        """ compare function, return 0 if the objects are equal, <0 if less >0 if greater """
        if not isinstance(other, TvProgram):
            return 1
        if self.start != other.start:
            return self.start - other.start
        if self.stop != other.stop:
            return self.stop - other.stop
        if self.title != other.title:
            return self.title > other.title
        if self.channel_id != other.channel_id:
            return self.channel_id > other.channel_id
        return 0


    def getattr(self, attr):
        """
        return the specific attribute as string or an empty string
        """
        _debug_('getattr(attr=%r)' % (attr,), 3)
        if attr == 'start':
            return Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(self.start)))
        if attr == 'pdc_start':
            return Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(self.pdc_start)))
        if attr == 'stop':
            return Unicode(time.strftime(config.TV_TIME_FORMAT, time.localtime(self.stop)))
        if attr == 'date':
            return Unicode(time.strftime(config.TV_DATE_FORMAT, time.localtime(self.start)))
        if attr == 'time':
            return self.getattr('start') + u' - ' + self.getattr('stop')
        if hasattr(self, attr):
            return getattr(self, attr)
        return ''


    def utf2str(self):
        """
        Decode all internal strings from Unicode to String
        """
        _debug_('utf2str()', 3)
        ret = copy.copy(self)
        for var in dir(ret):
            if not var.startswith('_') and isinstance(getattr(ret, var), unicode):
                setattr(ret, var, String(getattr(ret, var)))
        return ret


    def str2utf(self):
        """
        Encode all internal strings from String to Unicode
        """
        _debug_('str2utf()', 3)
        ret = copy.copy(self)
        for var in dir(ret):
            if not var.startswith('_') and isinstance(getattr(ret, var), str):
                setattr(ret, var, Unicode(getattr(ret, var)))
        return ret


class TvChannel:
    """
    Holds information about a TV channel
    """
    def __init__(self, id, displayname, tunerid):
        """ Copy the programs that are inside the indicated time bracket """
        _debug_('TvChannel.__init__(id=%r, displayname=%r, tunerid=%r)' % (id, displayname, tunerid), 2)
        self.id = id
        self.displayname = displayname
        self.tunerid = tunerid
        self.logo = ''
        self.times = []
        self.programs = []


    def set_logo(self, logo):
        """ Sets the channels logo """
        _debug_('TvChannel.set_logo(logo=%r)' % (logo,), 2)
        self.logo = logo


    def set_times(self, times):
        """ Sets the times list """
        _debug_('TvChannel.set_times(times=%r)' % (times,), 2)
        self.times = times


    def set_programs(self, programs):
        """ Sets the programs list """
        _debug_('TvChannel.set_programs(programs=%r)' % (programs,), 2)
        self.programs = programs


    def sort(self):
        """ Sort the programs so that the earliest is first in the list """
        _debug_('TvChannel.sort(), displayname=%r' % (self.displayname,), 2)
        f = lambda a, b: cmp(a.start, b.start)
        self.programs.sort(f)


    def __str__(self):
        s = 'CHANNEL ID   %-20s %-20s' % (self.id, '"'+self.displayname+'"')
        if self.programs:
            s += '\n'
            for program in self.programs:
                s += '   ' + String(program) + '\n'
        else:
            s += '     NO DATA\n'
        return s


    def __repr__(self):
        return '<TvChannel %r %r %r>' % (self.id, self.displayname, self.tunerid)



class TvGuide:
    """
    """
    def __init__(self):
        _debug_('TvGuide.__init__()', 2)
        self.timestamp = float(0)
        # These two types map to the same channel objects
        self.chan_dict = {}   # Channels mapped using the id
        self.chan_list = []   # Channels, ordered
        self.categories = []
        self.EPG_VERSION = EPG_VERSION


    def add_channel(self, channel):
        _debug_('add_channel(channel=%r)' % (channel,), 2)
        if channel.id in self.chan_dict:
            return
        # Add the channel to both the dictionary and the list. This works
        # well in Python since they will both point to the same object!
        self.chan_dict[channel.id] = channel
        self.chan_list += [channel]


    def add_program(self, program):
        """ The channel must be present, or the program is silently dropped """
        _debug_('add_program(program=%r)' % (program,), 2)
        if program.channel_id not in self.chan_dict:
            return
        for category in program.categories:
            if category not in self.categories:
                self.categories.append(category)

        programs = self.chan_dict[program.channel_id].programs
        if len(programs) > 0:
            if programs[-1].start < program.stop and programs[-1].stop > program.start:
                _debug_('invalid stop time: %r' % self.chan_dict[program.channel_id].programs[-1])
                # the tv guide is corrupt, the last entry has a stop time higher than
                # the next start time. Correct that by reducing the stop time of
                # the last entry
                self.chan_dict[program.channel_id].programs[-1].stop = program.start
            if programs[-1].start == programs[-1].stop:
                _debug_('program has no duration %r' % self.chan_dict[program.channel_id].programs[-1])
                # Oops, something is broken here
                self.chan_dict[program.channel_id].programs = programs[:-1]
        self.chan_dict[program.channel_id].programs += [program]


    def get_programs(self, start=0, stop=2147483647, channel_id=None, category=None):
        """
        Get all programs that occur at least partially between the start and stop
        timeframe.

        @param start: is 0, get all programs from the start.
        @param stop: is 2147483647, get all programs until the end.
        @param channel_id: can be used to select a channel id, all channels are returned otherwise.
        @param category: can be used to select only programs in the specified category
        @returns: a list of TV channels
        """
        _debug_('get_programs(start=%r, stop=%r, channel_id=%r)' % (time.strftime('%H:%M', time.localtime(start)),
            time.strftime('%H:%M', time.localtime(stop)), channel_id), 2)

        global channel_cache
        if category is None:
            channels = channel_cache.cached(start, stop, channel_id)
            if channels is not None:
                _debug_('cached channels=%r' % (channels,), 2)
                return channels

            channel_cache.reset(start, stop, channel_id)

        channels = []
        for chan in self.chan_list:
            if channel_id and chan.id != channel_id:
                continue

            c = TvChannel(chan.id, chan.displayname, chan.tunerid)
            # Copy the programs that are inside the indicated time bracket
            c.set_logo(chan.logo)
            c.set_times(chan.times)
            if category is None:
                f = lambda p, a=start, b=stop: not (p.start > b or p.stop < a)
            else:
                f = lambda p, a=start, b=stop, c=category: not (p.start > b or p.stop < a) and (c in p.categories)
            c.set_programs(filter(f, chan.programs))

            channels.append(c)
            if category is None:
                channel_cache.add(chan.id, c)

        _debug_('channels=%r' % (channels,), 2)
        return channels


    def sort(self):
        """ Sort all channel programs in time order """
        _debug_('TvGuide.sort()', 2)
        for chan in self.chan_list:
            chan.sort()


    def __str__(self):
        s = 'XML TV Guide\n'
        for chan in self.chan_list:
            s += String(chan)
        return s


    def __repr__(self):
        return '<TvGuide %r>' % (self.EPG_VERSION)



class ChannelCache:
    """
    This class caches the list of channels for get_programs
    """
    def __init__(self):
        _debug_('ChannelCache.__init__()', 2)
        self.channel_id = None
        self.timestamp = float(0)
        self.start = None
        self.stop = None
        self.channel_ids = []
        self.channels = []


    def reset(self, start, stop, channel_id):
        """
        Reset the cache to empty
        """
        _debug_('reset(start=%r, stop=%r, channel_id=%r)' % (start, stop, channel_id), 2)
        self.channel_id = channel_id
        if self.channel_id is None:
            self.timestamp = float(time.time())
            self.start = start
            self.stop = stop
            self.channel_ids = []
            self.channels = []


    def add(self, channel_id, channel):
        """
        Add a channel to the cache
        """
        _debug_('add(channel_id=%r, channel=%r)' % (channel_id, channel), 2)
        if self.channel_id is None:
            self.channel_ids.append(channel_id)
            self.channels.append(channel)


    def cached(self, start, stop, channel_id):
        """
        get the cached channel list for the channel_id

        @param start: start time of the channels
        @param channel_id: the channel to fetch from the cache
        @returns: None if the cache is out of date otherwise the list of channels
        """
        _debug_('cached(start=%r, stop=%r, channel_id=%r)' % (start, stop, channel_id), 2)
        if time.time() - self.timestamp > 20:
            #print 'cache is out of date: %r' % int(time.time() - self.timestamp)
            return None
        if start != self.start:
            #print 'cache has a different start time: %r != %r' % (start, self.start)
            return None
        if stop != self.stop:
            #print 'cache has a different stop time: %r != %r' % (stop, self.stop)
            return None
        if len(self.channels) == 0:
            #print 'cache is empty'
            return None
        if channel_id is not None:
            if channel_id not in self.channel_ids:
                #print 'cache does not contain channel %r' % (channel_id,)
                return None
            n = self.channel_ids.index(channel_id)
            #print 'cached channel=%r' % (self.channels[n:n+1],)
            return self.channels[n:n+1]
        #print 'cached channels=%r' % (self.channels[:],)
        return self.channels[:]

channel_cache = ChannelCache()
