# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to search the Freevo EPG.
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

import sys, time
import util.tv_util as tv_util

import config
from tv.record_client import RecordClient
from www.web_types import HTMLResource, FreevoResource

TRUE = 1
FALSE = 0


class SearchResource(FreevoResource):
    def __init__(self):
        self.recordclient = RecordClient()


    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        (server_available, message) = self.recordclient.pingNow()
        if not server_available:
            fv.printHeader(_('Search Results'), 'styles/main.css', selected=_('Search'))
            fv.res += '<h4>'+_('ERROR')+': '+_('Recording server is not available')+'</h4>'
            fv.printAdvancedSearchForm()
            fv.printLinks()
            fv.printFooter()

            return String( fv.res )

        find = fv.formValue(form, 'find')
        if fv.formValue(form, 'movies_only'):
            movies_only = 1
        else:
            movies_only = 0

        (got_matches, progs) = self.recordclient.findMatchesNow(find, movies_only)

        if got_matches:
            (status, favs) = self.recordclient.getFavoritesNow()
            (status, schedule) = self.recordclient.getScheduledRecordingsNow()
            if status:
                rec_progs = schedule.getProgramList()

        fv.printHeader(_('Search'), 'styles/main.css', selected=_('Search'))

        fv.res += '<br /><br />'
        fv.printAdvancedSearchForm()

        if not got_matches:
            if find or movies_only:
                fv.res += '<h3>'+_('No matches')+'</h3>'
        else:
            fv.res += '<div id="content"><br>'
            fv.tableOpen('border="0" cellpadding="4" cellspacing="1" width="100%"')
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(_('Start Time'), 'class="guidehead" colspan="1"')
            fv.tableCell(_('Stop Time'), 'class="guidehead" colspan="1"')
            fv.tableCell(_('Channel'), 'class="guidehead" colspan="1"')
            fv.tableCell(_('Title'), 'class="guidehead" colspan="1"')
            fv.tableCell(_('Episode'),'class="guidehead" colspan="1"')
            fv.tableCell(_('Program Description'), 'class="guidehead" colspan="1"')
            fv.tableCell(_('Actions'), 'class="guidehead" colspan="1"')
            fv.tableRowClose()

            for prog in progs:

                status = 'basic'

                for rp in rec_progs.values():

                    if rp.start == prog.start and rp.channel_id == prog.channel_id:
                        status = 'scheduled'
                        try:
                            if rp.isRecording == TRUE:
                                status = 'recording'
                        except:
                            sys.stderr.write('isRecording not set')

                if self.recordclient.isProgAFavoriteNow(prog, favs):
                    status = 'favorite'


                fv.tableRowOpen('class="chanrow"')
                fv.tableCell(time.strftime('%b %d ' + config.TV_TIME_FORMAT, time.localtime(prog.start)), 'class="'+status+'" colspan="1"')
                fv.tableCell(time.strftime('%b %d ' + config.TV_TIME_FORMAT, time.localtime(prog.stop)), 'class="'+status+'" colspan="1"')

                chan = tv_util.get_chan_displayname(prog.channel_id)
                if not chan: chan = 'UNKNOWN'
                fv.tableCell(chan, 'class="'+status+'" colspan="1"')

                fv.tableCell(prog.title, 'class="'+status+'" colspan="1"')
                if prog.sub_title:
                    fv.tableCell(prog.sub_title, 'class="'+status+'" colspan="1"')
                else:
                    fv.tableCell('&nbsp;', 'class="'+status+'" colspan="1"')


                if prog.desc == '':
                    cell = _('Sorry, the program description for %s is unavailable.') % ('<b>'+prog.title+'</b>')
                else:
                    cell = prog.desc
                fv.tableCell(cell, 'class="'+status+'" colspan="1"')

                if status == 'scheduled':
                    cell = ('<a href="record.rpy?chan=%s&start=%s&action=remove">'+_('Remove')+'</a>') % \
                        (prog.channel_id, prog.start)
                elif status == 'recording':
                    cell = ('<a href="record.rpy?chan=%s&start=%s&action=add">'+_('Record')+'</a>') % \
                        (prog.channel_id, prog.start)
                else:
                    cell = ('<a href="record.rpy?chan=%s&start=%s&action=add">'+_('Record')+'</a>') % \
                        (prog.channel_id, prog.start)

                cell += (' | <a href="edit_favorite.rpy?chan=%s&start=%s&action=add">'+_('New favorite')+'</a>') % \
                    (prog.channel_id, prog.start)
                fv.tableCell(cell, 'class="'+status+'" colspan="1"')

                fv.tableRowClose()

            fv.tableClose()

        fv.res += '</div>'
        # fv.printSearchForm()

        fv.printLinks()

        fv.printFooter()

        return String( fv.res )

resource = SearchResource()
