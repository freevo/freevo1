# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dialog definition and rendering module for livepause osd
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
# ----------------------------------------------------------------------- */
"""
Module containing the Widget model classes.
A widget is something that the user can navigate to and can have one of the following states:
 - active = The user has navigate to this widget and it has focues.
 - normal = The widget doesn't have focus but is still enabled and can be navigated to.
 - disabled = The widget is not navigatable to.
 - invisible = The widget is not drawn.
"""
import kaa
from pygame.locals import *

class WidgetModel(object):
    """
    The base class for all widgets.
    @ivar parent: The dialog or widget that contains this one.
    @ivar active: Whether this widget has focus.
    @ivar enabled: Whether this widget is navigable.
    @ivar visible: Whether this widget is drawn.
    @ivar signals: Dictionary of signals emitted by this widget. The base class emits 2 signals:
     - activated = The widget has recieved focus.
     - deactivated = The widget has lost focus.
    """
    def __init__(self):
        self.parent = None
        self.active = False
        self.enabled = True
        self.visible = True
        self.signals = kaa.Signals()
        self.signals['activated'] = kaa.Signal()
        self.signals['deactivated'] = kaa.Signal()


    def set_parent(self, parent):
        """
        Set the parent of this widget, either a dialog or another widget.
        @param parent: The parent dialog or widget.
        """
        self.parent = parent


    def redraw(self):
        """
        Request that the dialog containing this widget is redrawn.
        """
        if self.parent:
            self.parent.redraw()


    def set_active(self, active):
        """
        Actitivate/Deactivate this widget.
        @param active: Whether this widget has gained the focus or not.
        """
        if self.active != active:
            self.active = active
            if active:
                self.signals['activated'].emit(self)
            else:
                self.signals['deactivated'].emit(self)


    def handle_event(self, event):
        """
        Process the event supplied.
        @param event: kaa.Event to process.
        @return: True if the event was consumed, False otherwise.
        @rtype: boolean
        """
        return False

    def get_state(self):
        """
        Returns a text string describing the state of the model.
        Used by the skin module when determine how to draw the widget.

        @return A string describing the current state of the widget.
        """
        if self.visible:
            if self.enabled:
                if self.active:
                    return 'active'
                else:
                    return 'normal'
            else:
                return 'disabled'

        return 'invisible'


class ButtonModel(WidgetModel):
    """
    Widget model representing a simple button
    This model emits the following signals in addition to the base Widget signals:
     - pressed = The button has been pressed.
    """
    def __init__(self, text, icon=None):
        """
        Create a new instance.
        @param text: Text to display in the button.
        @param icon: Optional image filename to be displayed.
        """
        super(ButtonModel, self).__init__()
        self.text = text
        self.icon = icon
        self.pressed = False
        self.signals['pressed'] = kaa.Signal()
        self.pressed_timer = kaa.OneShotTimer(self.__unpress)

    def handle_event(self, event):
        if event == 'INPUT_ENTER':
            self.press()
            return True
        return super(ButtonModel, self).handle_event(event)

    def handle_mouse_event(self, event):
        if event.type == MOUSEBUTTONDOWN:
            self.press(False)

        elif event.type == MOUSEBUTTONUP:
            self.__unpress()


    def press(self, keyboard=True):
        """
        Press the button.
        """
        self.pressed = True
        self.redraw()
        if keyboard:
            self.pressed_timer.start(0.2)

    def __unpress(self):
        """
        Called by the timer to set the state to unpressed and emit the pressed signal.
        """
        self.pressed = False
        self.redraw()
        self.signals['pressed'].emit(self)

    def get_state(self):
        state = super(ButtonModel, self).get_state()
        if state == 'active' and self.pressed:
            return 'pressed'
        return state


