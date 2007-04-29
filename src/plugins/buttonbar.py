# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# buttonbar.py-ButtonBar plugin
# -----------------------------------------------------------------------
# $Id$
#
# -----------------------------------------------------------------------
# Freevo-A Home Theater PC framework
# Copyright (C) 2002 Krister Lagerstrom, et al.
# Please see the file freevo/Docs/CREDITS for a complete list of authors.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the Licestringnse, or
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

# python modules
import time
import os
import locale

# freevo modules
import config
import plugin
import skin
import osd
import event
import rc

from tv.tvguide import TVGuide
from item import Item
from menu import MenuItem, Menu
from pygame import image,transform, Surface

DEBUG = config.DEBUG

# Create the skin object
skin = skin.get_singleton()
skin.register('tvguideinfo', ('screen', 'title', 'info', 'plugin'))

# Create the events and assign them to the menus.
BUTTONBAR_RED    = event.Event('BUTTONBAR_RED')
BUTTONBAR_GREEN  = event.Event('BUTTONBAR_GREEN')
BUTTONBAR_YELLOW = event.Event('BUTTONBAR_YELLOW')
BUTTONBAR_BLUE   = event.Event('BUTTONBAR_BLUE')

event.MENU_EVENTS['RED']    = BUTTONBAR_RED
event.MENU_EVENTS['GREEN']  = BUTTONBAR_GREEN
event.MENU_EVENTS['YELLOW'] = BUTTONBAR_YELLOW
event.MENU_EVENTS['BLUE']   = BUTTONBAR_BLUE

event.TVMENU_EVENTS['RED']    = BUTTONBAR_RED
event.TVMENU_EVENTS['GREEN']  = BUTTONBAR_GREEN
event.TVMENU_EVENTS['YELLOW'] = BUTTONBAR_YELLOW
event.TVMENU_EVENTS['BLUE']   = BUTTONBAR_BLUE

# Action functions used to perform special actions for the button bar
def advance_tv_guide(arg=0, menuw=None):
    """
    action to advance the tv guide by a number of hours passed in arg.
    """
    tvguide = menuw.menustack[-1]
    new_start_time = tvguide.start_time + (arg * 60 * 60)
    new_end_time =  tvguide.stop_time + (arg * 60 * 60)
    programs = tvguide.guide.GetPrograms(new_start_time+1, new_end_time-1, [ tvguide.start_channel])
    if (len(programs) > 0) and (len(programs[0].programs) > 0):
        new_selected_program = programs[0].programs[0]
    else:
        new_selected_program = None
    tvguide.rebuild(new_start_time,new_end_time, tvguide.start_channel, new_selected_program)
    menuw.refresh()


def send_event_to_menu(arg=None, menuw=None):
    """
    send the event specified in arg to menuw's eventhandler.
    """
    menuw.eventhandler(arg)


# Program Info screen
class ShowProgramDetails:
    """
    Screen to show the details of the TV program
    """
    def __init__(self, menuw):
        tvguide = menuw.menustack[-1]
        prg = tvguide.selected
        if prg is None:
            name = _('No Information Available')
            description = ''
        else:
            name = prg.title
            description =  prg.getattr('time') + u'\n' + prg.desc
        item = MenuItem(name=name)
        item.description = description
        self.visible = True
        self.menuw = menuw
        self.menuw.hide(clear=False)
        rc.app(self)
        skin.draw('tvguideinfo', item)


    def eventhandler(self, event, menuw=None):
        """
        eventhandler
        """
        if event in ('MENU_SELECT', 'MENU_BACK_ONE_MENU'):
            rc.app(None)
            self.menuw.show()
            return True

        return False


def show_program_info(arg=None, menuw =None):
    ShowProgramDetails(menuw)


 # Plugin interface
