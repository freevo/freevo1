# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# freevo_scrobbler - Upload the music you play to your last.fm profile
# -----------------------------------------------------------------------
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

import urllib2, urllib
import md5 , time
import config

URL = 'http://post.audioscrobbler.com/?hs=true&p=1.1&c=xms&v=0.7'


class Scrobbler:

    def __init__(self):
        self.username = config.LASTFM_USER
        self.md5_pass = config.LASTFM_PASS
        hasher = md5.new()
        hasher.update(self.md5_pass);
        self.password = hasher.hexdigest()

    def config(self):
        pass

    def send_handshake(self):
        url = URL + '&u=%s' % (self.username)
        resp = None

        try:
            resp = urllib2.urlopen(url);
        except Exception,e:
            print 'Server not responding, handshake failed: %s' % (e)
            return False

        # check response
        lines = resp.read().rstrip().split('\n')
        status = lines.pop(0)

        if status.startswith('UPDATE'):
            print 'Please update: %s' % status

        if status == 'UPTODATE' or status.startswith('UPDATE'):
            challenge = lines.pop(0)

            hasher = md5.new()
            hasher.update(self.password)
            hasher.update(challenge)
            self.password_hash = hasher.hexdigest()

            self.submit_url = lines.pop(0)
            print 'Handshake SUCCESS'

        try: self.interval_time = int(lines.pop(0).split()[1])
        except: pass

        if status == 'UPTODATE' or status.startswith('UPDATE'):
            return True
        elif status == 'BADUSER':
            print 'Handshake failed: bad user'
            return False
        else:
            print 'Handshake failed: %s' % status;
            return False

    def submit_song(self, info):
        data = {
            'u': self.username,
            's': self.password_hash
        }
        if info['length'] > 30*1000 and info['title'] and info['artist']:
            _debug_('Sending song: %r - %r' % (info['artist'], info['title']))
            i = 0
            stamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            data['a[%d]' % i] = info['artist'].encode('utf-8')
            data['t[%d]' % i] = info['title'].encode('utf-8')
            data['l[%d]' % i] = str(info['length']).encode('utf-8')
            data['b[%d]' % i] = info['album'].encode('utf-8')
            data['m[%d]' % i] = ''
            data['i[%d]' % i] = stamp

            (host, file) = self.submit_url[7:].split('/')
            url = 'http://' + host + '/' + file
            resp = None
            try:
                data_str = urllib.urlencode(data)
                resp = urllib2.urlopen(url, data_str)
                resp_save = resp.read()
            except Exception, e:
                print 'Audioscrobbler server not responding, will try later: %s' % (e)

            lines = resp_save.rstrip().split('\n')

            try: (status, interval) = lines
            except:
                try: status = lines[0]
                except:
                    _debug_('Status incorrect')
                    return False
            else: self.interval_time = int(interval.split()[1])

            if status == 'BADAUTH':
                print 'Authentication failed: invalid username or bad password.'
                print url
                print data

            elif status == 'OK':
                print 'Submit successful'
                return True

            elif status.startswith('FAILED'):
                print 'FAILED response from server: %s' % status
                print 'Dumping full response:'
                print resp_save
            else:
                print 'Unknown response from server: %s' % status
                print 'Dumping full response:'
                print resp_save
        else:
            print 'Song not accepted!'

        return False
