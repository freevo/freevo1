# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# menu.py - freevo menu handling system
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

import string
import copy

import config
import plugin
import util
import skin
import rc

from gui import sounds
from event import *
from item import Item
from gui import GUIObject, AlertBox


class MenuItem(Item):
    """
    Default item for the menu. It includes one action
    """
    def __init__(self, name='', action=None, arg=None, type=None, image=None, icon=None, parent=None, skin_type=None):
        Item.__init__(self, parent, skin_type=skin_type)
        if name:
            self.name  = Unicode(name)
        if icon:
            self.icon  = icon
        if image:
            self.image = image

        self.function = action
        self.arg      = arg
        self.type     = type


    def __str__(self):
        """
        return the event as string
        """
        s = '"'+self.name+'"'
        if hasattr(self, 'action'):    s += ' action=%s' % self.action
        #if hasattr(self, 'arg') and self.arg: s += ' arg=%s' % self.arg[0]
        if hasattr(self, 'type'):      s += ' type=%s' % self.type
        if hasattr(self, 'image'):     s += ' image=%s' % self.image
        if hasattr(self, 'icon'):      s += ' icon=%s' % self.icon
        if hasattr(self, 'skin_type'): s += ' skin_type=%s' % self.skin_type
        #if hasattr(self, 'parent'):    s += ' parent=%s' % self.parent
        return s


    def __repr__(self):
        """
        return the menu item as a raw string
        """
        s = '<class %s %r>' % (self.__class__, self.name)
        return s


    def actions(self):
        """
        return the default action
        """
        return [ (self.select, self.name, 'MENU_SUBMENU') ]


    def select(self, arg=None, menuw=None):
        """
        call the default acion
        """
        if self.function and callable(self.function):
            self.function(arg=self.arg, menuw=menuw)



class Menu:
    """
    a Menu with Items for the MenuWidget
    """
    def __init__(self, heading, choices, fxd_file=None, umount_all=0, reload_func=None, item_types=None,
        force_skin_layout=-1):

        self.heading = heading
        self.choices = choices          # List of MenuItems
        if len(self.choices):
            self.selected = self.choices[0]
        else:
            self.selected = None
        self.page_start = 0
        self.previous_page_start = []
        self.previous_page_start.append(0)
        self.umount_all = umount_all    # umount all ROM drives on display?
        self.skin_settings = None
        if fxd_file:
            self.skin_settings = skin.load(fxd_file)

        # special items for the new skin to use in the view or info
        # area. If None, menu.selected will be taken
        self.infoitem = None
        self.viewitem = None

        # Called when a child menu returns. This function returns a new menu
        # or None and the old menu will be reused
        self.reload_func       = reload_func
        self.item_types        = item_types
        self.force_skin_layout = force_skin_layout
        self.display_style     = skin.get_display_style(self)

        # How many menus to go back when 'BACK_ONE_MENU' is called
        self.back_one_menu = 1


    def __str__(self):
        """
        return the class as string
        """
        s = '"%s" choices=%d' % (self.heading, len(self.choices))
        return s


    def items_per_page(self):
        """
        return the number of items per page for this skin
        """
        return skin.items_per_page(('menu', self))



