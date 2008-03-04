# -*- coding: iso-8859-1 -*-
# vim:autoindent:tabstop=4:softtabstop=4:shiftwidth=4:expandtab:filetype=python:
# -----------------------------------------------------------------------
# Web interface to the Freevo EPG.
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

import sys, string
import time
import datetime

from www.web_types import HTMLResource, FreevoResource
from twisted.web.woven import page

import util.tv_util as tv_util
import util
import config
import tv.epg_xmltv
from tv.record_client import RecordClient
from twisted.web import static
from www.configlib import *

DEBUG = 0

TRUE = 1
FALSE = 0

class GuideResource(FreevoResource):
    def __init__(self):
        self.recordclient = RecordClient()


    def GetChannelList(self, guide):
        clist = []
        for dchan in guide.chan_list:
            clist.append(dchan.displayname)

        return clist

    def TimeBooked(self,prog):
        bookedtime = False
        for schedule_prog in self.schedule.values():
            if  prog.start >=schedule_prog.start  and prog.start < schedule_prog.stop:
                bookedtime = True, schedule_prog
        if not bookedtime:
            schedule_prog = None
        return bookedtime , schedule_prog

    def GetChannel(self, display_channel,guide):
        for dchan in guide.chan_list:
            if display_channel == dchan.displayname:
                chan = dchan
        return chan

    def CreateChannelLine(self,prog):
        status = "programline"

        bookedtime, sch_prog = self.TimeBooked(prog)
        program_tip = ''
        if bookedtime:
            status = 'programtimebooked'
            program_tip = 'Scheduled Program : %s' %  Unicode(sch_prog.sub_title)

        if self.got_schedule:
            (result, reason) = self.recordclient.isProgScheduledNow(prog, self.schedule)
            if result:
                status = 'programlinerecord'
                if self.currenttime > prog.start  and self.currenttime < prog.stop:
                    status = 'programlinerecording'

        channel_line = ''
        cell = ''
        cell += '%s' % prog.title
        popid = '%s:%s' % (prog.channel_id, prog.start)
        pstarttime = time.localtime(prog.start)
        pstart = time.strftime(config.TV_TIME_FORMAT,pstarttime)
        channel_line += '<li id="%s">\n' % status
        channel_line += '<a id="%s" name="%s" onclick="guide_click(this, event)"> %s %s </a>\n' % (popid,program_tip,pstart,cell)
        channel_line += '<ul>\n'
        channel_line += '<li id="description">\n'
        if not prog.desc:
            channel_line += 'No Program Data'
        else:
            channel_line += '%s' % prog.desc
        channel_line  += '</li>\n'
        channel_line += '<li>%s</li>' % program_tip
        channel_line += '</ul>\n'
        channel_line += '</li>\n'
        return channel_line

    def BookTimeDiv():
        html = ''
        html += (
        u"<div id=\"popup\" class=\"proginfo\" style=\"display:none\">\n"\
        u"<div id=\"program-waiting\" style=\"background-color: #0B1C52; position: absolute\">\n"\
        u"  <br /><b>Fetching program information ...</b>\n"\
        u"</div>\n"\
        u"   <table id=\"program-info\" class=\"popup\">\n"\
        u"      <thead>\n"\
        u"         <tr>\n"\
        u"            <td id=\"program-title\">\n"\
        u"            </td>\n"\
        u"         </tr>\n"\
        u"      </thead>\n"\
        u"      <tbody>\n"\
        u"         <tr>\n"\
        u"            <td class=\"progdesc\" id=\"program-desc\">\n"\
        u"            </td>\n"\
        u"         </tr>\n"\
        u"         <tr>\n"\
        u"         <td class=\"progtime\">\n"\
        u"            <b>"+_('Start')+u":</b> <span id=\"program-start\"></span>, \n"\
        u"            <b>"+_('Stop')+u":</b> <span id=\"program-end\"></span>, \n"\
        u"            <b>"+_('Runtime')+u":</b> <span id=\"program-runtime\"></span> min\n"\
        u"            </td>\n"\
        u"         </td>\n"\
        u"      </tbody>\n"\
        u"      <tfoot>\n"\
        u"         <tr>\n"\
        u"            <td>\n"\
        u"               <table class=\"popupbuttons\">\n"\
        u"                  <tbody>\n"\
        u"                     <tr>\n"\
        u"                        <td onclick=\"program_popup_close();\">\n"\
        u"                        "+_('Close Window')+u"\n"\
        u"                        </td>\n"\
        u"                     </tr>\n"\
        u"                  </tbody>\n"\
        u"               </table>\n"\
        u"            </td>\n"\
        u"         </tr>\n"\
        u"      </tfoot>\n"\
        u"   </table>\n"\
        u"</div>\n" )
        html += "<iframe id='bookedhidden' style='visibility: hidden; width: 1px; height: 1px'></iframe>\n"
        return html


    def GetChannelPrograms(self,channel):
        channel_programs = '<ul id="daylistcontainer">\n'
        current_day =''

        for prog in channel.programs:

            if prog.stop > self.currenttime:
