# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# ButtonBar plug-in
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
import dialog.dialogs as dialogs
import dialog.widgets as widgets

from tv.tvguide import TVGuide
from tv.programitem import ProgramItem
from item import Item
from menu import MenuItem, Menu
from pygame import image,transform, Surface

# Create the skin_object object
skin_object = skin.get_singleton()

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

 # Plugin interface
class PluginInterface(plugin.DaemonPlugin):
    """
    This plugin adds to the bottom of the display the familiar
    Red/Green/Yellow/Blue buttons found on most TVs and settop boxes.
    The buttons make some actions from the submenu of a item available
    directly.

    To use the button bar add the following line to your local_conf.py:
    | plugin.activate('buttonbar')

    Where the actions mapped to each of the colors can be one of the following:
        - info - Brings up a screen displaying more information than can be displayed
          in the few lines available on the TV guide page.
        - record - Same as the record button.
        - adv:<number> - Special action to allow navigation of the TV Guide,
          <number> can be either positive or negative and is the number of hours
          to go forward/back.
        - now - jumps back to the currently running program

    You can also map the following actions to unused keys of your keyboard
    (For example):

    | KEYMAP[key.K_F7] = 'RED'
    | KEYMAP[key.K_F8] = 'GREEN'
    | KEYMAP[key.K_F11] = 'YELLOW'
    | KEYMAP[key.K_F12] = 'BLUE'
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
        self.colors = config.BUTTONBAR_ORDER

        self.events = []
        for index in self.colors:
            eventname = 'BUTTONBAR_' + index.upper()
            self.events.append(eventname)

        self.actions = [None, None, None, None]
        if not hasattr(config, 'BUTTONBAR_TVGUIDE_ACTIONS'):
            self.tvguide_actions = [MenuItem('-1 Day', action= self.advance_tv_guide, arg= -24),
                                    MenuItem('-6 Hours', action= self.advance_tv_guide, arg= -6),
                                    MenuItem('+6 Hours', action= self.advance_tv_guide, arg= 6),
                                    MenuItem('+1 Day', action= self.advance_tv_guide, arg= 24)]
        else:
            # Process TV Guide buttons
            self.tvguide_actions = [None, None, None, None]
            for index in range(0, len(self.colors)):
                actionstr = ''
                if config.BUTTONBAR_TVGUIDE_ACTIONS.has_key('button' + str(index+1)):
                    actionstr = config.BUTTONBAR_TVGUIDE_ACTIONS['button' + str(index+1)]
                if config.BUTTONBAR_TVGUIDE_ACTIONS.has_key(self.colors[index]):
                    actionstr = config.BUTTONBAR_TVGUIDE_ACTIONS[self.colors[index]]
                

                if actionstr == 'record':
                    self.tvguide_actions[index] = MenuItem(_('Record'),
                                                  action=self.send_event_to_menu,
                                                  arg= event.TV_START_RECORDING)
                elif actionstr == 'enter':
                    self.tvguide_actions[index] = MenuItem(_('More options'),
                                                  action=self.show_options,
                                                  arg=None)
                                                  #action=self.send_event_to_menu,
                                                  #arg= event.MENU_SUBMENU)
                elif actionstr == 'info':
                    self.tvguide_actions[index] = MenuItem(_('Full Description'),
                                                  action=self.show_program_info)
                elif actionstr == 'now':
                    self.tvguide_actions[index] = MenuItem(_('Now'),
                                                  action=self.jump_to_now)

                elif actionstr.startswith('adv:'):
                    hours = eval(actionstr[4:])
                    self.tvguide_actions[index] = MenuItem('Advance %d hours' % hours,
                                                  action= self.advance_tv_guide,
                                                  arg= hours)
                else:
                    msgtext = _('WARNING: ')
                    msgtext+= _('"%s" is not a valid argument for the button bar. ') % actionstr
                    _debug_(msgtext, DERROR)



        # Getting current LOCALE
        try:
            locale.resetlocale()
        except:
            pass

    # Action functions used to perform special actions for the button bar
    def advance_tv_guide(self, arg=0, menuw=None):
        """
        action to advance the tv guide by a number of hours passed in arg.
        """
        tvguide = menuw.menustack[-1]
        tvguide.advance_tv_guide(hours=arg)


    def jump_to_now(self, arg=None, menuw=None):
        """
        action to return to 'now' in the tv guide.
        """
        tvguide = menuw.menustack[-1]
        tvguide.jump_to_now(tvguide.selected)


    def send_event_to_menu(self, arg=None, menuw=None):
        """
        send the event specified in arg to menuw's eventhandler.
        """
        menuw.eventhandler(arg)

    def show_options(self, arg=None, menuw=None):
        """
        show the available options as a overlay menu.
        """
        if arg is None:
            tvguide = menuw.menustack[-1]
            pi = ProgramItem(tvguide, prog=tvguide.selected, context='guide')
            arg = pi.actions()

        menuw.pushmenu(DialogMenu(arg, menuw))
        skin_object.redraw()


    def show_program_info(self, arg=None, menuw=None):
        """
        open the 'Full description' screen
        """
        tvguide = menuw.menustack[-1]
        prg = ProgramItem(tvguide, tvguide.selected, context = 'guide')
        prg.show_description(menuw=menuw)


    def config(self):
        """
        Configuration options for the button bar.
        """
        # Available actions for use in the TVGuide are:
        # adv:<hours> - Advance the tv guide <hours> hours.
        # record           - Set the selected program to record.
        # info               - Display more information on the selected program.
        return [('BUTTONBAR_TVGUIDE_ACTIONS',
                    {  'button1':'adv:-24',
                       'button2':'adv:-6',
                       'button3':'adv:6',
                       'button4':'adv:24'
                    },
                    'actions to display in the button bar when the TV Guide is visible.'),
                ('BUTTONBAR_ORDER',
                    ['red', 'green', 'yellow', 'blue'],
                    'The order the color buttons will appear'),
                ('BUTTONBAR_HEIGHT',
                    60,
                    'The height of the button bar')]


    def draw(self, (type, object), osd):
        """
        Draw a background and color buttons
        """
        bar_height = config.BUTTONBAR_HEIGHT
        menu = osd.menu

        actions = self.get_actions(menu)

        if actions is None: # No actions, don't draw the bar.
            self.actions = [None, None, None, None]
            return

        # draw Button bar
        w = osd.width + (2 * osd.x)
        h = osd.y + bar_height
        y = ((osd.y * 2) + osd.height) - h

        f = skin_object.get_image('idlebar')

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
                self.draw_button(osd, x, y, buttonwidth, bar_height, self.colors[index], actions[index])
            self.actions[index] = actions[index]
            x += buttonwidth


    def draw_button(self, osd, x, y, w, h, color, action):
        """
        Draw a color button and associated text.
        """
        iconfilename = os.path.join(config.ICON_DIR, 'misc/' + color + 'button.png' )
        iw,ih = osd.drawimage(iconfilename, (x + 5, y + 7,  h - 14, h - 14))

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

        for index in range(0, len(self.events)):
            if event == self.events[index]:
                action = self.actions[index]
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

        if hasattr(menu, 'selected'):
            color_object = menu.selected
        else:
            color_object = menu

        for index in range(0, len(self.colors)):
            if hasattr(color_object, self.colors[index] + '_action'):
                found_color_actions = True
                result[index] = eval('color_object.' +  self.colors[index] + '_action')

            if hasattr(color_object, 'button' + str(index+1) + '_action'):
                found_color_actions = True
                result[index] = eval('color_object.button' +  str(index+1) + '_action')

        if found_color_actions:
            return result

        if ((isinstance(menu, Menu) and (menu.item_types == 'main')) or
             isinstance(menu, MenuItem)):
            return None

        if isinstance(menu, TVGuide):
            dateformat = config.TV_DATE_FORMAT
            timeformat = config.TV_TIME_FORMAT
            if not timeformat:
                timeformat = '%H:%M'
            if not dateformat:
                dateformat = '%d-%b'

            for action in self.tvguide_actions:
                if action and action.function == self.advance_tv_guide:
                    newtime = menu.start_time + (action.arg * 60 *60)
                    action.name = Unicode(time.strftime('%s %s' % (dateformat, timeformat),
                                                        time.localtime(newtime)))
            return self.tvguide_actions

        # Make sure this is a menu and not a submenu.
        if hasattr(menu, 'is_submenu') or (not hasattr(menu, 'selected')):
            return result

        # Determine the available actions
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

        for index in range(1, min(len(actions),5)):
            result[index-1] = actions[index]
            print actions[index]


        # Special case for when there are more than 5 possible actions the last button will 'Enter' the submenu
        if len(actions) > 5:
            result[3] = MenuItem(_("More Options"), action=self.show_options, arg=actions)
        return result

class DialogMenu:
    def __init__(self, actions, menuw):
        items = []
        for action in actions:
            if isinstance(action, MenuItem):
                string = action.name
            else:
                string = action[1]
            items.append((string, self.handler, (menuw, action)))
        self.dialog = dialogs.MenuDialog('', items, skin='bboptionsmenu')
        self.dialog.signals['hidden'].connect(self.__hidden)
        self.dialog.menu.signals['selection_changed'].connect(self.__redraw_skin)
        self.menuw = menuw
        self.__do_show = True
        self.selected = DialogMenuSelectedItem(self)

    def eventhandler(self, event):
        return True

    def __hidden(self, dialog):
        if self.__do_show:
            self.menuw.back_one_menu()

    def __redraw_skin(self, menu, menuitem):
        skin_object.redraw()

    def handler(self, dialog, arg):
        self.__do_show = False
        self.dialog.hide()
        menuw, action = arg
        if isinstance(action, MenuItem):
            action.select(menuw=menuw)
        else:
            action[0](menuw=menuw)
        if menuw.menustack[-1] == self:
            menuw.back_one_menu()

    def refresh(self):
        if self.__do_show:
            self.dialog.show()
        else:
            self.menuw.back_one_menu()

class DialogMenuSelectedItem:
    def __init__(self, menu):
        self.menu = menu
        self.type = None

    def getattr(self, name):
        if name == 'name':
            return self.name
        return None

    @property
    def name(self):
        item = self.menu.dialog.menu.get_active_item()
        if item:
            return item.text
        return None