class MenuWidget(GUIObject):
    """
    The MenuWidget handles a stack of Menus
    """
    def __init__(self):
        GUIObject.__init__(self)
        self.menustack = []
        self.rows = 0
        self.cols = 0
        self.visible = 1
        self.eventhandler_plugins = None
        self.event_context  = 'menu'
        self.show_callbacks = []
        self.force_page_rebuild = False


    def __str__(self):
        """
        return the class as string
        """
        s = '%s' % (self.label,)
        #s += ', rect=%s' % (self.rect,)
        return s


    def get_event_context(self):
        """
        return the event context
        """
        if self.menustack and hasattr(self.menustack[-1], 'event_context'):
            return self.menustack[-1].event_context
        return self.event_context


    def show(self):
        if not self.visible:
            self.visible = 1
            self.refresh(reload=1)
            for callback in copy.copy(self.show_callbacks):
                callback()
        rc.app(None)


    def hide(self, clear=True):
        if self.visible:
            self.visible = 0
            if clear:
                skin.clear(osd_update=clear)


    def delete_menu(self, arg=None, menuw=None, allow_reload=True):
        if len(self.menustack) > 1:
            self.menustack = self.menustack[:-1]
            menu = self.menustack[-1]

            if not isinstance(menu, Menu):
                return True

            if menu.reload_func and allow_reload:
                reload = menu.reload_func()
                if reload:
                    self.menustack[-1] = reload

            self.init_page()


    def delete_submenu(self, refresh=True, reload=False, osd_message=''):
        """
        Delete the last menu if it is a submenu. Also refresh or reload the
        new menu if the attributes are set to True. If osd_message is set,
        this message will be send if the current menu is no submenu
        """
        if len(self.menustack) > 1 and hasattr(self.menustack[-1], 'is_submenu') and \
               self.menustack[-1].is_submenu:
            if refresh and reload:
                self.back_one_menu(arg='reload')
            elif refresh:
                self.back_one_menu()
            else:
                self.delete_menu()
        elif len(self.menustack) > 1 and osd_message:
            rc.post_event(Event(OSD_MESSAGE, arg=osd_message))


    def back_one_menu(self, arg=None, menuw=None):
        if len(self.menustack) > 1:
            try:
                count = -self.menustack[-1].back_one_menu
            except:
                count = -1

            self.menustack = self.menustack[:count]
            menu = self.menustack[-1]

            if not isinstance(menu, Menu):
                menu.refresh()
                return True

            if skin.get_display_style(menu) != menu.display_style:
                self.rebuild_page()

            if menu.reload_func:
                reload = menu.reload_func()
                if reload:
                    self.menustack[-1] = reload
                self.init_page()
            else:
                self.init_page()

            if arg == 'reload':
                self.refresh(reload=1)
            else:
                self.refresh()


    def goto_main_menu(self, arg=None, menuw=None):
        self.menustack = [self.menustack[0]]
        menu = self.menustack[0]
        self.init_page()
        self.refresh()


    def goto_media_menu(self, media='audio'):
        """
        Go to a main menu item media = 'tv' or 'audio' or 'video' or 'image' or 'games'
        used for events:
            - MENU_GOTO_TVMENU
            - MENU_GOTO_TVGUIDEMENU #doesn't yet work
            - MENU_GOTO_VIDEOMENU
            - MENU_GOTO_AUDIOMENU
            - MENU_GOTO_IMAGEMENU
            - MENU_GOTO_GAMESMENU
            - MENU_GOTO_RADIOMENU
            - MENU_GOTO_SHUTDOWN
        """
        self.menustack = [self.menustack[0]]
        menu = self.menustack[0]
        self.init_page()

        if media == 'shutdown':
            for menuitem in self.menustack[0].choices:
                if self.all_items.index(menuitem) >= self.rows - 1:
                    self.goto_next_page()
                if string.find(str(menuitem), 'shutdown.') > 0:
                    menu.selected = menuitem
                    self.eventhandler(MENU_SELECT)
                    return

        elif media == 'tv.guide':
            menu.selected = self.all_items[len(self.menustack[0].choices)-1]
            for menuitem in self.menustack[0].choices:
                try:
                    if menuitem.arg == ('tv', 0):
                        menu.selected = menuitem
                        self.refresh()
                        self.eventhandler(MENU_SELECT)
                        self.refresh()
                        self.eventhandler(MENU_SELECT)
                        return
                except:
                    return
        level = 0
        for mediaitem in media.split('.'):
            for menuitem in self.menustack[level].choices:
                if config.DEBUG:
                    try:
                        print 'menuitem=%s' % menuitem
                    except:
                        pass
                try:
                    if menuitem.arg[0] == mediaitem:
                        if config.OSD_SOUNDS:
                            try:
                                key = "menu." + media
                                if config.OSD_SOUNDS[key]:
                                    sounds.play_sound(sounds.load_sound(key))
                            except:
                                pass
                        menuitem.select(menuw=self)
                        break
                except AttributeError: # may have no .arg (no media menu)
                    pass
                except TypeError: # .arg may be not indexable
                    pass
            level += 1


    def goto_prev_page(self, arg=None, menuw=None):
        menu = self.menustack[-1]

        if self.cols == 1:
            if menu.page_start != 0:
                menu.page_start = menu.previous_page_start.pop()
            self.init_page()
            menu.selected = self.all_items[0]
        else:
            if menu.page_start - self.cols >= 0:
                menu.page_start -= self.cols
                self.init_page()

        if arg != 'no_refresh':
            self.refresh()


    def goto_next_page(self, arg=None, menuw=None):
        menu = self.menustack[-1]
        self.rows, self.cols = menu.items_per_page()
        items_per_page = self.rows*self.cols

        if self.cols == 1:
            down_items = items_per_page - 1

            if menu.page_start + down_items < len(menu.choices):
                menu.previous_page_start.append(menu.page_start)
                menu.page_start += down_items
                self.init_page()
                menu.selected = self.menu_items[-1]
        else:
            if menu.page_start + self.cols * self.rows < len(menu.choices):
                if self.rows == 1:
                    menu.page_start += self.cols
                else:
                    menu.page_start += self.cols * (self.rows-1)
                self.init_page()

        if arg != 'no_refresh':
            self.refresh()


    def pushmenu(self, menu):
        self.menustack.append(menu)
        if isinstance(menu, Menu):
            menu.page_start = 0
            self.init_page()
            menu.selected = self.all_items[0]
            self.refresh()
        else:
            menu.refresh()


    def refresh(self, reload=0):
        menu = self.menustack[-1]

        if not isinstance(menu, Menu):
            # Do not draw if there are any children
            if self.children:
                return False

            return menu.refresh()

        if self.menustack[-1].umount_all == 1:
            util.umount_all()

        if reload:
            if menu.reload_func:
                reload = menu.reload_func()
                if reload:
                    self.menustack[-1] = reload
            if self.force_page_rebuild:
                self.force_page_rebuild = False
                self.rebuild_page()
            self.init_page()

        skin.draw('menu', self, self.menustack[-1])


    def make_submenu(self, menu_name, actions, item):
        #print 'make_submenu(menu_name=%r, actions=%r, item=%r)' % (menu_name, actions, item)
        items = []
        for a in actions:
            if isinstance(a, Item):
                items.append(a)
            else:
                items.append(MenuItem(a[1], a[0]))
        fxd_file = None

        if item.skin_fxd:
            fxd_file = item.skin_fxd

        for i in items:
            if not hasattr(item, 'is_mainmenu_item'):
                i.image = item.image
            if hasattr(item, 'display_type'):
                i.display_type = item.display_type
            elif hasattr(item, 'type'):
                i.display_type = item.type

        s = Menu(menu_name, items, fxd_file=fxd_file)
        s.is_submenu = True
        self.pushmenu(s)


    def _handle_up(self, menu, event):
        curr_selected = self.all_items.index(menu.selected)
        sounds.play_sound(sounds.MENU_NAVIGATE)
        if curr_selected-self.cols < 0 and \
               menu.selected != menu.choices[0]:
            self.goto_prev_page(arg='no_refresh')
            try:
                if self.cols == 1:
                    curr_selected = self.rows - 1
                elif self.rows != 1:
                    curr_selected = self.all_items.index(menu.selected)
                else:
                    curr_selected+=self.cols
            except ValueError:
                curr_selected += self.cols
        curr_selected = max(curr_selected-self.cols, 0)
        menu.selected = self.all_items[curr_selected]
        self.refresh()
        return


    def _handle_down(self, menu, event):
        curr_selected = self.all_items.index(menu.selected)
        sounds.play_sound(sounds.MENU_NAVIGATE)
        if curr_selected+self.cols > len(self.all_items)-1 and \
               menu.page_start + len(self.all_items) < len(menu.choices):

            self.goto_next_page(arg='no_refresh')
            try:
                if self.cols == 1:
                    curr_selected = 0
                elif self.rows != 1:
                    curr_selected = self.all_items.index(menu.selected)
                else:
                    curr_selected-=self.cols
            except ValueError:
                curr_selected -= self.cols
        curr_selected = min(curr_selected+self.cols, len(self.all_items)-1)
        menu.selected = self.all_items[curr_selected]
        self.refresh()
        return


    def _handle_pageup(self, menu, event):
        # Do nothing for an empty file list
        if not len(self.menu_items):
            return

        curr_selected = self.all_items.index(menu.selected)

        # Move to the previous page if the current position is at the
        # top of the list, otherwise move to the top of the list.
        if curr_selected == 0:
            self.goto_prev_page()
        else:
            curr_selected = 0
            menu.selected = self.all_items[curr_selected]
            self.refresh()
        return


    def _handle_pagedown(self, menu, event):
        # Do nothing for an empty file list
        if not len(self.menu_items):
            return

        if menu.selected == menu.choices[-1]:
            return

        curr_selected = self.all_items.index(menu.selected)
        bottom_index = self.menu_items.index(self.menu_items[-1])

        # Move to the next page if the current position is at the
        # bottom of the list, otherwise move to the bottom of the list.
        if curr_selected >= bottom_index:
            self.goto_next_page()
        else:
            curr_selected = bottom_index
            menu.selected = self.all_items[curr_selected]
            self.refresh()
        return

    def _handle_left(self, menu, event):
        # Do nothing for an empty file list
        if not len(self.menu_items):
            return

        sounds.play_sound(sounds.MENU_NAVIGATE)
        curr_selected = self.all_items.index(menu.selected)
        if curr_selected == 0:
            self.goto_prev_page(arg='no_refresh')
            try:
                curr_selected = self.all_items.index(menu.selected)
                if self.rows == 1:
                    curr_selected = len(self.all_items)
            except ValueError:
                curr_selected += self.cols
        curr_selected = max(curr_selected-1, 0)
        menu.selected = self.all_items[curr_selected]
        self.refresh()
        return


    def _handle_right(self, menu, event):
        # Do nothing for an empty file list
        if not len(self.menu_items):
            return

        sounds.play_sound(sounds.MENU_NAVIGATE)
        curr_selected = self.all_items.index(menu.selected)
        if curr_selected == len(self.all_items)-1:
            self.goto_next_page(arg='no_refresh')
            try:
                curr_selected = self.all_items.index(menu.selected)
                if self.rows == 1:
                    curr_selected -= 1
            except ValueError:
                curr_selected -= self.cols

        curr_selected = min(curr_selected+1, len(self.all_items)-1)
        menu.selected = self.all_items[curr_selected]
        self.refresh()
        return


    def _handle_play_item(self, menu, event):
        action = None
        arg    = None

        sounds.play_sound(sounds.MENU_SELECT)
        try:
            action = menu.selected.action
        except AttributeError:
            actions = menu.selected.actions()
            if not actions:
                actions = []

            # Add the actions of the plugins to the list of actions.  This is needed when a
            # Item class has no actions but plugins provides them. This case happens with an
            # empty disc.
            #
            # FIXME The event MENU_SELECT is called when selecting a submenu entry too. The
            # item passed to the plugin is then the submenu entry instead its parent item. So
            # if we are in a submenu we don't want to call the actions of the plugins.
            # because we'll break some (or all) plugins behavior.  Does that sound correct?

            if config.OSD_SOUNDS:
                if hasattr(menu.selected, 'arg'):
                    try:
                        key = "menu." + menu.selected.arg[0]
                        if config.OSD_SOUNDS[key]:
                            sounds.play_sound(sounds.load_sound(key))
                    except:
                        pass
                else:
                    try:
                        key = "menu." + menu.selected.__class__.__name__
                        if config.OSD_SOUNDS[key]:
                            sounds.play_sound(sounds.load_sound(key))
                    except:
                        pass

            if not hasattr(menu, 'is_submenu'):
                plugins = plugin.get('item') + plugin.get('item_%s' % menu.selected.type)

                if hasattr(menu.selected, 'display_type'):
                    plugins += plugin.get('item_%s' % menu.selected.display_type)

                plugins.sort(lambda l, o: cmp(l._level, o._level))

                for p in plugins:
                    for a in p.actions(menu.selected):
                        if isinstance(a, MenuItem):
                            actions.append(a)
                        else:
                            actions.append(a[:2])

            if actions:
                action = actions[0]
                if isinstance(action, MenuItem):
                    action = action.function
                    arg    = action.arg
                else:
                    action = action[0]
        if not action:
            AlertBox(text=_('No action defined for this choice!')).show()
        else:
            action(arg=arg, menuw=self)
        return


    def _handle_submenu(self, menu, event):
        #if hasattr(menu, 'is_submenu'):
        #    self._handle_play_item(menu, event)
        #    return

        actions = menu.selected.actions()
        force   = False
        if not actions:
            actions = []
            force   = True

        plugins = plugin.get('item') + plugin.get('item_%s' % menu.selected.type)

        if hasattr(menu.selected, 'display_type'):
            plugins += plugin.get('item_%s' % menu.selected.display_type)

        plugins.sort(lambda l, o: cmp(l._level, o._level))

        for p in plugins:
            for a in p.actions(menu.selected):
                if isinstance(a, MenuItem):
                    actions.append(a)
                else:
                    actions.append(a[:2])
                    if len(a) == 3 and a[2] == 'MENU_SUBMENU':
                        a[0](menuw=self)
                        return

        if actions:
            if len(actions) > 1 or force:
                self.make_submenu(menu.selected.name, actions, menu.selected)
            elif len(actions) == 1:
                # if there is only one action, call it!
                action = actions[0]
                arg = None
                if isinstance(action, MenuItem):
                    action = action.function
                    arg    = action.arg
                else:
                    action = action[0]
                action(arg=arg, menuw=self)
        return


    def _handle_call_item_action(self, menu, event):
        _debug_('calling action %s' % event.arg)

        for a in menu.selected.actions():
            if not isinstance(a, Item) and len(a) > 2 and a[2] == event.arg:
                a[0](arg=None, menuw=self)
                return

        plugins = plugin.get('item') + plugin.get('item_%s' % menu.selected.type)

        if hasattr(menu.selected, 'display_type'):
            plugins += plugin.get('item_%s' % menu.selected.display_type)

        for p in plugins:
            for a in p.actions(menu.selected):
                if not isinstance(a, MenuItem) and len(a) > 2 and a[2] == event.arg:
                    a[0](arg=None, menuw=self)
                    return
        _debug_('action %s not found' % event.arg)


    def eventhandler(self, event):
        menu = self.menustack[-1]

        if self.cols == 1 and isinstance(menu, Menu):
            if config.MENU_ARROW_NAVIGATION:
                if event == MENU_LEFT:
                    event = MENU_BACK_ONE_MENU
                elif event == MENU_RIGHT:
                    event = MENU_SELECT

            else:
                if event == MENU_LEFT:
                    event = MENU_PAGEUP
                elif event == MENU_RIGHT:
                    event = MENU_PAGEDOWN

        if self.eventhandler_plugins == None:
            self.eventhandler_plugins = plugin.get('daemon_eventhandler')

        if event == MENU_GOTO_MAINMENU:
            self.goto_main_menu()
            return

        if event == MENU_GOTO_TV:
            self.goto_media_menu("tv")
            return

        if event == MENU_GOTO_TVGUIDE:
            self.goto_media_menu("tv.guide")
            return

        if event == MENU_GOTO_VIDEOS:
            self.goto_media_menu("video")
            return

        if event == MENU_GOTO_MUSIC:
            self.goto_media_menu("audio")
            return

        if event == MENU_GOTO_IMAGES:
            self.goto_media_menu("image")
            return

        if event == MENU_GOTO_GAMES:
            self.goto_media_menu("games")
            return

        if event == MENU_GOTO_RADIO:
            self.goto_media_menu("audio.radio")
            return

        if event == MENU_GOTO_SHUTDOWN:
            self.goto_media_menu("shutdown")
            return

        if event == MENU_BACK_ONE_MENU:
            sounds.play_sound(sounds.MENU_BACK_ONE)
            self.back_one_menu()
            return

        if not isinstance(menu, Menu) and menu.eventhandler(event):
            return

        if event == 'MENU_REFRESH':
            self.refresh()
            return

        if event == 'MENU_REBUILD':
            self.init_page()
            self.refresh()
            return

        if not self.menu_items:
            if event in (MENU_SELECT, MENU_SUBMENU, MENU_PLAY_ITEM):
                self.back_one_menu()
                return
            menu = self.menustack[-2]
            if hasattr(menu.selected, 'eventhandler') and menu.selected.eventhandler:
                if menu.selected.eventhandler(event=event, menuw=self):
                    return
            for p in self.eventhandler_plugins:
                if p.eventhandler(event=event, menuw=self):
                    return
            return

        if not isinstance(menu, Menu):
            if self.eventhandler_plugins == None:
                self.eventhandler_plugins = plugin.get('daemon_eventhandler')

            for p in self.eventhandler_plugins:
                if p.eventhandler(event=event, menuw=self):
                    return

            _debug_('no eventhandler for event %s' % event, 2)
            return

        if event == MENU_UP:
            self._handle_up(menu, event)

        elif event == MENU_DOWN:
            self._handle_down(menu, event)

        elif event == MENU_PAGEUP:
            self._handle_pageup(menu, event)

        elif event == MENU_PAGEDOWN:
            self._handle_pagedown(menu, event)

        elif event == MENU_LEFT:
            self._handle_left(menu, event)

        elif event == MENU_RIGHT:
            self._handle_right(menu, event)

        elif event == MENU_PLAY_ITEM and hasattr(menu.selected, 'play'):
            menu.selected.play(menuw=self)

        elif event == MENU_PLAY_ITEM or event == MENU_SELECT:
            self._handle_play_item(menu, event)

        elif event == MENU_SUBMENU:
            self._handle_submenu(menu, event)

        elif event == MENU_CALL_ITEM_ACTION:
            self._handle_call_item_action(menu, event)

        elif event == MENU_CHANGE_STYLE and len(self.menustack) > 1:
            # did the menu change?
            if skin.toggle_display_style(menu):
                self.rebuild_page()
                self.refresh()
                return

        elif hasattr(menu.selected, 'eventhandler') and menu.selected.eventhandler:
            if menu.selected.eventhandler(event=event, menuw=self):
                return

        for p in self.eventhandler_plugins:
            if p.eventhandler(event=event, menuw=self):
                return

        _debug_('no eventhandler for event %s' % str(event), 2)
        return 0



    def rebuild_page(self):
        menu = self.menustack[-1]

        if not menu:
            return

        # recalc everything!
        current = menu.selected
        try:
            pos = menu.choices.index(current)
        except ValueError, e:
            print 'menu.choices.index(current) failed: %s' % (e)

        menu.previous_page_start = []
        menu.previous_page_start.append(0)
        menu.page_start = 0

        rows, cols = menu.items_per_page()
        items_per_page = rows*cols

        while pos >= menu.page_start + items_per_page:
            self.goto_next_page(arg='no_refresh')

        menu.selected = current
        self.init_page()
        menu.display_style = skin.get_display_style(menu)


    def init_page(self):

        menu = self.menustack[-1]
        if not menu:
            return

        # Create the list of main selection items (menu_items)
        menu_items           = []
        first                = menu.page_start
        self.rows, self.cols = menu.items_per_page()

        for choice in menu.choices[first : first+(self.rows*self.cols)]:
            menu_items.append(choice)

        self.rows, self.cols = menu.items_per_page()

        self.menu_items = menu_items

        if len(menu_items) == 0:
            self.all_items = menu_items + [ MenuItem('Back', self.back_one_menu) ]
        else:
            self.all_items = menu_items

        if not menu.selected in self.all_items:
            menu.selected = self.all_items[0]

        if not menu.choices:
            menu.selected = self.all_items[0]

        rc.post_event(MENU_PROCESS_END)

        # make sure we are in context 'menu'
        _debug_('menu: setting context to %s' % self.event_context, 2)
        rc.set_context(self.event_context)



# register menu to the skin
skin.register('menu', ('screen', 'title', 'subtitle', 'view', 'listing', 'info', 'plugin'))
