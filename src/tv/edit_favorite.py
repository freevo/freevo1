# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# Edit TV favorite recordings
# -----------------------------------------------------------------------
# $Id$
#
# Todo:
# Notes:
#
# -----------------------------------------------------------------------
#
# Freevo - A Home Theater PC framework
#
# Copyright (C) 2002 Krister Lagerstrom, et al.
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
# ----------------------------------------------------------------------


from time import gmtime, strftime

import config
import tv.epg_xmltv
from tv.record_client import RecordClient
import event as em

from tv.epg_types import TvProgram
from tv.record_types import Favorite, ScheduledRecordings
from tv.view_favorites import ViewFavorites

from gui.GUIObject      import *
from gui.Border         import *
from gui.Label          import *
from gui.AlertBox       import *
from gui.OptionBox      import *
from gui.LetterBoxGroup import *
from gui.ConfirmBox     import ConfirmBox

TRUE = 1
FALSE = 0


class EditFavorite(PopupBox):
    """
    @param prog:    the program to record
    @param left:    x coordinate, Integer
    @param top:     y coordinate, Integer
    @param width:   width in pixels, Integer
    @param height:  height in pixels, Integer
    @param context: context in which the object is instantiated
    """
    def __init__(self, parent=None, subject=None, left=None, top=None, width=500, height=350, context=None):
        """ """
        _debug_('EditFavorite.__init__(parent=%r, subject=%r, left=%r, top=%r, width=%r, height=%r, context=%r)' % \
            (parent, subject, left, top, width, height, context), 1)

        self.oldname = None
        if context:
            self.context = context
        else:
            context = 'guide'

        self.recordclient = RecordClient()
        if isinstance(subject, TvProgram):
            (result, favs) = self.recordclient.getFavorites()
            if result:
                num_favorites = len(favs)
                self.priority = num_favorites + 1
            else:
                self.priority = 1
            self.fav = Favorite(subject.title, subject, TRUE, TRUE, TRUE, self.priority, TRUE, FALSE)

        else:
            self.fav = subject
            self.oldname = self.fav.name

        PopupBox.__init__(self, text=_('Edit Favorite'), x=left, y=top, width=width, height=height)

        self.v_spacing = 15
        self.h_margin = 20
        self.v_margin = 20

        self.internal_h_align = Align.LEFT

        if not self.left:     self.left   = self.osd.width/2 - self.width/2
        if not self.top:      self.top    = self.osd.height/2 - self.height/2

        guide = epg_xmltv.get_guide()

        name = Label(_('Name')+':', self, Align.LEFT)
        self.name_input = LetterBoxGroup(text=self.fav.name)
        self.name_input.h_align = Align.NONE
        self.add_child(self.name_input)


        title = Label(_('Title')+': %s' % self.fav.title, self, Align.LEFT)

        chan = Label(_('Channel')+':', self, Align.LEFT)

        self.chan_box = OptionBox('ANY')
        self.chan_box.h_align = Align.NONE
        self.chan_box.add_item(text=_('ANY'), value='ANY')

        i = 1
        chan_index = 0
        for ch in guide.chan_list:
            #if ch.id == self.fav.channel_id:
            if ch.displayname == self.fav.channel:
                chan_index = i
            i += 1
            self.chan_box.add_item(text=ch.displayname, value=ch.displayname)


        self.chan_box.toggle_selected_index(chan_index)
        # This is a hack for setting the OptionBox's label to the current value.
        # It should be done by OptionBox when drawing, but it doesn't work :(
        self.chan_box.change_item(None)
        self.add_child(self.chan_box)

        dow = Label(_('Day of Week') +':', self, Align.LEFT)
        self.dow_box = OptionBox('ANY DAY')
        self.dow_box.h_align = Align.NONE

        self.dow_box.add_item(text=_('ANY DAY'), value='ANY')

        i=1
        dow_index = 0
        for dow in (_('Mon'), _('Tue'), _('Wed'), _('Thu'), _('Fri'), _('Sat'), _('Sun')):
            val = "%d" % (i-1)
            self.dow_box.add_item(text=_(dow), value=val )
            if val == self.fav.dow:
                dow_index = i
            i += 1
        self.dow_box.toggle_selected_index(dow_index)
        # This is a hack for setting the OptionBox's label to the current value.
        # It should be done by OptionBox when drawing, but it doesn't work :(
        self.dow_box.change_item(None)
        self.add_child(self.dow_box)

        tod = Label(_('Time of Day')+':', self, Align.LEFT)
        self.tod_box = OptionBox('ANY')
        self.tod_box.h_align = Align.NONE
        self.tod_box.add_item(text=_('ANY TIME'), value='ANY')

        i = 0
        tod_index = 0

        for h in range(0, 24):
            for m in (00, 30):
                val = i*30
                # Little hack: we calculate the hours from Jan 1st, 1970 GMT,
                # and then use strftime to get the string representation
                text = strftime(config.TV_TIME_FORMAT, gmtime(h * 3600 + 60 * m))
                self.tod_box.add_item(text=text, value=val)
                if val == self.fav.mod:
                    tod_index = i+1
                i += 1
        self.tod_box.toggle_selected_index(tod_index)
        # This is a hack for setting the OptionBox's label to the current
        # value. It should be done by OptionBox when drawing, but it doesn't
        # work :(
        self.tod_box.change_item(None)
        self.add_child(self.tod_box)

        self.save = Button(_('Save'))
        self.add_child(self.save)
        if self.oldname:
            self.remove = Button(_('Remove'))
            self.add_child(self.remove)
        else:
            self.remove = None
        self.cancel = Button(_('CANCEL'))
        self.add_child(self.cancel)


    def removeFavorite(self):
        _debug_('removeFavorite()', 2)
        (result, reason) = self.recordclient.removeFavoriteNow(self.oldname)
        if result:
            searcher = None
            if self.parent and self.context == 'favorites':
                for child in self.parent.children:
                    if isinstance(child, ViewFavorites):
                        searcher = child
                        break
                if searcher:
                    searcher.refreshList()
                self.destroy()
                if searcher:
                    searcher.draw()
                    self.osd.update()
        else:
            AlertBox(parent=self, text=_('Remove favorite failed')+(':\n%s' % reason)).show()


    def eventhandler(self, event, menuw=None):
        _debug_('eventhandler(event=%r, menuw=%r)' % (event, menuw), 2)

        if self.get_selected_child() == self.name_input:
            if event == em.INPUT_LEFT:
                self.name_input.change_selected_box('left')
                self.draw()
                return True
            elif event == em.INPUT_RIGHT:
                self.name_input.change_selected_box('right')
                self.draw()
                return True
            elif event == em.INPUT_ENTER:
                self.name_input.get_selected_box().toggle_selected()
                self.chan_box.toggle_selected()
                self.draw()
                return True
            elif event == em.INPUT_UP:
                self.name_input.get_selected_box().charUp()
                self.draw()
                return True
            elif event == em.INPUT_DOWN:
                self.name_input.get_selected_box().charDown()
                self.draw()
                return True
            elif event in em.INPUT_ALL_NUMBERS:
                self.name_input.get_selected_box().cycle_phone_char(event)
                self.draw()
                return True
            elif event == em.INPUT_EXIT:
                self.destroy()
                return True

        elif self.get_selected_child() == self.chan_box:
            if event in (em.INPUT_UP, em.INPUT_DOWN):
                self.chan_box.change_item(event)
                self.draw()
            elif event == em.INPUT_ENTER:
                if self.chan_box.selected or self.chan_box.list.is_visible():
                    self.chan_box.toggle_box()
                    self.draw()
            elif event in (em.INPUT_LEFT, em.MENU_PAGEUP):
                self.chan_box.toggle_selected()
                self.name_input.boxes[0].toggle_selected()
                self.draw()
            elif event in (em.INPUT_RIGHT, em.MENU_PAGEDOWN):
                self.chan_box.toggle_selected()
                self.dow_box.toggle_selected()
                self.draw()
            elif event == em.INPUT_EXIT:
                self.destroy()
            return True

        elif self.get_selected_child() == self.dow_box:
            if event in (em.INPUT_UP, em.INPUT_DOWN):
                self.dow_box.change_item(event)
                self.draw()
            elif event == em.INPUT_ENTER:
                if self.dow_box.selected or self.dow_box.list.is_visible():
                    self.dow_box.toggle_box()
                    self.draw()
            elif event in (em.INPUT_LEFT, em.MENU_PAGEUP):
                self.dow_box.toggle_selected()
                self.chan_box.toggle_selected()
                self.draw()
            elif event in (em.INPUT_RIGHT, em.MENU_PAGEDOWN):
                self.dow_box.toggle_selected()
                self.tod_box.toggle_selected()
                self.draw()
            elif event == em.INPUT_EXIT:
                self.destroy()
                return True
            return True

        elif self.get_selected_child() == self.tod_box:
            if event in (em.INPUT_UP, em.INPUT_DOWN):
                self.tod_box.change_item(event)
                self.draw()
            elif event == em.INPUT_ENTER:
                if self.tod_box.selected or self.tod_box.list.is_visible():
                    self.tod_box.toggle_box()
                    self.draw()
            elif event in (em.INPUT_LEFT, em.MENU_PAGEUP):
                self.tod_box.toggle_selected()
                self.dow_box.toggle_selected()
                self.draw()
            elif event in (em.INPUT_RIGHT, em.MENU_PAGEDOWN):
                self.tod_box.toggle_selected()
                self.save.toggle_selected()
                self.draw()
            elif event == em.INPUT_EXIT:
                self.destroy()
                return True
            return True

        elif self.get_selected_child() == self.save:
            if event == em.INPUT_ENTER:
                # remove the old favourite
                if self.oldname:
                    (result, reason) = self.recordclient.removeFavoriteNow(self.oldname)
                    if not result:
                        AlertBox(parent=self, text=_('Add favorite failed')+(':\n%s' % reason)).show()
                # add the new favourite
                (result, reason) = self.recordclient.addEditedFavoriteNow(self.name_input.get_word(), self.fav.title,
                    self.chan_box.list.get_selected_item().value, self.dow_box.list.get_selected_item().value,
                    self.tod_box.list.get_selected_item().value, self.fav.priority, self.fav.allowDuplicates,
                    self.fav.onlyNew)
                if result:
                    #tv.view_favorites.ViewFavorites(parent=self.parent, text='Favorites').show()
                    self.destroy()
                    AlertBox(parent='osd', text=_('Favorite %s has been saved') % self.name_input.get_word()).show()
                else:
                    AlertBox(parent=self, text=_('Add favorite failed')+(':\n%s' % reason)).show()
                return True
            elif event in (em.INPUT_LEFT, em.MENU_PAGEUP):
                self.save.toggle_selected()
                self.tod_box.toggle_selected()
                self.draw()
            elif event in (em.INPUT_RIGHT, em.MENU_PAGEDOWN):
                self.save.toggle_selected()
                if self.remove:
                    self.remove.toggle_selected()
                else:
                    self.cancel.toggle_selected()
                self.draw()
            elif event == em.INPUT_EXIT:
                self.destroy()
                return True
            return True

        elif self.get_selected_child() == self.remove:
            if event == em.INPUT_ENTER:
                ConfirmBox(text=_('Do you want to remove %s?') % self.name_input.get_word(),
                           handler=self.removeFavorite).show()
                return True
            elif event in (em.INPUT_LEFT, em.MENU_PAGEUP):
                self.save.toggle_selected()
                self.remove.toggle_selected()
                self.draw()
            elif event in (em.INPUT_RIGHT, em.MENU_PAGEDOWN):
                self.remove.toggle_selected()
                self.cancel.toggle_selected()
                self.draw()
            elif event in (em.INPUT_ENTER, em.INPUT_EXIT):
                self.destroy()
                return True
            return True

        elif self.get_selected_child() == self.cancel:
            if event in (em.INPUT_LEFT, em.MENU_PAGEUP):
                if self.remove:
                    self.remove.toggle_selected()
                else:
                    self.save.toggle_selected()
                self.cancel.toggle_selected()
                self.draw()
            elif event in (em.INPUT_ENTER, em.INPUT_EXIT):
                self.destroy()
                return True
            return True
        if event == em.INPUT_EXIT:
            self.destroy()
            return True
        elif event in (em.MENU_PAGEDOWN, em.MENU_PAGEUP):
            return True
        else:
            return self.parent.eventhandler(event)
