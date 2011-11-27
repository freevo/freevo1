# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# OSD skin designer
# -----------------------------------------------------------------------
# $Id$
#
# Notes:
#
#
# Todo:
#
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
import logging
logger = logging.getLogger("freevo.helpers.osddesigner")
from skins.osd.designer import WidgetStyleObject
from skins.osd.designer import WidgetStateObject
import skins.osd.skin
from dialog.widgets import MenuModel
import sys
import traceback
import os
import os.path
import re
import threading

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.gdk
import gtk.glade

import config

import pickle
from time import localtime
from time import time

from dialog.widgets import *
from skins.osd.designer import *

IMAGE_FILE_REGEX = re.compile('.*\.((png)|(jpe?g))$')

class ThemeTreeModel(gtk.GenericTreeModel):
    def __init__(self):
        super(gtk.GenericTreeModel, self).__init__()
        self.theme = ThemeObject()

    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST

    def on_get_n_columns(self):
        return 1

    def on_get_column_type(self, index):
        return gobject.TYPE_PYOBJECT

    def on_get_iter(self, path):
        obj = self.theme
        try:
            for element in path[1:]:
                i = element
                obj = obj.children[i]
            return obj
        except:
            traceback.print_exc()
        return None

    def on_get_path(self, rowref):
        obj = rowref
        path = ()
        while obj.parent:
            segment = obj.parent.children.index(obj)
            path = (segment,) + path
            obj = obj.parent
        path = (0,) + path
        return path

    def on_get_value(self, rowref, column):
        return rowref

    def on_iter_next(self, rowref):
        if rowref is None:
            return self.theme
        if rowref is self.theme:
            return None
        try:
            i = rowref.parent.children.index(rowref)
            return rowref.parent.children[i + 1]
        except IndexError:
            return None

    def on_iter_children(self, parent):
        if parent is None:
            return self.theme
        if parent.children is None:
            return None
        return parent.children[0]

    def on_iter_has_child(self, rowref):
        if rowref is None:
            rowref = self.theme
        return rowref.children is not None and len(rowref.children) > 0

    def on_iter_n_children(self, rowref):
        if rowref is None:
            return 1
        if rowref.children is None:
            return 0
        return len(rowref.children)

    def on_iter_nth_child(self, parent, n):
        if parent is None:
            if n == 0:
                return self.theme
            else:
                return None
        if parent.children is None:
            return None

        return parent.children[n]

    def on_iter_parent(self, child):
        return child.parent

    def load(self, filename):
        self.theme.load(filename)

    def save(self, filename):
        self.theme.save(filename)

    def add(self, parent, child):
        parent.add_child(child)
        return self.__child_added(parent, child)

    def insert(self, parent, index, child):
        parent.insert_child(index, child)
        return self.__child_added(parent, child)

    def __child_added(self, parent, child):
        path = self.on_get_path(child)
        iter = self.create_tree_iter(child)
        self.row_inserted(path, iter)
        if child.children:
            self.row_has_child_toggled(path, iter)

        if len(parent.children) == 1:
            path = self.on_get_path(parent)
            iter = self.create_tree_iter(parent)
            self.row_has_child_toggled(path, iter)
        return path

    def remove(self, child):
        parent = child.parent
        path = self.on_get_path(child)
        self.row_deleted(path)
        parent.remove_child(child)
        return path

    def get_object_path(self, obj):
        return self.on_get_path(obj)


class ImageFileWidget(gtk.HBox):
    def __init__(self, choose_image, changed_cb):
        super(ImageFileWidget, self).__init__()
        self.choose_image = choose_image
        self.changed_cb = changed_cb
        self.entry = gtk.Entry()
        self.button = gtk.Button('...')
        self.button.connect('clicked', self.on_button_clicked)
        self.entry.connect('focus-out-event', self.on_call_callback)
        self.entry.connect('activate', self.on_call_callback)
        self.entry.connect('changed', self.on_call_callback)
        self.pack_start(self.entry)
        self.pack_end(self.button, expand=False)
        self.filter = gtk.FileFilter()
        self.filter.set_name('Images')
        self.filter.add_pattern('*.png')
        self.filter.add_pattern('*.jpg')
        self.filter.add_pattern('*.jpeg')

    def on_button_clicked(self, *args):
        image_name = self.choose_image()
        if image_name:
            self.entry.set_text(image_name)

    def get_text(self):
        return self.entry.get_text()

    def set_text(self, text):
        self.entry.set_text(text)

    def on_call_callback(self, *args):
        self.changed_cb(self)

    @staticmethod
    def on_file_widget_chooser_delete(*args):
        ImageFileWidget.chooser.hide()
        return True

class UndoableAction(object):
    def __init__(self, name):
        self.name = name # Name of the action

    def undo(self):
        pass

    def redo(self):
        pass

class MoveAction(UndoableAction):
    def __init__(self, obj, original_pos, new_pos):
        super(MoveAction, self).__init__('Move')
        self.obj = obj
        self.original_pos = original_pos
        self.new_pos = new_pos

    def undo(self):
        self.obj.set_position(*self.original_pos)

    def redo(self):
        self.obj.set_position(*self.new_pos)

class ResizeAction(UndoableAction):
    def __init__(self, obj, original_size, new_size):
        super(ResizeAction, self).__init__('Resize')
        self.obj = obj
        self.original_size = original_size
        self.new_size = new_size

    def undo(self):
        self.obj.set_size(*self.original_size)

    def redo(self):
        self.obj.set_size(*self.new_size)

class PropertyChangeAction(UndoableAction):
    def __init__(self, obj, prop, prop_text, original_value, new_value):
        super(PropertyChangeAction, self).__init__('Change ' + prop_text)
        self.obj = obj
        self.prop = prop
        self.original_value = original_value
        self.new_value = new_value

    def undo(self):
        self.obj.set_prop(self.prop, self.original_value)

    def redo(self):
        self.obj.set_prop(self.prop, self.new_value)

class InsertAction(UndoableAction):
    def __init__(self, parent, obj):
        super(InsertAction, obj).__init__('Insert ' + obj.type)
        self.parent = parent
        self.obj = obj

    def undo(self):
        self.parent.remove_child(self.obj)

    def redo(self):
        self.parent.add_child(self.obj)

class DeleteAction(UndoableAction):
    def __init__(self, model, parent, obj, index):
        super(DeleteAction, self).__init__('Delete ' + obj.type)
        self.model = model
        self.parent = parent
        self.obj = obj
        self.index = index

    def undo(self):
        self.model.insert(self.parent, self.index, self.obj)

    def redo(self):
        self.model.remove(self.obj)


