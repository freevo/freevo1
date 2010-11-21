# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# dialogs module for livepause osd
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
Module defining the Dialog models.

Dialogs are displayed on a display and can be passive, they don't process events,
or active, process events and act on them. They all also prioritised, with lower priorities
being hidden when a higher priority dialog is shown, and reshown when the high priority is hidden.
The priority levels in ascending order are:
 - low
 - normal
 - high
"""
import time
import pygame.event
from pygame.locals import *
import rc
import event
import dialog
import config 
import util

import kaa

import skins.osd
from skins.osd.skin import OSDWidget

from widgets import ButtonModel, MenuModel, MenuItemModel

DEBUG_PERFORMANCE = False

REDRAW_DIALOG = event.Event('REDRAW_DIALOG')

class Dialog(object):
    """
    Base class for all dialogs.

    @ivar name: Name of the dialog skin
    @ivar skin: The skin object used to render the dialog.
    @ivar display: The display the dialog is displayed on.
    @ivar duration: The time in seconds that the dialog will be displayed for (float), 0.0 is forever.
    @ivar priority: The priority of the dialog, valid values are:
     - low
     - normal
     - high
    @ivar signals: Dictionary of signals, this class exposes the following:
      - shown - Emitted when the dialog has been prepared, ready to show
      - hidden - Emitted when the dialog has been finished.

    @cvar HIGH_PRIORITY: Constant for high priority.
    @cvar NORMAL_PRIORITY: Constant for normal priority.
    @cvar LOW_PRIORITY: Constant for low priority.
    """
    HIGH_PRIORITY   = 2
    NORMAL_PRIORITY = 1
    LOW_PRIORITY    = 0

    def __init__(self, name, duration):
        """
        Create a new instance.
        @param name: Name of the skin to render.
        @param duration: Time in seconds the dialog should be shown for by default.
        """
        self.name = name
        self._skin = None
        self.display = None
        self.duration = duration
        self.priority = Dialog.NORMAL_PRIORITY
        self.__first_show = True
        self.signals = kaa.Signals()
        self.signals['prepared'] = kaa.Signal()
        self.signals['shown'] = kaa.Signal()
        self.signals['hidden'] = kaa.Signal()
        self.signals['finished'] = kaa.Signal()
        self.updater = None
        self.__update_interval = 0
        self.last_render = 0.0
        if DEBUG_PERFORMANCE:
            self.__render_count = 0
            self.__first_render_time = 0.0
            self.__hide_time = 0.0

    @property
    def visible(self):
        return (self.display is not None) and (self.display.current_dialog == self)

    @property
    def skin(self):
        if self._skin is None:
            self._skin = skins.osd.get_definition(self.name)
        return self._skin

    def __get_update_interval(self):
        return self.__update_interval

    def __set_update_interval(self, interval):
        self.__update_interval = interval

        if self.updater is None and self.visible and interval > 0:
            self.updater = DialogUpdater(self)

        elif self.updater and interval == 0:
            self.updater.stop()
            self.updater = None

    update_interval = property(__get_update_interval, __set_update_interval)

    def show(self, duration=None):
        """
        Request the current display show the dialog.
        @param duration: Time in seconds the dialog should be displayed for, if None uses self.duration.
        """
        if self.display is None:
            self.display = dialog.get_display()
        if duration is None:
            duration = self.duration
        self.display.show_dialog(self, duration)


    def hide(self):
        """
        Remove the dialog from the display it was shown on.
        """
        if self.display:
            self.display.hide_dialog(self)


    def prepare(self):
        """
        Prepare the dialog to be rendered.
        This method emits the shown signal.
        """
        if self.skin:
            self.skin.prepare()
        self.__first_show = True
        self.signals['prepared'].emit(self)

    def render(self):
        """
        Render the dialog.
        @return: An image of the rendered dialog, or None.
        @rtype: kaa.imlib2.Image
        """
        if self.__first_show:
            self.__first_show = False
            if DEBUG_PERFORMANCE:
                self.__first_render_time = time.time()

            self.signals['shown'].emit(self)
            if self.__update_interval > 0:
                if self.updater:
                    self.updater.resume()
                else:
                    self.updater = DialogUpdater(self)

        result = None
        if self.skin:
            if DEBUG_PERFORMANCE:
                self.__render_count += 1
            result = self.skin.render(self.get_info_dict())
            self.last_render = time.time()

        return result

    def hidden(self):
        """
        Called when the display removes the dialog on the screen.
        The dialog may be shown again up until finish() is called.
        """
        if DEBUG_PERFORMANCE:
            self.__hide_time = time.time()
            _debug_('Dialog %s hidden open for %f seconds rendered %d times' % (self.__class__.__name__, self.__hide_time - self.__first_render_time, self.__render_count))

        if self.updater:
            self.updater.pause()

        self.__first_show = True
        self.signals['hidden'].emit(self)

    def finish(self):
        """
        The dialog has been finished with and can free any resources.
        This method emits the finished signal.
        """
        if self.updater:
            self.updater.stop()
            self.updater = None

        if self.skin:
            self.skin.finish()
        self.signals['finished'].emit(self)

    def get_info_dict(self):
        """
        Return the dictionary used to render the skin.
        @return: A dict containing the information used to render the skin.
        """
        return {}

class InputDialog(Dialog):
    """
    Dialog class that when shown changes the input context to 'input'.
    """
    def __init__(self, name, duration):
        super(InputDialog, self).__init__(name, duration)
        self.event_context = 'input'

    def eventhandler(self, event):
        if event in ('STOP', 'INPUT_EXIT'):
            self.hide()
            return True
        return False

class MessageDialog(Dialog):
    """
    Low priority dialog to show a generic string.
    """
    def __init__(self, message):
        """
        Creates a new instance.
        @param message: The message to be displayed.
        """
        super(MessageDialog, self).__init__('message', 3.0)
        self.message = message
        self.priority = Dialog.LOW_PRIORITY

    def get_info_dict(self):
        return {'message': self.message}


class VolumeDialog(Dialog):
    """
    Low priority dialog to display the current volume state.
    """
    def __init__(self):
        """
        Creates a new instance.
        """
        super(VolumeDialog, self).__init__('volume', 3.0)
        self.priority = Dialog.LOW_PRIORITY
        self.level = 0
        self.muted = False
        self.channel = None

    def set_details(self,level, muted, channel):
        """
        Set the details of the current audio status.

        @param level: Main volume level.
        @param muted: True if audio output has been muted, False otherwise.
        @param channel: The channel to show the volume for or None for the main level.
        Valid channels names are:
         - main
         - center
         - surround
         - lfe
        """
        self.level = level
        self.muted = muted

        if not channel:
            channel = 'main'

        self.channel = channel

        if channel == 'center':
            self.channel_name = _('Center')
        elif channel == 'surround':
            self.channel_name = _('Surround')
        elif channel == 'lfe':
            self.channel_name = _('LFE')
        else:
            self.channel_name = _('Volume')

    def get_info_dict(self):
        return {'volume'      : self.level,
                'muted'       : self.muted,
                'channel'     : self.channel,
                'channel_name': self.channel_name
                }

class PlayStateDialog(Dialog):
    """
    Low priority dialog to display play state and time information.
    """
    def __init__(self, state, item, get_time_info=None):
        """
        Creates a new instance.

        @param state: The play state can be one of the following:
         - play
         - pause
         - rewind
         - fastforward
         - seekback
         - seekforward
         - slow
         - fast
         - info
        @param get_time_info: A function to call to retrieve information about the
        current position and total play time, or None if not available. The function
        will return a tuple of elapsed time, total time and percent through the file.
        Both total time and percent position are optional.
        """
	super(PlayStateDialog, self).__init__('play_state', 3.0)
        self.priority = Dialog.LOW_PRIORITY
        self.state = state
        self.item = item
        self.get_time_info = get_time_info
        self.update_interval = 1.0

    def get_info_dict(self):
        time_info = None

        current_time = 0
        current_time_str = ''
        total_time = 0
        total_time_str = ''
        percent_pos = 0.0
        percent_str = ''

        try:
            channel = self.item.getChannel()
            mode = 'tv'
        except AttributeError:
            mode = 'video'


        if self.get_time_info:
            time_info = self.get_time_info()

        if time_info:
            current_time = time_info[0]
            current_time_hours = current_time / (60 * 60)
            current_time_minutes = (current_time / 60) - (current_time_hours * 60)
            current_time_seconds = current_time - (((current_time_hours * 60) + current_time_minutes) * 60)
            current_time_str = '%02d:%02d:%02d' % (current_time_hours, current_time_minutes, current_time_seconds)

            if len(time_info) > 1:
                total_time = time_info[1]
                total_time_hours = total_time / (60 * 60)
                total_time_minutes = (total_time / 60) - (total_time_hours * 60)
                total_time_seconds = total_time - (((total_time_hours * 60) + total_time_minutes) * 60)

                total_time_str   = '%02d:%02d:%02d' % (total_time_hours, total_time_minutes, total_time_seconds)

                if len(time_info) > 2:
                    percent_pos = time_info[2]
                else:
                    if total_time > 0:
                        percent_pos = float(current_time) / float(total_time)
                    else:
                        percent_pos = 0.0
                percent_str = '%d%%' % (percent_pos * 100)

        attr = {}
        if mode == 'video':
            if self.item.parent.type == 'video':
                attr['title'] = self.item.parent.name
            else:
                attr['title'] = self.item.name
            if not attr['title']:
                attr['title'] = "Not Available"

            attr['tagline'] = self.item.getattr('tagline')
            if not attr['tagline'] and self.item.parent.type == 'video':
                attr['tagline'] = self.item.parent.getattr('tagline')
            if not attr['tagline']:
                attr['tagline'] = None

            attr['image'] = self.item.image
	    # Skip thumbnails
	    if attr['image'] and attr['image'].endswith('.raw'):
		attr['image'] = None
            if not attr['image']:
		attr['image'] = self.item.parent.image
	    if not attr['image']:	
                attr['image'] = "nocover.png" 
            _debug_('Cover image for %s is %s' % (self.item.filename, attr['image']))

            attributes = ['year', 'genre', 'rating', 'runtime' ]
            for attribute in attributes:
                attr[attribute] = self.item.getattr(attribute)
                if not attr[attribute] and self.item.parent.type == 'video':
                    attr[attribute] = self.item.parent.getattr(attribute)
                if not attr[attribute]:
                    attr[attribute] = "Not Available"
                attr[attribute] = attribute.title() + ": " + attr[attribute]
        else:
            channel_number = self.item.getChannelNum()
            channel_logo = 'cover_tv.png'

            channel_id, channel_name, channel_info = self.item.getChannelInfo()

            attr['title'] = channel_name
            attr['image'] = channel_logo
            attr['tagline'] = channel_info
            attr['year'] = None
            attr['genre'] = None
            attr['rating'] = None
            attr['runtime'] = None

        now = time.localtime()
        if config.CLOCK_FORMAT:
            format = config.CLOCK_FORMAT
        else:
            format ='%a %d %H:%M'

        time_str = time.strftime(format, now)
        date_str = time.strftime("%Y/%m/%y", now)

        return {'state': self.state,
                'title': attr['title'],
                'image': attr['image'],
                'tagline': attr['tagline'],
                'year': attr['year'],
                'genre': attr['genre'],
                'rating': attr['rating'],
                'runtime': attr['runtime'],
                'time_raw' : now,
                'time': time_str,
                'date': date_str,
                'current_time': current_time,
                'total_time': total_time,
                'current_time_str': current_time_str,
                'total_time_str': total_time_str,
                'percent': percent_pos,
                'percent_str': percent_str,
                }

class WidgetDialog(InputDialog):
    """
    Dialog containing widgets that can be navigated by the user and change their state.
    """
    def __init__(self, skin, widgets, info=None):
        """
        Creates a new instance.
        @param skin: The name of the skin to use to render the dialog.
        @param widgets: A dict containing the names and model instances of the widgets.
        @param info: Optional dict containing information used to render the skin.
        """
        InputDialog.__init__(self, skin, 0.0)
        self.info = info
        self.widgets = widgets
        for widget in widgets.values():
            widget.set_active(False)
            widget.set_parent(self)
            widget.signals['activated'].connect(self.__widget_activate)

        self.navigation_map = {}
        self.set_navigation_map()

        self.selected_widget = None
        self.processing_event = False
        self.force_redraw = False
        self.exit_hides_dialog = False

    def redraw(self):
        """
        Request that the dialog be redrawn.
        """
        #_stack_('Processing events? %r' % self.processing_event )
        if self.processing_event:
            self.force_redraw = True
        else:
            rc.post_event(event.Event(REDRAW_DIALOG, self))

    def __widget_activate(self, widget):
        """
        Function to ensure that when a widget is activate that the previous
        active widget is deactivated.
        @param widget: The widget that was activated.
        """
        if self.selected_widget:
            self.selected_widget.set_active(False)

        self.selected_widget = widget
        if self.visible:
            self.redraw()

    def eventhandler(self, event):
        self.processing_event = True

        handled = False

        if self.selected_widget:
            handled = self.selected_widget.handle_event(event)

        if not handled:
            if self.exit_hides_dialog and event in ('INPUT_EXIT', 'STOP'):
                self.hide()
                self.force_redraw = False
                handled = True
            else:
                navigation = self.get_navigation_for(self.selected_widget)
                next_widget = None

                if event == 'INPUT_LEFT':
                    next_widget = navigation[0]

                elif event == 'INPUT_RIGHT':
                    next_widget = navigation[1]

                elif event == 'INPUT_UP':
                    next_widget = navigation[2]

                elif event == 'INPUT_DOWN':
                    next_widget = navigation[3]

                if next_widget:
                    next_widget.set_active(True)
                    handled = True


        if not handled:
            handled = super(WidgetDialog, self).eventhandler(event)

        self.processing_event = False

        if self.force_redraw:
            self.redraw()
            self.force_redraw = False

        return handled

    def handle_mouse_event(self, evt):
        widget = self.skin.get_widget_at(evt.pos)

        if widget is None:
            return
        new_pos = (evt.pos[0] - self.skin.position[0], evt.pos[1] - self.skin.position[1])
        evt_dict = {'pos':new_pos}
        if evt.type == MOUSEMOTION:
            evt_dict['rel'] = evt.rel
            evt_dict['buttons'] = evt.buttons
        if evt.type in (MOUSEBUTTONDOWN , MOUSEBUTTONUP):
            evt_dict['button'] = evt.button
        evt = pygame.event.Event(evt.type, evt_dict)
        if widget in self.widgets:
            widget_model = self.widgets[widget]
            if evt.type == MOUSEMOTION:
                widget_model.set_active(True)
            if hasattr(widget_model, 'handle_mouse_event'):
                widget_model.handle_mouse_event(evt)

    def get_info_dict(self):
        info_dict = None

        if self.info:
            if callable(self.info):
                info_dict = self.info()
            else:
                info_dict = self.info.copy()

        if info_dict is None:
            info_dict = {}

        for name, widget in self.widgets.items():
            info_dict[name] = widget

        info_dict['dialog'] = self

        return info_dict

    def set_navigation_map(self):
        """
        Sets the navigation map used by the dialog from the skin.
        """
        for obj in self.skin.objects:
            if isinstance(obj, OSDWidget) and obj.name in self.widgets:
                navigation_widgets = []
                if obj.navigation is not None:
                    for name in obj.navigation:
                        if name in self.widgets:
                            navigation_widgets.append(self.widgets[name])
                        else:
                            navigation_widgets.append(None)

                self.navigation_map[self.widgets[obj.name]] = tuple(navigation_widgets)

    def get_navigation_for(self, widget):
        """
        Returns a tuple containing widgets to navigate to in the following order:
         - left
         - right
         - up
         - down
        @return: A tuple of length 4 containing widgets to navigate to or None if the direction is not navigable.
        @rtype: tuple
        """
        if widget in self.navigation_map:
            return self.navigation_map[widget]

        return (None, None, None, None)

class ButtonDialog(WidgetDialog):
    """
    Dialog that contains several buttons, when one of these button is selected
    the dialog is closed.
    """

    QUESTION_TYPE = 'question'
    ERROR_TYPE = 'error'
    WARNING_TYPE = 'warning'

    def __init__(self, buttons, message, type=None, skin=None, widgets=None, info=None):
        """
        Create a new instance

        @param buttons: A sequence container tuples of button text and
        function to call when the button is pressed (and optional whether this
        button should be active)
        @param message: The message text to display.
        @param type: One of the follow info, warning, error, question or None
        @param skin: A custom dialog skin to use or None to use <#Buttons>buttons.
        @return: The dialog instance that was shown.
        @rtype: WidgetDialog
        """
        if widgets is None:
            widgets = {}

        self.type = type
        self.message = message

        to_select = None
        if len(buttons) == 1:
            button = ButtonModel(buttons[0][0])
            button.signals['pressed'].connect(self._button_pressed_handler)
            button.handler = buttons[0][1]
            widgets['button'] = button
            to_select = button
        else:
            for index in range(0,len(buttons)):
                button = ButtonModel(buttons[index][0])
                button.signals['pressed'].connect(self._button_pressed_handler)
                button.handler = buttons[index][1]
                widgets['button%d' % (index + 1)] = button

                if len(buttons[index]) > 2 and buttons[index][2]:
                    to_select = button
            if to_select is None:
                to_select = button
        if skin is None:
            skin = self._find_best_skin(len(buttons), type)


        super(ButtonDialog,self).__init__(skin, widgets, info)
        if to_select:
            to_select.set_active(True)

    def get_info_dict(self):
        info = super(ButtonDialog, self).get_info_dict()
        info['message'] = self.message
        info['dialog_type'] = self.type
        return info

    def _button_pressed_handler(self, button):
        """
        Internal function that is called when a button is pressed.
        This function first hides the dialog and then calls the buttons
        callback function.
        @param button: The button that was pressed.
        """
        self.hide()
        if button.handler:
            button.handler()

    def _find_best_skin(self, button_count, type):
        """
        Find the best matching skin name based on the number of buttons and type.
        @param button_count: Number of buttons.
        @param type: The type of the dialog (error, warning, question...)
        @return: A name to use for the skin.
        """

        name = '%dbutton' % button_count
        result = name
        if type:
            for skin_name in ('%s_type_%s' % (name, type), '%s_type' % name):
                if skins.osd.get_definition(skin_name):
                    result = skin_name
                    break
        return result

class MenuDialog(WidgetDialog):
    """
    Dialog that contains a menu widget.
    """
    def __init__(self, title, items, skin='menu'):
        menu = MenuModel()
        for item in items:
            if isinstance(item, MenuItemModel):
                menu.add(item)
            else:
                text, handler, arg = item
                menu_item = MenuItemModel(text)
                menu_item.handler = handler
                menu_item.arg = arg
                menu_item.signals['pressed'].connect(self._handle_pressed)
                menu.add(menu_item)
        super(MenuDialog, self).__init__(skin, {'menu':menu}, {'title':title})
        menu.set_active(True)
        self.menu = menu
        self.exit_hides_dialog = True

    def update(self, title=None, items=None):
        if title is not None:
            self.info = {'title':title}
        if items is not None:
            menu = self.widgets['menu']
            menu.remove_all()
            for item in items:
                if isinstance(item, MenuItemModel):
                    menu.add(item)
                else:
                    text, handler, arg = item
                    menu_item = MenuItemModel(text)
                    menu_item.handler = handler
                    menu_item.arg = arg
                    menu_item.signals['pressed'].connect(self._handle_pressed)
                    menu.add(menu_item)

    def _handle_pressed(self, item):
        if hasattr(item, 'arg'):
            arg = item.arg
        else:
            arg = None
        item.handler(self, arg)

class ProgressDialog(Dialog):
    """
    Dialog to display progress of an operation.
    Contains a message, percent progress display and progress text.
    """

    INDETERMINATE_UPDATE = 0.03
    INDETERMINATE_SIZE = 0.25
    INDETERMINATE_INC = 0.05

    def __init__(self, message, progress_text=u'', progress_percent=0.0, indeterminate=False):
        super(ProgressDialog, self).__init__('progress', 0)
        self.message = message
        self.progress_text = progress_text
        self.progress_percent = progress_percent
        self.indeterminate = False
        self.last_update = 0
        self.indeterminate_pos = 0.0
        self.indeterminate_dir = ProgressDialog.INDETERMINATE_INC
        self.indeterminate_size = ProgressDialog.INDETERMINATE_SIZE
        if indeterminate:
            self.set_indeterminate(True)

    def set_indeterminate(self, indeterminate):
        if  self.indeterminate != indeterminate:
            self.indeterminate = indeterminate

            if indeterminate:
                self.last_update = 0
                self.indeterminate_pos = 0.00
                self.indeterminate_dir = ProgressDialog.INDETERMINATE_INC
                self.update_interval = ProgressDialog.INDETERMINATE_UPDATE
            else:
                self.update_interval = 0.0

            if self.visible:
                self.show()

    def update_progress(self, progress_text, progress_percent):
        self.progress_text = progress_text
        self.progress_percent = progress_percent
        if self.visible:
            self.show()

    def get_info_dict(self):
        dict = {'message'          : self.message,
                'progress_text'    : self.progress_text}
        if self.indeterminate:
            now = time.time()
            if now - self.last_update >= ProgressDialog.INDETERMINATE_UPDATE:
                self.indeterminate_pos += self.indeterminate_dir
                if self.indeterminate_pos >= (1.0 - self.indeterminate_size):
                    self.indeterminate_dir = -ProgressDialog.INDETERMINATE_INC
                    self.indeterminate_pos = (1.0 - self.indeterminate_size)

                if self.indeterminate_pos < 0.0:
                    self.indeterminate_dir = ProgressDialog.INDETERMINATE_INC
                    self.indeterminate_pos = 0.0

                self.last_update = now
            dict['progress_percent'] = (self.indeterminate_pos, self.indeterminate_size)
        else:
            dict['progress_percent'] = self.progress_percent
        return dict

class DialogUpdater(object):
    def __init__(self, dialog):
        import pygame.time

        self.dialog = dialog
        self.state = 'running'
        self.timer = kaa.OneShotTimer(self.__update_dialog)
        self.timer.start(self.dialog.update_interval)
        self.delay = self.dialog.update_interval
        self.clock = pygame.time.Clock()

    def pause(self):
        self.timer.stop()


    def resume(self):
        clock.tick()
        self.start(self.delay)

    def stop(self):
        self.timer.stop()

    def __update_dialog(self):
        self.dialog.display.redraw_dialog(self.dialog)
        self.delay = self.dialog.update_interval - (self.clock.tick() / 1000.0)
        self.timer.start(self.delay)
