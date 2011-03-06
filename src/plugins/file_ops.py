# -*- coding: iso-8859-1 -*-
# -----------------------------------------------------------------------
# file_ops.py - Small file operations (currently only delete)
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


import os
import config
import plugin
import util

import dialog
from dialog.dialogs import ProgressDialog
from skin.widgets import TextEntryScreen
from gui.AlertBox import AlertBox

class PluginInterface(plugin.ItemPlugin):
    """
    small plugin to delete files
    """
    def config(self):
        return [ ('FILE_OPS_ALLOW_DELETE_IMAGE', True,
                  'Add delete image to the menu.'),
                 ('FILE_OPS_ALLOW_DELETE_EDL', True,
                  'Add delete edl to the menu.'),
                 ('FILE_OPS_ALLOW_DELETE_INFO', True,
                  'Add delete info to the menu.') ]


    def actions(self, item):
        """
        create list of possible actions
        """
        if not item.parent or not item.parent.type == 'dir':
            # only activate this for directory listings
            return []

        self.item = item

        items = []

        if hasattr(item, 'files') and item.files:
            if item.files.fxd_file and config.FILE_OPS_ALLOW_DELETE_INFO and \
                    not getattr(item, 'file_ops_no_delete_info', False):
                items.append((self.confirm_info_delete, _('Delete info'), 'delete_info'))
            if item.files.edl_file and config.FILE_OPS_ALLOW_DELETE_EDL and \
                    not getattr(item, 'file_ops_no_delete_edl', False):
                items.append((self.confirm_edl_delete, _('Delete edl'), 'delete_edl'))
            if item.files.image and config.FILE_OPS_ALLOW_DELETE_IMAGE and \
                    not getattr(item, 'file_ops_no_delete_image', False):
                items.append((self.confirm_image_delete, _('Delete image'), 'delete_image'))
            if item.files.delete_possible():
                items.append((self.confirm_delete, _('Delete'), 'delete'))
            if item.rename_possible():
                items.append((self.rename_box, _('Rename'), 'rename'))
        return items


    def confirm_delete(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Do you wish to delete\n \'%s\'?') % self.item.name,
                   self.delete_file, proceed_text=_('Delete'))


    def confirm_info_delete(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Delete info about\n \'%s\'?') % self.item.name,
                   self.delete_info, proceed_text=_('Delete info'))


    def confirm_edl_delete(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Delete edl about\n \'%s\'?') % self.item.name,
                   self.delete_edl, proceed_text=_('Delete edl'))


    def confirm_image_delete(self, arg=None, menuw=None):
        self.menuw = menuw
        dialog.show_confirmation(_('Delete image about\n \'%s\'?') % self.item.name,
                   self.delete_image, proceed_text=_('Delete image'))


    def safe_unlink(self, filename):
        try:
            os.unlink(filename)
        except Exception, why:
            print 'can\'t delete %r: %s' % (filename, why)


    def delete_file(self):
        dialog = ProgressDialog(_('Deleting...'), indeterminate=True)
        dialog.show()
        self.item.files.delete()
        dialog.hide()
        if self.menuw:
            self.menuw.delete_submenu(True, True)


    def delete_info(self):
        self.safe_unlink(self.item.files.image)
        self.safe_unlink(self.item.files.edl_file)
        self.safe_unlink(self.item.files.fxd_file)
        if self.menuw:
            self.menuw.delete_submenu(True, True)


    def delete_edl(self):
        self.safe_unlink(self.item.files.edl_file)
        if self.menuw:
            self.menuw.delete_submenu(True, True)


    def delete_image(self):
        self.safe_unlink(self.item.files.image)
        if self.item.parent:
            self.item.image = self.item.parent.image
        else:
            self.item.image = None
        if self.menuw:
            self.menuw.delete_submenu(True, True)


    def rename_box(self, arg=None, menuw=None):
        """
        shows rename interface
        """
        txt = TextEntryScreen((_('Rename'), self.rename), _('Rename'), self.item.name)
        txt.show(menuw)


    def rename(self, menuw, newname=''):
        """
        renames the item
        """
        _debug_('rename %s to %s' % (self.item.name, newname), 2)
        oldname = self.item.name
        if self.item.rename(newname):
            AlertBox(text=_('Rename %s to %s.') % (oldname, newname)).show()
        else:
            AlertBox(text=_('Rename %s to %s, failed.') % (oldname, newname)).show()
        menuw.delete_menu()
        menuw.refresh()