RESIZE_SQUARE_SIZE = 7
class Designer:
    def __init__(self, filename=None):
        gladeObject = gtk.glade.XML(os.path.join(config.SHARE_DIR, 'osddesigner/osddesigner.glade'))

        gladeObject.signal_autoconnect(self)
        widgets = gladeObject.get_widget_prefix('')
        for widget in widgets:
            exec("self.%s = widget" % widget.name)

        column = gtk.TreeViewColumn('Name',gtk.CellRendererText(), text=0)
        self.info_treeview.append_column(column)
        column = gtk.TreeViewColumn('Value',gtk.CellRendererText(), text=1)
        self.info_treeview.append_column(column)

        cell = gtk.CellRendererPixbuf()
        column = gtk.TreeViewColumn("Type", cell)
        column.set_cell_data_func(cell, self.get_cell_type)
        self.osds_treeview.append_column(column)

        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name",cell)
        column.set_cell_data_func(cell, self.get_cell_name)
        self.osds_treeview.append_column(column)

        cell = gtk.CellRendererText()
        self.images_dir_combobox.pack_start(cell)
        self.images_dir_combobox.add_attribute(cell, 'text', 0)
        self.images_model = gtk.ListStore(gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING)

        self.images_iconview.set_model(self.images_model)
        self.images_iconview.set_pixbuf_column(0)
        self.images_iconview.set_text_column(1)

        self.add_object_togglebuttons = (
                                         (self.text_togglebutton, TextObject),
                                         (self.image_togglebutton, ImageObject),
                                         (self.percent_togglebutton, PercentObject),
                                         (self.widget_togglebutton, WidgetObject),
                                         (self.menu_togglebutton, MenuObject),
                                         )
        self.insert_object_class = None
        self.updating_values = False

        self.statusbar_context_id = self.statusbar.get_context_id('Designer')
        self.open_filechooser = gtk.FileChooserDialog('Open theme',
                                            None,
                                            gtk.FILE_CHOOSER_ACTION_OPEN,
                                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.open_filechooser.set_default_response(gtk.RESPONSE_OK)
        self.open_filechooser.connect('delete-event',self.on_filechooser_delete_event)

        self.saveas_filechooser = gtk.FileChooserDialog('Save theme as...',
                                            None,
                                            gtk.FILE_CHOOSER_ACTION_SAVE,
                                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                             gtk.STOCK_SAVE_AS, gtk.RESPONSE_OK))
        self.saveas_filechooser.set_default_response(gtk.RESPONSE_OK)
        self.saveas_filechooser.connect('delete-event',self.on_filechooser_delete_event)
        filter = gtk.FileFilter()
        filter.set_name('OSD Skin')
        filter.add_pattern('*.fxd')
        self.fxd_file_filter = filter

        self.background_filechooser = gtk.FileChooserDialog('Select background',
                                            None,
                                            gtk.FILE_CHOOSER_ACTION_OPEN,
                                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.background_filechooser.set_default_response(gtk.RESPONSE_OK)
        self.background_filechooser.connect('delete-event',self.on_filechooser_delete_event)
        filter = gtk.FileFilter()
        filter.set_name('Images')
        filter.add_pattern('*.png')
        filter.add_pattern('*.bmp')
        filter.add_pattern('*.jpg')
        filter.add_pattern('*.jpeg')
        self.background_filechooser.add_filter(filter)
        self.image_file_filter = filter
        self.background_model = gtk.ListStore(gobject.TYPE_STRING)
        self.dialog_bg_combobox.set_model(self.background_model)
        self.dialog_bg_combobox.set_text_column(0)
        self.background_pixbuf = None
        self.show_dialog_outline = False
        self.set_clipboard_obj(None)

        self.recent_manager = gtk.recent_manager_get_default()
        self.recent_menu = gtk.RecentChooserMenu(self.recent_manager)
        self.recent_menuitem.set_submenu(self.recent_menu)
        filter = gtk.RecentFilter()
        filter.add_pattern('*.fxd')
        self.recent_menu.set_filter(filter)
        self.recent_menu.connect('item-activated', self.on_recent_menu_item_activated)

        cwd = os.getcwd()
        os.chdir(os.path.join(config.SHARE_DIR, 'osddesigner'))
        self.type_pixbufs = {}
        for type in ['theme', 'dialog', 'text', 'image', 'percent', 'widget', 'menu', 'font', 'color', 'style', 'state']:
            self.type_pixbufs[type] = gtk.gdk.pixbuf_new_from_file_at_size(type + '.png', 16, 16)

        os.chdir(cwd)

        self.load_settings()
        skins.osd.skin.report_error = self.skin_error

        if filename is None:
            self.new_theme()
        else:
            self.unsaved_flag = False
            self.load_theme(filename)


    #--------------------------------------------------------------------------
    # GUI Signals
    #--------------------------------------------------------------------------
    def on_main_window_delete_event(self, *args):
        if self.quit():
            return False
        return True


    def on_filechooser_delete_event(self, widget, evt):
        widget.hide()
        return True

    def on_dialog_button_clicked(self, *args):
        self.add_theme_object(DialogObject())

    def on_dialogchild_add_toggled(self, togglebutton):
        if togglebutton.get_active():
            for tb, obj_class in self.add_object_togglebuttons:
                if tb == togglebutton:
                    self.insert_object_class = obj_class
                    continue
                if tb.get_active():
                    tb.set_active(False)
            self.select_toolbutton.set_active(False)
        else:
            selected = None
            for tb, obj_class in self.add_object_togglebuttons:
                if tb.get_active():
                    selected = tb
            if selected is None:
                self.select_toolbutton.set_active(True)
                self.insert_object_class = None

    def on_select_toolbutton_toggled(self, *args):
        if self.select_toolbutton.get_active():
            for tb,obj_class in self.add_object_togglebuttons:
                if tb.get_active():
                    tb.set_active(False)
            self.insert_object_class = None

    def on_font_button_clicked(self, *args):
        self.add_theme_object(FontObject())

    def on_color_button_clicked(self, *args):
        self.add_theme_object(ColorObject())

    def on_style_button_clicked(self, *args):
        self.new_style_name_entry.set_text('')
        self.new_style_type_combobox.set_active(0)
        response = self.new_style_dialog.run()
        self.new_style_dialog.hide()
        if response == 1:
            obj = WidgetStyleObject()
            obj.set_prop('name', self.new_style_name_entry.get_text())
            type = self.new_style_type_combobox.get_active_text()
            if type == 'Button' or type == 'MenuItem':
                states_to_create = ['normal', 'active', 'disabled', 'pressed']
                if type == 'MenuItem':
                    states_to_create.append('highlighted')
            elif type == 'Togglebutton' or type == 'ToggleMenuItem':
                states_to_create = ['normal_selected', 'normal_unselected',
                                    'active_selected', 'active_unselected',
                                    'disabled_selected', 'disabled_unselected']
                if type == 'ToggleMenuItem':
                    states_to_create += ['highlighted_selected', 'highlighted_unselected']
            elif type == 'Menu':
                states_to_create = ['normal', 'active', 'disabled']
            for state in states_to_create:
                state_obj = WidgetStateObject()
                state_obj.set_prop('name', state)
                obj.add_child(state_obj)
            self.add_theme_object(obj)

    def on_drawingarea_button_press_event(self, widget, evt):
        if evt.button == 1:
            if self.insert_object_class is None:
                if self.current_dialog:
                    obj = self.find_object(evt.x, evt.y)

                    if obj == self.current_obj and self.current_obj is not None:
                        obj_x,obj_y,obj_w,obj_h = self.get_current_obj_rect()
                        obj_xw = obj_x + obj_w
                        obj_yh = obj_y + obj_h

                        self.current_obj_drag_start = (evt.x, evt.y)
                        self.drag_location_delta = (0,0)

                        if evt.x >= obj_x and evt.y >= obj_y and \
                            evt.x <= obj_x + RESIZE_SQUARE_SIZE and evt.y <= obj_y + RESIZE_SQUARE_SIZE:
                            self.drag_type = 'resize_tl'

                        elif evt.x >= obj_xw - RESIZE_SQUARE_SIZE and evt.y >= obj_y and \
                            evt.x <= obj_xw and evt.y <= obj_y + RESIZE_SQUARE_SIZE:
                            self.drag_type = 'resize_tr'

                        elif evt.x >= obj_x and evt.y >= obj_yh - RESIZE_SQUARE_SIZE and \
                            evt.x <= obj_x + RESIZE_SQUARE_SIZE and evt.y <= obj_yh:
                            self.drag_type = 'resize_bl'

                        elif evt.x >= obj_xw - RESIZE_SQUARE_SIZE and evt.y >= obj_yh - RESIZE_SQUARE_SIZE and \
                            evt.x <= obj_xw and evt.y <= obj_yh:
                            self.drag_type = 'resize_br'

                        else:
                            self.drag_type = 'move'
                    else:
                        self.set_current_object(obj)

            else:
                x = int(evt.x - 10)
                y = int(evt.y - 10)
                if self.current_dialog and \
                    x >= self.current_dialog.x and y >= self.current_dialog.y and \
                     x < self.current_dialog.x + self.current_dialog.width and \
                     y < self.current_dialog.y + self.current_dialog.height:
                    obj = self.insert_object_class()
                    obj.set_position(x - self.current_dialog.x, y - self.current_dialog.y)
                    self.add_dialog_object(obj)
                    self.select_toolbutton.set_active(True)

    def on_drawingarea_button_release_event(self, widget, evt):
        if self.current_obj and self.current_obj_drag_start:
            x,y,w,h = self.get_current_obj_drag_rect()
            self.set_current_obj_pos(x, y)
            self.set_current_obj_size(w, h)
            self.update_prop_values()
            self.current_obj_drag_start = None
            self.drag_type = None
            self.render_current_dialog()

    def on_drawingarea_motion_notify_event(self, widget, evt):
        if self.current_obj and self.current_obj_drag_start:
            delta_x = int(evt.x - self.current_obj_drag_start[0])
            delta_y = int(evt.y - self.current_obj_drag_start[1])
            self.drag_location_delta = (delta_x, delta_y)
            self.set_statusbar_text('Position %d,%d Size %d x %d' % self.get_current_obj_drag_rect())
            self.on_drawingarea_expose_event()

    def on_osds_treeview_button_press_event(self, widget, evt):
        if evt.button == 3:
            self.items_menu.popup(None, None, None, evt.button, evt.time)

    def on_osds_treeview_cursor_changed(self, *args):
        iter = self.osds_treeview.get_selection().get_selected()[1]
        if iter:
            obj = self.theme_treemodel.get_value(iter, 0)
            if isinstance(obj, DialogObject):
                self.set_current_dialog(obj, iter)
            self.set_current_object(obj)
        else:
            self.set_current_object(None)

    def on_drawingarea_expose_event(self, *args):
        context = self.drawingarea.window.cairo_create()

        if isinstance(self.current_dialog, WidgetStateObject):
            self.draw_current_state(context)

        elif isinstance(self.current_dialog, DialogObject):
            self.draw_current_dialog(context)


    def on_new_theme_activated(self, *args):
        self.new_theme()

    def on_save_theme_activated(self, *args):
        if self.theme_filename:
            self.save_theme(self.theme_filename)
        else:
            self.on_saveas_theme_mi_activated()

    def on_open_theme_activated(self, *args):
        self.open_filechooser.set_filter(self.fxd_file_filter)
        response = self.open_filechooser.run()
        self.open_filechooser.hide()
        if response == gtk.RESPONSE_OK:
            self.load_theme(self.open_filechooser.get_filename())


    def on_saveas_theme_mi_activate(self, *args):
        self.save_theme_as()

    def on_quit_mi_activated(self, *args):
        self.quit()

    def on_name_value_entry_activate(self, *args):
        name = self.name_entry.get_text()
        value = self.value_entry.get_text()
        try:
            value = eval(value)
        except:
            pass
        if name in self.current_dialog.info_dict:
            model,iter = self.info_treeview.get_selection().get_selected()
            model.set_value(iter, 1, repr(value))
        else:
            model = self.info_treeview.get_model()
            model.append((name, repr(value)))
        self.current_dialog.info_dict[name] = value
        self.render_current_dialog()

    def on_info_treeview_cursor_changed(self, *args):
        model,iter = self.info_treeview.get_selection().get_selected()
        if iter:
            name = model.get_value(iter, 0)
            value = model.get_value(iter, 1)
        else:
            name = ''
            value = ''
        self.name_entry.set_text(name)
        self.value_entry.set_text(value)


    def on_info_treeview_button_press_event(self, widget, evt):
        if evt.button == 3:
            model,iter = self.info_treeview.get_selection().get_selected()
            self.info_delete_menuitem.set_sensitive( iter != None)
            self.info_menu.popup(None, None, None, evt.button, evt.time)

    def on_info_delete_menuitem_activate(self, *args):
        model,iter = self.info_treeview.get_selection().get_selected()
        name = model.get_value(iter, 0)
        model.remove(iter)
        del self.current_dialog.info_dict[name]
        self.render_current_dialog()

    def on_dialog_bg_choose_button_clicked(self, *args):
        self.background_filechooser.set_filter(self.image_file_filter)
        response = self.background_filechooser.run()
        self.background_filechooser.hide()
        if response == gtk.RESPONSE_OK:
            found = False
            new_filename = self.background_filechooser.get_filename()
            index = 0
            for filename, in self.background_model:
                if filename == new_filename:
                    found = True
                    break
                index += 1
            if not found:
                self.background_model.append((new_filename,))
            self.dialog_bg_combobox.set_active(index)

    def on_dialog_bg_combobox_changed(self, *args):
        iter = self.dialog_bg_combobox.get_active_iter()
        if iter:
            filename = self.background_model.get_value(iter, 0)
            self.load_background(filename)


    def on_redo_activated(self, *args):
        self.redo()

    def on_undo_activated(self, *args):
        self.undo()

    def on_cut_activated(self, *args):
        self.cut_current_obj()

    def on_copy_activated(self, *args):
        self.copy_current_obj()

    def on_paste_activated(self, *args):
        self.paste_clipboard_obj()

    def on_delete_activated(self, *args):
        self.delete_current_obj()

    def on_show_dialog_menuitem_toggled(self, *args):
        self.show_dialog_outline = self.show_dialog_menuitem.get_active()
        self.drawingarea.queue_draw()

    def on_colorselectiondialog_delete_event(self, *args):
        self.colorselectiondialog.hide()
        return True

    def on_new_style_dialog_delete_event(self, *args):
        self.new_style_dialog.hide()
        return True

    def on_add_state_menuitem_activate(self, *args):
        self.add_state(WidgetStateObject())

    def on_recent_menu_item_activated(self, *args):
        filename = self.recent_menu.get_current_uri()[7:]
        self.load_theme(filename)

    def on_warnings_textview_populate_popup(self, textview, menu):
        sep_mi = gtk.SeparatorMenuItem()
        menu.append(sep_mi)
        sep_mi.show()
        clear_mi = gtk.ImageMenuItem(gtk.STOCK_CLEAR)
        menu.append(clear_mi)
        clear_mi.show()
        clear_mi.connect('activate', self.on_warnings_clear_menuitem_activate)

    def on_warnings_clear_menuitem_activate(self, *args):
        self.warnings_textview.get_buffer().set_text('')

    def on_choose_image_dialog_delete_event(self, *args):
        self.choose_image_dialog.hide()
        return True

    def on_images_dir_combobox_changed(self, *args):
        self.images_model.clear()
        self.images_iconview.unselect_all()
        dir = self.images_dir_combobox.get_active_text()
        self.__enable_image_chooser(False)
        thread = threading.Thread(target=self.__load_images, args=(dir,))
        thread.start()

    def on_images_iconview_selection_changed(self, *args):
        items = self.images_iconview.get_selected_items()
        if items:
            self.choose_image_ok_button.set_sensitive(True)
        else:
            self.choose_image_ok_button.set_sensitive(False)

    def on_images_iconview_item_activated(self, *args):
        self.choose_image_dialog.response(1)

    #--------------------------------------------------------------------------
    # Load/Save methods
    #--------------------------------------------------------------------------
    def load_theme(self, filename):
        if self.unsaved_flag:
            if self.theme_filename is None:
                unsaved_filename = 'Unsaved'
            else:
                unsaved_filename = os.path.basename(self.theme_filename)
            messagedialog = gtk.MessageDialog(self.main_window,
                                              gtk.DIALOG_MODAL,
                                              gtk.MESSAGE_WARNING,
                                              gtk.BUTTONS_NONE,
                                              'Save changed to "%s"?' % unsaved_filename)
            messagedialog.format_secondary_text('Your changes will be lost if you do not save them.')
            messagedialog.add_buttons(gtk.STOCK_SAVE, 1)
            messagedialog.add_buttons(gtk.STOCK_CANCEL, 2)
            messagedialog.add_buttons('Close without saving', 3)
            response = messagedialog.run()
            messagedialog.destroy()

            if response == 2:
                return
            if response == 1:
                if self.theme_filename:
                    self.save_theme(self.theme_filename)
                else:
                    self.save_theme_as()

        theme_model = ThemeTreeModel()
        theme_model.load(filename)
        self.new_theme(theme_model)
        self.theme_filename = filename
        self.unsaved_flag = False
        self.main_window.set_title('Freevo OSD Designer (%s)' % self.theme_filename)
        self.recent_manager.add_item('file://' + os.path.abspath(filename))

    def save_theme(self, filename):
        self.theme_filename = filename
        try:
            self.theme_treemodel.save(filename)
            self.recent_manager.add_item('file://' + os.path.abspath(filename))
        except:
            import traceback
            traceback.print_exc()

        self.unsaved_flag = False
        self.main_window.set_title('Freevo OSD Designer (%s)' % self.theme_filename)

    def save_theme_as(self):
        self.saveas_filechooser.set_filter(self.fxd_file_filter)
        response = self.saveas_filechooser.run()
        self.saveas_filechooser.hide()
        if response == gtk.RESPONSE_OK:
            self.save_theme(self.saveas_filechooser.get_filename())

    #--------------------------------------------------------------------------
    # Drawing methods
    #--------------------------------------------------------------------------
    def draw_current_dialog(self, context):
        context.set_source_rgb(0,0,0)
        theme = self.theme_treemodel.theme

        if self.background_pixbuf:
            context.set_source_pixbuf(self.background_pixbuf, 10, 10)
            context.paint()
        else:
            context.set_source_rgb(1, 1, 1)
            context.rectangle(10,10, theme.width, theme.height)
            context.fill()
        # Draw screen bounding box
        context.set_source_rgb(0, 0, 0)
        context.rectangle( 9, 9, theme.width + 1, theme.height + 1)
        context.stroke()

        # Draw dialog
        if self.current_dialog_pixbuf:
            context.set_source_pixbuf(self.current_dialog_pixbuf,
                                      10 + self.current_dialog.x, 10 + self.current_dialog.y)
            context.paint()

        # Draw bounding box round dialog if not current object
        if self.current_dialog != self.current_obj and self.show_dialog_outline:
            context.save()
            #context.set_line_width(0.2)
            context.set_dash([10,], 0)
            context.set_source_rgb(0.5,0.5,0.5)
            context.rectangle( 10 + self.current_dialog.x, 10 + self.current_dialog.y,
                               self.current_dialog.width, self.current_dialog.height)
            context.stroke()
            context.restore()

        # Draw selected object bounding box
        rect = self.get_current_obj_drag_rect()
        if rect and (self.current_obj.parent == self.current_dialog or self.current_obj == self.current_dialog):
            x,y,w,h = rect

            context.set_source_rgb(1, 0, 0)
            context.rectangle(x, y, w, h)
            context.stroke()
            if w > RESIZE_SQUARE_SIZE and h > RESIZE_SQUARE_SIZE:
                context.rectangle(x, y, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()
                context.rectangle(x + w - RESIZE_SQUARE_SIZE, y, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()
                context.rectangle(x + w - RESIZE_SQUARE_SIZE, y + h - RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()
                context.rectangle(x, y + h - RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()

    def draw_current_state(self, context):
        style = self.current_dialog.parent
        context.set_source_rgb(1, 1, 1)
        context.rectangle(10,10, style.width, style.height)
        context.fill()

        if self.current_dialog_pixbuf:
            context.set_source_pixbuf(self.current_dialog_pixbuf,
                                      10 + self.current_dialog.x, 10 + self.current_dialog.y)
            context.paint()

        rect = self.get_current_obj_drag_rect()
        if rect:
            x,y,w,h = rect

            context.set_source_rgb(1, 0, 0)
            context.rectangle(x, y, w, h)
            context.stroke()
            if w > RESIZE_SQUARE_SIZE and h > RESIZE_SQUARE_SIZE:
                context.rectangle(x, y, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()
                context.rectangle(x + w - RESIZE_SQUARE_SIZE, y, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()
                context.rectangle(x + w - RESIZE_SQUARE_SIZE, y + h - RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()
                context.rectangle(x, y + h - RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE, RESIZE_SQUARE_SIZE)
                context.fill()

    #--------------------------------------------------------------------------
    # Model management methods
    #--------------------------------------------------------------------------
    def new_theme(self, model=None):
        if model is None:
            model = ThemeTreeModel()
        model.theme.signals['property-changed'].connect(self.theme_prop_changed)
        self.theme_treemodel = model
        self.osds_treeview.set_model(self.theme_treemodel)
        self.theme_filename = None
        self.drag_type = None
        self.set_current_dialog(None, None)
        self.current_obj = None
        self.current_obj_drag_start = None
        self.drag_location_delta = None
        self.set_current_object(None)
        self.undo_stack = []
        self.redo_stack = []
        self.unsaved_flag = True
        self.update_undo_redo_buttons()
        # Force drawing area to be resized
        self.theme_prop_changed(model.theme, 'width', 0, model.theme.width)

    def add_theme_object(self, obj):
        path = self.theme_treemodel.add(self.theme_treemodel.theme, obj)
        self.osds_treeview.expand_to_path(path)
        self.set_unsaved()

    def add_dialog_object(self, obj):
        if self.current_dialog is None:
            return
        path = self.theme_treemodel.add(self.current_dialog, obj)
        self.osds_treeview.get_selection().select_path(path)
        self.osds_treeview.expand_to_path(path)
        self.set_current_object(obj)
        self.set_unsaved()

    def add_state(self, obj):
        if self.current_obj is None:
            return
        path = self.theme_treemodel.add(self.current_obj, obj)
        self.osds_treeview.get_selection().select_path(path)
        self.osds_treeview.expand_to_path(path)
        self.set_current_object(obj)
        self.set_unsaved()

    def set_current_dialog(self, obj, iter):
        if obj is None:
            self.name_entry.set_sensitive(False)
            self.value_entry.set_sensitive(False)
            self.info_treeview.set_sensitive(False)
        else:
            self.name_entry.set_sensitive(True)
            self.value_entry.set_sensitive(True)
            self.info_treeview.set_sensitive(True)

            model = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
            for name,value in obj.info_dict.items():
                if name != '__builtins__':
                    model.append((name,repr(value)))
            self.info_treeview.set_model(model)
            self.name_entry.set_text('')
            self.value_entry.set_text('')

        self.current_dialog = obj
        self.current_dialog_iter = iter
        self.render_current_dialog()

    def set_current_object(self, obj):
        prop_table = self.props_pack_alignment.get_child()
        if prop_table:
            self.props_pack_alignment.remove(prop_table)

        if obj == None:
            self.current_obj = None
        else:
            rows = len(obj.properties)

            if obj.type == 'dialog' or obj.type == 'color':
                rows += 1
            new_props_table = gtk.Table(rows=rows, columns=2)
            idx = 0
            widget_to_name = {}
            name_to_widget = {}
            for prop in obj.properties:
                label = gtk.Label(prop[1] + ':')
                label.set_alignment(1.0, 0.5)
                new_props_table.attach(label, 0, 1, idx, idx+1, xoptions=gtk.FILL, yoptions=gtk.FILL)

                if prop[2] == PROP_TYPE_STRING:
                    if len(prop) == 3:
                        widget = gtk.Entry()
                        widget.connect('focus-out-event', self.on_prop_value_changed)
                        widget.connect('activate',  self.on_prop_value_changed)
                    else:
                        widget = gtk.combo_box_entry_new_text()
                        if callable(prop[3]):
                            options = prop[3]()
                        else:
                            options = prop[3]
                        for option in options:
                            widget.append_text(option)
                        widget.connect('changed', self.on_prop_value_changed)
                        widget.connect('focus-out-event', self.on_prop_value_changed)
                        widget.child.connect('activate',  self.on_prop_value_changed)

                elif prop[2] == PROP_TYPE_TEXT:
                    textview = gtk.TextView()
                    textview.connect('focus-out-event', self.on_prop_value_changed)
                    widget_to_name[textview] = prop[0]
                    widget = gtk.ScrolledWindow()
                    widget.add(textview)

                elif prop[2] == PROP_TYPE_INT:
                    widget = gtk.SpinButton()
                    range = prop[3]
                    widget.set_range(float(range[0]),float(range[1]))
                    widget.set_increments(1.0, 1.0)
                    widget.connect('value-changed', self.on_prop_value_changed)

                elif prop[2] == PROP_TYPE_BOOL:
                    widget = gtk.ToggleButton()
                    widget.set_label('Yes')
                    widget.connect('toggled', self.on_prop_value_changed)

                elif prop[2] == PROP_TYPE_OPTION:
                    widget = gtk.combo_box_new_text()

                    if callable(prop[3]):
                        options = prop[3]()
                    else:
                        options = prop[3]
                    for option in options:
                        widget.append_text(option)
                    widget.connect('changed', self.on_prop_value_changed)

                elif prop[2] == PROP_TYPE_IMAGE:
                    widget = ImageFileWidget(self.show_image_chooser, self.on_prop_value_changed)

                new_props_table.attach(widget, 1, 2, idx, idx +1, yoptions=gtk.FILL)

                widget_to_name[widget] = prop[0]
                name_to_widget[prop[0]] = widget
                idx += 1

            if obj.type == 'dialog':
                button = gtk.Button('Autosize')
                button.set_tooltip_text('Determines the smallest size required by the dialog')
                button.connect('clicked', self.on_autosize_clicked)
                new_props_table.attach(button, 1, 2, idx, idx +1, yoptions=gtk.FILL)
            elif obj.type == 'color':
                button = gtk.Button('Select color')
                button.connect('clicked', self.on_select_color_clicked)
                new_props_table.attach(button, 1, 2, idx, idx +1, yoptions=gtk.FILL)


            self.current_obj = obj
            self.prop_to_widget = name_to_widget
            self.widget_to_prop = widget_to_name
            self.props_pack_alignment.add(new_props_table)
            self.update_prop_values()

        if isinstance(obj, WidgetStyleObject):
            self.item_separator_menuitem.show()
            self.add_state_menuitem.show()
        else:
            self.item_separator_menuitem.hide()
            self.add_state_menuitem.hide()

        if isinstance(obj, DialogChildObject) or isinstance(obj, DialogObject):
            x,y,w,h = self.get_current_obj_rect()
            x -= 10
            y -= 10
            self.set_statusbar_text('Position %d,%d Size %d x %d' % (x,y,w,h))
        else:
            self.set_statusbar_text('')
        if self.current_obj:
            path = self.theme_treemodel.get_object_path(self.current_obj)
            self.osds_treeview.expand_to_path(path)
            self.osds_treeview.get_selection().select_path(path)
        else:
            self.osds_treeview.get_selection().unselect_all()

        if self.current_obj is self.theme_treemodel.theme:
            self.enabled_cut_copy(False)
        else:
            self.enabled_cut_copy(self.current_obj is not None)
        self.update_current_object_label()
        self.props_pack_alignment.show_all()
        self.props_pack_alignment.queue_draw()
        self.drawingarea.queue_draw()

    def update_prop_values(self):
        self.updating_values = True

        for prop in self.current_obj.properties:
            widget = self.prop_to_widget[prop[0]]
            value = self.current_obj.get_prop(prop[0])
            if prop[2] == PROP_TYPE_STRING:
                if len(prop) == 4:
                    widget = widget.child
                widget.set_text(value)

            elif prop[2] == PROP_TYPE_TEXT:
                widget.get_child().get_buffer().set_text(value)

            elif prop[2] == PROP_TYPE_INT:
                widget.set_value(float(value))

            elif prop[2] == PROP_TYPE_BOOL:
                widget.set_active(value)

            elif prop[2] == PROP_TYPE_OPTION:
                model = widget.get_model()
                for i in xrange(len(model)):
                    if model[i][0] == value:
                        widget.set_active(i)
                        break

            elif prop[2] == PROP_TYPE_IMAGE:
                widget.set_text( value)
        self.updating_values = False

    def update_current_object_label(self):
        if self.current_obj:
            try:
                name = '(%s)' % self.current_obj.get_prop('name')
            except:
                name = ''
            self.props_label.set_text(self.current_obj.type + name)
        else:
            self.props_label.set_text('Nothing selected')

    def on_prop_value_changed(self, widget, *args):
        if not self.updating_values and self.current_obj:
            prop = self.widget_to_prop[widget]

            value = None
            orig_value = self.current_obj.get_prop(prop)
            if isinstance(widget, ImageFileWidget):
                value = widget.get_text()
            elif isinstance(widget, gtk.SpinButton):
                value = widget.get_value_as_int()
            elif isinstance(widget, gtk.TextView):
                buffer = widget.get_buffer()
                value = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())
            elif isinstance(widget, gtk.Entry):
                value = widget.get_text()
            elif isinstance(widget, gtk.ComboBox):
                value = widget.get_active_text()
            elif isinstance(widget, gtk.ToggleButton):
                value = widget.get_active()


            if value is not None and value != orig_value:
                try:
                    self.current_obj.set_prop(prop, value)
                    text = ''
                    for p in self.current_obj.properties:
                        if p[0] == prop:
                            text = p[1]
                            break

                    self.add_undo(PropertyChangeAction(self.current_obj, prop, text, orig_value, value))
                    self.set_unsaved()
                    self.render_current_dialog()

                    if prop == 'name':
                        self.osds_treeview.queue_draw()
                        self.update_current_object_label()
                except InvalidValueError, ex:
                    print ex.msg

    def on_autosize_clicked(self, *args):
        self.current_obj.update_position_size()
        self.update_prop_values()
        self.set_unsaved()
        self.render_current_dialog()

    def on_select_color_clicked(self, *args):
        color = gtk.gdk.Color(self.current_obj.get_prop('red') * 257,
                              self.current_obj.get_prop('green') * 257,
                              self.current_obj.get_prop('blue') * 257)
        alpha = self.current_obj.get_prop('alpha') * 257
        self.colorselectiondialog.colorsel.set_current_color(color)
        self.colorselectiondialog.colorsel.set_current_alpha(alpha)
        response = self.colorselectiondialog.run()
        self.colorselectiondialog.hide()
        if response == 1:
            new_color = self.colorselectiondialog.colorsel.get_current_color()
            new_alpha = self.colorselectiondialog.colorsel.get_current_alpha()
            if new_color.red != color.red or \
               new_color.green != color.green or \
               new_color.blue != color.blue or \
               new_alpha != alpha:
                self.current_obj.set_prop('red', new_color.red / 257)
                self.current_obj.set_prop('green', new_color.green / 257)
                self.current_obj.set_prop('blue', new_color.blue / 257)
                self.current_obj.set_prop('alpha', new_alpha / 257)
                self.update_prop_values()
                self.set_unsaved()
                self.render_current_dialog()

    def get_current_obj_rect(self):
        rect = None
        if isinstance(self.current_obj, DialogChildObject):
            rect = self.current_obj.parent.get_child_rect(self.current_obj)
            rect = (rect[0] + 10 +  self.current_obj.parent.x,
                    rect[1] + 10 +  self.current_obj.parent.y ,
                    rect[2], rect[3])

        elif isinstance(self.current_obj, DialogObject):
            rect = (self.current_obj.x + 10, self.current_obj.y + 10,
                    self.current_obj.width, self.current_obj.height)

        if rect is None:
            logger.debug('get_current_obj_rect() returning None for object of type %s', self.current_obj.__class__.__name__)
        return rect

    def set_current_obj_pos(self, x, y):
        if isinstance(self.current_obj, DialogChildObject):
            x -= 10 + self.current_obj.parent.x
            y -= 10 + self.current_obj.parent.y
        elif isinstance(self.current_obj, DialogObject):
            x -= 10
            y -= 10
        orig_pos = self.current_obj.get_position()
        if orig_pos[0] != x or orig_pos[1] != y:
            self.current_obj.set_position(x, y)
            self.add_undo(MoveAction(self.current_obj, orig_pos, (x,y)))

    def set_current_obj_size(self, w, h):
        orig_size = self.current_obj.get_size()
        if orig_size[0] != w or orig_size[1] != h:
            self.current_obj.set_size(w,h)
            self.add_undo(ResizeAction(self.current_obj, orig_size, (w,h)))

    def find_object(self, x, y):
        x -= 10
        y -= 10

        obj = self.current_dialog.find_child(x - self.current_dialog.x, y - self.current_dialog.y)
        if obj is None:
            if self.current_dialog.x <= x and self.current_dialog.y <= y and \
               self.current_dialog.x + self.current_dialog.width > x and \
               self.current_dialog.y + self.current_dialog.height > y:
                obj = self.current_dialog
        return obj

    def get_current_obj_drag_rect(self):
        if self.current_obj is None:
            return None

        rect = self.get_current_obj_rect()
        if rect is None:
            return None

        x,y,w,h = rect
        if self.drag_type == 'move':
            x += self.drag_location_delta[0]
            y += self.drag_location_delta[1]
        elif self.drag_type == 'resize_tl':
            x += self.drag_location_delta[0]
            y += self.drag_location_delta[1]
            w -= self.drag_location_delta[0]
            h -= self.drag_location_delta[1]
        elif self.drag_type == 'resize_tr':
            y += self.drag_location_delta[1]
            w += self.drag_location_delta[0]
            h -= self.drag_location_delta[1]
        elif self.drag_type == 'resize_bl':
            x += self.drag_location_delta[0]
            w -= self.drag_location_delta[0]
            h += self.drag_location_delta[1]
        elif self.drag_type == 'resize_br':
            w += self.drag_location_delta[0]
            h += self.drag_location_delta[1]

        if w < 1:
            w = 1
        if h < 1:
            h = 1
        return (x,y,w,h)

    def get_cell_type(self, column, cell, model, iter):
        obj = model.get_value(iter, 0)
        cell.set_property('pixbuf', self.type_pixbufs[obj.type])

    def get_cell_name(self, column, cell, model, iter):
        obj = model.get_value(iter, 0)
        try:
            name = obj.get_prop('name')
        except:
            name = ''
        cell.set_property('text', name)

    def set_statusbar_text(self, text):
        self.statusbar.pop(self.statusbar_context_id)
        self.statusbar.push(self.statusbar_context_id, text)

    def render_current_dialog(self):
        if self.current_dialog:
            img = self.current_dialog.draw()
            self.current_dialog_pixbuf = img.as_gdk_pixbuf()

        else:
            self.current_dialog_pixbuf = None

        self.drawingarea.queue_draw()

    def skin_error(self, error):
        buffer = self.warnings_textview.get_buffer()
        insert = buffer.get_insert()
        buffer.move_mark(insert, buffer.get_end_iter())

        buffer.insert(buffer.get_end_iter(), error + '\n')

        scroll_to_end = True
        scrollbar = self.warnings_scrolledwindow.get_vscrollbar()
        if scrollbar:
            try:
                adjustment = scrollbar.get_adjustment()
                if adjustment.upper - adjustment.page_size != adjustment.value:
                    scroll_to_end = False
            except:
                traceback.print_exc()
        if scroll_to_end:
            self.warnings_textview.scroll_to_mark(insert, 0.4, True, 0.0, 1.0)

    def load_background(self, filename):
        w = self.theme_treemodel.theme.width
        h = self.theme_treemodel.theme.height
        self.background_pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, w, h)
        self.drawingarea.queue_draw()

    def theme_prop_changed(self, theme, prop, old_value, new_value):
        if prop in ('width', 'height'):
            self.drawingarea.set_size_request(theme.width + 20,
                                             theme.height + 20)

    #--------------------------------------------------------------------------
    # Undo/Redo methods
    #--------------------------------------------------------------------------
    def undo(self):
        action = self.undo_stack.pop()
        action.undo()
        self.redo_stack.append(action)
        self.update_undo_redo_buttons()
        self.update_prop_values()
        self.render_current_dialog()
        self.drawingarea.queue_draw()
        self.set_unsaved()

    def redo(self):

        action = self.redo_stack.pop()
        action.redo()
        self.undo_stack.append(action)
        self.update_undo_redo_buttons()
        self.update_prop_values()
        self.render_current_dialog()
        self.drawingarea.queue_draw()
        self.set_unsaved()

    def add_undo(self, action):
        if self.redo_stack:
            self.redo_stack = []
        self.undo_stack.append(action)
        self.update_undo_redo_buttons()

    def update_undo_redo_buttons(self):
        enable_undo = len(self.undo_stack) > 0
        enable_redo = len(self.redo_stack) > 0
        self.undo_menuitem.set_sensitive(enable_undo)
        self.undo_toolbutton.set_sensitive(enable_undo)
        self.redo_menuitem.set_sensitive(enable_redo)
        self.redo_toolbutton.set_sensitive(enable_redo)

    def set_unsaved(self):
        self.unsaved_flag = True
        filename = self.theme_filename
        if filename is None:
            filename = 'Unsaved'

        self.main_window.set_title('Freevo OSD Designer (%s) *' % filename)
    #--------------------------------------------------------------------------
    # Clipboard methods
    #--------------------------------------------------------------------------
    def enabled_cut_copy(self, enable):
        self.cut_menuitem.set_sensitive(enable)
        self.item_cut_menuitem.set_sensitive(enable)
        self.copy_menuitem.set_sensitive(enable)
        self.item_copy_menuitem.set_sensitive(enable)
        self.delete_menuitem.set_sensitive(enable)
        self.item_delete_menuitem.set_sensitive(enable)

    def delete_current_obj(self):
        obj = self.current_obj
        parent = obj.parent
        index = parent.children.index(obj)
        self.theme_treemodel.remove(obj)
        self.add_undo(DeleteAction(self.theme_treemodel, parent, obj, index))
        self.set_current_object(None)

    def cut_current_obj(self):
        obj = self.current_obj
        self.delete_current_obj()
        self.set_clipboard_obj(obj)

    def copy_current_obj(self):
        self.set_clipboard_obj(self.current_obj)

    def paste_clipboard_obj(self):
        parent = self.current_obj
        if isinstance(parent, DialogChildObject) or \
           isinstance(parent, ColorObject) or \
           isinstance(parent, FontObject):
            parent = parent.parent

        if isinstance(parent, WidgetStateObject) and isinstance(self.clipboard_obj, WidgetObject):
            print 'Can\'t do that! No widgets in a widget state!'

        elif isinstance(parent, WidgetStyleObject) and not isinstance(self.clipboard_obj, WidgetStateObject):
            print 'Can\'t do that! Only widget states in a widget style'

        elif isinstance(parent, ThemeObject) and isinstance(self.clipboard_obj, DialogChildObject):
            print 'Can\'t do that! Can only add dialog child objects to a dialog or widget state!'

        else:
            print 'Adding %r to %r' % (self.clipboard_obj, parent)
            obj = self.clipboard_obj.copy()
            self.theme_treemodel.add(parent, obj)


    def set_clipboard_obj(self, obj):
        self.clipboard_obj = obj
        paste_enabled = obj is not None
        self.paste_menuitem.set_sensitive(paste_enabled)
        self.item_paste_menuitem.set_sensitive(paste_enabled)

    #--------------------------------------------------------------------------
    # Misc methods
    #--------------------------------------------------------------------------
    def show_image_chooser(self):
        model = gtk.ListStore(gobject.TYPE_STRING)
        icontheme = self.theme_treemodel.theme.icontheme
        if icontheme:
            search_dirs = [os.path.join(config.IMAGE_DIR, 'osd', icontheme),
                    os.path.join(config.ICON_DIR, 'osd', icontheme)]
        else:
            search_dirs = []
        search_dirs = search_dirs + [os.path.join(config.IMAGE_DIR, 'osd'),
                       os.path.join(config.ICON_DIR, 'osd'),
                       config.IMAGE_DIR,
                       config.ICON_DIR]
        dirs = list(search_dirs)
        while len(dirs):
            dir = dirs.pop()
            if os.path.exists(dir):
                model.append((dir,))
                for filename in os.listdir(dir):
                    if os.path.isdir(dir +'/'+ filename) and filename != '.svn':
                        dirs.insert(0, dir +'/'+ filename)

        self.choose_image_ok_button.set_sensitive(False)
        self.images_dir_combobox.set_model(model)
        self.images_dir_combobox.set_active(0)

        response = self.choose_image_dialog.run()
        self.choose_image_dialog.hide()
        if response == 1:
            paths = self.images_iconview.get_selected_items()
            if paths:
                filename = self.images_model[paths[0]][2]
                for dir in search_dirs:
                    if filename.startswith(dir):
                        return filename[len(dir) + 1:]
        return None

    def __load_images(self, dir):
        try:
            for filename in os.listdir(dir):
                path = dir + '/' + filename
                if IMAGE_FILE_REGEX.match(filename) and os.path.isfile(path):
                    pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(path, 32, 32)
                    info = gtk.gdk.pixbuf_get_file_info(path)
                    gobject.idle_add(self.__image_loaded, pixbuf, filename + ' (%dx%d)' % info[1:], path)
        except:
            traceback.print_exc()
        gobject.idle_add(self.__enable_image_chooser, True)

    def __image_loaded(self, pixbuf, text, path):
        self.images_model.append((pixbuf, text, path))
        return False

    def __enable_image_chooser(self, enable):
        self.images_dir_combobox.set_sensitive(enable)
        self.images_iconview.set_sensitive(enable)
        self.choose_image_cancel_button.set_sensitive(enable)
        return False

    def main(self):
        gtk.main()

    def quit(self):
        if self.unsaved_flag:
            if self.theme_filename is None:
                filename = 'Unsaved'
            else:
                filename = os.path.basename(self.theme_filename)
            messagedialog = gtk.MessageDialog(self.main_window,
                                              gtk.DIALOG_MODAL,
                                              gtk.MESSAGE_WARNING,
                                              gtk.BUTTONS_NONE,
                                              'Save changed to "%s" before closing?' % filename)
            messagedialog.format_secondary_text('Your changes will be lost if you do not save them.')
            messagedialog.add_buttons(gtk.STOCK_SAVE, 1)
            messagedialog.add_buttons(gtk.STOCK_CANCEL, 2)
            messagedialog.add_buttons('Close without saving', 3)
            response = messagedialog.run()
            messagedialog.destroy()

            if response == 2:
                return False
            if response == 1:
                if self.theme_filename:
                    self.save_theme(self.theme_filename)
                else:
                    self.save_theme_as()
        self.save_settings()
        gtk.main_quit()
        return True

    def save_settings(self):
        filenames = []
        for filename, in self.background_model:
            filenames.append(filename)
        show_dialog_outline = self.show_dialog_menuitem.get_active()

        settings = (1, filenames, show_dialog_outline)
        try:
            fp = open(config.FREEVO_STATICDIR + '/osddesigner.settings', 'wb')
            pickle.dump(settings, fp, -1)
            fp.close()
        except:
            traceback.print_exc()

    def load_settings(self):
        settings = None
        try:
            fp = open(config.FREEVO_STATICDIR + '/osddesigner.settings')
            settings = pickle.load(fp)
            fp.close()
        except:
            traceback.print_exc()

        if settings:
            if settings[0] == 1:
                for filename in settings[1]:
                    self.background_model.append((filename,))
                self.show_dialog_menuitem.set_active(settings[2])

if __name__ == "__main__":
    if len(sys.argv) > 2:
        filename = sys.argv[2]
    else:
        filename = None
    gtk.gdk.threads_init()
    designer = Designer(filename)
    designer.main()
