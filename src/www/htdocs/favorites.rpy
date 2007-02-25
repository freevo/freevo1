#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# favorites.rpy - Web interface to display your favorite programs.
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

import sys, time, string
import urllib
import config

import tv.record_client as ri
import util.tv_util as tv_util

from www.web_types import HTMLResource, FreevoResource

TRUE = 1
FALSE = 0


class FavoritesResource(FreevoResource):

    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        (server_available, message) = ri.connectionTest()
        if not server_available:
            fv.printHeader(_('Favorites'), 'styles/main.css', selected=_('Favorites'))
            fv.printMessagesFinish(
                [ '<b>'+_('ERROR')+'</b>: '+_('Recording server is unavailable.') ]
                )

            return String( fv.res )

        action = fv.formValue(form, 'action')
        oldname = fv.formValue(form, 'oldname')
        name = fv.formValue(form, 'name')
        if name: name = string.replace(name,'%26','&')
        title = fv.formValue(form, 'title')
        chan = fv.formValue(form, 'chan')
        dow = fv.formValue(form, 'dow')
        mod = fv.formValue(form, 'mod')
        priority = fv.formValue(form, 'priority')
        allowDuplicates = 1
        onlyNew = 0
        if config.DUPLICATE_DETECTION:
           allowDuplicates = fv.formValue(form, 'allowDuplicates')
        if config.ONLY_NEW_DETECTION:
           onlyNew = fv.formValue(form, 'onlyNew')

        if action == 'remove':
            ri.removeFavorite(name)
        elif action == 'add':
            ri.addEditedFavorite(name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)
        elif action == 'edit':
            ri.removeFavorite(oldname)
            ri.addEditedFavorite(name, title, chan, dow, mod, priority, allowDuplicates, onlyNew)
        elif action == 'bump':
            ri.adjustPriority(name, priority)
        else:
            pass

        (status, favorites) = ri.getFavorites()


        days = {
            '0' : _('Monday'),
            '1' : _('Tuesday'),
            '2' : _('Wednesday'),
            '3' : _('Thursday'),
            '4' : _('Friday'),
            '5' : _('Saturday'),
            '6' : _('Sunday')
        }

        fv.printHeader(_('Favorites'), 'styles/main.css',selected=_('Favorites'))
        fv.res +='&nbsp;'
        fv.tableOpen('')
        fv.tableRowOpen('class="chanrow"')
        fv.tableCell(_('Favorite Name'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Program'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Channel'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Day of week'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Time of day'), 'class="guidehead" colspan="1"')
        if config.DUPLICATE_DETECTION:
           fv.tableCell(_('Duplicates'), 'class="guidehead" colspan="1"')
        if config.ONLY_NEW_DETECTION:
           fv.tableCell(_('Episodes'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Actions'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Priority'), 'class="guidehead" colspan="1"')
        fv.tableRowClose()

        def sortByPriority(a,b):
            if (a.priority < b.priority):
               return -1
            elif (a.priority > b.priority):
               return 1
            else:
               return 0
        favs = favorites.values()
        favs.sort(sortByPriority)
        for fav in favs:
            status = 'favorite'
            if fav.channel == 'ANY':
                fchan = _('ANY')
            else:
                fchan = fav.channel
                
            fv.tableRowOpen('class="chanrow"')
            fv.tableCell(Unicode(fav.name), 'class="'+status+'" colspan="1"')
            fv.tableCell(Unicode(fav.title), 'class="'+status+'" colspan="1"')
            fv.tableCell(fchan, 'class="'+status+'" colspan="1"')

            if fav.dow != 'ANY':
                cell = '%s' % days[str(fav.dow)]
            else:
                cell = _('ANY')
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            if fav.mod != 'ANY':
                cell = '%s' % tv_util.minToTOD(fav.mod)
            else:
                cell = _('ANY')
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            if config.DUPLICATE_DETECTION:
               (tempStatus, tempFav) = ri.getFavorite(fav.title)
               if hasattr(tempFav,'allowDuplicates') and int(tempFav.allowDuplicates) == 1:
                  cell = 'ALLOW'
               elif hasattr(tempFav,'allowDuplicates') and int(tempFav.allowDuplicates) == 0:
                  cell = 'PREVENT'
               else:
                  cell = 'NONE'
               fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            if config.ONLY_NEW_DETECTION:
               (tempStatus, tempFav) = ri.getFavorite(fav.title)
               if hasattr(tempFav,'onlyNew') and int(tempFav.onlyNew) == 1:
                  cell = 'ONLY NEW'
               elif hasattr(tempFav,'onlyNew') and int(tempFav.onlyNew) == 0:
                  cell = 'ALL'
               else:
                  cell = 'NONE'
               fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            fname_esc = urllib.quote(String(fav.name.replace('&','%26')))
            # cell = '<input type="hidden" name="action" value="%s">' % action
            cell = ('<a href="edit_favorite.rpy?action=edit&name=%s">'+_('Edit')+'</a>, ') % fname_esc
            cell += ('<a href="favorites.rpy?action=remove&name=%s">'+_('Remove')+'</a>') % fname_esc
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')

            cell = ''

            if favs.index(fav) != 0:
                tmp_prio = int(fav.priority) - 1
                cell += ('<a href="favorites.rpy?action=bump&name=%s&priority=-1">'+_('Higher')+'</a>') % fname_esc

            if favs.index(fav) != 0 and favs.index(fav) != len(favs)-1:
                cell += ' | '

            if favs.index(fav) != len(favs)-1:
                tmp_prio = int(fav.priority) + 1
                cell += ('<a href="favorites.rpy?action=bump&name=%s&priority=1">'+_('Lower')+'</a>') % fname_esc

            fv.tableCell(cell, 'class="'+status+'" colspan="1"')
        
            fv.tableRowClose()

        fv.tableClose()

        fv.printSearchForm()

        fv.printLinks()

        fv.printFooter()

        return String( fv.res )
    
resource = FavoritesResource()