class PluginInterface(plugin.DaemonPlugin):
    """
    global button bar plugin.
    """
    def __init__(self):
        """
        init the buttonbar
        """
        plugin.DaemonPlugin.__init__(self)
        plugin.register(self, 'buttonbar')
        self.visible = True
        self.bar     = None
        self.barfile = ''
        self.surface = None
        self.colors = ['red', 'green', 'yellow', 'blue']
        self.actions = [None, None, None, None]
        if not hasattr(config, 'BUTTONBAR_TVGUIDE_ACTIONS'):
            self.tvguide_actions = [MenuItem('-1 Day', action= advance_tv_guide, arg= -24),
                                             MenuItem('-6 Hours', action= advance_tv_guide, arg= -6),
                                             MenuItem('+6 Hours', action= advance_tv_guide, arg= 6),
                                             MenuItem('+1 Day', action= advance_tv_guide, arg= 24)]
        else:
            # Process TV Guide buttons
            self.tvguide_actions = [None, None, None, None]
            for index in range(0, len(self.colors)):
                if config.BUTTONBAR_TVGUIDE_ACTIONS.has_key(self.colors[index]):
                    actionstr = config.BUTTONBAR_TVGUIDE_ACTIONS[self.colors[index]]
                    if actionstr == 'record':
                        self.tvguide_actions[index] = MenuItem(_('Record'),
                                                                                  action=send_event_to_menu,
                                                                                  arg= event.TV_START_RECORDING)
                    elif actionstr == 'info':
                        self.tvguide_actions[index] = MenuItem(_('Info'),
                                                                                  action=show_program_info)
                    elif actionstr.startswith('adv:'):
                        hours = eval(actionstr[4:])
                        self.tvguide_actions[index] = MenuItem('Advance %d hours' % hours,
                                                                                  action= advance_tv_guide,
                                                                                  arg= hours)
        # Getting current LOCALE
        try:
            locale.resetlocale()
        except:
            pass


    def config(self):
        """
        Configuration options for the button bar.
        """
        # Available actions for use in the TVGuide are:
        # adv:<hours> - Advance the tv guide <hours> hours.
        # record           - Set the selected program to record.
        # info               - Display more information on the selected program.
        return [('BUTTONBAR_TVGUIDE_ACTIONS',
                    { 'red':'adv:-24',
                       'green':'adv:-6',
                       'yellow':'adv:6',
                       'blue':'adv:24'
                    },
                    'actions to display in the button bar when the TV Guide is visible.')]


    def draw(self, (type, object), osd):
        """
        Draw a background and color buttons
        """
        BUTTON_BAR_HEIGHT = 60
        menu = osd.menu

        actions = self.get_actions(menu)

        if actions is None: # No actions, don't draw the bar.
            self.actions = [None, None, None, None]
            return

        # draw Button bar
        w = osd.width + (2 * osd.x)
        h = osd.y + BUTTON_BAR_HEIGHT
        y = ((osd.y * 2) + osd.height) - h

        f = skin.get_image('idlebar')

        if self.barfile != f:
            self.barfile = f
            try:
                self.bar = transform.scale(image.load(f).convert_alpha(), (w,h))
                self.bar = transform.flip(self.bar, False, True)
            except:
                self.bar = None

        # draw the cached barimage
        if self.bar:
            osd.drawimage(self.bar, (0, y, w, h), background=True)

        # Buttons modified from http://openclipart.org/cchost/media/files/kuba/1988
        # draw the buttons
        buttonwidth = osd.width / 4
        x = osd.x

        for index in range(0, len(self.colors)):
            if actions[index] is not None:
                self.draw_button(osd, x, y, buttonwidth, BUTTON_BAR_HEIGHT, self.colors[index], actions[index])
                self.actions[index] = actions[index]
            else:
                self.actions[index] = None
            x += buttonwidth


    def draw_button(self, osd, x, y, w, h, color, action):
        """
        Draw a color button and associated text.
        """
        iconfilename = os.path.join(config.ICON_DIR, 'misc/' + color + 'button.png' )
        iw,ih = osd.drawimage(iconfilename, (x + 5, y + 7,  -1, -1))

        if isinstance(action, MenuItem):
            string = action.name
        else:
            string = action[1]

        font = osd.get_font('small0')
        osd.drawstring(string, font, None,
                              x = x + 5 + iw, y = y + 5, width = w - iw, height = h - 10,
                              mode = 'soft', align_v='center')


    def eventhandler(self, event, menuw=None):
        """
        Handle color button events.
        """
        action = None	
        result = False

        if event == BUTTONBAR_RED:
            action = self.actions[0]
            result = True
        elif event == BUTTONBAR_GREEN:
            action = self.actions[1]
            result = True
        elif event == BUTTONBAR_YELLOW:
            action = self.actions[2]
            result = True
        elif event == BUTTONBAR_BLUE:
            action = self.actions[3]
            result = True


        if action is None:
           return result

        if isinstance(action, MenuItem):
           action.select(menuw=menuw)
        else:
           action[0](menuw=menuw)

        return result

    def get_actions(self, menu):
        """
        Retrieve the Red/Green/Yellow/Blue actions for supplied menu.
        The actions are returned in an array in the order:
        [red,green,yellow,blue].
        None is returned if no actions are available and the bar should not
        be drawn.
        """
        result = [None, None, None, None]
        found_color_actions = False

        for index in range(0, len(self.colors)):
            if hasattr(menu, self.colors[index] + '_action'):
                found_color_actions = True
                result[index] = eval('menu.' + color + '_action')

        if found_color_actions:
            return result

        if ((isinstance(menu, Menu) and (menu.item_types == 'main')) or
             isinstance(menu, MenuItem)):
            return None

        if isinstance(menu, TVGuide):
            dateformat = config.TV_DATEFORMAT
            timeformat = config.TV_TIMEFORMAT
            if not timeformat:
                timeformat = '%H:%M'
            if not dateformat:
                dateformat = '%d-%b'

            for action in self.tvguide_actions:
                if action.function == advance_tv_guide:
                    newtime = menu.start_time + (action.arg * 60 *60)
                    action.name = Unicode(time.strftime('%s %s' % (dateformat, timeformat),
                                                        time.localtime(newtime)))
            return self.tvguide_actions
        else:
            # Determine the available actions
            if hasattr(menu, 'is_submenu') or (not hasattr(menu, 'selected')):
                    return None

            actions = menu.selected.actions()
            if not actions:
               actions = []

            plugins = plugin.get('item') + plugin.get('item_%s' % menu.selected.type)

            if hasattr(menu.selected, 'display_type'):
                plugins += plugin.get('item_%s' % menu.selected.display_type)

            plugins.sort(lambda l, o: cmp(l._level, o._level))

            for p in plugins:
                for a in p.actions(menu.selected):
                    if isinstance(a, MenuItem):
                        actions.append(a)
                    elif len(a) == 2 or a[2] != 'MENU_SUBMENU':
                        actions.append(a[:2])

            if len(actions) <= 1:
                result = None

            if len(actions) > 1:
                result[0] = actions[0]
            if len(actions) >= 2:
                result[1] = actions[1]
            if len(actions) >= 3:
                result[2] = actions[2]
            if len(actions) == 4:
                result[3] = actions[3]

            # Special case for when there are more than 4 possible actions the last button will 'Enter' the submenu
            if len(actions) > 4:
                result[3] = MenuItem(_("More Options"), action=send_event_to_menu, arg= event.MENU_SUBMENU)
        return result


