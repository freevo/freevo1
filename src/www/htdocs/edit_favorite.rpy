# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# edit_favorites.rpy - Web interface to edit your favorites.
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

from tv.record_types import Favorite
import tv.epg_xmltv
import tv.record_client as ri
import config

from www.web_types import HTMLResource, FreevoResource

TRUE = 1
FALSE = 0


class EditFavoriteResource(FreevoResource):

    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        (server_available, message) = ri.connectionTest()
        if not server_available:
            fv.printHeader(_('Edit Favorite'), 'styles/main.css')
            fv.printMessagesFinish(
                [ '<b>'+_('ERROR')+'</b>: '+_('Recording server is unavailable.') ]
                )
            return String( fv.res )

        chan = Unicode(fv.formValue(form, 'chan'))
        if isinstance( chan, str ):
            chan = Unicode( chan, 'latin-1' )

        start = fv.formValue(form, 'start')
        action = fv.formValue(form, 'action')
        name = Unicode(fv.formValue(form, 'name'))
        name = string.replace(name,'%26','&')
        if isinstance( name, str ):
            name = Unicode( name, 'latin-1' )

        (result, favs) = ri.getFavorites()
        num_favorites = len(favs)

        if action == 'add' and chan and start:
            (result, prog) = ri.findProg(chan, start)

            if not result:
                fv.printHeader('Edit Favorite', 'styles/main.css')
                fv.printMessagesFinish(
                    [ '<b>'+_('ERROR') + '</b>: ' + \
                      ( _('No program found on %s at %s.')%\
                        ( '<b>'+chan+'</b>',
                          '<b>'+time.strftime('%x %X',
                                              time.localtime(int(start))) + \
                          '</b>'
                         )
                        ) + (' <i>(%s)</i>' % String(prog)) ] )
                return String(fv.res)

            if prog:
                print 'PROG: %s' % String(prog)

            priority = num_favorites + 1

            fav = Favorite(prog.title, prog, TRUE, TRUE, TRUE, priority, FALSE)
        elif action == 'edit' and name:
            (result, fav) = ri.getFavorite(name)
        else:
            pass

        if not result:
            fv.printHeader('Edit Favorite', 'styles/main.css')
            fv.printMessagesFinish(
                [ '<b>'+_('ERROR') + '</b>: ' + \
                  ( _('Favorite %s doesn\'t exists.') % \
                    ( '<b>'+name+'</b>' )
                    )+\
                  ( ' <i>(%s)</i>' % fav )
                  ] )
            return String(fv.res)


        guide = tv.epg_xmltv.get_guide()

        fv.printHeader(_('Edit Favorite'), 'styles/main.css')
        fv.res += '&nbsp;<br/>\n'
        # This seems out of place.
        #fv.tableOpen('border="0" cellpadding="4" cellspacing="1" width="100%"')
        #fv.tableRowOpen('class="chanrow"')
        #fv.tableCell('<img src="images/logo_200x100.png" />', 'align="left"')
        #fv.tableCell(_('Edit Favorite'), 'class="heading" align="left"')
        #fv.tableRowClose()
        #fv.tableClose()

        fv.res += '<br><form name="editfavorite" method="get" action="favorites.rpy">'

        fv.tableOpen('border="0" cellpadding="4" cellspacing="1" width="100%"')
        fv.tableRowOpen('class="chanrow"')
        fv.tableCell(_('Name of favorite'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Program'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Channel'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Day of week'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Time of day'), 'class="guidehead" colspan="1"')
        if config.DUPLICATE_DETECTION:
            fv.tableCell(_('Duplicates'), 'class="guidehead" colspan="1"')
        if config.ONLY_NEW_DETECTION:
            fv.tableCell(_('Episodes'), 'class="guidehead" colspan="1"')
        fv.tableCell(_('Action'), 'class="guidehead" colspan="1"')
        fv.tableRowClose()

        status = 'basic'

        fv.tableRowOpen('class="chanrow"')

        cell = '<input type="hidden" name="oldname" value="%s">' % fav.name
        cell += '<input type="text" size="20" name="name" value="%s">' % fav.name
        fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        cell = '<input type="hidden" name="title" value="%s">%s' % (fav.title, fav.title)
        fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        cell = '\n<select name="chan" selected="%s">\n' % fav.channel
        cell += '  <option value=ANY>'+_('ANY CHANNEL')+'</option>\n'

        i=1
        for ch in guide.chan_list:
            if ch.displayname == fav.channel:
                chan_index = i
            cell += '  <option value="%s">%s</option>\n' % (ch.displayname, ch.displayname)
            i = i +1

        cell += '</select>\n'
        fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        cell = '\n<select name="dow">\n' \
               '   <option value="ANY">'+_('ANY DAY')+'</option>\n' \
               '   <option value="0">'+_('Mon')+'</option>\n' \
               '   <option value="1">'+_('Tue')+'</option>\n' \
               '   <option value="2">'+_('Wed')+'</option>\n' \
               '   <option value="3">'+_('Thu')+'</option>\n' \
               '   <option value="4">'+_('Fri')+'</option>\n' \
               '   <option value="5">'+_('Sat')+'</option>\n' \
               '   <option value="6">'+_('Sun')+'</option>\n' \
               '</select>\n'

        fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        cell = '\n<select name="mod" selected="%s">\n' % fav.mod
        cell += '          <option value="ANY">'+_('ANY TIME')+'</option>\n'
        cell += """
          <option value="0">12:00 AM</option>
          <option value="30">12:30 AM</option>
          <option value="60">1:00 AM</option>
          <option value="90">1:30 AM</option>
          <option value="120">2:00 AM</option>
          <option value="150">2:30 AM</option>
          <option value="180">3:00 AM</option>
          <option value="210">3:30 AM</option>
          <option value="240">4:00 AM</option>
          <option value="270">4:30 AM</option>
          <option value="300">5:00 AM</option>
          <option value="330">5:30 AM</option>
          <option value="360">6:00 AM</option>
          <option value="390">6:30 AM</option>
          <option value="420">7:00 AM</option>
          <option value="450">7:30 AM</option>
          <option value="480">8:00 AM</option>
          <option value="510">8:30 AM</option>
          <option value="540">9:00 AM</option>
          <option value="570">9:30 AM</option>
          <option value="600">10:00 AM</option>
          <option value="630">10:30 AM</option>
          <option value="660">11:00 AM</option>
          <option value="690">11:30 AM</option>
          <option value="720">12:00 PM</option>
          <option value="750">12:30 PM</option>
          <option value="780">1:00 PM</option>
          <option value="810">1:30 PM</option>
          <option value="840">2:00 PM</option>
          <option value="870">2:30 PM</option>
          <option value="900">3:00 PM</option>
          <option value="930">3:30 PM</option>
          <option value="960">4:00 PM</option>
          <option value="990">4:30 PM</option>
          <option value="1020">5:00 PM</option>
          <option value="1050">5:30 PM</option>
          <option value="1080">6:00 PM</option>
          <option value="1110">6:30 PM</option>
          <option value="1140">7:00 PM</option>
          <option value="1170">7:30 PM</option>
          <option value="1200">8:00 PM</option>
          <option value="1230">8:30 PM</option>
          <option value="1260">9:00 PM</option>
          <option value="1290">9:30 PM</option>
          <option value="1320">10:00 PM</option>
          <option value="1350">10:30 PM</option>
          <option value="1380">11:00 PM</option>
          <option value="1410">11:30 PM</option>
        </select>
        """
        fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        if config.DUPLICATE_DETECTION:
            if hasattr(fav, 'allowDuplicates'):
                cell = '\n<select name="allowDuplicates" selected="%s">\n' % \
                fav.allowDuplicates
            else:
                cell = '\n<select name="allowDuplicates">\n'
            cell += '          <option value="1">'+_('ALLOW')+'</option>\n'
            cell += '          <option value="0">'+_('PREVENT')+'</option>\n'
            cell += '</select>\n'
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        if config.ONLY_NEW_DETECTION:
            if hasattr(fav, 'onlyNew'):
                cell = '\n<select name="onlyNew" selected="%s">\n' % fav.onlyNew
            else:
                cell = '\n<select name="onlyNew">\n'
            cell += '          <option value="0">'+_('ALL')+'</option>\n'
            cell += '          <option value="1">'+_('ONLY NEW')+'</option>\n'
            cell += '</select>\n'
            fv.tableCell(cell, 'class="'+status+'" colspan="1"')


        # cell = '\n<select name="priority" selected="%s">\n' % fav.priority
        # for i in range(num_favorites+1):
        #     cell += '  <option value="%s">%s</option>\n' % (i+1, i+1)
        # cell += '</select>\n'
        # fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        cell = '<input type="hidden" name="priority" value="%s">' % fav.priority
        cell += '<input type="hidden" name="action" value="%s">' % action
        cell += '<input type="submit" value="'+_('Save')+'">'
        fv.tableCell(cell, 'class="'+status+'" colspan="1"')

        fv.tableRowClose()

        fv.tableClose()

        fv.res += '</form>'

        fv.res += '<script language="JavaScript">'

        if fav.channel == 'ANY':
            fv.res += 'document.editfavorite.chan.options[0].selected=true\n'
        else:
            fv.res += 'document.editfavorite.chan.options[%s].selected=true\n' % chan_index

        if fav.dow == 'ANY':
            fv.res += 'document.editfavorite.dow.options[0].selected=true\n'
        else:
            fv.res += 'document.editfavorite.dow.options[(1+%s)].selected=true\n' % fav.dow

        if fav.mod == 'ANY':
            fv.res += 'document.editfavorite.mod.options[0].selected=true\n'
        else:
            mod_index = int(fav.mod)/30 + 1
            fv.res += 'document.editfavorite.mod.options[%s].selected=true\n' % mod_index

        fv.res += '</script>'

        fv.printSearchForm()

        fv.printLinks()

        fv.printFooter()

        return String( fv.res )

resource = EditFavoriteResource()
