# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Sqlite database wrapper
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


import os, traceback
import config

# helper functions

def tracknum(track):
    """
    Extract the track numbers from a mmpython result
    """

    trackno = -1
    trackof = -1

    if track:
        trackno = inti(track.split('/')[0])
        if track.find('/') != -1:
            trackof = inti(track.split('/')[1])
    return (trackno, trackof)


def escape(sql):
    """
    Escape a SQL query in a manner suitable for sqlite
    """
    if sql:
        sql = sql.replace("'", "''")
        return sql
    else:
        return 'null'

def inti(a):
    ret = 0
    if a:
        try:
            ret = int(a)
        except ValueError, e:
            print '"%s": %r' % (a, e)
            traceback.print_exc()

    return ret


try:
    import sqlite
except:
    _debug_('Python SQLite not installed!', DINFO)



class MetaDatabase:
    """ Class for working with the database """
    def __init__(self):
        sqlite_major_version = sqlite._sqlite.sqlite_version_info()[0]
        DATABASE = os.path.join(config.FREEVO_CACHEDIR, 'freevo.sqlite%i' % sqlite_major_version)
        self.db = sqlite.connect(DATABASE, client_encoding=config.LOCALE)
        self.cursor = self.db.cursor()


    def runQuery(self, query, close=False):
        """Execute a sql query on the database"""
        try:
            _debug_('query=%s' % (query))
            self.cursor.execute(query)
        except TypeError:
            traceback.print_exc()
            return False

        if close:
            # run a single query then close
            result = self.cursor.fetchall()
            self.db.commit()
            self.db.close()
            return result
        else:
            return self.cursor.fetchall()


    def close(self):
        """close the database, committing any open transactions first"""
        if not self.db.closed:
            self.db.commit()
            self.db.close()


    def commit(self):
        """commit transactions"""
        self.db.commit()


    def checkTable(self, table=None):
        if not table:
            return False
        # verify the table exists
        self.cursor.execute('SELECT name FROM sqlite_master where name="%s" and type="table"' % table)
        if not self.cursor.fetchone():
            return None
        return table
