# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# epg_xmltv.py - Freevo Electronic Program Guide module for XMLTV
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
import time
import os
import traceback
import calendar
import shutil

import config
import util

import tv.xmltv as xmltv

# The EPG data types. They need to be in an external module in order for pickling
# to work properly when run from inside this module and from the tv.py module.
from tv.epg_types import EPG_VERSION, TvGuide, TvChannel, TvProgram

class EpgException(Exception):
    """
    Electronic programming guide exception class
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


cached_guide = None


def get_guide(popup=False, XMLTV_FILE=None):
    """
    Get a TV guide from memory cache, file cache or raw XMLTV file.
    Tries to return at least the channels from the config file if there
    is no other data
    """
    global cached_guide

    if not XMLTV_FILE:
        XMLTV_FILE = config.XMLTV_FILE

    if popup:
        import dialog.dialogs
        popup_dialog = dialog.dialogs.ProgressDialog( _('Preparing the program guide'), indeterminate=True)

    # Can we use the cached version (if same as the file)?
    if (cached_guide == None or
        (os.path.isfile(XMLTV_FILE) and
         cached_guide.timestamp != os.path.getmtime(XMLTV_FILE))):

        # No, is there a pickled version ("file cache") in a file?
        pname = '%s/TV.xml.pickled' % config.FREEVO_CACHEDIR

        got_cached_guide = False
        if (os.path.isfile(XMLTV_FILE) and
            os.path.isfile(pname) and (os.path.getmtime(pname) > os.path.getmtime(XMLTV_FILE))):
            _debug_('XMLTV, reading cached file (%s)' % pname)

            if popup:
                popup_dialog.show()

            cached_guide = util.read_pickle(pname)

            epg_ver = None
            try:
                epg_ver = cached_guide.EPG_VERSION
            except AttributeError:
                _debug_('EPG does not have a version number, must be reloaded')

            if epg_ver != EPG_VERSION:
                _debug_('EPG version missmatch, must be reloaded')

            elif cached_guide.timestamp != os.path.getmtime(XMLTV_FILE):
                # Hmmm, weird, there is a pickled file newer than the TV.xml
                # file, but the timestamp in it does not match the TV.xml
                # timestamp. We need to reload!
                _debug_('EPG: Pickled file timestamp mismatch, reloading!')

            else:
                _debug_('XMLTV, got cached guide (version %s).' % epg_ver, DINFO)
                got_cached_guide = True

        if not got_cached_guide:
            # Need to reload the guide

            if popup:
                popup_dialog.show()

            _debug_('XMLTV, trying to read raw file (%s)' % XMLTV_FILE)
            try:
                cached_guide = load_guide(XMLTV_FILE)
            except:
                # Don't violently crash on a incomplete or empty TV.xml please.
                cached_guide = None
                print
                print String(_("Couldn't load the TV Guide, got an exception!"))
                print
                traceback.print_exc()
            else:
                # Replace config.XMLTV_FILE before we save the pickle in order
                # to avoid timestamp confision.
                if XMLTV_FILE != config.XMLTV_FILE:
                    _debug_('copying %r -> %r' % (XMLTV_FILE, config.XMLTV_FILE), DINFO)
                    shutil.copyfile(XMLTV_FILE, config.XMLTV_FILE)
                    os.unlink(XMLTV_FILE)
                    cached_guide.timestamp = os.path.getmtime(config.XMLTV_FILE)

                # Dump a pickled version for later reads
                util.save_pickle(cached_guide, pname)

    if not cached_guide:
        # An error occurred, return an empty guide
        cached_guide = TvGuide()

    if popup:
        popup_dialog.hide()

    return cached_guide


def load_guide(XMLTV_FILE=None):
    """
    Load a guide from the raw XMLTV file using the xmltv.py support lib.
    Returns a TvGuide or None if an error occurred
    """
    if not XMLTV_FILE:
        XMLTV_FILE = config.XMLTV_FILE

    # Create a new guide
    guide = TvGuide()

    # Is there a file to read from?
    if os.path.isfile(XMLTV_FILE):
        gotfile = 1
        guide.timestamp = os.path.getmtime(XMLTV_FILE)
    else:
        _debug_('XMLTV file (%s) missing!' % XMLTV_FILE)
        gotfile = 0

    # Add the channels that are in the config list, or all if the
    # list is empty
    if config.TV_CHANNELS:
        _debug_('Only adding channels in TV_CHANNELS to TvGuide')

        for data in config.TV_CHANNELS:
            (id, displayname, tunerid) = data[:3]
            c = TvChannel(id, displayname, tunerid)

            # Handle the optional time-dependent station info
            c.times = []
            if len(data) > 3 and len(data[3:4]) == 3:
                for (days, start_time, stop_time) in data[3:4]:
                    c.times.append((days, int(start_time), int(stop_time)))
            guide.add_channel(c)


    else: # Add all channels in the XMLTV file
        _debug_('Adding all channels to TvGuide')

        xmltv_channels = None
        if gotfile:
            # Don't read the channel info unless we have to, takes a long time!
            xmltv_channels = xmltv.read_channels(util.gzopen(XMLTV_FILE))

        # Was the guide read successfully?
        if not xmltv_channels:
            return None     # No

        for chan in xmltv_channels:
            id = chan['id'].encode(config.LOCALE, 'ignore')
            if ' ' in id:
                # Assume the format is "TUNERID CHANNELNAME"
                tunerid = id.split()[0]       # XXX Educated guess
                displayname = id.split()[1]   # XXX Educated guess
            else:
                display_name = chan['display-name'][0][0]
                if ' ' in display_name:
                    tunerid = display_name.split()[0]
                    displayname = display_name.split()[1]
                else:
                    tunerid = _('REPLACE WITH TUNERID FOR %s') % display_name
                    displayname = display_name

            c = TvChannel(id, displayname, tunerid)
            guide.add_channel(c)

    xmltv_programs = None
    if gotfile:
        _debug_('reading \"%s\" xmltv data' % XMLTV_FILE)
        f = util.gzopen(XMLTV_FILE)
        xmltv_programs = xmltv.read_programmes(f)
        f.close()

    # Was the guide read successfully?
    if not xmltv_programs:
        return guide    # Return the guide, it has the channels at least...

    needed_ids = []
    for chan in guide.chan_dict:
        needed_ids.append(chan)

    _debug_('creating guide for %s' % needed_ids)

    for p in xmltv_programs:
        if not p['channel'] in needed_ids:
            continue
        try:
            channel_id = p['channel']
            date = 'date' in p and Unicode(p['date']) or ''
            start = ''
            pdc_start = ''
            stop = ''
            title = Unicode(p['title'][0][0])
            desc = 'desc' in p and Unicode(util.format_text(p['desc'][0][0])) or ''
            sub_title = 'sub-title' in p and Unicode(p['sub-title'][0][0]) or ''
            categories = 'category' in p and [ cat[0] for cat in p['category'] ] or ''
            advisories = []
            ratings = {}

            if 'rating' in p:
                for r in p['rating']:
                    if r.get('system') == 'advisory':
                        advisories.append(String(r.get('value')))
                        continue
                    ratings[String(r.get('system'))] = String(r.get('value'))
            try:
                start = timestr2secs_utc(p['start'])
                pdc_start = 'pdc_start' in p and timestr2secs_utc(p['pdc_start']) or start
                try:
                    stop = timestr2secs_utc(p['stop'])
                except:
                    # Fudging end time
                    stop = timestr2secs_utc(p['start'][0:8] + '235900' + p['start'][14:18])
            except EpgException, why:
                _debug_('EpgException: %s' % (why,), DWARNING)
                continue

            # fix bad German titles to make favorites work
            if title.endswith('. Teil'):
                title = title[:-6]
                if title.rfind(' ') > 0:
                    try:
                        part = int(title[title.rfind(' ')+1:])
                        title = title[:title.rfind(' ')].rstrip()
                        if sub_title:
                            sub_title = u'Teil %s: %s' % (part, sub_title)
                        else:
                            sub_title = u'Teil %s' % part
                    except Exception, e:
                        print 'Teil:', e

            prog = TvProgram(channel_id, start, pdc_start, stop, title, sub_title, desc, categories, ratings)
            prog.advisories = advisories
            prog.date = date
            guide.add_program(prog)
        except:
            traceback.print_exc()
            print 'Error in tv guide, skipping'

    guide.sort()
    return guide


def timestr2secs_utc(timestr):
    """
    Convert a timestring to UTC (=GMT) seconds.

    The format is either one of these two:
    '20020702100000 CDT'
    '200209080000 +0100'
    """

    # Accounting for feeds that pre-adjust start/finish timestamps in the feed to the
    # correct timezone and DO NOT provide a timestamp offset (as it would be zero).
    # An example of this strange behaviour is the OzTivo feed


    tz = None
    adj_secs = time.timezone
    # This is either something like 'EDT', or '+1'
    try:
        tval, tz = timestr.split()
    except ValueError:
        tval = timestr
        if config.XMLTV_TIMEZONE is not None:
            tz = config.XMLTV_TIMEZONE

    if tz == 'CET':
        tz='+1'

    tmTuple = ( int(tval[0:4]), int(tval[4:6]), int(tval[6:8]),
                int(tval[8:10]), int(tval[10:12]), 0, -1, -1, -1 )
    secs = calendar.timegm( tmTuple )

    # Is it the '+1' format?
    if tz and (tz[0] == '+' or tz[0] == '-'):
        try:
            min = int(tz[3:5])
        except ValueError:
            # sometimes the mins are missing :-(
            min = 0
        adj_secs = int(tz[1:3])*3600+ min*60
        if tz[0] == '+':
            adj_secs = - adj_secs
    else:
        _debug_('Time spec %r has a timezone that cannot be parsed.' % timestr, DWARNING)
        try:
            secs = time.mktime(time.strptime(timestr, xmltv.date_format))
        except ValueError:
            secs = time.mktime(time.strptime(timestr[:12], '%Y%m%d%H%M'))
    return adj_secs + secs


if __name__ == '__main__':
    xmltv_file = config.XMLTV_FILE
    if len(sys.argv) > 1:
        xmltv_file = sys.argv[1]
    print '%r' % xmltv_file
    # To break in the debugger uncomment the following two lines
    #import pdb
    #pdb.set_trace()
    guide = load_guide(xmltv_file)
    print '%r' % (guide,)
    for channel in guide.chan_list:
        print '  %r' % channel
        for program in channel.programs:
            print '    %s' % program
