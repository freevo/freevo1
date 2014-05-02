# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# The main index to the web interface.
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

import config
import util
from www.web_types import HTMLResource, FreevoResource, RecordClientResource
import util.tv_util as tv_util

TRUE = 1
FALSE = 0

class IndexResource(FreevoResource):

    def __init__(self):
        self.recordclient = RecordClientResource()

    def _render(self, request):
        fv = HTMLResource()

        fv.printHeader(_('Welcome'), 'styles/main.css',selected=_('Home'))
        fv.res += '<div id="contentmain">\n'

        fv.res += '<br/><br/><h2>'+_('Freevo Web Status as of %s') % \
                (time.strftime('%B %d '+config.TV_TIME_FORMAT, time.localtime())) +'</h2>'

        status = self.recordclient().pingNow()
        (status, schedule) = self.recordclient().getScheduledRecordingsNow()

        if status is None:
            fv.res += '<p class="alert"><b>'+_('Notice')+'</b>: '+_('Recording server is not available')+'</p>\n'
        else:
            fv.res += '<p class="normal">'+_('Recording server is up and running')+'</p>\n'

        listexpire = tv_util.when_listings_expire()
        if listexpire == 1:
            fv.res += '<p class="alert"><b>'+_('Notice')+'</b>: '+_('Your listings expire in 1 hour')+'</p>\n'
        elif listexpire < 12:
            fv.res += '<p class="alert"><b>'+_('Notice')+'</b>: '+_('Your listings expire in %s hours') % \
                listexpire+'</p>\n'
        else:
            fv.res += '<p class="normal">'+_('Your listings are up to date')+'</p>\n'

        if status:
            progl = schedule
            f = lambda a, b: cmp(a.start, b.start)
            progl.sort(f)
            for prog in progl:
                try:
                    if prog.isRecording:
                        fv.res += '<p class="alert">'+_('Now Recording %s.')+'</p>\n' % prog.title
                        break
                except:
                    pass
            num_sched_progs = len(progl)
            if num_sched_progs == 1:
                fv.res += '<p class="normal">'+_('One program scheduled to record.')+'</p>\n'
            elif num_sched_progs > 0:
                fv.res += '<p class="normal">'+_('%i programs scheduled to record.') % num_sched_progs+'</p>\n'
            else:
                fv.res += '<p class="normal">'+_('No programs scheduled to record.')+'</p>\n'
        else:
            fv.res += '<p class="normal">'+_('No programs scheduled to record.')+'</p>\n'

        diskfree = _('%(free)i of %(total)i Mb free in %(dir)s') % ({
            'free': ((util.freespace(config.TV_RECORD_DIR) / 1024) / 1024),
            'total': ((util.totalspace(config.TV_RECORD_DIR) /1024) /1024),
            'dir': config.TV_RECORD_DIR})
        fv.res += '<p class="normal">' + diskfree + '</p>\n'
        fv.res += '</div>'
        fv.printWebRemote()
        fv.printSearchForm()
        #fv.printLinks()
        fv.printFooter()

        return String(fv.res)


resource = IndexResource()