class ToggleButtonModel(ButtonModel):
    """
    A button that can be in 2 states, selected or unselected.
    This class can be used in combination with the ToggleButtonGroup to
    implement radio buttons.
    This model emits the following signals in addition to the base Widget signals:
     - toggled = The selected state of the button has changed.
    @ivar selected: Whether this button is selected.
    """
    def __init__(self, text):
        """
        Create a new instance.
        @param text: The text to display along with the state of the button.
        """
        super(ToggleButtonModel, self).__init__(text)
        self.selected = False
        self.group = None
        self.signals['toggled'] = kaa.Signal()

    def set_selected(self, selected):
        """
        Set whether this button is selected or not. If the state of the button
        changes this method emits the toggled signal.
        @param selected: True if the button should be selected, False otherwise.
        """
        if selected != self.selected:
            # Don't allow selected button in a group to be deselected.
            if self.group and self.group.selected_button == self and not selected:
                return
            self.selected = selected
            self.signals['toggled'].emit(self, selected)
            self.redraw()

    def press(self):
        self.set_selected(not self.selected)

    def get_state(self):
        state = super(ToggleButtonModel, self).get_state()
        if state in ('normal', 'active', 'disabled'):
            if self.selected:
                state += '_selected'
            else:
                state += '_unselected'

        return state

class ToggleButtonGroup(object):
    """
    This class is used to group ToggleButtonModels together so that when one is
    selected all the others in the group are unselected.
    This class emits the selection_changed signal when the selected button
    changes.
    @ivar buttons: List of buttons managed by this group.
    @ivar selected_button: The currently selected button.
    @ivar signals: Dictionary of signals emitted by this class.
    """
    def __init__(self):
        """
        Create a new instance with initially no buttons.
        """
        self.buttons = []
        self.selected_button = None
        self.signals = kaa.Signals()
        self.signals['selection_changed'] = kaa.Signal()

    def add_button(self, button):
        """
        Add a button to the group of buttons.
        @param button: ToggleButtonModel to add to the group.
        """
        self.buttons.append(button)
        button.group = self
        button.signals['toggled'].connect(self.__button_toggled)
        if self.selected_button is None:
            button.set_selected(True)

    def remove_button(self, button):
        """
        Remove a button from the group of buttons.
        @param button: ToggleButtonModel to remove from the group.
        """
        self.buttons.remove(button)
        button.signals['toggled'].disconnect(self.__button_toggled)

    def __button_toggled(self, from_button, selected):
        """
        Internal function to monitor the state of the buttons and ensure only 1
        is selected.
        Emits the selected_changed signal when the selection changes.
        """
        if selected:
            self.selected_button = from_button
            for button in self.buttons:
                if from_button != button and button.selected:
                    button.set_selected(False)
            self.signals['selection_changed'].emit(self, from_button)



