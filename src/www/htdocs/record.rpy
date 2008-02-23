# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to your scheduled recordings.
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

from tv.record_client import RecordClient

from www.web_types import HTMLResource, FreevoResource

import config

TRUE = 1
FALSE = 0

class RecordResource(FreevoResource):
    def __init__(self):
        self.recordclient = RecordClient()

    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        chan = Unicode(fv.formValue(form, 'chan'))
        if isinstance( chan, str ):
            chan = Unicode( chan, 'latin-1' )

        start = fv.formValue(form, 'start')
        action = fv.formValue(form, 'action')

        server_available = self.recordclient.pingNow()
        if server_available is None:
            fv.printHeader('Scheduled Recordings', 'styles/main.css')
            fv.printMessagesFinish(['<b>'+_('ERROR')+'</b>: '+_('Recording server is not available')])
            return String( fv.res )

        if action == 'remove':
            recordings = self.recordclient.getScheduledRecordingsNow()
            progs = recordings.getProgramList()

            prog = None
            for what in progs.values():
                if start == '%s' % what.start and chan == '%s' % what.channel_id:
                    prog = what

            if prog:
                self.recordclient.removeScheduledRecordingNow(prog)
        elif action == 'add':
            (status, prog) = self.recordclient.findProgNow(chan, start)

            if not status:
                fv.printHeader('Scheduled Recordings', 'styles/main.css')
                fv.printMessagesFinish(
                    ['<b>'+_('ERROR') + '</b>: ' + \
                      _('No program found on %s at %s.') % \
                           ('<b>'+chan+'</b>', '<b>'+time.strftime('%x %X', time.localtime(int(start)))+'</b>')+\
                       (' <i>(%s)</i>' % String(prog))])
                return String(fv.res)

            self.recordclient.scheduleRecordingNow(prog)

        recordings = self.recordclient.getScheduledRecordingsNow()
        progs = recordings.getProgramList()
        favs = self.recordclient.getFavoritesNow()

        fv.printHeader(_('Scheduled Recordings'), 'styles/main.css', selected=_('Scheduled Recordings'))

        fv.res += '&nbsp;\n'

        fv.tableOpen('')
        fv.tableRowOpen('class="chanrow"')
        fv.tableCell(_('Start Time'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Stop Time'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Channel'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Title'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Episode'),'class="guidehead" colspan="1"')
        fv.tableCell(_('Program Description'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Actions'), 'class="guidehead" colspan="1"')
        fv.tableRowClose()

        f = lambda a, b: cmp(a.start, b.start)
        progl = progs.values()
        progl.sort(f)
        for prog in progl:
            status = 'basic'

            (isFav, message) = self.recordclient.isProgAFavoriteNow(prog, favs)
            if isFav:
                status = 'favorite'
            try:
                if prog.isRecording == TRUE:
                    status = 'recording'
            except:
                # sorry, have to pass without doing anything.
                pass

            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(time.strftime('%b %d '+config.TV_TIME_FORMAT, time.localtime(prog.start)),
                'class="'+status+'" colspan="1"')
            fv.tableCell(time.strftime('%b %d '+config.TV_TIME_FORMAT, time.localtime(prog.stop)),
                'class="'+status+'" colspan="1"')

            chan = tv_util.get_chan_displayname(prog.channel_id)
            if not chan: chan = _('UNKNOWN')
            fv.tableCell(chan, 'class="'+status+'" colspan="1"')
            fv.tableCell(Unicode(prog.title), 'class="'+status+'" colspan="1"')

            if prog.sub_title == '':
                cell = '&nbsp;'
            else:
                cell = Unicode(prog.sub_title)
            fv.tableCell(cell,'class="'+status+'" colspan="1"')


            if prog.desc == '':
                cell = _('Sorry, the program description for %s is unavailable.') % ('<b>'+prog.title+'</b>')
            else:
                cell = Unicode(prog.desc)
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            cell = ('<a href="record.rpy?chan=%s&amp;start=%s&amp;action=remove">'+_('Remove')+'</a>') % (prog.channel_id, prog.start)
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            fv.tableRowClose()

        fv.tableClose()

        fv.printSearchForm()
        #fv.printLinks()
        fv.printFooter()

        return String( fv.res )

resource = RecordResource()