#                if self.TimeBooked(prog):

                if time.strftime('%b %d (%a)', time.localtime(prog.start)) <> current_day:
                    if current_day <> '':
                        channel_programs += '</ul>\n'
                        channel_programs += '</li>\n'

                    current_day = time.strftime('%b %d (%a)', time.localtime(prog.start))
                    js_onclick = "ShowList('%s')" % current_day
                    channel_programs += '<li id="dayline">\n'
                    channel_programs += '<a onclick="%s" id="current">%s</a>\n' % (js_onclick,current_day)
                    channel_programs += '<ul id="%s" class="subnavlist">\n' % (current_day)
                channel_programs += self.CreateChannelLine(prog)


        channel_programs += '</ul>\n'
        return channel_programs


    def _render(self, request):
        fv = HTMLResource()
        form = request.args

        self.guide = tv.epg_xmltv.get_guide()
        (self.got_schedule, self.schedule) = self.recordclient.getScheduledRecordingsNow()
        self.currenttime = time.time()

        if self.got_schedule:
            self.schedule = self.schedule.getProgramList()

        fv.printHeader(_('TV Guide'), config.WWW_STYLESHEET, config.WWW_JAVASCRIPT, selected=_('TV Guide'))
        fv.res += '<link rel="stylesheet" href="styles/guidechannel.css" type="text/css" media="screen">\n'
        fv.res += '<div id="content">\n';
        fv.res += '&nbsp;<br/>\n'

        if not self.got_schedule:
            fv.printMessages([ '<b>'+_('ERROR')+'</b>: '+_('Recording server is not available') ])

        display_channel = fv.formValue(form,'channel')
        if not display_channel:
            display_channel = self.guide.chan_list[0].displayname
        clist = []

        getprogramlist = fv.formValue(form,'getprogramlist')
        if getprogramlist:
            chan = self.GetChannel(getprogramlist,self.guide)
            fv.res = self.GetChannelPrograms(chan)
            return String(fv.res)

        dchan = self.GetChannel(display_channel,self.guide)
        fv.res += '<script language="JavaScript" type="text/JavaScript" src="scripts/guidechannel.js"></script>\n'
        js_onclick = "ChangeChannel(this)"
        ctrl_opts = 'onchange="%s"' % js_onclick
        clist = self.GetChannelList(self.guide)
        fv.res += CreateSelectBoxControl('channel',clist,display_channel,ctrl_opts)

        if not dchan.programs:
            fv.res += 'This channel has no data loaded\n'

        channel_programs = self.GetChannelPrograms(dchan)
        fv.res += '<div id="ProgramList">\n'
        fv.res += channel_programs
        fv.res += '</div>\n'

        fv.printSearchForm()
        fv.printLinks()
        fv.res += '</div>\n'
        fv.res += (
            u"<div id=\"popup\" class=\"proginfo\" style=\"display:none\">\n"\
            u"<div id=\"program-waiting\" style=\"background-color: #0B1C52; position: absolute\">\n"\
            u"  <br /><b>Fetching program information ...</b>\n"\
            u"</div>\n"\
            u"   <table id=\"program-info\" class=\"popup\">\n"\
            u"      <thead>\n"\
            u"         <tr>\n"\
            u"            <td id=\"program-title\">\n"\
            u"            </td>\n"\
            u"         </tr>\n"\
            u"      </thead>\n"\
            u"      <tbody>\n"\
            u"         <tr>\n"\
            u"            <td class=\"progdesc\" id=\"program-desc\">\n"\
            u"            </td>\n"\
            u"         </tr>\n"\
            u"         <tr>\n"\
            u"         <td class=\"progtime\">\n"\
            u"            <b>"+_('Start')+u":</b> <span id=\"program-start\"></span>, \n"\
            u"            <b>"+_('Stop')+u":</b> <span id=\"program-end\"></span>, \n"\
            u"            <b>"+_('Runtime')+u":</b> <span id=\"program-runtime\"></span> min\n"\
            u"            </td>\n"\
            u"         </td>\n"\
            u"      </tbody>\n"\
            u"      <tfoot>\n"\
            u"         <tr>\n"\
            u"            <td>\n"\
            u"               <table class=\"popupbuttons\">\n"\
            u"                  <tbody>\n"\
            u"                     <tr>\n"\
            u"                        <td id=\"program-record-button\">\n"\
            u"                           "+_('Record')+u"\n"\
            u"                        </td>\n"\
            u"                        <td id=\"program-favorites-button\">\n"\
            u"                        "+_('Add to Favorites')+u"\n"\
            u"                        </td>\n"\
            u"                        <td onclick=\"program_popup_close();\">\n"\
            u"                        "+_('Close Window')+u"\n"\
            u"                        </td>\n"\
            u"                     </tr>\n"\
            u"                  </tbody>\n"\
            u"               </table>\n"\
            u"            </td>\n"\
            u"         </tr>\n"\
            u"      </tfoot>\n"\
            u"   </table>\n"\
            u"</div>\n" )
        fv.res += "<iframe id='hidden' style='visibility: hidden; width: 1px; height: 1px'></iframe>\n"
        fv.printFooter()

        return String( fv.res )


resource = GuideResource()