class MenuModel(WidgetModel):
    """
    Widget that displays a vertical list of selectable options.
    @ivar items: List of menu items managed by this menu.
    """
    def __init__(self):
        WidgetModel.__init__(self)
        self.items = []
        self.page = None
        self.offset = 0
        self.active_item = 0
        self.items_per_page = 0
        self.more_up = False
        self.more_down = False

    def handle_event(self, event):
        if event == 'INPUT_ENTER':
            self.items[self.active_item].press()
            return True

        elif event == 'INPUT_UP':
            if self.active_item > 0:
                self.items[self.active_item].active = False
                self.active_item -= 1
                if self.active_item < self.offset:
                    self.offset = self.active_item
                    self.__update_page()
                self.items[self.active_item].active = True
                self.redraw()
            return True

        elif event == 'INPUT_DOWN':
            if self.active_item < len(self.items) - 1:
                self.items[self.active_item].active = False
                self.active_item += 1

                if self.active_item >= self.offset + self.items_per_page:
                    self.offset = self.active_item - (self.items_per_page - 1)
                    self.__update_page()

                self.items[self.active_item].active = True
                self.redraw()
            return True

        elif event == 'INPUT_LEFT':
            if self.active_item != self.offset:
                self.items[self.active_item].active = False
                self.active_item = self.offset
                self.items[self.active_item].active = True
                self.redraw()
            return True

        elif event == 'INPUT_RIGHT':
            if self.active_item != self.offset + self.items_per_page:
                self.items[self.active_item].active = False
                self.active_item = self.offset + self.items_per_page
                if self.active_item >= len(self.items):
                    self.active_item =  len(self.items) - 1
                self.items[self.active_item].active = True
                self.redraw()
            return True

        return super(MenuModel, self).handle_event(event)

    def handle_mouse_event(self, event):
        if event.type == MOUSEMOTION:
            y = event.pos[1] - self.position[1]
            size_per_item = self.size[1] / self.items_per_page
            scroll_height = size_per_item / 4
            if y <= scroll_height  and self.offset >= 1:
                self.offset -= 1
                self.__update_page()
                self.redraw()
            if y >= (self.size[1] - scroll_height) and (self.offset + self.items_per_page) < len(self.items):
                self.offset += 1
                self.__update_page()
                self.redraw()

            idx = (y / size_per_item) + self.offset
            self.items[self.active_item].active = False
            self.active_item = idx
            if self.active_item >= len(self.items):
                self.active_item =  len(self.items) - 1
            self.items[self.active_item].active = True
            self.redraw()
        if event.type == MOUSEBUTTONDOWN or event.type == MOUSEBUTTONUP:
            self.items[self.active_item].handle_mouse_event(event)


    def activate_item(self, item):
        """
        Activate the specified menu item and redraw the dialog.
        @param item: MenuItemModel to be activated.
        """
        try:
            idx = self.items.index(item)
            self.items[self.active_item].active = False
            self.active_item = idx
            self.items[self.active_item].active = True
            self.redraw()
        except ValueError:
            pass

    def add(self, item):
        """
        Adds a new menu item to this menu.
        @param item: The MenuItem to add to this menu.
        """
        item.parent = self
        self.items.append(item)
        self.__update_page()
        self.redraw()

    def remove(self, item):
        """
        Remove a menu item from this menu.
        @param item: The MenuItem to remove.
        """
        item.parent = None
        idx = self.items.index(item)
        if idx <= self.offset:
            self.offset -= 1
        if idx <= self.active_item:
            self.active_item -= 1
        self.items.remove(item)
        self.__update_page()
        self.redraw()

    def remove_all(self):
        """
        Remove all items from this menu.
        """
        for item in self.items:
            item.parent = None
        self.items = []
        self.offset = 0
        self.active_item = 0
        self.__update_page()
        self.redraw()

    def layout(self, items_per_page, position, size):
        """
        Called by the skin to layout this menu.
        @param items_per_page: The number of items that are to be displayed on a page.
        """
        self.position = position
        self.size = size
        self.offset = 0
        self.active_item = 0
        self.items_per_page = items_per_page
        self.items[0].set_active(True)
        for item in self.items[1:]:
            item.set_active(False)

        self.__update_page()

    def __update_page(self):
        """
        Internal method to create the active page of menu items.
        """
        self.page = []
        count = 0
        while count + self.offset < len(self.items) and count < self.items_per_page:
            self.page.append(self.items[self.offset + count])
            count += 1

        self.more_down = self.offset + count < len(self.items)
        self.more_up = self.offset > 0


    def get_page_item(self, index):
        """
        Get a menu item on the active page.
        @param index: The index of the item to retrieve from the page.
        @return: A MenuItemModel or None if there is no model at the specific index.
        """
        if index >= len(self.page):
            return None
        return self.page[index]

    def get_active_item(self):
        """
        Retrieve the active MenuItemModel.
        @return: the active MenuItemModel.
        """
        return self.items[self.active_item]

class MenuItemModel(ButtonModel):
    """
    Simple item to be displayed in a menu.
    """
    def __init__(self, text, icon=None):
        """
        Creates a new instance.
        @param text: Text to be displayed by the item.
        @param icon: Optional image filename to display.
        """
        super(MenuItemModel, self).__init__(text, icon)

    def set_active(self, active):
        pass

    def get_state(self):
        state = super(MenuItemModel, self).get_state()
        if state == 'normal' and self == self.parent.get_active_item():
            return 'highlighted'
        return state

class ToggleMenuItemModel(MenuItemModel):
    """
    Menu item that can either be selected or unselected.
    """
    def __init__(self, text):
        """
        Creates a new instance.
        @param text: Text to be displayed by the item.
        """
        super(ToggleMenuItemModel, self).__init__(text)
        self.selected = False
        self.signals['toggled'] = kaa.Signal()

    def set_selected(self, selected):
        """
        Set whether this
        """
        if selected != self.selected:
            self.selected = selected
            self.signals['toggled'].emit(self, selected)
            self.redraw()

    def press(self, keyboard=True):
        self.set_selected(not self.selected)

    def get_state(self):
        state = super(ToggleMenuItemModel, self).get_state()
        if state in ('normal', 'active', 'disabled', 'highlighted'):
            if self.selected:
                state += '_selected'
            else:
                state += '_unselected'

        return state
